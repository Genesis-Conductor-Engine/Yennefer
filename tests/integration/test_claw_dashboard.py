# Copyright (c) 2026 Diamond Node Team
# Licensed under the MIT License - see LICENSE file for details

"""
Integration and End-to-End Test Suite for Claw and Telegram Notification Integration
and the Real-Time Web Dashboard WebSocket and REST APIs.
"""

import os
import sys
import time
import asyncio
import pytest
import httpx
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

# Ensure project root is in python path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from web.ui.web_ui import app
from src.monitoring.claws import (
    propagate_to_claws,
    send_telegram_notification,
    send_kimiclaw_notification,
    send_openclaw_notification,
    send_slack_notification
)

# Test constants
MOCK_GATEWAY_URL = "http://127.0.0.1:8000"
MOCK_SECRET = "test_gateway_secret_123"

# Mock payloads representing states: Optimal (H < 5.0), Sequential (7.5 <= H < 8.5), and Critical/Offload (H >= 8.5)
PAYLOAD_OPTIMAL = {
    "vram_used_mib": 4000,
    "vram_total_mib": 10000,
    "temperature_c": 62,
    "power_watts": 80,
    "gpu_name": "NVIDIA GTX 1650"
}

PAYLOAD_SEQUENTIAL = {
    "vram_used_mib": 8000,
    "vram_total_mib": 10000,
    "temperature_c": 75,
    "power_watts": 110,
    "gpu_name": "NVIDIA GTX 1650"
}

PAYLOAD_CRITICAL = {
    "vram_used_mib": 9200,
    "vram_total_mib": 10000,
    "temperature_c": 82,
    "power_watts": 125,
    "gpu_name": "NVIDIA GTX 1650"
}


@pytest.fixture(autouse=True)
def configure_test_environment():
    """Configure environment variables and app state for accelerated testing."""
    # Set environment variables for testing
    os.environ["GATEWAY_URL"] = MOCK_GATEWAY_URL
    os.environ["GATEWAY_SECRET"] = MOCK_SECRET
    os.environ["CLAW_PERIODIC_INTERVAL"] = "0.1"  # Fast periodic alerts (0.1s)
    os.environ["METRICS_POLL_INTERVAL"] = "0.05"  # Fast websocket/gateway polling (0.05s)
    
    # Save original app state variables if they exist, and override them
    orig_poll = getattr(app.state, "gateway_poll_interval", None)
    orig_periodic = getattr(app.state, "periodic_notification_interval", None)
    
    app.state.gateway_poll_interval = 0.05
    app.state.periodic_notification_interval = 0.1
    
    # Disable rate limits in app state slowapi rate limiter if present
    original_limiter = getattr(app.state, "limiter", None)
    if original_limiter:
        original_limiter.enabled = False
        
    yield
    
    # Restore original settings
    if orig_poll is not None:
        app.state.gateway_poll_interval = orig_poll
    if orig_periodic is not None:
        app.state.periodic_notification_interval = orig_periodic
    if original_limiter:
        original_limiter.enabled = True
        
    # Cleanup environment variables
    os.environ.pop("GATEWAY_URL", None)
    os.environ.pop("GATEWAY_SECRET", None)
    os.environ.pop("CLAW_PERIODIC_INTERVAL", None)
    os.environ.pop("METRICS_POLL_INTERVAL", None)


@pytest.fixture
def mock_gateway():
    """Fixture to mock outgoing HTTP calls to the local Gateway."""
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        yield mock_get


@pytest.fixture
def mock_claws():
    """Fixture to mock high-level claws propagation function."""
    with patch("src.monitoring.claws.propagate_to_claws", new_callable=AsyncMock) as mock_prop:
        yield mock_prop


# =============================================================================
# 1. WebSocket Metrics Streaming Test Scenarios
# =============================================================================

