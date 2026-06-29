# Agent 3 - Validator (Ouroboros Protocol)

## Overview

Agent 3 is the Validator in the Ouroboros Protocol, implementing a **Seismic Tree-of-Thoughts** methodology to rigorously evaluate payloads from Agent 1 (Generator) and Agent 2 (Attacker).

## Location

- **System Prompt**: `~/diamondnode-unified-inference/config/agent3_system_prompt.yaml`
- **Implementation**: `~/diamondnode-unified-inference/src/orchestrator/agent3_validator.py`
- **Tests**: `~/diamondnode-unified-inference/tests/test_agent3_validator.py`

## Validation Phases

### 1. Seismic Scan
Analyzes payload structure and traces provenance through the Generator→Attacker chain.
- Computes topology hash for payload identification
- Measures perturbation magnitude (L2 norm of changes)
- Checks structural integrity

### 2. Topological Validation
Verifies mathematical invariants and constraints:
- Conservation laws (energy, momentum, information)
- Dimensional consistency
- Symmetry preservation
- Boundary condition integrity

**Score**: `[0.0, 1.0]` where >= 0.75 is CRYSTALLINE grade

### 3. Hardware Grounding (aSHARD)
Validates against physical GPU constraints:
- **VRAM Budget**: 4GB limit (GTX 1650) with 90% allocation buffer
- **Thermal Envelope**: Max 89.6°C, minimum 2°C margin required
- **Compute Capability**: 7.5 alignment
- **Memory Bandwidth**: 128 GB/s feasibility

### 4. Operational Authority (PI Scope)
Validates Process Invariance boundaries:
- Operation whitelist compliance
- Resource limit enforcement
- State transition legality
- Execution safety verification

### 5. Crystallization Decision
Synthesizes all metrics into final state classification.

## Output States

### NULL
**Critical failure** - Payload rejected completely.

**Triggers**:
- Invariant score < 0.3
- VRAM requirement exceeds 4GB
- Thermal margin < 2°C
- PI scope boundary violated
- Critical symmetry broken
- Dimensional mismatch

**Action**: Trigger restart cycle, signal Generator for constraint correction

### DUCTILE
**Acceptable with corrections** - Payload can be salvaged.

**Conditions**:
- 0.3 <= invariant_score < 0.75
- Hardware constraints met but not optimal
- Minor corrections required

**Action**: Apply rigid filtering, annotate transformations, retry

### CRYSTALLINE
**Perfect** - Payload ready for production execution.

**Requirements**:
- Invariant score >= 0.75
- VRAM utilization <= 75% (not too tight)
- Thermal margin >= 5°C
- All conservation laws satisfied
- PI scope fully contained
- No structural violations

**Action**: Commit to execution pipeline

## Usage

### Basic Usage

```python
from orchestrator.agent3_validator import OuroborosAgent3Validator

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

# Evaluate payload
result = validator.evaluate_payload(
    payload=my_payload,
    generator_output=agent1_output,
    attacker_perturbation=agent2_perturbation
)

print(f"State: {result['validation_result']['state']}")
```

### Convenience Function

```python
from orchestrator.agent3_validator import validate_payload

result = validate_payload(
    payload=my_payload,
    invariant_truth={...}
)
```

### Rigid Filtering (DUCTILE Correction)

```python
corrected = validator.apply_rigid_filtering(payload)
# Automatically enforces:
# - VRAM limits
# - Matrix size constraints  
# - Compute intensity caps
```

## Hardware Constraints (aSHARD)

Default configuration for **NVIDIA GTX 1650**:

```python
AShardParams(
    vram_total_bytes=4294967296,      # 4GB
    vram_allocation_buffer=0.9,        # 90% safety margin
    thermal_max_celsius=89.6,
    compute_capability=(7, 5),
    memory_bandwidth_gbps=128.0
)
```

Override for different hardware:

```python
validator = OuroborosAgent3Validator(
    invariant_truth=invariant_truth,
    ashard_params={
        "vram_total_bytes": 8589934592,  # 8GB
        "thermal_max_celsius": 85.0
    }
)
```

## Testing

Run full test suite:

```bash
cd ~/diamondnode-unified-inference
source ~/venv312/bin/activate
python tests/test_agent3_validator.py
```

**Test Coverage**:
- ✅ CRYSTALLINE state (perfect payload)
- ✅ NULL state (VRAM overflow)
- ✅ NULL state (invariant violation)
- ✅ NULL state (PI scope violation)
- ✅ DUCTILE state (acceptable with corrections)
- ✅ Rigid filtering (payload correction)
- ✅ Seismic scan (perturbation detection)
- ✅ Convenience function

## Integration with Ouroboros Protocol

```
┌─────────────┐
│   Agent 1   │ Generator
│  (Generator)│──┐
└─────────────┘  │
                 ▼
              ┌─────────────┐
              │   Agent 2   │ Attacker
              │  (Attacker) │──┐
              └─────────────┘  │
                               ▼
                          ┌─────────────┐
                          │   Agent 3   │ Validator
                          │ (Validator) │
                          └─────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
         ┌────────┐         ┌─────────┐       ┌────────────┐
         │  NULL  │         │ DUCTILE │       │CRYSTALLINE │
         │Restart │         │ Correct │       │   Commit   │
         └────────┘         └─────────┘       └────────────┘
```

## Output Format

```json
{
  "validation_result": {
    "state": "CRYSTALLINE",
    "timestamp": "2026-05-20T00:00:00+00:00",
    "evaluation_summary": {
      "topological_score": 1.0,
      "hardware_compliance": true,
      "pi_validity": true,
      "invariant_violations": [],
      "corrections_required": []
    },
    "detailed_analysis": {
      "seismic_scan": {
        "topology_hash": "abc123...",
        "perturbation_magnitude": 0.05,
        "structural_integrity": true
      },
      "topological_validation": {...},
      "hardware_grounding": {...},
      "operational_authority": {...}
    },
    "recommendations": {
      "action": "COMMIT",
      "rationale": "Payload meets all validation criteria",
      "next_steps": ["Execute payload in production pipeline"]
    }
  }
}
```

## Monitoring

```python
# Track restart count
print(f"Restarts: {validator.restart_count}")

# Audit trail
# All NULL states trigger restart events with:
# - Timestamp
# - Restart count
# - Failure reason
# - Corrective action
```

## License

Copyright (c) 2026 Diamond Node Team  
Licensed under the MIT License
