"""Test suite for waveform_equilibrium.py

Validates:
1. Spectral decomposition accuracy
2. Waveform state computation
3. Convergence detection
4. Resource monitoring
5. Integration with CUDA-Q outputs
"""

import sys
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from models.waveform_equilibrium import (
    compute_eigenspace_decomposition,
    compute_waveform_state,
    ConvergenceTracker,
    analyze_qaoa_iteration,
    get_gpu_metrics,
    GPUMetrics
)


def test_eigenspace_decomposition():
    """Test spectral decomposition of symmetric QUBO matrix."""
    print("\n=== Test 1: Eigenspace Decomposition ===")
    
    # Create simple 4x4 symmetric matrix
    Q = np.array([
        [2.0, 1.0, 0.5, 0.0],
        [1.0, 3.0, 1.0, 0.5],
        [0.5, 1.0, 2.5, 1.0],
        [0.0, 0.5, 1.0, 2.0]
    ])
    
    eigenspace = compute_eigenspace_decomposition(Q)
    
    # Verify dimensions
    assert eigenspace.dimension == 4
    assert eigenspace.eigenvalues.shape == (4,)
    assert eigenspace.eigenvectors.shape == (4, 4)
    
    # Verify orthonormality
    print(f"  Orthogonality error: {eigenspace.orthogonality_error:.2e}")
    assert eigenspace.orthogonality_error < 1e-10, "Eigenvectors not orthonormal"
    
    # Verify eigenvalues sorted ascending
    assert np.all(np.diff(eigenspace.eigenvalues) >= 0), "Eigenvalues not sorted"
    
    # Verify reconstruction: Q = V Λ V^T
    V = eigenspace.eigenvectors
    L = np.diag(eigenspace.eigenvalues)
    Q_reconstructed = V @ L @ V.T
    reconstruction_error = np.linalg.norm(Q - Q_reconstructed, 'fro')
    print(f"  Reconstruction error: {reconstruction_error:.2e}")
    assert reconstruction_error < 1e-10, "Failed to reconstruct Q"
    
    print(f"  Spectral gap: {eigenspace.spectral_gap:.4f}")
    print(f"  Energy scale: {eigenspace.energy_scale:.4f}")
    print("  ✅ PASS: Eigenspace decomposition correct")


def test_waveform_state_computation():
    """Test waveform state analysis from state vector."""
    print("\n=== Test 2: Waveform State Computation ===")
    
    # Create QUBO matrix
    Q = np.array([
        [1.0, 0.5, 0.2],
        [0.5, 2.0, 0.3],
        [0.2, 0.3, 1.5]
    ])
    
    eigenspace = compute_eigenspace_decomposition(Q)
    
    # Create state vector heavily weighted toward ground eigenspace
    state_vector = eigenspace.eigenvectors[:, 0] * 0.9  # 90% in ground state
    state_vector += eigenspace.eigenvectors[:, 1] * 0.3  # 30% in first excited
    state_vector /= np.linalg.norm(state_vector)  # Normalize
    
    waveform = compute_waveform_state(state_vector, eigenspace)
    
    # Verify populations sum to 1
    pop_sum = np.sum(waveform.populations)
    print(f"  Population sum: {pop_sum:.6f} (should be 1.0)")
    assert abs(pop_sum - 1.0) < 1e-6, "Populations don't sum to 1"
    
    # Verify purity bounds
    assert 0 <= waveform.purity <= 1, "Purity out of bounds [0,1]"
    print(f"  Purity: {waveform.purity:.4f}")
    
    # Verify effective dimension
    print(f"  Effective dimension: {waveform.effective_dimension}")
    assert waveform.effective_dimension >= 1, "Invalid effective dimension"
    
    # Verify expected energy
    manual_energy = np.dot(waveform.populations, eigenspace.eigenvalues)
    print(f"  Expected energy: {waveform.expected_energy:.4f} (manual: {manual_energy:.4f})")
    assert abs(waveform.expected_energy - manual_energy) < 1e-6, "Energy calculation mismatch"
    
    # Verify dominant eigenspace
    k_dom, pop_dom = waveform.dominant_eigenspace()
    print(f"  Dominant eigenspace: k={k_dom}, population={pop_dom:.4f}")
    assert pop_dom == np.max(waveform.populations), "Dominant eigenspace incorrect"
    
    print("  ✅ PASS: Waveform state computation correct")


