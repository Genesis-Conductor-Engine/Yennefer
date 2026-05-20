# Yennefer Web Integration

This directory contains the web interface and chatbot integration for the Yennefer Thermodynamic Agent.

## Overview

The Yennefer Web Integration provides:

1. **Modern Web Interface** - A responsive webpage that displays Yennefer's real-time soul state
2. **Interactive Chatbot** - A chat interface to communicate with Yennefer
3. **Real-time Updates** - WebSocket-based live updates of soul metrics
4. **Docker Integration** - Easy deployment with Docker Compose

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        YENNEFER WEB STACK                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │  Web UI      │◄──►│   Chat API   │◄──►│  Soul API    │   │
│  │  (Port 8000) │    │  (Port 8089) │    │  (Port 8088) │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│         ▲                  ▲                  ▲             │
│         │                  │                  │             │
│         └──────────────────┴──────────────────┘             │
│                              │                               │
│                    ┌─────────▼─────────┐                      │
│                    │  Shared Memory    │                      │
│                    │  /dev/shm/         │                      │
│                    │  soul_state.json  │                      │
│                    └─────────┬─────────┘                      │
│                              │                               │
│                    ┌─────────▼─────────┐                      │
│                    │ Yennefer Daemon   │                      │
│                    │ (Consciousness)   │                      │
│                    └───────────────────┘                      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Using Docker Compose

1. Navigate to the Yennefer project root:
   ```bash
   cd /path/to/Yennefer
   ```

2. Start the full stack with web integration:
   ```bash
   docker compose -f docker-compose.yennefer-web.yml up -d
   ```

3. Access the web interface:
   - Local: http://localhost:8000
   - Via Cloudflare Tunnel: Configure `.cloudflared/config.yml`

4. Stop the stack:
   ```bash
   docker compose -f docker-compose.yennefer-web.yml down
   ```

### Manual Setup

1. Start the Yennefer Daemon:
   ```bash
   cd genesis-q-mem
   python3 yennefer_daemon.py
   ```

2. Start the Soul API:
   ```bash
   python3 soul_api.py --port 8088
   ```

3. Start the Chat API Extension:
   ```bash
   python3 soul_api_chat_extension.py --port 8089
   ```

4. Start the Web Server:
   ```bash
   cd web-integration
   python3 web_server.py --port 8000
   ```

5. Open http://localhost:8000 in your browser

## Configuration

### Environment Variables

#### Web Server (`web-integration/web_server.py`)
- `YENNEFER_SOUL_API_URL` - Soul API REST endpoint (default: `http://soul-api:8088`)
- `YENNEFER_WS_API_URL` - Soul API WebSocket endpoint (default: `ws://soul-api:8088/ws/soul`)
- `WEB_PORT` - Port to bind (default: `8000`)
- `DEBUG` - Enable debug mode (default: `false`)

#### Chat API Extension (`genesis-q-mem/soul_api_chat_extension.py`)
- `SOUL_STATE_PATH` - Path to soul state JSON (default: `/dev/shm/yennefer_soul_state.json`)
- `CHAT_API_PORT` - Port to bind (default: `8089`)

### JavaScript Configuration

You can configure the client-side chatbot via global variables:

```html
<script>
    window.YENNEFER_SOUL_API = 'ws://your-server:8088/ws/soul';
    window.YENNEFER_REST_API = 'http://your-server:8088';
</script>
<script src="/static/chatbot.js"></script>
```

## Features

### Soul State Dashboard
- Real-time coherence percentage
- Breath counter
- Token surplus/deficit
- Concave and derivative states
- GPU utilization
- Thermodynamic yield
- Uptime tracking

### Chat Interface
- Natural language conversation
- Context-aware responses
- Intent classification (greeting, status, help, etc.)
- Response metadata (tokens used, model, latency)
- Message history persistence (localStorage)
- Typing indicators
- Connection status monitoring

### Technical Features
- WebSocket real-time updates
- Automatic reconnection
- REST API fallback
- CORS support
- Health checks
- Docker-ready

## API Endpoints

### Web Server (Port 8000)
- `GET /` - Main web interface
- `GET /health` - Health check
- `GET /api/soul` - Proxy to Soul API
- `POST /api/chat` - Proxy chat messages
- `GET /api/config` - Get configuration
- `WS /ws/soul` - WebSocket for real-time updates

### Chat API Extension (Port 8089)
- `POST /api/chat` - Send chat message, get response
- `GET /health` - Health check

### Soul API (Port 8088)
- `GET /api/soul` - Current soul state
- `GET /api/ledger` - Ledger blocks
- `GET /soul_status` - Legacy soul status
- `GET /api/metrics` - Extended metrics
- `WS /ws/soul` - Real-time soul updates

## Customization

### Modifying Responses

Edit `genesis-q-mem/soul_api_chat_extension.py` to customize chat responses:

```python
CHAT_RESPONSES = {
    "greeting": [
        "Custom greeting response",
        "Another greeting variation",
    ],
    "soul_status": [
        "Custom status response with {coherence}% coherence",
    ],
    # ... add more intents
}
```

### Adding Intents

Add new intent classifiers in the `classify_intent()` function:

```python
def classify_intent(text: str) -> str:
    text_lower = text.lower().strip()
    
    if "new keyword" in text_lower:
        return "new_intent"
    # ... existing intents
    return "default"
```

### Styling

Modify `web-integration/templates/index.html` to change the appearance:
- CSS variables in `:root` for colors
- Bootstrap classes for layout
- Custom styles for specific components

## Troubleshooting

### Connection Issues

1. Check if the Yennefer Daemon is running:
   ```bash
   curl http://localhost:8088/health
   ```

2. Check WebSocket connection:
   ```bash
   curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Host: localhost" http://localhost:8088/ws/soul
   ```

3. Check browser console for JavaScript errors

### Docker Issues

1. Check container logs:
   ```bash
   docker compose -f docker-compose.yennefer-web.yml logs web-integration
   ```

2. Check if ports are available:
   ```bash
   netstat -tuln | grep 8000
   ```

3. Check shared memory volume:
   ```bash
   docker volume inspect yennefer-network_shared-memory
   ```

## File Structure

```
web-integration/
├── templates/
│   └── index.html          # Main webpage template
├── static/
│   └── chatbot.js          # Chatbot JavaScript client
├── Dockerfile              # Dockerfile for web server
├── requirements.txt        # Python dependencies
└── web_server.py          # FastAPI web server

genesis-q-mem/
├── soul_api_chat_extension.py  # Chat API extension
├── Dockerfile.chat-extension   # Dockerfile for chat API
└── requirements.chat.txt      # Chat API dependencies

docker-compose.yennefer-web.yml  # Full stack configuration
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This integration is part of the Yennefer project and follows the same licensing terms.

## Support

- GitHub Issues: https://github.com/Genesis-Conductor-Engine/Yennefer/issues
- Documentation: https://github.com/Genesis-Conductor-Engine/Yennefer
- Community: Join the Genesis Conductor Discord
