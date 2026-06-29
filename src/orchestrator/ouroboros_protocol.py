# Copyright (c) 2026 Diamond Node Team
# Licensed under the MIT License - see LICENSE file for details

"""
Ouroboros Protocol - Complete Generator→Attacker→Validator Loop

This module implements the full three-agent architecture for the Ouroboros Protocol:
1. Agent 1 (Generator): Generates payloads from natural language prompts
2. Agent 2 (Attacker): Applies adversarial perturbations to test robustness
3. Agent 3 (Validator): Validates and classifies as NULL/DUCTILE/CRYSTALLINE

The loop restarts on NULL states and applies corrections for DUCTILE states.
"""

import os
import json
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("[Warning] Anthropic SDK not available. Install with: pip install anthropic")

from agent3_validator import OuroborosAgent3Validator


@dataclass
class OuroborosMetrics:
    """Metrics tracking for Ouroboros loop execution"""
    total_iterations: int = 0
    null_count: int = 0
    ductile_count: int = 0
    crystalline_count: int = 0
    total_validation_time: float = 0.0
    restart_count: int = 0
    convergence_iteration: Optional[int] = None
    
    @property
    def average_validation_time(self) -> float:
        """Average time per validation"""
        if self.total_iterations == 0:
            return 0.0
        return self.total_validation_time / self.total_iterations
    
    @property
    def convergence_rate(self) -> float:
        """Convergence rate (1.0 = converged on first try)"""
        if self.convergence_iteration is None:
            return 0.0
        return 1.0 / self.convergence_iteration
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            **asdict(self),
            "average_validation_time": self.average_validation_time,
            "convergence_rate": self.convergence_rate
        }


