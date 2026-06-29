# Unified Inference Server Implementation Guide

## Phase 1: Core Orchestration Layer (Priority 1)

### File 1: Python Orchestrator Entry Point
**Location:** `~/unified-inference/python/orchestrator.py`

```python
"""Main FastAPI orchestration server for unified inference.

Coordinates:
- VRAM monitoring and resource allocation
- Request routing to specialized services
- Dynamic model loading/unloading
- OFFLOAD triggering to Diamond Gateway
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import asyncio
import httpx
from datetime import datetime

from core.vram_orchestrator import VRAMOrchestrator
from core.resource_monitor import ResourceMonitor
from core.priority_queue import RequestQueue, Priority
from core.offload_client import OffloadClient
from services.cuda_q_service import CUDAQService
from services.yolo_service import YOLOService
from services.llm_service import LLMService

# Global state
orchestrator: Optional[VRAMOrchestrator] = None
resource_monitor: Optional[ResourceMonitor] = None
request_queue: Optional[RequestQueue] = None
offload_client: Optional[OffloadClient] = None

# Service instances
cuda_q: Optional[CUDAQService] = None
yolo: Optional[YOLOService] = None
llm: Optional[LLMService] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources."""
    global orchestrator, resource_monitor, request_queue, offload_client
    global cuda_q, yolo, llm
    
    # Initialize monitoring
    resource_monitor = ResourceMonitor()
    await resource_monitor.start()
    
    # Initialize orchestrator
    orchestrator = VRAMOrchestrator(
        total_vram_gb=4.0,
        temp_max=89.6,
        hamiltonian_threshold=8.5
    )
    
    # Initialize request queue
    request_queue = RequestQueue()
    
    # Initialize offload client
    offload_client = OffloadClient(
        gateway_url="http://localhost:8000/v1/orchestrate",
        notion_url="https://notion-bridge.optimizationinversion.workers.dev"
    )
    
    # Pre-load Priority 1 service (CUDA-Q)
    cuda_q = CUDAQService()
    await cuda_q.load_model()
    print(f"✓ CUDA-Q service loaded ({cuda_q.vram_mb} MB)")
    
    # Pre-load Priority 2 service (YOLO) if VRAM available
    yolo = YOLOService()
    if orchestrator.can_allocate(yolo.vram_mb):
        await yolo.load_model()
        print(f"✓ YOLO11s service loaded ({yolo.vram_mb} MB)")
    
    # Initialize Priority 3 service (LLM) but don't load yet
    llm = LLMService()
    print(f"✓ LLM service initialized (will load on demand)")
    
    yield
    
    # Cleanup
    await resource_monitor.stop()
    if cuda_q:
        await cuda_q.unload_model()
    if yolo:
        await yolo.unload_model()
    if llm:
        await llm.unload_model()

app = FastAPI(
    title="Diamond Node Unified Inference Server",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================================================================================
# Health & Metrics Endpoints
# ==================================================================================

@app.get("/health")
async def health_check():
    """System health check."""
    services = {
        "cuda_q": "loaded" if cuda_q and cuda_q.is_loaded else "unloaded",
        "yolo": "loaded" if yolo and yolo.is_loaded else "unloaded",
        "llm": "loaded" if llm and llm.is_loaded else "unloaded"
    }
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "services": services
    }

@app.get("/metrics")
async def get_metrics():
    """Real-time GPU metrics and service status."""
    metrics = await resource_monitor.get_metrics()
    hamiltonian = orchestrator.calculate_hamiltonian(
        vram_used_mb=metrics["vram_used_mb"],
        temp_celsius=metrics["temperature"]
    )
    
    return {
        "vram": {
            "used_mb": metrics["vram_used_mb"],
            "total_mb": metrics["vram_total_mb"],
            "util_pct": metrics["vram_util_pct"],
            "available_mb": metrics["vram_total_mb"] - metrics["vram_used_mb"]
        },
        "temperature": {
            "current": metrics["temperature"],
            "max": 89.6,
            "headroom_pct": ((89.6 - metrics["temperature"]) / 89.6) * 100
        },
        "hamiltonian": round(hamiltonian, 2),
        "services": {
            "cuda_q": {
                "status": "loaded" if cuda_q.is_loaded else "unloaded",
                "vram_mb": cuda_q.vram_mb if cuda_q.is_loaded else 0
            },
            "yolo": {
                "status": "loaded" if yolo.is_loaded else "unloaded",
                "vram_mb": yolo.vram_mb if yolo.is_loaded else 0
            },
            "llm": {
                "status": "loaded" if llm.is_loaded else "unloaded",
                "vram_mb": llm.vram_mb if llm.is_loaded else 0
            }
        },
        "queue": {
            "pending": request_queue.size(),
            "processing": request_queue.active_count()
        }
    }

# ==================================================================================
# CUDA-Q Quantum Optimization Endpoints
# ==================================================================================

class QAOARequest(BaseModel):
    problem_type: str = Field(..., description="mycelial_qubo, ising, or maxcut")
    graph_nodes: int = Field(16, ge=4, le=20)
    edges: List[List[int]]
    qaoa_depth: int = Field(3, ge=1, le=10)
    iterations: int = Field(100, ge=10, le=1000)
    convergence_threshold: float = Field(1e-4, gt=0)
    session_id: Optional[str] = None

@app.post("/cuda-q/qaoa")
async def run_qaoa(request: QAOARequest, background_tasks: BackgroundTasks):
    """Run QAOA optimization on quantum circuit."""
    # Check VRAM and trigger OFFLOAD if needed
    metrics = await resource_monitor.get_metrics()
    H = orchestrator.calculate_hamiltonian(metrics["vram_used_mb"], metrics["temperature"])
    
    if H > 8.5:
        await offload_client.trigger_offload(
            session_id=request.session_id or f"qaoa-{datetime.utcnow().timestamp()}",
            context=request.dict(),
            vram_used=metrics["vram_used_mb"],
            vram_total=metrics["vram_total_mb"],
            hamiltonian=H
        )
        raise HTTPException(503, "VRAM saturated, context offloaded. Retry in 30s.")
    
    # Ensure CUDA-Q is loaded
    if not cuda_q.is_loaded:
        await cuda_q.load_model()
    
    # Add to priority queue (P1)
    request_id = await request_queue.enqueue(Priority.P1, request.dict())
    
    try:
        # Execute QAOA
        result = await cuda_q.run_qaoa(
            problem_type=request.problem_type,
            graph_nodes=request.graph_nodes,
            edges=request.edges,
            qaoa_depth=request.qaoa_depth,
            iterations=request.iterations,
            convergence_threshold=request.convergence_threshold
        )
        
        request_queue.complete(request_id)
        return result
        
    except Exception as e:
        request_queue.fail(request_id, str(e))
        raise HTTPException(500, f"QAOA execution failed: {str(e)}")

# ==================================================================================
# Computer Vision Endpoints
# ==================================================================================

class DetectionRequest(BaseModel):
    image: str = Field(..., description="Base64-encoded image")
    confidence: float = Field(0.5, ge=0.1, le=1.0)
    iou: float = Field(0.45, ge=0.1, le=1.0)
    session_id: Optional[str] = None

@app.post("/vision/detect")
async def detect_objects(request: DetectionRequest):
    """Object detection with YOLO11s."""
    # Check VRAM
    metrics = await resource_monitor.get_metrics()
    H = orchestrator.calculate_hamiltonian(metrics["vram_used_mb"], metrics["temperature"])
    
    if H > 8.5:
        await offload_client.trigger_offload(
            session_id=request.session_id or f"vision-{datetime.utcnow().timestamp()}",
            context={"image_size": len(request.image)},
            vram_used=metrics["vram_used_mb"],
            vram_total=metrics["vram_total_mb"],
            hamiltonian=H
        )
        raise HTTPException(503, "VRAM saturated, retry in 30s.")
    
    # Ensure YOLO is loaded
    if not yolo.is_loaded:
        # Unload LLM if needed
        if llm.is_loaded and not orchestrator.can_allocate(yolo.vram_mb):
            await llm.unload_model()
        await yolo.load_model()
    
    # Add to queue (P2)
    request_id = await request_queue.enqueue(Priority.P2, request.dict())
    
    try:
        result = await yolo.detect(
            image_b64=request.image,
            confidence=request.confidence,
            iou=request.iou
        )
        request_queue.complete(request_id)
        return result
    except Exception as e:
        request_queue.fail(request_id, str(e))
        raise HTTPException(500, f"Detection failed: {str(e)}")

# ==================================================================================
# LLM Endpoints
# ==================================================================================

class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    max_tokens: int = Field(512, ge=1, le=2048)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    stream: bool = False
    session_id: Optional[str] = None

@app.post("/llm/chat")
async def chat(request: ChatRequest):
    """Conversational AI with Qwen 1.5 4B."""
    # Check VRAM
    metrics = await resource_monitor.get_metrics()
    H = orchestrator.calculate_hamiltonian(metrics["vram_used_mb"], metrics["temperature"])
    
    if H > 7.5:  # Lower threshold for LLM
        # Try unloading YOLO first
        if yolo.is_loaded:
            await yolo.unload_model()
            await asyncio.sleep(1)  # Wait for VRAM release
            metrics = await resource_monitor.get_metrics()
            H = orchestrator.calculate_hamiltonian(metrics["vram_used_mb"], metrics["temperature"])
    
    if H > 8.5:
        await offload_client.trigger_offload(
            session_id=request.session_id or f"llm-{datetime.utcnow().timestamp()}",
            context={"messages": request.messages},
            vram_used=metrics["vram_used_mb"],
            vram_total=metrics["vram_total_mb"],
            hamiltonian=H
        )
        raise HTTPException(503, "VRAM saturated, retry in 60s.")
    
    # Ensure LLM is loaded
    if not llm.is_loaded:
        if not orchestrator.can_allocate(llm.vram_mb):
            # Unload YOLO to make space
            if yolo.is_loaded:
                await yolo.unload_model()
        await llm.load_model()
    
    # Add to queue (P3)
    request_id = await request_queue.enqueue(Priority.P3, request.dict())
    
    try:
        result = await llm.chat(
            messages=request.messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stream=request.stream
        )
        request_queue.complete(request_id)
        return result
    except Exception as e:
        request_queue.fail(request_id, str(e))
        raise HTTPException(500, f"Chat failed: {str(e)}")

# ==================================================================================
# Multi-Modal Pipeline
# ==================================================================================

class PipelineRequest(BaseModel):
    image: Optional[str] = None
    prompt: Optional[str] = None
    services: List[str] = Field(..., description="Services to use: vision, llm, cuda-q")
    session_id: Optional[str] = None

@app.post("/pipeline/analyze")
async def multimodal_pipeline(request: PipelineRequest):
    """Multi-modal analysis pipeline."""
    results = {}
    start_time = datetime.utcnow()
    
    # Vision step
    if "vision" in request.services and request.image:
        detection_result = await detect_objects(DetectionRequest(
            image=request.image,
            session_id=request.session_id
        ))
        results["vision"] = detection_result
    
    # LLM step
    if "llm" in request.services and request.prompt:
        messages = [{"role": "user", "content": request.prompt}]
        if "vision" in results:
            # Add vision context
            objects = [d["class"] for d in results["vision"]["detections"]]
            messages[0]["content"] += f"\n\nDetected objects: {', '.join(objects)}"
        
        chat_result = await chat(ChatRequest(
            messages=messages,
            session_id=request.session_id
        ))
        results["llm"] = chat_result
    
    # CUDA-Q step (if requested)
    if "cuda-q" in request.services:
        # This would need problem definition from LLM output
        results["cuda-q"] = {"status": "requires_problem_definition"}
    
    end_time = datetime.utcnow()
    metrics = await resource_monitor.get_metrics()
    
    return {
        "results": results,
        "total_time_ms": (end_time - start_time).total_seconds() * 1000,
        "vram_peak_mb": metrics["vram_used_mb"],
        "hamiltonian": orchestrator.calculate_hamiltonian(
            metrics["vram_used_mb"], 
            metrics["temperature"]
        )
    }

# ==================================================================================
# Internal Admin Endpoints
# ==================================================================================

@app.post("/internal/unload-model")
async def unload_model(service: str):
    """Force unload a model (admin only)."""
    if service == "yolo" and yolo.is_loaded:
        await yolo.unload_model()
        return {"status": "unloaded", "service": "yolo"}
    elif service == "llm" and llm.is_loaded:
        await llm.unload_model()
        return {"status": "unloaded", "service": "llm"}
    else:
        raise HTTPException(400, f"Invalid service or already unloaded: {service}")

@app.post("/internal/load-model")
async def load_model(service: str):
    """Force load a model (admin only)."""
    metrics = await resource_monitor.get_metrics()
    
    if service == "yolo":
        if orchestrator.can_allocate(yolo.vram_mb):
            await yolo.load_model()
            return {"status": "loaded", "service": "yolo"}
        else:
            raise HTTPException(503, "Insufficient VRAM")
    elif service == "llm":
        if orchestrator.can_allocate(llm.vram_mb):
            await llm.load_model()
            return {"status": "loaded", "service": "llm"}
        else:
            raise HTTPException(503, "Insufficient VRAM")
    else:
        raise HTTPException(400, f"Invalid service: {service}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")
```

