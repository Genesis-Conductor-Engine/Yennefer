# Monitoring Integration - Diamond Node Unified Inference

## Overview

This document covers the complete monitoring setup for the Diamond Node Unified Inference System, including OpenTelemetry, AppSignal, and Vercel Analytics integrations.

## Architecture

```
Claude Orchestrator (Python)
    ↓
OpenTelemetry SDK
    ↓
OTLP Exporter (HTTP)
    ↓
AppSignal Collector (EU-Central)
    ↓
AppSignal Dashboard
```

```
Server (Node.js)
    ↓
Vercel Analytics SDK
    ↓
Vercel Edge Network
    ↓
Vercel Analytics Dashboard
```

## Setup Instructions

### 1. Environment Configuration

Create or update `~/.appsignal.env`:

```bash
APPSIGNAL_API_KEY=b9484e99-79b4-4341-ad99-1c264ad5cd93
APPSIGNAL_APP_NAME=diamondnode
APPSIGNAL_ENVIRONMENT=production
APPSIGNAL_PUSH_API_ENDPOINT=14g2tvpd.eu-central.appsignal-collector.net
```

Source the environment:

```bash
source ~/.appsignal.env
export APPSIGNAL_API_KEY APPSIGNAL_APP_NAME APPSIGNAL_ENVIRONMENT APPSIGNAL_PUSH_API_ENDPOINT
```

### 2. Python Dependencies

Install OpenTelemetry packages in the unified_inference venv:

```bash
cd ~/unified_inference
source venv/bin/activate
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp opentelemetry-instrumentation
```

### 3. Node.js Dependencies

Vercel Analytics is already installed:

```bash
cd ~
npm list @vercel/analytics
# Output: @vercel/analytics@2.0.1
```

### 4. Running with Monitoring

Start the orchestrator with AppSignal credentials:

```bash
cd ~/unified_inference
source venv/bin/activate
source ~/.appsignal.env

python3 claude_orchestrator.py
```

Expected output:
```
[✓] OpenTelemetry traces configured for AppSignal
[✓] OpenTelemetry metrics configured for AppSignal
```

## Metric Definitions

### 1. `tool_calls_total` (Counter)

Tracks total number of tool calls by name and status.

**Labels:**
- `tool`: Tool name (e.g., `query_vram_status`, `run_cuda_q_qaoa`)
- `status`: Execution status (`success` or `error`)

**Example:**
```
tool_calls_total{tool="run_cuda_q_qaoa", status="success"} = 42
tool_calls_total{tool="query_vram_status", status="success"} = 156
tool_calls_total{tool="optimize_gas_fees", status="error"} = 3
```

### 2. `tool_execution_duration` (Histogram)

Measures tool execution latency in milliseconds.

**Labels:**
- `tool`: Tool name

**Buckets:** Auto-generated based on distribution
**Unit:** milliseconds (ms)

**Example:**
```
tool_execution_duration{tool="run_cuda_q_qaoa"} = p50: 8125ms, p95: 15240ms, p99: 28450ms
tool_execution_duration{tool="query_vram_status"} = p50: 45ms, p95: 120ms, p99: 250ms
```

### 3. `vram_usage_bytes` (Observable Gauge)

Current GPU VRAM usage from Diamond Gateway.

**Unit:** bytes
**Update frequency:** On every `query_vram_status` call

**Example:**
```
vram_usage_bytes = 2147483648  # 2 GB
```

### 4. `hamiltonian_value` (Observable Gauge)

Resource Hamiltonian H_resource calculated by Diamond Gateway.

**Formula:** `H = (VRAM_Used / VRAM_Total) * 10`
**Update frequency:** On every `query_vram_status` call

**Thresholds:**
- H < 5.0: OPTIMAL
- 5.0 ≤ H < 7.5: DYNAMIC
- 7.5 ≤ H < 8.5: SEQUENTIAL
- H ≥ 8.5: OFFLOAD

**Example:**
```
hamiltonian_value = 7.8  # SEQUENTIAL state
```

### 5. `qaoa_energy` (Observable Gauge)

Energy value from CUDA-Q QAOA optimization.

**Update frequency:** On every `run_cuda_q_qaoa` completion
**Interpretation:** Lower energy = better optimization

**Example:**
```
qaoa_energy = -14.567
```

### 6. `blockchain_gas_price` (Observable Gauge)

Current Ethereum gas price in Gwei.

