# MARU MCP Runtime - Production Deployment Guide

**Envelope Version:** 0.3.0  
**Hardware:** GTX 1650 4GB VRAM Substrate  
**Architecture:** Interleaved JAX/CUDA-Q Execution with Zero OOM Tolerance

---

## Architecture Overview

The MARU (Memory Allocation & Resource Utilization) runtime provides production-grade VRAM management for constrained GPU environments. It enforces strict memory partitioning between JAX-based workloads (hyperNEAT, quantum memory) and CUDA-Q multilane electron state computations.

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    GTX 1650 4GB VRAM                        │
├─────────────────────────────────┬───────────────────────────┤
│  JAX / hyperNEAT / qmem         │  CUDA-Q Multilane         │
│  45% (1800MB ceiling)           │  55% (2200MB ceiling)     │
│  XLA_PYTHON_CLIENT_MEM=0.45     │  4 lanes + interleaving   │
└─────────────────────────────────┴───────────────────────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │  Interleaved Bus       │
            │  Yield/Throttle Logic  │
            └────────────────────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │  VRAM Guardian         │
            │  Enforce Ceilings      │
            │  NOX Reframe on Breach │
            └────────────────────────┘
```

### Components

| Component | Purpose | Port | Log Path |
|-----------|---------|------|----------|
| **maru_runtime_launch.sh** | Podman container orchestration | - | stdout |
| **interleaved_bus_monitor.py** | Yield/throttle coordination | 9090 | /var/maru/bus_state.log |
| **vram_guardian.py** | VRAM ceiling enforcement | - | /var/maru/vram_violations.log |
| **nox_engine_state.json** | NOX engine state & reframe | - | /var/maru/nox_state.json |

---

## VRAM Partitioning Rationale

### Why 45% JAX / 55% CUDA-Q?

1. **JAX Overhead**: JAX/XLA requires memory for:
   - Compiled kernels (persistent)
   - Intermediate buffers (temporary)
   - HyperNEAT graph structures (dynamic)
   - Quantum memory state (qmem.lock)

2. **CUDA-Q Requirements**: Multilane electron state potentiation needs:
   - 4 concurrent execution lanes
   - Position/momentum wavefunction buffers
   - Entanglement tracking matrices

3. **Safety Buffer**: ~96MB reserved for system overhead

### Measured Utilization Patterns

- **JAX Baseline**: ~400MB (no active computation)
- **HyperNEAT Pulsing**: 800-1200MB (peaks during fitness evaluation)
- **qmem Active**: 1400-1700MB (quantum state maintenance)
- **CUDA-Q Idle**: ~200MB (driver overhead)
- **CUDA-Q 4-Lane Active**: 1800-2100MB (multilane execution)

**Total Peak**: ~3900MB (safely under 4096MB with buffers)

---

## Launch Procedure

### Prerequisites

```bash
# Install Podman (if not already present)
sudo apt-get update && sudo apt-get install -y podman

# Verify NVIDIA GPU access
nvidia-smi

# Ensure Podman has GPU support
sudo apt-get install -y nvidia-container-toolkit
podman info | grep -i nvidia
```

### Launch

```bash
cd ~/diamondnode-unified-inference/deployment
chmod +x maru_runtime_launch.sh
./maru_runtime_launch.sh
```

### Expected Output

```
[MARU] MARU MCP Runtime Launch (envelope: 0.3.0)
[MARU] Checking prerequisites (envelope: 0.3.0)...
[MARU] ✓ Prerequisites validated
[MARU] Setting up MARU state directory...
[MARU] ✓ Initialized NOX engine state
[MARU] ✓ MARU state directory ready: /var/lib/maru_state
[MARU] Launching MARU runtime container...
[MARU]   JAX VRAM: 0.45 (45%)
[MARU]   CUDA-Q VRAM: 0.55 (55%)
[MARU]   Interleaved Bus: ENABLED
[MARU]   Guardian Mode: ENABLED
[MARU] ✓ Container launched: maru-runtime
[MARU] Waiting for health check...
[MARU] ✓ Service healthy
[MARU] ═══════════════════════════════════════════════════
[MARU] MARU MCP Runtime - ACTIVE
[MARU] ═══════════════════════════════════════════════════
```

### Verify Deployment

```bash
# Check container status
podman ps | grep maru-runtime

# Check health endpoint
curl http://localhost:8000/health