---

### File 2: VRAM Orchestrator Core
**Location:** `~/unified-inference/python/core/vram_orchestrator.py`

```python
"""VRAM orchestration using waveform equilibrium principles."""

from typing import Dict, List, Optional
from dataclasses import dataclass
import asyncio

@dataclass
class ModelAllocation:
    """VRAM allocation for a model."""
    name: str
    vram_mb: int
    priority: int  # 1=highest
    loaded: bool = False
    last_used: Optional[float] = None

class VRAMOrchestrator:
    """Manages VRAM allocation based on waveform equilibrium."""
    
    def __init__(self, total_vram_gb: float, temp_max: float, hamiltonian_threshold: float):
        self.total_vram_mb = int(total_vram_gb * 1024)
        self.temp_max = temp_max
        self.hamiltonian_threshold = hamiltonian_threshold
        self.allocations: Dict[str, ModelAllocation] = {}
        
    def register_model(self, name: str, vram_mb: int, priority: int):
        """Register a model for orchestration."""
        self.allocations[name] = ModelAllocation(
            name=name,
            vram_mb=vram_mb,
            priority=priority
        )
    
    def calculate_hamiltonian(self, vram_used_mb: int, temp_celsius: float) -> float:
        """Calculate resource Hamiltonian.
        
        H_resource = (VRAM_used/VRAM_total) * 10 + 0.3 * (T/T_max)
        """
        vram_term = (vram_used_mb / self.total_vram_mb) * 10.0
        thermal_term = 0.3 * (temp_celsius / self.temp_max)
        return vram_term + thermal_term
    
    def can_allocate(self, vram_mb: int, current_used_mb: Optional[int] = None) -> bool:
        """Check if VRAM can be allocated."""
        if current_used_mb is None:
            # Conservative estimate
            current_used_mb = sum(
                alloc.vram_mb for alloc in self.allocations.values() if alloc.loaded
            )
        return (current_used_mb + vram_mb) < (self.total_vram_mb * 0.95)  # 95% threshold
    
    def suggest_unload(self, required_mb: int, current_used_mb: int) -> List[str]:
        """Suggest models to unload to free VRAM."""
        # Sort by priority (lowest first) and last used
        loaded = [
            alloc for alloc in self.allocations.values() 
            if alloc.loaded and alloc.priority > 1  # Don't unload P1
        ]
        loaded.sort(key=lambda x: (x.priority, -(x.last_used or 0)))
        
        to_unload = []
        freed_mb = 0
        
        for alloc in loaded:
            if current_used_mb - freed_mb + required_mb < self.total_vram_mb * 0.9:
                break
            to_unload.append(alloc.name)
            freed_mb += alloc.vram_mb
        
        return to_unload
    
    def mark_loaded(self, name: str):
        """Mark model as loaded."""
        if name in self.allocations:
            self.allocations[name].loaded = True
            import time
            self.allocations[name].last_used = time.time()
    
    def mark_unloaded(self, name: str):
        """Mark model as unloaded."""
        if name in self.allocations:
            self.allocations[name].loaded = False
    
    def update_usage(self, name: str):
        """Update last used timestamp."""
        if name in self.allocations:
            import time
            self.allocations[name].last_used = time.time()
```

