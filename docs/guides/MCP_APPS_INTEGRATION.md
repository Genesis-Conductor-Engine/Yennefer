# MCP Apps Integration - Diamond Node

## Overview

**MCP Apps** (Model Context Protocol Apps) brings interactive UI capabilities to the Diamond Node unified inference system. Instead of plain text responses, users now get rich, interactive interfaces for YOLO11 detection, VRAM monitoring, CUDA-Q optimization, and blockchain analytics.

## Installation Complete ✅

```bash
npm install -g @modelcontextprotocol/ext-apps  # v1.7.1 installed
```

## Configuration

### Files Created

| File | Purpose |
|------|---------|
| `mcp_yolo_app.json` | MCP Apps configuration with 4 interactive tools |
| `mcp_yolo_server.py` | FastAPI MCP server with apps support |
| `MCP_APPS_INTEGRATION.md` | This documentation |

### Interactive Apps Configured

#### 1. YOLO11 Object Detection 🎯
**UI Type:** Interactive Canvas with Bounding Box Overlay

**Features:**
- Upload image or paste URL
- Real-time object detection
- Interactive bounding boxes with labels
- Confidence threshold slider
- Class filtering
- Zoom and pan
- Export results (JSON/CSV)

**Input:**
```json
{
  "image_path": "/path/to/image.jpg",
  "confidence_threshold": 0.5,
  "batch_size": 1
}
```

**Output:**
```json
{
  "detections": [
    {
      "class": "person",
      "confidence": 0.92,
      "bbox": [100, 150, 300, 450]
    }
  ],
  "inference_time_ms": 47,
  "vram_used_mb": 1200
}
```

#### 2. VRAM Monitor 📊
**UI Type:** Real-time Circular Gauge Dashboard

**Features:**
- Live VRAM usage percentage
- Hamiltonian value display
- Color-coded states (OPTIMAL/DYNAMIC/SEQUENTIAL/OFFLOAD)
- GPU temperature and power
- Auto-refresh every 5 seconds
- Historical trend chart

**Thresholds:**
- H < 5.0: 🟢 OPTIMAL (green)
- H 5.0-7.5: 🟡 DYNAMIC (yellow)
- H 7.5-8.5: 🟠 SEQUENTIAL (orange)
- H > 8.5: 🔴 OFFLOAD (red)

#### 3. CUDA-Q QAOA Optimizer 📈
**UI Type:** Interactive Line Chart

**Features:**
- Energy convergence visualization
- Iteration-by-iteration tracking
- Best energy marker
- Purity and effective dimension metrics
- Zoom and tooltip
- Export PNG
- Convergence detection

**Output:**
```json
{
  "energy_history": [45.2, 38.7, 32.1, 29.3],
  "best_energy": 29.3,
  "purity": 0.91,
  "effective_dimension": 30,
  "convergence_iteration": 4,
  "execution_time_ms": 165
}
```

#### 4. Blockchain Portfolio Risk 💰
**UI Type:** Multi-Chart Dashboard

**Features:**
- Balance timeline (area chart)
- Risk metrics radar (volatility, Sharpe, drawdown, VaR)
- Wallet address validation
- Historical block selection
- Real-time on-chain data
- Export portfolio report

**Output:**
```json
{
  "volatility": 0.224,
  "sharpe_ratio": -0.229,
  "max_drawdown": 0.35,
  "var_95": 0.18,
  "balance_history": [...]
}
```

---

## Usage

### 1. Start MCP Apps Server

```bash
cd ~/unified_inference
source ~/xinference_venv/bin/activate
python mcp_yolo_server.py
```

Server starts on: **http://localhost:8081**

### 2. Access Apps

**Web Browser:**
http://localhost:8081/

**MCP Client Configuration:**
```json
{
  "mcpServers": {
    "diamond-node-apps": {
      "command": "python",
      "args": ["~/unified_inference/mcp_yolo_server.py"],
      "env": {}
    }
  }
}
```

