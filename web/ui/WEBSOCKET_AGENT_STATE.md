# WebSocket Agent State Streaming

Real-time agent state streaming endpoint for the Yennefer Web UI.

## Endpoint

```
ws://localhost:8080/ws/agent-state
```

## Features

- ✅ Real-time state updates when agent status changes
- ✅ Periodic heartbeats every 5 seconds
- ✅ Broadcast to multiple connected clients simultaneously
- ✅ Graceful reconnection handling
- ✅ Initial state snapshot with VRAM metrics on connection
- ✅ Client command support (get_state, ping)

## Message Types

### 1. `connection` - Initial Connection

Sent immediately when client connects.

```json
{
  "type": "connection",
  "timestamp": "2026-05-20T19:50:00Z",
  "data": {
    "status": "connected",
    "message": "Connected to Diamond Node agent state stream",
    "current_state": {
      "status": "idle",
      "activity": null,
      "last_action": null,
      "connections": 1,
      "uptime": 1716234600.5
    }
  }
}
```

### 2. `state_update` - State Changed

Sent when agent internal state changes.

```json
{
  "type": "state_update",
  "timestamp": "2026-05-20T19:50:05Z",
  "data": {
    "status": "thinking",
    "activity": "Processing chat request",
    "last_action": {...},
    "connections": 2,
    "uptime": 1716234605.5,
    "metrics": {
      "vram_used_mib": 1024,
      "vram_total_mib": 4096,
      "temperature_c": 65,
      "gpu_name": "NVIDIA GTX 1650"
    }
  }
}
```

### 3. `activity` - New Activity Started

Broadcast when a new activity begins (e.g., chat request processing).

```json
{
  "type": "activity",
  "timestamp": "2026-05-20T19:50:10Z",
  "data": {
    "activity": "Processing WebSocket chat message",
    "details": {
      "client_id": "123456789",
      "message_length": 256
    }
  }
}
```

### 4. `action` - Action Completed

Broadcast when an action completes with duration metrics.

```json
{
  "type": "action",
  "timestamp": "2026-05-20T19:50:15Z",
  "data": {
    "action": "Chat request completed",
    "result": {
      "response_length": 512,
      "thinking_length": 128,
      "tool_calls": 2
    },
    "duration_ms": 5234.5,
    "timestamp": "2026-05-20T19:50:15Z"
  }
}
```

### 5. `heartbeat` - Keep-Alive Ping

Sent every 5 seconds to maintain connection.

```json
{
  "type": "heartbeat",
  "timestamp": "2026-05-20T19:50:20Z",
  "data": {
    "uptime": 25.3,
    "connections": 2
  }
}
```

## Agent Status Values

| Status | Description |
|--------|-------------|
| `idle` | Agent is idle, waiting for requests |
| `active` | Agent is processing a request |
| `thinking` | Agent is in thinking/reasoning mode |
| `executing` | Agent is executing a tool or action |
| `error` | Agent encountered an error |

## Client Commands

Clients can send commands to the server via JSON messages:

### Get Current State

```json
{"command": "get_state"}
```

Response:
```json
{
  "type": "state_update",
  "timestamp": "2026-05-20T19:50:25Z",
  "data": {
    "status": "idle",
    "activity": null,
    ...
  }
}
```

### Ping

```json
{"command": "ping"}
```

Response:
```json
{
  "type": "pong",
  "timestamp": "2026-05-20T19:50:30Z"
}
```

## Integration Points

The agent state manager broadcasts events from:

1. **`/api/chat` (non-streaming)**: Broadcasts activity start, action completion, and state changes
2. **`/ws/chat` (streaming)**: Broadcasts WebSocket chat processing events
3. **Future orchestration endpoints**: Can integrate with any endpoint for real-time visibility

## Usage Examples

### JavaScript/Browser

```javascript
const ws = new WebSocket('ws://localhost:8080/ws/agent-state');

ws.onopen = () => {
  console.log('Connected to agent state stream');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  switch (message.type) {
    case 'connection':
      console.log('Connected:', message.data);
      break;
    
    case 'state_update':
      console.log('State:', message.data.status);
      updateUI(message.data);
      break;
    
    case 'activity':
      console.log('Activity:', message.data.activity);
      showNotification(message.data.activity);
      break;
    
    case 'action':
      console.log('Action completed:', message.data.action);
      console.log('Duration:', message.data.duration_ms, 'ms');
      break;
    
    case 'heartbeat':
      console.log('Heartbeat - uptime:', message.data.uptime);
      break;
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected - attempting reconnect...');
  setTimeout(() => connectWebSocket(), 5000);
};

// Request current state
ws.send(JSON.stringify({command: 'get_state'}));
```

