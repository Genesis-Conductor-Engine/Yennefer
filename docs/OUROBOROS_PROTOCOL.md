# Ouroboros Protocol Implementation

Complete Generator→Attacker→Validator loop for the Ouroboros Protocol.

## Overview

The Ouroboros Protocol implements a three-agent self-validating architecture:

1. **Agent 1 (Generator)**: Generates structured payloads from natural language prompts
2. **Agent 2 (Attacker)**: Applies adversarial perturbations to test robustness
3. **Agent 3 (Validator)**: Validates and classifies payloads as NULL/DUCTILE/CRYSTALLINE

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Ouroboros Protocol                     │
│                                                          │
│  ┌──────────────┐                                       │
│  │  Agent 1     │  Natural language prompt              │
│  │  Generator   │  ──────────────────►                  │
│  │  (Claude)    │  Structured payload                   │
│  └──────┬───────┘                                       │
│         │                                                │
│         ▼                                                │
│  ┌──────────────┐                                       │
│  │  Agent 2     │  Original payload                     │
│  │  Attacker    │  ──────────────────►                  │
│  │  (Claude)    │  Perturbed payload                    │
│  └──────┬───────┘                                       │
│         │                                                │
│         ▼                                                │
│  ┌──────────────┐                                       │
│  │  Agent 3     │  Validation result:                   │
│  │  Validator   │  • CRYSTALLINE → Lock & advance       │
│  │  (Seismic    │  • DUCTILE → Apply corrections        │
│  │   ToT)       │  • NULL → Restart with constraints    │
│  └──────────────┘                                       │
│         │                                                │
│         ├─────► CRYSTALLINE ──────► DONE                │
│         ├─────► DUCTILE ──────► Correct & retry         │
│         └─────► NULL ──────► Restart loop               │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Loop Behavior

### NULL State
- **Trigger**: Critical validation failure
- **Action**: Full restart with corrected constraints
- **Increments**: `restart_count`, `null_count`, `iteration`

### DUCTILE State
- **Trigger**: Acceptable with corrections required
- **Action**: Apply rigid filtering, re-validate
- **No full restart**: Corrections applied in-place

### CRYSTALLINE State
- **Trigger**: Perfect validation score
- **Action**: Lock payload and advance orchestration
- **Result**: Loop exits successfully

## Installation

```bash
cd ~/diamondnode-unified-inference
source yennefer_venv/bin/activate

# Install dependencies
pip install anthropic pyyaml

# Set API key
export ANTHROPIC_API_KEY="your-api-key"
# or
source ~/load-env.sh
```

## Quick Start

```python
from ouroboros_protocol import OuroborosProtocol
from agent3_validator import OuroborosAgent3Validator

# Define invariant truth (mathematical constraints)
invariant_truth = {
    "conservation_laws": ["energy_conservation", "momentum_preservation"],
    "symmetries": ["time_reversal", "gauge_invariance"],
    "dimensional_constraints": {
        "max_matrix_size": 2048,
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

print(f"Final State: {result['final_state']}")
print(f"Converged: {result['converged']}")
print(f"Iterations: {result['metrics']['total_iterations']}")
```

## Running Examples

### Quick Test
```bash
cd ~/diamondnode-unified-inference
source ~/load-env.sh
yennefer_venv/bin/python examples/test_ouroboros.py
```

### Full Example Suite
```bash
cd ~/diamondnode-unified-inference
source ~/load-env.sh
yennefer_venv/bin/python examples/run_ouroboros.py
```

Available examples:
1. Simple Matrix Multiplication
2. CUDA-Q Quantum Simulation
3. ML Inference (YOLO11)
4. Stress Test (Tight VRAM Constraints)

## API Reference

### `OuroborosProtocol`

#### Constructor
```python
OuroborosProtocol(
    agent3_validator: OuroborosAgent3Validator,
    llm_generator: Optional[Any] = None,
    llm_attacker: Optional[Any] = None,
    api_key: Optional[str] = None,
    model: str = "claude-opus-4-20250514",
    max_tokens: int = 4096
)
```

#### Methods

##### `agent1_generate(prompt: str, constraints: Optional[Dict] = None) -> Dict`
Generate structured payload from natural language prompt.

**Args:**
- `prompt`: Natural language task description
- `constraints`: Optional constraints from previous NULL states

**Returns:**
```python
{
    "payload": {...},
    "reasoning": "...",
    "timestamp": "...",
    "generation_time": 1.23,
    "model": "claude-opus-4-20250514",
    "constraints_applied": False
}
```

##### `agent2_attack(payload: Dict) -> Dict`
Apply adversarial perturbations to payload.

**Args:**
- `payload`: Payload from Agent 1

**Returns:**
```python
{
    "perturbed_payload": {...},
    "perturbation": {
        "type": "resource_stress",
        "changes": [...],
        "magnitude": 0.75
    },
    "attack_vector": "vram_stress",
    "reasoning": "...",
    "timestamp": "...",
    "attack_time": 0.56
}
```

##### `agent3_validate(payload: Dict, generator_output: Dict, attack_result: Dict) -> Dict`
Validate perturbed payload using Agent 3.

**Args:**
- `payload`: Perturbed payload from Agent 2
- `generator_output`: Original output from Agent 1
- `attack_result`: Attack result from Agent 2