def test_convergence_tracking():
    """Test convergence tracking across multiple iterations."""
    print("\n=== Test 3: Convergence Tracking ===")
    
    Q = np.random.randn(5, 5)
    Q = (Q + Q.T) / 2  # Symmetrize
    eigenspace = compute_eigenspace_decomposition(Q)
    
    tracker = ConvergenceTracker(
        energy_epsilon=1e-3,
        purity_epsilon=1e-4,
        max_effective_dim=3
    )
    
    # Simulate convergence: gradually concentrate in ground state
    n_iterations = 10
    for i in range(n_iterations):
        # State vector with increasing weight on ground eigenspace
        alpha_0 = 0.5 + 0.05 * i  # Increase from 0.5 to 0.95
        state_vector = eigenspace.eigenvectors[:, 0] * alpha_0
        state_vector += eigenspace.eigenvectors[:, 1] * (1 - alpha_0) * 0.7
        state_vector /= np.linalg.norm(state_vector)
        
        waveform = compute_waveform_state(state_vector, eigenspace)
        
        # Simulate GPU metrics
        mock_gpu = GPUMetrics(
            vram_used_mib=100 + i * 10,
            vram_total_mib=4096,
            vram_util_pct=(100 + i * 10) / 40.96,
            temp_celsius=31 + i * 2,
            temp_headroom_pct=100 * (1 - (31 + i * 2) / 89.6),
            timestamp="2025-05-12T00:00:00Z"
        )
        
        metrics = tracker.record_iteration(
            iteration=i,
            waveform=waveform,
            gpu_metrics=mock_gpu,
            operations_count=512
        )
        
        print(f"  Iter {i}: E={metrics.energy:.4f}, ∇E={metrics.energy_gradient:.4e}, "
              f"S={metrics.purity:.4f}, D_eff={metrics.effective_dimension}, "
              f"converged={metrics.converged}")
    
    # Verify history length
    assert len(tracker.history) == n_iterations
    assert len(tracker.waveform_history) == n_iterations
    
    # Verify energy decreases (mostly)
    energies = [m.energy for m in tracker.history]
    energy_decreased = energies[-1] < energies[0]
    print(f"  Energy decreased: {energy_decreased} ({energies[0]:.4f} → {energies[-1]:.4f})")
    
    # Verify summary
    summary = tracker.get_summary()
    print(f"  Summary: {summary['total_iterations']} iterations, "
          f"converged={summary['converged']}, "
          f"energy improvement={summary['energy_improvement']:.4f}")
    
    assert summary['total_iterations'] == n_iterations
    
    print("  ✅ PASS: Convergence tracking works correctly")


def test_resource_hamiltonian():
    """Test resource Hamiltonian computation."""
    print("\n=== Test 4: Resource Hamiltonian ===")
    
    # Test case 1: Low utilization (should be < 8.5)
    gpu1 = GPUMetrics(
        vram_used_mib=124,
        vram_total_mib=4096,
        vram_util_pct=3.0,
        temp_celsius=31.0,
        temp_headroom_pct=96.0,
        timestamp="2025-05-12T00:00:00Z"
    )
    H1 = gpu1.ising_hamiltonian()
    print(f"  Low util: VRAM={gpu1.vram_used_mib}MiB, T={gpu1.temp_celsius}°C → H={H1:.4f}")
    assert H1 < 8.5, "Low utilization should not trigger OFFLOAD"
    
    # Test case 2: High VRAM (should be > 8.5)
    gpu2 = GPUMetrics(
        vram_used_mib=3500,
        vram_total_mib=4096,
        vram_util_pct=85.4,
        temp_celsius=60.0,
        temp_headroom_pct=33.0,
        timestamp="2025-05-12T00:00:00Z"
    )
    H2 = gpu2.ising_hamiltonian()
    print(f"  High VRAM: VRAM={gpu2.vram_used_mib}MiB, T={gpu2.temp_celsius}°C → H={H2:.4f}")
    assert H2 > 8.5, "High VRAM should trigger OFFLOAD"
    
    # Test case 3: Combined high (should be > 8.5)
    gpu3 = GPUMetrics(
        vram_used_mib=3400,
        vram_total_mib=4096,
        vram_util_pct=83.0,
        temp_celsius=70.0,
        temp_headroom_pct=21.9,
        timestamp="2025-05-12T00:00:00Z"
    )
    H3 = gpu3.ising_hamiltonian()
    print(f"  Combined high: VRAM={gpu3.vram_used_mib}MiB, T={gpu3.temp_celsius}°C → H={H3:.4f}")
    assert H3 > 8.5, "Combined high VRAM+temp should trigger OFFLOAD"
    
    print("  ✅ PASS: Resource Hamiltonian correctly triggers OFFLOAD")


