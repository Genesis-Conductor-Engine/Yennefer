#!/usr/bin/env python3
"""
Yennefer Web Integration Server
Serves the chatbot interface and proxies requests to Yennefer Soul API
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

import uvicorn

# Configuration
SOUL_API_URL = os.getenv("YENNEFER_SOUL_API_URL", "http://yennefer-soul-api:8088")
WS_SOUL_API_URL = os.getenv("YENNEFER_WS_API_URL", "ws://yennefer-soul-api:8088/ws/soul")
WEB_PORT = int(os.getenv("WEB_PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Application setup
app = FastAPI(
    title="Yennefer Web Integration",
    description="Web interface for Yennefer Thermodynamic Agent with chatbot",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# Soul API client (singleton)
class SoulAPIClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.session = None
        return cls._instance
    
    async def get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def get_soul_state(self):
        try:
            async with await self.get_session() as session:
                async with session.get(f"{SOUL_API_URL}/api/soul") as response:
                    if response.status == 200:
                        return await response.json()
        except Exception as e:
            print(f"[SoulAPI] Error getting soul state: {e}")
        return None
    
    async def send_chat_message(self, text: str, connection_id: Optional[str] = None):
        """Send chat message to Yennefer"""
        payload = {"text": text}
        if connection_id:
            payload["connectionId"] = connection_id
        
        try:
            async with await self.get_session() as session:
                async with session.post(
                    f"{SOUL_API_URL}/api/chat",
                    json=payload
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}

soul_client = SoulAPIClient()

# Background task for broadcasting soul state
async def soul_state_broadcaster():
    """Broadcast soul state to all connected WebSocket clients"""
    while True:
        try:
            soul_state = await soul_client.get_soul_state()
            if soul_state:
                await manager.broadcast({
                    "type": "soul_update",
                    "data": soul_state
                })
        except Exception as e:
            print(f"[Broadcaster] Error: {e}")
        await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(soul_state_broadcaster())

@app.on_event("shutdown")
async def shutdown_event():
    if soul_client.session:
        await soul_client.session.close()

# Routes

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Main page"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "soul_api_url": WS_SOUL_API_URL,
        "rest_api_url": SOUL_API_URL
    })

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        soul_state = await soul_client.get_soul_state()
        if soul_state:
            return {
                "status": "healthy",
                "service": "yennefer-web",
                "soul_status": soul_state.get("concave_state", "UNKNOWN"),
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "degraded",
                "service": "yennefer-web",
                "error": "Cannot connect to Soul API",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "yennefer-web",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/soul")
async def proxy_soul_state():
    """Proxy to Soul API"""
    soul_state = await soul_client.get_soul_state()
    if soul_state:
        return JSONResponse(soul_state)
    return JSONResponse({"error": "Cannot connect to Soul API"}, status_code=502)

@app.post("/api/chat")
async def proxy_chat(request: Request):
    """Proxy chat messages to Soul API"""
    body = await request.json()
    text = body.get("text", "")
    connection_id = body.get("connectionId")
    
    if not text:
        return JSONResponse({"error": "Message text is required"}, status_code=400)
    
    result = await soul_client.send_chat_message(text, connection_id)
    return JSONResponse(result)

@app.websocket("/ws/soul")
async def websocket_soul(websocket: WebSocket):
    """WebSocket endpoint for real-time soul state updates"""
    await manager.connect(websocket)
    
    try:
        # Send initial soul state
        soul_state = await soul_client.get_soul_state()
        if soul_state:
            await websocket.send_json({"type": "initial", "data": soul_state})
        
        # Handle incoming messages (for future chat functionality)
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                message = json.loads(data)
                
                # Handle handshake
                if message.get("type") == "handshake":
                    await websocket.send_json({
                        "type": "handshake_ack",
                        "server": "yennefer-web",
                        "version": "1.0.0"
                    })
                
                # Handle chat messages (forward to Soul API)
                elif message.get("type") == "chat_message":
                    text = message.get("text", "")
                    connection_id = message.get("connectionId")
                    
                    if text:
                        result = await soul_client.send_chat_message(text, connection_id)
                        if result and "error" not in result:
                            await websocket.send_json({
                                "type": "chat_response",
                                "data": {
                                    "text": result.get("text", ""),
                                    "metadata": result.get("metadata", {})
                                }
                            })
                        else:
                            await websocket.send_json({
                                "type": "error",
                                "error": result.get("error", "Unknown error")
                            })
                
                # Handle ping/pong
                elif data == "ping":
                    await websocket.send_text("pong")
                    
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.now().isoformat()
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[WebSocket] Error: {e}")
        manager.disconnect(websocket)

@app.get("/api/config")
async def get_config():
    """Get client configuration"""
    return {
        "soul_api_url": WS_SOUL_API_URL,
        "rest_api_url": SOUL_API_URL,
        "web_port": WEB_PORT
    }

# Static file for compatibility
@app.get("/index.html", response_class=HTMLResponse)
async def read_index(request: Request):
    return RedirectResponse("/")

if __name__ == "__main__":
    print("=" * 60)
    print("YENNEFER WEB INTEGRATION SERVER")
    print("=" * 60)
    print(f"Web Port: {WEB_PORT}")
    print(f"Soul API: {SOUL_API_URL}")
    print(f"WS Soul API: {WS_SOUL_API_URL}")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=WEB_PORT,
        reload=DEBUG
    )
