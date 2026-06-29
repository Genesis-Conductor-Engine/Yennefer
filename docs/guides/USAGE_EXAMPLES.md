# Usage Examples

Practical examples for common Diamond Node workflows.

## Table of Contents

- [Natural Language AI](#natural-language-ai)
- [Blockchain Analytics](#blockchain-analytics)
- [Object Detection](#object-detection)
- [Quantum Optimization](#quantum-optimization)
- [System Monitoring](#system-monitoring)

## Natural Language AI

### Basic Chat Interface

```python
import asyncio
from src.orchestrator import ClaudeOrchestrator

async def chat_session():
    orchestrator = ClaudeOrchestrator(
        api_key="sk-ant-...",
        enable_caching=True,
        enable_streaming=True
    )
    
    # Start conversation
    response = await orchestrator.chat(
        message="What blockchain networks do you support?"
    )
    
    print(response["content"])
```

### Streaming Responses

```python
async def streaming_chat():
    orchestrator = ClaudeOrchestrator(api_key="sk-ant-...")
    
    print("Assistant: ", end="", flush=True)
    
    async for chunk in orchestrator.stream_chat(
        message="Explain how QAOA optimization works"
    ):
        if chunk["type"] == "text":
            print(chunk["data"], end="", flush=True)
        elif chunk["type"] == "tool_use":
            print(f"\n[Using: {chunk['data']['name']}]")
    
    print("\n")
```

### Tool Execution

```python
from src.orchestrator import ClaudeOrchestrator
from src.blockchain_tools import BLOCKCHAIN_TOOLS

async def chat_with_tools():
    orchestrator = ClaudeOrchestrator(api_key="sk-ant-...")
    
    response = await orchestrator.chat(
        message="Analyze wallet 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        tools=BLOCKCHAIN_TOOLS
    )
    
    # Claude automatically calls query_wallet_balance()
    print(f"Tools used: {len(response['tool_calls'])}")
    print(response["content"])
```

## Blockchain Analytics

### Query Wallet Balance

```python
from src.blockchain_tools import query_wallet_balance

async def check_wallet():
    result = await query_wallet_balance(
        address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        chain="ethereum",
        include_tokens=True
    )
    
    print(f"💰 Total Value: ${result['total_usd_value']:,.2f}\n")
    
    # Native balance
    native = result['native_balance']
    print(f"{native['symbol']}: {native['balance']:.4f} (${native['usd_value']:,.2f})")
    
    # Top tokens
    print("\nTop Holdings:")
    for token in sorted(result['tokens'], key=lambda x: x['usd_value'], reverse=True)[:5]:
        print(f"  {token['symbol']}: ${token['usd_value']:,.2f}")
```

### Portfolio Risk Analysis

```python
from src.blockchain_tools import analyze_portfolio_risk

async def analyze_risk():
    holdings = [
        {"symbol": "ETH", "amount": 10.5, "usd_value": 21000},
        {"symbol": "BTC", "amount": 0.5, "usd_value": 22500},
        {"symbol": "USDC", "amount": 5000, "usd_value": 5000}
    ]
    
    risk = await analyze_portfolio_risk(
        holdings=holdings,
        risk_model="monte_carlo",
        time_horizon=30
    )
    
    print(f"📊 Risk Analysis")
    print(f"  Risk Score: {risk['risk_score']:.2f}/1.0")
    print(f"  Volatility: {risk['volatility']['annual']:.1f}%")
    print(f"  Diversification: {risk['diversification']['score']:.2f}/1.0")
    print(f"  Value at Risk (95%): ${risk['var_95']:,.2f}")
    
    print("\n💡 Recommendations:")
    for rec in risk['recommendations']:
        print(f"  - {rec}")
```

### Monte Carlo Rebalancing

```python
from src.blockchain_tools import simulate_rebalancing

async def rebalance_portfolio():
    current = {"ETH": 0.7, "BTC": 0.2, "USDC": 0.1}
    target = {"ETH": 0.5, "BTC": 0.3, "USDC": 0.2}
    
    result = await simulate_rebalancing(
        current_allocation=current,
        target_allocation=target,
        simulations=1000,
        time_horizon=30
    )
    
    print("🔄 Rebalancing Simulation\n")
    
    print("Required Trades:")
    for trade in result['rebalancing_trades']:
        action = "🟢 BUY" if trade['action'] == 'buy' else "🔴 SELL"
        print(f"  {action} {trade['amount']:.4f} {trade['symbol']} (${trade['usd_value']:,.2f})")
    
    print(f"\nExpected Outcome:")
    outcome = result['expected_outcomes']
    print(f"  Mean Return: {outcome['mean_return']:.2f}%")
    print(f"  Best Case: {outcome['best_case']:.2f}%")
    print(f"  Worst Case: {outcome['worst_case']:.2f}%")
    print(f"  Win Probability: {outcome['probability_positive']:.1%}")
    
    print(f"\nCost Analysis:")
    costs = result['cost_analysis']
    print(f"  Gas Fees: ${costs['gas_fees']:.2f}")
    print(f"  Slippage: ${costs['slippage']:.2f}")
    print(f"  Total: ${costs['total_cost']:.2f}")
```

### Gas Fee Optimization

```python
from src.blockchain_tools import optimize_gas_fees

async def optimize_gas():
    gas = await optimize_gas_fees(
        transaction_type="swap",
        priority="medium",
        max_wait_time=300
    )
    
    rec = gas['recommended_gas']
    print("⛽ Gas Optimization\n")
    print(f"Recommended:")
    print(f"  Max Fee: {rec['max_fee']:.2f} gwei")
    print(f"  Priority Fee: {rec['max_priority_fee']:.2f} gwei")
    print(f"  Est. Cost: ${rec['estimated_cost']['usd']:.2f}")
    
    print("\nAlternatives:")
    for alt in gas['alternatives']:
        print(f"  {alt['priority'].upper()}: {alt['max_fee']:.2f} gwei → ${alt['estimated_cost']['usd']:.2f} (~{alt['estimated_time']}s)")
    
    savings = gas['savings_opportunity']
    if savings['potential_savings'] > 1:
        print(f"\n💰 Save ${savings['potential_savings']:.2f} by waiting until {savings['optimal_time']}")
```

## Object Detection

### YOLO11 Detection

```python
from src.yolo11 import YOLO11Detector

async def detect_objects():
    detector = YOLO11Detector(
        model_path="models/yolo11n.pt",
        device="cuda"
    )
    
    results = await detector.detect(
        image_url="https://example.com/street.jpg",
        confidence=0.5
    )
    
    print(f"🎯 Detected {len(results['detections'])} objects\n")
    
    for det in results['detections']:
        print(f"{det['label']}: {det['confidence']:.1%} at ({det['bbox']})")
```

### Batch Detection

```python
async def batch_detect():
    detector = YOLO11Detector(model_path="models/yolo11n.pt")
    
    image_urls = [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg",
        "https://example.com/image3.jpg"
    ]
    
    results = await detector.batch_detect(
        image_urls=image_urls,
        confidence=0.5
    )
    
    for i, result in enumerate(results):
        print(f"Image {i+1}: {len(result['detections'])} objects detected")
```

### MCP App Integration

```python
from src.mcp_apps import MCPAppsClient

async def render_detection_ui():
    client = MCPAppsClient(base_url="http://localhost:8000")
    
    # Render detection interface
    response = await client.call(
        method="apps/render",
        params={
            "app_id": "yolo11-detector",
            "component": "detection-view",
            "props": {
                "image_url": "https://example.com/image.jpg",
                "confidence": 0.5
            }
        }
    )
    
    print("UI rendered:", response["result"]["component"]["type"])
```

## Quantum Optimization

### CUDA-Q QAOA Portfolio Optimization

```python
from src.cuda_q import QAOAOptimizer

async def optimize_portfolio():
    optimizer = QAOAOptimizer(
        backend="nvidia",
        num_qubits=10
    )
    
    # Define portfolio optimization problem
    holdings = [
        {"symbol": "ETH", "weight": 0.3},
        {"symbol": "BTC", "weight": 0.3},
        {"symbol": "SOL", "weight": 0.2},
        {"symbol": "USDC", "weight": 0.2}
    ]
    
    result = await optimizer.optimize(
        holdings=holdings,
        constraints={
            "min_weight": 0.1,
            "max_weight": 0.4
        },
        num_layers=3
    )
    
    print("🔬 QAOA Optimization\n")
    print(f"Energy: {result['energy']:.6f}")
    print(f"Convergence: {result['convergence']:.2%}")
    
    print("\nOptimal Allocation:")
    for token, weight in result['optimal_allocation'].items():
        print(f"  {token}: {weight:.1%}")
    
    # Convergence analysis
    print(f"\nEnergy Convergence:")
    for i, energy in enumerate(result['energy_values'][:5]):
        print(f"  Layer {i+1}: {energy:.6f}")
```

### Waveform Equilibrium Analysis

```python
async def analyze_waveform():
    optimizer = QAOAOptimizer(backend="nvidia")
    
    result = await optimizer.analyze_waveform_equilibrium(
        initial_state="|0000>",
        target_state="|1010>",
        time_steps=100
    )
    
    print("🌊 Waveform Analysis\n")
    print(f"Equilibrium reached: {result['converged']}")
    print(f"Final energy: {result['final_energy']:.6f}")
    print(f"Time to equilibrium: {result['convergence_time']:.2f}s")
```

## System Monitoring

### Health Check

```python
import httpx

async def check_system_health():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/health")
        health = response.json()
        
        print(f"System Status: {health['status'].upper()}")
        print(f"Uptime: {health['uptime_seconds'] / 3600:.1f} hours\n")
        
        # Check components
        print("Components:")
        for name, component in health['components'].items():
            status = "✓" if component['status'] == 'healthy' else "✗"
            print(f"  {status} {name}: {component['status']}")
        
        # VRAM monitoring
        vram = health['metrics']['vram']
        print(f"\nVRAM: {vram['used_mb']}/{vram['total_mb']} MB ({vram['utilization']:.1%})")
        print(f"Hamiltonian: {vram['hamiltonian']:.2f} (threshold: {vram['threshold']})")
```

### VRAM Monitoring

```python
async def monitor_vram():
    """Monitor VRAM and trigger offload if needed."""
    client = httpx.AsyncClient()
    
    while True:
        response = await client.get("http://localhost:8000/health")
        health = response.json()
        
        vram = health['metrics']['vram']
        H = vram['hamiltonian']
        
        print(f"H(s) = {H:.2f}")
        
        if H >= 8.5:
            print("⚠️ High VRAM pressure - triggering offload")
            await trigger_offload()
        
        await asyncio.sleep(10)

async def trigger_offload():
    """Offload context to Notion."""
    # Implementation from gateway.py
    pass
```

### Request Metrics

```python
async def log_metrics():
    """Log request metrics to AppSignal."""
    import appsignal
    
    response = await httpx.get("http://localhost:8000/health")
    health = response.json()
    
    metrics = health['metrics']['requests']
    
    appsignal.set_gauge("requests.total", metrics['total'])
    appsignal.set_gauge("requests.last_minute", metrics['last_minute'])
    appsignal.set_gauge("requests.error_rate", metrics['error_rate'])
    
    latency = health['metrics']['latency']
    appsignal.set_gauge("latency.p50", latency['p50_ms'])
    appsignal.set_gauge("latency.p95", latency['p95_ms'])
    appsignal.set_gauge("latency.p99", latency['p99_ms'])
```

## Complete Workflow Example

### End-to-End Portfolio Analysis

```python
async def complete_analysis(wallet_address: str):
    """Complete portfolio analysis workflow."""
    
    print(f"📊 Analyzing wallet {wallet_address}\n")
    
    # 1. Query wallet balance
    print("1. Querying wallet...")
    balance = await query_wallet_balance(
        address=wallet_address,
        chain="ethereum"
    )
    print(f"   Total value: ${balance['total_usd_value']:,.2f}")
    
    # 2. Analyze risk
    print("\n2. Analyzing risk...")
    risk = await analyze_portfolio_risk(
        holdings=balance['tokens'],
        risk_model="monte_carlo"
    )
    print(f"   Risk score: {risk['risk_score']:.2f}")
    print(f"   Diversification: {risk['diversification']['score']:.2f}")
    
    # 3. Optimize with QAOA
    print("\n3. Running QAOA optimization...")
    optimizer = QAOAOptimizer(backend="nvidia")
    optimal = await optimizer.optimize(
        holdings=balance['tokens'][:10],  # Top 10 tokens
        constraints={"min_weight": 0.05}
    )
    print(f"   Energy: {optimal['energy']:.6f}")
    
    # 4. Simulate rebalancing
    print("\n4. Simulating rebalancing...")
    current_alloc = {t['symbol']: t['usd_value'] / balance['total_usd_value'] 
                     for t in balance['tokens'][:5]}
    
    result = await simulate_rebalancing(
        current_allocation=current_alloc,
        target_allocation=optimal['optimal_allocation'],
        simulations=1000
    )
    print(f"   Expected return: {result['expected_outcomes']['mean_return']:.2f}%")
    print(f"   Cost: ${result['cost_analysis']['total_cost']:.2f}")
    
    # 5. Generate report with Claude
    print("\n5. Generating AI report...")
    orchestrator = ClaudeOrchestrator(api_key="sk-ant-...")
    
    report = await orchestrator.chat(
        message=f"""
        Summarize this portfolio analysis:
        - Total value: ${balance['total_usd_value']:,.2f}
        - Risk score: {risk['risk_score']:.2f}
        - Diversification: {risk['diversification']['score']:.2f}
        - QAOA energy: {optimal['energy']:.6f}
        - Rebalancing cost: ${result['cost_analysis']['total_cost']:.2f}
        - Expected return: {result['expected_outcomes']['mean_return']:.2f}%
        
        Provide actionable recommendations.
        """
    )
    
    print("\n" + "="*60)
    print("📝 AI REPORT")
    print("="*60)
    print(report['content'])

# Run complete analysis
asyncio.run(complete_analysis("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"))
```

## Best Practices

### Error Handling

```python
from src.blockchain_tools.exceptions import BlockchainError

async def safe_query(address: str):
    try:
        result = await query_wallet_balance(address)
        return result
    except BlockchainError as e:
        print(f"Error: {e}")
        return None
```

### Rate Limiting

```python
import asyncio

async def batch_queries_with_rate_limit(addresses: List[str]):
    """Query multiple wallets with rate limiting."""
    results = []
    
    for i, address in enumerate(addresses):
        result = await query_wallet_balance(address)
        results.append(result)
        
        # Rate limit: 60 requests/minute = 1 per second
        if i < len(addresses) - 1:
            await asyncio.sleep(1)
    
    return results
```

### Caching

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
async def cached_query(address: str):
    """Cache wallet queries for 5 minutes."""
    return await query_wallet_balance(address)
```

## Related Documentation

- [API Reference](../api/)
- [Claude Orchestrator](CLAUDE_ORCHESTRATOR_README.md)
- [Blockchain Tools](BLOCKCHAIN_TOOLS_IMPLEMENTATION.md)
- [Development Setup](DEVELOPMENT.md)

---

**Last updated:** 2025-05-12
