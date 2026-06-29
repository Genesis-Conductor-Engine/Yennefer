#!/usr/bin/env python3
# @Igor Holt
"""
Yennefer Performance Tests
EnKG kernel throughput, validation latency, memory efficiency, thermal limits
"""

import pytest
import torch
import time
import psutil
import os
from pathlib import Path
from typing import List, Dict, Any

from src.kernels.enkg_exchange import (
    apply_M_matrix, 
    benchmark_enkg_kernel,
    TRITON_AVAILABLE
)


class TestEnKGPerformance:
    """Performance tests for EnKG exchange kernel"""
    
    def test_throughput_target_150gbs(self):
        """Test EnKG kernel throughput (target: >150 GB/s)"""
        if not torch.cuda.is_available():
            pytest.skip("CUDA not available for throughput testing")
        
        # Large tensor for accurate measurement
        size = 1024 * 1024  # 1M elements
        results = benchmark_enkg_kernel(size=size, n_iterations=100)
        
        throughput = results['throughput_gb_s']
        target = 150.0
        
        print(f"\n{'='*60}")
        print(f"EnKG Throughput Test")
        print(f"{'='*60}")
        print(f"Size: {size:,} elements")
        print(f"Device: {results['device']}")
        print(f"Triton: {results['triton_available']}")
        print(f"Throughput: {throughput:.2f} GB/s")
        print(f"Target: {target:.2f} GB/s")
        print(f"Status: {'✓ PASS' if throughput >= target else '✗ FAIL'}")
        print(f"{'='*60}")
        
        # Relaxed assertion for GTX 1650 (128 GB/s theoretical)
        # Real throughput is typically 80-90% of theoretical
        min_acceptable = 100.0  # GB/s
        assert throughput >= min_acceptable, \
            f"Throughput {throughput:.2f} GB/s below minimum {min_acceptable} GB/s"
        
        if throughput >= target:
            print(f"✓ Throughput target achieved: {throughput:.2f} GB/s")
        else:
            print(f"⚠ Throughput below target but acceptable: {throughput:.2f} GB/s")
    
    def test_throughput_scaling(self):
        """Test throughput scaling with tensor size"""
        if not torch.cuda.is_available():
            pytest.skip("CUDA not available")
        
        sizes = [1024, 10240, 102400, 1024*1024]
        results = []
        
        print(f"\n{'='*60}")
        print(f"Throughput Scaling Test")
        print(f"{'='*60}")
        print(f"{'Size':<15} {'Time (ms)':<15} {'Throughput (GB/s)':<20}")
        print(f"{'-'*60}")
        
        for size in sizes:
            benchmark = benchmark_enkg_kernel(size=size, n_iterations=50)
            results.append(benchmark)
            
            print(f"{size:<15,} {benchmark['avg_time_ms']:<15.4f} {benchmark['throughput_gb_s']:<20.2f}")
        
        print(f"{'='*60}")
        
        # Throughput should increase with size (better amortization)
        throughputs = [r['throughput_gb_s'] for r in results]
        assert throughputs[-1] > throughputs[0], \
            "Throughput should scale with tensor size"
        
        print(f"✓ Scaling verified: {throughputs[0]:.2f} → {throughputs[-1]:.2f} GB/s")
    
    def test_latency_small_tensors(self):
        """Test latency for small tensor operations"""
        sizes = [64, 128, 256, 512, 1024]
        latencies = []
        
        print(f"\n{'='*60}")
        print(f"Small Tensor Latency Test")
        print(f"{'='*60}")
        print(f"{'Size':<15} {'Latency (μs)':<15}")
        print(f"{'-'*60}")
        
        for size in sizes:
            x = torch.randn(size, dtype=torch.float32)
            if torch.cuda.is_available():
                x = x.cuda()
            
            # Warmup
            for _ in range(10):
                _ = apply_M_matrix(x, kappa=0.7, gamma=0.3)
            
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            
            # Measure
            n_iterations = 100
            start = time.perf_counter()
            for _ in range(n_iterations):
                _ = apply_M_matrix(x, kappa=0.7, gamma=0.3)
            
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            
            end = time.perf_counter()
            latency_us = (end - start) * 1e6 / n_iterations
            latencies.append(latency_us)
            
            print(f"{size:<15,} {latency_us:<15.2f}")
        
        print(f"{'='*60}")
        
        # Latency should be reasonable (<1ms for small tensors)
        max_latency = max(latencies)
        assert max_latency < 1000, f"Latency too high: {max_latency:.2f} μs"
        
        print(f"✓ Latency acceptable: max {max_latency:.2f} μs")
    
    def test_batch_processing_throughput(self):
        """Test throughput for batch processing"""
        if not torch.cuda.is_available():
            pytest.skip("CUDA not available")
        
        batch_sizes = [1, 10, 50, 100]
        tensor_size = 10240
        
        print(f"\n{'='*60}")
        print(f"Batch Processing Throughput Test")
        print(f"{'='*60}")
        print(f"Tensor size per batch item: {tensor_size:,}")
        print(f"{'Batch Size':<15} {'Total Time (ms)':<20} {'Items/sec':<15}")
        print(f"{'-'*60}")
        
        for batch_size in batch_sizes:
            x = torch.randn(batch_size, tensor_size, dtype=torch.float32).cuda()
            
            # Warmup
            for _ in range(5):
                _ = apply_M_matrix(x, kappa=0.7, gamma=0.3)
            
            torch.cuda.synchronize()
            
            # Measure
            n_iterations = 50
            start = time.perf_counter()
            for _ in range(n_iterations):
                _ = apply_M_matrix(x, kappa=0.7, gamma=0.3)
            torch.cuda.synchronize()
            end = time.perf_counter()
            
            total_time_ms = (end - start) * 1000
            items_per_sec = (batch_size * n_iterations) / (end - start)
            
            print(f"{batch_size:<15} {total_time_ms:<20.2f} {items_per_sec:<15.1f}")
        
        print(f"{'='*60}")
        print(f"✓ Batch processing benchmark complete")
    
    def test_memory_copy_overhead(self):
        """Test memory copy overhead (host ↔ device)"""
        if not torch.cuda.is_available():
            pytest.skip("CUDA not available")
        
        sizes = [1024, 10240, 102400, 1024*1024]
        
        print(f"\n{'='*60}")
        print(f"Memory Copy Overhead Test")
        print(f"{'='*60}")
        print(f"{'Size':<15} {'H→D (ms)':<15} {'Compute (ms)':<15} {'D→H (ms)':<15}")
        print(f"{'-'*60}")
        
        for size in sizes:
            # Host to device
            x_cpu = torch.randn(size, dtype=torch.float32)
            start = time.perf_counter()
            x_gpu = x_cpu.cuda()
            torch.cuda.synchronize()
            h2d_time = (time.perf_counter() - start) * 1000
            
            # Compute
            start = time.perf_counter()
            result = apply_M_matrix(x_gpu, kappa=0.7, gamma=0.3)
            torch.cuda.synchronize()
            compute_time = (time.perf_counter() - start) * 1000
            
            # Device to host
            start = time.perf_counter()
            result_cpu = result.cpu()
            torch.cuda.synchronize()
            d2h_time = (time.perf_counter() - start) * 1000
            
            print(f"{size:<15,} {h2d_time:<15.4f} {compute_time:<15.4f} {d2h_time:<15.4f}")
        
        print(f"{'='*60}")
        print(f"✓ Memory copy overhead measured")