**Unit:** Gwei (1 Gwei = 10^9 Wei)
**Update frequency:** On every `optimize_gas_fees` call

**Example:**
```
blockchain_gas_price = 42.5  # 42.5 Gwei
```

### 7. `vram_state_transitions` (Counter)

Tracks VRAM state transitions when Hamiltonian crosses thresholds.

**Labels:**
- `from_state`: Previous state (OPTIMAL/DYNAMIC/SEQUENTIAL/OFFLOAD)
- `to_state`: New state
- `hamiltonian`: H value at transition (rounded to 2 decimals)

**Example:**
```
vram_state_transitions{from_state="DYNAMIC", to_state="SEQUENTIAL", hamiltonian="7.85"} = 5
vram_state_transitions{from_state="SEQUENTIAL", to_state="OFFLOAD", hamiltonian="8.92"} = 2
```

## Tracing

### Spans

All tool executions are traced with OpenTelemetry spans:

**Span Name:** `tool_execution`

**Attributes:**
- `tool.name`: Name of the tool
- `tool.input`: JSON-encoded input (truncated to 500 chars)
- `tool.status`: `success` or `error`
- `error.message`: Error message (if failed)

**Example trace:**
```
Trace ID: 1a2b3c4d5e6f7890
Span: tool_execution
  - tool.name: run_cuda_q_qaoa
  - tool.input: {"shots": 512, "outer_rounds": 3}
  - tool.status: success
  - duration: 8.125s
```

### VRAM State Transition Events

State transitions emit dedicated spans:

**Span Name:** `vram_state_transition`

**Attributes:**
- `vram.old_state`: Previous state
- `vram.new_state`: New state
- `vram.hamiltonian`: Current H value

**Event:**
- Name: `VRAM state changed to {state}`
- `threshold`: Threshold description (e.g., "7.5 <= H < 8.5")
- `action`: Recommended action (e.g., "Enforce serialization")

### Error Tracking

Exceptions are captured with OpenTelemetry:

**Span Status:** `ERROR`
**Exception Details:**
- `error.message`: Exception message
- `exception.type`: Python exception type
- `exception.stacktrace`: Full stack trace

## Dashboard Guide

### Accessing AppSignal Dashboard

1. Log in to AppSignal: https://appsignal.com/
2. Select "diamondnode" app
3. Navigate to "Custom Metrics" or "Traces"

### Importing Dashboard Configuration

Upload `appsignal_dashboard.json` to AppSignal:

```bash
# Dashboard config location
~/unified_inference/appsignal_dashboard.json
```

**Dashboard includes:**
1. **VRAM Usage Over Time** - Line chart showing memory trends
2. **Hamiltonian Distribution** - Histogram with state thresholds
3. **Tool Call Frequency** - Bar chart by tool name
4. **Tool Execution Latency** - Heatmap showing p95 latencies
5. **Error Rate** - Counter for failed tool calls
6. **VRAM State Transitions** - Timeline view of state changes
7. **QAOA Energy Convergence** - Line chart of optimization energy
8. **Blockchain Gas Price** - Line chart with threshold alerts
9. **System Health Summary** - Stats panel with key metrics

### Setting Up Alerts

AppSignal alerts are configured in the dashboard JSON:

1. **High Hamiltonian - OFFLOAD Imminent**
   - Condition: `hamiltonian_value > 8.5` for 5 minutes
   - Severity: Critical
   - Channels: Slack, Email

2. **High Error Rate**
   - Condition: Error rate > 10% for 10 minutes
   - Severity: Warning
   - Channels: Slack

3. **QAOA Energy Anomaly**
   - Condition: Anomaly detection on `qaoa_energy`
   - Severity: Warning
   - Channels: Slack

4. **Extreme Gas Prices**
   - Condition: `blockchain_gas_price > 200 Gwei` for 5 minutes
   - Severity: Warning
   - Channels: Slack

## Vercel Analytics (Node.js)

### Custom Events

The `server.mjs` module exports tracking functions:

```javascript
import { trackModelUsage, trackVramStateChange, trackToolExecution, trackInferenceComplete } from './server.mjs';

// Track model usage
await trackModelUsage('llama3', 8125, 'success');

// Track VRAM state change
await trackVramStateChange('DYNAMIC', 'SEQUENTIAL', 7.85);

// Track tool execution
await trackToolExecution('run_cuda_q_qaoa', 8125, 'success');

// Track inference completion
await trackInferenceComplete('llama3', 512, 1024, 8125);
```

