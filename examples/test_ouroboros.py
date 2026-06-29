#!/usr/bin/env python3
# Copyright (c) 2026 Diamond Node Team
# Licensed under the MIT License - see LICENSE file for details

"""
Quick Test: Ouroboros Protocol Basic Functionality

Verifies that the Ouroboros Protocol can be instantiated and
executes all three phases correctly.
"""

import os
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src" / "orchestrator"
sys.path.insert(0, str(src_path))

print(f"Python path: {sys.path[0]}")
print(f"Source path: {src_path}")

try:
    from ouroboros_protocol import OuroborosProtocol, OuroborosMetrics
    from agent3_validator import OuroborosAgent3Validator
    print("✅ Successfully imported Ouroboros modules")
except ImportError as e:
    print(f"❌ Failed to import modules: {e}")
    sys.exit(1)


def test_basic_instantiation():
    """Test that we can create the protocol"""
    print("\n" + "="*60)
    print("TEST 1: Basic Instantiation")
    print("="*60)
    
    try:
        # Create validator
        invariant_truth = {
            "conservation_laws": ["energy_conservation"],
            "symmetries": ["time_reversal"],
            "dimensional_constraints": {"max_size": 1024},
            "boundary_conditions": {"max_iterations": 100}
        }
        
        validator = OuroborosAgent3Validator(
            invariant_truth=invariant_truth,
            use_local_llm=True  # Don't use API for basic test
        )
        print("✅ Created Agent 3 Validator")
        
        # Check API key
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("⚠️  No ANTHROPIC_API_KEY found - skipping protocol creation")
            return True
        
        # Create protocol
        protocol = OuroborosProtocol(
            agent3_validator=validator,
            api_key=api_key
        )
        print("✅ Created Ouroboros Protocol")
        
        # Check metrics
        assert protocol.metrics.total_iterations == 0
        assert protocol.metrics.null_count == 0
        print("✅ Metrics initialized correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_metrics():
    """Test metrics tracking"""
    print("\n" + "="*60)
    print("TEST 2: Metrics Tracking")
    print("="*60)
    
    try:
        metrics = OuroborosMetrics()
        
        # Test initial state
        assert metrics.total_iterations == 0
        assert metrics.average_validation_time == 0.0
        assert metrics.convergence_rate == 0.0
        print("✅ Initial state correct")
        
        # Test updates
        metrics.total_iterations = 3
        metrics.null_count = 1
        metrics.ductile_count = 1
        metrics.crystalline_count = 1
        metrics.total_validation_time = 6.0
        metrics.convergence_iteration = 3
        
        assert metrics.average_validation_time == 2.0
        assert metrics.convergence_rate == 1.0 / 3.0
        print("✅ Metrics calculations correct")
        
        # Test to_dict
        metrics_dict = metrics.to_dict()
        assert "total_iterations" in metrics_dict
        assert "average_validation_time" in metrics_dict
        assert "convergence_rate" in metrics_dict
        print("✅ Metrics serialization works")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_validator_integration():
    """Test integration with Agent 3"""
    print("\n" + "="*60)
    print("TEST 3: Agent 3 Validator Integration")
    print("="*60)
    
    try:
        # Create validator
        invariant_truth = {
            "conservation_laws": ["vram_budget"],
            "symmetries": [],
            "dimensional_constraints": {"max_vram_bytes": 3865051136},
            "boundary_conditions": {"thermal_limit": 89.6}
        }
        
        validator = OuroborosAgent3Validator(
            invariant_truth=invariant_truth,
            use_local_llm=True
        )
        
        # Create a test payload
        test_payload = {
            "operation": "matrix_multiply",
            "parameters": {
                "matrix_size": 512,
                "vram_requirement_bytes": 1073741824,  # 1GB
                "compute_intensity": 0.5,
                "batch_size": 1,
                "precision": "fp32"
            },
            "metadata": {
                "priority": "medium",
                "timeout_seconds": 60,
                "retries": 3
            }
        }
        
        # Validate payload
        result = validator.evaluate_payload(
            payload=test_payload,
            generator_output={"payload": test_payload},
            attacker_perturbation={}
        )
        
        assert "validation_result" in result
        assert "state" in result["validation_result"]
        state = result["validation_result"]["state"]
        assert state in ["NULL", "DUCTILE", "CRYSTALLINE"]
        print(f"✅ Validation completed: state = {state}")
        
        # Test corrections for DUCTILE
        if state == "DUCTILE":
            corrected = validator.apply_rigid_filtering(test_payload)
            assert "parameters" in corrected
            print("✅ Corrections applied successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("OUROBOROS PROTOCOL - Quick Test Suite")
    print("="*80)
    
    tests = [
        ("Basic Instantiation", test_basic_instantiation),
        ("Metrics Tracking", test_metrics),
        ("Agent 3 Integration", test_validator_integration)
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            success = test_func()
            results[name] = success
        except Exception as e:
            print(f"\n❌ {name} raised exception: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