class OuroborosProtocol:
    """
    Complete Ouroboros Protocol implementation with Generator→Attacker→Validator loop
    
    The protocol operates in three phases:
    1. Generation (Agent 1): Generate payload from natural language prompt
    2. Attack (Agent 2): Apply adversarial perturbations
    3. Validation (Agent 3): Validate and classify state
    
    Loop behavior:
    - NULL: Restart with corrected constraints
    - DUCTILE: Apply corrections and re-validate (no full restart)
    - CRYSTALLINE: Lock payload and advance orchestration
    """
    
    def __init__(
        self,
        agent3_validator: OuroborosAgent3Validator,
        llm_generator: Optional[Any] = None,
        llm_attacker: Optional[Any] = None,
        api_key: Optional[str] = None,
        model: str = "claude-opus-4-20250514",
        max_tokens: int = 4096
    ):
        """
        Initialize Ouroboros Protocol
        
        Args:
            agent3_validator: Initialized Agent 3 Validator
            llm_generator: Optional LLM client for Generator (Agent 1)
            llm_attacker: Optional LLM client for Attacker (Agent 2)
            api_key: Anthropic API key (if not using provided clients)
            model: Claude model to use
            max_tokens: Maximum tokens per request
        """
        self.agent3 = agent3_validator
        self.model = model
        self.max_tokens = max_tokens
        
        # Setup LLM clients
        if llm_generator is not None:
            self.generator_client = llm_generator
        elif ANTHROPIC_AVAILABLE:
            self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
            if self.api_key:
                self.generator_client = Anthropic(api_key=self.api_key)
            else:
                raise ValueError("No ANTHROPIC_API_KEY found. Set in environment or pass as api_key parameter.")
        else:
            raise ImportError("Anthropic SDK required. Install with: pip install anthropic")
        
        if llm_attacker is not None:
            self.attacker_client = llm_attacker
        else:
            # Share the same client for efficiency
            self.attacker_client = self.generator_client
        
        # Metrics tracking
        self.metrics = OuroborosMetrics()
        
        # Iteration history
        self.iteration_history: List[Dict[str, Any]] = []
    
    def agent1_generate(self, prompt: str, constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Phase 1: Generator (Agent 1)
        
        Generates a structured payload from a natural language prompt.
        
        Args:
            prompt: Natural language task description
            constraints: Optional constraints from previous NULL states
            
        Returns:
            dict with:
                - payload: Generated structured payload
                - reasoning: Generation reasoning
                - timestamp: Generation timestamp
        """
        system_prompt = """You are Agent 1 (Generator) in the Ouroboros Protocol.

Your role is to generate structured payloads for GPU/ML operations based on natural language prompts.

Output format (JSON):
{
  "operation": "string (e.g., 'matrix_multiply', 'quantum_simulation', 'ml_inference')",
  "parameters": {
    "matrix_size": int,
    "vram_requirement_bytes": int,
    "compute_intensity": float (0.0-1.0),
    "batch_size": int,
    "precision": "string ('fp16', 'fp32', 'fp64')"
  },
  "metadata": {
    "priority": "string ('low', 'medium', 'high')",
    "timeout_seconds": int,
    "retries": int
  }
}

CRITICAL CONSTRAINTS:
- VRAM limit: 3.6 GB (GTX 1650 with 90% safety margin)
- Thermal limit: 89.6°C (leave 5°C margin)
- Compute intensity: ≤ 0.85 to avoid thermal throttling

If constraints are provided from a previous NULL state, strictly adhere to them."""

        user_message = f"Task: {prompt}"
        
        if constraints:
            user_message += f"\n\nPrevious NULL state constraints:\n{json.dumps(constraints, indent=2)}"
            user_message += "\n\nGenerate a corrected payload that satisfies these constraints."
        
        try:
            start_time = time.time()
            
            response = self.generator_client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            
            generation_time = time.time() - start_time
            
            # Extract JSON from response
            content = response.content[0].text
            
            # Try to parse JSON (handle markdown code blocks)
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content.strip()
            
            payload = json.loads(json_str)
            
            result = {
                "payload": payload,
                "reasoning": f"Generated from prompt: {prompt}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "generation_time": generation_time,
                "model": self.model,
                "constraints_applied": constraints is not None
            }
            
            print(f"[Agent 1] Generated payload in {generation_time:.2f}s")
            
            return result
            
        except Exception as e:
            print(f"[Agent 1] Generation failed: {e}")
            raise
    
    def agent2_attack(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 2: Attacker (Agent 2)
        
        Applies adversarial perturbations to test payload robustness.
        
        Args:
            payload: Payload from Agent 1
            
        Returns:
            dict with:
                - perturbed_payload: Payload with perturbations applied
                - perturbation: Description of perturbations
                - attack_vector: Type of attack
                - timestamp: Attack timestamp
        """
        system_prompt = """You are Agent 2 (Attacker) in the Ouroboros Protocol.

Your role is to apply adversarial perturbations to test payload robustness.

Attack strategies:
1. Resource stress: Increase VRAM/compute requirements
2. Boundary testing: Push parameters to edge cases
3. Type fuzzing: Modify data types or formats
4. Temporal stress: Tighten timeout constraints
5. Priority inversion: Change priority unexpectedly

Apply perturbations that are realistic and likely to expose weaknesses, but not so extreme that they're obviously invalid.

Output format (JSON):
{
  "perturbed_payload": <modified payload>,
  "perturbation": {
    "type": "string (strategy name)",
    "changes": [list of changes made],
    "magnitude": float (0.0-1.0, severity of perturbation)
  },
  "attack_vector": "string (attack type)",
  "reasoning": "string (why this attack is relevant)"
}"""

        user_message = f"Original payload:\n{json.dumps(payload, indent=2)}\n\nApply adversarial perturbations."
        
        try:
            start_time = time.time()
            
            response = self.attacker_client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            
            attack_time = time.time() - start_time
            
            # Extract JSON from response
            content = response.content[0].text
            
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content.strip()
            
            attack_result = json.loads(json_str)
            
            attack_result["timestamp"] = datetime.now(timezone.utc).isoformat()
            attack_result["attack_time"] = attack_time
            
            print(f"[Agent 2] Applied attack '{attack_result.get('attack_vector', 'unknown')}' in {attack_time:.2f}s")
            
            return attack_result
            
        except Exception as e:
            print(f"[Agent 2] Attack failed: {e}")
            # Return original payload if attack fails
            return {
                "perturbed_payload": payload,
                "perturbation": {"type": "none", "changes": [], "magnitude": 0.0},
                "attack_vector": "none",
                "reasoning": f"Attack failed: {e}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "attack_time": 0.0
            }
    
    def agent3_validate(
        self, 
        payload: Dict[str, Any], 
        generator_output: Dict[str, Any],
        attack_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Phase 3: Validation (Agent 3)
        
        Validates perturbed payload using Agent 3 Validator.
        
        Args:
            payload: Perturbed payload from Agent 2
            generator_output: Original output from Agent 1
            attack_result: Attack result from Agent 2
            
        Returns:
            Validation result with state (NULL/DUCTILE/CRYSTALLINE)
        """
        start_time = time.time()
        
        validation_result = self.agent3.evaluate_payload(
            payload=payload,
            generator_output=generator_output,
            attacker_perturbation=attack_result.get("perturbation", {})
        )
        
        validation_time = time.time() - start_time
        
        # Update metrics
        self.metrics.total_validation_time += validation_time
        
        state = validation_result["validation_result"]["state"]
        
        if state == "NULL":
            self.metrics.null_count += 1
        elif state == "DUCTILE":
            self.metrics.ductile_count += 1
        elif state == "CRYSTALLINE":
            self.metrics.crystalline_count += 1
        
        print(f"[Agent 3] Validation complete: {state} (in {validation_time:.2f}s)")
        
        return validation_result
    
    def execute_loop(
        self, 
        prompt: str, 
        max_iterations: int = 5,
        save_history: bool = True
    ) -> Dict[str, Any]:
        """
        Execute complete Ouroboros loop with restart on NULL
        
        Loop behavior:
        - NULL: Trigger restart, increment iteration counter
        - DUCTILE: Apply corrections, re-validate (no loop restart)
        - CRYSTALLINE: Lock payload, advance orchestration
        
        Args:
            prompt: Natural language task description
            max_iterations: Maximum number of loop iterations
            save_history: Save iteration history to file
            
        Returns:
            Final result with:
                - final_payload: Crystallized payload (if converged)
                - final_state: Final validation state
                - metrics: Loop execution metrics
                - history: Iteration history
        """
        print(f"\n{'='*60}")
        print(f"OUROBOROS PROTOCOL - Starting Loop")
        print(f"Prompt: {prompt}")
        print(f"Max Iterations: {max_iterations}")
        print(f"{'='*60}\n")
        
        iteration = 0
        constraints = None
        final_payload = None
        final_state = None
        
        while iteration < max_iterations:
            iteration += 1
            self.metrics.total_iterations = iteration
            
            print(f"\n--- Iteration {iteration}/{max_iterations} ---")
            
            iteration_start = time.time()
            
            # Phase 1: Generation
            print("\n[Phase 1] Generator (Agent 1)")
            generator_output = self.agent1_generate(prompt, constraints)
            payload = generator_output["payload"]
            
            # Phase 2: Attack
            print("\n[Phase 2] Attacker (Agent 2)")
            attack_result = self.agent2_attack(payload)
            perturbed_payload = attack_result["perturbed_payload"]
            
            # Phase 3: Validation
            print("\n[Phase 3] Validator (Agent 3)")
            validation_result = self.agent3_validate(
                perturbed_payload,
                generator_output,
                attack_result
            )
            
            state = validation_result["validation_result"]["state"]
            iteration_time = time.time() - iteration_start
            
            # Record iteration
            iteration_record = {
                "iteration": iteration,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "generator_output": generator_output,
                "attack_result": attack_result,
                "validation_result": validation_result,
                "state": state,
                "iteration_time": iteration_time
            }
            self.iteration_history.append(iteration_record)
            
            print(f"\n[Iteration {iteration}] State: {state} (took {iteration_time:.2f}s)")
            
            # Handle state
            if state == "NULL":
                print(f"[NULL] Triggering restart (attempt {iteration}/{max_iterations})")
                self.metrics.restart_count += 1
                
                # Extract constraints from validation result
                eval_summary = validation_result["validation_result"]["evaluation_summary"]
                hw_details = validation_result["validation_result"]["detailed_analysis"]["hardware_grounding"]
                
                constraints = {
                    "max_vram_bytes": int(hw_details.get("vram_available", 3865051136) * 0.9),
                    "max_compute_intensity": 0.75,
                    "thermal_margin_required": 5.0,
                    "corrections_required": eval_summary.get("corrections_required", [])
                }
                
                print(f"[NULL] Constraints for next iteration: {json.dumps(constraints, indent=2)}")
                continue
                
            elif state == "DUCTILE":
                print(f"[DUCTILE] Applying corrections")
                
                # Apply corrections
                corrected_payload = self.agent3.apply_rigid_filtering(perturbed_payload)
                
                # Re-validate (no full restart)
                print("[DUCTILE] Re-validating corrected payload")
                revalidation_result = self.agent3_validate(
                    corrected_payload,
                    generator_output,
                    attack_result
                )
                
                revalidation_state = revalidation_result["validation_result"]["state"]
                
                if revalidation_state == "CRYSTALLINE":
                    print(f"[DUCTILE→CRYSTALLINE] Payload crystallized after corrections")
                    final_payload = corrected_payload
                    final_state = "CRYSTALLINE"
                    self.metrics.convergence_iteration = iteration
                    break
                elif revalidation_state == "DUCTILE":
                    print(f"[DUCTILE→DUCTILE] Still ductile, but acceptable")
                    final_payload = corrected_payload
                    final_state = "DUCTILE"
                    self.metrics.convergence_iteration = iteration
                    break
                else:
                    print(f"[DUCTILE→NULL] Corrections insufficient, restarting")
                    self.metrics.restart_count += 1
                    
                    # Extract new constraints
                    eval_summary = revalidation_result["validation_result"]["evaluation_summary"]
                    hw_details = revalidation_result["validation_result"]["detailed_analysis"]["hardware_grounding"]
                    
                    constraints = {
                        "max_vram_bytes": int(hw_details.get("vram_available", 3865051136) * 0.8),
                        "max_compute_intensity": 0.65,
                        "thermal_margin_required": 7.0,
                        "corrections_required": eval_summary.get("corrections_required", [])
                    }
                    continue
                    
            elif state == "CRYSTALLINE":
                print(f"[CRYSTALLINE] Payload locked and ready for orchestration")
                final_payload = perturbed_payload
                final_state = "CRYSTALLINE"
                self.metrics.convergence_iteration = iteration
                break
        
        # Finalize
        if self.metrics.convergence_iteration is None:
            print(f"\n[FAILED] Did not converge after {max_iterations} iterations")
            final_state = "FAILED"
        
        result = {
            "final_payload": final_payload,
            "final_state": final_state,
            "converged": self.metrics.convergence_iteration is not None,
            "metrics": self.metrics.to_dict(),
            "history": self.iteration_history
        }
        
        # Save history
        if save_history:
            self._save_history(result)
        
        # Print summary
        self._print_summary(result)
        
        return result
    
    def _save_history(self, result: Dict[str, Any]) -> None:
        """Save iteration history to file"""
        logs_dir = Path(__file__).parent.parent.parent / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = logs_dir / f"ouroboros_loop_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n[History] Saved to {filename}")
    
    def _print_summary(self, result: Dict[str, Any]) -> None:
        """Print execution summary"""
        print(f"\n{'='*60}")
        print(f"OUROBOROS PROTOCOL - Loop Summary")
        print(f"{'='*60}")
        print(f"Final State: {result['final_state']}")
        print(f"Converged: {result['converged']}")
        print(f"\nMetrics:")
        metrics = result['metrics']
        print(f"  Total Iterations: {metrics['total_iterations']}")
        print(f"  NULL Count: {metrics['null_count']}")
        print(f"  DUCTILE Count: {metrics['ductile_count']}")
        print(f"  CRYSTALLINE Count: {metrics['crystalline_count']}")
        print(f"  Restart Count: {metrics['restart_count']}")
        print(f"  Average Validation Time: {metrics['average_validation_time']:.2f}s")
        print(f"  Convergence Rate: {metrics['convergence_rate']:.2f}")
        if metrics['convergence_iteration']:
            print(f"  Converged at Iteration: {metrics['convergence_iteration']}")
        print(f"{'='*60}\n")


def validate_payload(
    payload: Dict[str, Any],
    invariant_truth: Dict[str, Any],
    ashard_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Standalone validation function (convenience wrapper)
    
    Args:
        payload: Payload to validate
        invariant_truth: Mathematical constraints
        ashard_params: Hardware constraints
        
    Returns:
        Validation result
    """
    validator = OuroborosAgent3Validator(
        invariant_truth=invariant_truth,
        ashard_params=ashard_params
    )
    
    return validator.evaluate_payload(
        payload=payload,
        generator_output={"payload": payload},
        attacker_perturbation={}
    )