class TestValidationPerformance:
    """Performance tests for validation components"""
    
    def test_validation_latency(self):
        """Test Agent3 validator latency"""
        from src.orchestrator.agent3_validator import OuroborosAgent3Validator
        
        validator = OuroborosAgent3Validator(
            invariant_truth={},
            use_local_llm=True
        )
        
        payload = {
            "type": "test",
            "data": [1.0] * 100,
            "timestamp": "2026-05-20T00:00:00Z"
        }
        
        # Warmup
        for _ in range(5):
            _ = validator.validate(payload, mock_result="DUCTILE")
        
        # Measure
        n_iterations = 50
        latencies = []
        
        for _ in range(n_iterations):
            start = time.perf_counter()
            _ = validator.validate(payload, mock_result="DUCTILE")
            end = time.perf_counter()
            latencies.append((end - start) * 1000)
        
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)
        
        print(f"\n{'='*60}")
        print(f"Validation Latency Test")
        print(f"{'='*60}")
        print(f"Iterations: {n_iterations}")
        print(f"Avg latency: {avg_latency:.2f} ms")
        print(f"Min latency: {min_latency:.2f} ms")
        print(f"Max latency: {max_latency:.2f} ms")
        print(f"{'='*60}")
        
        # Should be fast (<50ms)
        assert avg_latency < 50, f"Validation too slow: {avg_latency:.2f} ms"
        
        print(f"✓ Validation latency acceptable: {avg_latency:.2f} ms")


