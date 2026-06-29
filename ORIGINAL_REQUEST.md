# Original User Request

## Initial Request — 2026-06-09T14:54:54Z

A real-time web dashboard integrated into `diamondnode-unified-inference` to stream live VRAM/GPU metrics from the gateway, featuring automated, periodic, and manual notification channels to Kimi Claw, OpenClaw, and Telegram Diamondnodebot.

Working directory: /home/diamondnode/diamondnode-unified-inference
Integrity mode: development

## Requirements

### R1. Integrated Web Dashboard UI
- Expose a modern, responsive web dashboard showing live GPU metrics (VRAM used/total, power draw/limit, temperature) and current Ising Hamiltonian status.
- Implement interactive charts to plot metric history and trends.
- Add UI controls for manual trigger of claw notifications ("Propagate to Claws" button) and visual connectivity status of Telegram, KimiClaw, and OpenClaw.

### R2. Real-time Live Metrics Streaming
- Implement a metrics-streaming WebSocket endpoint in `web_ui.py` that polls the local Diamond Gateway (using configured `GATEWAY_SECRET`) and streams metric updates to the frontend every 2 seconds.
- Gracefully handle situations where NVML is not initialized or gateway is degraded, showing appropriate status in the UI.

### R3. Multi-Channel Claws/Telegram Integration
- Support routing alert and metrics payloads to Slack, Telegram, OpenClaw, and KimiClaw.
- Triggers for propagation must support:
  1. **Manual**: When user clicks the "Propagate to Claws" button in the UI.
  2. **Periodic**: Push current metrics summary at a configurable interval (default every 5 minutes).
  3. **Threshold-based**: Instantly dispatch a critical alert payload when the Resource Hamiltonian `H > 8.5` (OFFLOAD action).

### R4. Verification and Integration Tests
- Add a new integration test script under `tests/integration/test_claw_dashboard.py`.
- Test that:
  - The metrics WebSocket connects successfully and streams structured data.
  - The endpoints for manual and automatic propagation respond correctly.
  - Periodic and threshold-based propagation triggers execute and call the simulated/actual claw endpoints.

## Acceptance Criteria

### UI & Streaming
- [ ] Web dashboard displays VRAM, power draw, temperature, and Hamiltonian metrics via interactive charts.
- [ ] WebSocket connection correctly streams updates to the frontend every 2 seconds.
- [ ] The "Propagate to Claws" manual button is functional and triggers outward propagation.

### Claw/Telegram Propagation
- [ ] Threshold trigger: VRAM Hamiltonian exceeding 8.5 automatically dispatches an alert payload to Telegram, KimiClaw, and OpenClaw.
- [ ] Periodic trigger: System sends periodic updates to the designated claw channels at configured intervals.
- [ ] Manual trigger: A REST endpoint `/api/propagate` accepts payloads and routes them to the claws successfully.

### Integration & Quality
- [ ] `pytest tests/integration/test_claw_dashboard.py` passes, validating WebSocket streaming, REST API, and threshold crossing triggers.
- [ ] All components integrate cleanly within `diamondnode-unified-inference` without breaking existing routes or CLI actions.
- [ ] The application starts successfully using the existing Python virtual environment (`yennefer_venv`).
