# AppSignal Monitoring Setup - Diamond Node Unified Inference System

## ✅ Configuration Complete

### **Credentials**
- **App Name:** diamondnode
- **Environment:** production
- **API Key:** b9484e99-79b4-4341-ad99-1c264ad5cd93
- **Endpoint:** 14g2tvpd.eu-central.appsignal-collector.net
- **Service:** Unified Inference System

### **OpenTelemetry Monitor**
- **Binary:** `/home/diamondnode/opentelemetry-go/otel-monitor` (21 MB)
- **Source:** `/home/diamondnode/opentelemetry-go/main.go`
- **Status:** ✅ Built successfully

---

## 🚀 Quick Start

### **1. Load Environment Variables**
```bash
source ~/.appsignal.env
```

### **2. Run OpenTelemetry Monitor**
```bash
cd ~/opentelemetry-go
export APPSIGNAL_API_KEY=b9484e99-79b4-4341-ad99-1c264ad5cd93
./otel-monitor
```

### **3. Verify in AppSignal Dashboard**
Visit: https://appsignal.com/diamondnode/sites/production

---

## 📊 Metrics Being Monitored

### **System Metrics**
- CPU usage
- Memory usage
- GPU VRAM (via Diamond Gateway)
- GPU temperature
- Disk I/O

### **Application Metrics**
1. **CUDA-Q QAOA**
   - Iterations per second
   - Energy convergence
   - Quantum purity
   - VRAM usage (124 MB peak)

2. **YOLO11s Vision**
   - Frames per second
   - Detection latency
   - mAP accuracy
   - VRAM usage (1.2 GB)

3. **Qwen 1.5 Chat**
   - Tokens per second
   - Response latency
   - Perplexity
   - VRAM usage (2.5 GB)

4. **Waveform Equilibrium**
   - Resource Hamiltonian (H_resource)
   - OFFLOAD triggers (H > 8.5)
   - Eigenspace purity
   - Convergence metrics

### **Trace Data**
- Request routing
- Model loading times
- Inference latency
- VRAM allocation events
- Error tracking

---

## 🔗 Integration Points

### **1. Diamond Gateway** (`/opt/diamond-gateway/gateway.py`)
```python
import os
from opentelemetry import trace, metrics

# Initialize tracer
tracer = trace.get_tracer("diamond-gateway")
meter = metrics.get_meter("diamond-gateway")

# Track VRAM
vram_gauge = meter.create_gauge(
    "gpu.vram.used",
    description="GPU VRAM usage in MiB",
    unit="MiB"
)

# Track Hamiltonian
hamiltonian_gauge = meter.create_gauge(
    "waveform.hamiltonian",
    description="Resource Hamiltonian value",
    unit="1"
)

@app.post("/v1/orchestrate")
async def orchestrate(request: Request):
    with tracer.start_as_current_span("orchestrate"):
        # ... existing logic
        vram_gauge.set(vram_used_mib)
        hamiltonian_gauge.set(H_resource)
```

### **2. Unified Inference Orchestrator**
```python
# ~/unified_inference/orchestrator.py
from opentelemetry import trace

tracer = trace.get_tracer("inference-orchestrator")

class InferenceOrchestrator:
    def route_request(self, model_type: str):
        with tracer.start_as_current_span("route_request",
                                          attributes={"model": model_type}):
            # ... routing logic
```

### **3. Waveform Equilibrium**
```python
# ~/diamond-node/scripts/waveform_equilibrium.py
from opentelemetry import metrics

meter = metrics.get_meter("waveform-equilibrium")

purity_gauge = meter.create_gauge(
    "qaoa.purity",
    description="Quantum state purity",
    unit="1"
)

energy_histogram = meter.create_histogram(
    "qaoa.energy",
    description="QAOA energy values",
    unit="1"
)
```

---

## 📈 Custom Dashboards

### **Unified Inference Dashboard**
Create in AppSignal with these widgets:

