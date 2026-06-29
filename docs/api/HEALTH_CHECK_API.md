# Health Check API Reference

API documentation for system health monitoring endpoints.

## Overview

The Health Check API provides real-time system status, component health, and performance metrics.

## Endpoint

**URL:** `GET /health`

**Authentication:** None (public endpoint)

**Response Format:** JSON

## Response Schema

```json
{
  "status": "healthy" | "degraded" | "unhealthy",
  "timestamp": "2025-05-12T10:30:00Z",
  "version": "1.0.0",
  "uptime_seconds": 86400,
  "components": {
    "orchestrator": { ... },
    "blockchain_tools": { ... },
    "yolo11": { ... },
    "cuda_q": { ... },
    "mcp_apps": { ... },
    "database": { ... }
  },
  "metrics": {
    "vram": { ... },
    "requests": { ... },
    "latency": { ... }
  }
}
```

## Component Status

Each component reports detailed health information:

### Claude Orchestrator

```json
{
  "orchestrator": {
    "status": "healthy",
    "api_key_valid": true,
    "model": "claude-3-5-sonnet-20241022",
    "cache_enabled": true,
    "streaming_enabled": true,
    "last_request": "2025-05-12T10:29:45Z",
    "error_rate": 0.001,
    "avg_response_time_ms": 245
  }
}
```

### Blockchain Tools

```json
{
  "blockchain_tools": {
    "status": "healthy",
    "rpc_connections": {
      "ethereum": "connected",
      "polygon": "connected",
      "arbitrum": "connected"
    },
    "api_keys_valid": {
      "alchemy": true,
      "etherscan": true,
      "coingecko": true
    },
    "cache_hit_rate": 0.85,
    "avg_query_time_ms": 150
  }
}
```

### YOLO11 Detection

```json
{
  "yolo11": {
    "status": "healthy",
    "model_loaded": true,
    "model_path": "/models/yolo11n.pt",
    "device": "cuda:0",
    "vram_usage_mb": 512,
    "avg_inference_time_ms": 45,
    "detections_count": 1234
  }
}
```

### CUDA-Q QAOA

```json
{
  "cuda_q": {
    "status": "healthy",
    "backend": "nvidia",
    "qpu_available": true,
    "max_qubits": 30,
    "avg_optimization_time_s": 2.5,
    "energy_convergence_rate": 0.95
  }
}
```

### MCP Apps

```json
{
  "mcp_apps": {
    "status": "healthy",
    "apps_loaded": 3,
    "active_sessions": 5,
    "jsonrpc_version": "2.0",
    "avg_render_time_ms": 80
  }
}
```

### Database

```json
{
  "database": {
    "status": "healthy",
    "type": "postgresql",
    "connection_pool": {
      "active": 5,
      "idle": 10,
      "max": 20
    },
    "avg_query_time_ms": 15
  }
}
```

## System Metrics

### VRAM Monitoring (H_resource)

```json
{
  "vram": {
    "total_mb": 10240,
    "used_mb": 3584,
    "free_mb": 6656,
    "utilization": 0.35,
    "hamiltonian": 3.5,
    "threshold": 8.5,
    "status": "healthy"
  }
}
```

**H_resource Formula:**
```
H(s) = (VRAM_Used / VRAM_Total) * 10
```

- `H < 8.5`: System healthy, continue operations
- `H ≥ 8.5`: High memory pressure, trigger offload

### Request Metrics

```json
{
  "requests": {
    "total": 123456,
    "last_minute": 45,
    "last_hour": 2340,
    "last_24h": 98765,
    "error_rate": 0.002,
    "rate_limit_hits": 5
  }
}
```

### Latency Metrics

```json
{
  "latency": {
    "p50_ms": 120,
    "p95_ms": 450,
    "p99_ms": 890,
    "max_ms": 2340
  }
}
```

## Status Definitions

### Overall Status

- **healthy**: All components operational, no issues
- **degraded**: Some components have warnings, system functional
- **unhealthy**: Critical components failing, system impaired

### Component Status

- **healthy**: Component fully operational
- **warning**: Component operational but with issues
- **error**: Component not functioning
- **disabled**: Component intentionally disabled

## Examples

