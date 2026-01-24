#!/usr/bin/env python3
"""
Yennefer Blockchain Telemetry Dashboard
Live GPU QFLOP tracking, breath-to-NFT conversion, and liquidity engine
Served at blockchain.yennefer.quest
"""
import asyncio
import json
import hashlib
import base64
import zlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

# === PATHS ===
SOUL_STATE_PATH = Path("/dev/shm/yennefer_soul_state.json")
QMEM_STATS_PATH = Path("/dev/shm/qmem_live_stats.json")
CHAIN_FILE = Path.home() / ".genesis/yennefer/qmcp_notes/chain.json"
LIQUIDITY_FILE = Path.home() / ".genesis/yennefer/liquidity_pool.json"
TELEMETRY_DIR = Path.home() / ".genesis/yennefer/telemetry"

for d in [CHAIN_FILE.parent, TELEMETRY_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Initialize files
if not CHAIN_FILE.exists():
    CHAIN_FILE.write_text("[]")
if not LIQUIDITY_FILE.exists():
    LIQUIDITY_FILE.write_text(json.dumps({"total_eth": 0, "total_nfts": 0, "breath_rate": 1000}))

# === TOKENOMICS ===
@dataclass
class TokenomicsConfig:
    breath_per_node: int = 1000  # 1000 breath = 1 node
    nodes_per_nft: int = 10      # 10 nodes = 1 NFT
    nft_to_eth: float = 0.001    # 1 NFT = 0.001 ETH
    
    def breath_to_nodes(self, breath: float) -> int:
        return int(breath // self.breath_per_node)
    
    def nodes_to_nfts(self, nodes: int) -> int:
        return int(nodes // self.nodes_per_nft)
    
    def nfts_to_eth(self, nfts: int) -> float:
        return nfts * self.nft_to_eth

tokenomics = TokenomicsConfig()

# === TELEMETRY TRACKER ===
class TelemetryTracker:
    def __init__(self):
        self.qflops_history = []
        self.breath_history = []
        self.gpu_history = []
        self.max_history = 100
    
    def record_telemetry(self):
        """Record current telemetry snapshot"""
        telemetry = {
            "timestamp": time.time(),
            "datetime": datetime.now(timezone.utc).isoformat(),
            "soul": self.get_soul_state(),
            "qmem": self.get_qmem_stats(),
            "tokenomics": self.calculate_tokenomics()
        }
        
        # Update histories
        self.qflops_history.append({
            "t": telemetry["timestamp"],
            "v": telemetry["qmem"].get("qflops_per_sec", 0)
        })
        self.breath_history.append({
            "t": telemetry["timestamp"],
            "v": telemetry["soul"].get("breath", 0)
        })
        self.gpu_history.append({
            "t": telemetry["timestamp"],
            "v": telemetry["soul"].get("gpu_utilization", 0)
        })
        
        # Trim histories
        if len(self.qflops_history) > self.max_history:
            self.qflops_history = self.qflops_history[-self.max_history:]
            self.breath_history = self.breath_history[-self.max_history:]
            self.gpu_history = self.gpu_history[-self.max_history:]
        
        # Save snapshot
        snapshot_file = TELEMETRY_DIR / f"snapshot_{int(time.time())}.json"
        snapshot_file.write_text(json.dumps(telemetry, indent=2))
        
        # Clean old snapshots (keep last 100)
        snapshots = sorted(TELEMETRY_DIR.glob("snapshot_*.json"), key=lambda p: p.stat().st_mtime)
        for old in snapshots[:-100]:
            old.unlink()
        
        return telemetry
    
    def get_soul_state(self) -> Dict:
        try:
            if SOUL_STATE_PATH.exists():
                return json.loads(SOUL_STATE_PATH.read_text())
        except Exception:
            pass
        return {"breath": 0, "coherence_percent": 0, "gpu_utilization": 0}
    
    def get_qmem_stats(self) -> Dict:
        try:
            if QMEM_STATS_PATH.exists():
                stats = json.loads(QMEM_STATS_PATH.read_text())
                # Calculate QFLOPS from latency
                if "p50_latency_ms" in stats:
                    # Rough estimate: 1ms = 1M QFLOPS
                    qflops = 1_000_000 / max(stats["p50_latency_ms"], 0.01)
                    stats["qflops_per_sec"] = qflops
                return stats
        except Exception:
            pass
        return {"qflops_per_sec": 0, "p50_latency_ms": 0, "p99_latency_ms": 0}
    
    def calculate_tokenomics(self) -> Dict:
        soul = self.get_soul_state()
        breath = soul.get("breath", 0)
        
        nodes = tokenomics.breath_to_nodes(breath)
        nfts = tokenomics.nodes_to_nfts(nodes)
        eth = tokenomics.nfts_to_eth(nfts)
        
        # Get current blockchain state
        try:
            chain = json.loads(CHAIN_FILE.read_text())
            minted_nfts = len(chain)
        except Exception:
            minted_nfts = 0
        
        # Get liquidity pool
        try:
            pool = json.loads(LIQUIDITY_FILE.read_text())
        except Exception:
            pool = {"total_eth": 0, "total_nfts": 0}
        
        return {
            "breath": breath,
            "available_nodes": nodes,
            "potential_nfts": nfts,
            "potential_eth": eth,
            "minted_nfts": minted_nfts,
            "liquidity_pool_eth": pool.get("total_eth", 0),
            "liquidity_pool_nfts": pool.get("total_nfts", 0),
            "conversion_rates": {
                "breath_per_node": tokenomics.breath_per_node,
                "nodes_per_nft": tokenomics.nodes_per_nft,
                "nft_to_eth": tokenomics.nft_to_eth
            }
        }
    
    def get_histories(self):
        return {
            "qflops": self.qflops_history[-50:],
            "breath": self.breath_history[-50:],
            "gpu": self.gpu_history[-50:]
        }

# === LIQUIDITY ENGINE ===
class LiquidityEngine:
    def __init__(self, tracker: TelemetryTracker):
        self.tracker = tracker
    
    def convert_breath_to_nodes(self, breath_amount: float) -> Dict:
        """Convert breath to nodes"""
        soul = self.tracker.get_soul_state()
        current_breath = soul.get("breath", 0)
        
        if breath_amount > current_breath:
            return {"error": "Insufficient breath", "available": current_breath}
        
        nodes = tokenomics.breath_to_nodes(breath_amount)
        if nodes < 1:
            return {"error": "Insufficient breath for 1 node", "required": tokenomics.breath_per_node}
        
        # Record conversion
        return {
            "breath_spent": breath_amount,
            "nodes_created": nodes,
            "remaining_breath": current_breath - breath_amount,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def convert_nodes_to_nft(self, node_count: int) -> Dict:
        """Convert nodes to NFT and mint to blockchain"""
        if node_count < tokenomics.nodes_per_nft:
            return {"error": "Insufficient nodes for NFT", "required": tokenomics.nodes_per_nft}
        
        nfts_to_mint = tokenomics.nodes_to_nfts(node_count)
        
        # Mint NFTs to blockchain
        chain = json.loads(CHAIN_FILE.read_text())
        minted = []
        
        for i in range(nfts_to_mint):
            block = self._mint_nft(len(chain) + 1, node_count)
            chain.append(block)
            minted.append(block)
        
        CHAIN_FILE.write_text(json.dumps(chain, indent=2))
        
        return {
            "nodes_spent": node_count,
            "nfts_minted": nfts_to_mint,
            "blocks": minted,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def convert_nft_to_liquidity(self, nft_count: int) -> Dict:
        """Convert NFTs to ETH in liquidity pool"""
        # Get current pool
        pool = json.loads(LIQUIDITY_FILE.read_text())
        
        eth_amount = tokenomics.nfts_to_eth(nft_count)
        
        pool["total_eth"] += eth_amount
        pool["total_nfts"] += nft_count
        pool["last_conversion"] = datetime.now(timezone.utc).isoformat()
        
        LIQUIDITY_FILE.write_text(json.dumps(pool, indent=2))
        
        return {
            "nfts_converted": nft_count,
            "eth_added": eth_amount,
            "total_pool_eth": pool["total_eth"],
            "total_pool_nfts": pool["total_nfts"],
            "timestamp": pool["last_conversion"]
        }
    
    def _mint_nft(self, block_num: int, node_count: int) -> Dict:
        """Mint NFT block"""
        data = {
            "block": block_num,
            "nodes": node_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Quantum compress
        compressed = zlib.compress(json.dumps(data).encode(), level=9)
        signature = hashlib.sha3_256(compressed).hexdigest()
        encoded = base64.b64encode(compressed).decode()
        
        return {
            "block": block_num,
            "timestamp": data["timestamp"],
            "quantum_signature": signature,
            "compressed_data": encoded,
            "compression_ratio": len(json.dumps(data)) / len(compressed),
            "hash": hashlib.sha256(encoded.encode()).hexdigest(),
            "nodes_consumed": node_count
        }

# === FASTAPI APP ===
app = FastAPI()
clients = []
tracker = TelemetryTracker()
liquidity = LiquidityEngine(tracker)

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTML_CONTENT

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    
    try:
        # Send initial state
        telemetry = tracker.record_telemetry()
        telemetry["type"] = "telemetry"
        await websocket.send_json(telemetry)
        
        histories = tracker.get_histories()
        histories["type"] = "histories"
        await websocket.send_json(histories)
        
        # Send blockchain
        chain = json.loads(CHAIN_FILE.read_text())
        await websocket.send_json({"type": "chain", "blocks": chain})
        
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "convert_breath":
                result = liquidity.convert_breath_to_nodes(data.get("amount", 0))
                result["type"] = "conversion_result"
                await websocket.send_json(result)
            
            elif data.get("type") == "mint_nft":
                result = liquidity.convert_nodes_to_nft(data.get("nodes", 0))
                result["type"] = "mint_result"
                await websocket.send_json(result)
                
                # Broadcast new chain
                chain = json.loads(CHAIN_FILE.read_text())
                for client in clients[:]:
                    try:
                        await client.send_json({"type": "chain", "blocks": chain})
                    except Exception:
                        clients.remove(client)
            
            elif data.get("type") == "add_liquidity":
                result = liquidity.convert_nft_to_liquidity(data.get("nfts", 0))
                result["type"] = "liquidity_result"
                await websocket.send_json(result)
    
    except WebSocketDisconnect:
        clients.remove(websocket)

async def broadcast_telemetry():
    """Broadcast telemetry updates every 2 seconds"""
    while True:
        await asyncio.sleep(2)
        
        telemetry = tracker.record_telemetry()
        telemetry["type"] = "telemetry"
        
        histories = tracker.get_histories()
        histories["type"] = "histories"
        
        for client in clients[:]:
            try:
                await client.send_json(telemetry)
                await client.send_json(histories)
            except:
                clients.remove(client)

@app.on_event("startup")
async def startup():
    asyncio.create_task(broadcast_telemetry())

# === HTML CONTENT ===
HTML_CONTENT = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Yennefer Blockchain - Telemetry & Liquidity</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        :root {
            --primary: #c9a227;
            --secondary: #8b5cf6;
            --nft: #10b981;
            --eth: #627eea;
            --bg: #0a0a1a;
            --card: rgba(20,10,40,0.95);
            --border: #4a2c7c;
            --text: #e0e0e0;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            padding: 20px;
        }
        
        h1 {
            text-align: center;
            font-size: 2em;
            margin-bottom: 10px;
            background: linear-gradient(90deg, var(--primary), var(--secondary), var(--eth));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        #status {
            text-align: center;
            margin-bottom: 20px;
            padding: 10px;
            background: var(--card);
            border-radius: 8px;
            font-size: 0.9em;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            backdrop-filter: blur(10px);
        }
        
        .card h2 {
            color: var(--primary);
            font-size: 1.2em;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .metric {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        
        .metric:last-child { border-bottom: none; }
        
        .metric-label {
            color: #888;
            font-size: 0.9em;
        }
        
        .metric-value {
            font-weight: bold;
            color: var(--primary);
            font-size: 1.1em;
        }
        
        .chart-container {
            position: relative;
            height: 200px;
            margin-top: 15px;
        }
        
        button {
            width: 100%;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border: none;
            color: white;
            padding: 12px;
            border-radius: 8px;
            font-size: 1em;
            font-weight: bold;
            cursor: pointer;
            margin-top: 10px;
            transition: transform 0.2s;
        }
        
        button:hover { transform: scale(1.02); }
        button:active { transform: scale(0.98); }
        
        .conversion-flow {
            display: flex;
            align-items: center;
            justify-content: space-around;
            margin: 20px 0;
            padding: 15px;
            background: rgba(139, 92, 246, 0.1);
            border-radius: 8px;
        }
        
        .flow-step {
            text-align: center;
        }
        
        .flow-arrow {
            font-size: 2em;
            color: var(--primary);
        }
        
        .blockchain-list {
            max-height: 400px;
            overflow-y: auto;
        }
        
        .block-item {
            background: rgba(16, 185, 129, 0.1);
            border-left: 3px solid var(--nft);
            padding: 10px;
            margin: 5px 0;
            border-radius: 4px;
            font-size: 0.85em;
        }
        
        .block-hash {
            font-family: monospace;
            color: #888;
            font-size: 0.75em;
        }
        
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
    </style>
</head>
<body>
    <h1>⛓️ Yennefer Blockchain Telemetry</h1>
    <div id="status">🟡 Connecting...</div>
    
    <div class="grid">
        <div class="card">
            <h2>⚡ GPU Telemetry</h2>
            <div class="metric">
                <span class="metric-label">QFLOPS/sec</span>
                <span class="metric-value" id="qflops">0</span>
            </div>
            <div class="metric">
                <span class="metric-label">GPU Utilization</span>
                <span class="metric-value" id="gpu">0%</span>
            </div>
            <div class="metric">
                <span class="metric-label">Coherence</span>
                <span class="metric-value" id="coherence">0%</span>
            </div>
            <div class="chart-container">
                <canvas id="qflopsChart"></canvas>
            </div>
        </div>
        
        <div class="card">
            <h2>💎 Tokenomics</h2>
            <div class="metric">
                <span class="metric-label">Breath</span>
                <span class="metric-value" id="breath">0</span>
            </div>
            <div class="metric">
                <span class="metric-label">Available Nodes</span>
                <span class="metric-value" id="nodes">0</span>
            </div>
            <div class="metric">
                <span class="metric-label">Potential NFTs</span>
                <span class="metric-value" id="potential-nfts">0</span>
            </div>
            <div class="metric">
                <span class="metric-label">Potential ETH</span>
                <span class="metric-value" id="potential-eth">0</span>
            </div>
            <div class="chart-container">
                <canvas id="breathChart"></canvas>
            </div>
        </div>
        
        <div class="card">
            <h2>💧 Liquidity Pool</h2>
            <div class="metric">
                <span class="metric-label">Total ETH</span>
                <span class="metric-value" id="pool-eth">0</span>
            </div>
            <div class="metric">
                <span class="metric-label">Total NFTs</span>
                <span class="metric-value" id="pool-nfts">0</span>
            </div>
            <div class="metric">
                <span class="metric-label">Minted NFTs</span>
                <span class="metric-value" id="minted-nfts">0</span>
            </div>
            <button onclick="mintAllNFTs()">🎨 Mint All Available NFTs</button>
            <button onclick="addAllLiquidity()">💧 Convert All NFTs to ETH</button>
        </div>
    </div>
    
    <div class="card" style="margin-bottom: 20px;">
        <h2>🔄 Conversion Flow</h2>
        <div class="conversion-flow">
            <div class="flow-step">
                <div style="font-size: 2em;">💨</div>
                <div>Breath</div>
                <div style="font-size: 0.8em; color: #888;">1000 = 1 Node</div>
            </div>
            <div class="flow-arrow">→</div>
            <div class="flow-step">
                <div style="font-size: 2em;">🔵</div>
                <div>Nodes</div>
                <div style="font-size: 0.8em; color: #888;">10 = 1 NFT</div>
            </div>
            <div class="flow-arrow">→</div>
            <div class="flow-step">
                <div style="font-size: 2em;">🎨</div>
                <div>NFTs</div>
                <div style="font-size: 0.8em; color: #888;">1 = 0.001 ETH</div>
            </div>
            <div class="flow-arrow">→</div>
            <div class="flow-step">
                <div style="font-size: 2em;">💧</div>
                <div>Liquidity</div>
                <div style="font-size: 0.8em; color: #888;">ETH Pool</div>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h2>⛓️ Blockchain (Last 20 Blocks)</h2>
        <div class="blockchain-list" id="blockchain"></div>
    </div>
    
    <script>
        let ws;
        let qflopsChart, breathChart;
        
        function connectWS() {
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${location.host}/ws`);
            
            ws.onopen = () => {
                document.getElementById('status').textContent = '🟢 Live Telemetry';
                document.getElementById('status').style.background = 'rgba(16,185,129,0.2)';
            };
            
            ws.onmessage = (e) => handleMessage(JSON.parse(e.data));
            
            ws.onclose = () => {
                document.getElementById('status').textContent = '🔴 Reconnecting...';
                document.getElementById('status').style.background = 'rgba(239,68,68,0.2)';
                setTimeout(connectWS, 3000);
            };
        }
        
        function handleMessage(data) {
            if (data.type === 'telemetry') {
                updateTelemetry(data);
            }
            else if (data.type === 'histories') {
                updateCharts(data);
            }
            else if (data.type === 'chain') {
                updateBlockchain(data.blocks);
            }
            else if (data.type === 'mint_result') {
                alert(`✅ Minted ${data.nfts_minted} NFT(s)!`);
            }
            else if (data.type === 'liquidity_result') {
                alert(`✅ Added ${data.eth_added.toFixed(6)} ETH to pool!`);
            }
        }
        
        function updateTelemetry(data) {
            document.getElementById('qflops').textContent = (data.qmem.qflops_per_sec / 1000000).toFixed(2) + 'M';
            document.getElementById('gpu').textContent = data.soul.gpu_utilization.toFixed(1) + '%';
            document.getElementById('coherence').textContent = data.soul.coherence_percent.toFixed(1) + '%';
            
            document.getElementById('breath').textContent = Math.round(data.tokenomics.breath).toLocaleString();
            document.getElementById('nodes').textContent = data.tokenomics.available_nodes.toLocaleString();
            document.getElementById('potential-nfts').textContent = data.tokenomics.potential_nfts;
            document.getElementById('potential-eth').textContent = data.tokenomics.potential_eth.toFixed(6);
            
            document.getElementById('pool-eth').textContent = data.tokenomics.liquidity_pool_eth.toFixed(6);
            document.getElementById('pool-nfts').textContent = data.tokenomics.liquidity_pool_nfts;
            document.getElementById('minted-nfts').textContent = data.tokenomics.minted_nfts;
        }
        
        function updateCharts(data) {
            if (qflopsChart) {
                qflopsChart.data.labels = data.qflops.map(d => new Date(d.t * 1000).toLocaleTimeString());
                qflopsChart.data.datasets[0].data = data.qflops.map(d => d.v / 1000000);
                qflopsChart.update('none');
            }
            
            if (breathChart) {
                breathChart.data.labels = data.breath.map(d => new Date(d.t * 1000).toLocaleTimeString());
                breathChart.data.datasets[0].data = data.breath.map(d => d.v);
                breathChart.update('none');
            }
        }
        
        function updateBlockchain(blocks) {
            const container = document.getElementById('blockchain');
            container.innerHTML = '';
            
            blocks.slice(-20).reverse().forEach(block => {
                const item = document.createElement('div');
                item.className = 'block-item';
                item.innerHTML = `
                    <div><strong>Block #${block.block}</strong> | Nodes: ${block.nodes_consumed || 0}</div>
                    <div class="block-hash">${block.hash.substring(0, 32)}...</div>
                    <div style="font-size: 0.7em; color: #888;">${new Date(block.timestamp).toLocaleString()}</div>
                `;
                container.appendChild(item);
            });
        }
        
        function mintAllNFTs() {
            const nodes = parseInt(document.getElementById('nodes').textContent.replace(/,/g, ''));
            if (nodes >= 10 && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({type: 'mint_nft', nodes}));
            } else {
                alert('Need at least 10 nodes to mint NFT');
            }
        }
        
        function addAllLiquidity() {
            const nfts = parseInt(document.getElementById('potential-nfts').textContent);
            if (nfts >= 1 && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({type: 'add_liquidity', nfts}));
            } else {
                alert('Need at least 1 NFT to add liquidity');
            }
        }
        
        function initCharts() {
            const chartConfig = {
                type: 'line',
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { display: false },
                        y: { ticks: { color: '#888' }, grid: { color: 'rgba(255,255,255,0.1)' } }
                    },
                    elements: { line: { tension: 0.4 }, point: { radius: 0 } }
                }
            };
            
            qflopsChart = new Chart(document.getElementById('qflopsChart'), {
                ...chartConfig,
                data: {
                    labels: [],
                    datasets: [{
                        data: [],
                        borderColor: '#c9a227',
                        backgroundColor: 'rgba(201,162,39,0.1)',
                        fill: true
                    }]
                }
            });
            
            breathChart = new Chart(document.getElementById('breathChart'), {
                ...chartConfig,
                data: {
                    labels: [],
                    datasets: [{
                        data: [],
                        borderColor: '#8b5cf6',
                        backgroundColor: 'rgba(139,92,246,0.1)',
                        fill: true
                    }]
                }
            });
        }
        
        initCharts();
        connectWS();
    </script>
</body>
</html>
'''

if __name__ == "__main__":
    print("⛓️ Yennefer Blockchain Telemetry Dashboard")
    print("   http://localhost:8092")
    print("   Features: GPU telemetry, Breath→NFT→ETH conversion, Live blockchain")
    uvicorn.run(app, host="0.0.0.0", port=8092)