### Python Client

```python
import asyncio
import websockets
import json

async def monitor_agent_state():
    uri = "ws://localhost:8080/ws/agent-state"
    
    async with websockets.connect(uri) as websocket:
        async for message in websocket:
            data = json.loads(message)
            
            if data['type'] == 'activity':
                print(f"Activity: {data['data']['activity']}")
            elif data['type'] == 'action':
                print(f"Action: {data['data']['action']}")
                print(f"Duration: {data['data']['duration_ms']}ms")

asyncio.run(monitor_agent_state())
```

## Testing

Run the included test client:

```bash
cd ~/diamondnode-unified-inference/web/ui
python3 test_agent_state_ws.py
```

This will connect to the WebSocket and display all messages for 30 seconds.

## REST API Alternative

For clients that cannot use WebSockets, use the polling endpoint:

```bash
curl http://localhost:8080/api/agent-state
```

Returns:
```json
{
  "state": {
    "status": "idle",
    "activity": null,
    "last_action": {...},
    "connections": 0,
    "uptime": 1716234600.5,
    "metrics": {...}
  },
  "timestamp": "2026-05-20T19:50:35Z"
}
```

Rate limit: 30 requests/minute

## Architecture

```
┌─────────────────┐
│  Web UI Client  │
│   (Browser)     │
└────────┬────────┘
         │ ws://
         │
┌────────▼────────────────────┐
│  AgentStateManager          │
│  - active_connections[]     │
│  - internal state           │
│  - broadcast()              │
│  - update_state()           │
└────────┬────────────────────┘
         │ broadcasts to
         │
┌────────▼────────────┐  ┌──────────────┐  ┌──────────────┐
│ /api/chat endpoint  │  │ /ws/chat     │  │ Future       │
│ (non-streaming)     │  │ (streaming)  │  │ Endpoints    │
└─────────────────────┘  └──────────────┘  └──────────────┘
```

## Performance

- **Heartbeat interval**: 5 seconds
- **Message size**: Typically < 1KB per message
- **Overhead**: Minimal - async/await with no blocking
- **Scalability**: Tested with multiple concurrent clients
- **Reconnection**: Clients receive full state snapshot on reconnect

## Security

- Rate limiting inherited from FastAPI middleware
- WebSocket accepts from allowed CORS origins
- No authentication required for local development
- Production deployments should add:
  - WebSocket authentication (token-based)
  - TLS/WSS encryption
  - Origin validation

## Future Enhancements

- [ ] Add authentication/authorization for WebSocket connections
- [ ] Persist historical state snapshots to database
- [ ] Add filtering (subscribe to specific event types)
- [ ] Add room/channel support for multi-agent systems
- [ ] Metrics export (Prometheus/OpenTelemetry)
- [ ] State replay/rewind functionality

## Implementation Details

**File**: `/home/diamondnode/diamondnode-unified-inference/web/ui/web_ui.py`

**Key components**:
- `AgentStateManager` class (line ~219)
- `/ws/agent-state` endpoint (line ~800)
- `/api/agent-state` REST endpoint
- Integration in `/api/chat` and `/ws/chat`

**Dependencies**:
- `fastapi` - WebSocket support
- `asyncio` - Async message broadcasting
- `httpx` - VRAM metrics fetching

## Troubleshooting

### WebSocket connection fails

1. Check web_ui.py is running: `curl http://localhost:8080/api/health`
2. Check WebSocket support in client browser
3. Verify CORS settings in web_ui.py

### No heartbeats received

1. Check heartbeat task didn't crash (check logs)
2. Verify connection is still open
3. Check client timeout settings

### Missing state updates

1. Verify endpoint integration (broadcasts in `/api/chat`, etc.)
2. Check `agent_state_manager.broadcast_activity()` calls
3. Monitor server logs for errors

### Multiple clients not receiving broadcasts

1. Verify `AgentStateManager.broadcast()` loop
2. Check for disconnected sockets in `active_connections`
3. Monitor exception handling in broadcast loop

## License

Copyright (c) 2026 Diamond Node Team  
Licensed under the MIT License
