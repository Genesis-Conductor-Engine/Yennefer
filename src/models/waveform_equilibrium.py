"""Waveform Equilibrium at Eigenvector Planes — GTX 1650 Optimized

Mathematical functions for modeling quantum state evolution at eigenvector planes,
optimized for CUDA-Q QAOA on NVIDIA GTX 1650 (4GB VRAM).

Core Mathematical Framework:
============================

1. **Waveform Equilibrium Function**
   Ψ_eq(t) = Σ_k α_k |φ_k⟩ e^(-iλ_k t)
   
   where:
   - |φ_k⟩ are eigenvectors of QUBO Hamiltonian H
   - λ_k are eigenvalues (energy levels)
   - α_k are expansion coefficients from initial state
   - Equilibrium reached when dΨ/dt = 0 in projection to eigenspace

2. **Spectral Decomposition of QUBO Hamiltonian**
   H = Q⊗I - Σ_i h_i Z_i - Σ_{i<j} J_{ij} Z_i⊗Z_j
   
   Eigenspace decomposition:
   H = Σ_k λ_k |φ_k⟩⟨φ_k|
   
   Orthogonality: ⟨φ_i|φ_j⟩ = δ_{ij}

3. **Resource-Bounded Convergence Metrics**
   - VRAM efficiency: η_VRAM = (computational_throughput) / (VRAM_used)
   - Thermal efficiency: η_thermal = (iterations/sec) / (ΔT_gpu)
   - Convergence rate: ρ = -d(⟨H⟩)/dt at equilibrium

4. **Ising Hamiltonian for Resource Management**
   H_resource(s) = (VRAM_used / VRAM_total) * 10 + β * (T_gpu / T_max)
   
   Threshold: H_resource > 8.5 triggers OFFLOAD

Architecture:
=============
- Designed for 16-node mycelial QAOA solver
- Memory-efficient: O(n²) for n-qubit systems, max 20 qubits per subspace
- GPU-aware: monitors VRAM usage and thermal headroom
- Vectorized operations: uses NumPy for performance

Integration:
============
Connects to mycelial_qubo.py via:
- State vector analysis at each QAOA iteration
- Convergence detection for early stopping
- Resource-aware scaling based on GPU metrics
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple, Dict, List, Any

import numpy as np
from numpy.linalg import eigh, norm


# ==================================================================================
# Resource Monitoring
# ==================================================================================

@dataclass
class GPUMetrics:
    """Real-time GPU metrics for resource-bounded optimization."""
    vram_used_mib: int
    vram_total_mib: int
    vram_util_pct: float
    temp_celsius: float
    temp_headroom_pct: float
    timestamp: str
    
    def ising_hamiltonian(self, beta: float = 0.3, temp_max: float = 89.6) -> float:
        """Compute Ising Hamiltonian for resource state.
        
        H(s) = (VRAM_used/VRAM_total) * 10 + β * (T_gpu/T_max)
        
        Args:
            beta: Thermal penalty weight (default: 0.3)
            temp_max: Maximum safe temperature in °C (default: 89.6)
        
        Returns:
            H(s): Resource Hamiltonian value (threshold: 8.5 for OFFLOAD)
        """
        vram_term = (self.vram_used_mib / self.vram_total_mib) * 10.0
        thermal_term = beta * (self.temp_celsius / temp_max)
        return vram_term + thermal_term
    
    def as_dict(self) -> dict:
        return asdict(self)


def get_gpu_metrics() -> Optional[GPUMetrics]:
    """Query nvidia-smi for current GPU metrics."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            parts = [p.strip() for p in result.stdout.strip().split(",")]
            used_mib = int(parts[0])
            total_mib = int(parts[1])
            temp_c = float(parts[2])
            
            return GPUMetrics(
                vram_used_mib=used_mib,
                vram_total_mib=total_mib,
                vram_util_pct=100.0 * used_mib / total_mib,
                temp_celsius=temp_c,
                temp_headroom_pct=100.0 * (1.0 - temp_c / 89.6),
                timestamp=datetime.now(timezone.utc).isoformat()
            )
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass
    return None