**Returns:**
```python
{
    "validation_result": {
        "state": "CRYSTALLINE",  # or DUCTILE or NULL
        "timestamp": "...",
        "evaluation_summary": {...},
        "detailed_analysis": {...},
        "recommendations": {...}
    }
}
```

##### `execute_loop(prompt: str, max_iterations: int = 5, save_history: bool = True) -> Dict`
Execute complete Ouroboros loop with restart on NULL.

**Args:**
- `prompt`: Natural language task description
- `max_iterations`: Maximum loop iterations (default: 5)
- `save_history`: Save iteration history to file (default: True)

**Returns:**
```python
{
    "final_payload": {...},
    "final_state": "CRYSTALLINE",
    "converged": True,
    "metrics": {
        "total_iterations": 3,
        "null_count": 1,
        "ductile_count": 1,
        "crystalline_count": 1,
        "restart_count": 1,
        "convergence_iteration": 3,
        "average_validation_time": 2.45,
        "convergence_rate": 0.33
    },
    "history": [...]
}
```

### `OuroborosMetrics`

Tracks loop execution metrics:

```python
@dataclass
class OuroborosMetrics:
    total_iterations: int = 0
    null_count: int = 0
    ductile_count: int = 0
    crystalline_count: int = 0
    total_validation_time: float = 0.0
    restart_count: int = 0
    convergence_iteration: Optional[int] = None
```

**Properties:**
- `average_validation_time`: Average time per validation
- `convergence_rate`: Convergence rate (1.0 = first try)

## Configuration

### Hardware Constraints (aSHARD)

Default for GTX 1650:
```python
{
    "vram_total_bytes": 4294967296,  # 4GB
    "vram_allocation_buffer": 0.9,   # 90% safety margin
    "thermal_max_celsius": 89.6,
    "compute_capability": (7, 5),
    "memory_bandwidth_gbps": 128.0
}
```

### Invariant Truth

Mathematical constraints for validation:
```python
{
    "conservation_laws": [
        "energy_conservation",
        "momentum_preservation",
        "information_conservation"
    ],
    "symmetries": [
        "time_reversal",
        "gauge_invariance",
        "translation_symmetry"
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
```

## Metrics and Monitoring

### Iteration History

Each iteration is recorded with:
- Generator output
- Attack result
- Validation result
- State (NULL/DUCTILE/CRYSTALLINE)
- Iteration time

History is saved to `logs/ouroboros_loop_YYYYMMDD_HHMMSS.json`.

### Convergence Tracking

```python
# Check if loop converged
if result['converged']:
    print(f"Converged at iteration {result['metrics']['convergence_iteration']}")
else:
    print("Did not converge")

# Convergence rate (1.0 = first try, 0.33 = third try)
print(f"Convergence rate: {result['metrics']['convergence_rate']:.2f}")
```

### State Distribution

```python
metrics = result['metrics']
total = metrics['total_iterations']

print(f"NULL: {metrics['null_count']} ({metrics['null_count']/total*100:.1f}%)")
print(f"DUCTILE: {metrics['ductile_count']} ({metrics['ductile_count']/total*100:.1f}%)")
print(f"CRYSTALLINE: {metrics['crystalline_count']} ({metrics['crystalline_count']/total*100:.1f}%)")
```

## Integration with Diamond Gateway

The Ouroboros Protocol integrates with the Diamond Gateway for VRAM orchestration:

```python
# Query VRAM status before execution
import requests

response = requests.get(
    "http://localhost:8000/v1/orchestrate",
    headers={"Authorization": f"Bearer {gateway_secret}"},
    json={"session_id": "ouroboros-session"}
)

hamiltonian = response.json()["hamiltonian"]

if hamiltonian > 8.5:
    print("VRAM critical - trigger OFFLOAD")
else:
    # Execute Ouroboros loop
    result = protocol.execute_loop(prompt)
```

## Troubleshooting

### API Key Not Found
```
ValueError: No ANTHROPIC_API_KEY found
```

**Solution:**
```bash
export ANTHROPIC_API_KEY="your-key"
# or
source ~/load-env.sh
```

### Module Import Errors
```
ImportError: cannot import name 'OuroborosProtocol'
```

**Solution:**
```bash
# Ensure you're in the correct directory
cd ~/diamondnode-unified-inference

# Check Python path
python -c "import sys; print(sys.path)"

# Add src to path in your script
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "orchestrator"))
```

### NULL States Not Restarting

Check that `max_iterations` is sufficient:
```python
result = protocol.execute_loop(
    prompt="...",
    max_iterations=10  # Increase if needed
)
```

### Validation Takes Too Long

Reduce `max_tokens` or use faster model:
```python
protocol = OuroborosProtocol(
    agent3_validator=validator,
    model="claude-sonnet-4-20250514",  # Faster
    max_tokens=2048  # Reduce token budget
)
```

## Performance

Typical execution times on GTX 1650:

| Phase | Time (avg) |
|-------|------------|
| Generator (Agent 1) | 1.5s |
| Attacker (Agent 2) | 0.8s |
| Validator (Agent 3) | 2.2s |
| **Total per iteration** | **4.5s** |

Convergence typically occurs in 2-4 iterations.

## License

MIT License - see LICENSE file for details

## References

- Agent 3 Validator: `src/orchestrator/agent3_validator.py`
- System Prompt: `config/agent3_system_prompt.yaml`
- Claude Orchestrator: `src/orchestrator/claude_orchestrator.py`
- Diamond Gateway: `/opt/diamond-gateway/gateway.py`
