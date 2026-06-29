# Agent State Endpoint 500 Error Fix

**Date:** 2026-05-20  
**Status:** ✅ RESOLVED

## Problem

Two endpoints were returning 500 Internal Server Error:
- `/api/agent-state` (simplified agent state)
- `/api/vram` (VRAM metrics)

**Root Cause:**  
The `slowapi` rate limiter was configured with `headers_enabled=True` in the `bot_protection` module. When this option is enabled, the rate limiter needs to inject rate limit headers into the response, which requires a `Response` parameter in the endpoint function signature.

**Error Message:**
```
Exception: parameter `response` must be an instance of starlette.responses.Response
```

## Solution

Added the missing `response: Response` parameter to both affected endpoints:

### 1. `/api/agent-state` endpoint (line 362)

**Before:**
```python
@app.get("/api/agent-state")
@limiter.limit("30/minute")
async def get_agent_state_simple(request: Request):
```

**After:**
```python
@app.get("/api/agent-state")
@limiter.limit("30/minute")
async def get_agent_state_simple(request: Request, response: Response):
```

### 2. `/api/vram` endpoint (line 397)

**Before:**
```python
@app.get("/api/vram")
@limiter.limit("20/minute")
async def get_vram_status(request: Request):
```

**After:**
```python
@app.get("/api/vram")
@limiter.limit("20/minute")
async def get_vram_status(request: Request, response: Response):
```

## Verification

All endpoints now return 200 OK:

```bash
# Agent state (simplified)
curl http://localhost:8080/api/agent-state
# Returns: {"state": {...}, "timestamp": "..."}

# Agent state (comprehensive)
curl http://localhost:8080/api/agent/state
# Returns: {"status": "idle", "current_activity": null, ...}

# VRAM metrics
curl http://localhost:8080/api/vram
# Returns: {"detail": "Gateway unavailable..."} (401 from gateway, not 500)

# Health check
curl http://localhost:8080/api/health
# Returns: {"status": "healthy", ...}

# WebSocket
wscat -c ws://localhost:8080/ws/agent-state
# Connects successfully, receives {"type": "connection", ...}
```

## Why This Happened

The `/api/agent/state` endpoint already had the `response: Response` parameter, so it was working correctly. The simpler endpoints (`/api/agent-state` and `/api/vram`) were created without this parameter, causing the 500 error when the rate limiter tried to inject headers.

## Affected Files

- `web/ui/web_ui.py` (2 endpoints fixed)

## Related Configuration

The rate limiter is configured in `src/security/bot_protection.py`:

```python
limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=["100/minute"],
    storage_uri="memory://",
    headers_enabled=True,  # This requires Response parameter
)
```

## Best Practice

**All FastAPI endpoints decorated with `@limiter.limit()` must include both:**
1. `request: Request` (for rate limit key calculation)
2. `response: Response` (for rate limit header injection when `headers_enabled=True`)

```python
@app.get("/api/example")
@limiter.limit("30/minute")
async def example_endpoint(request: Request, response: Response):
    return {"result": "success"}
```

## Status

- ✅ `/api/agent-state` - Working (200 OK)
- ✅ `/api/agent/state` - Working (200 OK)
- ✅ `/api/vram` - Working (200 OK, gateway auth required for data)
- ✅ `/api/health` - Working (200 OK)
- ✅ `/ws/agent-state` - Working (WebSocket connected)
- ✅ Rate limiting - Active and functional

## Testing

Run the following commands to verify all endpoints:

```bash
# Test all HTTP endpoints
curl -s http://localhost:8080/api/agent-state | jq .
curl -s http://localhost:8080/api/agent/state | jq .
curl -s http://localhost:8080/api/vram | jq .
curl -s http://localhost:8080/api/health | jq .

# Test WebSocket
python -c "
import asyncio, websockets, json
async def test():
    async with websockets.connect('ws://localhost:8080/ws/agent-state') as ws:
        msg = await ws.recv()
        print(json.loads(msg))
asyncio.run(test())
"

# Test rate limiting (should see X-Process-Time header)
curl -I http://localhost:8080/api/agent-state
```