class TestMemoryEfficiency:
    """Memory efficiency tests"""
    
    def test_memory_allocation_cleanup(self):
        """Test proper memory allocation and cleanup"""
        if not torch.cuda.is_available():
            pytest.skip("CUDA not available")
        
        torch.cuda.empty_cache()
        initial_allocated = torch.cuda.memory_allocated()
        initial_reserved = torch.cuda.memory_reserved()
        
        print(f"\n{'='*60}")
        print(f"Memory Efficiency Test")
        print(f"{'='*60}")
        print(f"Initial state:")
        print(f"  Allocated: {initial_allocated / 1e6:.2f} MB")
        print(f"  Reserved: {initial_reserved / 1e6:.2f} MB")
        
        # Allocate and process
        sizes = [10240, 102400, 1024*1024]
        peak_allocated = initial_allocated
        
        for size in sizes:
            x = torch.randn(size, dtype=torch.float32).cuda()
            result = apply_M_matrix(x, kappa=0.7, gamma=0.3)
            
            allocated = torch.cuda.memory_allocated()
            peak_allocated = max(peak_allocated, allocated)
            
            print(f"\nSize {size:,}:")
            print(f"  Allocated: {allocated / 1e6:.2f} MB")
            
            # Cleanup
            del x, result
            torch.cuda.synchronize()
        
        # Final cleanup
        torch.cuda.empty_cache()
        final_allocated = torch.cuda.memory_allocated()
        final_reserved = torch.cuda.memory_reserved()
        
        print(f"\nFinal state:")
        print(f"  Allocated: {final_allocated / 1e6:.2f} MB")
        print(f"  Reserved: {final_reserved / 1e6:.2f} MB")
        print(f"  Peak during test: {peak_allocated / 1e6:.2f} MB")
        print(f"{'='*60}")
        
        # Memory should be released
        assert final_allocated <= initial_allocated * 1.1, "Memory leak detected"
        
        print(f"✓ Memory properly managed, no leaks detected")
    
    def test_vram_usage_within_limits(self):
        """Test VRAM usage stays within aSHARD limits (4GB GTX 1650)"""
        if not torch.cuda.is_available():
            pytest.skip("CUDA not available")
        
        vram_total = 4 * 1024**3  # 4GB
        vram_limit = int(vram_total * 0.9)  # 90% safety margin
        
        torch.cuda.empty_cache()
        
        # Try to allocate up to safe limit
        safe_tensor_size = vram_limit // (4 * 2)  # float32, leave 50% margin
        
        try:
            x = torch.randn(safe_tensor_size, dtype=torch.float32).cuda()
            allocated = torch.cuda.memory_allocated()
            
            print(f"\n{'='*60}")
            print(f"VRAM Limit Test")
            print(f"{'='*60}")
            print(f"Total VRAM: {vram_total / 1e9:.2f} GB")
            print(f"Safe limit (90%): {vram_limit / 1e9:.2f} GB")
            print(f"Allocated: {allocated / 1e9:.2f} GB")
            print(f"Usage: {(allocated / vram_total) * 100:.1f}%")
            print(f"{'='*60}")
            
            assert allocated <= vram_limit, f"Exceeded VRAM limit: {allocated / 1e9:.2f} GB"
            
            # Perform operation
            result = apply_M_matrix(x, kappa=0.7, gamma=0.3)
            assert result is not None
            
            print(f"✓ VRAM usage within limits")
            
        finally:
            if 'x' in locals():
                del x
            if 'result' in locals():
                del result
            torch.cuda.empty_cache()
    
    def test_cpu_memory_usage(self):
        """Test CPU memory usage during operations"""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1e6  # MB
        
        # Process large tensors on CPU
        sizes = [10240, 102400, 1024*1024]
        peak_memory = initial_memory
        
        print(f"\n{'='*60}")
        print(f"CPU Memory Usage Test")
        print(f"{'='*60}")
        print(f"Initial: {initial_memory:.2f} MB")
        
        for size in sizes:
            x = torch.randn(size, dtype=torch.float32)
            result = apply_M_matrix(x, kappa=0.7, gamma=0.3)
            
            current_memory = process.memory_info().rss / 1e6
            peak_memory = max(peak_memory, current_memory)
            
            print(f"Size {size:,}: {current_memory:.2f} MB")
            
            del x, result
        
        final_memory = process.memory_info().rss / 1e6
        memory_increase = final_memory - initial_memory
        
        print(f"Peak: {peak_memory:.2f} MB")
        print(f"Final: {final_memory:.2f} MB")
        print(f"Increase: {memory_increase:.2f} MB")
        print(f"{'='*60}")
        
        # Memory increase should be reasonable (<500 MB)
        assert memory_increase < 500, f"Excessive memory usage: {memory_increase:.2f} MB"
        
        print(f"✓ CPU memory usage acceptable")


