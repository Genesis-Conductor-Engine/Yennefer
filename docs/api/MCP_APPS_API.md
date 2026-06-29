# MCP Apps API Reference

API documentation for Model Context Protocol (MCP) Apps integration.

## Overview

MCP Apps provides interactive UI components for Claude, enabling rich visual interfaces for object detection, blockchain analytics, and more.

## JSON-RPC Endpoint

**Base URL:** `http://localhost:8000/mcp`

**Protocol:** JSON-RPC 2.0

**Content-Type:** `application/json`

## Methods

### `apps/list`

List all available MCP apps.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "apps/list",
  "params": {},
  "id": 1
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "apps": [
      {
        "id": "yolo11-detector",
        "name": "YOLO11 Object Detector",
        "description": "Interactive object detection with YOLO11",
        "icon": "🎯",
        "category": "computer-vision",
        "capabilities": ["image-upload", "real-time-detection", "bounding-boxes"]
      },
      {
        "id": "blockchain-portfolio",
        "name": "Blockchain Portfolio Analyzer",
        "description": "Analyze crypto portfolios and risk",
        "icon": "💰",
        "category": "blockchain",
        "capabilities": ["wallet-query", "risk-analysis", "rebalancing"]
      }
    ]
  },
  "id": 1
}
```

### `apps/render`

Render an app UI component.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "apps/render",
  "params": {
    "app_id": "yolo11-detector",
    "component": "detection-view",
    "props": {
      "image_url": "https://example.com/image.jpg",
      "confidence": 0.5
    }
  },
  "id": 2
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "type": "ui-component",
    "component": {
      "type": "container",
      "children": [
        {
          "type": "image",
          "src": "https://example.com/image.jpg",
          "alt": "Detection image"
        },
        {
          "type": "overlay",
          "boxes": [
            {
              "label": "person",
              "confidence": 0.95,
              "bbox": [100, 150, 300, 450],
              "color": "#00ff00"
            }
          ]
        },
        {
          "type": "table",
          "headers": ["Label", "Confidence", "Position"],
          "rows": [
            ["person", "95%", "x:100 y:150 w:200 h:300"]
          ]
        }
      ]
    }
  },
  "id": 2
}
```

### `apps/execute`

Execute an app action.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "method": "apps/execute",
  "params": {
    "app_id": "blockchain-portfolio",
    "action": "analyze-risk",
    "arguments": {
      "wallet_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
      "chain": "ethereum"
    }
  },
  "id": 3
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "action": "analyze-risk",
    "status": "success",
    "data": {
      "risk_score": 0.35,
      "volatility": "medium",
      "diversification": 0.72,
      "recommendations": [
        "Consider rebalancing to reduce concentration risk",
        "Add stablecoin allocation for stability"
      ]
    }
  },
  "id": 3
}
```

## UI Component Types

MCP Apps supports the following UI component types:

### Container

```json
{
  "type": "container",
  "layout": "vertical",  // "vertical" | "horizontal" | "grid"
  "spacing": 16,
  "children": [...]
}
```

### Image

```json
{
  "type": "image",
  "src": "https://example.com/image.jpg",
  "alt": "Description",
  "width": 640,
  "height": 480
}
```

### Overlay

```json
{
  "type": "overlay",
  "boxes": [
    {
      "label": "person",
      "confidence": 0.95,
      "bbox": [x, y, width, height],
      "color": "#00ff00"
    }
  ]
}
```

### Table

```json
{
  "type": "table",
  "headers": ["Column 1", "Column 2"],
  "rows": [
    ["Value 1", "Value 2"],
    ["Value 3", "Value 4"]
  ],
  "sortable": true
}
```

### Chart

```json
{
  "type": "chart",
  "chart_type": "line",  // "line" | "bar" | "pie" | "scatter"
  "data": {
    "labels": ["Jan", "Feb", "Mar"],
    "datasets": [
      {
        "label": "Portfolio Value",
        "data": [1000, 1200, 1100],
        "color": "#3b82f6"
      }
    ]
  }
}
```

### Button

```json
{
  "type": "button",
  "label": "Rebalance Portfolio",
  "action": "rebalance",
  "variant": "primary",  // "primary" | "secondary" | "danger"
  "disabled": false
}
```

### Text

```json
{
  "type": "text",
  "content": "Analysis complete",
  "style": "heading",  // "heading" | "body" | "caption" | "code"
  "color": "#1f2937"
}
```

## Available Apps

### YOLO11 Object Detector

**App ID:** `yolo11-detector`

**Components:**
- `detection-view`: Main detection interface
- `upload-form`: Image upload form
- `results-list`: Detection results table

**Actions:**
- `detect`: Run object detection
- `export-results`: Export detection data

**Example:**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post("http://localhost:8000/mcp", json={
        "jsonrpc": "2.0",
        "method": "apps/execute",
        "params": {
            "app_id": "yolo11-detector",
            "action": "detect",
            "arguments": {
                "image_url": "https://example.com/image.jpg",
                "confidence": 0.5
            }
        },
        "id": 1
    })
    
    result = response.json()["result"]
    print(f"Detected {len(result['data']['detections'])} objects")
```