**HTTP Transport:**
```bash
# List available apps
curl -X POST http://localhost:8081/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"apps/list"}'

# Call YOLO11 detection
curl -X POST http://localhost:8081/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "id":2,
    "method":"tools/call",
    "params":{
      "name":"run_yolo11_detection",
      "arguments":{
        "image_path":"/tmp/test.jpg",
        "confidence_threshold":0.5
      }
    }
  }'
```

### 3. Integrate with Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "diamond-node-apps": {
      "url": "http://localhost:8081/mcp",
      "transport": "http"
    }
  }
}
```

Then ask Claude:
- "Show me YOLO11 detection on this image"
- "Display the VRAM monitor"
- "Run CUDA-Q optimization and show the energy chart"
- "Analyze portfolio risk for 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User (Claude Desktop)                   │
└─────────────────────────────────────────────────────────────┘
                            ↓ MCP Protocol
┌─────────────────────────────────────────────────────────────┐
│              MCP Apps Server (port 8081)                    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  FastAPI + MCP JSON-RPC                               │  │
│  │  • initialize                                         │  │
│  │  • tools/list                                         │  │
│  │  • tools/call                                         │  │
│  │  • apps/list (NEW)                                    │  │
│  │  • apps/render (NEW)                                  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│           Claude Orchestrator (unified_inference)           │
│  • execute_tool()                                           │
│  • YOLO11, CUDA-Q, Blockchain, VRAM monitoring             │
└─────────────────────────────────────────────────────────────┘
```

---

## MCP Apps vs Traditional Web UI

| Aspect | Traditional Web UI | MCP Apps |
|--------|-------------------|----------|
| **Integration** | Separate service, manual API calls | Native in AI conversation |
| **Context** | Lost between requests | Full conversation context |
| **Interaction** | Click buttons, submit forms | Natural language + interactive UI |
| **Updates** | Manual refresh or WebSocket | Auto-refresh + streaming |
| **Deployment** | Nginx, domain, HTTPS | Local or HTTP endpoint |

**Example:**

**Traditional:**
1. User: "What's the VRAM status?"
2. AI: "The VRAM is at 65%. Would you like me to show the dashboard?"
3. User: "Yes"
4. AI: "Please visit http://localhost:8080/vram"
5. User opens browser, clicks dashboard

**MCP Apps:**
1. User: "What's the VRAM status?"
2. AI shows live VRAM gauge inline in chat ✨
3. User can interact with gauge directly (zoom, export, refresh)

---

## Supported MCP Clients

| Client | Apps Support | Status |
|--------|-------------|--------|
| Claude Desktop | ✅ Yes | Embedded UIs render inline |
| VSCode Copilot | ✅ Yes | Side panel rendering |
| Cursor | ✅ Yes | Inline components |
| Goose | ✅ Yes | Terminal UI fallback |
| Postman | ✅ Yes | API testing with preview |
| MCPJam | ✅ Yes | Full playground support |

---

## Development

### Add New App

1. Edit `mcp_yolo_app.json`:

```json
{
  "name": "my_new_tool",
  "display_name": "My Tool",
  "description": "My interactive tool",
  "ui_type": "chart",
  "output_schema": {...},
  "ui_component": {
    "type": "bar-chart",
    "renderer": "recharts"
  }
}
```

2. Implement tool in `claude_orchestrator.py`:

```python
async def execute_tool(self, tool_name, tool_input):
    if tool_name == "my_new_tool":
        result = await my_tool_implementation()
        return result
```

3. Restart MCP server

### UI Component Types

| Type | Renderer | Use Case |
|------|----------|----------|
| `canvas` | `bounding-box-overlay` | Object detection, segmentation |
| `gauge` | `circular-progress` | Metrics, percentages, thresholds |
| `line-chart` | `recharts` | Time series, convergence |
| `area-chart` | `recharts` | Historical data, trends |
| `bar-chart` | `recharts` | Comparisons, categories |
| `radar-chart` | `recharts` | Multi-dimensional metrics |
| `dashboard` | `grid` | Multiple widgets |
| `table` | `data-grid` | Structured data, sorting, filtering |
| `form` | `json-schema-form` | User input, configuration |