class TestThermalLimits:
    """Thermal constraint tests"""
    
    def test_thermal_monitoring(self):
        """Test GPU thermal monitoring (if available)"""
        if not torch.cuda.is_available():
            pytest.skip("CUDA not available")
        
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            
            temp_before = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            
            # Run intensive workload
            size = 1024 * 1024
            x = torch.randn(size, dtype=torch.float32).cuda()
            
            for _ in range(100):
                _ = apply_M_matrix(x, kappa=0.7, gamma=0.3)
            
            torch.cuda.synchronize()
            
            temp_after = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            
            print(f"\n{'='*60}")
            print(f"Thermal Monitoring Test")
            print(f"{'='*60}")
            print(f"Temperature before: {temp_before}°C")
            print(f"Temperature after: {temp_after}°C")
            print(f"Delta: {temp_after - temp_before}°C")
            print(f"Thermal limit: 89.6°C")
            print(f"{'='*60}")
            
            # Should stay below thermal limit
            thermal_limit = 89.6
            assert temp_after < thermal_limit, f"Temperature {temp_after}°C exceeds limit {thermal_limit}°C"
            
            print(f"✓ Thermal limits respected")
            
            pynvml.nvmlShutdown()
            
        except ImportError:
            pytest.skip("pynvml not available for thermal monitoring")
    
    def test_sustained_load_thermal(self):
        """Test thermal behavior under sustained load"""
        if not torch.cuda.is_available():
            pytest.skip("CUDA not available")
        
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            
            size = 1024 * 1024
            x = torch.randn(size, dtype=torch.float32).cuda()
            
            temps = []
            duration = 10  # seconds
            
            print(f"\n{'='*60}")
            print(f"Sustained Load Thermal Test")
            print(f"{'='*60}")
            print(f"Duration: {duration}s")
            print(f"Monitoring temperature every second...")
            
            start = time.time()
            iteration = 0
            
            while time.time() - start < duration:
                _ = apply_M_matrix(x, kappa=0.7, gamma=0.3)
                iteration += 1
                
                if iteration % 100 == 0:
                    torch.cuda.synchronize()
                    temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                    temps.append(temp)
                    print(f"  {len(temps)}s: {temp}°C")
            
            torch.cuda.synchronize()
            
            max_temp = max(temps)
            avg_temp = sum(temps) / len(temps)
            
            print(f"\nMax temperature: {max_temp}°C")
            print(f"Avg temperature: {avg_temp:.1f}°C")
            print(f"Thermal limit: 89.6°C")
            print(f"{'='*60}")
            
            thermal_limit = 89.6
            assert max_temp < thermal_limit, f"Max temp {max_temp}°C exceeds limit {thermal_limit}°C"
            
            print(f"✓ Sustained load thermal test passed")
            
            pynvml.nvmlShutdown()
            
        except ImportError:
            pytest.skip("pynvml not available")


class TestPerformanceRegression:
    """Performance regression tests"""
    
    def test_performance_baseline(self):
        """Establish performance baseline for regression testing"""
        if not torch.cuda.is_available():
            pytest.skip("CUDA not available")
        
        baseline = {
            "throughput_min_gbs": 100.0,
            "latency_max_ms": 1.0,
            "memory_max_mb": 500
        }
        
        # Throughput test
        results = benchmark_enkg_kernel(size=1024*1024, n_iterations=100)
        throughput = results['throughput_gb_s']
        
        # Latency test
        x = torch.randn(1024, dtype=torch.float32).cuda()
        start = time.perf_counter()
        _ = apply_M_matrix(x, kappa=0.7, gamma=0.3)
        torch.cuda.synchronize()
        latency_ms = (time.perf_counter() - start) * 1000
        
        # Memory test
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1e6
        
        print(f"\n{'='*60}")
        print(f"Performance Baseline Test")
        print(f"{'='*60}")
        print(f"Throughput: {throughput:.2f} GB/s (min: {baseline['throughput_min_gbs']})")
        print(f"Latency: {latency_ms:.4f} ms (max: {baseline['latency_max_ms']})")
        print(f"Memory: {memory_mb:.2f} MB (max: {baseline['memory_max_mb']})")
        print(f"{'='*60}")
        
        assert throughput >= baseline['throughput_min_gbs']
        assert latency_ms <= baseline['latency_max_ms']
        assert memory_mb <= baseline['memory_max_mb']
        
        print(f"✓ Performance meets baseline requirements")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
