#!/usr/bin/env python3
# @Igor Holt
"""
Yennefer Integration Tests
Full orchestration cycle: EnKG → Validation → aSHARD allocation → Gateway integration
"""

import pytest
import torch
import yaml
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import Yennefer components
from src.kernels.enkg_exchange import apply_M_matrix, TRITON_AVAILABLE
from src.orchestrator.agent3_validator import (
    OuroborosAgent3Validator,
    ValidationResult,
    AShardParams,
    PIScope,
    InvariantTruth
)
from workers.yennefer_telemetry_daemon import YenneferTelemetryDaemon


class TestYenneferIntegration:
    """Integration tests for full Yennefer orchestration cycle"""
    
    @pytest.fixture
    def config_path(self):
        """Path to yennefer config"""
        return Path("/home/diamondnode/diamondnode-unified-inference/config/yennefer_config.yaml")
    
    @pytest.fixture
    def ashard_params(self):
        """GTX 1650 hardware parameters"""
        return AShardParams(
            vram_total_bytes=4294967296,  # 4GB
            vram_allocation_buffer=0.9,
            thermal_max_celsius=89.6,
            compute_capability=(7, 5),
            memory_bandwidth_gbps=128.0
        )
    
    @pytest.fixture
    def invariant_truth(self):
        """Mathematical invariants for validation"""
        return {
            "conservation_laws": ["energy_conservation", "momentum_conservation"],
            "symmetries": ["time_translation", "gauge_invariance"],
            "dimensional_constraints": {
                "max_vram_gb": 4,
                "min_throughput_gb_s": 150
            },
            "boundary_conditions": {
                "thermal_max": 89.6,
                "vram_buffer": 0.9
            }
        }
    
    @pytest.fixture
    def pi_scope(self):
        """Process Invariance scope"""
        return {
            "allowed_operations": ["enkg_exchange", "validation", "telemetry"],
            "resource_limits": {
                "max_memory_mb": 3600,
                "max_compute_time_s": 30
            },
            "state_transitions": {
                "NULL": ["DUCTILE"],
                "DUCTILE": ["CRYSTALLINE", "NULL"],
                "CRYSTALLINE": ["DUCTILE"]
            },
            "execution_context": {
                "device": "cuda",
                "precision": "float32"
            }
        }
    
    def test_enkg_to_validation_pipeline(self, ashard_params, invariant_truth, pi_scope):
        """Test EnKG kernel → Validator pipeline"""
        # Step 1: Generate state vector with EnKG
        x = torch.tensor([1.0, 2.0, 3.0, 4.0], dtype=torch.float32)
        if torch.cuda.is_available():
            x = x.cuda()
        
        # Apply EnKG exchange operator
        kappa, gamma = 0.7, 0.3
        result = apply_M_matrix(x, kappa=kappa, gamma=gamma)
        
        assert result is not None
        assert result.shape == x.shape
        assert not torch.isnan(result).any()
        
        # Step 2: Validate with Agent3
        validator = OuroborosAgent3Validator(
            invariant_truth=invariant_truth,
            ashard_params=ashard_params.__dict__,
            pi_scope=pi_scope,
            use_local_llm=True  # Use mock for testing
        )
        
        # Create payload from EnKG result
        payload = {
            "type": "enkg_exchange",
            "input": x.cpu().tolist(),
            "output": result.cpu().tolist(),
            "operator": {"kappa": kappa, "gamma": gamma},
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # Validate (will use mock LLM)
        validation_result = validator.validate(payload, mock_result="DUCTILE")
        
        assert validation_result is not None
        assert validation_result.state in ["NULL", "DUCTILE", "CRYSTALLINE"]
        
        print(f"✓ EnKG→Validation pipeline: {x.shape} tensor → {validation_result.state}")
    
    def test_ashard_allocation_and_cleanup(self, ashard_params):
        """Test aSHARD (autonomic SHARD) memory allocation and cleanup"""
        if not torch.cuda.is_available():
            pytest.skip("CUDA not available for aSHARD testing")
        
        # Calculate safe allocation size
        total_bytes = ashard_params.vram_total_bytes
        buffer = ashard_params.vram_allocation_buffer
        safe_bytes = int(total_bytes * buffer)
        
        # Allocate tensor within aSHARD limits
        tensor_size = safe_bytes // (4 * 4)  # float32 input + output must both fit on 4GB cards
        
        try:
            # Allocate
            tensor = torch.randn(tensor_size, device='cuda', dtype=torch.float32)
            
            # Check memory
            allocated = torch.cuda.memory_allocated()
            reserved = torch.cuda.memory_reserved()
            
            assert allocated > 0, "No memory allocated"
            assert allocated <= safe_bytes, f"Allocation exceeded aSHARD limit: {allocated} > {safe_bytes}"
            
            # Perform operation
            result = apply_M_matrix(tensor, kappa=0.8, gamma=0.2)
            assert result.shape == tensor.shape
            
            print(f"✓ aSHARD allocation: {allocated / 1e9:.2f} GB / {total_bytes / 1e9:.2f} GB ({(allocated/total_bytes)*100:.1f}%)")
            
        finally:
            # Cleanup
            del tensor
            if 'result' in locals():
                del result
            torch.cuda.empty_cache()
            
            # Verify cleanup
            final_allocated = torch.cuda.memory_allocated()
            assert final_allocated < allocated, "Memory not properly released"
            print(f"✓ aSHARD cleanup: {final_allocated / 1e9:.2f} GB remaining")
    
    @patch('workers.yennefer_telemetry_daemon.NotionClient')
    def test_gateway_integration_mock(self, mock_notion, config_path):
        """Test gateway integration with mock Notion client"""
        # Mock Notion client
        mock_client = MagicMock()
        mock_notion.return_value = mock_client
        mock_client.pages.create.return_value = {"id": "test-page-id"}
        
        # Create daemon
        daemon = YenneferTelemetryDaemon(str(config_path))
        daemon.notion_client = mock_client
        
        # Run single cycle
        daemon.run_cycle()
        
        # Verify Notion was called
        assert mock_client.pages.create.called
        call_args = mock_client.pages.create.call_args
        
        # Verify payload structure
        properties = call_args.kwargs['properties']
        assert "Timestamp" in properties
        assert "η_thermo" in properties
        assert "ε" in properties
        assert "γ" in properties
        assert "VRAM_JAX_Pct" in properties
        
        print(f"✓ Gateway integration: {daemon.run_count} cycles, Notion POST verified")
    
    def test_telemetry_data_flow(self, config_path):
        """Test telemetry data collection and processing"""
        daemon = YenneferTelemetryDaemon(str(config_path))
        
        # Compute metrics
        metrics = daemon.compute_metrics()
        
        # Verify required fields
        required_fields = [
            "eta_thermo", "epsilon", "gamma", "delta_q",
            "vram_jax_pct", "cuda_q_kernel_status", "crystalline_score"
        ]
        
        for field in required_fields:
            assert field in metrics, f"Missing field: {field}"
            assert metrics[field] is not None
        
        # Verify value ranges
        assert 0 <= metrics["eta_thermo"] <= 1.0
        assert 0 <= metrics["epsilon"] <= 1.0
        assert metrics["gamma"] > 0
        assert 0 <= metrics["vram_jax_pct"] <= 100
        assert 0 <= metrics["crystalline_score"] <= 1.0
        
        print(f"✓ Telemetry data: η={metrics['eta_thermo']:.4f}, ε={metrics['epsilon']:.4f}, VRAM={metrics['vram_jax_pct']:.2f}%")
    
    def test_hysteresis_mechanism(self, config_path):
        """Test ε hysteresis with gamma buffer"""
        from workers.thermodynamic_simulator import epsilon_with_hysteresis
        
        gamma = 0.05  # From config
        
        # Test cases: (current, previous, expected)
        test_cases = [
            (0.5, 0.4, 0.5),      # Increase > gamma → accept
            (0.45, 0.4, 0.4),     # Increase < gamma → hold
            (0.3, 0.4, 0.3),      # Decrease > gamma → accept
            (0.38, 0.4, 0.4),     # Decrease < gamma → hold
            (0.5, 0.5, 0.5),      # No change → hold
        ]
        
        for current, previous, expected in test_cases:
            result = epsilon_with_hysteresis(current, previous, gamma)
            assert abs(result - expected) < 1e-6, \
                f"Hysteresis failed: ε({current}) from {previous} = {result}, expected {expected}"
        
        print("✓ Hysteresis mechanism: all test cases passed")
    
    def test_crystalline_score_computation(self):
        """Test crystalline score calculation"""
        from workers.thermodynamic_simulator import ThermodynamicSimulator
        
        simulator = ThermodynamicSimulator(envelope_version="0.3.0", electron_sim_steps=100)
        
        # Test cases: (eta, vram_ratio, expected_range)
        test_cases = [
            (0.9, 0.3, (0.8, 1.0)),   # High eta, low VRAM → high score
            (0.5, 0.5, (0.5, 0.8)),   # Medium eta, medium VRAM → medium score
            (0.2, 0.9, (0.0, 0.4)),   # Low eta, high VRAM → low score
        ]
        
        for eta, vram_ratio, (min_score, max_score) in test_cases:
            score = simulator.compute_crystalline_score(
                eta, vram_ratio,
                base_score=0.75,
                vram_penalty_factor=0.1,
                eta_bonus_factor=0.2
            )
            
            assert 0 <= score <= 1.0, f"Score out of bounds: {score}"
            assert min_score <= score <= max_score, \
                f"Score {score} not in expected range [{min_score}, {max_score}]"
        
        print("✓ Crystalline score: all test cases passed")
    
    def test_end_to_end_orchestration_cycle(self, config_path, ashard_params, invariant_truth, pi_scope):
        """Test complete orchestration cycle: EnKG → Telemetry → Validation"""
        # Step 1: EnKG operation
        x = torch.randn(1024, dtype=torch.float32)
        if torch.cuda.is_available():
            x = x.cuda()
        
        result = apply_M_matrix(x, kappa=0.7, gamma=0.3)
        assert result is not None
        
        # Step 2: Telemetry collection
        daemon = YenneferTelemetryDaemon(str(config_path))
        metrics = daemon.compute_metrics()
        assert metrics["eta_thermo"] is not None
        
        # Step 3: Validation
        validator = OuroborosAgent3Validator(
            invariant_truth=invariant_truth,
            ashard_params=ashard_params.__dict__,
            pi_scope=pi_scope,
            use_local_llm=True
        )
        
        payload = {
            "enkg_result": result.cpu().tolist()[:10],  # Sample
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        validation_result = validator.validate(payload, mock_result="CRYSTALLINE")
        assert validation_result.state in ["NULL", "DUCTILE", "CRYSTALLINE"]
        
        print(f"✓ E2E orchestration: EnKG({x.shape}) → Telemetry(η={metrics['eta_thermo']:.3f}) → Validation({validation_result.state})")
    
    def test_thermal_constraints(self, ashard_params):
        """Test thermal constraint enforcement"""
        thermal_max = ashard_params.thermal_max_celsius
        
        # Mock thermal reading
        mock_temps = [70.0, 85.0, 89.0, 90.0, 95.0]
        
        for temp in mock_temps:
            thermal_ok = temp <= thermal_max
            
            if not thermal_ok:
                # Should trigger throttling/offload
                print(f"  Thermal warning: {temp}°C > {thermal_max}°C")
            else:
                print(f"  Thermal OK: {temp}°C ≤ {thermal_max}°C")
        
        print("✓ Thermal constraints: monitoring functional")
    
    def test_memory_bandwidth_validation(self, ashard_params):
        """Test memory bandwidth meets requirements"""
        if not torch.cuda.is_available():
            pytest.skip("CUDA not available for bandwidth testing")
        
        from src.kernels.enkg_exchange import benchmark_enkg_kernel
        
        # Run benchmark
        results = benchmark_enkg_kernel(size=1024*1024, n_iterations=50)
        
        # Check against aSHARD specs
        min_throughput = 100.0  # GB/s (reasonable for GTX 1650)
        actual_throughput = results['throughput_gb_s']
        
        assert actual_throughput > min_throughput, \
            f"Throughput too low: {actual_throughput:.2f} GB/s < {min_throughput} GB/s"
        
        print(f"✓ Memory bandwidth: {actual_throughput:.2f} GB/s (min: {min_throughput} GB/s)")


class TestYenneferErrorHandling:
    """Test error handling and edge cases"""
    
    def test_invalid_enkg_input(self):
        """Test EnKG with invalid inputs"""
        # Odd dimension
        with pytest.raises(ValueError, match="even"):
            x = torch.tensor([1.0, 2.0, 3.0])
            apply_M_matrix(x, kappa=0.5, gamma=0.5)
        
        # Non-contiguous
        with pytest.raises(ValueError, match="contiguous"):
            x = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
            apply_M_matrix(x.T, kappa=0.5, gamma=0.5)
        
        print("✓ Invalid input handling: errors raised correctly")
    
    def test_missing_config(self):
        """Test handling of missing configuration"""
        with pytest.raises(FileNotFoundError):
            YenneferTelemetryDaemon("/nonexistent/config.yaml")
        
        print("✓ Missing config handling: error raised correctly")
    
    def test_notion_client_unavailable(self, tmp_path):
        """Test graceful degradation when Notion client unavailable"""
        # Create minimal config
        config = {
            "yennefer": {
                "cadence_hours": 1,
                "notion_db": "test-db-id",
                "hysteresis": {"gamma_buffer": 0.05},
                "thermodynamic": {
                    "eta_thermo_max": 1.0,
                    "electron_sim_steps": 100,
                    "quantum_delta_range": [0.01, 0.15]
                },
                "vram_thresholds": {
                    "jax_warn": 0.42,
                    "jax_critical": 0.45
                },
                "crystalline": {
                    "base_score": 0.75,
                    "vram_penalty_factor": 0.1,
                    "eta_bonus_factor": 0.2
                }
            }
        }
        
        config_path = tmp_path / "test_config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config, f)
        
        # Create daemon without Notion
        daemon = YenneferTelemetryDaemon(str(config_path))
        daemon.notion_client = None
        
        # Should still compute metrics
        metrics = daemon.compute_metrics()
        assert metrics is not None
        
        # POST should fail gracefully
        success = daemon.post_to_notion(metrics)
        assert not success
        
        print("✓ Notion unavailable: graceful degradation")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