# Check interleaved bus metrics
curl http://localhost:9090/metrics

# Monitor logs
podman logs -f maru-runtime
```

---

## Interleaved Bus Protocol

The interleaved bus prevents VRAM conflicts by coordinating JAX and CUDA-Q execution.

### Yield Rules

**Rule 1: CUDA-Q yields to JAX priority workloads**

```
IF (hyperNEAT.pulsing OR qmem.active) AND cuda_q.state == RUNNING:
    cuda_q.yield_execution()
    # Signal written to: /var/maru/cuda_q_yield.signal
```

**Rule 2: JAX throttles during CUDA-Q active periods**

```
IF cuda_q.active AND jax.memory_fraction > 0.42:
    jax.throttle()
    # Signal written to: /var/maru/jax_throttle.signal
```

### Bus State Monitoring

```bash
# Real-time bus metrics
curl http://localhost:9090/metrics | jq

# Example output:
{
  "envelope_version": "0.3.0",
  "timestamp": "2025-01-15T12:34:56Z",
  "jax": {
    "memory_fraction": 0.38,
    "memory_mb": 684.5,
    "active": true,
    "hyperneat_pulsing": false,
    "qmem_active": false
  },
  "cuda_q": {
    "active": true,
    "kernel_state": "RUNNING",
    "lanes": [true, true, false, false]
  },
  "bus_stats": {
    "yield_count": 42,
    "throttle_count": 18,
    "conflict_count": 3
  }
}
```

### Bus State Log

```bash
tail -f /var/lib/maru_state/bus_state.log

# Example entries:
[2025-01-15 12:34:56] [BUS] INFO: ✓ CUDA-Q yielded (hyperNEAT: True, qmem: False)
[2025-01-15 12:35:12] [BUS] WARNING: ⚠ JAX throttled (memory: 43.2%, threshold: 42.0%)
[2025-01-15 12:35:45] [BUS] WARNING: ⚠ Potential bus conflict (JAX: 41.5%, CUDA-Q: RUNNING)
```

---

## VRAM Guardian

The VRAM Guardian enforces hard ceilings with zero OOM tolerance.

### Enforcement Policy

1. **Poll NVIDIA-SMI every 5 seconds**
2. **Detect violations** (process exceeds ceiling)
3. **Grace period** (5 seconds for voluntary reduction)
4. **Terminate** (SIGTERM → SIGKILL)
5. **Log violation** (timestamp, PID, overage)
6. **NOX reframe** (3+ violations in 5 minutes)

### Ceiling Enforcement

| Category | Ceiling | XLA Env Var |
|----------|---------|-------------|
| JAX | 1800MB | `XLA_PYTHON_CLIENT_MEM_FRACTION=0.45` |
| CUDA-Q | 2200MB | (implicit, 55% allocation) |

### Grace Period Example

```
[2025-01-15 12:40:23] [GUARDIAN] WARNING: ⚠ VRAM VIOLATION: JAX process [PID 1234] python3 using 1950MB (ceiling: 1800MB, overage: 150MB)
[2025-01-15 12:40:23] [GUARDIAN] WARNING: Grace period: 5s for PID 1234 to reduce VRAM usage
[2025-01-15 12:40:28] [GUARDIAN] ERROR: 🔥 TERMINATING process [PID 1234] python3 for VRAM violation
[2025-01-15 12:40:28] [GUARDIAN] INFO: ✓ Process 1234 terminated
```

### NOX Reframe Integration

When violations exceed threshold (3 in 5 minutes):

```
[2025-01-15 12:45:00] [GUARDIAN] CRITICAL: 🚨 REFRAME THRESHOLD EXCEEDED: 3 violations in 300s window
[2025-01-15 12:45:00] [GUARDIAN] CRITICAL: ⚡ Triggering NOX engine REFRAME
[2025-01-15 12:45:00] [GUARDIAN] INFO: ✓ NOX reframe event recorded to /var/lib/maru_state/nox_state.json
```

Reframe event written to `nox_state.json`:

```json
{
  "reframe_events": [
    {
      "timestamp": "2025-01-15T12:45:00Z",
      "trigger": "vram_violations",
      "violation_count": 3,
      "envelope_version": "0.3.0"
    }
  ]
}
```

---

## Troubleshooting OOM Scenarios

### Scenario 1: JAX OOM Despite 45% Allocation

**Symptoms:**
```
RuntimeError: RESOURCE_EXHAUSTED: Out of memory
```

**Diagnosis:**
```bash
# Check actual JAX memory usage
curl http://localhost:9090/metrics | jq '.jax.memory_mb'

