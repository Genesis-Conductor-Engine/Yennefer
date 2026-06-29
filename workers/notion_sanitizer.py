"""
Notion Sanitizer - Pre-annealment Payload Validation
Envelope Version: 0.3.0
"""

import math
import logging
from typing import Dict, Tuple, Any
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NotionSanitizer:
    """
    Pre-annealment payload sanitization for Notion API submissions.
    Validates thermodynamic telemetry before POST.
    """
    
    def __init__(self, envelope_version: str = "0.3.0"):
        self.envelope_version = envelope_version
        self.validation_log = []
        
    def validate_payload(self, payload: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Validate Notion payload before POST.
        
        Returns:
            (status, sanitized_payload)
            status: "CLEAN" | "SANITIZED" | "REJECTED"
        """
        status = "CLEAN"
        issues = []
        sanitized = payload.copy()
        
        # Validate η_thermo
        if "eta_thermo" in sanitized:
            eta = sanitized["eta_thermo"]
            if not self._is_valid_number(eta):
                issues.append(f"Invalid η_thermo: {eta}")
                sanitized["eta_thermo"] = 0.0
                status = "SANITIZED"
            elif not (0.0 <= eta <= 1.0):
                issues.append(f"η_thermo out of range: {eta}")
                sanitized["eta_thermo"] = max(0.0, min(1.0, eta))
                status = "SANITIZED"
        
        # Validate ε
        if "epsilon" in sanitized:
            eps = sanitized["epsilon"]
            if not self._is_valid_number(eps):
                issues.append(f"Invalid ε: {eps}")
                sanitized["epsilon"] = 0.0
                status = "SANITIZED"
            elif not (0.0 <= eps <= 1.0):
                issues.append(f"ε out of range: {eps}")
                sanitized["epsilon"] = max(0.0, min(1.0, eps))
                status = "SANITIZED"
        
        # Validate γ
        if "gamma" in sanitized:
            gamma = sanitized["gamma"]
            if not self._is_valid_number(gamma):
                issues.append(f"Invalid γ: {gamma}")
                sanitized["gamma"] = 0.05
                status = "SANITIZED"
        
        # Validate Δq
        if "delta_q" in sanitized:
            dq = sanitized["delta_q"]
            if not self._is_valid_number(dq):
                issues.append(f"Invalid Δq: {dq}")
                sanitized["delta_q"] = 0.05
                status = "SANITIZED"
        
        # Validate VRAM percentage
        if "vram_jax_pct" in sanitized:
            vram = sanitized["vram_jax_pct"]
            if not self._is_valid_number(vram):
                issues.append(f"Invalid VRAM: {vram}")
                sanitized["vram_jax_pct"] = 0.0
                status = "SANITIZED"
            elif not (0.0 <= vram <= 100.0):
                issues.append(f"VRAM out of range: {vram}")
                sanitized["vram_jax_pct"] = max(0.0, min(100.0, vram))
                status = "SANITIZED"
        
        # Validate crystalline score
        if "crystalline_score" in sanitized:
            score = sanitized["crystalline_score"]
            if not self._is_valid_number(score):
                issues.append(f"Invalid crystalline_score: {score}")
                sanitized["crystalline_score"] = 0.0
                status = "SANITIZED"
            elif not (0.0 <= score <= 1.0):
                issues.append(f"crystalline_score out of range: {score}")
                sanitized["crystalline_score"] = max(0.0, min(1.0, score))
                status = "SANITIZED"
        
        # Check for critical corruption - reject if too many issues
        if len(issues) > 5:
            status = "REJECTED"
            logger.error(f"Payload REJECTED - too many issues: {issues}")
            self._create_envelope_capsule(payload, issues)
            return status, None
        
        # Log sanitization
        if status != "CLEAN":
            logger.warning(f"Payload {status}: {issues}")
            sanitized["sanitization_notes"] = "; ".join(issues)
        
        self.validation_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "status": status,
            "issues": issues
        })
        
        return status, sanitized
    
    def _is_valid_number(self, value: Any) -> bool:
        """Check if value is a valid number (not NaN, inf)."""
        if value is None:
            return False
        try:
            if math.isnan(value) or math.isinf(value):
                return False
            return True
        except (TypeError, ValueError):
            return False
    
    def _create_envelope_capsule(self, payload: Dict[str, Any], issues: list):
        """
        Create envelope capsule for rejected payloads.
        Log to isolated #!nox reframe.
        """
        capsule = {
            "envelope_version": self.envelope_version,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "REJECTED",
            "original_payload": payload,
            "validation_issues": issues,
            "reframe_marker": "#!nox"
        }
        
        # Write to isolated reframe log
        capsule_path = f"/home/diamondnode/diamondnode-unified-inference/logs/rejected_capsules_{datetime.utcnow().strftime('%Y%m%d')}.log"
        try:
            with open(capsule_path, "a") as f:
                f.write(f"{capsule}\n")
            logger.info(f"Envelope capsule written to {capsule_path}")
        except Exception as e:
            logger.error(f"Failed to write envelope capsule: {e}")
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of recent validations."""
        if not self.validation_log:
            return {"total": 0, "clean": 0, "sanitized": 0, "rejected": 0}
        
        total = len(self.validation_log)
        clean = sum(1 for v in self.validation_log if v["status"] == "CLEAN")
        sanitized = sum(1 for v in self.validation_log if v["status"] == "SANITIZED")
        rejected = sum(1 for v in self.validation_log if v["status"] == "REJECTED")
        
        return {
            "total": total,
            "clean": clean,
            "sanitized": sanitized,
            "rejected": rejected,
            "clean_rate": clean / total if total > 0 else 0
        }


if __name__ == "__main__":
    # Test sanitizer
    sanitizer = NotionSanitizer()
    
    print(f"Notion Sanitizer v{sanitizer.envelope_version}")
    print("=" * 50)
    
    # Test 1: Clean payload
    clean_payload = {
        "eta_thermo": 0.75,
        "epsilon": 0.50,
        "gamma": 0.05,
        "delta_q": 0.08,
        "vram_jax_pct": 42.5,
        "crystalline_score": 0.82
    }
    status, result = sanitizer.validate_payload(clean_payload)
    print(f"\nTest 1 - Clean Payload: {status}")
    print(f"  Result: {result}")
    
    # Test 2: NaN values
    nan_payload = {
        "eta_thermo": float('nan'),
        "epsilon": 0.50,
        "vram_jax_pct": float('inf')
    }
    status, result = sanitizer.validate_payload(nan_payload)
    print(f"\nTest 2 - NaN/Inf Payload: {status}")
    print(f"  Result: {result}")
    
    # Test 3: Out of range
    oor_payload = {
        "eta_thermo": 1.5,
        "epsilon": -0.2,
        "vram_jax_pct": 150.0
    }
    status, result = sanitizer.validate_payload(oor_payload)
    print(f"\nTest 3 - Out of Range Payload: {status}")
    print(f"  Result: {result}")
    
    # Summary
    print("\nValidation Summary:")
    summary = sanitizer.get_validation_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