### Blockchain Portfolio Analyzer

**App ID:** `blockchain-portfolio`

**Components:**
- `portfolio-view`: Portfolio overview
- `risk-dashboard`: Risk metrics dashboard
- `rebalancing-tool`: Interactive rebalancing

**Actions:**
- `analyze-risk`: Analyze portfolio risk
- `simulate-rebalancing`: Monte Carlo rebalancing simulation
- `optimize-gas`: Gas fee optimization

**Example:**
```python
response = await client.post("http://localhost:8000/mcp", json={
    "jsonrpc": "2.0",
    "method": "apps/execute",
    "params": {
        "app_id": "blockchain-portfolio",
        "action": "simulate-rebalancing",
        "arguments": {
            "current_allocation": {"ETH": 0.6, "BTC": 0.3, "USDC": 0.1},
            "target_allocation": {"ETH": 0.5, "BTC": 0.3, "USDC": 0.2},
            "simulations": 1000
        }
    },
    "id": 2
})
```

### CUDA-Q QAOA Optimizer

**App ID:** `cuda-q-qaoa`

**Components:**
- `optimizer-view`: Optimization interface
- `results-graph`: Energy convergence graph
- `parameters-form`: QAOA parameters

**Actions:**
- `optimize`: Run QAOA optimization
- `visualize-circuit`: Visualize quantum circuit

## Integration with Claude

MCP Apps integrate seamlessly with Claude Orchestrator:

```python
from src.orchestrator import ClaudeOrchestrator
from src.mcp_apps import MCPAppsClient

orchestrator = ClaudeOrchestrator(api_key=api_key)
mcp_client = MCPAppsClient(base_url="http://localhost:8000")

# Define MCP tools for Claude
mcp_tools = [
    {
        "name": "render_mcp_app",
        "description": "Render an interactive MCP app UI",
        "input_schema": {
            "type": "object",
            "properties": {
                "app_id": {"type": "string"},
                "component": {"type": "string"},
                "props": {"type": "object"}
            },
            "required": ["app_id", "component"]
        }
    }
]

# Claude can now use MCP apps
response = await orchestrator.chat(
    message="Show me object detection for this image",
    tools=mcp_tools
)
```

## Error Handling

All JSON-RPC errors follow the standard format:

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32600,
    "message": "Invalid Request",
    "data": {
      "details": "Missing required parameter: app_id"
    }
  },
  "id": 1
}
```

**Error Codes:**
- `-32700`: Parse error
- `-32600`: Invalid request
- `-32601`: Method not found
- `-32602`: Invalid params
- `-32603`: Internal error
- `-32000`: App not found
- `-32001`: Component not found
- `-32002`: Action failed

## Configuration

Configure MCP Apps via environment variables:

```bash
MCP_APPS_ENABLED=true
MCP_APPS_PORT=8000
MCP_APPS_HOST=0.0.0.0
MCP_APPS_LOG_LEVEL=INFO
```

## Performance

- **Response time:** < 100ms for UI rendering
- **Action execution:** Varies by action (detection: ~200ms, blockchain query: ~500ms)
- **Concurrent requests:** Supports 100+ concurrent connections
- **WebSocket support:** For real-time updates (coming soon)

## Related Documentation

- [MCP Apps Integration Guide](../guides/MCP_APPS_INTEGRATION.md)
- [Building Custom Apps](../guides/CUSTOM_MCP_APPS.md)
- [Claude Orchestrator API](ORCHESTRATOR_API.md)

---

**Last updated:** 2025-05-12