# ==================================================================================
# Spectral Decomposition
# ==================================================================================

@dataclass
class EigenspaceDecomposition:
    """Spectral decomposition of QUBO Hamiltonian into orthogonal eigenspaces.
    
    Mathematical Foundation:
    ------------------------
    For QUBO matrix Q ∈ ℝ^{n×n}, compute eigendecomposition:
        Q = V Λ V^T
    
    where:
        V = [v₁, v₂, ..., vₙ] are orthonormal eigenvectors
        Λ = diag(λ₁, λ₂, ..., λₙ) are eigenvalues (sorted)
    
    Orthogonality: vᵢ · vⱼ = δᵢⱼ
    Completeness: Σᵢ |vᵢ⟩⟨vᵢ| = I
    """
    eigenvalues: np.ndarray  # Shape: (n,) sorted ascending
    eigenvectors: np.ndarray  # Shape: (n, n), columns are eigenvectors
    dimension: int
    spectral_gap: float  # λ₁ - λ₀ (ground-first excited gap)
    energy_scale: float  # λₘₐₓ - λₘᵢₙ
    orthogonality_error: float  # ||V^T V - I||_F (should be ~0)
    
    def project_to_eigenspace(self, state_vector: np.ndarray, 
                              k: int) -> Tuple[float, np.ndarray]:
        """Project state vector onto k-th eigenspace.
        
        α_k = ⟨φ_k|ψ⟩ = v_k^T · ψ
        
        Args:
            state_vector: Quantum state |ψ⟩ in computational basis
            k: Eigenspace index (0 = ground state)
        
        Returns:
            (coefficient, projected_state): (α_k, α_k|φ_k⟩)
        """
        eigenvector_k = self.eigenvectors[:, k]
        alpha_k = np.dot(eigenvector_k, state_vector)
        projected = alpha_k * eigenvector_k
        return float(alpha_k), projected
    
    def compute_expansion_coefficients(self, state_vector: np.ndarray) -> np.ndarray:
        """Compute full eigenspace expansion coefficients.
        
        |ψ⟩ = Σ_k α_k |φ_k⟩  where α_k = ⟨φ_k|ψ⟩
        
        Returns:
            α: Array of coefficients [α₀, α₁, ..., α_{n-1}]
        """
        # Normalize input state
        psi_norm = state_vector / (norm(state_vector) + 1e-12)
        # α = V^T · ψ (exploit orthonormality)
        coefficients = self.eigenvectors.T @ psi_norm
        return coefficients
    
    def effective_dimension(self, state_vector: np.ndarray, 
                           threshold: float = 0.01) -> int:
        """Compute effective dimensionality of state in eigenspace.
        
        D_eff = number of eigenvectors with |α_k|² > threshold
        
        Lower D_eff indicates state is localized in few eigenspaces
        (good for convergence). Higher D_eff indicates dispersion.
        """
        alphas = self.compute_expansion_coefficients(state_vector)
        populations = np.abs(alphas) ** 2
        return int(np.sum(populations > threshold))
    
    def as_dict(self) -> dict:
        """Serialize (eigenvalues only, eigenvectors too large)."""
        return {
            "dimension": self.dimension,
            "eigenvalues": self.eigenvalues.tolist(),
            "spectral_gap": self.spectral_gap,
            "energy_scale": self.energy_scale,
            "orthogonality_error": self.orthogonality_error
        }


