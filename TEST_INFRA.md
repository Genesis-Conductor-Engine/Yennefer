# Test Infrastructure: Real-time Web Dashboard & Claw Integration

This document outlines the testing strategy, architecture, and environment configuration for validating the real-time web dashboard and external Claw notification channels (Telegram, Slack, KimiClaw, OpenClaw) in the `diamondnode-unified-inference` service.

## Architecture

The testing framework is designed for end-to-end (E2E) and integration coverage of real-time messaging, HTTP REST endpoints, and background worker threads under local network isolation constraints (`CODE_ONLY` network mode).

```
 ┌─────────────────────────────────────────────────────────────┐
 │                      Integration Tests                      │
 │             (tests/integration/test_claw_dashboard.py)       │
 └───────────────┬─────────────────────────────┬───────────────┘
                 │                             │
                 ▼ (FastAPI TestClient)        ▼ (Python patch/mock)
 ┌──────────────────────────────────────┐    ┌─────────────────┐
 │            FastAPI App               │    │   Claws Stubs   │
 │         (web/ui/web_ui.py)           │    │ (src/monitoring/│
 └──────┬────────────────────────┬──────┘    │    claws.py)    │
        │                        │           └─────────────────┘
        ▼ (/ws/live-metrics)     ▼ (POST /api/propagate)
 ┌──────────────────────┐    ┌──────────────────────┐
 │ WebSocket Streaming  │    │  REST API Ingress    │
 └──────────────────────┘    └──────────────────────┘
```

## Mocking & Simulation Strategy

To ensure reproducible, zero-dependency, and deterministic test execution:
1. **Diamond Gateway Mocking**: Intercepts `httpx.AsyncClient.get` calls made by the backend, redirecting requests to in-memory state objects that simulate VRAM utilization transitions:
   - Optimal utilization ($H < 5.0$).
   - Sequential utilization ($7.5 \le H < 8.5$).
   - Critical Offload utilization ($H \ge 8.5$).
2. **Claws Dispatch Mocking**: Mocks high-level functions in `src.monitoring.claws` (e.g. `propagate_to_claws`, `trigger_notion_offload`) using `unittest.mock.patch` with `AsyncMock`. This asserts parameters, formats, and message content without attempting real outbound network calls.
3. **Graceful Degradation Simulation**: Simulates `httpx.ConnectError` to verify that the WebSocket endpoints stream a `DEGRADED` status report rather than crashing the client connection.

## Configuration & Time Acceleration

Standard intervals (2-second polling, 5-minute periodic checks) are overridden at runtime via test fixtures to prevent testing lags and pipeline timeouts:
- **`app.state.gateway_poll_interval`** / **`METRICS_POLL_INTERVAL`**: Overridden to `0.05` seconds.
- **`app.state.periodic_notification_interval`** / **`CLAW_PERIODIC_INTERVAL`**: Overridden to `0.1` seconds.
- **SlowAPI Rate Limiting**: Disabled (`app.state.limiter.enabled = False`) during the test run to prevent `429 Too Many Requests` response errors when repeating calls rapidly.

## Execution and CI/CD

To run the integration tests locally or within the CI/CD pipeline, execute:

```bash
# Activate environmental properties
source ~/load-env.sh

# Run pytest using the designated Python environment
/home/diamondnode/diamondnode-unified-inference/yennefer_venv/bin/pytest tests/integration/test_claw_dashboard.py -v
```

### Invalidation Conditions
The test suite will fail or be invalidated if:
1. Active internet access is attempted during testing, violating network containment.
2. The asynchronous event loop is not properly awaited inside the lifespans context manager.
3. Overridden intervals do not restore their initial state after test completion.