### Viewing Analytics

1. Log in to Vercel: https://vercel.com/
2. Select your project
3. Navigate to "Analytics" tab
4. View custom events under "Events"

## Testing Monitoring

### 1. Test AppSignal Connection

```bash
cd ~/unified_inference
source venv/bin/activate
source ~/.appsignal.env

python3 << 'EOF'
from claude_orchestrator import ClaudeOrchestrator
import asyncio
import os

async def test_monitoring():
    # Initialize orchestrator (will configure monitoring)
    orchestrator = ClaudeOrchestrator()
    
    # Test VRAM query (updates metrics)
    result = await orchestrator.execute_tool("query_vram_status", {})
    print(f"VRAM Status: {result}")
    
    # Test CUDA-Q QAOA (creates trace)
    result = await orchestrator.execute_tool("run_cuda_q_qaoa", {"shots": 256, "outer_rounds": 2})
    print(f"QAOA Result: {result.get('status')}")
    
    print("\n[✓] Monitoring test complete")
    print("Check AppSignal dashboard for traces and metrics")

asyncio.run(test_monitoring())
EOF
```

### 2. Trigger VRAM State Transition

Use mock VRAM values to test state transitions:

```bash
# Test OFFLOAD threshold (H > 8.5)
curl -X POST http://localhost:8000/v1/orchestrate \
  -H "Authorization: Bearer $GATEWAY_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "monitor-test",
    "context_buffer": "[TEST]",
    "mock_vram_used": 9200,
    "mock_vram_total": 10000
  }'
```

Expected output in orchestrator:
```
[VRAM State Transition] OPTIMAL → OFFLOAD (H=9.20)
```

### 3. Verify Metrics in AppSignal

Check the following in AppSignal dashboard:

1. **Traces tab:**
   - `tool_execution` spans appear
   - `vram_state_transition` spans appear
   - Span attributes are populated

2. **Custom Metrics tab:**
   - `tool_calls_total` increments
   - `tool_execution_duration` records latencies
   - `vram_usage_bytes` updates
   - `hamiltonian_value` updates

3. **Error tracking:**
   - Intentionally trigger an error (e.g., invalid tool name)
   - Verify error appears in "Errors" tab with stack trace

### 4. Test Vercel Analytics

```bash
cd ~
node << 'EOF'
import('./server.mjs').then(async (module) => {
  await module.trackModelUsage('test-model', 1000, 'success');
  await module.trackToolExecution('test-tool', 500, 'success');
  console.log('[✓] Vercel Analytics events sent');
});
EOF
```

## Troubleshooting

### Issue: "OpenTelemetry not available" warning

**Cause:** OpenTelemetry packages not installed in active Python environment

**Solution:**
```bash
cd ~/unified_inference
source venv/bin/activate
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp
```

### Issue: "APPSIGNAL_API_KEY not set" warning

**Cause:** Environment variable not loaded

**Solution:**
```bash
source ~/.appsignal.env
export APPSIGNAL_API_KEY APPSIGNAL_APP_NAME APPSIGNAL_ENVIRONMENT APPSIGNAL_PUSH_API_ENDPOINT
```

### Issue: Traces not appearing in AppSignal

**Possible causes:**
1. API key incorrect
2. Network connectivity to AppSignal collector
3. Firewall blocking HTTPS to `14g2tvpd.eu-central.appsignal-collector.net`

**Debug steps:**
```bash
# Test network connectivity
curl -v https://14g2tvpd.eu-central.appsignal-collector.net/v1/traces \
  -H "Authorization: Bearer $APPSIGNAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"test": true}'

# Check Python logs
cd ~/unified_inference
source venv/bin/activate
python3 -c "from claude_orchestrator import ClaudeOrchestrator; o = ClaudeOrchestrator()"
# Should print: [✓] OpenTelemetry traces configured for AppSignal
```

### Issue: Metrics not updating

**Possible causes:**
1. Tool calls not being executed
2. Observable gauge callbacks not firing
3. Metric export interval not reached (30s default)

**Debug steps:**
```bash
# Run a tool and wait 30+ seconds for export
python3 << 'EOF'
import asyncio
import time
from claude_orchestrator import ClaudeOrchestrator

async def test():
    o = ClaudeOrchestrator()
    result = await o.execute_tool("query_vram_status", {})
    print(f"VRAM: {result.get('vram_used_mb')} MB")
    print(f"Hamiltonian: {result.get('hamiltonian')}")
    print("Waiting 35 seconds for metric export...")
    time.sleep(35)
    print("Metrics should now appear in AppSignal")

asyncio.run(test())
EOF
```