# Check violations log
tail /var/lib/maru_state/vram_violations.log
```

**Resolution:**
1. Reduce batch size in JAX workload
2. Enable gradient checkpointing (if applicable)
3. Consider reducing `XLA_PYTHON_CLIENT_MEM_FRACTION` to 0.40

### Scenario 2: CUDA-Q Kernel Starvation

**Symptoms:**
- CUDA-Q kernels never execute
- `bus_stats.yield_count` constantly increasing

**Diagnosis:**
```bash
# Check bus state
curl http://localhost:9090/metrics | jq '.cuda_q.kernel_state'

# Check if hyperNEAT/qmem always active
curl http://localhost:9090/metrics | jq '.jax | {hyperneat_pulsing, qmem_active}'
```

**Resolution:**
1. Reduce hyperNEAT pulse frequency
2. Implement time-sliced execution windows
3. Adjust yield priority in `nox_engine_state.json`

### Scenario 3: Frequent VRAM Violations

**Symptoms:**
- Guardian terminates processes repeatedly
- NOX reframe triggered multiple times

**Diagnosis:**
```bash
# Count violations
grep "VRAM VIOLATION" /var/lib/maru_state/vram_violations.log | wc -l

# Identify offending processes
grep "TERMINATING" /var/lib/maru_state/vram_violations.log
```

**Resolution:**
1. Profile offending workload memory usage
2. Reduce parallelism (fewer CUDA-Q lanes)
3. Implement explicit memory cleanup (JAX: `jax.clear_caches()`)

### Scenario 4: Bus Conflicts

**Symptoms:**
- `bus_stats.conflict_count` increasing
- Both JAX and CUDA-Q active simultaneously at high load

**Diagnosis:**
```bash
# Monitor bus conflicts
watch -n 1 'curl -s http://localhost:9090/metrics | jq .bus_stats'
```

**Resolution:**
1. Lower JAX throttle threshold (currently 0.42)
2. Implement exclusive execution windows
3. Add epsilon hysteresis to prevent oscillation

---

## NOX Engine Integration Points

### Crystalline Threshold

The NOX engine monitors system state via Hamiltonian convergence:

```
H(s) = (VRAM_Used / VRAM_Total) * 10
```

When `H(s) < crystalline_threshold` for `min_hold_cycles`, the system enters crystalline state (stable, low-entropy).

### Epsilon Hysteresis

Prevents oscillation at VRAM boundaries:

```json
{
  "epsilon_hysteresis": {
    "enabled": true,
    "gamma_buffer": 0.05,
    "min_hold_cycles": 3
  }
}
```

**Effect:** System must stay below `crystalline_threshold - gamma_buffer` for 3 cycles before declaring crystalline state.

### Structural Lock

When `structural_lock: true`, NOX engine freezes adaptations. Use this to stabilize a working configuration.

```bash
# Enable structural lock
jq '.nox_engine.structural_lock = true' /var/lib/maru_state/nox_state.json > /tmp/updated.json
mv /tmp/updated.json /var/lib/maru_state/nox_state.json
```

### Reframe Events

Reframe events signal the NOX engine to reconsider its strategy. Triggered by:
- VRAM violations exceeding threshold
- Manual trigger via `nox_state.json` update
- External system signals

---

## Envelope Version: 0.3.0

All components share envelope version `0.3.0` for compatibility verification.

### Version Components

```
0.3.0
│ │ │
│ │ └─ Patch: Bug fixes, minor tweaks
│ └─── Minor: New features, backward-compatible
└───── Major: Breaking changes, protocol updates
```

### Proof Schema

The MARU runtime embeds proof schemas for formal verification:

#### Kobayashi Maru Proof

**Type:** Crystalline Convergence  
**Invariant:** System achieves stable low-entropy state under constraints

```
∀ cycles ∈ [t, t+min_hold_cycles]:
  H(s_cycles) < crystalline_threshold - gamma_buffer
  ⇒ crystalline_state = TRUE
