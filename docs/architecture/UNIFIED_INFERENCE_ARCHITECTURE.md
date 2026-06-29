# Unified Inference Server Architecture
**Diamond Node Multi-Model Orchestration System**

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER (External)                         │
│  WebSocket/HTTP Clients, TRTC Real-time Streaming, REST API Consumers  │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────────────┐
│                    UNIFIED API GATEWAY (Node.js)                        │
│                         server.mjs (Port 3000)                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  • HTTP/WebSocket endpoints                                     │   │
│  │  • TRTC SDK integration (audio/video streaming)                 │   │
│  │  • Request routing & load balancing                             │   │
│  │  • Authentication & rate limiting                               │   │
│  │  • Connection pooling to Python backends                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────┬────────────────┬───────────────┬─────────────────┬────────┘
              │                │               │                 │
    ┌─────────▼──────┐  ┌──────▼─────┐  ┌─────▼──────┐  ┌──────▼──────┐
    │  /cuda-q/*     │  │ /vision/*  │  │  /llm/*    │  │ /metrics    │
    │  QAOA/Quantum  │  │ YOLO11s    │  │ Qwen 1.5   │  │ VRAM Status │
    └────────┬───────┘  └─────┬──────┘  └──────┬─────┘  └──────┬──────┘
             │                │                │                │
┌────────────▼────────────────▼────────────────▼────────────────▼─────────┐
│           ORCHESTRATION LAYER (Python FastAPI Backend)                  │
│                  inference_orchestrator.py (Port 8001)                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  VRAM Orchestrator (Waveform Equilibrium)                        │  │
│  │  • Monitors H_resource = (VRAM/Total)*10 + 0.3*(T/89.6)         │  │
│  │  • Priority queue: CUDA-Q(P1) > YOLO11(P2) > Qwen(P3)           │  │
│  │  • Dynamic model loading/unloading                               │  │
│  │  • CUDA stream management                                        │  │
│  │  • Triggers OFFLOAD when H > 8.5                                 │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌────────────┐  ┌────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  CUDA-Q    │  │  YOLO11s   │  │  Qwen 1.5    │  │  Waveform    │  │
│  │  Service   │  │  Service   │  │  LLM Service │  │  Equilibrium │  │
│  │  (124 MB)  │  │  (1.2 GB)  │  │  (2-3 GB)    │  │  Module      │  │
│  │  Port 8002 │  │  Port 8003 │  │  Port 8004   │  │  (Library)   │  │
│  └─────┬──────┘  └─────┬──────┘  └──────┬───────┘  └──────┬───────┘  │
└────────┼───────────────┼─────────────────┼──────────────────┼──────────┘
         │               │                 │                  │
         └───────────────┴─────────────────┴──────────────────┘
                                   │
                 ┌─────────────────▼──────────────────┐
                 │    GPU VRAM (4 GB Total)           │
                 │  ┌──────────────────────────────┐  │
                 │  │ CUDA Streams (Parallel Exec) │  │
                 │  │  Stream 0: CUDA-Q            │  │
                 │  │  Stream 1: YOLO11s           │  │
                 │  │  Stream 2: Qwen 1.5 (mutex)  │  │
                 │  └──────────────────────────────┘  │
                 │  GTX 1650 (4 cores, 896 shaders)  │
                 └────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────┐
│              CONTEXT OFFLOAD LAYER (Existing Infrastructure)            │
│  ┌────────────────────┐         ┌─────────────────────────────────┐    │
│  │ Diamond Gateway    │────────▶│  Notion Bridge (Cloudflare)     │    │
│  │ /v1/orchestrate    │         │  Soul-Capsule Database          │    │
│  │ Port 8000          │         │  (Context Persistence)          │    │
│  └────────────────────┘         └─────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. API Endpoint Specifications

### 2.1 Unified Gateway (Node.js - Port 3000)

#### Health & Metrics
```
GET /health
  Response: { status: "ok", services: { cuda_q: "running", yolo: "idle", llm: "loaded" } }

GET /metrics
  Response: {
    vram: { used_mib: 1324, total_mib: 3972, util_pct: 33.3 },
    temperature: { current: 45.2, max: 89.6, headroom_pct: 49.6 },
    hamiltonian: 3.48,
    services: { cuda_q: { status: "idle", vram_mb: 7 }, ... }
  }
```

#### CUDA-Q Quantum Optimization
```
POST /cuda-q/qaoa
  Body: {
    problem_type: "mycelial_qubo" | "ising" | "maxcut",
    graph_nodes: 16,
    edges: [[0,1], [1,2], ...],
    qaoa_depth: 3,
    iterations: 100,
    convergence_threshold: 1e-4
  }
  Response: {
    solution: [1, 0, 1, ...],
    energy: -42.7,
    convergence: { reached: true, iterations: 73 },
    vram_peak_mb: 124,
    execution_time_ms: 1847
  }

POST /cuda-q/waveform-analysis
  Body: { state_vector: [...], eigenspace: {...} }
  Response: { equilibrium: true, convergence_rate: 0.0012, ... }
```

#### Computer Vision (YOLO11s)
```
POST /vision/detect
  Body: { image: "base64...", confidence: 0.5, iou: 0.45 }
  Response: {
    detections: [
      { class: "person", confidence: 0.92, bbox: [x, y, w, h] },
      ...
    ],
    inference_time_ms: 1.47,
    vram_used_mb: 1200
  }

POST /vision/track
  WebSocket endpoint for real-time object tracking with TRTC stream
```

#### Large Language Model (Qwen 1.5 4B)
```
POST /llm/chat
  Body: {
    messages: [{ role: "user", content: "..." }],
    max_tokens: 512,
    temperature: 0.7,
    stream: false
  }
  Response: {
    content: "...",
    tokens: { prompt: 45, completion: 127 },
    vram_used_mb: 2800
  }

POST /llm/embed
  Body: { texts: ["text1", "text2"] }
  Response: { embeddings: [[...], [...]] }
```

#### Multi-Modal Pipeline
```
POST /pipeline/analyze
  Body: {
    image: "base64...",
    prompt: "Describe the objects and suggest quantum optimization for placement",
    services: ["vision", "llm", "cuda-q"]
  }
  Response: {
    vision_results: {...},
    llm_analysis: "...",
    optimization: {...},
    total_time_ms: 3425,
    vram_peak_mb: 3200
  }
```

---

## 3. Service Orchestration Flow

### 3.1 Request Processing Pipeline

```
Incoming Request
    │
    ├─▶ [Gateway] Authenticate & Validate
    │       │
    │       ├─▶ Check service availability
    │       └─▶ Estimate VRAM requirement
    │
    ├─▶ [Orchestrator] Resource Check
    │       │
    │       ├─▶ Query current VRAM state via Diamond Gateway
    │       ├─▶ Calculate H_resource = (VRAM/Total)*10 + 0.3*(T/89.6)
    │       │
    │       ├─▶ IF H > 8.5:
    │       │      └─▶ Trigger OFFLOAD (context → Notion)
    │       │      └─▶ Unload low-priority models (Qwen first)
    │       │      └─▶ Wait for VRAM < threshold
    │       │
    │       └─▶ Check priority queue & model loading state
    │
    ├─▶ [Model Loader] Dynamic Loading
    │       │
    │       ├─▶ Priority 1 (CUDA-Q): Always hot, lightweight (124 MB)
    │       ├─▶ Priority 2 (YOLO11s): Keep loaded if VRAM available
    │       └─▶ Priority 3 (Qwen): Load on-demand, mutex with large ops
    │
    ├─▶ [Execution] Model Inference
    │       │
    │       ├─▶ Acquire CUDA stream
    │       ├─▶ Execute inference
    │       ├─▶ Monitor VRAM & temperature
    │       └─▶ Release stream
    │
    └─▶ [Response] Return results + metrics
```

### 3.2 VRAM Allocation States

```
STATE 1: Idle (H ≤ 2.0)
├─ CUDA-Q: Loaded (124 MB)
├─ YOLO11s: Loaded (1.2 GB)
├─ Qwen: Unloaded
└─ Available: ~2.7 GB

STATE 2: Vision Active (H = 3.3)
├─ CUDA-Q: Loaded, idle (124 MB)
├─ YOLO11s: Running (1.2 GB)
├─ Qwen: Unloaded
└─ Available: ~2.7 GB

STATE 3: LLM Active (H = 7.8)
├─ CUDA-Q: Loaded, idle (124 MB)
├─ YOLO11s: Unloaded
├─ Qwen: Running (2.8 GB)
└─ Available: ~1 GB

STATE 4: Multi-Modal (H = 8.2, near threshold)
├─ CUDA-Q: Running (124 MB)
├─ YOLO11s: Running (1.2 GB)
├─ Qwen: Loaded, queued (2.8 GB) ← WAIT
└─ Sequential execution required

STATE 5: OFFLOAD Triggered (H > 8.5)
├─ Context saved to Notion
├─ Unload Qwen (-2.8 GB)
├─ Unload YOLO if needed (-1.2 GB)
└─ Return to STATE 1
```

---

## 4. Resource Allocation Strategy

### 4.1 Priority-Based Scheduling

**Priority Tier 1: CUDA-Q (Always Hot)**
- Rationale: Smallest footprint (124 MB), highest scientific value
- Strategy: Keep loaded at all times, minimal overhead
- VRAM Impact: 3.1% of total capacity

**Priority Tier 2: YOLO11s (Hot by Default)**
- Rationale: Fast inference (1.47ms), common use case
- Strategy: Load on startup, keep warm during idle
- VRAM Impact: 30% of total capacity
- Unload Condition: When Qwen needs >70% VRAM

**Priority Tier 3: Qwen 1.5 4B (Load on Demand)**
- Rationale: Largest model (2-3 GB), intermittent use
- Strategy: Load when requested, unload after 60s idle or if H > 7.5
- VRAM Impact: 70-75% of total capacity
- Mutex: Cannot coexist with YOLO + other large ops

### 4.2 Waveform Equilibrium Integration

**Hamiltonian Calculation:**
```python
H_resource(t) = (VRAM_used / VRAM_total) × 10 + 0.3 × (T_gpu / 89.6)

Thresholds:
  H < 5.0: GREEN (all models available)
  5.0 ≤ H < 7.5: YELLOW (dynamic loading)
  7.5 ≤ H < 8.5: ORANGE (single heavy model only)
  H ≥ 8.5: RED (trigger OFFLOAD, unload models)
```

**Temperature Monitoring:**
```python
# GTX 1650 thermal limits
T_max = 89.6°C (critical thermal shutdown)
T_safe = 75°C (sustained workload safe zone)
T_idle = 35-45°C (typical idle)

# Thermal headroom calculation
headroom_pct = ((T_max - T_current) / T_max) × 100

# Thermal throttling
if T_current > 80°C:
    reduce_batch_size()
    increase_cooling_wait()
```

### 4.3 CUDA Stream Parallelism

```python
# Stream allocation
stream_cuda_q = cuda.Stream(0)   # Quantum operations
stream_vision = cuda.Stream(1)   # YOLO inference
stream_llm = cuda.Stream(2)      # Qwen (mutex mode)

# Parallel execution example
with stream_cuda_q:
    cuda_q_result = run_qaoa(problem)
    
with stream_vision:
    yolo_result = detect_objects(image)

# Both run simultaneously if VRAM permits
cuda.synchronize()  # Wait for both

# Sequential LLM (cannot run with others)
if vram_available > 3000:
    with stream_llm:
        llm_result = generate_text(prompt)
```

---

## 5. Implementation File Structure

```
diamondnode/
│
├── unified-inference/                   # New unified server root
│   ├── server.mjs                       # Node.js API Gateway (TRTC + routing)
│   ├── package.json                     # Node dependencies
│   │
│   ├── python/                          # Python backend services
│   │   ├── orchestrator.py              # Main FastAPI orchestration server
│   │   ├── services/
│   │   │   ├── cuda_q_service.py        # CUDA-Q QAOA wrapper
│   │   │   ├── yolo_service.py          # YOLO11s detection service
│   │   │   ├── llm_service.py           # Qwen 1.5 inference service
│   │   │   └── resource_monitor.py      # VRAM/temp monitoring
│   │   │
│   │   ├── core/
│   │   │   ├── vram_orchestrator.py     # Dynamic model loading
│   │   │   ├── priority_queue.py        # Request prioritization
│   │   │   ├── stream_manager.py        # CUDA stream allocation
│   │   │   └── offload_client.py        # Diamond Gateway + Notion integration
│   │   │
│   │   └── requirements.txt             # Python dependencies
│   │
│   ├── config/
│   │   ├── models.yaml                  # Model configurations
│   │   ├── thresholds.yaml              # VRAM/temp thresholds
│   │   └── endpoints.yaml               # Service endpoints
│   │
│   ├── scripts/
│   │   ├── start-services.sh            # Start all services
│   │   ├── health-check.sh              # Verify all endpoints
│   │   └── load-models.sh               # Pre-load models
│   │
│   └── systemd/
│       ├── unified-gateway.service      # Node.js gateway service
│       └── inference-orchestrator.service # Python orchestrator service
│
├── diamond-node/                        # Existing diamond-node repo
│   └── scripts/
│       ├── waveform_equilibrium.py      # ← Used by orchestrator
│       ├── mycelial_qubo.py             # ← Used by cuda_q_service
│       └── ...
│
└── /opt/diamond-gateway/                # Existing gateway (metrics only)
    └── gateway.py                       # ← Queried for VRAM metrics
```

---

## 6. Implementation Phases

### Phase 1: Core Orchestration (Week 1)
**Files to Create:**
1. `unified-inference/python/orchestrator.py` — FastAPI server with basic routing
2. `unified-inference/python/core/vram_orchestrator.py` — VRAM monitoring + Hamiltonian calc
3. `unified-inference/python/core/resource_monitor.py` — GPU metrics via pynvml
4. `unified-inference/config/thresholds.yaml` — Configuration

**Validation:**
- GET `/metrics` returns live VRAM/temp data
- POST `/internal/check-vram` returns H_resource value
- Basic health checks for all services

### Phase 2: Service Integration (Week 2)
**Files to Create:**
5. `unified-inference/python/services/cuda_q_service.py` — Wrap mycelial_qubo.py
6. `unified-inference/python/services/yolo_service.py` — YOLO11s integration
7. `unified-inference/python/core/stream_manager.py` — CUDA stream allocation

**Validation:**
- POST `/cuda-q/qaoa` runs 16-node QAOA successfully
- POST `/vision/detect` returns bounding boxes
- Verify parallel execution with CUDA streams

### Phase 3: LLM Integration (Week 3)
**Files to Create:**
8. `unified-inference/python/services/llm_service.py` — Qwen 1.5 via Xinference
9. `unified-inference/python/core/priority_queue.py` — Request scheduling
10. `unified-inference/python/core/offload_client.py` — Diamond Gateway client

**Validation:**
- POST `/llm/chat` generates responses
- OFFLOAD triggers when H > 8.5
- Context saved to Notion successfully

### Phase 4: Unified Gateway (Week 4)
**Files to Create:**
11. `unified-inference/server.mjs` — Node.js API Gateway with TRTC
12. `unified-inference/package.json` — Dependencies
13. `unified-inference/scripts/start-services.sh` — Orchestration script

**Validation:**
- All endpoints accessible through single gateway
- TRTC streaming works with real-time object detection
- Load testing: 100 concurrent requests

### Phase 5: Production Deployment (Week 5)
**Files to Create:**
14. `unified-inference/systemd/unified-gateway.service`
15. `unified-inference/systemd/inference-orchestrator.service`
16. `unified-inference/scripts/health-check.sh`

**Validation:**
- Services auto-start on boot
- Logs properly configured
- Monitoring dashboard integration

---

## 7. Key Design Decisions

### 7.1 Why Node.js Gateway + Python Backend?
- **Node.js**: Excellent for WebSocket/TRTC real-time streaming, async I/O
- **Python**: Native ML ecosystem (PyTorch, CUDA-Q, YOLO), easier GPU integration
- **Communication**: HTTP/JSON for simplicity, gRPC for future optimization

### 7.2 Why Separate Services?
- **Isolation**: One model crash doesn't take down entire system
- **Scalability**: Can distribute to multiple GPUs/machines later
- **Development**: Teams can work on services independently

### 7.3 Why Priority Queue?
- **Fairness**: CUDA-Q (scientific) gets priority over LLM (conversational)
- **Efficiency**: YOLO (fast) shouldn't wait for Qwen (slow)
- **Resource Optimization**: Prevents VRAM thrashing with smart scheduling

### 7.4 Waveform Equilibrium Role
- **Real-time Monitoring**: Continuous H_resource calculation
- **Predictive Offload**: Trigger OFFLOAD before OOM crash
- **Thermal Awareness**: Prevents thermal throttling/shutdown
- **Scientific Grounding**: Based on quantum state evolution math

---

## 8. Testing Strategy

### 8.1 Unit Tests
```bash
# VRAM orchestrator
python -m pytest tests/test_vram_orchestrator.py

# Hamiltonian calculation
python -m pytest tests/test_waveform_equilibrium.py

# Model services
python -m pytest tests/test_cuda_q_service.py
```

### 8.2 Integration Tests
```bash
# End-to-end CUDA-Q
curl -X POST http://localhost:3000/cuda-q/qaoa -d @tests/qaoa_request.json

# Multi-modal pipeline
curl -X POST http://localhost:3000/pipeline/analyze -d @tests/multimodal.json
```

### 8.3 Load Tests
```bash
# Apache Bench
ab -n 1000 -c 10 http://localhost:3000/metrics

# Locust
locust -f tests/load_test.py --host http://localhost:3000
```

### 8.4 VRAM Stress Test
```python
# Intentionally trigger OFFLOAD
response = requests.post("http://localhost:3000/cuda-q/qaoa", ...)
assert response.json()["vram_peak_mb"] < 4000

# Verify OFFLOAD triggered
metrics = requests.get("http://localhost:3000/metrics").json()
assert metrics["hamiltonian"] < 8.5  # Should stabilize
```

---

## 9. Monitoring & Observability

### 9.1 Metrics to Track
```yaml
GPU Metrics:
  - vram_used_mb (gauge)
  - vram_util_pct (gauge)
  - gpu_temp_celsius (gauge)
  - hamiltonian_value (gauge)
  - offload_triggered_total (counter)

Service Metrics:
  - requests_total (counter) per service
  - request_duration_seconds (histogram)
  - active_models (gauge)
  - model_load_time_seconds (histogram)

Error Metrics:
  - oom_errors_total (counter)
  - timeout_errors_total (counter)
  - inference_failures_total (counter)
```

### 9.2 Logging Strategy
```python
# Structured logging (JSON)
{
  "timestamp": "2025-05-12T06:51:23Z",
  "level": "INFO",
  "service": "vram_orchestrator",
  "event": "offload_triggered",
  "hamiltonian": 8.73,
  "vram_used_mb": 3800,
  "session_id": "sess-12345"
}
```

### 9.3 Alerting Rules
```yaml
Critical Alerts:
  - H_resource > 9.0 for >30s
  - GPU temp > 85°C
  - Service unresponsive >10s

Warning Alerts:
  - H_resource > 7.5 for >2min
  - GPU temp > 75°C for >5min
  - Request queue >50 items
```

---

## 10. Future Enhancements

### 10.1 Multi-GPU Support
- Distribute models across multiple GPUs
- Use NCCL for inter-GPU communication
- Load balance requests across GPUs

### 10.2 Model Quantization
- INT8 quantization for Qwen (3GB → 1.5GB)
- FP16 mixed precision for YOLO
- Reduces VRAM, increases throughput

### 10.3 Persistent Context Cache
- Redis for hot context storage
- Avoid full Notion roundtrip for frequent sessions
- TTL-based expiration

### 10.4 Edge Deployment
- Deploy YOLO + lightweight LLM to edge devices
- Route heavy CUDA-Q to cloud
- Hybrid inference architecture

---

## Appendix: Quick Start Commands

```bash
# 1. Clone and setup
cd ~/unified-inference
python3 -m venv venv
source venv/bin/activate
pip install -r python/requirements.txt
npm install

# 2. Configure
export GATEWAY_SECRET="your-secret"
export NOTION_TOKEN="your-token"

# 3. Start services
./scripts/start-services.sh

# 4. Verify health
curl http://localhost:3000/health
curl http://localhost:3000/metrics

# 5. Test CUDA-Q
curl -X POST http://localhost:3000/cuda-q/qaoa \
  -H "Content-Type: application/json" \
  -d '{"problem_type":"mycelial_qubo","graph_nodes":16,"qaoa_depth":3}'

# 6. Test YOLO
curl -X POST http://localhost:3000/vision/detect \
  -H "Content-Type: application/json" \
  -d '{"image":"base64...","confidence":0.5}'

# 7. Monitor logs
tail -f logs/orchestrator.log
tail -f logs/gateway.log
```

---

**Document Version:** 1.0  
**Last Updated:** 2025-05-12  
**Author:** Diamond Node Orchestration Team  
**Status:** Ready for Phase 1 Implementation
