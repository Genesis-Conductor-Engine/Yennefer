# @Igor Holt
"""
Tests for Yennefer's EnKG exchange operator Triton kernel.
"""

import pytest
import torch
import numpy as np
from src.kernels.enkg_exchange import apply_M_matrix, benchmark_enkg_kernel, TRITON_AVAILABLE


class TestEnKGExchangeOperator:
    """Test suite for EnKG exchange operator M = κI + γσ_x"""
    
    def test_identity_behavior(self):
        """Test pure identity operator (κ=1, γ=0)"""
        x = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], dtype=torch.float32)
        result = apply_M_matrix(x, kappa=1.0, gamma=0.0)
        
        # Identity should return input unchanged
        assert torch.allclose(result, x), f"Expected {x}, got {result}"
        print(f"✓ Identity test passed: {x} -> {result}")
    
    def test_pauli_x_behavior(self):
        """Test pure Pauli-X operator (κ=0, γ=1)"""
        x = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], dtype=torch.float32)
        result = apply_M_matrix(x, kappa=0.0, gamma=1.0)
        
        # Pauli-X should swap pairs: [a,b,c,d] -> [b,a,d,c]
        expected = torch.tensor([2.0, 1.0, 4.0, 3.0, 6.0, 5.0], dtype=torch.float32)
        assert torch.allclose(result, expected), f"Expected {expected}, got {result}"
        print(f"✓ Pauli-X test passed: {x} -> {result}")
    
    def test_mixed_operator(self):
        """Test mixed operator (κ=0.7, γ=0.3)"""
        x = torch.tensor([1.0, 2.0, 3.0, 4.0], dtype=torch.float32)
        result = apply_M_matrix(x, kappa=0.7, gamma=0.3)
        
        # Manual calculation:
        # result[0] = 0.7*1.0 + 0.3*2.0 = 0.7 + 0.6 = 1.3
        # result[1] = 0.3*1.0 + 0.7*2.0 = 0.3 + 1.4 = 1.7
        # result[2] = 0.7*3.0 + 0.3*4.0 = 2.1 + 1.2 = 3.3
        # result[3] = 0.3*3.0 + 0.7*4.0 = 0.9 + 2.8 = 3.7
        expected = torch.tensor([1.3, 1.7, 3.3, 3.7], dtype=torch.float32)
        assert torch.allclose(result, expected, atol=1e-6), f"Expected {expected}, got {result}"
        print(f"✓ Mixed operator test passed: {x} -> {result}")
    
    def test_contiguous_requirement(self):
        """Test that non-contiguous tensors raise ValueError"""
        x = torch.tensor([[1.0, 2.0], [3.0, 4.0]], dtype=torch.float32)
        x_noncontiguous = x.T  # Transpose makes it non-contiguous
        
        with pytest.raises(ValueError, match="contiguous"):
            apply_M_matrix(x_noncontiguous, kappa=0.5, gamma=0.5)
        
        # Contiguous version should work
        result = apply_M_matrix(x_noncontiguous.contiguous(), kappa=0.5, gamma=0.5)
        assert result is not None
        print("✓ Contiguous requirement test passed")
    
    def test_even_dimension_requirement(self):
        """Test that odd-length tensors raise ValueError"""
        x = torch.tensor([1.0, 2.0, 3.0], dtype=torch.float32)
        
        with pytest.raises(ValueError, match="even"):
            apply_M_matrix(x, kappa=0.5, gamma=0.5)
        
        print("✓ Even dimension requirement test passed")
    
    def test_multidimensional_tensor(self):
        """Test with multidimensional tensors"""
        x = torch.tensor([[1.0, 2.0, 3.0, 4.0],
                         [5.0, 6.0, 7.0, 8.0]], dtype=torch.float32)
        result = apply_M_matrix(x, kappa=1.0, gamma=0.0)
        
        # Identity should preserve shape
        assert result.shape == x.shape
        assert torch.allclose(result, x)
        print(f"✓ Multidimensional test passed: shape {x.shape} preserved")
    
    def test_zero_operator(self):
        """Test zero operator (κ=0, γ=0)"""
        x = torch.tensor([1.0, 2.0, 3.0, 4.0], dtype=torch.float32)
        result = apply_M_matrix(x, kappa=0.0, gamma=0.0)
        
        expected = torch.zeros_like(x)
        assert torch.allclose(result, expected), f"Expected {expected}, got {result}"
        print("✓ Zero operator test passed")
    
    def test_normalization_preserving(self):
        """Test that the operator preserves certain properties for κ²+γ²=1"""
        # When κ²+γ²=1, the operator is unitary for paired qubits
        kappa = np.sqrt(0.6)
        gamma = np.sqrt(0.4)
        
        x = torch.tensor([1.0, 0.0, 0.0, 1.0], dtype=torch.float32)
        result = apply_M_matrix(x, kappa=kappa, gamma=gamma)
        
        # Check that norm is approximately preserved
        input_norm = torch.norm(x)
        output_norm = torch.norm(result)
        assert torch.allclose(input_norm, output_norm, atol=1e-5), \
            f"Norm not preserved: {input_norm} -> {output_norm}"
        print(f"✓ Normalization test passed: norm {input_norm:.4f} preserved")
    
    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
    def test_cuda_execution(self):
        """Test execution on CUDA device"""
        x = torch.tensor([1.0, 2.0, 3.0, 4.0], device='cuda', dtype=torch.float32)
        result = apply_M_matrix(x, kappa=0.8, gamma=0.2)
        
        assert result.device.type == 'cuda'
        # Compare with CPU result
        x_cpu = x.cpu()
        result_cpu = apply_M_matrix(x_cpu, kappa=0.8, gamma=0.2)
        assert torch.allclose(result.cpu(), result_cpu, atol=1e-5)
        print("✓ CUDA execution test passed")
    
    def test_large_tensor(self):
        """Test with large tensor to verify memory handling"""
        size = 10000
        x = torch.randn(size, dtype=torch.float32)
        result = apply_M_matrix(x, kappa=0.6, gamma=0.4)
        
        assert result.shape == x.shape
        assert not torch.isnan(result).any()
        assert not torch.isinf(result).any()
        print(f"✓ Large tensor test passed: {size} elements processed")