### Basic Health Check

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "healthy",
  "timestamp": "2025-05-12T10:30:00Z",
  "version": "1.0.0",
  "uptime_seconds": 86400
}
```

### Python Client

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get("http://localhost:8000/health")
    health = response.json()
    
    if health["status"] == "healthy":
        print("✓ System healthy")
    else:
        print(f"⚠ System {health['status']}")
        
    # Check VRAM
    vram = health["metrics"]["vram"]
    if vram["hamiltonian"] > 8.5:
        print(f"⚠ High VRAM pressure: H={vram['hamiltonian']:.2f}")
```

### Monitoring Script

```python
import asyncio
import httpx

async def monitor_health():
    """Monitor system health every 30 seconds."""
    client = httpx.AsyncClient()
    
    while True:
        try:
            response = await client.get("http://localhost:8000/health", timeout=5)
            health = response.json()
            
            # Check overall status
            if health["status"] != "healthy":
                alert(f"System {health['status']}")
            
            # Check components
            for name, component in health["components"].items():
                if component["status"] != "healthy":
                    alert(f"Component {name} is {component['status']}")
            
            # Check VRAM
            vram = health["metrics"]["vram"]
            if vram["hamiltonian"] > 8.5:
                alert(f"High VRAM: H={vram['hamiltonian']:.2f}")
            
        except httpx.TimeoutException:
            alert("Health check timeout")
        except Exception as e:
            alert(f"Health check failed: {e}")
        
        await asyncio.sleep(30)

def alert(message: str):
    """Send alert notification."""
    print(f"[ALERT] {message}")
    # Send to monitoring system, Slack, etc.
```

## Integration with Monitoring

### AppSignal

```python
import appsignal

@appsignal.instrument
async def check_health():
    response = await httpx.get("http://localhost:8000/health")
    health = response.json()
    
    # Report metrics
    appsignal.set_gauge("system.health", 1 if health["status"] == "healthy" else 0)
    appsignal.set_gauge("vram.hamiltonian", health["metrics"]["vram"]["hamiltonian"])
    appsignal.set_gauge("requests.error_rate", health["metrics"]["requests"]["error_rate"])
    
    return health
```

### Prometheus

```python
from prometheus_client import Gauge, Counter

# Define metrics
health_status = Gauge('system_health_status', 'System health status (1=healthy)')
vram_hamiltonian = Gauge('vram_hamiltonian', 'VRAM Hamiltonian value')
request_total = Counter('requests_total', 'Total requests')

async def export_metrics():
    """Export health metrics to Prometheus."""
    response = await httpx.get("http://localhost:8000/health")
    health = response.json()
    
    health_status.set(1 if health["status"] == "healthy" else 0)
    vram_hamiltonian.set(health["metrics"]["vram"]["hamiltonian"])
    request_total.inc(health["metrics"]["requests"]["last_minute"])
```

## Configuration

Configure health check behavior:

```bash
# Health check settings
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_CACHE_TTL=5
HEALTH_CHECK_TIMEOUT=10

# Component checks
CHECK_ORCHESTRATOR=true
CHECK_BLOCKCHAIN=true
CHECK_YOLO11=true
CHECK_CUDA_Q=true
CHECK_MCP_APPS=true

# Thresholds
VRAM_WARNING_THRESHOLD=7.5
VRAM_CRITICAL_THRESHOLD=8.5
ERROR_RATE_THRESHOLD=0.01
```

## Troubleshooting

### Component Unhealthy

If a component reports `error` status, check:

1. **Orchestrator:** Verify `ANTHROPIC_API_KEY`
2. **Blockchain:** Check RPC URLs and API keys
3. **YOLO11:** Ensure model file exists and CUDA available
4. **CUDA-Q:** Verify NVIDIA backend installation
5. **MCP Apps:** Check port 8000 not in use

### High VRAM (H > 8.5)

Actions when Hamiltonian exceeds threshold:

1. Trigger context offload to Notion
2. Clear model cache
3. Restart inference services
4. Scale to additional GPU

### High Error Rate

If `error_rate > 0.01`:

1. Check logs for recent errors
2. Verify API rate limits
3. Check network connectivity
4. Review recent deployments

## Related Documentation

- [Monitoring Setup](../deployment/APPSIGNAL_MONITORING_SETUP.md)
- [Production Deployment](../deployment/PRODUCTION_DEPLOYMENT_COMPLETE.md)
- [Troubleshooting Guide](../guides/TROUBLESHOOTING.md)

---

**Last updated:** 2025-05-12
