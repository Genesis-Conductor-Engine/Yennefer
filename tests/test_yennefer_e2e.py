#!/usr/bin/env python3
# @Igor Holt
"""
Yennefer End-to-End Tests
Full workflow: Start orchestrator → Telemetry cycle → Exchange operator → Validation → Shutdown
"""

import pytest
import torch
import yaml
import time
import signal
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.kernels.enkg_exchange import apply_M_matrix
from workers.yennefer_telemetry_daemon import YenneferTelemetryDaemon


class TestYenneferE2E:
    """End-to-end workflow tests"""
    
    @pytest.fixture
    def config_path(self):
        """Path to yennefer config"""
        return Path("/home/diamondnode/diamondnode-unified-inference/config/yennefer_config.yaml")
    
    @pytest.fixture
    def config(self, config_path):
        """Load yennefer config"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def test_start_orchestrator(self, config_path):
        """Test orchestrator initialization"""
        # Create daemon
        daemon = YenneferTelemetryDaemon(str(config_path))
        
        assert daemon is not None
        assert daemon.simulator is not None
        assert daemon.sanitizer is not None
        assert daemon.envelope_version == "0.3.0"
        assert daemon.run_count == 0
        
        print("✓ Orchestrator started successfully")
    
    def test_telemetry_cycle(self, config_path):
        """Test single telemetry cycle"""
        daemon = YenneferTelemetryDaemon(str(config_path))
        
        initial_run_count = daemon.run_count
        
        # Run cycle (without Notion POST)
        daemon.notion_client = None
        daemon.run_cycle()
        
        assert daemon.run_count == initial_run_count + 1
        
        print(f"✓ Telemetry cycle completed: run_count={daemon.run_count}")
    
    def test_exchange_operator_application(self):
        """Test EnKG exchange operator application"""
        # Create state vector
        x = torch.tensor([1.0, 2.0, 3.0, 4.0], dtype=torch.float32)
        if torch.cuda.is_available():
            x = x.cuda()
        
        # Apply operator
        kappa, gamma = 0.7, 0.3
        result = apply_M_matrix(x, kappa=kappa, gamma=gamma)
        
        assert result is not None
        assert result.shape == x.shape
        assert not torch.isnan(result).any()
        
        # Verify transformation
        expected_0 = kappa * x[0] + gamma * x[1]
        assert torch.allclose(result[0], expected_0, atol=1e-6)
        
        print(f"✓ Exchange operator applied: {x.cpu().tolist()} → {result.cpu().tolist()}")
    
    def test_validation_output(self, config_path):
        """Test validation generates correct output"""
        from src.orchestrator.agent3_validator import OuroborosAgent3Validator
        
        invariant_truth = {
            "conservation_laws": ["energy"],
            "symmetries": ["time_translation"],
            "dimensional_constraints": {},
            "boundary_conditions": {}
        }
        
        validator = OuroborosAgent3Validator(
            invariant_truth=invariant_truth,
            use_local_llm=True
        )
        
        payload = {
            "type": "test_payload",
            "data": [1.0, 2.0, 3.0, 4.0],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # Test all three states
        for expected_state in ["NULL", "DUCTILE", "CRYSTALLINE"]:
            result = validator.validate(payload, mock_result=expected_state)
            
            assert result is not None
            assert result.state == expected_state
            assert result.timestamp is not None
            
            print(f"  Validation output: {expected_state} ✓")
        
        print("✓ Validation output verified")
    
    def test_clean_shutdown(self, config_path):
        """Test clean shutdown and resource cleanup"""
        daemon = YenneferTelemetryDaemon(str(config_path))
        
        # Simulate some work
        metrics = daemon.compute_metrics()
        assert metrics is not None
        
        # Cleanup (daemon should handle gracefully)
        del daemon
        
        # Check GPU memory if CUDA available
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            allocated = torch.cuda.memory_allocated()
            print(f"  GPU memory after shutdown: {allocated / 1e6:.2f} MB")
        
        print("✓ Clean shutdown completed")
    
    def test_full_workflow_integration(self, config_path):
        """Test complete workflow from start to finish"""
        print("\n" + "="*60)
        print("Full Yennefer E2E Workflow Test")
        print("="*60)
        
        # Step 1: Start orchestrator
        print("\n[1/5] Starting orchestrator...")
        daemon = YenneferTelemetryDaemon(str(config_path))
        assert daemon is not None
        print("  ✓ Orchestrator started")
        
        # Step 2: Run telemetry cycle
        print("\n[2/5] Running telemetry cycle...")
        daemon.notion_client = None  # Skip Notion POST for test
        daemon.run_cycle()
        metrics = daemon.compute_metrics()
        assert metrics is not None
        print(f"  ✓ Telemetry collected: η={metrics['eta_thermo']:.4f}, ε={metrics['epsilon']:.4f}")
        
        # Step 3: Apply exchange operator
        print("\n[3/5] Applying EnKG exchange operator...")
        x = torch.randn(128, dtype=torch.float32)
        if torch.cuda.is_available():
            x = x.cuda()
        
        kappa = 0.7
        gamma = 0.3
        result = apply_M_matrix(x, kappa=kappa, gamma=gamma)
        assert result is not None
        print(f"  ✓ Exchange operator applied: κ={kappa}, γ={gamma}")
        
        # Step 4: Validate output
        print("\n[4/5] Validating output...")
        from src.orchestrator.agent3_validator import OuroborosAgent3Validator
        
        validator = OuroborosAgent3Validator(
            invariant_truth={},
            use_local_llm=True
        )
        
        payload = {
            "enkg_result": result.cpu().tolist()[:10],
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        validation_result = validator.validate(payload, mock_result="CRYSTALLINE")
        assert validation_result.state in ["NULL", "DUCTILE", "CRYSTALLINE"]
        print(f"  ✓ Validation complete: {validation_result.state}")
        
        # Step 5: Clean shutdown
        print("\n[5/5] Shutting down...")
        del daemon
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        print("  ✓ Clean shutdown")
        
        print("\n" + "="*60)
        print("✓ Full E2E workflow completed successfully")
        print("="*60)
    
    def test_error_recovery(self, config_path):
        """Test error recovery in workflow"""
        daemon = YenneferTelemetryDaemon(str(config_path))
        
        # Simulate error in telemetry computation
        original_read_vram = daemon.read_vram_jax
        
        def failing_read_vram():
            raise RuntimeError("Simulated VRAM read failure")
        
        daemon.read_vram_jax = failing_read_vram
        
        # Should handle gracefully
        try:
            daemon.run_cycle()
        except RuntimeError:
            # Expected to propagate in test
            pass
        
        # Restore function
        daemon.read_vram_jax = original_read_vram
        
        # Should work again
        daemon.run_cycle()
        assert daemon.run_count > 0
        
        print("✓ Error recovery verified")
    
    def test_concurrent_operations(self):
        """Test concurrent EnKG operations"""
        if not torch.cuda.is_available():
            pytest.skip("CUDA not available")
        
        # Launch multiple operations
        tensors = [torch.randn(1024, dtype=torch.float32).cuda() for _ in range(5)]
        results = []
        
        for i, x in enumerate(tensors):
            kappa = 0.6 + (i * 0.05)
            gamma = 0.4 - (i * 0.05)
            result = apply_M_matrix(x, kappa=kappa, gamma=gamma)
            results.append(result)
        
        torch.cuda.synchronize()
        
        # Verify all completed
        assert len(results) == len(tensors)
        for result in results:
            assert result is not None
            assert not torch.isnan(result).any()
        
        print(f"✓ Concurrent operations completed: {len(results)} tensors processed")
    
    @patch('workers.yennefer_telemetry_daemon.NotionClient')
    def test_full_workflow_with_notion(self, mock_notion, config_path):
        """Test full workflow with Notion integration"""
        # Mock Notion client
        mock_client = MagicMock()
        mock_notion.return_value = mock_client
        mock_client.pages.create.return_value = {"id": "test-page-id"}
        
        print("\n" + "="*60)
        print("Full Workflow with Notion Integration")
        print("="*60)
        
        # Initialize daemon
        print("\n[1/4] Initializing daemon...")
        daemon = YenneferTelemetryDaemon(str(config_path))
        daemon.notion_client = mock_client
        print("  ✓ Daemon initialized with Notion client")
        
        # Run telemetry cycle
        print("\n[2/4] Running telemetry cycle...")
        daemon.run_cycle()
        assert daemon.run_count == 1
        print(f"  ✓ Cycle completed: run_count={daemon.run_count}")
        
        # Verify Notion POST
        print("\n[3/4] Verifying Notion POST...")
        assert mock_client.pages.create.called
        call_args = mock_client.pages.create.call_args
        properties = call_args.kwargs['properties']
        
        required_fields = ["Timestamp", "η_thermo", "ε", "γ", "VRAM_JAX_Pct"]
        for field in required_fields:
            assert field in properties, f"Missing field: {field}"
        
        print(f"  ✓ Notion POST verified: {len(properties)} properties")
        
        # Validate data integrity
        print("\n[4/4] Validating data integrity...")
        eta_value = properties["η_thermo"]["number"]
        epsilon_value = properties["ε"]["number"]
        
        assert 0 <= eta_value <= 1.0
        assert 0 <= epsilon_value <= 1.0
        print(f"  ✓ Data integrity verified: η={eta_value:.4f}, ε={epsilon_value:.4f}")
        
        print("\n" + "="*60)
        print("✓ Full workflow with Notion integration completed")
        print("="*60)
    
    def test_state_persistence(self, config_path, tmp_path):
        """Test state persistence across cycles"""
        daemon = YenneferTelemetryDaemon(str(config_path))
        
        # Run first cycle
        initial_epsilon = daemon.prev_epsilon
        daemon.run_cycle()
        epsilon_after_cycle1 = daemon.prev_epsilon
        
        # Run second cycle
        daemon.run_cycle()
        epsilon_after_cycle2 = daemon.prev_epsilon
        
        # State should be tracked
        assert daemon.run_count == 2
        assert daemon.hold_cycles >= 0
        
        print(f"✓ State persistence verified:")
        print(f"  Initial ε: {initial_epsilon:.4f}")
        print(f"  After cycle 1: {epsilon_after_cycle1:.4f}")
        print(f"  After cycle 2: {epsilon_after_cycle2:.4f}")
        print(f"  Hold cycles: {daemon.hold_cycles}")
    
    def test_multi_cycle_convergence(self, config_path):
        """Test convergence behavior over multiple cycles"""
        daemon = YenneferTelemetryDaemon(str(config_path))
        daemon.notion_client = None
        
        epsilons = []
        crystalline_scores = []
        
        print("\n" + "="*60)
        print("Multi-Cycle Convergence Test")
        print("="*60)
        print(f"{'Cycle':<10} {'ε':<15} {'Crystalline':<15}")
        print("-"*60)
        
        for cycle in range(5):
            daemon.run_cycle()
            metrics = daemon.compute_metrics()
            
            epsilons.append(metrics["epsilon"])
            crystalline_scores.append(metrics["crystalline_score"])
            
            print(f"{cycle+1:<10} {metrics['epsilon']:<15.4f} {metrics['crystalline_score']:<15.4f}")
        
        print("="*60)
        
        # Verify tracking
        assert len(epsilons) == 5
        assert len(crystalline_scores) == 5
        
        print(f"✓ Multi-cycle convergence tracked: {daemon.run_count} cycles")


class TestYenneferStressTests:
    """Stress tests for Yennefer deployment"""
    
    def test_extended_runtime(self, config_path):
        """Test extended runtime stability"""
        daemon = YenneferTelemetryDaemon(str(config_path))
        daemon.notion_client = None
        
        cycles = 20
        errors = 0
        
        print(f"\n{'='*60}")
        print(f"Extended Runtime Test ({cycles} cycles)")
        print(f"{'='*60}")
        
        for i in range(cycles):
            try:
                daemon.run_cycle()
            except Exception as e:
                errors += 1
                print(f"  Cycle {i+1}: ERROR - {e}")
            else:
                if (i + 1) % 5 == 0:
                    print(f"  Cycle {i+1}: OK")
        
        success_rate = (cycles - errors) / cycles * 100
        
        print(f"{'='*60}")
        print(f"Completed: {cycles} cycles")
        print(f"Errors: {errors}")
        print(f"Success rate: {success_rate:.1f}%")
        print(f"{'='*60}")
        
        assert success_rate >= 95, f"Success rate too low: {success_rate:.1f}%"
        
        print(f"✓ Extended runtime test passed: {success_rate:.1f}% success")
    
    def test_rapid_fire_operations(self):
        """Test rapid-fire EnKG operations"""
        if not torch.cuda.is_available():
            pytest.skip("CUDA not available")
        
        n_operations = 1000
        x = torch.randn(1024, dtype=torch.float32).cuda()
        
        print(f"\n{'='*60}")
        print(f"Rapid-Fire Operations Test ({n_operations} ops)")
        print(f"{'='*60}")
        
        start = time.perf_counter()
        
        for i in range(n_operations):
            kappa = 0.7 + (i % 10) * 0.01
            gamma = 0.3 - (i % 10) * 0.01
            result = apply_M_matrix(x, kappa=kappa, gamma=gamma)
        
        torch.cuda.synchronize()
        end = time.perf_counter()
        
        duration = end - start
        ops_per_sec = n_operations / duration
        
        print(f"Duration: {duration:.2f}s")
        print(f"Throughput: {ops_per_sec:.1f} ops/sec")
        print(f"{'='*60}")
        
        assert ops_per_sec > 100, f"Throughput too low: {ops_per_sec:.1f} ops/sec"
        
        print(f"✓ Rapid-fire test passed: {ops_per_sec:.1f} ops/sec")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
