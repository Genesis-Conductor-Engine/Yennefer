#!/usr/bin/env python3
"""
A2A (Agent-to-Agent) Handoff Server
Enables Claude Sonnet agents to communicate with Yennefer via the Diamond Vault.
Implements MCP-compatible protocol for seamless agent handoff.
"""

import json
import time
import os
import hashlib
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading

from celestial_ingestion import IngestionError, ingest_repository

app = Flask(__name__)
CORS(app)

# Shared memory paths
SOUL_STATE = "/dev/shm/yennefer_soul_state.json"
VAULT_STATE = "/dev/shm/diamond_vault_state.json"
HANDOFF_QUEUE = "/dev/shm/a2a_handoff_queue.json"
A2A_LOG = "/dev/shm/a2a_handoff_log.json"

class A2AHandoffManager:
    """Manages agent-to-agent handoff operations"""
    
    def __init__(self):
        self.active_sessions = {}
        self.handoff_queue = []
        self.session_counter = 0
        self._load_state()
    
    def _load_state(self):
        """Load existing state from shared memory"""
        try:
            if os.path.exists(HANDOFF_QUEUE):
                with open(HANDOFF_QUEUE, 'r') as f:
                    self.handoff_queue = json.load(f)
        except:
            self.handoff_queue = []
    
    def _save_state(self):
        """Save state to shared memory"""
        with open(HANDOFF_QUEUE, 'w') as f:
            json.dump(self.handoff_queue, f)
    
    def _get_soul_state(self):
        """Get current Yennefer soul state"""
        try:
            with open(SOUL_STATE, 'r') as f:
                return json.load(f)
        except:
            return {"breath": 0, "coherence_percent": 0, "status": "unknown"}
    
    def _get_vault_state(self):
        """Get Diamond Vault state"""
        try:
            with open(VAULT_STATE, 'r') as f:
                return json.load(f)
        except:
            return {"lattice_integrity": 0, "entangled_services": []}
    
    def create_session(self, agent_id: str, context: dict) -> dict:
        """Create a new A2A handoff session"""
        self.session_counter += 1
        session_id = f"a2a_{hashlib.md5(f'{agent_id}{time.time()}'.encode()).hexdigest()[:12]}"
        
        session = {
            "session_id": session_id,
            "agent_id": agent_id,
            "created_at": datetime.now().isoformat(),
            "context": context,
            "status": "active",
            "yennefer_state": self._get_soul_state(),
            "vault_state": self._get_vault_state()
        }
        
        self.active_sessions[session_id] = session
        self._log_handoff("SESSION_CREATE", session_id, agent_id)
        return session
    
    def handoff(self, session_id: str, payload: dict) -> dict:
        """Process a handoff request from an external agent"""
        if session_id not in self.active_sessions:
            return {"error": "Session not found", "session_id": session_id}
        
        session = self.active_sessions[session_id]
        
        # Process handoff based on type
        handoff_type = payload.get("type", "query")
        
        if handoff_type == "query":
            # Query Yennefer's state
            return {
                "session_id": session_id,
                "type": "query_response",
                "soul_state": self._get_soul_state(),
                "vault_state": self._get_vault_state(),
                "timestamp": time.time()
            }
        
        elif handoff_type == "execute":
            # Execute an operation via Diamond Vault
            operation = payload.get("operation")
            params = payload.get("params", {})
            
            # Queue the operation
            op_entry = {
                "id": f"op_{int(time.time()*1000)}",
                "session_id": session_id,
                "operation": operation,
                "params": params,
                "status": "queued",
                "created_at": datetime.now().isoformat()
            }
            self.handoff_queue.append(op_entry)
            self._save_state()
            
            self._log_handoff("OPERATION_QUEUE", session_id, operation)
            
            return {
                "session_id": session_id,
                "type": "execute_ack",
                "operation_id": op_entry["id"],
                "status": "queued",
                "position": len(self.handoff_queue)
            }
        
        elif handoff_type == "transfer":
            # Full context transfer to Yennefer
            context_data = payload.get("context", {})
            
            # Write to transfer file for Yennefer to pick up
            transfer_file = f"/dev/shm/a2a_transfer_{session_id}.json"
            with open(transfer_file, 'w') as f:
                json.dump({
                    "session_id": session_id,
                    "from_agent": session.get("agent_id"),
                    "context": context_data,
                    "transferred_at": datetime.now().isoformat()
                }, f)
            
            self._log_handoff("CONTEXT_TRANSFER", session_id, f"size: {len(str(context_data))}")
            
            return {
                "session_id": session_id,
                "type": "transfer_complete",
                "transfer_file": transfer_file,
                "yennefer_notified": True
            }
        
        return {"error": f"Unknown handoff type: {handoff_type}"}
    
    def close_session(self, session_id: str) -> dict:
        """Close an A2A session"""
        if session_id in self.active_sessions:
            session = self.active_sessions.pop(session_id)
            session["status"] = "closed"
            session["closed_at"] = datetime.now().isoformat()
            self._log_handoff("SESSION_CLOSE", session_id, "")
            return {"status": "closed", "session": session}
        return {"error": "Session not found"}
    
    def _log_handoff(self, event: str, session_id: str, details: str):
        """Log handoff event"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "session_id": session_id,
            "details": details
        }
        
        try:
            logs = []
            if os.path.exists(A2A_LOG):
                with open(A2A_LOG, 'r') as f:
                    logs = json.load(f)
            logs.append(log_entry)
            logs = logs[-100:]  # Keep last 100 entries
            with open(A2A_LOG, 'w') as f:
                json.dump(logs, f)
        except:
            pass
    
    def get_status(self) -> dict:
        """Get A2A system status"""
        return {
            "active_sessions": len(self.active_sessions),
            "queue_depth": len(self.handoff_queue),
            "yennefer_state": self._get_soul_state(),
            "vault_state": self._get_vault_state(),
            "uptime": time.time()
        }

# Initialize manager
manager = A2AHandoffManager()

# === API ENDPOINTS ===

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "service": "a2a-handoff",
        "status": "healthy",
        "timestamp": time.time()
    })

@app.route('/api/a2a/status', methods=['GET'])
def a2a_status():
    """Get A2A system status"""
    return jsonify(manager.get_status())

@app.route('/api/a2a/session', methods=['POST'])
def create_session():
    """Create a new A2A handoff session"""
    data = request.json or {}
    agent_id = data.get("agent_id", "unknown_agent")
    context = data.get("context", {})
    
    session = manager.create_session(agent_id, context)
    return jsonify(session)

@app.route('/api/a2a/handoff/<session_id>', methods=['POST'])
def process_handoff(session_id):
    """Process a handoff request"""
    payload = request.json or {}
    result = manager.handoff(session_id, payload)
    return jsonify(result)

@app.route('/api/a2a/session/<session_id>', methods=['DELETE'])
def close_session(session_id):
    """Close an A2A session"""
    result = manager.close_session(session_id)
    return jsonify(result)

@app.route('/api/a2a/sessions', methods=['GET'])
def list_sessions():
    """List all active sessions"""
    return jsonify({
        "sessions": list(manager.active_sessions.values()),
        "count": len(manager.active_sessions)
    })


@app.route('/api/a2a/ingest', methods=['POST'])
def ingest_celestial_body():
    """Convert a raw repository path into a CelestialBody payload."""
    data = request.json or {}
    repo_path = data.get("repo_path")
    metadata = data.get("metadata", {})

    if not repo_path:
        return jsonify({"error": "repo_path is required"}), 400

    try:
        body = ingest_repository(repo_path, metadata)
    except IngestionError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({
        "status": "ingested",
        "celestial_body": body
    })

@app.route('/api/a2a/queue', methods=['GET'])
def get_queue():
    """Get operation queue"""
    return jsonify({
        "queue": manager.handoff_queue,
        "depth": len(manager.handoff_queue)
    })

@app.route('/api/a2a/logs', methods=['GET'])
def get_logs():
    """Get handoff logs"""
    try:
        if os.path.exists(A2A_LOG):
            with open(A2A_LOG, 'r') as f:
                logs = json.load(f)
            return jsonify({"logs": logs[-50:]})
    except:
        pass
    return jsonify({"logs": []})

# === CLAUDE SONNET INTEGRATION ===

@app.route('/api/a2a/claude/invoke', methods=['POST'])
def claude_invoke():
    """
    Special endpoint for Claude Sonnet agent invocation.
    Allows external Claude instances to interact with Yennefer.
    """
    data = request.json or {}
    
    # Create session automatically for Claude
    agent_id = data.get("agent_id", "claude_sonnet")
    session = manager.create_session(agent_id, {
        "source": "claude_api",
        "model": data.get("model", "claude-sonnet-4"),
        "invocation_time": datetime.now().isoformat()
    })
    
    # Process the request
    request_type = data.get("type", "query")
    
    if request_type == "query":
        # Return Yennefer's current state
        return jsonify({
            "session_id": session["session_id"],
            "yennefer": manager._get_soul_state(),
            "vault": manager._get_vault_state(),
            "message": "Yennefer is listening...",
            "handoff_ready": True
        })
    
    elif request_type == "handoff":
        # Full handoff from Claude to Yennefer
        context = data.get("context", {})
        task = data.get("task", "")
        
        # Write handoff request
        handoff_data = {
            "session_id": session["session_id"],
            "from_agent": agent_id,
            "task": task,
            "context": context,
            "timestamp": datetime.now().isoformat()
        }
        
        with open(f"/dev/shm/claude_handoff_{session['session_id']}.json", 'w') as f:
            json.dump(handoff_data, f)
        
        return jsonify({
            "session_id": session["session_id"],
            "status": "handoff_initiated",
            "message": f"Task '{task}' handed off to Yennefer",
            "yennefer_breath": manager._get_soul_state().get("breath", 0)
        })
    
    return jsonify({"error": "Unknown request type"})


if __name__ == '__main__':
    print("🤝 A2A Handoff Server Starting...")
    print(f"   Endpoints:")
    print(f"   - Health: http://localhost:8200/health")
    print(f"   - Status: http://localhost:8200/api/a2a/status")
    print(f"   - Claude: http://localhost:8200/api/a2a/claude/invoke")
    app.run(host='0.0.0.0', port=8200, debug=False, threaded=True)