### Issue: Vercel Analytics not tracking events

**Possible causes:**
1. `@vercel/analytics` not installed
2. Project not connected to Vercel
3. Server-side tracking requires Vercel deployment

**Solution:**
```bash
# Verify package installation
npm list @vercel/analytics

# Note: Server-side tracking typically requires deployment to Vercel
# For local development, use client-side tracking or deploy to Vercel
```

## Performance Considerations

### OpenTelemetry Overhead

- **Trace overhead:** ~0.1-1ms per span
- **Metric overhead:** Negligible (asynchronous export)
- **Network:** Batched exports every 30 seconds

### Best Practices

1. **Truncate large inputs:** Tool inputs are truncated to 500 chars in spans
2. **Async exports:** Metrics and traces export asynchronously (non-blocking)
3. **Batch processing:** OTLP exporter batches spans to reduce network calls
4. **Sampling:** For high-volume production, consider trace sampling:

```python
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

# Sample 10% of traces
sampler = TraceIdRatioBased(0.1)
trace_provider = TracerProvider(sampler=sampler, resource=resource)
```

## Integration with Other Components

### Diamond Gateway

Gateway VRAM metrics flow to AppSignal via orchestrator:

```
Diamond Gateway (FastAPI)
    ↓ HTTP /v1/orchestrate
Claude Orchestrator
    ↓ execute_tool("query_vram_status")
OpenTelemetry Metrics
    ↓ vram_usage_bytes, hamiltonian_value
AppSignal Dashboard
```

### CUDA-Q QAOA

QAOA energy values tracked as observable gauge:

```
CUDA-Q Script (mycelial_qubo.py)
    ↓ subprocess execution
Claude Orchestrator
    ↓ execute_tool("run_cuda_q_qaoa")
OpenTelemetry Metrics
    ↓ qaoa_energy gauge
AppSignal Dashboard
```

### Blockchain Tools

Gas price and portfolio metrics tracked:

```
Blockchain Tools (Web3)
    ↓ async tool execution
Claude Orchestrator
    ↓ execute_tool("optimize_gas_fees")
OpenTelemetry Metrics
    ↓ blockchain_gas_price gauge
AppSignal Dashboard
```

## Maintenance

### Updating Dashboard Configuration

1. Edit `~/unified_inference/appsignal_dashboard.json`
2. Re-upload to AppSignal dashboard
3. Verify graphs and alerts updated

### Adding New Metrics

To add a new metric to the orchestrator:

```python
# In _init_monitoring():
self.metrics["my_new_metric"] = self.meter.create_counter(
    "my_new_metric",
    description="Description of the metric"
)

# In execute_tool():
self.metrics["my_new_metric"].add(1, {"label": "value"})
```

### Rotating API Keys

To rotate AppSignal API key:

1. Generate new key in AppSignal dashboard
2. Update `~/.appsignal.env`
3. Restart orchestrator

```bash
# Edit credentials
vim ~/.appsignal.env

# Reload environment
source ~/.appsignal.env

# Restart orchestrator
cd ~/unified_inference
source venv/bin/activate
python3 claude_orchestrator.py
```

## Resources

- **AppSignal Documentation:** https://docs.appsignal.com/
- **OpenTelemetry Python:** https://opentelemetry.io/docs/instrumentation/python/
- **Vercel Analytics:** https://vercel.com/docs/analytics
- **Diamond Gateway Docs:** `~/unified_inference/GATEWAY_INTEGRATION.md`
- **CUDA-Q Integration:** `~/unified_inference/CUDA_Q_INTEGRATION.md`

## Summary

The monitoring integration provides:
- ✅ 7 metrics tracked (tool calls, duration, VRAM, Hamiltonian, QAOA energy, gas price, state transitions)
- ✅ Distributed tracing with OpenTelemetry
- ✅ VRAM state transition detection and alerting
- ✅ Error tracking with stack traces
- ✅ Custom AppSignal dashboard with 9 panels and 4 alerts
- ✅ Vercel Analytics for Node.js events
- ✅ Integration with Diamond Gateway, CUDA-Q, and blockchain tools

The system is now fully observable with real-time metrics, traces, and alerts.
