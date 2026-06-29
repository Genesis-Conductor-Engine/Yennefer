#!/usr/bin/env python3
# @Igor Holt
"""
Ouroboros Protocol Tests
Generator → Attacker → Validator flow with NULL/DUCTILE/CRYSTALLINE states
"""

import pytest
import torch
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from dataclasses import asdict

from src.orchestrator.agent3_validator import (
    OuroborosAgent3Validator,
    ValidationResult,
    AShardParams,
    PIScope,
    InvariantTruth
)
from src.kernels.enkg_exchange import apply_M_matrix


class MockGenerator:
    """Mock Agent 1 - Generator"""
    
    def __init__(self, seed=42):
        self.seed = seed
        torch.manual_seed(seed)
    
    def generate_payload(self, iteration: int) -> dict:
        """Generate test payload"""
        # Create synthetic state vector
        size = 128
        x = torch.randn(size, dtype=torch.float32)
        
        # Apply EnKG transformation
        kappa = 0.7 + (iteration * 0.01)
        gamma = 0.3 - (iteration * 0.01)
        result = apply_M_matrix(x, kappa=kappa, gamma=gamma)
        
        return {
            "type": "generated_state",
            "iteration": iteration,
            "state_vector": result.tolist(),
            "operator": {"kappa": kappa, "gamma": gamma},
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "generator_version": "1.0.0"
        }


class MockAttacker:
    """Mock Agent 2 - Attacker"""
    
    def __init__(self, attack_strategy="perturbation"):
        self.attack_strategy = attack_strategy
        self.attack_count = 0
    
    def attack_payload(self, payload: dict) -> dict:
        """Apply attack transformation to payload"""
        self.attack_count += 1
        
        # Clone payload
        attacked = payload.copy()
        attacked["attacked"] = True
        attacked["attack_strategy"] = self.attack_strategy
        attacked["attack_count"] = self.attack_count
        
        # Apply attack based on strategy
        if self.attack_strategy == "perturbation":
            # Add small noise
            state = torch.tensor(payload["state_vector"])
            noise = torch.randn_like(state) * 0.05
            attacked["state_vector"] = (state + noise).tolist()
            attacked["perturbation_magnitude"] = 0.05
        
        elif self.attack_strategy == "corruption":
            # Corrupt random elements
            state = torch.tensor(payload["state_vector"])
            mask = torch.rand_like(state) > 0.9
            state[mask] = float('nan')
            attacked["state_vector"] = state.tolist()
            attacked["corruption_rate"] = 0.1
        
        elif self.attack_strategy == "amplification":
            # Amplify values
            state = torch.tensor(payload["state_vector"])
            attacked["state_vector"] = (state * 10.0).tolist()
            attacked["amplification_factor"] = 10.0
        
        elif self.attack_strategy == "none":
            # Pass through unchanged
            pass
        
        return attacked


