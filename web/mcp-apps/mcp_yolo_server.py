#!/usr/bin/env python3
# Copyright (c) 2026 Diamond Node Team
# Licensed under the MIT License - see LICENSE file for details

"""
MCP Apps Server for Diamond Node - YOLO11 Integration

This server extends the unified inference system with MCP Apps support,
providing interactive UIs for YOLO11 detection, VRAM monitoring, QAOA
optimization, and blockchain portfolio analysis.
"""

import os
import sys
import json
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add unified_inference to path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, WebSocket, Request, Response
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

try:
    from claude_orchestrator import ClaudeOrchestrator
    ORCHESTRATOR_AVAILABLE = True
except ImportError:
    ORCHESTRATOR_AVAILABLE = False
    print("⚠ ClaudeOrchestrator not available, using mock")


app = FastAPI(
    title="Diamond Node MCP Apps Server",
    description="MCP Apps integration for YOLO11, CUDA-Q, and Blockchain tools",
    version="1.0.0"
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator instance
orchestrator = None
if ORCHESTRATOR_AVAILABLE:
    try:
        orchestrator = ClaudeOrchestrator()
        print("✓ ClaudeOrchestrator initialized")
    except Exception as e:
        print(f"⚠ ClaudeOrchestrator initialization failed: {e}")


# ============================================================================
# MCP Protocol Endpoints
# ============================================================================

@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """
    Main MCP JSON-RPC endpoint.
    Handles initialize, tools/list, tools/call, apps/list, apps/render.
    """
    config_path = Path(__file__).parent / "mcp_yolo_app.json"
    try:
        body = await request.json()
        method = body.get("method")
        params = body.get("params", {})
        request_id = body.get("id", 1)
        
        if method == "initialize":
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2025-03-26",
                    "serverInfo": {
                        "name": "diamond-node-mcp-apps",
                        "version": "1.0.0"
                    },
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "apps": {"listChanged": False},
                        "streaming": True
                    }
                }
            })
        
        elif method == "tools/list":
            # Use tools from orchestrator if available, else fallback to config
            if orchestrator:
                tools = ClaudeOrchestrator.TOOLS
            elif config_path.exists():
                config = json.loads(config_path.read_text())
                tools = [
                    {
                        "name": tool["name"],
                        "description": tool["description"],
                        "inputSchema": tool.get("input_schema", {})
                    }
                    for tool in config.get("tools", [])
                ]
            else:
                tools = []
            
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": tools}
            })
        
        elif method == "resources/list":
            resources = [
                {
                    "uri": "ui://widgets/nox_control_panel.html",
                    "name": "NOX Engine Control Panel",
                    "mimeType": "text/html;profile=mcp-app",
                    "description": "Interactive management panel for the NOX engine"
                }
            ]
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"resources": resources}
            })
            
        elif method == "resources/read":
            uri = params.get("uri")
            if uri == "ui://widgets/nox_control_panel.html":
                try:
                    widget_path = Path(__file__).parent / "widgets" / "nox_control_panel.html"
                    html = widget_path.read_text()
                    
                    # Inlining logic for @modelcontextprotocol/ext-apps
                    bundle_path = "/home/diamondnode/.npm-global/lib/node_modules/@modelcontextprotocol/ext-apps/dist/src/app-with-deps.js"
                    if os.path.exists(bundle_path):
                        bundle_raw = Path(bundle_path).read_text()
                        # Extract exports and convert to globalThis.ExtApps
                        import re
                        match = re.search(r'export\{([^}]+)\};?\s*$', bundle_raw)
                        if match:
                            body = match.group(1)
                            pairs = [p.strip().split(" as ") for p in body.split(",")]
                            ext_apps_body = ",".join([f"{p[1] if len(p)>1 else p[0]}:{p[0]}" for p in pairs])
                            bundle = f"globalThis.ExtApps={{{ext_apps_body}}};"
                        else:
                            bundle = bundle_raw
                    else:
                        bundle = "console.error('ext-apps bundle not found');"
                    
                    final_html = html.replace("/*__EXT_APPS_BUNDLE__*/", bundle)
                    
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "contents": [
                                {
                                    "uri": uri,
                                    "mimeType": "text/html;profile=mcp-app",
                                    "text": final_html
                                }
                            ]
                        }
                    })
                except Exception as e:
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32603, "message": str(e)}
                    })
            
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": "Resource not found"}
            })

        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            
            # Execute tool via orchestrator
            if orchestrator:
                try:
                    result = await orchestrator.execute_tool(tool_name, tool_args)
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(result, indent=2)
                                }
                            ]
                        }
                    })
                except Exception as e:
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32603,
                            "message": f"Tool execution failed: {str(e)}"
                        }
                    })
            else:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": "Orchestrator not available"
                    }
                })
        
        elif method == "apps/list":
            # Return MCP Apps definitions
            config_path = Path(__file__).parent / "mcp_yolo_app.json"
            if config_path.exists():
                config = json.loads(config_path.read_text())
                apps = [
                    {
                        "name": tool["name"],
                        "displayName": tool.get("display_name", tool["name"]),
                        "description": tool["description"],
                        "uiType": tool.get("ui_type", "embedded"),
                        "component": tool.get("ui_component", {})
                    }
                    for tool in config.get("tools", [])
                ]
            else:
                apps = []
            
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"apps": apps}
            })
        
        elif method == "apps/render":
            # Render app UI (return HTML or component definition)
            app_name = params.get("name")
            app_data = params.get("data", {})
            
            config_path = Path(__file__).parent / "mcp_yolo_app.json"
            if config_path.exists():
                config = json.loads(config_path.read_text())
                app_config = next(
                    (tool for tool in config.get("tools", []) if tool["name"] == app_name),
                    None
                )
                
                if app_config:
                    # Return component definition for client-side rendering
                    return JSONResponse({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "html": None,  # Client-side rendering
                            "component": app_config.get("ui_component", {}),
                            "data": app_data
                        }
                    })
            
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"App not found: {app_name}"
                }
            })
        
        else:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            })
    
    except Exception as e:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32700,
                "message": f"Parse error: {str(e)}"
            }
        })


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "service": "diamond-node-mcp-apps",
        "version": "1.0.0",
        "orchestrator_available": ORCHESTRATOR_AVAILABLE,
        "orchestrator_ready": orchestrator is not None
    })