def test_websocket_metrics_streaming(mock_gateway):
    """
    Test that /ws/live-metrics connects, polls the Gateway with Authorization headers,
    and streams metrics updates at configured intervals with correct payload schemas.
    """
    # Mock Gateway to return optimal metrics
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = PAYLOAD_OPTIMAL
    mock_gateway.return_value = mock_response

    client = TestClient(app)
    
    # Connect to websocket endpoint
    with client.websocket_connect("/ws/live-metrics") as websocket:
        # Assert initial connection message structure
        initial_msg = websocket.receive_json()
        assert initial_msg["type"] == "connection"
        
        # Wait for and receive first streamed update
        update_msg = websocket.receive_json()
        assert update_msg["type"] == "metrics_update"
        assert "timestamp" in update_msg
        
        # Verify metric calculations & schema mapping
        data = update_msg["data"]
        assert data["vram_used_mib"] == 4000
        assert data["vram_total_mib"] == 10000
        assert data["vram_percent"] == 40.0
        assert data["power_watts"] == 80
        assert data["temperature"] == 62
        assert data["hamiltonian"] == 4.0
        assert data["state"] == "OPTIMAL"
        
        # Modify gateway metrics to test sequential state transition
        mock_response.json.return_value = PAYLOAD_SEQUENTIAL
        
        update_msg2 = websocket.receive_json()
        data2 = update_msg2["data"]
        assert data2["vram_used_mib"] == 8000
        assert data2["hamiltonian"] == 8.0
        assert data2["state"] == "SEQUENTIAL"
        
        # Verify that the Gateway client request contained the correct Authorization header
        assert mock_gateway.call_count >= 1
        called_args, called_kwargs = mock_gateway.call_args
        headers = called_kwargs.get("headers", {})
        assert headers.get("Authorization") == f"Bearer {MOCK_SECRET}"


def test_websocket_metrics_streaming_degraded(mock_gateway):
    """
    Test that /ws/live-metrics handles gateway connection failure or errors gracefully
    without dropping the connection, sending a "degraded" state update instead.
    """
    # Simulate an HTTP error or connection failure
    mock_gateway.side_effect = httpx.ConnectError("Connection refused to Gateway")

    client = TestClient(app)
    
    with client.websocket_connect("/ws/live-metrics") as websocket:
        initial_msg = websocket.receive_json()
        assert initial_msg["type"] == "connection"
        
        # Receive update
        update_msg = websocket.receive_json()
        assert update_msg["type"] == "metrics_update"
        assert update_msg["data"]["state"] == "DEGRADED"
        assert "error" in update_msg["data"]


# =============================================================================
# 2. REST API /api/propagate Test Scenarios
# =============================================================================

def test_rest_api_propagate(mock_claws):
    """
    Test manual notification endpoint POST /api/propagate.
    Verifies that payloads are successfully accepted and routed to all claws.
    """
    mock_claws.return_value = ["telegram", "kimiclaw", "openclaw", "slack"]
    
    client = TestClient(app)
    payload = {
        "message": "Manual trigger metrics summary",
        "metrics": {
            "vram_used_mib": 6000,
            "vram_total_mib": 10000,
            "hamiltonian": 6.0,
            "state": "DYNAMIC"
        }
    }
    
    response = client.post("/api/propagate", json=payload)
    
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "success"
    assert sorted(res_data["delivered"]) == sorted(["telegram", "kimiclaw", "openclaw", "slack"])
    
    # Assert mock_claws was invoked with formatted message and metrics
    mock_claws.assert_called_once_with(
        message="Manual trigger metrics summary",
        metrics={
            "vram_used_mib": 6000,
            "vram_total_mib": 10000,
            "hamiltonian": 6.0,
            "state": "DYNAMIC"
        }
    )


def test_rest_api_propagate_validation_error():
    """
    Test that POST /api/propagate returns 422 Unprocessable Entity
    or 400 Bad Request when receiving malformed JSON payload.
    """
    client = TestClient(app)
    # Missing required 'message' field
    payload = {
        "metrics": {
            "vram_used_mib": 6000,
            "vram_total_mib": 10000
        }
    }
    response = client.post("/api/propagate", json=payload)
    assert response.status_code in [400, 422]