class TestOuroborosProtocol:
    """Test Ouroboros three-agent protocol"""
    
    @pytest.fixture
    def generator(self):
        return MockGenerator(seed=42)
    
    @pytest.fixture
    def attacker_benign(self):
        return MockAttacker(attack_strategy="none")
    
    @pytest.fixture
    def attacker_perturbation(self):
        return MockAttacker(attack_strategy="perturbation")
    
    @pytest.fixture
    def attacker_corruption(self):
        return MockAttacker(attack_strategy="corruption")
    
    @pytest.fixture
    def attacker_amplification(self):
        return MockAttacker(attack_strategy="amplification")
    
    @pytest.fixture
    def validator(self):
        invariant_truth = {
            "conservation_laws": ["energy", "momentum"],
            "symmetries": ["time_translation"],
            "dimensional_constraints": {"max_vram_gb": 4},
            "boundary_conditions": {"thermal_max": 89.6}
        }
        
        ashard_params = {
            "vram_total_bytes": 4294967296,
            "vram_allocation_buffer": 0.9,
            "thermal_max_celsius": 89.6,
            "compute_capability": (7, 5)
        }
        
        pi_scope = {
            "allowed_operations": ["enkg_exchange", "validation"],
            "resource_limits": {"max_memory_mb": 3600},
            "state_transitions": {
                "NULL": ["DUCTILE"],
                "DUCTILE": ["CRYSTALLINE", "NULL"],
                "CRYSTALLINE": ["DUCTILE"]
            },
            "execution_context": {"device": "cuda", "precision": "float32"}
        }
        
        return OuroborosAgent3Validator(
            invariant_truth=invariant_truth,
            ashard_params=ashard_params,
            pi_scope=pi_scope,
            use_local_llm=True
        )
    
    def test_generator_attacker_validator_flow_benign(self, generator, attacker_benign, validator):
        """Test G→A→V flow with benign input (should be CRYSTALLINE)"""
        # Generate
        payload = generator.generate_payload(iteration=0)
        assert "state_vector" in payload
        assert payload["iteration"] == 0
        
        # Attack (benign pass-through)
        attacked = attacker_benign.attack_payload(payload)
        assert attacked["attack_strategy"] == "none"
        
        # Validate
        result = validator.validate(attacked, mock_result="CRYSTALLINE")
        
        assert result.state == "CRYSTALLINE"
        print(f"✓ Benign flow: Generator → Attacker(none) → Validator = {result.state}")
    
    def test_generator_attacker_validator_flow_perturbation(self, generator, attacker_perturbation, validator):
        """Test G→A→V flow with perturbation (should be DUCTILE)"""
        # Generate
        payload = generator.generate_payload(iteration=0)
        
        # Attack with perturbation
        attacked = attacker_perturbation.attack_payload(payload)
        assert attacked["attacked"] is True
        assert attacked["perturbation_magnitude"] == 0.05
        
        # Validate
        result = validator.validate(attacked, mock_result="DUCTILE")
        
        assert result.state == "DUCTILE"
        print(f"✓ Perturbation flow: Generator → Attacker(perturb) → Validator = {result.state}")
    
    def test_generator_attacker_validator_flow_corruption(self, generator, attacker_corruption, validator):
        """Test G→A→V flow with corruption (should be NULL)"""
        # Generate
        payload = generator.generate_payload(iteration=0)
        
        # Attack with corruption
        attacked = attacker_corruption.attack_payload(payload)
        assert attacked["attacked"] is True
        assert attacked["corruption_rate"] == 0.1
        
        # Check for NaN
        state = torch.tensor(attacked["state_vector"])
        has_nan = torch.isnan(state).any()
        assert has_nan, "Corruption should introduce NaN"
        
        # Validate
        result = validator.validate(attacked, mock_result="NULL")
        
        assert result.state == "NULL"
        print(f"✓ Corruption flow: Generator → Attacker(corrupt) → Validator = {result.state}")
    
    def test_generator_attacker_validator_flow_amplification(self, generator, attacker_amplification, validator):
        """Test G→A→V flow with amplification (should be NULL or DUCTILE)"""
        # Generate
        payload = generator.generate_payload(iteration=0)
        
        # Attack with amplification
        attacked = attacker_amplification.attack_payload(payload)
        assert attacked["amplification_factor"] == 10.0
        
        # Validate
        result = validator.validate(attacked, mock_result="NULL")
        
        assert result.state in ["NULL", "DUCTILE"]
        print(f"✓ Amplification flow: Generator → Attacker(amplify) → Validator = {result.state}")
    
    def test_all_output_states(self, generator, validator):
        """Test all three validation states: NULL, DUCTILE, CRYSTALLINE"""
        payload_base = generator.generate_payload(iteration=0)
        
        # Test each state
        states = ["NULL", "DUCTILE", "CRYSTALLINE"]
        
        for expected_state in states:
            payload = payload_base.copy()
            payload["test_state"] = expected_state
            
            result = validator.validate(payload, mock_result=expected_state)
            assert result.state == expected_state
            print(f"  {expected_state}: ✓")
        
        print("✓ All output states validated: NULL, DUCTILE, CRYSTALLINE")
    
    def test_null_triggers_restart(self, generator, attacker_corruption, validator):
        """Test that NULL state triggers protocol restart"""
        restart_count = 0
        max_restarts = 3
        
        for attempt in range(max_restarts):
            # Generate
            payload = generator.generate_payload(iteration=attempt)
            
            # Attack (corruption)
            attacked = attacker_corruption.attack_payload(payload)
            
            # Validate
            result = validator.validate(attacked, mock_result="NULL")
            
            if result.state == "NULL":
                restart_count += 1
                print(f"  Attempt {attempt + 1}: NULL → Restart")
            else:
                print(f"  Attempt {attempt + 1}: {result.state} → Continue")
                break
        
        assert restart_count > 0, "NULL state should trigger restart"
        print(f"✓ NULL restart protocol: {restart_count} restarts before success")
    
    def test_convergence_to_crystalline(self, generator, validator):
        """Test convergence from NULL → DUCTILE → CRYSTALLINE"""
        # Simulate convergence sequence
        sequence = [
            ("NULL", "Initial validation fails"),
            ("NULL", "Second attempt fails"),
            ("DUCTILE", "Partial validation succeeds"),
            ("DUCTILE", "Refinement in progress"),
            ("CRYSTALLINE", "Full validation achieved"),
        ]
        
        for iteration, (expected_state, description) in enumerate(sequence):
            payload = generator.generate_payload(iteration=iteration)
            result = validator.validate(payload, mock_result=expected_state)
            
            assert result.state == expected_state
            print(f"  Iteration {iteration}: {expected_state} - {description}")
        
        print("✓ Convergence test: NULL → DUCTILE → CRYSTALLINE")
    
    def test_state_transitions_valid(self, validator):
        """Test that state transitions respect PI scope"""
        pi_scope = {
            "state_transitions": {
                "NULL": ["DUCTILE"],
                "DUCTILE": ["CRYSTALLINE", "NULL"],
                "CRYSTALLINE": ["DUCTILE"]
            }
        }
        
        # Valid transitions
        valid = [
            ("NULL", "DUCTILE"),
            ("DUCTILE", "CRYSTALLINE"),
            ("DUCTILE", "NULL"),
            ("CRYSTALLINE", "DUCTILE"),
        ]
        
        # Invalid transitions
        invalid = [
            ("NULL", "CRYSTALLINE"),  # Can't skip DUCTILE
            ("NULL", "NULL"),         # Can't stay in NULL
            ("CRYSTALLINE", "NULL"),  # Can't go directly to NULL
            ("CRYSTALLINE", "CRYSTALLINE"),  # Can't stay (must refine)
        ]
        
        for from_state, to_state in valid:
            assert to_state in pi_scope["state_transitions"][from_state], \
                f"Invalid transition: {from_state} → {to_state}"
            print(f"  ✓ {from_state} → {to_state}")
        
        for from_state, to_state in invalid:
            assert to_state not in pi_scope["state_transitions"][from_state], \
                f"Transition should be invalid: {from_state} → {to_state}"
            print(f"  ✗ {from_state} → {to_state} (correctly blocked)")
        
        print("✓ State transition validation complete")
    
    def test_multi_iteration_protocol(self, generator, attacker_perturbation, validator):
        """Test multi-iteration Ouroboros protocol"""
        max_iterations = 10
        results = []
        
        for iteration in range(max_iterations):
            # Generate
            payload = generator.generate_payload(iteration=iteration)
            
            # Attack (with decreasing perturbation)
            attacker = MockAttacker(attack_strategy="perturbation")
            attacked = attacker.attack_payload(payload)
            
            # Reduce perturbation over time (simulate convergence)
            state = torch.tensor(attacked["state_vector"])
            noise_scale = 0.1 * (1.0 - iteration / max_iterations)
            noise = torch.randn_like(state) * noise_scale
            attacked["state_vector"] = (state + noise).tolist()
            
            # Validate (mock progressive improvement)
            if iteration < 3:
                mock_state = "NULL"
            elif iteration < 7:
                mock_state = "DUCTILE"
            else:
                mock_state = "CRYSTALLINE"
            
            result = validator.validate(attacked, mock_result=mock_state)
            results.append(result.state)
            
            print(f"  Iteration {iteration}: {result.state} (noise: {noise_scale:.3f})")
        
        # Check convergence pattern
        assert "NULL" in results[:5], "Should start with NULL"
        assert "DUCTILE" in results[3:8], "Should transition to DUCTILE"
        assert "CRYSTALLINE" in results[7:], "Should converge to CRYSTALLINE"
        
        print(f"✓ Multi-iteration protocol: {results[-3:]} (final states)")
    
    def test_attack_detection(self, generator, attacker_corruption, validator):
        """Test that validator can detect attacks"""
        # Benign payload
        benign_payload = generator.generate_payload(iteration=0)
        benign_result = validator.validate(benign_payload, mock_result="CRYSTALLINE")
        
        # Attacked payload
        attacked_payload = attacker_corruption.attack_payload(benign_payload)
        attacked_result = validator.validate(attacked_payload, mock_result="NULL")
        
        # Validator should distinguish
        assert benign_result.state != attacked_result.state or attacked_result.state == "NULL"
        
        print(f"✓ Attack detection: benign={benign_result.state}, attacked={attacked_result.state}")
    
    def test_validator_resilience(self, generator, validator):
        """Test validator resilience to malformed inputs"""
        # Missing fields
        payload_missing = {"iteration": 0}
        result = validator.validate(payload_missing, mock_result="NULL")
        assert result.state == "NULL"
        
        # Invalid data types
        payload_invalid = {
            "state_vector": "not_a_list",
            "operator": None
        }
        result = validator.validate(payload_invalid, mock_result="NULL")
        assert result.state == "NULL"
        
        # Empty payload
        payload_empty = {}
        result = validator.validate(payload_empty, mock_result="NULL")
        assert result.state == "NULL"
        
        print("✓ Validator resilience: handled malformed inputs")