```

#### VRAM Partition Proof

**Type:** Hamiltonian Balance  
**Invariant:** Total VRAM usage never exceeds hardware limit

```
∀ t: sum(VRAM_JAX(t), VRAM_CUDA_Q(t)) ≤ 4096 - buffer_mb
```

**Enforcement:** VRAM Guardian with grace period + termination

---

## Configuration Files

### Environment Variables

Set in container launch script:

| Variable | Value | Purpose |
|----------|-------|---------|
| `XLA_PYTHON_CLIENT_MEM_FRACTION` | 0.45 | JAX VRAM allocation |
| `CUDA_VISIBLE_DEVICES` | 0 | GPU device selection |
| `MARU_GUARDIAN_MODE` | enabled | Enable VRAM guardian |
| `NOX_ENGINE_STATE` | /var/maru/nox_state.json | NOX state file path |
| `CUDA_Q_LANES` | 4 | Multilane count |
| `INTERLEAVED_BUS` | true | Enable bus coordination |
| `JAX_VRAM_CEILING_MB` | 1800 | JAX ceiling (MB) |
| `CUDA_Q_VRAM_CEILING_MB` | 2200 | CUDA-Q ceiling (MB) |

### Volume Mounts

```bash
-v ~/diamondnode-unified-inference/src:/app/src:ro
-v ~/diamondnode-unified-inference/config:/app/config:ro
-v /var/lib/maru_state:/var/maru:rw
```

### Health Check

```bash
--health-cmd="curl -f http://localhost:8000/health || exit 1"
--health-interval=30s
--health-timeout=10s
--health-retries=3
--health-start-period=40s
```

---

## Production Operations

### Start Runtime

```bash
cd ~/diamondnode-unified-inference/deployment
./maru_runtime_launch.sh
```

### Stop Runtime

```bash
podman stop maru-runtime
```

### Restart Runtime

```bash
podman restart maru-runtime
```

### View Logs

```bash
# Container logs
podman logs -f maru-runtime

# Bus state log
tail -f /var/lib/maru_state/bus_state.log

# VRAM violations log
tail -f /var/lib/maru_state/vram_violations.log
```

### Monitor Metrics

```bash
# Bus metrics
watch -n 1 'curl -s http://localhost:9090/metrics | jq'

# NVIDIA GPU stats
watch -n 1 nvidia-smi
```

### Shell Access

```bash
podman exec -it maru-runtime bash
```

### Update NOX State

```bash
# Edit state file
vim /var/lib/maru_state/nox_state.json

# Restart required for changes to take effect
podman restart maru-runtime
```

---

## Performance Tuning

### Reduce JAX Memory Pressure

```bash
# Lower JAX allocation to 40%
export XLA_PYTHON_CLIENT_MEM_FRACTION=0.40

# Re-launch runtime
./maru_runtime_launch.sh
```

### Reduce CUDA-Q Lanes

```bash
# Edit launch script: CUDA_Q_LANES=2
vim maru_runtime_launch.sh

# Re-launch
./maru_runtime_launch.sh
```

### Adjust Throttle Threshold

Edit `interleaved_bus_monitor.py`:

```python
JAX_MEMORY_THROTTLE_THRESHOLD = 0.38  # Lower = more aggressive throttling
```

### Increase Grace Period

Edit `vram_guardian.py`:

```python
GRACE_PERIOD_SEC = 10.0  # Give processes more time to reduce VRAM
```

---

## Appendix: File Locations

| File | Path |
|------|------|
| Launch Script | `~/diamondnode-unified-inference/deployment/maru_runtime_launch.sh` |
| Bus Monitor | `~/diamondnode-unified-inference/deployment/interleaved_bus_monitor.py` |
| VRAM Guardian | `~/diamondnode-unified-inference/deployment/vram_guardian.py` |
| NOX State Template | `~/diamondnode-unified-inference/deployment/nox_engine_state.json` |
| NOX State (Runtime) | `/var/lib/maru_state/nox_state.json` |
| Bus Log | `/var/lib/maru_state/bus_state.log` |
| Violations Log | `/var/lib/maru_state/vram_violations.log` |

---

## Support

For issues or questions:

1. Check logs: `podman logs maru-runtime`
2. Verify metrics: `curl http://localhost:9090/metrics`
3. Review state: `cat /var/lib/maru_state/nox_state.json`
4. Check GPU: `nvidia-smi`

**Envelope Version:** 0.3.0  
**Hardware Target:** GTX 1650 4GB VRAM  
**Zero OOM Tolerance:** Enforced

---

*"The Kobayashi Maru is not a test of skill, but of character."*
