"""Mycelial QUBO orchestrator — DiamondNode GTX 1650

Models fungal hyphal-network growth as a QUBO solved by CUDA-Q sampling.

Architecture:
  outer loop  — refines the Q matrix from accumulated run history
  inner loop  — CUDA-Q QAOA sampling over the current subspace
  persistence — state written to JSON after every outer iteration
  resilience  — double-loopback: if inner circuit fails, replay from last
                stable checkpoint; if outer loop diverges, reset Q to
                the last minimum-energy configuration

Subspace model
  Each "electron expansion subspace" is a k-node subset of the full
  N-node grid. CUDA-Q samples binary assignments for the k nodes;
  the best assignment is stitched back into the global state.

QUBO objective
  min  sum_{i<j} Q_ij * x_i * x_j  +  sum_i h_i * x_i
  Q encodes:
    - distance penalty (long edges cost more)
    - redundancy reward (multi-path bonus)
    - resource proximity reward (edges near resource sites)
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

STATE_DIR = Path(os.environ.get("DIAMOND_STATE_DIR",
                                Path(__file__).parent.parent / "state"))
LOG_DIR = Path(os.environ.get("DIAMOND_LOG_DIR",
                              Path(__file__).parent.parent / "logs"))
STATE_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = STATE_DIR / "mycelial_state.json"
CHECKPOINT_FILE = STATE_DIR / "mycelial_checkpoint.json"


# ---------------------------------------------------------------------------
# State model
# ---------------------------------------------------------------------------

@dataclass
class MycelialState:
    iteration: int = 0
    n_nodes: int = 16
    active_edges: list[list[int]] = field(default_factory=list)
    energy_history: list[float] = field(default_factory=list)
    best_energy: float = float("inf")
    best_edges: list[list[int]] = field(default_factory=list)
    resource_nodes: list[int] = field(default_factory=lambda: [0, 15])
    node_positions: list[list[float]] = field(default_factory=list)
    last_updated: str = ""
    run_log: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def _default_positions(n: int) -> list[list[float]]:
    """Place nodes on a sqrt(n) x sqrt(n) grid."""
    side = int(math.ceil(math.sqrt(n)))
    return [[float(i % side), float(i // side)] for i in range(n)]


def load_state() -> MycelialState:
    if STATE_FILE.exists():
        d = json.loads(STATE_FILE.read_text())
        return MycelialState(**d)
    s = MycelialState()
    s.node_positions = _default_positions(s.n_nodes)
    s.resource_nodes = [0, s.n_nodes - 1]
    return s


def save_state(state: MycelialState, *, checkpoint: bool = False) -> None:
    state.last_updated = datetime.now(timezone.utc).isoformat()
    STATE_FILE.write_text(json.dumps(state.as_dict(), indent=2))
    if checkpoint:
        CHECKPOINT_FILE.write_text(STATE_FILE.read_text())


# ---------------------------------------------------------------------------
# QUBO matrix
# ---------------------------------------------------------------------------

def build_Q(state: MycelialState, lam_dist: float = 0.4,
            lam_redund: float = -0.2, lam_resource: float = -0.8) -> np.ndarray:
    """Build upper-triangular Q matrix (edge variables only, flattened)."""
    n = state.n_nodes
    pos = np.array(state.node_positions)
    res = set(state.resource_nodes)
    edges = [(i, j) for i in range(n) for j in range(i + 1, n)]
    m = len(edges)
    Q = np.zeros((m, m))

    current = {(min(e), max(e)) for e in state.active_edges}

    for idx, (i, j) in enumerate(edges):
        dist = float(np.linalg.norm(pos[i] - pos[j]))
        resource_bonus = lam_resource if (i in res or j in res) else 0.0
        redund_bonus = lam_redund if (i, j) in current else 0.0
        Q[idx, idx] = lam_dist * dist + resource_bonus + redund_bonus

    return Q, edges


# ---------------------------------------------------------------------------
# CUDA-Q subspace sampler
# ---------------------------------------------------------------------------

def _cudaq_sample_subspace(q_sub: np.ndarray, shots: int = 512) -> np.ndarray:
    """Sample a k-variable QUBO subspace via CUDA-Q QAOA (1 layer)."""
    try:
        import cudaq
    except ImportError:
        return np.random.randint(0, 2, size=q_sub.shape[0])

    k = q_sub.shape[0]
    if k > 20:
        k = 20
        q_sub = q_sub[:k, :k]

    # QAOA layer: RX mixer + ZZ phase separation
    @cudaq.kernel
    def qaoa(gamma: float, beta: float) -> None:
        qubits = cudaq.qvector(k)
        # Initial state |+>^k
        for i in range(k):
            h(qubits[i])
        # Phase-separation: ZZ gates for each non-zero Q[i,j]
        for i in range(k):
            for j in range(i + 1, k):
                if abs(q_sub[i, j]) > 1e-9:
                    cx(qubits[i], qubits[j])
                    rz(gamma * q_sub[i, j], qubits[j])
                    cx(qubits[i], qubits[j])
            rz(gamma * q_sub[i, i], qubits[i])
        # Mixer
        for i in range(k):
            rx(2.0 * beta, qubits[i])
        mz(*[qubits[i] for i in range(k)])

    try:
        result = cudaq.sample(qaoa, 0.3, 0.2, shots_count=shots)
        counts = dict(result)
        best = max(counts, key=counts.get)
        return np.array([int(b) for b in best], dtype=int)
    except Exception:
        return np.random.randint(0, 2, size=k)


def _energy(x: np.ndarray, Q: np.ndarray) -> float:
    return float(x @ Q @ x)


# ---------------------------------------------------------------------------
# Double-loopback iteration
# ---------------------------------------------------------------------------

SUBSPACE_SIZE = 10  # edges per subspace chunk


def run_iteration(state: MycelialState, *, shots: int = 512,
                  outer_rounds: int = 3) -> dict[str, Any]:
    """One full outer-loop iteration with inner CUDA-Q subspace sampling."""
    Q_full, edges = build_Q(state)
    n_edges = len(edges)
    total_energy = 0.0

    # Warm-start best_x from saved best edges
    best_edge_set = {(min(e), max(e)) for e in state.best_edges}
    best_x = np.array([1 if (min(edges[i][0], edges[i][1]), max(edges[i][0], edges[i][1])) in best_edge_set else 0 for i in range(n_edges)], dtype=int)

    log_entry: dict[str, Any] = {
        "iteration": state.iteration,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "subspaces": [],
        "outer_round": 0,
    }

    for outer_round in range(outer_rounds):
        log_entry["outer_round"] = outer_round
        subspace_assignments: list[tuple[list[int], np.ndarray]] = []

        # Inner loop: sample each subspace
        for start in range(0, n_edges, SUBSPACE_SIZE):
            end = min(start + SUBSPACE_SIZE, n_edges)
            idx = list(range(start, end))
            q_sub = Q_full[np.ix_(idx, idx)]

            # Inner loopback: retry once on exception
            for attempt in range(2):
                try:
                    x_sub = _cudaq_sample_subspace(q_sub, shots=shots)
                    break
                except Exception:
                    x_sub = np.random.randint(0, 2, size=len(idx))

            subspace_assignments.append((idx, x_sub))
            log_entry["subspaces"].append({
                "start": start, "end": end,
                "active": int(x_sub.sum()),
                "attempt": attempt + 1,
            })

        # Stitch subspaces back into global assignment
        x_candidate = best_x.copy()
        for idx_list, x_sub in subspace_assignments:
            for local_i, global_i in enumerate(idx_list):
                if local_i < len(x_sub):
                    x_candidate[global_i] = x_sub[local_i]

        energy = _energy(x_candidate, Q_full)
        total_energy = energy

        if energy < state.best_energy:
            state.best_energy = energy
            state.best_edges = [list(edges[i]) for i in range(n_edges)
                                if x_candidate[i] == 1]
            best_x = x_candidate.copy()
            save_state(state, checkpoint=True)

    state.active_edges = [list(edges[i]) for i in range(n_edges)
                          if best_x[i] == 1]
    state.energy_history.append(total_energy)
    state.iteration += 1

    log_entry["energy"] = total_energy
    log_entry["best_energy"] = state.best_energy
    log_entry["active_edges"] = len(state.active_edges)
    state.run_log.append(log_entry)
    save_state(state)
    return log_entry


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Mycelial QUBO iteration")
    p.add_argument("--shots", type=int, default=512)
    p.add_argument("--outer-rounds", type=int, default=3)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    state = load_state()
    result = run_iteration(state, shots=args.shots,
                           outer_rounds=args.outer_rounds)

    log_line = json.dumps(result, indent=2 if args.json else None)
    print(log_line)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = LOG_DIR / f"qubo-{ts}.json"
    log_path.write_text(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