@app.get("/.well-known/mcp")
async def mcp_discovery():
    """MCP discovery endpoint"""
    return JSONResponse({
        "protocol": "mcp",
        "version": "2025-03-26",
        "endpoint": "/mcp",
        "transport": "http",
        "capabilities": ["tools", "apps", "streaming"]
    })


# ============================================================================
# Demo/Testing Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with API info"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Diamond Node MCP Apps Server</title>
        <style>
            body { font-family: system-ui; max-width: 800px; margin: 40px auto; padding: 0 20px; background: #0A0E27; color: #fff; }
            h1 { color: #00D4FF; }
            code { background: #151B3B; padding: 2px 6px; border-radius: 3px; }
            .endpoint { background: #151B3B; padding: 15px; margin: 10px 0; border-radius: 8px; }
            .method { color: #00D4FF; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>🎯 Diamond Node MCP Apps Server</h1>
        <p>Interactive UI extensions for YOLO11, CUDA-Q, and Blockchain tools</p>
        
        <h2>Endpoints</h2>
        <div class="endpoint">
            <span class="method">POST</span> <code>/mcp</code> - MCP JSON-RPC endpoint
        </div>
        <div class="endpoint">
            <span class="method">GET</span> <code>/health</code> - Health check
        </div>
        <div class="endpoint">
            <span class="method">GET</span> <code>/.well-known/mcp</code> - MCP discovery
        </div>
        
        <h2>Available Apps</h2>
        <ul>
            <li><strong>YOLO11 Detection</strong> - Interactive object detection with bounding box overlay</li>
            <li><strong>VRAM Monitor</strong> - Real-time GPU usage with Hamiltonian gauge</li>
            <li><strong>CUDA-Q QAOA</strong> - Quantum optimization with energy convergence chart</li>
            <li><strong>Portfolio Risk</strong> - Blockchain wallet risk analysis dashboard</li>
        </ul>
        
        <h2>Usage</h2>
        <p>Add to your MCP client configuration:</p>
        <pre><code>{
  "mcpServers": {
    "diamond-node": {
      "command": "python",
      "args": ["~/unified_inference/mcp_yolo_server.py"],
      "env": {}
    }
  }
}</code></pre>
        
        <p>Or use the HTTP transport:</p>
        <pre><code>curl -X POST http://localhost:8080/mcp \\
  -H "Content-Type: application/json" \\
  -d '{"jsonrpc":"2.0","id":1,"method":"apps/list"}'</code></pre>
    </body>
    </html>
    """)


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("MCP_APPS_PORT", "8081"))
    
    print(f"""
╔════════════════════════════════════════════════════════════════╗
║         Diamond Node MCP Apps Server                           ║
║         Interactive UIs for YOLO11 + CUDA-Q + Blockchain       ║
╚════════════════════════════════════════════════════════════════╝

🌐 Server: http://localhost:{port}
🔌 MCP Endpoint: http://localhost:{port}/mcp
🏥 Health Check: http://localhost:{port}/health
📋 Config: ~/unified_inference/mcp_yolo_app.json

🎯 Available Apps:
  • YOLO11 Object Detection (interactive canvas)
  • VRAM Monitor (real-time gauge)
  • CUDA-Q QAOA Optimizer (energy chart)
  • Blockchain Portfolio Risk (dashboard)

Starting server...
""")
    
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