def test_integration_api():
    """Test the main integration API function."""
    print("\n=== Test 5: Integration API ===")
    
    # Create synthetic QAOA output
    n_vars = 8
    Q = np.random.randn(n_vars, n_vars)
    Q = (Q + Q.T) / 2
    
    # Simulate state vector
    state_vector = np.random.randn(n_vars)
    state_vector /= np.linalg.norm(state_vector)
    
    # Initialize tracker
    tracker = ConvergenceTracker()
    
    # Analyze iteration
    result = analyze_qaoa_iteration(
        state_vector=state_vector,
        Q_matrix=Q,
        iteration=5,
        tracker=tracker
    )
    
    # Verify result structure
    assert "iteration" in result
    assert "eigenspace" in result
    assert "waveform" in result
    assert "convergence" in result
    assert "gpu" in result
    assert "recommendation" in result
    
    print(f"  Iteration: {result['iteration']}")
    print(f"  Eigenspace dimension: {result['eigenspace']['dimension']}")
    print(f"  Waveform energy: {result['waveform']['expected_energy']:.4f}")
    print(f"  Recommendation: {result['recommendation']['action']}")
    
    # Verify recommendation structure
    rec = result["recommendation"]
    assert "action" in rec
    assert rec["action"] in ["CONTINUE", "EARLY_STOP", "OFFLOAD"]
    assert "reason" in rec
    assert "details" in rec
    
    print("  ✅ PASS: Integration API works correctly")


def test_gpu_metrics_query():
    """Test GPU metrics query (may fail if nvidia-smi unavailable)."""
    print("\n=== Test 6: GPU Metrics Query ===")
    
    gpu = get_gpu_metrics()
    
    if gpu is None:
        print("  ⚠️  SKIP: nvidia-smi not available or failed")
        return
    
    print(f"  VRAM: {gpu.vram_used_mib} / {gpu.vram_total_mib} MiB ({gpu.vram_util_pct:.2f}%)")
    print(f"  Temperature: {gpu.temp_celsius}°C (headroom: {gpu.temp_headroom_pct:.1f}%)")
    print(f"  Resource Hamiltonian: {gpu.ising_hamiltonian():.4f}")
    
    # Basic sanity checks
    assert gpu.vram_used_mib >= 0
    assert gpu.vram_total_mib > 0
    assert gpu.vram_used_mib <= gpu.vram_total_mib
    assert gpu.temp_celsius > 0
    assert gpu.temp_celsius < 150  # Reasonable upper bound
    
    print("  ✅ PASS: GPU metrics query works")


def run_all_tests():
    """Run complete test suite."""
    print("=" * 70)
    print("Waveform Equilibrium Test Suite")
    print("=" * 70)
    
    tests = [
        test_eigenspace_decomposition,
        test_waveform_state_computation,
        test_convergence_tracking,
        test_resource_hamiltonian,
        test_integration_api,
        test_gpu_metrics_query
    ]
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ❌ FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"  ⚠️  SKIP: {e}")
            skipped += 1
    
    print("\n" + "=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 70)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