---

### File 3: Resource Monitor
**Location:** `~/unified-inference/python/core/resource_monitor.py`

```python
"""Real-time GPU resource monitoring."""

import asyncio
import pynvml
from typing import Dict, Optional
from datetime import datetime

class ResourceMonitor:
    """Monitors GPU VRAM and temperature in real-time."""
    
    def __init__(self, poll_interval: float = 2.0):
        self.poll_interval = poll_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._latest_metrics: Dict = {}
        self._handle = None
        
    async def start(self):
        """Start monitoring loop."""
        pynvml.nvmlInit()
        self._handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        print("✓ Resource monitor started")
        
    async def stop(self):
        """Stop monitoring loop."""
        self._running = False
        if self._task:
            await self._task
        pynvml.nvmlShutdown()
        print("✓ Resource monitor stopped")
        
    async def _monitor_loop(self):
        """Background monitoring loop."""
        while self._running:
            try:
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(self._handle)
                temp = pynvml.nvmlDeviceGetTemperature(self._handle, pynvml.NVML_TEMPERATURE_GPU)
                
                self._latest_metrics = {
                    "vram_used_mb": memory_info.used // (1024 ** 2),
                    "vram_total_mb": memory_info.total // (1024 ** 2),
                    "vram_util_pct": (memory_info.used / memory_info.total) * 100,
                    "temperature": temp,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                print(f"Monitor error: {e}")
            
            await asyncio.sleep(self.poll_interval)
    
    async def get_metrics(self) -> Dict:
        """Get latest metrics."""
        if not self._latest_metrics:
            # First call, do synchronous read
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(self._handle)
            temp = pynvml.nvmlDeviceGetTemperature(self._handle, pynvml.NVML_TEMPERATURE_GPU)
            return {
                "vram_used_mb": memory_info.used // (1024 ** 2),
                "vram_total_mb": memory_info.total // (1024 ** 2),
                "vram_util_pct": (memory_info.used / memory_info.total) * 100,
                "temperature": temp,
                "timestamp": datetime.utcnow().isoformat()
            }
        return self._latest_metrics.copy()
```

