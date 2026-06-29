#!/usr/bin/env python3
# Copyright (c) 2026 Diamond Node Team
# Licensed under the MIT License - see LICENSE file for details

"""
Test suite for Agent 3 - Validator (Ouroboros Protocol)

Tests all three output states: NULL, DUCTILE, CRYSTALLINE
Validates topological, hardware, and operational authority checks
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orchestrator.agent3_validator import (
    OuroborosAgent3Validator,
    validate_payload,
    InvariantTruth,
    AShardParams,
    PIScope
)


def print_test_header(test_name: str):
    """Print formatted test header"""
    print("\n" + "=" * 70)
    print(f"TEST: {test_name}")
    print("=" * 70)


def print_result(result: dict):
    """Print validation result in readable format"""
    state = result['validation_result']['state']
    summary = result['validation_result']['evaluation_summary']
    recommendations = result['validation_result']['recommendations']
    
    print(f"\n📊 VALIDATION RESULT:")
    print(f"   State: {state}")
    print(f"   Topological Score: {summary['topological_score']:.2f}")
    print(f"   Hardware Compliance: {summary['hardware_compliance']}")
    print(f"   PI Validity: {summary['pi_validity']}")
    print(f"   Invariant Violations: {len(summary['invariant_violations'])}")
    
    if summary['corrections_required']:
        print(f"\n   Corrections Required:")
        for correction in summary['corrections_required']:
            print(f"      - {correction.get('type', 'unknown')}: {correction.get('action', 'N/A')}")
    
    print(f"\n   Recommendation: {recommendations['action']}")
    print(f"   Rationale: {recommendations['rationale']}")


def test_crystalline_state():
    """Test 1: Perfect payload should produce CRYSTALLINE state"""
    print_test_header("CRYSTALLINE State - Perfect Payload")
    
    invariant_truth = {
        "conservation_laws": ["energy", "information"],
        "symmetries": ["time_reversal"],
        "dimensional_constraints": {
            "input": "vector",
            "output": "vector",
            "matrix": "matrix"
        },
        "boundary_conditions": {"type": "periodic"}
    }
    
    payload = {
        "operation": "compute",
        "parameters": {
            "input": [1.0, 2.0, 3.0, 4.0],
            "output": [1.05, 2.05, 3.05, 4.05],
            "energy_in": 100.0,
            "energy_out": 100.0,
            "input_entropy": 2.5,
            "output_entropy": 2.6,
            "matrix_size": 512,
            "compute_intensity": 0.6,
            "vram_requirement_bytes": 1073741824,  # 1GB
            "compute_capability": (7, 0)
        },
        "metadata": {
            "state": "running",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0"
        }
    }
    
    validator = OuroborosAgent3Validator(invariant_truth=invariant_truth)
    result = validator.evaluate_payload(
        payload=payload,
        generator_output={"source": "agent1"},
        attacker_perturbation={"noise": 0.01}
    )
    
    print_result(result)
    
    assert result['validation_result']['state'] == 'CRYSTALLINE', \
        f"Expected CRYSTALLINE, got {result['validation_result']['state']}"
    
    print("\n✅ Test PASSED: CRYSTALLINE state correctly identified")
    return result


def test_null_state_vram_overflow():
    """Test 2: VRAM overflow should produce NULL state"""
    print_test_header("NULL State - VRAM Overflow")
    
    invariant_truth = {
        "conservation_laws": ["energy"],
        "symmetries": [],
        "dimensional_constraints": {},
        "boundary_conditions": {}
    }
    
    payload = {
        "operation": "compute",
        "parameters": {
            "matrix_size": 50000,  # Would require ~10GB VRAM
            "compute_intensity": 0.95,
            "vram_requirement_bytes": 10737418240  # 10GB - exceeds GTX 1650
        },
        "metadata": {
            "state": "running"
        }
    }
    
    validator = OuroborosAgent3Validator(invariant_truth=invariant_truth)
    result = validator.evaluate_payload(
        payload=payload,
        generator_output={},
        attacker_perturbation={}
    )
    
    print_result(result)
    
    assert result['validation_result']['state'] == 'NULL', \
        f"Expected NULL, got {result['validation_result']['state']}"
    
    assert validator.restart_count == 1, \
        f"Expected restart_count=1, got {validator.restart_count}"
    
    print("\n✅ Test PASSED: NULL state correctly triggered for VRAM overflow")
    return result


def test_null_state_thermal_violation():
    """Test 3: Thermal violation should produce NULL state"""
    print_test_header("NULL State - Thermal Violation")
    
    invariant_truth = {
        "conservation_laws": [],
        "symmetries": [],
        "dimensional_constraints": {},
        "boundary_conditions": {}
    }
    
    payload = {
        "operation": "compute",
        "parameters": {
            "matrix_size": 1024,
            "compute_intensity": 1.0,  # 100% intensity -> thermal violation
            "vram_requirement_bytes": 2147483648  # 2GB - within limits
        },
        "metadata": {
            "state": "running"
        }
    }
    
    validator = OuroborosAgent3Validator(invariant_truth=invariant_truth)
    result = validator.evaluate_payload(
        payload=payload,
        generator_output={},
        attacker_perturbation={}
    )
    
    print_result(result)
    
    assert result['validation_result']['state'] == 'NULL', \
        f"Expected NULL, got {result['validation_result']['state']}"
    
    print("\n✅ Test PASSED: NULL state correctly triggered for thermal violation")
    return result


def test_null_state_invariant_failure():
    """Test 4: Low invariant score should produce NULL state"""
    print_test_header("NULL State - Invariant Violation")
    
    invariant_truth = {
        "conservation_laws": ["energy", "momentum", "information"],
        "symmetries": ["time_reversal"],
        "dimensional_constraints": {
            "input": "vector",
            "output": "scalar"  # Mismatch!
        },
        "boundary_conditions": {}
    }
    
    payload = {
        "operation": "compute",
        "parameters": {
            "input": [1.0, 2.0, 3.0],
            "output": [1.0, 2.0, 3.0],  # Should be scalar but is vector
            "energy_in": 100.0,
            "energy_out": 50.0,  # Energy not conserved!
            "input_entropy": 3.0,
            "output_entropy": 1.0,  # Information loss!
            "matrix_size": 256,
            "compute_intensity": 0.3,
            "vram_requirement_bytes": 536870912  # 512MB
        },
        "metadata": {
            "state": "running"
        }
    }
    
    validator = OuroborosAgent3Validator(invariant_truth=invariant_truth)
    result = validator.evaluate_payload(
        payload=payload,
        generator_output={},
        attacker_perturbation={}
    )
    
    print_result(result)
    
    assert result['validation_result']['state'] == 'NULL', \
        f"Expected NULL, got {result['validation_result']['state']}"
    
    assert len(result['validation_result']['evaluation_summary']['invariant_violations']) > 0, \
        "Expected invariant violations to be recorded"
    
    print("\n✅ Test PASSED: NULL state correctly triggered for invariant violations")
    return result


def test_ductile_state():
    """Test 5: Acceptable with corrections should produce DUCTILE state"""
    print_test_header("DUCTILE State - Acceptable with Corrections")
    
    invariant_truth = {
        "conservation_laws": ["energy"],
        "symmetries": [],
        "dimensional_constraints": {
            "input": "vector",
            "output": "vector"
        },
        "boundary_conditions": {}
    }
    
    payload = {
        "operation": "compute",
        "parameters": {
            "input": [1.0, 2.0, 3.0],
            "output": [1.1, 2.1, 3.1],
            "energy_in": 100.0,
            "energy_out": 100.0,
            "matrix_size": 2048,
            "compute_intensity": 0.8,  # High but not critical
            "vram_requirement_bytes": 3221225472  # 3GB - tight but fits
        },
        "metadata": {
            "state": "running"
        }
    }
    
    validator = OuroborosAgent3Validator(invariant_truth=invariant_truth)
    result = validator.evaluate_payload(
        payload=payload,
        generator_output={},
        attacker_perturbation={"perturbation_strength": 0.05}
    )
    
    print_result(result)
    
    assert result['validation_result']['state'] == 'DUCTILE', \
        f"Expected DUCTILE, got {result['validation_result']['state']}"
    
    assert len(result['validation_result']['evaluation_summary']['corrections_required']) > 0, \
        "Expected corrections to be required for DUCTILE state"
    
    print("\n✅ Test PASSED: DUCTILE state correctly identified with corrections")
    return result


def test_rigid_filtering():
    """Test 6: Rigid filtering should correct DUCTILE payloads"""
    print_test_header("Rigid Filtering - Payload Correction")
    
    invariant_truth = {
        "conservation_laws": [],
        "symmetries": [],
        "dimensional_constraints": {},
        "boundary_conditions": {}
    }
    
    payload = {
        "operation": "compute",
        "parameters": {
            "matrix_size": 10000,  # Too large
            "compute_intensity": 0.95,  # Too high
            "vram_requirement_bytes": 5368709120  # 5GB - too much
        },
        "metadata": {
            "state": "running"
        }
    }
    
    validator = OuroborosAgent3Validator(invariant_truth=invariant_truth)
    
    print("\n📋 Original payload parameters:")
    print(f"   Matrix size: {payload['parameters']['matrix_size']}")
    print(f"   Compute intensity: {payload['parameters']['compute_intensity']}")
    print(f"   VRAM requirement: {payload['parameters']['vram_requirement_bytes'] / 1e9:.1f} GB")
    
    corrected = validator.apply_rigid_filtering(payload)
    
    print("\n📋 Corrected payload parameters:")
    print(f"   Matrix size: {corrected['parameters']['matrix_size']}")
    print(f"   Compute intensity: {corrected['parameters']['compute_intensity']}")
    print(f"   VRAM requirement: {corrected['parameters']['vram_requirement_bytes'] / 1e9:.1f} GB")
    
    assert corrected['parameters']['matrix_size'] < payload['parameters']['matrix_size'], \
        "Matrix size should be reduced"
    
    assert corrected['parameters']['compute_intensity'] <= 0.85, \
        "Compute intensity should be capped at 0.85"
    
    assert corrected['parameters']['vram_requirement_bytes'] <= validator.ashard_params.vram_total_bytes * 0.9, \
        "VRAM should be within allocation buffer"
    
    print("\n✅ Test PASSED: Rigid filtering correctly applied corrections")
    return corrected


def test_pi_scope_violation():
    """Test 7: PI scope violation should produce NULL state"""
    print_test_header("NULL State - PI Scope Violation")
    
    invariant_truth = {
        "conservation_laws": [],
        "symmetries": [],
        "dimensional_constraints": {},
        "boundary_conditions": {}
    }
    
    pi_scope = {
        "allowed_operations": ["read", "compute"],  # "write" not allowed
        "resource_limits": {"max_threads": 512, "max_memory_mb": 2048},
        "state_transitions": {"valid_states": ["init", "running", "complete"]},
        "execution_context": {"sandbox": True}
    }
    
    payload = {
        "operation": "write",  # Forbidden operation!
        "parameters": {
            "matrix_size": 256,
            "compute_intensity": 0.3,
            "vram_requirement_bytes": 536870912,  # 512MB
            "max_threads": 1024  # Exceeds limit!
        },
        "metadata": {
            "state": "unauthorized"  # Invalid state!
        }
    }
    
    validator = OuroborosAgent3Validator(
        invariant_truth=invariant_truth,
        pi_scope=pi_scope
    )
    
    result = validator.evaluate_payload(
        payload=payload,
        generator_output={},
        attacker_perturbation={}
    )
    
    print_result(result)
    
    assert result['validation_result']['state'] == 'NULL', \
        f"Expected NULL, got {result['validation_result']['state']}"
    
    pi_violations = result['validation_result']['detailed_analysis']['operational_authority']['permission_violations']
    assert len(pi_violations) > 0, "Expected PI violations to be recorded"
    
    print(f"\n   PI Violations detected: {len(pi_violations)}")
    for violation in pi_violations:
        print(f"      - {violation}")
    
    print("\n✅ Test PASSED: NULL state correctly triggered for PI scope violation")
    return result


def test_convenience_function():
    """Test 8: Convenience function should work correctly"""
    print_test_header("Convenience Function - validate_payload()")
    
    invariant_truth = {
        "conservation_laws": ["energy"],
        "symmetries": [],
        "dimensional_constraints": {},
        "boundary_conditions": {}
    }
    
    payload = {
        "operation": "compute",
        "parameters": {
            "energy_in": 50.0,
            "energy_out": 50.0,
            "matrix_size": 256,
            "compute_intensity": 0.4,
            "vram_requirement_bytes": 268435456  # 256MB
        },
        "metadata": {
            "state": "running"
        }
    }
    
    result = validate_payload(
        payload=payload,
        invariant_truth=invariant_truth
    )
    
    print_result(result)
    
    assert 'validation_result' in result, "Result should contain validation_result"
    assert result['validation_result']['state'] in ['NULL', 'DUCTILE', 'CRYSTALLINE'], \
        "State should be one of the three valid states"
    
    print("\n✅ Test PASSED: Convenience function works correctly")
    return result


def test_seismic_scan():
    """Test 9: Seismic scan should detect perturbations"""
    print_test_header("Seismic Scan - Perturbation Detection")
    
    invariant_truth = {
        "conservation_laws": [],
        "symmetries": [],
        "dimensional_constraints": {},
        "boundary_conditions": {}
    }
    
    payload = {
        "operation": "compute",
        "parameters": {
            "matrix_size": 256,
            "compute_intensity": 0.5,
            "vram_requirement_bytes": 268435456
        },
        "metadata": {
            "state": "running"
        }
    }
    
    generator_output = {"original_matrix_size": 256}
    attacker_perturbation = {
        "noise_x": 0.1,
        "noise_y": 0.2,
        "noise_z": 0.15
    }
    
    validator = OuroborosAgent3Validator(invariant_truth=invariant_truth)
    result = validator.evaluate_payload(
        payload=payload,
        generator_output=generator_output,
        attacker_perturbation=attacker_perturbation
    )
    
    seismic = result['validation_result']['detailed_analysis']['seismic_scan']
    
    print(f"\n📊 Seismic Scan Results:")
    print(f"   Topology Hash: {seismic['topology_hash'][:16]}...")
    print(f"   Perturbation Magnitude: {seismic['perturbation_magnitude']:.4f}")
    print(f"   Structural Integrity: {seismic['structural_integrity']}")
    
    assert seismic['perturbation_magnitude'] > 0, "Should detect perturbation"
    assert seismic['structural_integrity'], "Structure should be valid"
    
    print("\n✅ Test PASSED: Seismic scan correctly detects perturbations")
    return result


def run_all_tests():
    """Run all test cases"""
    print("\n" + "🚀" * 35)
    print("OUROBOROS PROTOCOL - AGENT 3 VALIDATOR TEST SUITE")
    print("🚀" * 35)
    
    tests = [
        ("CRYSTALLINE State", test_crystalline_state),
        ("NULL State (VRAM Overflow)", test_null_state_vram_overflow),
        ("NULL State (Thermal Violation)", test_null_state_thermal_violation),
        ("NULL State (Invariant Failure)", test_null_state_invariant_failure),
        ("DUCTILE State", test_ductile_state),
        ("Rigid Filtering", test_rigid_filtering),
        ("PI Scope Violation", test_pi_scope_violation),
        ("Convenience Function", test_convenience_function),
        ("Seismic Scan", test_seismic_scan)
    ]
    
    passed = 0
    failed = 0
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
            passed += 1
        except AssertionError as e:
            print(f"\n❌ Test FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ Test ERROR: {e}")
            failed += 1
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUITE SUMMARY")
    print("=" * 70)
    print(f"Total Tests: {len(tests)}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    print(f"Success Rate: {(passed/len(tests)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Agent 3 Validator is ready for deployment.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review and fix.")
    
    return results


if __name__ == "__main__":
    results = run_all_tests()
    
    # Save results to file
    output_dir = Path(__file__).parent / "test_results"
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / f"agent3_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_file, 'w') as f:
        json.dump(
            {k: v for k, v in results.items()},
            f,
            indent=2,
            default=str
        )
    
    print(f"\n📄 Results saved to: {output_file}")
