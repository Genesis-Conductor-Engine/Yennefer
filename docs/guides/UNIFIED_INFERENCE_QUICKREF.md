# Unified Inference Server - Quick Reference

## Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────┐
│  CLIENT (WebSocket/HTTP)                                     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│  NODE.JS GATEWAY (Port 3000)                                │
│  • TRTC SDK (audio/video streaming)                         │
│  • HTTP/WebSocket routing                                   │
│  • Load balancing                                           │
└──────┬──────────┬──────────┬──────────┬──────────────────────┘
       │          │          │          │
  ┌────▼───┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐
  │CUDA-Q  │ │YOLO11s │ │Qwen 1.5│ │Metrics │
  │/qaoa   │ │/detect │ │/chat   │ │/health │
  └────┬───┘ └───┬────┘ └───┬────┘ └────────┘
       │         │          │
┌──────▼─────────▼──────────▼──────────────────────────────────┐
│  PYTHON ORCHESTRATOR (Port 8001) - FastAPI                   │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ VRAM Orchestrator (Waveform Equilibrium)               │  │
│  │ • H = (VRAM/Total)*10 + 0.3*(T/89.6)                  │  │
│  │ • Threshold: H > 8.5 → OFFLOAD                        │  │
│  │ • Priority: CUDA-Q(P1) > YOLO(P2) > Qwen(P3)          │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │ CUDA-Q   │  │ YOLO11s  │  │ Qwen 1.5 │                   │
│  │ Service  │  │ Service  │  │ Service  │                   │
│  │ 124 MB   │  │ 1.2 GB   │  │ 2.8 GB   │                   │
│  │ Always   │  │ Keep hot │  │ On-demand│                   │
│  └──────────┘  └──────────┘  └──────────┘                   │
└──────────────────────┬────────────────────────────────────────┘
                       │
            ┌──────────▼───────────┐
            │ GTX 1650 (4 GB VRAM) │
            │ CUDA Streams         │
            │ • Stream 0: CUDA-Q   │
            │ • Stream 1: YOLO11s  │
            │ • Stream 2: Qwen     │
            └──────────┬───────────┘
                       │
      ┌────────────────▼────────────────┐
      │ Diamond Gateway → Notion Bridge │
      │ (OFFLOAD context when H > 8.5)  │
      └─────────────────────────────────┘
```

---

## VRAM State Machine

```
┌──────────────────────────────────────────────────────────────┐
│ STATE 1: IDLE (H = 0.2 - 2.0)                                │
│ CUDA-Q: ✓ Loaded (124 MB)                                    │
│ YOLO11s: ✓ Loaded (1200 MB)                                  │
│ Qwen: ✗ Unloaded                                             │
│ Available: 2676 MB (67%)                                     │
└──────────────────────────────────────────────────────────────┘
                            │
                            │ POST /vision/detect
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ STATE 2: VISION ACTIVE (H = 3.3 - 4.5)                       │
│ CUDA-Q: ✓ Idle (124 MB)                                      │
│ YOLO11s: ▶ Running (1200 MB)                                 │
│ Qwen: ✗ Unloaded                                             │
│ Available: 2676 MB (67%)                                     │
└──────────────────────────────────────────────────────────────┘
                            │
                            │ POST /llm/chat
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ STATE 3: PREP FOR LLM (H = 3.3)                              │
│ Action: Unload YOLO11s to make space                         │
│ CUDA-Q: ✓ Loaded (124 MB)                                    │
│ YOLO11s: ✗ Unloading... → Unloaded                           │
│ Qwen: ⏳ Loading...                                          │
│ Available: 3876 MB → 1076 MB (27%)                           │
└──────────────────────────────────────────────────────────────┘
                            │
                            │ Model loaded
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ STATE 4: LLM ACTIVE (H = 7.3 - 7.8)                          │
│ CUDA-Q: ✓ Idle (124 MB)                                      │
│ YOLO11s: ✗ Unloaded                                          │
│ Qwen: ▶ Running (2800 MB)                                    │
│ Available: 1076 MB (27%)                                     │
└──────────────────────────────────────────────────────────────┘
                            │
                            │ POST /cuda-q/qaoa (while LLM active)
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ STATE 5: SEQUENTIAL EXEC (H = 7.3 - 8.2)                     │
│ CUDA-Q: ⏳ Queued (will use 124 MB of available)            │
│ YOLO11s: ✗ Unloaded                                          │
│ Qwen: ▶ Running (2800 MB)                                    │
│ Note: CUDA-Q waits for Qwen to complete (low VRAM footprint)│
└──────────────────────────────────────────────────────────────┘
                            │
                            │ Temp spike or large batch
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ STATE 6: OFFLOAD TRIGGERED (H > 8.5)                         │
│ Action: Save context → Notion, unload Qwen                   │
│ CUDA-Q: ✓ Loaded (124 MB)                                    │
│ YOLO11s: ✗ Unloaded                                          │
│ Qwen: ✗ Unloading... → Unloaded                              │
│ HTTP 503: "VRAM saturated, retry in 60s"                     │
└──────────────────────────────────────────────────────────────┘
                            │
                            │ Return to STATE 1
                            ▼
                         (IDLE)