---

## Configuration Files

### config/thresholds.yaml
```yaml
vram:
  total_gb: 4.0
  safe_threshold_pct: 90
  warning_threshold_pct: 75
  critical_threshold_pct: 95

temperature:
  max_celsius: 89.6
  safe_celsius: 75.0
  warning_celsius: 80.0

hamiltonian:
  threshold: 8.5
  warning: 7.5
  safe: 5.0
  beta: 0.3  # thermal weight

models:
  cuda_q:
    vram_mb: 124
    priority: 1
    keep_loaded: true
    
  yolo11s:
    vram_mb: 1200
    priority: 2
    keep_loaded: false
    idle_unload_seconds: 300
    
  qwen_1.5_4b:
    vram_mb: 2800
    priority: 3
    keep_loaded: false
    idle_unload_seconds: 60

offload:
  enabled: true
  gateway_url: "http://localhost:8000/v1/orchestrate"
  notion_url: "https://notion-bridge.optimizationinversion.workers.dev"
  retry_attempts: 3
  retry_delay_seconds: 5
```

### config/endpoints.yaml
```yaml
services:
  gateway:
    host: "127.0.0.1"
    port: 3000
    
  orchestrator:
    host: "127.0.0.1"
    port: 8001
    
  cuda_q:
    host: "127.0.0.1"
    port: 8002
    
  yolo:
    host: "127.0.0.1"
    port: 8003
    
  llm:
    host: "127.0.0.1"
    port: 8004

diamond_gateway:
  url: "http://localhost:8000"
  auth_env: "GATEWAY_SECRET"

notion_bridge:
  url: "https://notion-bridge.optimizationinversion.workers.dev"
  database_id: "21e416066ef1411084d1bbaf67af79d1"
```

