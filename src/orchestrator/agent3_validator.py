# Copyright (c) 2026 Diamond Node Team
# Licensed under the MIT License - see LICENSE file for details

"""
Agent 3 - Validator for the Ouroboros Protocol

This module implements the Validator agent using a Seismic Tree-of-Thoughts
methodology to evaluate payloads from Generator (Agent 1) and Attacker (Agent 2).
Validates against topological anchors, hardware grounding (aSHARD), and 
operational authority (Process Invariance).

Output states: NULL, DUCTILE, CRYSTALLINE
"""

import os
import json
import hashlib
import time
import copy
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import yaml

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("[Warning] Anthropic SDK not available. Install with: pip install anthropic")


@dataclass
class InvariantTruth:
    """Mathematical invariants and constraints for validation"""
    conservation_laws: List[str]
    symmetries: List[str]
    dimensional_constraints: Dict[str, Any]
    boundary_conditions: Dict[str, Any]


@dataclass
class AShardParams:
    """Hardware-specific physical constraints (aSHARD = autonomic SHARD)"""
    vram_total_bytes: int = 4294967296  # 4GB for GTX 1650
    vram_allocation_buffer: float = 0.9  # 90% safety margin
    thermal_max_celsius: float = 89.6
    compute_capability: Tuple[int, int] = (7, 5)
    memory_bandwidth_gbps: float = 128.0


@dataclass
class PIScope:
    """Process Invariance operational boundaries"""
    allowed_operations: List[str]
    resource_limits: Dict[str, Any]
    state_transitions: Dict[str, Any]
    execution_context: Dict[str, Any]


@dataclass
class ValidationResult:
    """Structured validation result"""
    state: str  # NULL | DUCTILE | CRYSTALLINE
    timestamp: str
    evaluation_summary: Dict[str, Any]
    detailed_analysis: Dict[str, Any]
    recommendations: Dict[str, Any]