```

---

## API Quick Reference

### Core Endpoints

| Method | Endpoint | Purpose | Priority |
|--------|----------|---------|----------|
| GET | `/health` | Service status | - |
| GET | `/metrics` | GPU metrics + Hamiltonian | - |
| POST | `/cuda-q/qaoa` | Quantum optimization | P1 |
| POST | `/vision/detect` | Object detection | P2 |
| POST | `/llm/chat` | Conversational AI | P3 |
| POST | `/pipeline/analyze` | Multi-modal pipeline | Mixed |

### Hamiltonian Thresholds

| Range | State | Action |
|-------|-------|--------|
| H < 5.0 | 🟢 GREEN | All models available |
| 5.0 ≤ H < 7.5 | 🟡 YELLOW | Dynamic loading |
| 7.5 ≤ H < 8.5 | 🟠 ORANGE | Single heavy model only |
| H ≥ 8.5 | 🔴 RED | OFFLOAD, unload models |

### VRAM Budgets

| Model | VRAM | Priority | Loading Strategy |
|-------|------|----------|------------------|
| CUDA-Q | 124 MB | P1 | Always loaded |
| YOLO11s | 1200 MB | P2 | Keep hot (default) |
| Qwen 1.5 | 2800 MB | P3 | On-demand, 60s TTL |

---

## Example Requests

### 1. CUDA-Q Quantum Optimization

```bash
curl -X POST http://localhost:3000/cuda-q/qaoa \
  -H "Content-Type: application/json" \
  -d '{
    "problem_type": "mycelial_qubo",
    "graph_nodes": 16,
    "edges": [[0,1], [1,2], [2,3], ...],
    "qaoa_depth": 3,
    "iterations": 100,
    "convergence_threshold": 0.0001
  }'

# Response:
{
  "solution": [1, 0, 1, 0, ...],
  "energy": -42.7,
  "convergence": {
    "reached": true,
    "iterations": 73,
    "final_delta": 0.00008
  },
  "vram_peak_mb": 124,
  "execution_time_ms": 1847
}
```

### 2. YOLO11s Object Detection

```bash
curl -X POST http://localhost:3000/vision/detect \
  -H "Content-Type: application/json" \
  -d '{
    "image": "'$(base64 -w 0 image.jpg)'",
    "confidence": 0.5,
    "iou": 0.45
  }'

# Response:
{
  "detections": [
    {
      "class": "person",
      "confidence": 0.92,
      "bbox": [120, 50, 200, 450]
    },
    {
      "class": "car",
      "confidence": 0.87,
      "bbox": [300, 200, 150, 100]
    }
  ],
  "inference_time_ms": 1.47,
  "vram_used_mb": 1200
}
```

### 3. Qwen 1.5 Chat

```bash
curl -X POST http://localhost:3000/llm/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Explain quantum annealing in 50 words"}
    ],
    "max_tokens": 100,
    "temperature": 0.7
  }'

# Response:
{
  "content": "Quantum annealing is a quantum computing method that finds optimal solutions by exploiting quantum tunneling. It starts with qubits in superposition, then gradually evolves to the lowest energy state representing the solution, useful for optimization problems.",
  "tokens": {
    "prompt": 12,
    "completion": 47
  },
  "vram_used_mb": 2800
}
```

### 4. Multi-Modal Pipeline

```bash
curl -X POST http://localhost:3000/pipeline/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "image": "'$(base64 -w 0 scene.jpg)'",
    "prompt": "Describe the objects and suggest quantum optimization for spatial arrangement",
    "services": ["vision", "llm"]
  }'

