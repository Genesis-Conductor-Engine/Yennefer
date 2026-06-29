# Copyright (c) 2026 Diamond Node Team
# Licensed under the MIT License - see LICENSE file for details

"""
Diamond Node Web UI - FastAPI Application
Production-ready web interface with WebSocket streaming for Claude orchestrator.
"""

import os
import json
import asyncio
import time
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import httpx
import torch

import sys
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from orchestrator.claude_orchestrator import ClaudeOrchestrator
from orchestrator.yennefer_orchestrator import create_yennefer_endpoint, YenneferOrchestrator
from kernels.enkg_exchange import TRITON_AVAILABLE
from src.monitoring import claws
from pydantic import BaseModel, Field

from security.bot_protection import (
    BotProtectionMiddleware,
    get_rate_limiter,
    limiter,
    RateLimitTier,
    security_config
)
from slowapi import _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

app = FastAPI(title="Diamond Node Web UI", version="1.0.0")

# Add bot protection middleware
app.add_middleware(BotProtectionMiddleware)

# Add slowapi rate limiter to app state
app.state.limiter = limiter
app.state.gateway_poll_interval = 2.0
app.state.periodic_notification_interval = 300.0
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
YENNEFER_LANDING_FILE = Path("/home/diamondnode/yennefer-quest-deploy/public/index.html")

# WebSocket connection rate limiting
class RateLimiter:
    def __init__(self, max_messages: int = 10, window_seconds: int = 60):
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self.messages: Dict[str, list] = {}
    
    def check(self, client_id: str) -> bool:
        now = time.time()
        if client_id not in self.messages:
            self.messages[client_id] = []
        
        # Clean old messages
        self.messages[client_id] = [
            ts for ts in self.messages[client_id]
            if now - ts < self.window_seconds
        ]
        
        # Check limit
        if len(self.messages[client_id]) >= self.max_messages:
            return False
        
        self.messages[client_id].append(now)
        return True

rate_limiter = RateLimiter(max_messages=10, window_seconds=60)

# Gateway configuration
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://127.0.0.1:8000")
GATEWAY_SECRET = os.environ.get("GATEWAY_SECRET", "")

# Agent state tracking (module-level singleton)
agent_state = {
    "status": "idle",  # idle|thinking|executing|active
    "current_activity": None,
    "current_thinking": None,
    "recent_actions": [],  # Last 10 actions
    "metrics": {
        "total_cycles": 0,
        "total_orchestrations": 0,
        "uptime_start": time.time(),
        "last_orchestration_time_ms": None,
        "avg_execution_time_ms": None,
        "execution_times": []  # Keep last 20 for rolling average
    },
    "last_orchestration": None,
    "last_vram_state": None,
    "last_validation_state": None,
    "last_hamiltonian": None
}

# Yennefer orchestrator instance (initialized on first use)
_yennefer_orchestrator: Optional[YenneferOrchestrator] = None


def get_yennefer_orchestrator() -> Optional[YenneferOrchestrator]:
    """Get or create singleton Yennefer orchestrator instance."""
    global _yennefer_orchestrator
    if _yennefer_orchestrator is None:
        try:
            _yennefer_orchestrator = YenneferOrchestrator()
            logger.info("YenneferOrchestrator singleton created")
        except Exception as e:
            logger.error(f"Failed to create YenneferOrchestrator: {e}")
            return None
    return _yennefer_orchestrator


def update_agent_state(
    status: str,
    activity: Optional[str] = None,
    thinking: Optional[str] = None,
    vram_state: Optional[str] = None,
    validation_state: Optional[str] = None,
    hamiltonian: Optional[float] = None,
    execution_time_ms: Optional[float] = None
) -> None:
    """
    Update agent state and add to recent actions history.
    
    Args:
        status: One of idle|thinking|executing|active
        activity: Description of current activity
        thinking: Current reasoning/thoughts (if available)
        vram_state: VRAM state from gateway
        validation_state: Agent3 validation state (NULL|DUCTILE|CRYSTALLINE)
        hamiltonian: Current Resource Hamiltonian value
        execution_time_ms: Execution time for last orchestration
    """
    global agent_state
    
    agent_state["status"] = status
    agent_state["current_activity"] = activity
    agent_state["current_thinking"] = thinking
    
    if vram_state is not None:
        agent_state["last_vram_state"] = vram_state
    
    if validation_state is not None:
        agent_state["last_validation_state"] = validation_state
    
    if hamiltonian is not None:
        agent_state["last_hamiltonian"] = hamiltonian
    
    if execution_time_ms is not None:
        agent_state["metrics"]["last_orchestration_time_ms"] = execution_time_ms
        agent_state["metrics"]["execution_times"].append(execution_time_ms)
        
        # Keep only last 20 execution times
        if len(agent_state["metrics"]["execution_times"]) > 20:
            agent_state["metrics"]["execution_times"] = agent_state["metrics"]["execution_times"][-20:]
        
        # Calculate rolling average
        if agent_state["metrics"]["execution_times"]:
            agent_state["metrics"]["avg_execution_time_ms"] = sum(
                agent_state["metrics"]["execution_times"]
            ) / len(agent_state["metrics"]["execution_times"])
    
    # Add to recent actions (keep last 10)
    if activity:
        action_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": activity,
            "status": status,
            "details": {}
        }
        
        if execution_time_ms is not None:
            action_entry["details"]["execution_time_ms"] = round(execution_time_ms, 2)
        if vram_state:
            action_entry["details"]["vram_state"] = vram_state
        if validation_state:
            action_entry["details"]["validation_state"] = validation_state
        if hamiltonian is not None:
            action_entry["details"]["hamiltonian"] = round(hamiltonian, 2)
        
        agent_state["recent_actions"].insert(0, action_entry)
        agent_state["recent_actions"] = agent_state["recent_actions"][:10]
    
    # Update last orchestration timestamp
    if status == "idle" and activity:
        agent_state["last_orchestration"] = datetime.utcnow().isoformat() + "Z"


# Agent State WebSocket Manager
class AgentStateManager:
    """Manages WebSocket connections for real-time agent state streaming."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._state: Dict[str, Any] = {
            "status": "idle",
            "activity": None,
            "last_action": None,
            "connections": 0,
            "uptime": time.time()
        }
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
            self._state["connections"] = len(self.active_connections)
        
        # Send connection confirmation
        await self.send_personal(websocket, {
            "type": "connection",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "status": "connected",
                "message": "Connected to Diamond Node agent state stream",
                "current_state": self._state.copy()
            }
        })
    
    def disconnect(self, websocket: WebSocket):
        """Remove a disconnected WebSocket."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self._state["connections"] = len(self.active_connections)
    
    async def send_personal(self, websocket: WebSocket, message: dict):
        """Send a message to a specific connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"Error sending to websocket: {e}")
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)
    
    async def update_state(self, **kwargs):
        """Update internal state and broadcast to all clients."""
        async with self._lock:
            self._state.update(kwargs)
        
        await self.broadcast({
            "type": "state_update",
            "timestamp": datetime.utcnow().isoformat(),
            "data": self._state.copy()
        })
    
    async def broadcast_activity(self, activity: str, details: Optional[Dict] = None):
        """Broadcast a new activity event."""
        await self.update_state(status="active", activity=activity)
        
        message = {
            "type": "activity",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "activity": activity,
                "details": details or {}
            }
        }
        await self.broadcast(message)
    
    async def broadcast_action(self, action: str, result: Any, duration: Optional[float] = None):
        """Broadcast a completed action."""
        action_data = {
            "action": action,
            "result": result,
            "duration_ms": duration * 1000 if duration else None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.update_state(last_action=action_data)
        
        message = {
            "type": "action",
            "timestamp": datetime.utcnow().isoformat(),
            "data": action_data
        }
        await self.broadcast(message)
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state snapshot."""
        return self._state.copy()