---

## Implementation Order (Recommended)

### Week 1: Foundation
1. Create directory structure
2. Implement `resource_monitor.py`
3. Implement `vram_orchestrator.py`
4. Test Hamiltonian calculation
5. Implement `orchestrator.py` (health + metrics only)

### Week 2: Service Integration
6. Implement `cuda_q_service.py` (wrap mycelial_qubo.py)
7. Implement `yolo_service.py` (YOLOv11s integration)
8. Test individual services
9. Implement `priority_queue.py`

### Week 3: Advanced Features
10. Implement `llm_service.py` (Xinference + Qwen)
11. Implement `offload_client.py`
12. Test OFFLOAD flow end-to-end
13. Implement `stream_manager.py` for CUDA streams

### Week 4: Gateway & Production
14. Enhance `server.mjs` with routing
15. Add TRTC streaming for real-time vision
16. Create systemd services
17. Load testing and optimization

### Week 5: Deployment & Monitoring
18. Production deployment
19. Monitoring dashboard
20. Documentation and runbooks
21. Performance tuning

---

## Quick Start Script

**Location:** `~/unified-inference/scripts/quick-start.sh`

```bash
#!/bin/bash
set -e

echo "🚀 Diamond Node Unified Inference - Quick Start"

# Check prerequisites
command -v python3 >/dev/null || { echo "Python 3 required"; exit 1; }
command -v node >/dev/null || { echo "Node.js required"; exit 1; }
command -v nvcc >/dev/null || { echo "CUDA required"; exit 1; }

# Setup Python environment
cd ~/unified-inference/python
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Setup Node.js environment
cd ~/unified-inference
npm install

# Configure secrets
if [ -z "$GATEWAY_SECRET" ]; then
    echo "⚠️  GATEWAY_SECRET not set. Export it:"
    echo "   export GATEWAY_SECRET='your-secret'"
fi

# Start services
echo "Starting orchestrator..."
source venv/bin/activate
python python/orchestrator.py &
ORCH_PID=$!

sleep 5

echo "Starting gateway..."
node server.mjs &
GATEWAY_PID=$!

echo ""
echo "✅ Services started:"
echo "   Orchestrator: http://localhost:8001 (PID: $ORCH_PID)"
echo "   Gateway: http://localhost:3000 (PID: $GATEWAY_PID)"
echo ""
echo "Test with:"
echo "   curl http://localhost:3000/health"
echo "   curl http://localhost:3000/metrics"
echo ""
echo "Stop with:"
echo "   kill $ORCH_PID $GATEWAY_PID"
```

---

## Next Steps

1. **Review architecture** in `UNIFIED_INFERENCE_ARCHITECTURE.md`
2. **Create directory structure**: `mkdir -p ~/unified-inference/{python/{core,services},config,scripts}`
3. **Start with Phase 1** files above
4. **Test incrementally** after each file
5. **Iterate based on benchmarks**

All files are ready for implementation. The architecture is designed for:
- ✅ 4 GB VRAM constraint
- ✅ Dynamic model loading
- ✅ Waveform equilibrium orchestration
- ✅ Multi-service coexistence
- ✅ Production-ready monitoring
