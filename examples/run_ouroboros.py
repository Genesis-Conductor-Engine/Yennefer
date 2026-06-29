#!/usr/bin/env python3
# Copyright (c) 2026 Diamond Node Team
# Licensed under the MIT License - see LICENSE file for details

"""
Example: Run Ouroboros Protocol Loop

This script demonstrates the complete Generator→Attacker→Validator loop
with various test scenarios.
"""

import os
import sys
import json
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src" / "orchestrator"
sys.path.insert(0, str(src_path))

from ouroboros_protocol import OuroborosProtocol
from agent3_validator import OuroborosAgent3Validator


def example_1_simple_matrix_multiply():
    """Example 1: Simple matrix multiplication"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Simple Matrix Multiplication")
    print("="*80)
    
    # Setup invariant truth (mathematical constraints)
    invariant_truth = {
        "conservation_laws": [
            "matrix_dimension_compatibility",
            "numerical_precision_preservation"
        ],
        "symmetries": [
            "commutative_addition",
            "associative_multiplication"
        ],
        "dimensional_constraints": {
            "max_matrix_size": 2048,
            "min_matrix_size": 1,
            "supported_precisions": ["fp16", "fp32", "fp64"]
        },
        "boundary_conditions": {
            "max_iterations": 1000,
            "convergence_threshold": 1e-6
        }
    }
    
    # Create Agent 3 Validator
    validator = OuroborosAgent3Validator(
        invariant_truth=invariant_truth
    )
    
    # Create Ouroboros Protocol
    protocol = OuroborosProtocol(
        agent3_validator=validator,
        model="claude-opus-4-20250514"
    )
    
    # Execute loop
    result = protocol.execute_loop(
        prompt="Multiply two 512×512 matrices in FP32 precision",
        max_iterations=5
    )
    
    return result


def example_2_quantum_simulation():
    """Example 2: CUDA-Q quantum simulation"""
    print("\n" + "="*80)
    print("EXAMPLE 2: CUDA-Q Quantum Simulation")
    print("="*80)
    
    invariant_truth = {
        "conservation_laws": [
            "qubit_count_preservation",
            "unitary_evolution",
            "probability_normalization"
        ],
        "symmetries": [
            "time_reversal_symmetry",
            "gauge_invariance"
        ],
        "dimensional_constraints": {
            "max_qubits": 25,
            "min_qubits": 2,
            "supported_gates": ["H", "X", "Y", "Z", "CNOT", "RZ", "RX", "RY"]
        },
        "boundary_conditions": {
            "max_circuit_depth": 100,
            "max_shots": 10000
        }
    }
    
    validator = OuroborosAgent3Validator(
        invariant_truth=invariant_truth
    )
    
    protocol = OuroborosProtocol(
        agent3_validator=validator,
        model="claude-opus-4-20250514"
    )
    
    result = protocol.execute_loop(
        prompt="Simulate a 10-qubit quantum circuit for VQE with 1000 shots",
        max_iterations=5
    )
    
    return result


def example_3_ml_inference():
    """Example 3: ML inference with YOLO11"""
    print("\n" + "="*80)
    print("EXAMPLE 3: ML Inference (YOLO11)")
    print("="*80)
    
    invariant_truth = {
        "conservation_laws": [
            "image_dimension_preservation",
            "batch_size_consistency"
        ],
        "symmetries": [
            "translation_equivariance",
            "scale_invariance"
        ],
        "dimensional_constraints": {
            "max_batch_size": 8,
            "supported_resolutions": [640, 1280],
            "supported_models": ["yolo11n", "yolo11s", "yolo11m"]
        },
        "boundary_conditions": {
            "max_inference_time_ms": 5000,
            "min_confidence": 0.25
        }
    }
    
    validator = OuroborosAgent3Validator(
        invariant_truth=invariant_truth
    )
    
    protocol = OuroborosProtocol(
        agent3_validator=validator,
        model="claude-opus-4-20250514"
    )
    
    result = protocol.execute_loop(
        prompt="Run YOLO11s inference on a batch of 4 images at 640×640 resolution",
        max_iterations=5
    )
    
    return result


def example_4_stress_test():
    """Example 4: Stress test with tight constraints"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Stress Test (Tight VRAM Constraints)")
    print("="*80)
    
    invariant_truth = {
        "conservation_laws": [
            "vram_budget_conservation",
            "thermal_envelope_preservation"
        ],
        "symmetries": [],
        "dimensional_constraints": {
            "max_vram_bytes": 3221225472,  # 3GB (tight for GTX 1650)
            "max_batch_size": 2
        },
        "boundary_conditions": {
            "thermal_limit_celsius": 85.0  # Aggressive limit
        }
    }
    
    validator = OuroborosAgent3Validator(
        invariant_truth=invariant_truth
    )
    
    protocol = OuroborosProtocol(
        agent3_validator=validator,
        model="claude-opus-4-20250514"
    )
    
    result = protocol.execute_loop(
        prompt="Train a neural network with 1024×1024 feature maps and batch size 8",
        max_iterations=5
    )
    
    return result


def main():
    """Run all examples"""
    # Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not found in environment")
        print("Please run: source ~/load-env.sh")
        sys.exit(1)
    
    examples = [
        ("Simple Matrix Multiply", example_1_simple_matrix_multiply),
        ("CUDA-Q Quantum Simulation", example_2_quantum_simulation),
        ("ML Inference (YOLO11)", example_3_ml_inference),
        ("Stress Test (Tight Constraints)", example_4_stress_test)
    ]
    
    print("\n" + "="*80)
    print("OUROBOROS PROTOCOL - Example Runner")
    print("="*80)
    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    print(f"  0. Run all examples")
    
    choice = input("\nSelect example (0-4): ").strip()
    
    if choice == "0":
        results = {}
        for name, example_func in examples:
            try:
                result = example_func()
                results[name] = result
            except Exception as e:
                print(f"\nERROR in {name}: {e}")
                results[name] = {"error": str(e)}
        
        # Print overall summary
        print("\n" + "="*80)
        print("OVERALL SUMMARY")
        print("="*80)
        for name, result in results.items():
            if "error" in result:
                print(f"  {name}: FAILED - {result['error']}")
            else:
                state = result.get("final_state", "UNKNOWN")
                converged = result.get("converged", False)
                iterations = result["metrics"]["total_iterations"]
                print(f"  {name}: {state} (converged={converged}, iterations={iterations})")
        
    elif choice in ["1", "2", "3", "4"]:
        idx = int(choice) - 1
        name, example_func = examples[idx]
        try:
            result = example_func()
            print(f"\n✅ {name} completed successfully")
            print(f"Final State: {result.get('final_state', 'UNKNOWN')}")
            print(f"Converged: {result.get('converged', False)}")
        except Exception as e:
            print(f"\n❌ {name} failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("Invalid choice")
        sys.exit(1)


if __name__ == "__main__":
    main()
