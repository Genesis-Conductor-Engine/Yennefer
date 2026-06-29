# Yennefer Orchestration - Quick Reference

## Files

| File | Purpose |
|------|---------|
| `src/orchestrator/yennefer_orchestrator.py` | Main orchestrator class |
| `src/kernels/enkg_exchange.py` | EnKG Triton kernel |
| `src/orchestrator/agent3_validator.py` | Agent 3 Validator |
| `workers/yennefer_telemetry_daemon.py` | Telemetry daemon |
| `config/ashard_config.yaml` | Hardware config (GTX 1650) |
| `config/yennefer_config.yaml` | Yennefer settings |

## Commands

### Run Orchestrator
```bash
cd ~/diamondnode-unified-inference
source yennefer_venv/bin/activate
python src/orchestrator/yennefer_orchestrator.py --kappa 0.7 --gamma 0.3 --size 1024
```

### Run Tests
```bash
python tests/test_yennefer_orchestrator.py
```

### Start Web UI (with /v1/yennefer endpoint)
```bash
python web/ui/web_ui.py  # Port 8080
```

### Test Endpoint
```bash
curl -X POST http://127.0.0.1:8080/v1/yennefer \
  -H "Content-Type: application/json" \
  -d '{"kappa": 0.7, "gamma": 0.3, "vector_size": 512}'
```

## Ports

| Service | Port | Status |
|---------|------|--------|
| Diamond Gateway | 8000 | ✅ |
| Web UI (FastAPI) | 8080 | ✅ |
| Yennefer Landing | 8090 | 🔄 Future |
| Vibe Swarm API | 8300 | 🔄 Future |

## Validation States

- **NULL:** Invalid or unsafe state
- **DUCTILE:** Acceptable but suboptimal
- **CRYSTALLINE:** Optimal state

## EnKG Operator

M = κI + γσ_x

- **κ (kappa):** Identity component (0-1)
- **γ (gamma):** Pauli-X exchange (0-1)

**Examples:**
- κ=1, γ=0 → Identity (no change)
- κ=0, γ=1 → Pure Pauli-X (swap pairs)
- κ=0.7, γ=0.3 → Mixed (70% identity, 30% exchange)

## Environment Variables

```bash
export GATEWAY_SECRET="..."        # Diamond Gateway auth
export ANTHROPIC_API_KEY="..."     # Agent 3 Validator
export NOTION_TOKEN="..."          # Telemetry daemon
```

Load with: `source ~/load-env.sh`

## Integration Points

1. **EnKG Kernel** → Triton GPU kernel for state vector exchange
2. **Agent 3 Validator** → Seismic Tree-of-Thoughts validation
3. **Diamond Gateway** → VRAM/temp monitoring, H(s) computation
4. **Telemetry Daemon** → Hourly Notion persistence

## Troubleshooting

**Port conflict:** Gateway has priority on 8000  
**CUDA OOM:** Reduce vector_size or batch_size  
**Triton unavailable:** `pip install triton`  
**Gateway 401:** Set `GATEWAY_SECRET` env var  
**Agent 3 fails:** Set `ANTHROPIC_API_KEY`

## Test Results

```
✅ EnKG Kernel....................... PASS
✅ Telemetry Cycle................... PASS
✅ Agent 3 Validation................ PASS
✅ Full Orchestration................ PASS
✅ FastAPI Endpoint.................. PASS

5/5 tests passed (1.52s)
```

## Performance

- **EnKG kernel:** 0.036ms (1K elements, GTX 1650)
- **Telemetry cycle:** ~50ms
- **Agent 3 validation:** ~500ms (Claude API)
- **Full orchestration:** ~562ms

## Documentation

- [Integration Guide](docs/YENNEFER_INTEGRATION_GUIDE.md)
- [Completion Report](YENNEFER_ORCHESTRATION_COMPLETE.md)
- [EnKG Kernel](YENNEFER_ENKG_KERNEL_COMPLETE.md)
- [Telemetry](YENNEFER_TELEMETRY_COMPLETE.md)