def compute_eigenspace_decomposition(Q: np.ndarray, 
                                     verify_orthogonality: bool = True) -> EigenspaceDecomposition:
    """Compute spectral decomposition of QUBO matrix Q.
    
    Algorithm:
    ----------
    1. Symmetrize Q: Q_sym = (Q + Q^T) / 2
    2. Compute eigendecomposition: Q_sym = V Λ V^T
    3. Sort by eigenvalue (ascending)
    4. Verify orthonormality: ||V^T V - I||_F < ε
    
    Args:
        Q: QUBO matrix (n×n), may be upper-triangular
        verify_orthogonality: Check orthonormality of eigenvectors
    
    Returns:
        Eigenspace decomposition with sorted eigenvalues/vectors
    
    Complexity: O(n³) — suitable for n ≤ 100 (typical mycelial subspace: n=10-20)
    """
    n = Q.shape[0]
    
    # Symmetrize (QUBO matrices may be upper-triangular)
    Q_sym = (Q + Q.T) / 2.0
    
    # Compute eigendecomposition (sorted by eigenvalue)
    eigenvalues, eigenvectors = eigh(Q_sym)
    
    # Compute metrics
    spectral_gap = float(eigenvalues[1] - eigenvalues[0]) if n > 1 else 0.0
    energy_scale = float(eigenvalues[-1] - eigenvalues[0])
    
    # Verify orthonormality
    orthogonality_error = 0.0
    if verify_orthogonality:
        VtV = eigenvectors.T @ eigenvectors
        identity = np.eye(n)
        orthogonality_error = float(norm(VtV - identity, 'fro'))
    
    return EigenspaceDecomposition(
        eigenvalues=eigenvalues,
        eigenvectors=eigenvectors,
        dimension=n,
        spectral_gap=spectral_gap,
        energy_scale=energy_scale,
        orthogonality_error=orthogonality_error
    )


# ==================================================================================
# Waveform Equilibrium
# ==================================================================================

@dataclass
class WaveformState:
    """Quantum waveform state in eigenspace representation.
    
    Mathematical Model:
    -------------------
    |Ψ(t)⟩ = Σ_k α_k(t) e^(-iλ_k t) |φ_k⟩
    
    At equilibrium:
        d|Ψ⟩/dt = 0  in projection to low-energy eigenspace
    
    Convergence criterion:
        ||⟨H⟩_t - ⟨H⟩_{t-Δt}|| < ε  (energy stabilization)
    """
    expansion_coefficients: np.ndarray  # α_k for each eigenspace
    populations: np.ndarray  # |α_k|² (probability in each eigenspace)
    expected_energy: float  # ⟨H⟩ = Σ_k |α_k|² λ_k
    purity: float  # Tr(ρ²) where ρ = Σ_k |α_k|²|φ_k⟩⟨φ_k|
    effective_dimension: int  # Number of significantly populated eigenspaces
    timestamp: str
    
    def is_near_equilibrium(self, prev_state: 'WaveformState', 
                           epsilon: float = 1e-3) -> bool:
        """Check if waveform has reached equilibrium.
        
        Criterion: |⟨H⟩_t - ⟨H⟩_{t-1}| < ε
        """
        delta_energy = abs(self.expected_energy - prev_state.expected_energy)
        return delta_energy < epsilon
    
    def dominant_eigenspace(self) -> Tuple[int, float]:
        """Return index and population of most populated eigenspace."""
        k_max = int(np.argmax(self.populations))
        pop_max = float(self.populations[k_max])
        return k_max, pop_max
    
    def as_dict(self) -> dict:
        k_dominant, pop_dominant = self.dominant_eigenspace()
        return {
            "expected_energy": self.expected_energy,
            "purity": self.purity,
            "effective_dimension": self.effective_dimension,
            "dominant_eigenspace": k_dominant,
            "dominant_population": pop_dominant,
            "timestamp": self.timestamp
        }