# Response:
{
  "results": {
    "vision": {
      "detections": [...]
    },
    "llm": {
      "content": "The scene contains 3 people and 2 cars. For optimal spatial arrangement using quantum optimization, we could model this as a QUBO problem where each object's position is a variable..."
    }
  },
  "total_time_ms": 3425,
  "vram_peak_mb": 3200,
  "hamiltonian": 8.1
}
```

---

## File Structure Summary

```
~/unified-inference/
├── server.mjs                          # Node.js API Gateway
├── package.json                        # Node dependencies
│
├── python/
│   ├── orchestrator.py                 # Main FastAPI server ⭐
│   │
│   ├── core/
│   │   ├── vram_orchestrator.py        # VRAM allocation logic ⭐
│   │   ├── resource_monitor.py         # GPU metrics via pynvml ⭐
│   │   ├── priority_queue.py           # Request scheduling
│   │   ├── stream_manager.py           # CUDA stream allocation
│   │   └── offload_client.py           # Diamond Gateway client
│   │
│   ├── services/
│   │   ├── cuda_q_service.py           # CUDA-Q wrapper
│   │   ├── yolo_service.py             # YOLO11s service
│   │   └── llm_service.py              # Qwen 1.5 service
│   │
│   └── requirements.txt
│
├── config/
│   ├── thresholds.yaml                 # VRAM/temp thresholds
│   └── endpoints.yaml                  # Service URLs
│
├── scripts/
│   ├── start-services.sh               # Orchestration script
│   ├── quick-start.sh                  # One-command setup
│   └── health-check.sh                 # Verify endpoints
│
└── systemd/
    ├── unified-gateway.service         # Node.js service
    └── inference-orchestrator.service  # Python service
```

**⭐ = Start here (Phase 1)**

---

## Implementation Checklist

### Phase 1: Foundation (Week 1)
- [ ] Create `~/unified-inference/` directory structure
- [ ] Implement `resource_monitor.py` (GPU metrics)
- [ ] Implement `vram_orchestrator.py` (Hamiltonian calc)
- [ ] Test Hamiltonian: `H = (VRAM/Total)*10 + 0.3*(T/89.6)`
- [ ] Implement `orchestrator.py` (health + metrics endpoints only)
- [ ] Verify: `curl localhost:8001/metrics` returns GPU data

### Phase 2: Service Integration (Week 2)
- [ ] Implement `cuda_q_service.py` (wrap `mycelial_qubo.py`)
- [ ] Test: POST `/cuda-q/qaoa` with 16-node problem
- [ ] Implement `yolo_service.py` (YOLOv11s)
- [ ] Test: POST `/vision/detect` with sample image
- [ ] Implement `priority_queue.py`
- [ ] Verify priority ordering: P1 > P2 > P3

### Phase 3: LLM Integration (Week 3)
- [ ] Setup Xinference server for Qwen 1.5 4B
- [ ] Implement `llm_service.py`
- [ ] Test: POST `/llm/chat` generates response
- [ ] Implement `offload_client.py`
- [ ] Test OFFLOAD: Trigger H > 8.5, verify Notion write
- [ ] Implement `stream_manager.py` for CUDA streams

### Phase 4: Gateway & Production (Week 4)
- [ ] Enhance `server.mjs` with routing to orchestrator
- [ ] Add TRTC streaming for real-time vision
- [ ] Implement WebSocket endpoint `/vision/track`
- [ ] Create systemd services
- [ ] Test: systemctl start/stop services
- [ ] Load test: 100 concurrent requests

### Phase 5: Deployment (Week 5)
- [ ] Deploy to production
- [ ] Configure monitoring dashboard
- [ ] Write runbooks for common issues
- [ ] Performance tuning (batch sizes, timeouts)
- [ ] Documentation finalization

---

## Monitoring Dashboard

### Key Metrics to Display

```
┌─────────────────────────────────────────────────────────────┐
│ Diamond Node Unified Inference - Live Status                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ GPU Status                                                   │
│   VRAM: ████████░░░░░░░░ 1324 / 3972 MB (33.3%)            │
│   Temp: ████░░░░░░░░░░░░ 45.2°C / 89.6°C (44.4%)           │
│   H(s): ██░░░░░░░░░░░░░░ 3.48 / 8.5 (SAFE)                 │
│                                                              │
│ Models                                                       │
│   ✓ CUDA-Q    : LOADED  (124 MB)   [P1]                    │
│   ✓ YOLO11s   : LOADED  (1200 MB)  [P2]                    │
│   ✗ Qwen 1.5  : UNLOADED (0 MB)    [P3]                    │
│                                                              │
│ Request Queue                                                │
│   Pending: 0                                                 │
│   Active:  2 (1× CUDA-Q, 1× YOLO)                          │
│                                                              │
│ Performance (Last 5min)                                      │
│   Requests:     127 total (25.4/min)                        │
│   Latency:      p50=142ms, p95=1847ms, p99=3421ms          │
│   Errors:       0 (0.0%)                                    │
│   OFFLOADs:     0                                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### Issue: H > 8.5 frequently triggered

