# aSHARD Configuration for Yennefer Deployment

## Overview

aSHARD (bare-metal GPU) configuration for NVIDIA GTX 1650 deployment in the Yennefer telemetry system.

## Hardware Specifications

- **GPU**: NVIDIA GeForce GTX 1650
- **VRAM**: 3.63 GB (3,895,918,592 bytes)
- **Compute Capability**: 7.5 (Turing architecture)
- **Tensor Cores**: None (GTX series)
- **Multi-processors**: 14
- **Max Temperature**: 89.6°C (hardware limit)

## Configuration Files

### Main Config: `config/ashard_config.yaml`

VRAM allocation strategy:
- **enkg_kernel**: 1.63 GB (50%) - Triton kernel operations
- **orchestration**: 815 MB (25%) - Claude orchestration
- **buffer**: 815 MB (25%) - Safety buffer

Thermal management:
- **Warning threshold**: 85°C - Start throttling
- **Critical threshold**: 89°C - Emergency stop
- **Throttle factor**: 0.7 (reduce to 70% capacity)

## Scripts

### 1. GPU Detection: `scripts/detect_ashard.py`

Detects GPU capabilities and validates configuration:

```bash
python scripts/detect_ashard.py
```

Output:
- CUDA availability
- Device specifications
- Recommended configuration
- Config validation results

### 2. Allocation Test: `scripts/test_ashard_allocation.py`

Tests VRAM allocation and Triton kernel execution:

```bash
python scripts/test_ashard_allocation.py
```

Tests:
- ✓ Thermal check before starting
- ✓ VRAM allocation per config
- ✓ Basic GPU tensor operations
- ✓ Triton kernel execution
- ✓ Memory cleanup
- ✓ Gateway integration (if credentials available)

### 3. Thermal Monitor: `scripts/thermal_monitor.py`

Continuous GPU temperature and VRAM monitoring:

```bash
python scripts/thermal_monitor.py
```

Features:
- Real-time temperature monitoring
- VRAM usage tracking
- Thermal throttling alerts
- Emergency stop recommendations
- Diamond Gateway integration

Output example:
```
[2026-05-20 00:15:30] Temp: 42.0°C | VRAM: 1.23/3.63GB (33.9%) | Status: OK
```

## Integration with Diamond Gateway

The aSHARD configuration integrates with Diamond Gateway (`localhost:8000`) for:

1. **Metrics polling**: `/metrics` endpoint
   - GPU temperature
   - VRAM usage
   - Power consumption

2. **Orchestration**: `/v1/orchestrate` endpoint
   - Hamiltonian calculation: `H(s) = (VRAM_Used / VRAM_Total) * 10`
   - OFFLOAD trigger when `H(s) > 8.5`
   - Notion soul-capsule persistence

## Usage in Yennefer

### Initialization

```python
import yaml
import torch

# Load config
with open("config/ashard_config.yaml") as f:
    config = yaml.safe_load(f)

ashard = config["ashard"]
device = torch.device(ashard["device"])

# Allocate VRAM
allocation = ashard["vram_allocation"]
kernel_buffer = torch.zeros(
    allocation["enkg_kernel"] // 4,  # float32 = 4 bytes
    dtype=torch.float32,
    device=device
)
```

### Thermal Check

```python
import pynvml

pynvml.nvmlInit()
handle = pynvml.nvmlDeviceGetHandleByIndex(0)
temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)

if temp >= 85.0:
    # Throttle workload
    pass
elif temp >= 89.0:
    # Emergency stop
    pass
```

### Gateway Integration

```python
import requests
import os

gateway_url = "http://localhost:8000/metrics"
token = os.getenv("GATEWAY_SECRET")

response = requests.get(
    gateway_url,
    headers={"Authorization": f"Bearer {token}"}
)

metrics = response.json()
# Use metrics.vram_used_mib, metrics.temperature, etc.
```

## Monitoring Recommendations

1. **Continuous monitoring**: Run `thermal_monitor.py` as daemon
2. **Pre-allocation checks**: Run `detect_ashard.py` before deployment
3. **Test allocations**: Run `test_ashard_allocation.py` after config changes
4. **Gateway health**: Monitor `http://localhost:8000/health`

## Thermal Throttling Strategy

| Temperature | Action | Description |
|-------------|--------|-------------|
| < 85°C | Normal operation | Full GPU utilization |
| 85-89°C | Throttle | Reduce to 70% capacity, increase check interval |
| > 89°C | Emergency stop | Halt all GPU workloads, cool down |

## Known Limitations

1. **No tensor cores**: GTX 1650 lacks hardware tensor cores (GTX vs RTX)
   - Triton kernels work but without tensor acceleration
   - Mixed precision (FP16/BF16) slower than RTX series

2. **VRAM ceiling**: 3.63 GB total, ~3.27 GB usable after allocation
   - Large models require quantization or offloading
   - Batch size limited to 8 (configurable)

3. **Thermal headroom**: Max 89.6°C leaves minimal safety margin
   - Active cooling recommended
   - Ambient temperature monitoring critical

## Troubleshooting

### OOM (Out of Memory)

```bash
# Check current allocation
nvidia-smi

# Clear PyTorch cache
python -c "import torch; torch.cuda.empty_cache()"

# Adjust config allocations in ashard_config.yaml
```

### Thermal throttling

```bash
# Check current temperature
nvidia-smi --query-gpu=temperature.gpu --format=csv

# Monitor continuously
watch -n 1 nvidia-smi
```

### Gateway connection failed

```bash
# Check gateway status
curl http://localhost:8000/health

# Verify credentials
echo $GATEWAY_SECRET

# Test metrics endpoint
curl -H "Authorization: Bearer $GATEWAY_SECRET" \
  http://localhost:8000/metrics
```

## Next Steps

1. ✅ Configuration created and validated
2. ✅ GPU detection working
3. ✅ Allocation tests passing
4. ✅ Triton kernel execution confirmed
5. ✅ Thermal monitoring implemented
6. 🔄 Deploy to production Yennefer pipeline
7. 🔄 Integrate with Claude orchestration
8. 🔄 Configure systemd service for thermal_monitor.py

## References

- Diamond Gateway: `http://localhost:8000`
- Notion soul-capsule DB: `21e416066ef1411084d1bbaf67af79d1`
- CUDA-Q QAOA simulation: `~/diamond-node/scripts/mycelial_qubo.py`
- Unified inference orchestrator: `~/diamondnode-unified-inference/src/orchestrator/`