def compute_waveform_state(state_vector: np.ndarray,
                          eigenspace: EigenspaceDecomposition,
                          population_threshold: float = 0.01) -> WaveformState:
    """Compute waveform state from quantum state vector.
    
    Algorithm:
    ----------
    1. Project state onto eigenspace basis: α = V^T ψ
    2. Compute populations: P_k = |α_k|²
    3. Compute expected energy: ⟨H⟩ = Σ_k P_k λ_k
    4. Compute purity: S = Σ_k P_k²
    5. Count effective dimensions: D_eff = |{k : P_k > threshold}|
    
    Args:
        state_vector: Quantum state |ψ⟩ in computational basis
        eigenspace: Precomputed eigenspace decomposition
        population_threshold: Minimum population to count in D_eff
    
    Returns:
        Waveform state with eigenspace statistics
    """
    # Compute expansion coefficients
    alphas = eigenspace.compute_expansion_coefficients(state_vector)
    
    # Compute populations (probability in each eigenspace)
    populations = np.abs(alphas) ** 2
    populations /= (np.sum(populations) + 1e-12)  # Normalize
    
    # Expected energy: ⟨H⟩ = Σ_k |α_k|² λ_k
    expected_energy = float(np.dot(populations, eigenspace.eigenvalues))
    
    # Purity: Tr(ρ²) = Σ_k P_k²
    purity = float(np.sum(populations ** 2))
    
    # Effective dimension
    eff_dim = int(np.sum(populations > population_threshold))
    
    return WaveformState(
        expansion_coefficients=alphas,
        populations=populations,
        expected_energy=expected_energy,
        purity=purity,
        effective_dimension=eff_dim,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


# ==================================================================================
# Convergence Analysis
# ==================================================================================

@dataclass
class ConvergenceMetrics:
    """Multi-dimensional convergence metrics for QAOA optimization.
    
    Tracks convergence across orthogonal performance dimensions:
    1. Energy convergence (primary objective)
    2. State fidelity convergence (eigenspace localization)
    3. Resource efficiency (VRAM utilization)
    4. Thermal efficiency (computations per degree C)
    """
    iteration: int
    energy: float
    energy_gradient: float  # d⟨H⟩/dt (should → 0 at equilibrium)
    purity: float
    effective_dimension: int
    vram_efficiency: float  # operations / MiB
    thermal_efficiency: float  # operations / °C
    converged: bool
    timestamp: str
    
    def as_dict(self) -> dict:
        return asdict(self)


class ConvergenceTracker:
    """Track convergence across multiple QAOA iterations.
    
    Equilibrium Detection:
    ----------------------
    Waveform equilibrium reached when:
    1. Energy gradient: |dE/dt| < ε_energy
    2. Purity stable: |dS/dt| < ε_purity
    3. State localized: D_eff ≤ threshold
    
    Early stopping prevents wasted GPU cycles.
    """
    
    def __init__(self, 
                 energy_epsilon: float = 1e-3,
                 purity_epsilon: float = 1e-4,
                 max_effective_dim: int = 5):
        self.energy_epsilon = energy_epsilon
        self.purity_epsilon = purity_epsilon
        self.max_effective_dim = max_effective_dim
        
        self.history: List[ConvergenceMetrics] = []
        self.waveform_history: List[WaveformState] = []
    
    def record_iteration(self,
                        iteration: int,
                        waveform: WaveformState,
                        gpu_metrics: Optional[GPUMetrics] = None,
                        operations_count: int = 1) -> ConvergenceMetrics:
        """Record convergence metrics for current iteration."""
        
        # Compute energy gradient (finite difference)
        energy_gradient = 0.0
        if len(self.waveform_history) > 0:
            prev = self.waveform_history[-1]
            energy_gradient = waveform.expected_energy - prev.expected_energy
        
        # Compute resource efficiencies
        vram_efficiency = 0.0
        thermal_efficiency = 0.0
        if gpu_metrics is not None:
            vram_efficiency = operations_count / max(gpu_metrics.vram_used_mib, 1)
            thermal_efficiency = operations_count / max(gpu_metrics.temp_celsius, 1.0)
        
        # Check convergence
        converged = self._check_convergence(waveform, energy_gradient)
        
        metrics = ConvergenceMetrics(
            iteration=iteration,
            energy=waveform.expected_energy,
            energy_gradient=energy_gradient,
            purity=waveform.purity,
            effective_dimension=waveform.effective_dimension,
            vram_efficiency=vram_efficiency,
            thermal_efficiency=thermal_efficiency,
            converged=converged,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        self.history.append(metrics)
        self.waveform_history.append(waveform)
        
        return metrics
    
    def _check_convergence(self, waveform: WaveformState, 
                          energy_grad: float) -> bool:
        """Check if equilibrium criteria are met."""
        # Need at least 2 iterations for gradient
        if len(self.waveform_history) < 2:
            return False
        
        # Energy stabilization
        energy_converged = abs(energy_grad) < self.energy_epsilon
        
        # Purity stabilization
        prev_purity = self.waveform_history[-1].purity
        purity_converged = abs(waveform.purity - prev_purity) < self.purity_epsilon
        
        # Eigenspace localization
        dimension_converged = waveform.effective_dimension <= self.max_effective_dim
        
        return energy_converged and purity_converged and dimension_converged
    
    def get_summary(self) -> dict:
        """Generate convergence summary report."""
        if not self.history:
            return {"status": "no_data"}
        
        final = self.history[-1]
        initial = self.history[0]
        
        return {
            "total_iterations": len(self.history),
            "converged": final.converged,
            "initial_energy": initial.energy,
            "final_energy": final.energy,
            "energy_improvement": initial.energy - final.energy,
            "final_purity": final.purity,
            "final_effective_dim": final.effective_dimension,
            "avg_vram_efficiency": float(np.mean([m.vram_efficiency for m in self.history if m.vram_efficiency > 0])),
            "avg_thermal_efficiency": float(np.mean([m.thermal_efficiency for m in self.history if m.thermal_efficiency > 0]))
        }


# ==================================================================================
# Main API Functions
# ==================================================================================

def analyze_qaoa_iteration(state_vector: np.ndarray,
                           Q_matrix: np.ndarray,
                           iteration: int,
                           tracker: Optional[ConvergenceTracker] = None) -> Dict[str, Any]:
    """Complete waveform equilibrium analysis for single QAOA iteration.
    
    This is the main API function for integration with mycelial_qubo.py
    
    Workflow:
    ---------
    1. Compute eigenspace decomposition of Q matrix
    2. Project state vector onto eigenspace basis
    3. Compute waveform equilibrium metrics
    4. Check convergence criteria
    5. Monitor GPU resources
    
    Args:
        state_vector: Output state from QAOA circuit |ψ⟩
        Q_matrix: QUBO matrix for current subspace
        iteration: Current outer-loop iteration number
        tracker: Optional convergence tracker for multi-iteration analysis
    
    Returns:
        Dictionary with:
        - eigenspace: Spectral decomposition metrics
        - waveform: Waveform state in eigenspace basis
        - convergence: Convergence metrics (if tracker provided)
        - gpu: GPU metrics (VRAM, temperature)
        - recommendation: Action recommendation (CONTINUE/EARLY_STOP/OFFLOAD)
    """
    # Step 1: Eigenspace decomposition
    eigenspace = compute_eigenspace_decomposition(Q_matrix)
    
    # Step 2: Waveform state analysis
    waveform = compute_waveform_state(state_vector, eigenspace)
    
    # Step 3: GPU metrics
    gpu_metrics = get_gpu_metrics()
    
    # Step 4: Convergence tracking
    convergence_metrics = None
    if tracker is not None:
        convergence_metrics = tracker.record_iteration(
            iteration=iteration,
            waveform=waveform,
            gpu_metrics=gpu_metrics
        )
    
    # Step 5: Generate recommendation
    recommendation = _generate_recommendation(
        waveform=waveform,
        convergence=convergence_metrics,
        gpu=gpu_metrics
    )
    
    return {
        "iteration": iteration,
        "eigenspace": eigenspace.as_dict(),
        "waveform": waveform.as_dict(),
        "convergence": convergence_metrics.as_dict() if convergence_metrics else None,
        "gpu": gpu_metrics.as_dict() if gpu_metrics else None,
        "recommendation": recommendation,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def _generate_recommendation(waveform: WaveformState,
                            convergence: Optional[ConvergenceMetrics],
                            gpu: Optional[GPUMetrics]) -> Dict[str, Any]:
    """Generate action recommendation based on equilibrium analysis."""
    
    # Check for convergence (early stopping opportunity)
    if convergence is not None and convergence.converged:
        return {
            "action": "EARLY_STOP",
            "reason": "waveform_equilibrium_reached",
            "details": {
                "energy_gradient": convergence.energy_gradient,
                "effective_dimension": waveform.effective_dimension
            }
        }
    
    # Check for resource overflow (OFFLOAD trigger)
    if gpu is not None:
        H_resource = gpu.ising_hamiltonian()
        if H_resource > 8.5:
            return {
                "action": "OFFLOAD",
                "reason": "resource_hamiltonian_overflow",
                "details": {
                    "H_resource": H_resource,
                    "vram_util_pct": gpu.vram_util_pct,
                    "temp_celsius": gpu.temp_celsius
                }
            }
    
    # Default: continue optimization
    return {
        "action": "CONTINUE",
        "reason": "optimization_in_progress",
        "details": {
            "expected_energy": waveform.expected_energy,
            "purity": waveform.purity
        }
    }


# ==================================================================================
# Visualization Helpers (for analysis notebooks)
# ==================================================================================

def export_convergence_trace(tracker: ConvergenceTracker, 
                            output_path: Path) -> None:
    """Export convergence history to JSON for visualization."""
    data = {
        "summary": tracker.get_summary(),
        "iterations": [m.as_dict() for m in tracker.history],
        "export_time": datetime.now(timezone.utc).isoformat()
    }
    output_path.write_text(json.dumps(data, indent=2))


# ==================================================================================
# Testing Interface
# ==================================================================================

def run_synthetic_test(n_qubits: int = 10, n_iterations: int = 5) -> Dict[str, Any]:
    """Run synthetic test with random QUBO matrix and state vectors.
    
    Useful for validation without full CUDA-Q execution.
    """
    print(f"Running synthetic test: {n_qubits} qubits, {n_iterations} iterations")
    
    # Generate random QUBO matrix
    Q = np.random.randn(n_qubits, n_qubits)
    Q = (Q + Q.T) / 2.0  # Symmetrize
    
    # Initialize tracker
    tracker = ConvergenceTracker()
    
    # Simulate QAOA iterations with converging state vectors
    results = []
    for i in range(n_iterations):
        # Generate state vector that converges to ground eigenspace
        state_vector = np.random.randn(n_qubits)
        # Add bias toward ground state
        state_vector[0] += (i + 1) * 0.5
        state_vector /= norm(state_vector)
        
        result = analyze_qaoa_iteration(
            state_vector=state_vector,
            Q_matrix=Q,
            iteration=i,
            tracker=tracker
        )
        results.append(result)
        
        print(f"  Iteration {i}: E={result['waveform']['expected_energy']:.4f}, "
              f"D_eff={result['waveform']['effective_dimension']}, "
              f"Action={result['recommendation']['action']}")
    
    summary = tracker.get_summary()
    print(f"\nConvergence Summary:")
    print(f"  Final energy: {summary['final_energy']:.4f}")
    print(f"  Energy improvement: {summary['energy_improvement']:.4f}")
    print(f"  Converged: {summary['converged']}")
    
    return {
        "summary": summary,
        "iterations": results
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        run_synthetic_test()
    else:
        print(__doc__)
        print("\nRun with 'test' argument to execute synthetic validation:")
        print("  python waveform_equilibrium.py test")