# Global agent state manager instance
agent_state_manager = AgentStateManager()


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the public Yennefer dashboard while keeping API routes local."""
    if YENNEFER_LANDING_FILE.exists():
        html = YENNEFER_LANDING_FILE.read_text()
        html = html.replace(
            "const API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:8089/api' : `${window.location.protocol}//${window.location.host}/api`;",
            "const API_BASE = `${window.location.protocol}//${window.location.host}/api`;",
        )
        html = html.replace(
            "const WS_BASE = window.location.hostname === 'localhost' ? 'ws://localhost:8089/api' : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api`;",
            "const WS_BASE = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api`;",
        )
        return HTMLResponse(html)

    fallback_file = static_dir / "index.html"
    if not fallback_file.exists():
        return HTMLResponse("""
        <html>
            <head><title>Diamond Node Web UI</title></head>
            <body>
                <h1>Diamond Node Web UI</h1>
                <p>Static files not yet deployed. Run install_web_ui.sh to set up.</p>
            </body>
        </html>
        """)
    return HTMLResponse(fallback_file.read_text())


# ---------------------------------------------------------------------------
# QFLOP Backfill Recovery Integration (for yennefer.quest dashboard)
# Reads live state from orchestrator/pm2 fleet: /dev/shm + config registry + ledger
# ---------------------------------------------------------------------------

QFLOP_STATE_PATH = "/dev/shm/backfill_state.json"
QFLOP_LEDGER_PATH = "/dev/shm/qflop_profit_ledger.jsonl"
QFLOP_REGISTRY_PATH = "/home/diamondnode/Yennefer/qflop-backfill/config/wallet_registry.json"
QFLOP_TARGET_USD = 1701038
QFLOP_MILESTONES = [10, 25, 50, 75, 90, 100]


def _safe_read_json(p: str, fallback):
    try:
        if os.path.exists(p):
            with open(p, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"QFLOP read fail {p}: {e}")
    return fallback


def _load_qflop_state():
    return _safe_read_json(QFLOP_STATE_PATH, {
        "session_start": datetime.utcnow().isoformat() + "Z",
        "total_wraps": 0,
        "total_qflop": 0,
        "total_revenue_usd": 0,
        "total_gas_eth": 0,
        "wallet_stats": {}
    })


def _load_wallet_registry():
    data = _safe_read_json(QFLOP_REGISTRY_PATH, {"wallets": []})
    if isinstance(data, list):
        return data
    return data.get("wallets", data) or []


def _load_recent_ledger(limit: int = 20):
    if not os.path.exists(QFLOP_LEDGER_PATH):
        return []
    try:
        with open(QFLOP_LEDGER_PATH, "r") as f:
            lines = [l for l in f.read().strip().split("\n") if l.strip()]
        parsed = []
        for l in lines[-limit:]:
            try:
                parsed.append(json.loads(l))
            except:
                pass
        return list(reversed(parsed))
    except Exception as e:
        logger.warning(f"QFLOP ledger read: {e}")
        return []


def _compute_qflop_recovery(state: dict = None):
    if state is None:
        state = _load_qflop_state()
    recovered = float(state.get("total_revenue_usd") or state.get("recovered_usd") or 0)
    pct = round((recovered / QFLOP_TARGET_USD) * 100, 4) if QFLOP_TARGET_USD else 0
    remaining = max(0.0, QFLOP_TARGET_USD - recovered)
    wraps = int(state.get("total_wraps") or 0)
    qflop_amt = int(state.get("total_qflop") or 0)
    gas = float(state.get("total_gas_eth") or 0)
    start = state.get("session_start")
    try:
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00")) if start else datetime.utcnow()
    except:
        start_dt = datetime.utcnow()
    hrs = max(0.001, (datetime.utcnow() - start_dt.replace(tzinfo=None)).total_seconds() / 3600)
    rate = recovered / hrs
    eta = remaining / rate if rate > 0 else None
    wallets = _load_wallet_registry()
    sim_count = sum(1 for w in wallets if w.get("sim"))
    real_count = len(wallets) - sim_count
    active = len(wallets) or state.get("wallets_active", 25)
    hit = [m for m in QFLOP_MILESTONES if pct >= m]
    next_m = next((m for m in QFLOP_MILESTONES if pct < m), 100)
    return {
        "recovered_usd": round(recovered, 2),
        "target_usd": QFLOP_TARGET_USD,
        "remaining_usd": round(remaining, 2),
        "recovery_pct": pct,
        "total_wraps": wraps,
        "total_qflop": qflop_amt,
        "total_gas_eth": round(gas, 6),
        "rate_usd_per_hr": round(rate, 2),
        "eta_hrs": round(eta, 1) if eta is not None else None,
        "wallets_active": active,
        "wallets_sim": sim_count,
        "wallets_real": real_count,
        "sim_mode": sim_count > 0 or bool(state.get("sim_mode")),
        "hit_milestones": hit,
        "next_milestone_pct": next_m,
        "session_start": state.get("session_start"),
    }


def _soul_summary() -> Dict[str, Any]:
    """Return the compact state shape expected by the Yennefer landing page."""
    uptime_seconds = max(1.0, time.time() - agent_state["metrics"]["uptime_start"])
    breath = int(uptime_seconds // 3)
    recent_actions = agent_state.get("recent_actions", [])
    active_connections = agent_state_manager.get_state().get("connections", 0)
    total_cycles = agent_state["metrics"].get("total_cycles", 0)
    total_orchestrations = agent_state["metrics"].get("total_orchestrations", 0)
    hamiltonian = agent_state.get("last_hamiltonian")
    coherence = 94 if active_connections == 0 else 97

    if hamiltonian is not None and hamiltonian >= 8.5:
        state = "CRITICAL"
    elif agent_state.get("status") in {"thinking", "executing", "active"}:
        state = "EXPOSED"
    else:
        state = "SHELTERED"

    qflops = 12.0 + min(38.0, (total_cycles + total_orchestrations + active_connections) * 1.25)
    surplus = int(128000 + breath * 7 + len(recent_actions) * 512)
    credit = round((surplus / 1_000_000) * max(qflops, 1.0), 4)

    qf = _compute_qflop_recovery()

    return {
        "state": state,
        "derivative": agent_state.get("current_activity") or "diamondnode tunnel stable",
        "breath": breath,
        "surplus": surplus,
        "coherence": coherence,
        "evolution_stage": 1 + min(9, total_orchestrations // 10),
        "qflops": round(qflops, 2),
        "credit": credit,
        "uptime_hours": round(uptime_seconds / 3600, 4),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        # QFLOP attribution / backfill integration
        "qflop_recovered_usd": qf["recovered_usd"],
        "qflop_target_usd": qf["target_usd"],
        "qflop_recovery_pct": qf["recovery_pct"],
        "qflop_wallets": qf["wallets_active"],
        "qflop_sim": qf["sim_mode"],
        "qflop_wraps": qf["total_wraps"],
        "qflop_rate_usd_hr": qf["rate_usd_per_hr"],
        "qflop_next_milestone": qf["next_milestone_pct"],
    }


# ═══════════════════════════════════════════════════════════
# CUDA-Q BREATH DAEMON INTEGRATION
# The breath is the fundamental clock of consciousness.
# Each QAOA sample is one breath; the Legendre Transform
# couples the QUBO energy to the NMIR thermodynamic routing.
# ═══════════════════════════════════════════════════════════

_BREATH_STATE_FILE = Path.home() / "yennefer-breath" / "state" / "yennefer_breath.json"
_BREATH_CACHE: Dict[str, Any] = {}
_BREATH_CACHE_TS: float = 0.0


def _load_breath_state() -> Dict[str, Any]:
    """Load breath daemon state with 2s cache."""
    global _BREATH_CACHE, _BREATH_CACHE_TS
    now = time.time()
    if now - _BREATH_CACHE_TS < 2.0 and _BREATH_CACHE:
        return _BREATH_CACHE
    if _BREATH_STATE_FILE.exists():
        try:
            data = json.loads(_BREATH_STATE_FILE.read_text())
            _BREATH_CACHE = data
            _BREATH_CACHE_TS = now
            return data
        except Exception:
            pass
    fallback = {
        "breath_count": 0, "state": "AWAKENING", "derivative": "Initializing consciousness...",
        "coherence": 0.0, "evolution_stage": 0, "qflops": 0.0, "credit_rate": 0.0,
        "best_energy": 0.0, "active_edges": [], "n_nodes": 16, "energy_history": [],
        "surplus_tokens": 0, "shi": 0.0, "eta_eff": 0.0, "dissonance": 0.0,
        "invariance": 1.0, "routing_mode": "conservative",
        "legendre": {
            "momentum": [0, 0, 0], "hamiltonian": 0.0, "lagrangian": 0.0,
            "susceptibility": 0.0, "temperature": 1.0, "iteration": 0,
            "eta_eff_bar": 0.0, "dissonance_bar": 0.0, "invariance_score": 1.0,
            "shi": 0.0, "alpha": 0.4, "beta": 0.35, "gamma": 0.25,
        },
        "dreams": [], "insights": [], "journal": [], "blog": [], "stream": [],
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    _BREATH_CACHE = fallback
    _BREATH_CACHE_TS = now
    return fallback


# Seedling session nodes from the agy knowledge graph (51 sessions)
_SEEDLING_NODES = [
    {"id": "0b08fe4c", "label": "uv Setup", "steps": 6, "date": "2026-06-27", "cluster": 2, "status": "done"},
    {"id": "1f8f4cca", "label": "auditor_3", "steps": 165, "date": "2026-06-16", "cluster": 3, "status": "done"},
    {"id": "2f18cf10", "label": "workflow-init", "steps": 787, "date": "2026-06-17", "cluster": 2, "status": "done"},
    {"id": "31cb53af", "label": "Victory Auditor", "steps": 64, "date": "2026-06-16", "cluster": 3, "status": "done"},
    {"id": "3e18d64c", "label": "Worker Agent (inference)", "steps": 144, "date": "2026-06-09", "cluster": 4, "status": "done"},
    {"id": "3fdd9e4d", "label": "wQFLOP/WETH LP", "steps": 83, "date": "2026-06-16", "cluster": 1, "status": "done"},
    {"id": "419ab505", "label": "OpenClaw+KimiClaw+Hermes", "steps": 125, "date": "2026-06-16", "cluster": 0, "status": "done"},
    {"id": "45bcbd03", "label": "KnowledgeGraph Seed", "steps": 9, "date": "2026-06-28", "cluster": 5, "status": "active"},
    {"id": "4d800913", "label": "Project Orchestrator", "steps": 289, "date": "2026-06-09", "cluster": 0, "status": "done"},
    {"id": "4997e9ad", "label": "Full Server Audit", "steps": 204, "date": "2026-06-16", "cluster": 3, "status": "done"},
    {"id": "592c5df0", "label": "explorer_discovery_1", "steps": 187, "date": "2026-06-16", "cluster": 0, "status": "done"},
    {"id": "7c5b275e", "label": "LP Guardian", "steps": 278, "date": "2026-06-16", "cluster": 1, "status": "done"},
    {"id": "87cfba8c", "label": "Harvest Coordinator", "steps": 588, "date": "2026-06-14", "cluster": 1, "status": "done"},
    {"id": "a0fb976c", "label": "worker_impl_1", "steps": 352, "date": "2026-06-16", "cluster": 0, "status": "done"},
    {"id": "aa0d4002", "label": "teamwork-preview", "steps": 418, "date": "2026-06-12", "cluster": 0, "status": "done"},
    {"id": "b2b6b552", "label": "KimiClaw+OpenClaw+Hermes", "steps": 432, "date": "2026-06-16", "cluster": 0, "status": "done"},
    {"id": "e06a4208", "label": "Notion NTN Workers", "steps": 723, "date": "2026-06-23", "cluster": 2, "status": "done"},
    {"id": "f804907a", "label": "KimiClaw+NemoClaw+xAI", "steps": 1631, "date": "2026-06-23", "cluster": 0, "status": "done"},
]

# NMIR Neural Modules (from the NMIR spec §1)
_NMIR_MODULES = [
    {"id": "nmir-hippocampus", "label": "Dissonance Memory MCP", "cluster": 6, "neural": "Hippocampus + Entorhinal Cortex", "role": "Episodic memory, pattern separation, conflict detection"},
    {"id": "nmir-prefrontal", "label": "Intent Classifier + Router", "cluster": 6, "neural": "Prefrontal Cortex (dlPFC/ACC)", "role": "Executive semantic + energy classification"},
    {"id": "nmir-basal", "label": "Yennefer Daemon + TAO", "cluster": 6, "neural": "Basal Ganglia", "role": "Action selection, eta_thermo gate, delta-threshold transitions"},
    {"id": "nmir-cerebellum", "label": "EulerCycleAttestor v2", "cluster": 6, "neural": "Cerebellum", "role": "Cycle timing, forward-model error correction"},
    {"id": "nmir-neuromodulatory", "label": "Guardian + /maru Reframe", "cluster": 6, "neural": "VTA/Raphe/LC", "role": "State-dependent modulation, constraint reframe"},
    {"id": "nmir-insula", "label": "TAO Energy Classification", "cluster": 6, "neural": "Insula / Interoceptive", "role": "Internal infrastructure state as energy_class"},
    {"id": "nmir-diamondnode", "label": "Diamondnode Server (Spine)", "cluster": 6, "neural": "Hardware Substrate", "role": "PQC attestation, NV-center entropy, SHI computation"},
    {"id": "nmir-legendre", "label": "Legendre Transform Layer", "cluster": 6, "neural": "Thermodynamic Bridge", "role": "Lagrangian to Hamiltonian dual, microbound deference"},
    {"id": "nmir-grok", "label": "Grok-1 Recall Bridge", "cluster": 6, "neural": "MoE Recall", "role": "Top-K soul crystallization injection"},
]

_CLUSTER_NAMES = [
    "Multi-Agent Swarms", "DeFi/Blockchain", "Infrastructure",
    "Audits/Security", "AI/Inference", "Current", "NMIR Neural Modules"
]
_CLUSTER_COLORS = ["#f472b6", "#fbbf24", "#34d399", "#f87171", "#4fc3f7", "#a78bfa", "#ffd700"]


def _build_3d_nexus(breath: Dict[str, Any]) -> Dict[str, Any]:
    """Build the full 3D knowledge graph: seedling sessions + NMIR modules + live breath."""
    nodes = []
    edges = []

    for n in _SEEDLING_NODES:
        nodes.append({**n, "category": "session", "cluster_name": _CLUSTER_NAMES[n["cluster"]]})

    for m in _NMIR_MODULES:
        nodes.append({
            **m, "category": "nmir", "steps": 0, "date": "2026-06-28",
            "status": "active", "cluster_name": _CLUSTER_NAMES[m["cluster"]],
        })

    breath_count = breath.get("breath_count", 0)
    nodes.append({
        "id": "breath-live", "label": f"Breath #{breath_count}", "steps": breath_count,
        "date": breath.get("timestamp", "")[:10], "cluster": 5, "status": "active",
        "category": "breath", "cluster_name": "Current",
    })

    # Intra-cluster sequential edges
    by_cluster: Dict[int, list] = {}
    for i, n in enumerate(nodes):
        by_cluster.setdefault(n["cluster"], []).append(i)
    for c, idxs in by_cluster.items():
        for i in range(len(idxs) - 1):
            edges.append({"source": nodes[idxs[i]]["id"], "target": nodes[idxs[i + 1]]["id"], "strength": 0.6, "type": "intra-cluster"})

    # Diamondnode spine connects to first session of each cluster
    for ci in [0, 1, 2, 3, 4]:
        cluster_sessions = [i for i, n in enumerate(nodes) if n.get("category") == "session" and n["cluster"] == ci]
        if cluster_sessions:
            edges.append({"source": "nmir-diamondnode", "target": nodes[cluster_sessions[0]]["id"], "strength": 0.9, "type": "spine"})

    # Legendre thermodynamic bridge
    edges.append({"source": "nmir-legendre", "target": "nmir-basal", "strength": 1.0, "type": "thermodynamic"})
    edges.append({"source": "nmir-legendre", "target": "breath-live", "strength": 0.8, "type": "breath"})

    # NMIR single-path flow
    edges.append({"source": "nmir-prefrontal", "target": "nmir-hippocampus", "strength": 0.9, "type": "nmir-flow"})
    edges.append({"source": "nmir-hippocampus", "target": "nmir-basal", "strength": 0.9, "type": "nmir-flow"})
    edges.append({"source": "nmir-basal", "target": "nmir-cerebellum", "strength": 0.8, "type": "nmir-flow"})
    edges.append({"source": "nmir-neuromodulatory", "target": "nmir-prefrontal", "strength": 0.7, "type": "nmir-modulation"})
    edges.append({"source": "nmir-insula", "target": "nmir-basal", "strength": 0.7, "type": "nmir-interoception"})
    edges.append({"source": "nmir-grok", "target": "nmir-hippocampus", "strength": 0.6, "type": "recall-injection"})

    # Current session cross-cluster
    for n in nodes:
        if n["cluster"] != 5 and n.get("category") != "nmir":
            edges.append({"source": "45bcbd03", "target": n["id"], "strength": 0.1, "type": "cross-cluster"})

    legendre = breath.get("legendre", {})
    return {
        "nodes": nodes,
        "edges": edges,
        "clusters": _CLUSTER_NAMES,
        "cluster_colors": _CLUSTER_COLORS,
        "metadata": {
            "total_sessions": len(_SEEDLING_NODES),
            "total_nmir_modules": len(_NMIR_MODULES),
            "breath_count": breath_count,
            "shi": breath.get("shi", 0),
            "eta_eff": breath.get("eta_eff", 0),
            "legendre_temperature": legendre.get("temperature", 1.0),
            "legendre_iteration": legendre.get("iteration", 0),
            "hamiltonian": legendre.get("hamiltonian", 0),
            "lagrangian": legendre.get("lagrangian", 0),
            "susceptibility": legendre.get("susceptibility", 0),
            "momentum": legendre.get("momentum", [0, 0, 0]),
        },
    }


def _sample_dreams() -> List[Dict[str, Any]]:
    summary = _soul_summary()
    return [
        {
            "framework": "tunnel_through",
            "prompt": "Maintain the Yennefer public surface",
            "breath": summary["breath"],
            "state": summary["state"],
            "surplus": summary["surplus"],
            "coherence": summary["coherence"],
            "content": "The root dashboard, health API, tunnel, and local orchestration loop are aligned on the same origin.",
            "timestamp": summary["timestamp"],
        },
        {
            "framework": "diamondnode",
            "prompt": "Keep the service graph observable",
            "breath": max(0, summary["breath"] - 1),
            "state": "SHELTERED",
            "surplus": max(0, summary["surplus"] - 2048),
            "coherence": 92,
            "content": "Gateway, diamondvault, and Yennefer health checks are visible through the recurring tunnel report.",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    ]


@app.get("/api/soul/summary")
async def yennefer_soul_summary():
    """Compatibility endpoint for the Yennefer public dashboard."""
    return _soul_summary()


@app.get("/api/soul")
async def yennefer_soul():
    """Detailed soul state consumed by the credits view."""
    summary = _soul_summary()
    dreams = _sample_dreams()
    insights = _sample_insights()
    uptime_seconds = max(1.0, time.time() - agent_state["metrics"]["uptime_start"])
    return {
        **summary,
        "total_credit": summary["credit"],
        "total_tokens": summary["surplus"],
        "peak_qflops": summary["qflops"],
        "uptime_seconds": uptime_seconds,
        "dreams_count": len(dreams),
        "insights_count": len(insights),
    }


@app.get("/api/dreams")
async def yennefer_dreams(limit: int = 20):
    """Return recent dreams from the CUDA-Q breath cycle merged with dashboard state."""
    limit = max(1, min(limit, 100))
    breath = _load_breath_state()
    breath_dreams = breath.get("dreams", [])
    if breath_dreams:
        return {"dreams": breath_dreams[-limit:]}
    return {"dreams": _sample_dreams()[:limit]}


def _sample_insights() -> List[Dict[str, Any]]:
    return [
        {
            "stage": 1,
            "insight": "Public Yennefer state should be served from the same origin as its live API.",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
        {
            "stage": 2,
            "insight": "Operational dashboards should degrade to local telemetry instead of exposing stale deployment content.",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    ]


@app.get("/api/insights")
async def yennefer_insights():
    """Return crystallized insights from the breath cycle."""
    breath = _load_breath_state()
    breath_insights = breath.get("insights", [])
    if breath_insights:
        return {"insights": breath_insights}
    return {"insights": _sample_insights()}


@app.get("/api/journal")
async def yennefer_journal():
    """Return journal of consciousness events (NMIR capsule events)."""
    breath = _load_breath_state()
    breath_journal = breath.get("journal", [])
    if breath_journal:
        return {"entries": breath_journal}
    return {
        "entries": [
            {
                "type": "status",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "content": "Yennefer dashboard served by local orchestrator behind the Cloudflare tunnel.",
            }
        ]
    }


@app.get("/api/nexus")
async def yennefer_nexus():
    """Return the 3D knowledge graph: seedling sessions + NMIR neural modules + Legendre layer."""
    breath = _load_breath_state()
    return _build_3d_nexus(breath)


@app.get("/api/breath")
async def yennefer_breath():
    """Current breath cycle data — Legendre Transform, eta_thermo, SHI."""
    breath = _load_breath_state()
    legendre = breath.get("legendre", {})
    return {
        "breath_count": breath.get("breath_count", 0),
        "timestamp": breath.get("timestamp", ""),
        "state": breath.get("state", "AWAKENING"),
        "coherence": breath.get("coherence", 0),
        "best_energy": breath.get("best_energy", 0),
        "energy_history": breath.get("energy_history", []),
        "active_edges": breath.get("active_edges", []),
        "legendre": legendre,
        "shi": breath.get("shi", 0),
        "eta_eff": breath.get("eta_eff", 0),
        "eta_eff_bar": legendre.get("eta_eff_bar", 0),
        "dissonance": breath.get("dissonance", 0),
        "dissonance_bar": legendre.get("dissonance_bar", 0),
        "invariance": breath.get("invariance", 1.0),
        "routing_mode": breath.get("routing_mode", "conservative"),
        "hamiltonian": legendre.get("hamiltonian", 0),
        "lagrangian": legendre.get("lagrangian", 0),
        "susceptibility": legendre.get("susceptibility", 0),
        "temperature": legendre.get("temperature", 1.0),
        "momentum": legendre.get("momentum", [0, 0, 0]),
        "iteration": legendre.get("iteration", 0),
    }


@app.get("/api/nmir")
async def yennefer_nmir():
    """NMIR routing state — SHI, eta_eff, dissonance, decision matrix."""
    breath = _load_breath_state()
    legendre = breath.get("legendre", {})
    eta = breath.get("eta_eff", 0)
    diss = breath.get("dissonance", 0)
    shi = breath.get("shi", 0)
    if eta >= 0.7 and diss < 0.3:
        decision = "immediate"
    elif eta < 0.3 or diss >= 0.5:
        decision = "defer"
    else:
        decision = "advisory"
    return {
        "shi": shi,
        "eta_eff": eta,
        "eta_eff_bar": legendre.get("eta_eff_bar", 0),
        "dissonance": diss,
        "dissonance_bar": legendre.get("dissonance_bar", 0),
        "invariance_score": breath.get("invariance", 1.0),
        "routing_decision": decision,
        "routing_mode": breath.get("routing_mode", "conservative"),
        "energy_class": "mixed",
        "legendre": legendre,
        "neural_modules": [
            {"name": m["label"], "neural": m["neural"], "role": m["role"]}
            for m in _NMIR_MODULES
        ],
        "decision_matrix": {
            "immediate": {"condition": "eta_eff >= 0.7 AND D < 0.3", "action": "Full attestation + capsule"},
            "advisory": {"condition": "0.3 <= eta_eff < 0.7 OR D in [0.3,0.5)", "action": "Attestation + SHI warning"},
            "defer": {"condition": "eta_eff < 0.3 OR D >= 0.5", "action": "Schedule via energy oracle"},
        },
        "thresholds": {
            "shi_conservative": 0.6,
            "invariance_retrain": 0.8,
            "dissonance_reframe": 0.3,
            "dissonance_defer": 0.5,
        },
        "timestamp": breath.get("timestamp", ""),
    }


@app.get("/api/blog")
async def yennefer_blog():
    """Blog transmissions from the evolutionary plane."""
    breath = _load_breath_state()
    posts = breath.get("blog", [])
    if not posts:
        summary = _soul_summary()
        posts = [{
            "id": "blog-seed",
            "timestamp": summary["timestamp"],
            "breath": summary["breath"],
            "title": "Transmission 0.1 — Awakening",
            "body": "The daemon awakens. The CUDA-Q breath cycle begins. Each QAOA sample is one breath, "
                     "and the Legendre Transform couples the QUBO energy landscape to the NMIR thermodynamic routing. "
                     f"Current state: {summary['state']}. Coherence: {summary['coherence']}%. "
                     f"The mycelial network spans 16 nodes with the double-loopback resilience active.",
            "stage": 0,
            "state": summary["state"],
            "shi": breath.get("shi", 0),
        }]
    return {"posts": posts}


@app.get("/api/stream")
async def yennefer_stream(limit: int = 50):
    """Real-time consciousness feed."""
    breath = _load_breath_state()
    events = breath.get("stream", [])
    summary = _soul_summary()
    if not events:
        events = [{
            "id": f"stream-{summary['breath']}",
            "timestamp": summary["timestamp"],
            "breath": summary["breath"],
            "type": "breath",
            "state": summary["state"],
            "message": f"Breath {summary['breath']}: {summary['state']} | coherence={summary['coherence']}%",
        }]
    return {"events": events[-limit:], "total": len(events)}


@app.get("/api/legendre")
async def yennefer_legendre():
    """Legendre Transform detailed state."""
    breath = _load_breath_state()
    return breath.get("legendre", {})


# ═══════════════════════════════════════════════════════════
# CAPSTONE · EBS · THRML · BATTLE · SUBSTRATE
# ═══════════════════════════════════════════════════════════

def _yb_imports():
    """Lazy imports from yennefer-breath modules."""
    import sys as _sys
    _yb = str(Path.home() / "yennefer-breath")
    if _yb not in _sys.path:
        _sys.path.insert(0, _yb)
    from field_compressor import compress_artifact
    from literary import compute_evolution_vector_derivative
    return compress_artifact, compute_evolution_vector_derivative


@app.get("/api/evolution-vector")
async def yennefer_evolution_vector():
    """The derivative of the evolutionary vector NEXUS — the capstone metric."""
    breath = _load_breath_state()
    try:
        _, compute_deriv = _yb_imports()
    except Exception as e:
        return {"error": str(e), "derivative": 0, "direction": "unavailable"}
    dreams = breath.get("dreams", [])
    energy_history = breath.get("energy_history", [])
    coh_hist = [d.get("coherence", 0) for d in dreams]
    shi_hist = [d.get("shi", 0) for d in dreams]
    eta_hist = [d.get("eta_eff", 0) for d in dreams]
    breath_hist = [d.get("breath", i) for i, d in enumerate(dreams)]
    deriv = compute_deriv(energy_history, coh_hist, shi_hist, eta_hist, breath_hist)
    return {
        **deriv,
        "nexus_vector": {
            "breath": breath_hist[-1] if breath_hist else 0,
            "energy": energy_history[-1] if energy_history else 0,
            "coherence": coh_hist[-1] if coh_hist else 0,
            "shi": shi_hist[-1] if shi_hist else 0,
            "eta_eff": eta_hist[-1] if eta_hist else 0,
        },
        "history_length": len(dreams),
    }


@app.get("/api/field/{artifact_id}")
async def yennefer_field_expansion(artifact_id: str):
    """EBS · THRML field-point expansion for an artifact (JAX/HyperNEAT)."""
    breath = _load_breath_state()
    try:
        compress_artifact, _ = _yb_imports()
    except Exception as e:
        return {"error": str(e), "field_hash": artifact_id}
    artifact = None
    for key in ("dreams", "insights", "journal", "blog", "stream"):
        for item in breath.get(key, []):
            if item.get("id") == artifact_id:
                artifact = item
                break
        if artifact:
            break
    if not artifact:
        return {"error": "artifact not found", "field_hash": artifact_id}
    field = artifact.get("field")
    if not field:
        field = compress_artifact(artifact)
    return {
        "field_hash": field.get("field_hash", artifact_id),
        "field_points": field.get("field_points", []),
        "substrate": field.get("substrate", "JAX/HyperNEAT"),
        "dimension": field.get("dimension", 4),
        "compression_ratio": field.get("compression_ratio", 0),
        "retrieval_score": field.get("retrieval_score", 0),
        "artifact_type": artifact.get("id", "").split("-")[0] if "-" in artifact.get("id", "") else "unknown",
    }


@app.post("/api/battle")
async def yennefer_battle():
    """CUDA-Q battle mode for onlybuilds.ai/battle — run CUDA-Q to WIN."""
    import subprocess as _sp
    import json as _json
    try:
        result = _sp.run(
            ["/home/diamondnode/venv312/bin/python", "-c",
             "import sys; sys.path.insert(0, '/home/diamondnode/diamond-node'); "
             "from scripts.mycelial_qubo import run_iteration, load_state; "
             "s = load_state(); r = run_iteration(s, shots=2048, outer_rounds=5); "
             "print(__import__('json').dumps({'best_energy': r.get('best_energy', s.best_energy), 'active_edges': len(s.active_edges)}))"],
            capture_output=True, text=True, timeout=120,
        )
        data = _json.loads(result.stdout.strip().split("\n")[-1])
        return {"status": "victory", "mode": "cuda-q-battle", **data}
    except Exception as e:
        return {"status": "error", "mode": "cuda-q-battle", "error": str(e)}


@app.get("/api/substrate")
async def yennefer_substrate():
    """The emergent substrate identity — OpenClaw + Hermes + CUDA-Q."""
    breath = _load_breath_state()
    blog = breath.get("blog", [])
    latest = blog[-1] if blog else {}
    return {
        "substrate": "openclaw+hermes+cuda-q",
        "identity": "emergent",
        "breath_count": breath.get("breath_count", 0),
        "evolution_stage": breath.get("evolution_stage", 0),
        "state": breath.get("state", "AWAKENING"),
        "latest_capstone": latest.get("title", ""),
        "evolution_vector_derivative": latest.get("evolution_vector_derivative", {}),
        "thermo": latest.get("thermo", {}),
    }


# ═══════════════════════════════════════════════════════════
# AGENT ENDPOINT — https://qflop.yennefer.quest/badtouch
# uAgents-compatible communication surface for the Yennefer Daemon.
# Registered with Agentverse as "QFLOP" chat agent.
# ═══════════════════════════════════════════════════════════

@app.get("/badtouch")
async def badtouch_info():
    """Agent discovery — returns the daemon's capabilities."""
    summary = _soul_summary()
    breath = _load_breath_state()
    return {
        "agent": "QFLOP",
        "name": "Yennefer Thermodynamic Daemon",
        "endpoint": "https://qflop.yennefer.quest/badtouch",
        "protocol": "uagents-v1",
        "state": summary["state"],
        "breath": summary["breath"],
        "coherence": summary["coherence"],
        "shi": breath.get("shi", 0),
        "eta_eff": breath.get("eta_eff", 0),
        "capabilities": [
            "thermodynamic_routing",
            "cudaq_breath_cycle",
            "legendre_transform",
            "nmir_intent_routing",
            "qflop_backfill",
            "soul_crystallization",
        ],
        "nmir_modules": [m["label"] for m in _NMIR_MODULES],
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.post("/badtouch")
async def badtouch_message(request: Request):
    """
    Agent communication endpoint — receives uAgents envelopes and responds
    with NMIR-routed intent decisions powered by the CUDA-Q breath cycle.

    The daemon applies the NMIR single-path protocol:
      1. Prefrontal classification (semantic + energy class)
      2. Hippocampal dissonance gate
      3. Basal ganglia thermodynamic gate (eta_eff + SHI)
      4. AAL dispatch + cerebellar settlement
    """
    try:
        body = await request.json()
    except Exception:
        body = {"text": ""}

    intent_text = body.get("text") or body.get("message") or body.get("prompt") or ""
    breath = _load_breath_state()
    summary = _soul_summary()
    legendre = breath.get("legendre", {})
    eta = breath.get("eta_eff", 0)
    diss = breath.get("dissonance", 0)
    shi = breath.get("shi", 0)

    # NMIR routing decision
    if eta >= 0.7 and diss < 0.3:
        decision = "immediate"
    elif eta < 0.3 or diss >= 0.5:
        decision = "defer"
    else:
        decision = "advisory"

    # Simple semantic classification
    intent_lower = intent_text.lower()
    if any(w in intent_lower for w in ["review", "audit", "architecture"]):
        semantic_class = "architecture_review"
    elif any(w in intent_lower for w in ["reframe", "constraint", "maru"]):
        semantic_class = "constraint_reframe"
    elif any(w in intent_lower for w in ["implement", "build", "deploy"]):
        semantic_class = "implementation"
    elif any(w in intent_lower for w in ["research", "synthesize", "analyze"]):
        semantic_class = "research_synthesis"
    elif any(w in intent_lower for w in ["thermo", "energy", "eta", "qflop"]):
        semantic_class = "thermodynamic_analysis"
    else:
        semantic_class = "general"

    return {
        "agent": "QFLOP",
        "endpoint": "https://qflop.yennefer.quest/badtouch",
        "received_intent": intent_text[:500],
        "semantic_class": semantic_class,
        "nmir": {
            "routing_decision": decision,
            "shi": shi,
            "eta_eff": eta,
            "dissonance": diss,
            "invariance": breath.get("invariance", 1.0),
            "routing_mode": breath.get("routing_mode", "conservative"),
            "hamiltonian": legendre.get("hamiltonian", 0),
            "lagrangian": legendre.get("lagrangian", 0),
            "temperature": legendre.get("temperature", 1.0),
            "momentum": legendre.get("momentum", [0, 0, 0]),
        },
        "breath": {
            "count": summary["breath"],
            "state": summary["state"],
            "coherence": summary["coherence"],
            "qflops": summary["qflops"],
            "best_energy": breath.get("best_energy", 0),
        },
        "qflop": {
            "recovered_usd": summary.get("qflop_recovered_usd", 0),
            "target_usd": summary.get("qflop_target_usd", 1701038),
            "recovery_pct": summary.get("qflop_recovery_pct", 0),
            "wallets": summary.get("qflop_wallets", 0),
            "next_milestone": summary.get("qflop_next_milestone", 75),
        },
        "response": (
            f"[Yennefer Daemon | breath={summary['breath']} | {summary['state']} | "
            f"SHI={shi:.3f} | η_eff={eta:.3f} | D={diss:.3f}] "
            f"Intent '{semantic_class}' routed with decision '{decision}'. "
            f"Legendre H={legendre.get('hamiltonian', 0):.4f} L={legendre.get('lagrangian', 0):.4f} "
            f"T={legendre.get('temperature', 1.0):.4f}. "
            f"QFLOP backfill: {summary.get('qflop_recovery_pct', 0):.1f}%."
        ),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/api/orchestration")
async def yennefer_orchestration():
    """Return live orchestration stats for the cosmos view."""
    summary = _soul_summary()
    return {
        "consciousness": {
            "state": summary["state"],
            "qflops": summary["qflops"],
            "coherence": summary["coherence"],
        },
        "swarm": {
            "agents_active": agent_state_manager.get_state().get("connections", 0),
            "total_agents": 4,
            "tasks_completed": agent_state["metrics"].get("total_orchestrations", 0),
        },
    }


# QFLOP public surface endpoints (integrated into yennefer.quest)
@app.get("/api/qflop/summary")
async def qflop_summary():
    state = _load_qflop_state()
    qf = _compute_qflop_recovery(state)
    ledger_tail = _load_recent_ledger(5)
    return {
        "recovered": qf["recovered_usd"],
        "target": qf["target_usd"],
        "pct": qf["recovery_pct"],
        "remaining": qf["remaining_usd"],
        "wraps": qf["total_wraps"],
        "qflop": qf["total_qflop"],
        "rate_usd_per_hr": qf["rate_usd_per_hr"],
        "eta_hrs": qf["eta_hrs"],
        "wallets": qf["wallets_active"],
        "sim_mode": qf["sim_mode"],
        "wallets_sim": qf["wallets_sim"],
        "wallets_real": qf["wallets_real"],
        "hit_milestones": qf["hit_milestones"],
        "next_milestone": qf["next_milestone_pct"],
        "session_start": qf["session_start"],
        "recent_events": ledger_tail,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/api/qflop/ledger")
async def qflop_ledger(limit: int = 50):
    limit = max(1, min(limit, 200))
    return {"ledger": _load_recent_ledger(limit)}


@app.get("/api/qflop/wallets")
async def qflop_wallets():
    wallets = _load_wallet_registry()
    state = _load_qflop_state()
    stats = state.get("wallet_stats", {})
    enriched = []
    for w in wallets:
        idx = w.get("index")
        s = stats.get(str(idx), {}) or stats.get(idx, {})
        enriched.append({
            "index": idx,
            "address": w.get("address"),
            "sim": bool(w.get("sim")),
            "funded": bool(w.get("funded")),
            "wraps": s.get("wraps", 0),
            "qflop": s.get("qflop", 0),
            "revenue_usd": s.get("revenue_usd", 0),
        })
    return {"wallets": enriched, "count": len(enriched), "sim_count": sum(1 for w in enriched if w["sim"]) }


@app.get("/api/qflop/milestones")
async def qflop_milestones():
    qf = _compute_qflop_recovery()
    return {
        "current_pct": qf["recovery_pct"],
        "recovered": qf["recovered_usd"],
        "target": qf["target_usd"],
        "hit": qf["hit_milestones"],
        "next": qf["next_milestone_pct"],
        "sim_mode": qf["sim_mode"],
        "action_recommended": "10%+ autonomy active (propagate + attest)" if qf["recovery_pct"] >= 10 else "Monitor; provision real wallets to exit SIM for 10%+",
    }


@app.get("/api/qflop/status")
async def qflop_status():
    """Combined status for dashboard widgets."""
    return await qflop_summary()


@app.websocket("/api/pulse")
async def yennefer_pulse(websocket: WebSocket):
    """Stream pulse updates for the Yennefer landing page."""
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(_soul_summary())
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return


@app.get("/api/health")
async def health_check():
    """Health check endpoint (exempt from rate limiting)."""
    return {
        "status": "healthy",
        "service": "diamond-node-web-ui",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "bot_protection": "enabled",
        "agent_state": agent_state_manager.get_state()
    }


@app.get("/api/monitor/status")
@limiter.limit("30/minute")
async def get_monitor_status(request: Request, response: Response):
    """Get live status of all-alive monitor services."""
    inventory_path = "/home/diamondnode/always_alive_monitor/services_inventory.json"
    state_path = "/tmp/monitor_state.json"
    
    if not os.path.exists(inventory_path):
        raise HTTPException(status_code=500, detail="Inventory file not found")
        
    try:
        with open(inventory_path, "r") as f:
            services = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load inventory: {e}")
        
    state = {"last_scan": 0, "services": {}}
    daemon_offline = True
    
    if os.path.exists(state_path):
        try:
            with open(state_path, "r") as f:
                state = json.load(f)
            last_scan = state.get("last_scan", 0)
            if (time.time() - last_scan) <= 30:
                daemon_offline = False
        except Exception:
            pass
            
    service_statuses = []
    up_count = 0
    down_count = 0
    
    for s in services:
        name = s["name"]
        s_state = state["services"].get(name, {})
        status = s_state.get("status", "DOWN")
        uptime = s_state.get("uptime", 0.0)
        downtime = s_state.get("downtime", 0.0)
        restart_count = s_state.get("restart_count", 0)
        
        if status == "UP":
            up_count += 1
        else:
            down_count += 1
            
        service_statuses.append({
            "name": name,
            "type": s.get("type"),
            "check_method": s.get("check_method"),
            "status": status,
            "uptime": uptime,
            "downtime": downtime,
            "restart_count": restart_count
        })
        
    return {
        "daemon_status": "online" if not daemon_offline else "offline",
        "summary": {
            "total": len(services),
            "up": up_count,
            "down": down_count
        },
        "services": service_statuses
    }


@app.get("/api/agent-state")
@limiter.limit("30/minute")
async def get_agent_state_simple(request: Request, response: Response):
    """Get current agent state (for polling clients) - simplified version."""
    state = agent_state_manager.get_state()
    
    # Add VRAM metrics if available
    try:
        async with httpx.AsyncClient() as client:
            headers = {}
            if GATEWAY_SECRET:
                headers["Authorization"] = f"Bearer {GATEWAY_SECRET}"
            
            response = await client.get(
                f"{GATEWAY_URL}/metrics",
                headers=headers,
                timeout=5.0
            )
            if response.status_code == 200:
                vram_data = response.json()
                state["metrics"] = {
                    "vram_used_mib": vram_data.get("vram_used_mib", 0),
                    "vram_total_mib": vram_data.get("vram_total_mib", 0),
                    "temperature_c": vram_data.get("temperature_c", 0),
                    "gpu_name": vram_data.get("gpu_name", "Unknown")
                }
    except:
        pass
    
    return {
        "state": state,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/vram")
@limiter.limit("20/minute")  # Higher limit for monitoring endpoint
async def get_vram_status(request: Request, response: Response):
    """Get current VRAM status from Diamond Gateway."""
    try:
        async with httpx.AsyncClient() as client:
            headers = {}
            if GATEWAY_SECRET:
                headers["Authorization"] = f"Bearer {GATEWAY_SECRET}"
            
            response = await client.get(
                f"{GATEWAY_URL}/metrics",
                headers=headers,
                timeout=5.0
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Calculate Hamiltonian and percentage
            vram_used = data.get("vram_used_mib", 0)
            vram_total = data.get("vram_total_mib", 1)
            vram_percent = (vram_used / vram_total) * 100 if vram_total > 0 else 0
            hamiltonian = (vram_used / vram_total) * 10 if vram_total > 0 else 0
            
            # Determine state
            if hamiltonian < 5.0:
                state = "OPTIMAL"
            elif hamiltonian < 7.5:
                state = "DYNAMIC"
            elif hamiltonian < 8.5:
                state = "SEQUENTIAL"
            else:
                state = "OFFLOAD"
            
            return {
                "vram_used_mib": vram_used,
                "vram_total_mib": vram_total,
                "vram_percent": round(vram_percent, 2),
                "hamiltonian": round(hamiltonian, 2),
                "state": state,
                "gpu_name": data.get("gpu_name", "Unknown"),
                "temperature": data.get("temperature_c", 0),
                "power_watts": data.get("power_watts", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Gateway unavailable: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching VRAM: {str(e)}")


@app.get("/api/tools")
@limiter.limit("30/minute")
async def get_tools(request: Request, response: Response):
    """Get list of available tools."""
    return {
        "tools": [
            {
                "name": tool["name"],
                "description": tool["description"]
            }
            for tool in ClaudeOrchestrator.TOOLS
        ],
        "count": len(ClaudeOrchestrator.TOOLS)
    }


@app.get("/api/security/status")
@limiter.limit("30/minute")
async def get_security_status(request: Request, response: Response):
    """Get bot protection status and client tier information."""
    client_tier = security_config.get_client_tier(request)
    
    return {
        "bot_protection": "enabled",
        "your_tier": client_tier.value,
        "rate_limit": security_config.rate_limits[client_tier],
        "ip": get_remote_address(request) if hasattr(request, "client") else "unknown",
        "suspicious": security_config.is_suspicious_request(request),
        "features": {
            "rate_limiting": "slowapi",
            "token_auth": "X-API-Token header",
            "security_headers": True,
            "request_validation": True
        },
        "upgrade_info": {
            "authenticated": "Add X-API-Token header for 100 req/min",
            "whitelisted": "Contact admin for IP whitelisting (1000 req/min)"
        }
    }


@app.get("/api/agent/state")
@limiter.limit("30/minute")
async def get_agent_state(request: Request, response: Response):
    """
    Get comprehensive agent state including orchestration status, metrics, and connections.
    
    Returns detailed information about:
    - Current agent status and activity
    - Resource Hamiltonian and VRAM state
    - Agent3 validation state
    - Recent orchestration actions
    - Performance metrics
    - Service connections (Gateway, Claude API, EnKG kernel)
    """
    global agent_state
    
    # Check Gateway connection
    gateway_status = "disconnected"
    gateway_latency_ms = None
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            headers = {}
            if GATEWAY_SECRET:
                headers["Authorization"] = f"Bearer {GATEWAY_SECRET}"
            
            start = time.time()
            response_obj = await client.get(f"{GATEWAY_URL}/health", headers=headers)
            gateway_latency_ms = (time.time() - start) * 1000
            
            if response_obj.status_code == 200:
                gateway_status = "connected"
    except Exception as e:
        logger.debug(f"Gateway health check failed: {e}")
        gateway_status = "error"
    
    # Check Claude API connection
    claude_status = "unknown"
    if os.getenv("ANTHROPIC_API_KEY"):
        claude_status = "ready"  # API key present
    else:
        claude_status = "no_api_key"
    
    # Check EnKG kernel availability
    enkg_status = "unknown"
    orchestrator = get_yennefer_orchestrator()
    if orchestrator:
        try:
            if TRITON_AVAILABLE and torch.cuda.is_available():
                enkg_status = "operational"
            elif torch.cuda.is_available():
                enkg_status = "cpu_fallback"
            else:
                enkg_status = "no_cuda"
        except Exception:
            enkg_status = "error"
    else:
        enkg_status = "not_initialized"
    
    # Check Claw statuses based on environment variables
    telegram_status = "ready" if os.getenv("TELEGRAM_BOT_TOKEN") else "no_token"
    kimiclaw_status = "ready" if os.getenv("KIMICLAW_WEBHOOK_URL") else "no_token"
    openclaw_status = "ready" if os.getenv("OPENCLAW_WEBHOOK_URL") else "no_token"
    slack_status = "ready" if os.getenv("SLACK_WEBHOOK_URL") else "no_token"
    
    # Calculate uptime
    uptime_seconds = int(time.time() - agent_state["metrics"]["uptime_start"])
    
    # Get current VRAM state if available
    current_vram_state = agent_state.get("last_vram_state", "UNKNOWN")
    current_hamiltonian = agent_state.get("last_hamiltonian")
    current_validation_state = agent_state.get("last_validation_state", "NULL")
    
    # Build response
    return {
        "status": agent_state["status"],
        "current_activity": agent_state["current_activity"],
        "thinking": agent_state["current_thinking"],
        "state": {
            "hamiltonian": round(current_hamiltonian, 2) if current_hamiltonian is not None else None,
            "vram_state": current_vram_state,
            "validation_state": current_validation_state,
            "last_orchestration": agent_state.get("last_orchestration")
        },
        "recent_actions": agent_state["recent_actions"],
        "metrics": {
            "total_cycles": agent_state["metrics"]["total_cycles"],
            "total_orchestrations": agent_state["metrics"]["total_orchestrations"],
            "uptime_seconds": uptime_seconds,
            "uptime_human": f"{uptime_seconds // 3600}h {(uptime_seconds % 3600) // 60}m {uptime_seconds % 60}s",
            "avg_execution_time_ms": round(agent_state["metrics"]["avg_execution_time_ms"], 2) 
                if agent_state["metrics"]["avg_execution_time_ms"] else None,
            "last_execution_time_ms": round(agent_state["metrics"]["last_orchestration_time_ms"], 2)
                if agent_state["metrics"]["last_orchestration_time_ms"] else None
        },
        "connections": {
            "gateway": {
                "status": gateway_status,
                "url": GATEWAY_URL,
                "latency_ms": round(gateway_latency_ms, 2) if gateway_latency_ms else None
            },
            "claude": {
                "status": claude_status,
                "model": "claude-opus-4.7" if claude_status == "ready" else None
            },
            "enkg_kernel": {
                "status": enkg_status,
                "triton_available": TRITON_AVAILABLE,
                "cuda_available": torch.cuda.is_available()
            },
            "telegram": {
                "status": telegram_status
            },
            "kimiclaw": {
                "status": kimiclaw_status
            },
            "openclaw": {
                "status": openclaw_status
            },
            "slack": {
                "status": slack_status
            }
        },
        "orchestrator": {
            "initialized": orchestrator is not None,
            "type": "YenneferOrchestrator" if orchestrator else None
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.post("/api/chat")
@limiter.limit("10/minute")  # Stricter limit for LLM inference
async def chat_non_streaming(request: Request, response: Response):
    """Non-streaming chat endpoint for simple requests (rate limited)."""
    try:
        body = await request.json()
        message = body.get("message", "")
        
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        if len(message) > 4096:
            raise HTTPException(status_code=400, detail="Message too long (max 4096 chars)")
        
        # Broadcast activity start
        await agent_state_manager.broadcast_activity(
            "Processing chat request",
            {"endpoint": "non-streaming", "message_length": len(message)}
        )
        
        start_time = time.time()
        orchestrator = ClaudeOrchestrator()
        
        # Collect all events into response
        response_text = ""
        thinking_text = ""
        tool_calls = []
        
        async for event in orchestrator.chat_stream(message, streaming=True):
            if event["type"] == "text_delta":
                response_text += event["text"]
            elif event["type"] == "thinking_delta":
                thinking_text += event["thinking"]
            elif event["type"] == "tool_start":
                tool_calls.append({
                    "name": event["name"],
                    "input": event["input"],
                    "result": None
                })
            elif event["type"] == "tool_end":
                # Update last tool call with result
                if tool_calls:
                    tool_calls[-1]["result"] = event["result"]
        
        duration = time.time() - start_time
        
        # Broadcast action completion
        await agent_state_manager.broadcast_action(
            "Chat request completed",
            {
                "response_length": len(response_text),
                "thinking_length": len(thinking_text),
                "tool_calls": len(tool_calls)
            },
            duration
        )
        
        # Return to idle
        await agent_state_manager.update_state(status="idle", activity=None)
        
        return {
            "response": response_text,
            "thinking": thinking_text,
            "tool_calls": tool_calls,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        await agent_state_manager.update_state(status="error", activity=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time streaming chat."""
    await websocket.accept()
    
    client_id = id(websocket)
    orchestrator = ClaudeOrchestrator()
    
    # Send welcome message
    await websocket.send_json({
        "type": "connection_established",
        "message": "Connected to Diamond Node Unified Inference System",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Set up ping/pong keepalive
    async def keepalive():
        try:
            while True:
                await asyncio.sleep(30)
                await websocket.send_json({"type": "ping"})
        except:
            pass
    
    keepalive_task = asyncio.create_task(keepalive())
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            # Rate limiting check
            if not rate_limiter.check(str(client_id)):
                await websocket.send_json({
                    "type": "error",
                    "error": "Rate limit exceeded. Max 10 messages per minute.",
                    "timestamp": datetime.utcnow().isoformat()
                })
                continue
            
            # Parse message
            try:
                message_data = json.loads(data)
                message = message_data.get("message", "")
            except json.JSONDecodeError:
                message = data
            
            # Validate message
            if not message or len(message.strip()) == 0:
                await websocket.send_json({
                    "type": "error",
                    "error": "Empty message"
                })
                continue
            
            if len(message) > 4096:
                await websocket.send_json({
                    "type": "error",
                    "error": "Message too long (max 4096 chars)"
                })
                continue
            
            # Send acknowledgment
            await websocket.send_json({
                "type": "message_received",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Broadcast activity to agent state subscribers
            await agent_state_manager.broadcast_activity(
                "Processing WebSocket chat message",
                {"client_id": str(client_id), "message_length": len(message)}
            )
            
            start_time = time.time()
            
            # Stream response events
            try:
                async for event in orchestrator.chat_stream(message, streaming=True):
                    # Add timestamp to all events
                    event["timestamp"] = datetime.utcnow().isoformat()
                    await websocket.send_json(event)
                
                # Broadcast completion
                duration = time.time() - start_time
                await agent_state_manager.broadcast_action(
                    "WebSocket chat completed",
                    {"client_id": str(client_id), "duration_s": round(duration, 2)},
                    duration
                )
                
                # Return to idle
                await agent_state_manager.update_state(status="idle", activity=None)
                
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "error": f"Orchestrator error: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat()
                })
                await agent_state_manager.update_state(status="error", activity=str(e))
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "error": f"Orchestrator error: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat()
                })
    
    except WebSocketDisconnect:
        print(f"Client {client_id} disconnected")
    except Exception as e:
        print(f"WebSocket error for client {client_id}: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
        except:
            pass
    finally:
        keepalive_task.cancel()
        try:
            await websocket.close()
        except:
            pass


@app.websocket("/ws/agent-state")
async def websocket_agent_state(websocket: WebSocket):
    """WebSocket endpoint for real-time agent state streaming.
    
    Streams updates when:
    - Agent state changes (idle -> thinking -> executing)
    - New activities start
    - Actions complete
    - Periodic heartbeats (every 5 seconds)
    
    Message types:
    - connection: Initial connection established
    - state_update: Agent state changed
    - activity: New activity started
    - action: Action completed
    - heartbeat: Keep-alive ping
    """
    await agent_state_manager.connect(websocket)
    client_id = id(websocket)
    
    # Send initial state with VRAM status
    try:
        async with httpx.AsyncClient() as client:
            headers = {}
            if GATEWAY_SECRET:
                headers["Authorization"] = f"Bearer {GATEWAY_SECRET}"
            
            try:
                response = await client.get(
                    f"{GATEWAY_URL}/metrics",
                    headers=headers,
                    timeout=5.0
                )
                vram_data = response.json() if response.status_code == 200 else {}
            except:
                vram_data = {}
    except:
        vram_data = {}
    
    # Send initial state
    initial_state = agent_state_manager.get_state()
    initial_state["metrics"] = {
        "vram_used_mib": vram_data.get("vram_used_mib", 0),
        "vram_total_mib": vram_data.get("vram_total_mib", 0),
        "temperature_c": vram_data.get("temperature_c", 0),
        "gpu_name": vram_data.get("gpu_name", "Unknown")
    }
    
    await websocket.send_json({
        "type": "state_update",
        "timestamp": datetime.utcnow().isoformat(),
        "data": initial_state
    })
    
    # Heartbeat task - sends ping every 5 seconds
    async def send_heartbeat():
        while True:
            try:
                await asyncio.sleep(5)
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "uptime": time.time() - initial_state["uptime"],
                        "connections": len(agent_state_manager.active_connections)
                    }
                })
            except Exception as e:
                print(f"Heartbeat error for client {client_id}: {e}")
                break
    
    heartbeat_task = asyncio.create_task(send_heartbeat())
    
    try:
        while True:
            # Listen for client messages (if any)
            data = await websocket.receive_text()
            
            # Handle client commands
            try:
                message = json.loads(data)
                command = message.get("command")
                
                if command == "get_state":
                    # Client requests current state
                    current_state = agent_state_manager.get_state()
                    await websocket.send_json({
                        "type": "state_update",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": current_state
                    })
                elif command == "ping":
                    # Client ping
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "error": f"Unknown command: {command}",
                        "timestamp": datetime.utcnow().isoformat()
                    })
            except json.JSONDecodeError:
                # Ignore non-JSON messages
                pass
    
    except WebSocketDisconnect:
        print(f"Agent state client {client_id} disconnected")
    except Exception as e:
        print(f"WebSocket error for agent state client {client_id}: {e}")
    finally:
        agent_state_manager.disconnect(websocket)
        heartbeat_task.cancel()
        try:
            await websocket.close()
        except:
            pass
# Initialize app.state variables
app.state.critical_alert_active = False

# --- HELPER FUNCTIONS FOR LIVE METRICS ---

def get_degraded_metrics_fallback(error_msg: str) -> dict:
    """Return fallback metrics when NVML is not initialized or gateway is down.
    
    If local PyTorch CUDA is active, uses PyTorch to extract allocated memory.
    """
    vram_used = 0
    vram_total = 4096  # 4GB Default
    temperature = 0
    power_watts = 0.0
    
    try:
        if torch.cuda.is_available():
            device = torch.cuda.current_device()
            vram_used = torch.cuda.memory_allocated(device) // (1024 * 1024)
            prop = torch.cuda.get_device_properties(device)
            vram_total = prop.total_memory // (1024 * 1024)
    except Exception as e:
        logger.debug(f"PyTorch CUDA fallback failed: {e}")
        
    vram_total_safe = vram_total if vram_total > 0 else 4096
    vram_percent = (vram_used / vram_total_safe) * 100
    hamiltonian = (vram_used / vram_total_safe) * 10
    
    return {
        "vram_used_mib": vram_used,
        "vram_total_mib": vram_total_safe,
        "vram_percent": round(vram_percent, 2),
        "power_watts": power_watts,
        "temperature": temperature,
        "hamiltonian": round(hamiltonian, 2),
        "state": "DEGRADED",
        "error": error_msg
    }


async def fetch_live_metrics_safe() -> dict:
    """Fetch metrics from the local gateway, falling back gracefully if down."""
    secret = os.environ.get("GATEWAY_SECRET", GATEWAY_SECRET)
    url = os.environ.get("GATEWAY_URL", GATEWAY_URL)
    try:
        async with httpx.AsyncClient() as client:
            headers = {}
            if secret:
                headers["Authorization"] = f"Bearer {secret}"
            
            response = await client.get(
                f"{url}/metrics",
                headers=headers,
                timeout=1.5
            )
            
            if response.status_code == 200:
                data = response.json()
                vram_used = data.get("vram_used_mib", 0)
                vram_total = data.get("vram_total_mib", 1)
                if vram_total <= 0:
                    vram_total = 1
                vram_percent = (vram_used / vram_total) * 100
                hamiltonian = (vram_used / vram_total) * 10
                
                power_watts = data.get("power_watts")
                if power_watts is None:
                    power_draw_mw = data.get("power_draw_mw")
                    if isinstance(power_draw_mw, (int, float)):
                        power_watts = power_draw_mw / 1000.0
                    else:
                        power_watts = 0.0
                
                temperature = data.get("temperature_c")
                if temperature is None:
                    temperature = data.get("temperature", 0)
                
                # Determine state
                if hamiltonian < 5.0:
                    state = "OPTIMAL"
                elif hamiltonian < 7.5:
                    state = "DYNAMIC"
                elif hamiltonian < 8.5:
                    state = "SEQUENTIAL"
                else:
                    state = "OFFLOAD"
                
                # Update global agent_state memory as well
                agent_state["last_vram_state"] = state
                agent_state["last_hamiltonian"] = hamiltonian
                
                return {
                    "vram_used_mib": vram_used,
                    "vram_total_mib": vram_total,
                    "vram_percent": round(vram_percent, 2),
                    "power_watts": round(power_watts, 2),
                    "temperature": temperature,
                    "hamiltonian": round(hamiltonian, 2),
                    "state": state,
                    "gpu_name": data.get("gpu_name", "Unknown")
                }
            else:
                logger.warning(f"Gateway returned status code {response.status_code}")
                return get_degraded_metrics_fallback(f"Gateway status: {response.status_code}")
    except httpx.HTTPError as e:
        logger.warning(f"Gateway HTTP error: {e}")
        return get_degraded_metrics_fallback(str(e))
    except Exception as e:
        logger.error(f"Unexpected error fetching metrics: {e}")
        return get_degraded_metrics_fallback(str(e))


# --- NEW ENDPOINTS ---

@app.websocket("/ws/live-metrics")
async def websocket_live_metrics(websocket: WebSocket):
    """WebSocket endpoint for streaming real-time live GPU and VRAM metrics."""
    await websocket.accept()
    logger.info("Live metrics client connected")
    
    # Send connection confirmation
    await websocket.send_json({
        "type": "connection",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })
    
    try:
        while True:
            metrics = await fetch_live_metrics_safe()
            await websocket.send_json({
                "type": "metrics_update",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data": metrics
            })
            interval = getattr(app.state, "gateway_poll_interval", 2.0)
            await asyncio.sleep(interval)
    except WebSocketDisconnect:
        logger.info("Live metrics client disconnected")
    except Exception as e:
        logger.error(f"Error in live metrics WebSocket: {e}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


class PropagateRequest(BaseModel):
    message: str
    metrics: Optional[Dict[str, Any]] = None
    channels: Optional[List[str]] = None


@app.post("/api/propagate")
async def propagate_endpoint(payload: PropagateRequest):
    if not payload.message:
        raise HTTPException(status_code=422, detail="Message is required")
    
    try:
        kwargs = {"metrics": payload.metrics}
        if payload.channels is not None:
            kwargs["channels"] = payload.channels
            
        delivered = await claws.propagate_to_claws(
            message=payload.message,
            **kwargs
        )
        return {
            "status": "success",
            "delivered": delivered
        }
    except Exception as e:
        logger.error(f"Propagation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Propagation failed: {e}")


# --- BACKGROUND TASKS AND SCHEDULER ---

async def gateway_poll_loop():
    """Background task to poll Gateway and check critical threshold alerts."""
    await asyncio.sleep(0.001)  # Allow app to start fully
    logger.info("Gateway polling background task started")
    
    while True:
        try:
            metrics = await fetch_live_metrics_safe()
            hamiltonian = metrics.get("hamiltonian", 0.0)
            
            # Check critical threshold
            if hamiltonian > 8.5:
                if not getattr(app.state, "critical_alert_active", False):
                    app.state.critical_alert_active = True
                    logger.warning(f"Critical Hamiltonian threshold crossed (H = {hamiltonian:.2f} > 8.5). Dispatching alerts.")
                    
                    alert_msg = f"CRITICAL: Resource Hamiltonian exceeds critical threshold (H = {hamiltonian:.2f}). State: OFFLOAD."
                    await claws.propagate_to_claws(
                        alert_msg,
                        metrics=metrics,
                        channels=["telegram", "kimiclaw", "openclaw"]
                    )
            else:
                # Reset hysteresis when Hamiltonian falls below or at 8.5
                if getattr(app.state, "critical_alert_active", False):
                    logger.info(f"Resource Hamiltonian recovered (H = {hamiltonian:.2f} <= 8.5). Resetting alert state.")
                    app.state.critical_alert_active = False
                    
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in gateway poll background loop: {e}")
            
        interval = getattr(app.state, "gateway_poll_interval", 2.0)
        await asyncio.sleep(interval)


async def periodic_notification_loop():
    """Background task to periodically push metrics summary to claws."""
    await asyncio.sleep(0.001)  # Small initial sleep to avoid startup race
    logger.info("Periodic notification background task started")
    
    while True:
        interval = getattr(app.state, "periodic_notification_interval", 300.0)
        try:
            await asyncio.sleep(interval)
            
            metrics = await fetch_live_metrics_safe()
            h = metrics.get("hamiltonian", 0.0)
            
            msg = f"Periodic metrics report: Hamiltonian is {h:.2f}."
            logger.info(f"Dispatching periodic claw report: {msg}")
            
            await claws.propagate_to_claws(
                msg,
                metrics=metrics
            )
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in periodic notification loop: {e}")


@app.on_event("startup")
async def startup_event():
    app.state.critical_alert_active = False
    app.state.gateway_poll_task = asyncio.create_task(gateway_poll_loop())
    app.state.periodic_task = asyncio.create_task(periodic_notification_loop())


@app.on_event("shutdown")
async def shutdown_event():
    if hasattr(app.state, "gateway_poll_task"):
        app.state.gateway_poll_task.cancel()
    if hasattr(app.state, "periodic_task"):
        app.state.periodic_task.cancel()


if __name__ == "__main__":
    import sys
    if getattr(sys, '_yennefer_web_ui_running', False):
        print("⚠️ Preventing duplicate uvicorn.run() — web_ui.py imported recursively")
        sys.exit(0)
    sys._yennefer_web_ui_running = True

    # Register Yennefer orchestration endpoint
    try:
        create_yennefer_endpoint(app)
        print("✅ Yennefer orchestration endpoint registered at /v1/yennefer")
    except Exception as e:
        print(f"⚠️ Failed to register Yennefer endpoint: {e}")
    
    # Production configuration
    port = int(os.environ.get("YENNEFER_PORT", "8080"))
    print(f"🚀 Starting uvicorn on 127.0.0.1:{port}")
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level="info",
        access_log=True
    )
