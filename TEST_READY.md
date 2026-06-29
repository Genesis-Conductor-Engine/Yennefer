# Test Readiness Attestation (Milestone 1)

This document certifies that the End-to-End (E2E) and integration testing framework for the real-time web dashboard and Claw/Telegram propagation channels in `diamondnode-unified-inference` has been fully implemented and is ready for feature development.

## Feature Checklist

| Feature Target | Test Scenario | Status | Expected Pass / Fail |
|---|---|---|---|
| **WebSocket live-metrics** | Connection & schema validation | `READY` | Fails (404 / Connection Error) |
| **WebSocket live-metrics** | Degraded gateway state handling | `READY` | Fails (404 / Connection Error) |
| **REST POST /api/propagate** | Manual alert delivery routing | `READY` | Fails (404) |
| **REST POST /api/propagate** | Payload schema & validation error | `READY` | Fails (404) |
| **Background Scheduler** | Periodic metrics push (5-min interval) | `READY` | Fails (AssertionError) |
| **Background Scheduler** | Threshold-based offload ($H > 8.5$) | `READY` | Fails (AssertionError) |

> **Note**: As this is Milestone 1 (E2E Testing Framework Setup), the tests are written against the interface contracts. They are expected to fail with **404 / Connection Errors / AssertionError** until the underlying business logic and routes are implemented in Milestones 2 and 3.

## Coverage Summary

- **Test Suite Path**: `tests/integration/test_claw_dashboard.py`
- **Integration Points**:
  - `web/ui/web_ui.py` (FastAPI app routing and state management)
  - `src/monitoring/claws.py` (High-level communication dispatcher)
- **Target Coverage Metrics**:
  - WebSocket Streaming Branch: 100% path coverage.
  - REST API Ingress Branch: Validation error handling & standard success path.
  - Background Task Loop: Time acceleration-based polling intervals (0.05s/0.1s) and hysteresis alert-suppression validation.

## Test Verification Output

The test suite was run under the `yennefer_venv` Python virtual environment. As expected, all 6 test scenarios failed cleanly with route resolution / assertion errors without throwing any syntax or import errors.

```
=========================== short test summary info ============================
FAILED tests/integration/test_claw_dashboard.py::test_websocket_metrics_streaming
FAILED tests/integration/test_claw_dashboard.py::test_websocket_metrics_streaming_degraded
FAILED tests/integration/test_claw_dashboard.py::test_rest_api_propagate
FAILED tests/integration/test_claw_dashboard.py::test_rest_api_propagate_validation_error
FAILED tests/integration/test_claw_dashboard.py::test_periodic_notifications
FAILED tests/integration/test_claw_dashboard.py::test_threshold_based_triggers
======================== 6 failed, 7 warnings in 2.68s =========================
```