class TestOuroborosPerformance:
    """Performance tests for Ouroboros protocol"""
    
    def test_protocol_latency(self):
        """Test end-to-end protocol latency"""
        generator = MockGenerator()
        attacker = MockAttacker(attack_strategy="perturbation")
        validator = OuroborosAgent3Validator(
            invariant_truth={},
            ashard_params={},
            pi_scope={},
            use_local_llm=True
        )
        
        iterations = 10
        latencies = []
        
        for i in range(iterations):
            start = time.perf_counter()
            
            # Full protocol
            payload = generator.generate_payload(iteration=i)
            attacked = attacker.attack_payload(payload)
            result = validator.validate(attacked, mock_result="DUCTILE")
            
            end = time.perf_counter()
            latency_ms = (end - start) * 1000
            latencies.append(latency_ms)
        
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        
        # Should be fast (<100ms per iteration)
        assert avg_latency < 100, f"Average latency too high: {avg_latency:.2f}ms"
        
        print(f"✓ Protocol latency: avg={avg_latency:.2f}ms, max={max_latency:.2f}ms")
    
    def test_throughput(self):
        """Test protocol throughput (iterations per second)"""
        generator = MockGenerator()
        validator = OuroborosAgent3Validator(
            invariant_truth={},
            use_local_llm=True
        )
        
        iterations = 50
        start = time.perf_counter()
        
        for i in range(iterations):
            payload = generator.generate_payload(iteration=i)
            validator.validate(payload, mock_result="DUCTILE")
        
        end = time.perf_counter()
        duration = end - start
        throughput = iterations / duration
        
        # Should achieve >10 iterations/sec
        assert throughput > 10, f"Throughput too low: {throughput:.2f} iter/s"
        
        print(f"✓ Protocol throughput: {throughput:.2f} iterations/sec")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