---

## Testing

### Test MCP Protocol

```bash
# Initialize
curl -X POST http://localhost:8081/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'

# List apps
curl -X POST http://localhost:8081/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"apps/list"}'

# Render VRAM monitor
curl -X POST http://localhost:8081/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "id":3,
    "method":"apps/render",
    "params":{"name":"query_vram_status","data":{}}
  }'
```

### Test with Claude

```bash
# Add server to Claude config, then ask:
"Show me the YOLO11 detection interface"
"Display the VRAM monitor gauge"
"Run QAOA and show the energy convergence chart"
```

---

## Monitoring

MCP Apps server integrates with existing monitoring:

**LangSmith:**
- Trace all `tools/call` requests
- Track app rendering performance
- Monitor user interactions

**AppSignal:**
- HTTP request metrics
- Tool execution latency
- Error rates

**Logs:**
```bash
# Server logs
tail -f ~/unified_inference/mcp_apps.log

# Check health
curl http://localhost:8081/health
```

---

## Production Deployment

### Systemd Service

Create `/etc/systemd/system/mcp-apps.service`:

```ini
[Unit]
Description=Diamond Node MCP Apps Server
After=network.target web-ui.service

[Service]
Type=simple
User=diamondnode
WorkingDirectory=/home/diamondnode/unified_inference
Environment="PATH=/home/diamondnode/xinference_venv/bin:/usr/bin"
Environment="MCP_APPS_PORT=8081"
ExecStart=/home/diamondnode/xinference_venv/bin/python mcp_yolo_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable mcp-apps
sudo systemctl start mcp-apps
sudo systemctl status mcp-apps
```

---

## Security

- ✅ Runs on localhost by default
- ✅ No authentication required (local-only)
- ⚠️ For remote access, add reverse proxy with auth (nginx + BasicAuth)
- ⚠️ Sanitize tool inputs (addresses, file paths)
- ⚠️ Rate limit tool calls (prevent abuse)

---

## Troubleshooting

**Issue:** Apps not rendering in Claude

**Solution:**
1. Verify server is running: `curl http://localhost:8081/health`
2. Check Claude config: `~/Library/Application Support/Claude/claude_desktop_config.json`
3. Restart Claude Desktop
4. Check logs: `tail -f ~/unified_inference/mcp_apps.log`

**Issue:** Tool execution fails

**Solution:**
1. Verify orchestrator is available: Check `orchestrator_ready: true` in `/health`
2. Test tool directly: `curl -X POST http://localhost:8081/mcp -d '...'`
3. Check dependencies: `source ~/xinference_venv/bin/activate && python -c "import claude_orchestrator"`

**Issue:** UI components not displaying correctly

**Solution:**
1. Check `mcp_yolo_app.json` syntax: `python -m json.tool mcp_yolo_app.json`
2. Verify `ui_component` definitions match client capabilities
3. Test in different MCP client (Postman, MCPJam)

---

## Next Steps

1. ✅ MCP Apps installed and configured
2. ✅ 4 interactive apps created (YOLO11, VRAM, QAOA, Portfolio)
3. ✅ FastAPI MCP server implemented
4. ⏳ Test with Claude Desktop (add config)
5. ⏳ Deploy systemd service for production
6. ⏳ Add more apps (optimizer dashboard, gas fee timeline, etc.)

---

## Resources

- **GitHub:** https://github.com/modelcontextprotocol/ext-apps
- **NPM:** https://www.npmjs.com/package/@modelcontextprotocol/ext-apps
- **MCP Spec:** https://modelcontextprotocol.io/
- **Local Config:** `~/unified_inference/mcp_yolo_app.json`
- **Local Server:** `~/unified_inference/mcp_yolo_server.py`

---

**Status:** ✅ MCP Apps integration complete!

**YOLO Detection UI:** Ready for interactive object detection with bounding box overlays.