class OuroborosAgent3Validator:
    """
    Agent 3 - Validator in the Ouroboros Protocol
    
    Evaluates payloads using Seismic Tree-of-Thoughts methodology:
    1. Seismic Scan - Structural analysis
    2. Topological Validation - Mathematical invariants
    3. Hardware Grounding - aSHARD alignment
    4. Operational Authority - PI scope validation
    5. Crystallization Decision - NULL/DUCTILE/CRYSTALLINE
    """
    
    def __init__(
        self, 
        invariant_truth: Dict[str, Any],
        ashard_params: Optional[Dict[str, Any]] = None,
        pi_scope: Optional[Dict[str, Any]] = None,
        system_prompt_path: Optional[Path] = None,
        api_key: Optional[str] = None,
        use_local_llm: bool = False
    ):
        """
        Initialize Agent 3 Validator
        
        Args:
            invariant_truth: Mathematical constraints and ground truth
            ashard_params: Hardware constraints (defaults to GTX 1650 specs)
            pi_scope: Process Invariance operational boundaries
            system_prompt_path: Path to agent3_system_prompt.yaml
            api_key: Anthropic API key (if using Claude)
            use_local_llm: Use local LLM instead of Claude API
        """
        invariant_truth = invariant_truth or {}
        self.invariant_truth = InvariantTruth(
            conservation_laws=invariant_truth.get("conservation_laws", []),
            symmetries=invariant_truth.get("symmetries", []),
            dimensional_constraints=invariant_truth.get("dimensional_constraints", {}),
            boundary_conditions=invariant_truth.get("boundary_conditions", {}),
        )
        
        if not ashard_params:
            self.ashard_params = AShardParams()
        else:
            self.ashard_params = AShardParams(**ashard_params)
        
        if not pi_scope:
            self.pi_scope = PIScope(
                allowed_operations=["compute", "read", "write"],
                resource_limits={"max_threads": 1024, "max_memory_mb": 3600},
                state_transitions={"valid_states": ["init", "running", "complete"]},
                execution_context={"sandbox": True, "isolation": "process"}
            )
        else:
            self.pi_scope = PIScope(**pi_scope)
        
        # Load system prompt
        if system_prompt_path is None:
            config_dir = Path(__file__).parent.parent.parent / "config"
            system_prompt_path = config_dir / "agent3_system_prompt.yaml"
        
        self.system_prompt_path = Path(system_prompt_path)
        self.system_prompt = self._load_system_prompt()
        
        # Setup LLM backend
        self.use_local_llm = use_local_llm
        if not use_local_llm and ANTHROPIC_AVAILABLE:
            self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
            if self.api_key:
                self.client = Anthropic(api_key=self.api_key)
            else:
                print("[Warning] No ANTHROPIC_API_KEY found, will use local validation only")
                self.client = None
        else:
            self.client = None
        
        # Restart counter for monitoring
        self.restart_count = 0
    
    def _load_system_prompt(self) -> Dict[str, Any]:
        """Load system prompt from YAML file"""
        if not self.system_prompt_path.exists():
            raise FileNotFoundError(f"System prompt not found: {self.system_prompt_path}")
        
        with open(self.system_prompt_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _compute_topology_hash(self, payload: Dict[str, Any]) -> str:
        """Compute deterministic hash of payload structure"""
        payload_str = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(payload_str.encode()).hexdigest()
    
    def _seismic_scan(self, payload: Dict[str, Any], generator_output: Dict[str, Any], 
                      attacker_perturbation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 1: Seismic Scan - Analyze payload structure and trace provenance
        
        Returns:
            topology_hash: Unique identifier for payload structure
            perturbation_magnitude: Measure of attacker's impact
            structural_integrity: Boolean indicating if structure is valid
        """
        topology_hash = self._compute_topology_hash(payload)
        
        # Measure perturbation magnitude (L2 norm of changes)
        perturbation_magnitude = 0.0
        if attacker_perturbation:
            # Extract numerical changes
            for key in attacker_perturbation:
                if isinstance(attacker_perturbation[key], (int, float)):
                    perturbation_magnitude += attacker_perturbation[key] ** 2
            perturbation_magnitude = perturbation_magnitude ** 0.5
        
        # Check structural integrity
        required_keys = ["operation", "parameters", "metadata"]
        structural_integrity = all(key in payload for key in required_keys)
        
        return {
            "topology_hash": topology_hash,
            "perturbation_magnitude": perturbation_magnitude,
            "structural_integrity": structural_integrity
        }
    
    def _topological_validation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 2: Topological Validation - Verify mathematical invariants
        
        Checks:
        - Conservation laws (energy, momentum, information)
        - Dimensional consistency
        - Symmetry preservation
        - Boundary condition integrity
        
        Returns:
            invariant_score: [0.0, 1.0]
            dimension_match: boolean
            symmetry_preserved: boolean
            conservation_violations: list[str]
        """
        score = 0.0
        violations = []
        
        # Check conservation laws
        conservation_checks = len(self.invariant_truth.conservation_laws)
        if conservation_checks > 0:
            passed = 0
            for law in self.invariant_truth.conservation_laws:
                # Check if payload respects this conservation law
                if self._check_conservation_law(payload, law):
                    passed += 1
                else:
                    violations.append(f"Conservation law violated: {law}")
            score += (passed / conservation_checks) * 0.4
        
        # Check dimensional consistency
        dimension_match = self._check_dimensional_consistency(payload)
        if dimension_match:
            score += 0.3
        else:
            violations.append("Dimensional mismatch detected")
        
        # Check symmetry preservation
        symmetry_preserved = self._check_symmetries(payload)
        if symmetry_preserved:
            score += 0.3
        else:
            violations.append("Symmetry violation detected")
        
        return {
            "invariant_score": score,
            "dimension_match": dimension_match,
            "symmetry_preserved": symmetry_preserved,
            "conservation_violations": violations
        }
    
    def _check_conservation_law(self, payload: Dict[str, Any], law: str) -> bool:
        """Check if a specific conservation law is satisfied"""
        # Simplified check - in production, this would be more sophisticated
        if law == "energy":
            # Check if energy is conserved (if present)
            params = payload.get("parameters", {})
            if "energy_in" in params and "energy_out" in params:
                return abs(params["energy_in"] - params["energy_out"]) < 1e-6
            return True  # No energy terms, assume satisfied
        
        elif law == "information":
            # Check if information content is preserved
            params = payload.get("parameters", {})
            if "input_entropy" in params and "output_entropy" in params:
                return params["output_entropy"] >= params["input_entropy"] * 0.95
            return True
        
        return True  # Default: assume satisfied if not explicitly violated
    
    def _check_dimensional_consistency(self, payload: Dict[str, Any]) -> bool:
        """Verify dimensional consistency of parameters"""
        constraints = self.invariant_truth.dimensional_constraints
        params = payload.get("parameters", {})
        
        for key, expected_dim in constraints.items():
            if key in params:
                value = params[key]
                # Check if value matches expected dimension
                if isinstance(expected_dim, str):
                    if expected_dim == "scalar" and not isinstance(value, (int, float)):
                        return False
                    elif expected_dim == "vector" and not isinstance(value, list):
                        return False
                    elif expected_dim == "matrix" and not (isinstance(value, list) and 
                                                          isinstance(value[0], list)):
                        return False
        
        return True
    
    def _check_symmetries(self, payload: Dict[str, Any]) -> bool:
        """Check if required symmetries are preserved"""
        # Simplified symmetry check
        for symmetry in self.invariant_truth.symmetries:
            if symmetry == "time_reversal":
                # Check if operation is time-reversible
                if payload.get("operation") in ["hash", "random"]:
                    return False
        
        return True
    
    def _hardware_grounding(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 3: Hardware Grounding - Validate against aSHARD constraints
        
        Checks:
        - VRAM budget compliance
        - Thermal envelope
        - Compute capability alignment
        - Memory bandwidth feasibility
        
        Returns:
            vram_utilization: [0.0, 1.0]
            vram_fits: boolean
            thermal_margin: float (degrees C)
            hardware_compatible: boolean
        """
        params = payload.get("parameters", {})
        
        # Estimate VRAM usage
        vram_estimate = params.get("vram_requirement_bytes", 0)
        if not vram_estimate and "matrix_size" in params:
            # Rough estimate: matrix of size N requires ~N^2 * 4 bytes (float32)
            n = params["matrix_size"]
            vram_estimate = n * n * 4
        
        vram_limit = self.ashard_params.vram_total_bytes * self.ashard_params.vram_allocation_buffer
        vram_utilization = vram_estimate / self.ashard_params.vram_total_bytes
        vram_fits = vram_estimate <= vram_limit
        
        # Estimate thermal impact
        compute_intensity = params.get("compute_intensity", 0.5)  # [0.0, 1.0]
        thermal_estimate = 45.0 + compute_intensity * 40.0  # Base 45°C + load
        thermal_margin = self.ashard_params.thermal_max_celsius - thermal_estimate
        thermal_violation = compute_intensity >= 1.0 or thermal_margin < 2.0
        
        # Check compute capability
        required_cc = params.get("compute_capability", (7, 0))
        hardware_compatible = (
            required_cc[0] <= self.ashard_params.compute_capability[0] and
            required_cc[1] <= self.ashard_params.compute_capability[1]
        )
        
        return {
            "vram_utilization": vram_utilization,
            "vram_fits": vram_fits,
            "thermal_margin": thermal_margin,
            "thermal_violation": thermal_violation,
            "hardware_compatible": hardware_compatible
        }
    
    def _operational_authority(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 4: Operational Authority - Validate PI scope
        
        Checks:
        - PI boundary compliance
        - Execution trace validity
        - Resource access permissions
        - State transition legality
        
        Returns:
            pi_scope_valid: boolean
            execution_safe: boolean
            state_transition_legal: boolean
            permission_violations: list[str]
        """
        violations = []
        
        # Check if operation is allowed
        operation = payload.get("operation", "")
        pi_scope_valid = operation in self.pi_scope.allowed_operations
        if not pi_scope_valid:
            violations.append(f"Operation not in PI scope: {operation}")
        
        # Check resource limits
        params = payload.get("parameters", {})
        execution_safe = True
        
        for resource, limit in self.pi_scope.resource_limits.items():
            if resource in params:
                if params[resource] > limit:
                    execution_safe = False
                    violations.append(f"Resource limit exceeded: {resource} > {limit}")
        
        # Check state transitions
        current_state = payload.get("metadata", {}).get("state", "init")
        valid_states = self.pi_scope.state_transitions.get("valid_states", [])
        state_transition_legal = current_state in valid_states
        if not state_transition_legal:
            violations.append(f"Invalid state transition: {current_state}")
        
        return {
            "pi_scope_valid": pi_scope_valid,
            "execution_safe": execution_safe,
            "state_transition_legal": state_transition_legal,
            "permission_violations": violations
        }
    
    def crystallization_phase(self, payload: Dict[str, Any]) -> str:
        """
        Phase 5: Crystallization Decision
        
        Synthesizes evaluation metrics into final state classification.
        
        Returns: "NULL" | "DUCTILE" | "CRYSTALLINE"
        """
        # Run all validation phases
        topo_result = self._topological_validation(payload)
        hw_result = self._hardware_grounding(payload)
        pi_result = self._operational_authority(payload)
        
        invariant_score = topo_result["invariant_score"]
        
        # NULL: Critical failure
        if invariant_score < 0.3:
            return "NULL"
        
        if not hw_result["vram_fits"]:
            return "NULL"
        
        # Thermal margin must be at least 2°C, or NULL if negative
        if hw_result["thermal_violation"]:
            return "NULL"
        
        if not pi_result["pi_scope_valid"]:
            return "NULL"
        
        if not topo_result["dimension_match"]:
            return "NULL"
        
        # CRYSTALLINE: Perfect score (strict criteria)
        if (invariant_score >= 0.75 and 
            hw_result["vram_fits"] and 
            hw_result["vram_utilization"] < 0.70 and  # Not too tight on VRAM
            hw_result["thermal_margin"] >= 5.0 and
            hw_result["hardware_compatible"] and
            pi_result["pi_scope_valid"] and
            pi_result["execution_safe"] and
            pi_result["state_transition_legal"] and
            topo_result["symmetry_preserved"] and
            len(topo_result["conservation_violations"]) == 0):
            return "CRYSTALLINE"
        
        # DUCTILE: Acceptable with corrections
        return "DUCTILE"

    def validate(self, payload: Dict[str, Any], mock_result: Optional[str] = None) -> ValidationResult:
        """
        Compatibility wrapper for orchestration callers that expect a
        ValidationResult object instead of the evaluate_payload dict envelope.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        normalized_payload = self._normalize_validation_payload(payload)

        if mock_result is not None:
            state = mock_result
            topo_result = self._topological_validation(normalized_payload)
            hw_result = self._hardware_grounding(normalized_payload)
            pi_result = self._operational_authority(normalized_payload)
            return ValidationResult(
                state=state,
                timestamp=timestamp,
                evaluation_summary={
                    "topological_score": topo_result["invariant_score"],
                    "hardware_compliance": hw_result["vram_fits"] and hw_result["hardware_compatible"],
                    "pi_validity": pi_result["pi_scope_valid"],
                    "invariant_violations": topo_result["conservation_violations"],
                    "mocked": True,
                },
                detailed_analysis={
                    "topological_validation": topo_result,
                    "hardware_grounding": hw_result,
                    "operational_authority": pi_result,
                },
                recommendations={"action": "MOCK_RESULT"},
            )

        result = self.evaluate_payload(
            payload=normalized_payload,
            generator_output={},
            attacker_perturbation={},
        )["validation_result"]

        return ValidationResult(
            state=result["state"],
            timestamp=result["timestamp"],
            evaluation_summary=result["evaluation_summary"],
            detailed_analysis=result["detailed_analysis"],
            recommendations=result["recommendations"],
        )

    def _normalize_validation_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if "operation" in payload and "parameters" in payload and "metadata" in payload:
            return payload

        operation = payload.get("operation") or payload.get("type") or "validation"
        parameters = dict(payload.get("parameters", {}))
        metadata = dict(payload.get("metadata", {}))
        metadata.setdefault("state", "NULL")

        if "telemetry" in payload:
            telemetry = payload["telemetry"]
            if isinstance(telemetry, dict):
                parameters.setdefault("vram_requirement_bytes", int(telemetry.get("vram_used_mb", 0) * 1024 * 1024))
                parameters.setdefault("compute_intensity", min(float(telemetry.get("vram_percent", 0.0)) / 100.0, 1.0))

        return {
            **payload,
            "operation": operation,
            "parameters": parameters,
            "metadata": metadata,
        }
    
    def apply_rigid_filtering(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply rigid filtering to payload to enforce hard constraints.
        Used for DUCTILE payloads that need corrections.
        
        Returns: Corrected payload
        """
        corrected = copy.deepcopy(payload)
        params = corrected.get("parameters", {})
        
        # Enforce VRAM limit
        vram_limit = self.ashard_params.vram_total_bytes * self.ashard_params.vram_allocation_buffer
        
        original_vram_requirement = params.get("vram_requirement_bytes")
        if original_vram_requirement is not None and original_vram_requirement > vram_limit:
            if "matrix_size" in params and params["matrix_size"] > 1:
                reduction_factor = (vram_limit / original_vram_requirement) ** 0.5
                params["matrix_size"] = max(1, int(params["matrix_size"] * reduction_factor))
            params["vram_requirement_bytes"] = int(vram_limit)
        
        # Enforce matrix size based on VRAM (if present)
        if "matrix_size" in params:
            max_size = int((vram_limit / 4) ** 0.5)
            original_size = params["matrix_size"]
            params["matrix_size"] = min(params["matrix_size"], max_size)
            
            # If we reduced matrix size, also update vram_requirement
            if params["matrix_size"] < original_size:
                params["vram_requirement_bytes"] = params["matrix_size"] * params["matrix_size"] * 4
        
        # Enforce compute intensity
        if "compute_intensity" in params:
            params["compute_intensity"] = min(params["compute_intensity"], 0.85)
        
        corrected["parameters"] = params
        return corrected
    
    def trigger_restart(self) -> None:
        """
        Trigger restart protocol when NULL state is encountered.
        Logs failure and signals Generator (Agent 1) to restart with corrected constraints.
        """
        self.restart_count += 1
        print(f"[Agent 3] NULL state detected. Triggering restart #{self.restart_count}")
        
        # In production, this would signal Agent 1 via message queue or IPC
        # For now, just log the event
        restart_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "restart_count": self.restart_count,
            "reason": "NULL validation state",
            "action": "Signal Generator for constraint correction"
        }
        
        print(f"[Agent 3] Restart event: {json.dumps(restart_event, indent=2)}")
    
    def evaluate_payload(
        self, 
        payload: Dict[str, Any],
        generator_output: Dict[str, Any],
        attacker_perturbation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Main evaluation method for Agent 3.
        
        Runs all validation phases and produces structured output.
        
        Args:
            payload: The payload to validate
            generator_output: Original output from Agent 1
            attacker_perturbation: Perturbation applied by Agent 2
        
        Returns:
            ValidationResult as dict with state (NULL/DUCTILE/CRYSTALLINE)
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Phase 1: Seismic Scan
        seismic_result = self._seismic_scan(payload, generator_output, attacker_perturbation)
        
        # Phase 2: Topological Validation
        topo_result = self._topological_validation(payload)
        
        # Phase 3: Hardware Grounding
        hw_result = self._hardware_grounding(payload)
        
        # Phase 4: Operational Authority
        pi_result = self._operational_authority(payload)
        
        # Phase 5: Crystallization Decision
        state = self.crystallization_phase(payload)
        
        # Prepare corrections if DUCTILE
        corrections_required = []
        if state == "DUCTILE":
            if not hw_result["vram_fits"]:
                corrections_required.append({
                    "type": "vram_reduction",
                    "action": "Reduce VRAM requirement to fit within budget"
                })
            elif hw_result["vram_utilization"] >= 0.70:
                corrections_required.append({
                    "type": "vram_headroom",
                    "action": "Reduce VRAM requirement to preserve execution headroom"
                })
            if hw_result["thermal_margin"] < 5.0:
                corrections_required.append({
                    "type": "thermal_optimization",
                    "action": "Reduce compute intensity to improve thermal margin"
                })
            if topo_result["conservation_violations"]:
                corrections_required.append({
                    "type": "invariant_correction",
                    "violations": topo_result["conservation_violations"]
                })
        
        # Compile result
        result = {
            "validation_result": {
                "state": state,
                "timestamp": timestamp,
                "evaluation_summary": {
                    "topological_score": topo_result["invariant_score"],
                    "hardware_compliance": hw_result["vram_fits"] and hw_result["hardware_compatible"],
                    "pi_validity": pi_result["pi_scope_valid"],
                    "invariant_violations": topo_result["conservation_violations"],
                    "corrections_required": corrections_required
                },
                "detailed_analysis": {
                    "seismic_scan": seismic_result,
                    "topological_validation": topo_result,
                    "hardware_grounding": hw_result,
                    "operational_authority": pi_result
                },
                "recommendations": self._generate_recommendations(state, topo_result, hw_result, pi_result)
            }
        }
        
        # Trigger restart if NULL
        if state == "NULL":
            self.trigger_restart()
        
        return result
    
    def _generate_recommendations(
        self, 
        state: str, 
        topo_result: Dict[str, Any],
        hw_result: Dict[str, Any],
        pi_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate actionable recommendations based on validation results"""
        if state == "CRYSTALLINE":
            return {
                "action": "COMMIT",
                "rationale": "Payload meets all validation criteria",
                "next_steps": ["Execute payload in production pipeline"]
            }
        
        elif state == "DUCTILE":
            next_steps = []
            rationale_parts = []
            
            if topo_result["invariant_score"] < 0.75:
                next_steps.append("Apply invariant corrections")
                rationale_parts.append("topological refinement needed")
            
            if not hw_result["vram_fits"] or hw_result["thermal_margin"] < 5.0:
                next_steps.append("Apply hardware-aware optimizations")
                rationale_parts.append("hardware constraints violated")
            
            return {
                "action": "CORRECT_AND_RETRY",
                "rationale": f"Payload acceptable with corrections: {', '.join(rationale_parts)}",
                "next_steps": next_steps
            }
        
        else:  # NULL
            next_steps = ["Trigger Generator restart with corrected constraints"]
            
            if topo_result["invariant_score"] < 0.3:
                next_steps.append("Revise mathematical invariants")
            
            if not hw_result["vram_fits"]:
                next_steps.append("Enforce stricter VRAM budgets")
            
            if not pi_result["pi_scope_valid"]:
                next_steps.append("Verify PI scope boundaries")
            
            return {
                "action": "REJECT",
                "rationale": "Critical validation failures detected",
                "next_steps": next_steps
            }


# Convenience function for quick validation
def validate_payload(
    payload: Dict[str, Any],
    invariant_truth: Dict[str, Any],
    ashard_params: Optional[Dict[str, Any]] = None,
    generator_output: Optional[Dict[str, Any]] = None,
    attacker_perturbation: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convenience function for one-shot payload validation.
    
    Example:
        result = validate_payload(
            payload=my_payload,
            invariant_truth={
                "conservation_laws": ["energy", "information"],
                "symmetries": ["time_reversal"],
                "dimensional_constraints": {"input": "vector", "output": "vector"},
                "boundary_conditions": {}
            }
        )
        print(f"State: {result['validation_result']['state']}")
    """
    validator = OuroborosAgent3Validator(
        invariant_truth=invariant_truth,
        ashard_params=ashard_params
    )
    
    return validator.evaluate_payload(
        payload=payload,
        generator_output=generator_output or {},
        attacker_perturbation=attacker_perturbation or {}
    )


if __name__ == "__main__":
    # Example usage
    print("Agent 3 - Validator (Ouroboros Protocol)")
    print("=" * 60)
    
    # Define invariant truth
    invariant_truth = {
        "conservation_laws": ["energy", "information"],
        "symmetries": ["time_reversal"],
        "dimensional_constraints": {
            "input": "vector",
            "output": "vector"
        },
        "boundary_conditions": {}
    }
    
    # Create validator
    validator = OuroborosAgent3Validator(invariant_truth=invariant_truth)
    
    # Test payload (CRYSTALLINE)
    test_payload_crystalline = {
        "operation": "compute",
        "parameters": {
            "input": [1.0, 2.0, 3.0],
            "output": [1.1, 2.1, 3.1],
            "energy_in": 100.0,
            "energy_out": 100.0,
            "input_entropy": 2.5,
            "output_entropy": 2.6,
            "matrix_size": 256,
            "compute_intensity": 0.5,
            "vram_requirement_bytes": 1073741824  # 1GB
        },
        "metadata": {
            "state": "running",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }
    
    result = validator.evaluate_payload(
        payload=test_payload_crystalline,
        generator_output={},
        attacker_perturbation={}
    )
    
    print(f"\nTest 1 (Expected CRYSTALLINE):")
    print(f"State: {result['validation_result']['state']}")
    print(f"Topological Score: {result['validation_result']['evaluation_summary']['topological_score']:.2f}")
    print(f"Hardware Compliance: {result['validation_result']['evaluation_summary']['hardware_compliance']}")
    
    # Test payload (NULL - VRAM overflow)
    test_payload_null = {
        "operation": "compute",
        "parameters": {
            "matrix_size": 50000,  # Requires ~10GB VRAM
            "compute_intensity": 0.95,
            "vram_requirement_bytes": 10737418240  # 10GB
        },
        "metadata": {
            "state": "running"
        }
    }
    
    result_null = validator.evaluate_payload(
        payload=test_payload_null,
        generator_output={},
        attacker_perturbation={}
    )
    
    print(f"\nTest 2 (Expected NULL - VRAM overflow):")
    print(f"State: {result_null['validation_result']['state']}")
    print(f"Recommendation: {result_null['validation_result']['recommendations']['action']}")
    
    print("\n" + "=" * 60)
    print("Agent 3 validation complete.")