**Diagnosis:**
```bash
curl http://localhost:3000/metrics | jq .hamiltonian
# If > 8.5 often, check:
curl http://localhost:3000/metrics | jq '.vram, .temperature'
```

**Solutions:**
1. **High VRAM**: Reduce batch sizes, unload idle models
2. **High Temp**: Improve cooling, reduce clock speeds
3. **Both**: Lower thermal weight: `beta = 0.2` instead of `0.3`

### Issue: Models not loading

**Diagnosis:**
```bash
# Check service status
curl http://localhost:3000/health | jq .services

# Check logs
tail -f ~/unified-inference/logs/orchestrator.log
```

**Solutions:**
1. Manually unload models: `curl -X POST http://localhost:8001/internal/unload-model?service=llm`
2. Restart orchestrator: `systemctl restart inference-orchestrator`
3. Check CUDA availability: `nvidia-smi`

### Issue: Slow inference

**Diagnosis:**
```bash
# Check queue depth
curl http://localhost:3000/metrics | jq '.queue'

# Check VRAM fragmentation
nvidia-smi --query-gpu=memory.used,memory.free --format=csv
```

**Solutions:**
1. Increase workers: `uvicorn ... --workers 4`
2. Use CUDA streams (already implemented)
3. Batch small requests together

---

## Security Checklist

- [ ] `GATEWAY_SECRET` set in environment (never commit)
- [ ] `NOTION_TOKEN` set in environment (never commit)
- [ ] Orchestrator binds to `127.0.0.1` only (not `0.0.0.0`)
- [ ] Rate limiting enabled on gateway
- [ ] Authentication required for admin endpoints
- [ ] HTTPS/TLS enabled in production
- [ ] Input validation on all endpoints
- [ ] Resource limits (max batch size, max tokens)

---

## Performance Targets

| Metric | Target | Measured |
|--------|--------|----------|
| CUDA-Q QAOA (16 nodes) | < 2000ms | TBD |
| YOLO11s inference | < 5ms | TBD |
| Qwen 1.5 chat (512 tokens) | < 3000ms | TBD |
| Model load time (YOLO) | < 2000ms | TBD |
| Model load time (Qwen) | < 5000ms | TBD |
| OFFLOAD trigger time | < 500ms | TBD |
| Gateway latency (routing) | < 10ms | TBD |

---

## Next Steps

1. ✅ **Review architecture**: `UNIFIED_INFERENCE_ARCHITECTURE.md`
2. ✅ **Review implementation**: `unified-inference-implementation.md`
3. ⏭️ **Create directory**: `mkdir -p ~/unified-inference`
4. ⏭️ **Start Phase 1**: Implement resource_monitor.py
5. ⏭️ **Test incrementally**: After each module
6. ⏭️ **Benchmark**: Compare to targets
7. ⏭️ **Deploy**: Production systemd services

**Estimated Time:** 5 weeks (1 week per phase)  
**Complexity:** High (multi-service orchestration)  
**Risk:** Medium (VRAM constraints, thermal management)  
**Value:** Very High (unified inference platform)

---

**Document Version:** 1.0  
**Last Updated:** 2025-05-12  
**Status:** Ready for Implementation