# =============================================================================
# 3. Periodic Background Notifications Test Scenarios
# =============================================================================

async def test_periodic_notifications(mock_gateway, mock_claws):
    """
    Test that the background task loop periodically retrieves metrics from the
    Gateway and dispatches a periodic report to claws at the configured interval.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = PAYLOAD_OPTIMAL
    mock_gateway.return_value = mock_response
    
    mock_claws.return_value = ["telegram", "slack"]

    # Starting TestClient with block context runs startup lifespans/background tasks
    client = TestClient(app)
    with client:
        # Yield control to let the background scheduler execute at least one periodic cycle (interval=0.1s)
        await asyncio.sleep(0.25)
        
        # Verify Gateway was polled
        assert mock_gateway.call_count >= 1
        
        # Verify periodic reports were sent to claws
        assert mock_claws.call_count >= 1
        
        # Confirm that the periodic report text was generated
        args, kwargs = mock_claws.call_args
        assert any("periodic" in str(arg).lower() for arg in args)


# =============================================================================
# 4. Threshold-based Notification Triggers (H > 8.5) Test Scenarios
# =============================================================================

async def test_threshold_based_triggers(mock_gateway, mock_claws):
    """
    Test that resource Hamiltonian H crossing the threshold H > 8.5 triggers
    instant dispatch to claws, and checks state-based suppression (hysteresis) to prevent flooding.
    """
    # Setup a sequence of gateway responses to simulate transition phases:
    # 1. Normal state (H = 4.0) -> No alert
    # 2. Critical state (H = 9.2) -> Instant alert triggered
    # 3. Critical state (H = 9.2) -> Suppressed (no duplicate notification)
    # 4. Recover to Normal state (H = 4.0) -> Reset state
    # 5. Critical state (H = 9.2) -> Instant alert triggered again
    responses = [
        httpx.Response(200, json=PAYLOAD_OPTIMAL),   # H = 4.0 (Normal)
        httpx.Response(200, json=PAYLOAD_CRITICAL),  # H = 9.2 (Threshold Crossed -> ALERT 1)
        httpx.Response(200, json=PAYLOAD_CRITICAL),  # H = 9.2 (Suppressed due to hysteresis)
        httpx.Response(200, json=PAYLOAD_OPTIMAL),   # H = 4.0 (Reset)
        httpx.Response(200, json=PAYLOAD_CRITICAL)   # H = 9.2 (Threshold Crossed again -> ALERT 2)
    ]
    
    call_idx = 0
    async def sequential_get(*args, **kwargs):
        nonlocal call_idx
        res = responses[min(call_idx, len(responses) - 1)]
        call_idx += 1
        return res
        
    mock_gateway.side_effect = sequential_get
    mock_claws.return_value = ["telegram", "kimiclaw", "openclaw"]
    
    client = TestClient(app)
    with client:
        # Give enough time for the background polling task (0.05s interval) to cycle through the states
        await asyncio.sleep(0.35)
        
        # Verify that propagate_to_claws was called exactly twice (for steps 2 and 5)
        # and suppressed on step 3.
        # Periodic alerts might add calls, so we inspect call args to filter for 'critical' / 'threshold' / 'offload' alerts
        critical_calls = []
        for call in mock_claws.call_args_list:
            args, kwargs = call
            message = args[0] if len(args) > 0 else kwargs.get("message", "")
            if "critical" in message.lower() or "offload" in message.lower():
                critical_calls.append(call)
                
        assert len(critical_calls) == 2, f"Expected exactly 2 critical notifications, got {len(critical_calls)}"
        
        # Check that details of the first critical alert contain correct info
        first_call_args = critical_calls[0][0]
        assert "9.2" in first_call_args[0]
        assert "critical" in first_call_args[0].lower()