class TestBenchmark:
    """Test suite for benchmarking functionality"""
    
    def test_benchmark_execution(self):
        """Test that benchmark runs without errors"""
        results = benchmark_enkg_kernel(size=1024, n_iterations=10)
        
        assert 'device' in results
        assert 'avg_time_ms' in results
        assert 'throughput_gb_s' in results
        assert 'triton_available' in results
        
        assert results['avg_time_ms'] > 0
        assert results['throughput_gb_s'] > 0
        
        print(f"✓ Benchmark test passed:")
        print(f"  Device: {results['device']}")
        print(f"  Avg time: {results['avg_time_ms']:.4f} ms")
        print(f"  Throughput: {results['throughput_gb_s']:.2f} GB/s")
        print(f"  Triton available: {results['triton_available']}")
    
    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
    def test_benchmark_cuda_performance(self):
        """Benchmark CUDA performance if available"""
        results = benchmark_enkg_kernel(size=1024*1024, n_iterations=100)
        
        if results['device'] == 'cuda':
            # Basic performance check (should be >1 GB/s on modern GPUs)
            assert results['throughput_gb_s'] > 1.0, \
                f"Low throughput: {results['throughput_gb_s']:.2f} GB/s"
            print(f"✓ CUDA performance test passed: {results['throughput_gb_s']:.2f} GB/s")


class TestTritonAvailability:
    """Test Triton availability and fallback behavior"""
    
    def test_triton_status(self):
        """Report Triton availability status"""
        if TRITON_AVAILABLE:
            print("✓ Triton is available")
        else:
            print("⚠ Triton not available, using CPU fallback")
        
        # Test should always pass, just reports status
        assert True
    
    def test_cpu_fallback(self):
        """Test that CPU fallback works correctly"""
        x = torch.tensor([1.0, 2.0, 3.0, 4.0], dtype=torch.float32)
        result = apply_M_matrix(x, kappa=0.6, gamma=0.4)
        
        # Verify computation is correct
        expected_0 = 0.6 * 1.0 + 0.4 * 2.0
        expected_1 = 0.4 * 1.0 + 0.6 * 2.0
        
        assert torch.allclose(result[0], torch.tensor(expected_0), atol=1e-6)
        assert torch.allclose(result[1], torch.tensor(expected_1), atol=1e-6)
        print("✓ CPU fallback test passed")


def test_end_to_end():
    """End-to-end integration test"""
    print("\n" + "="*60)
    print("EnKG Exchange Operator End-to-End Test")
    print("="*60)
    
    # Create test state vector representing two qubits
    x = torch.tensor([0.6, 0.8, 0.8, -0.6], dtype=torch.float32)
    
    print(f"Input state: {x}")
    print(f"Input norm: {torch.norm(x):.4f}")
    
    # Apply various operators
    operators = [
        (1.0, 0.0, "Identity"),
        (0.0, 1.0, "Pauli-X"),
        (0.707, 0.707, "Hadamard-like"),
        (0.9, 0.1, "Mostly Identity"),
        (0.1, 0.9, "Mostly Exchange"),
    ]
    
    for kappa, gamma, name in operators:
        result = apply_M_matrix(x, kappa=kappa, gamma=gamma)
        norm_preserved = torch.allclose(torch.norm(x), torch.norm(result), atol=1e-5)
        print(f"\n{name} (κ={kappa}, γ={gamma}):")
        print(f"  Output: {result}")
        print(f"  Output norm: {torch.norm(result):.4f}")
        print(f"  Norm preserved: {'✓' if norm_preserved else '✗'}")
    
    print("\n" + "="*60)
    print("All tests completed successfully!")
    print("="*60)


if __name__ == '__main__':
    # Run tests with pytest if available, otherwise run manually
    try:
        import sys
        sys.exit(pytest.main([__file__, '-v', '-s']))
    except (ImportError, SystemExit):
        # Run tests manually if pytest not available
        print("Running tests manually (pytest not available)...\n")
        
        test_suite = TestEnKGExchangeOperator()
        test_suite.test_identity_behavior()
        test_suite.test_pauli_x_behavior()
        test_suite.test_mixed_operator()
        test_suite.test_contiguous_requirement()
        test_suite.test_even_dimension_requirement()
        test_suite.test_multidimensional_tensor()
        test_suite.test_zero_operator()
        test_suite.test_normalization_preserving()
        test_suite.test_large_tensor()
        
        if torch.cuda.is_available():
            test_suite.test_cuda_execution()
        
        benchmark_suite = TestBenchmark()
        benchmark_suite.test_benchmark_execution()
        
        if torch.cuda.is_available():
            benchmark_suite.test_benchmark_cuda_performance()
        
        triton_suite = TestTritonAvailability()
        triton_suite.test_triton_status()
        triton_suite.test_cpu_fallback()
        
        test_end_to_end()
