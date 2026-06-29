# Project: Real-time Web Dashboard and Claw/Telegram Integration

## Architecture
The real-time dashboard and claws/Telegram integration is built on top of the `diamondnode-unified-inference` service:
- **Frontend UI (`web/static/`)**: A responsive UI utilizing HTML5, CSS, and JS (with interactive charts and connectivity states) displaying live metrics, Ising Hamiltonian status, and triggering manual claw propagation.
- **FastAPI Backend (`web/ui/web_ui.py`)**:
  - WebSocket endpoint `/ws/metrics` or similar to poll Diamond Gateway (`/metrics` or `/v1/orchestrate`) and stream metrics every 2 seconds.
  - REST endpoint `/api/propagate` to handle outward manual notifications.
  - Background scheduler (or async loop) to manage periodic (5-minute interval) and threshold-based (`H > 8.5`) notifications.
- **Claw Integration Module (`src/monitoring/claws.py` or within `web_ui.py`)**:
  - Logic to format and send payloads to KimiClaw, OpenClaw, Telegram, and Slack endpoints.
- **Test Infrastructure (`tests/integration/test_claw_dashboard.py`)**:
  - Comprehensive tests validating WebSockets, REST APIs, and automated/manual triggers.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | E2E Testing Framework | Create `tests/integration/test_claw_dashboard.py` and `TEST_INFRA.md`, publish `TEST_READY.md` | None | DONE |
| 2 | Real-time Dashboard UI & WebSocket | Implement WebSocket metrics poll/stream, build frontend UI with charts | M1 | DONE |
| 3 | Claw & Telegram Integration | Implement REST `/api/propagate`, background periodic/threshold triggers (`H > 8.5`), notification clients | M2 | DONE |
| 4 | Verification & Adversarial Hardening | Run all E2E tests, execute adversarial testing (Tier 5), perform Forensic Audit | M3 | DONE |

## Interface Contracts
### WebSocket Endpoint `/ws/live-metrics`
- **Output (every 2 seconds)**:
  ```json
  {
    "type": "metrics_update",
    "timestamp": "2026-06-09T14:55:09Z",
    "data": {
      "vram_used_mib": 9200,
      "vram_total_mib": 10000,
      "vram_percent": 92.0,
      "power_watts": 120,
      "temperature": 75,
      "hamiltonian": 9.2,
      "state": "OFFLOAD"
    }
  }
  ```

### REST Endpoint `POST /api/propagate`
- **Request Body**:
  ```json
  {
    "message": "Manual trigger metrics summary",
    "metrics": { ... }
  }
  ```
- **Response**:
  ```json
  {
    "status": "success",
    "delivered": ["telegram", "kimiclaw", "openclaw"]
  }
  ```

### Outward Claw Notification Structure
- **Telegram (Diamondnodebot)**, **KimiClaw**, **OpenClaw**, **Slack**:
  - Post payload contains a structured markdown or JSON summary of VRAM metrics, Hamiltonian, and severity state.

## Code Layout
- `web/ui/web_ui.py`: FastAPI routes, WebSocket handlers, and background loops.
- `web/static/`: Dashboard HTML, JS scripts, CSS styles.
- `src/monitoring/claws.py`: External notification dispatchers.
- `tests/integration/test_claw_dashboard.py`: Integration and end-to-end tests.