1. **VRAM Usage Timeline**
   - Metric: `gpu.vram.used`
   - Type: Line chart
   - Colors: Green (<60%), Yellow (60-80%), Red (>80%)

2. **Resource Hamiltonian Gauge**
   - Metric: `waveform.hamiltonian`
   - Type: Gauge
   - Alert: H > 8.5 (OFFLOAD threshold)

3. **Model Inference Latency**
   - Metrics: 
     - `cuda_q.inference_time`
     - `yolo11.inference_time`
     - `qwen.inference_time`
   - Type: Stacked bar chart

4. **Throughput by Model**
   - Metrics:
     - `cuda_q.iterations_per_sec`
     - `yolo11.fps`
     - `qwen.tokens_per_sec`
   - Type: Multi-line chart

5. **Error Rate**
   - Metric: `errors.count`
   - Grouped by: model_type
   - Type: Area chart

---

## 🔔 Alert Rules

### **Critical Alerts**
1. **VRAM Exhaustion**
   - Condition: `gpu.vram.used > 3400` (85% of 4 GB)
   - Action: Trigger OFFLOAD to Notion

2. **High Temperature**
   - Condition: `gpu.temperature > 80`
   - Action: Throttle workload

3. **Hamiltonian Threshold**
   - Condition: `waveform.hamiltonian > 8.5`
   - Action: Initiate context offload

### **Warning Alerts**
1. **Slow Inference**
   - Condition: `cuda_q.inference_time > 5000ms`
   - Action: Log and investigate

2. **Low Throughput**
   - Condition: `yolo11.fps < 10`
   - Action: Check VRAM contention

3. **High Error Rate**
   - Condition: `errors.rate > 5%`
   - Action: Page on-call engineer

---

## 🛠️ Troubleshooting

### **API Key Not Found**
```bash
# Check environment
echo $APPSIGNAL_API_KEY

# Reload config
source ~/.appsignal.env

# Verify file
cat ~/.appsignal.env
```

### **Connection Issues**
```bash
# Test endpoint connectivity
curl -I https://14g2tvpd.eu-central.appsignal-collector.net

# Check firewall
sudo ufw status

# Verify DNS
nslookup 14g2tvpd.eu-central.appsignal-collector.net
```

### **No Metrics Showing**
1. Verify otel-monitor is running: `ps aux | grep otel-monitor`
2. Check logs: `journalctl -u otel-monitor -f`
3. Validate API key: Visit AppSignal dashboard
4. Ensure instruments are initialized before use

---

## 📁 File Locations

```
~/
├── .appsignal.env                        (Environment variables)
├── main.go                               (Updated with env var)
├── opentelemetry-go/
│   ├── otel-monitor                      (Compiled binary)
│   └── main.go                           (OpenTelemetry setup)
├── diamond-node/
│   ├── scripts/waveform_equilibrium.py   (Add OTel metrics)
│   └── unified_inference/
│       ├── orchestrator.py               (Add OTel tracing)
│       └── optimizer.py                  (Add OTel metrics)
└── /opt/diamond-gateway/
    └── gateway.py                        (Add OTel integration)
```

---

## 🎯 Next Steps

1. **Immediate:**
   - Run `./otel-monitor` to start sending telemetry
   - Verify data in AppSignal dashboard
   - Set up critical alerts

2. **This Week:**
   - Integrate OTel into Diamond Gateway
   - Add tracing to unified inference orchestrator
   - Create custom dashboards

3. **This Month:**
   - Set up SLO/SLI monitoring
   - Configure anomaly detection
   - Build Pareto frontier visualization

---

## 📚 Resources

- **AppSignal Dashboard:** https://appsignal.com/diamondnode/sites/production
- **OpenTelemetry Docs:** https://opentelemetry.io/docs/
- **AppSignal Go Docs:** https://docs.appsignal.com/go/
- **Python OTel SDK:** https://opentelemetry-python.readthedocs.io/

---

**Status:** ✅ Monitoring infrastructure ready for production deployment!
