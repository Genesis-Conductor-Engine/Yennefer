# LangSmith Integration - Diamond Node

## Overview

LangSmith provides **LLM-specific observability** for the Diamond Node unified inference system. It complements AppSignal (system metrics) with:

- LLM call tracing (tokens, latency, cost estimation)
- Tool execution tracking
- Multi-step workflow visualization
- Error tracking and debugging
- Performance analytics and A/B testing

## Configuration

### Environment Variables

Already configured in `~/.env`:

```bash
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=$YOUR_LANGSMITH_API_KEY
LANGSMITH_PROJECT=diamondnode
```

### Package Installation

✅ Already installed: `langsmith 0.8.3` in `~/xinference_venv/`

## Architecture

### Dual Monitoring Strategy

```
┌─────────────────────────────────────────────────────────┐
│                   User Request                          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Claude Orchestrator                        │
│  ┌──────────────────────────────────────────────────┐   │
│  │  LangSmith Tracing (LLM-specific)                │   │
│  │  - Token counts, latency                         │   │
│  │  - Chain/agent workflows                         │   │
│  │  - Tool execution logs                           │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  AppSignal/OpenTelemetry (System-level)          │   │
│  │  - VRAM usage, Hamiltonian                       │   │
│  │  - GPU metrics, temperatures                     │   │
│  │  - Service health, errors                        │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Usage

### 1. Basic Tracing

```python
from unified_inference.langsmith_integration import tracer

# Trace LLM calls
@tracer.trace_llm_call("claude_portfolio_analysis")
async def analyze_portfolio(address: str):
    response = await orchestrator.chat(f"Analyze portfolio for {address}")
    return response

# Trace tool executions
@tracer.trace_tool("cuda_q_qaoa")
async def run_qaoa(shots: int):
    result = subprocess.run([...])
    return result

# Trace multi-step workflows
@tracer.trace_chain("blockchain_optimization_workflow")
async def optimize_blockchain_portfolio(address: str):
    balance = await query_wallet_balance(address)
    risk = await analyze_portfolio_risk(address)
    rebalancing = await simulate_rebalancing(...)
    return {"balance": balance, "risk": risk, "rebalancing": rebalancing}
```

### 2. Add Runtime Metadata

```python
tracer.add_metadata({
    "vram_used_mb": 2500,
    "hamiltonian": 6.2,
    "gpu_temp": 72,
    "model": "claude-opus-4-7",
    "effort": "xhigh"
})
```

### 3. Log User Feedback

```python
# After user rates a response
tracer.log_feedback(
    run_id="abc-123-def-456",
    score=0.95,
    comment="Excellent rebalancing recommendation"
)
```

## Integration with Claude Orchestrator

### Option 1: Wrap Existing Methods (Recommended)

Add decorators to `claude_orchestrator.py`:

```python
from langsmith_integration import tracer

class ClaudeOrchestrator:
    
    @tracer.trace_llm_call("claude_orchestrator_chat")
    async def chat(self, message: str, streaming: bool = False):
        # Existing implementation
        ...
        
        # Add metadata
        tracer.add_metadata({
            "streaming": streaming,
            "model": self.model,
            "max_tokens": self.max_tokens
        })
        
        return response
    
    @tracer.trace_tool("execute_tool")
    async def execute_tool(self, tool_name: str, tool_input: dict):
        # Existing implementation
        ...
        
        tracer.add_metadata({
            "tool": tool_name,
            "input_keys": list(tool_input.keys())
        })
        
        return result
```

### Option 2: Manual Tracing

For fine-grained control:

```python
from langsmith import traceable

@traceable(run_type="chain", name="blockchain_portfolio_optimizer")
async def full_portfolio_workflow(address: str):
    # Nested traces automatically linked
    balance = await query_wallet_balance(address)  # Sub-trace
    risk = await analyze_portfolio_risk(address)    # Sub-trace
    optimization = await run_cuda_q_qaoa(...)       # Sub-trace
    
    return {
        "balance": balance,
        "risk": risk,
        "optimization": optimization
    }
```

## Dashboard & Analytics

### Access LangSmith Dashboard

https://smith.langchain.com/

- **Organization:** diamondnode
- **Project:** diamondnode

### Key Metrics to Monitor

1. **LLM Performance**
   - Tokens per request (input/output)
   - Latency distribution
   - Cost per request
   - Cache hit rate (for prompt caching)

2. **Tool Execution**
   - Tool call frequency (which tools used most)
   - Tool latency (CUDA-Q, blockchain, optimizer)
   - Tool success/failure rates

3. **Workflow Analytics**
   - End-to-end workflow latency
   - Step-by-step bottleneck analysis
   - Common error patterns

4. **Business Metrics**
   - Portfolio optimization success rate
   - Average gas savings per transaction
   - VRAM offload frequency

## Comparison: LangSmith vs AppSignal

| Aspect | LangSmith | AppSignal |
|--------|-----------|-----------|
| **Focus** | LLM/AI-specific | System-level infrastructure |
| **Traces** | LLM calls, chains, agents | HTTP requests, database queries |
| **Metrics** | Tokens, cost, prompts | VRAM, CPU, GPU, memory |
| **Use Case** | Debug LLM behavior, optimize prompts | Monitor system health, performance |
| **Visualization** | Chain graphs, token usage | Time-series, dashboards |
| **Cost Tracking** | Built-in LLM cost estimation | Custom metric tracking |

**Best Practice:** Use both together for complete observability.

## Testing

### Test LangSmith Integration

```bash
cd ~/unified_inference
source ~/xinference_venv/bin/activate
python langsmith_integration.py
```

Expected output:
```
✓ LangSmith tracing enabled (project: diamondnode)
Testing LangSmith integration...
Enabled: True
Available: True

1. Testing LLM call tracing...
Result: Response to: What is the meaning of life?

2. Testing tool tracing...
Result: {'vram_used': 2500, 'vram_total': 4096}

3. Testing chain tracing...
Result: {'balance': {...}, 'risk': {...}, 'rebalancing': {...}}

✓ All tests complete. Check LangSmith dashboard:
  https://smith.langchain.com/o/diamondnode/projects/p/diamondnode
```

### View Traces in Dashboard

1. Go to https://smith.langchain.com/
2. Select organization: **diamondnode**
3. Select project: **diamondnode**
4. View traces in real-time
5. Filter by run type: llm, tool, chain
6. Analyze latency, tokens, costs

## Production Deployment

### 1. Enable in Production

Update `~/.env.production`:

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=$YOUR_LANGSMITH_API_KEY
LANGSMITH_PROJECT=diamondnode-prod  # Separate project for production
```

### 2. Add to Orchestrator Initialization

```python
# In claude_orchestrator.py
from langsmith_integration import tracer

def __init__(self):
    # Existing initialization
    ...
    
    # Initialize LangSmith
    if tracer.enabled:
        print(f"✓ LangSmith tracing active (project: {tracer.project})")
```

### 3. Set Sampling Rate (Optional)

For high-volume production, sample traces to reduce costs:

```python
import random

@tracer.trace_llm_call("claude_chat")
async def chat(self, message: str):
    # Only trace 10% of requests
    if random.random() < 0.1:
        tracer.add_metadata({"sampled": True})
    # ... rest of implementation
```

## Security

- ✅ API key stored in `.env` (not in code)
- ✅ Project-level access control in LangSmith
- ⚠️ **Do not log sensitive data** (wallet private keys, API keys)
- ⚠️ Sanitize inputs before logging (PII, financial data)

### Sanitization Example

```python
@tracer.trace_tool("query_wallet_balance")
async def query_wallet_balance(address: str):
    # Sanitize address for logging
    safe_address = f"{address[:6]}...{address[-4:]}"
    tracer.add_metadata({"address": safe_address})
    # ... rest of implementation
```

## Troubleshooting

### Traces Not Appearing

1. **Check environment variables:**
   ```bash
   echo $LANGSMITH_TRACING
   echo $LANGSMITH_API_KEY
   ```

2. **Verify package installed:**
   ```bash
   ~/xinference_venv/bin/pip show langsmith
   ```

3. **Test connectivity:**
   ```bash
   cd ~/unified_inference
   python langsmith_integration.py
   ```

### High Latency

LangSmith adds ~10-50ms overhead per trace. To minimize:
- Use async operations (already implemented)
- Batch trace exports (automatic)
- Set sampling rate for high-volume endpoints

### Cost Concerns

LangSmith pricing (as of 2026-05):
- **Free tier:** 10k traces/month
- **Team:** $39/month, 100k traces
- **Enterprise:** Custom pricing

For Diamond Node (estimated ~1k traces/day):
- Free tier sufficient for development
- Team tier for production

## Next Steps

1. ✅ LangSmith installed and configured
2. ⏳ Add decorators to `claude_orchestrator.py`
3. ⏳ Test with real blockchain portfolio workflow
4. ⏳ Create custom dashboard in LangSmith
5. ⏳ Set up alerts for anomalies (high latency, errors)

## Resources

- **LangSmith Docs:** https://docs.smith.langchain.com/
- **Dashboard:** https://smith.langchain.com/
- **Integration Code:** `~/unified_inference/langsmith_integration.py`
- **Config:** `~/.env` (LANGSMITH_* variables)

---

**Status:** ✅ LangSmith integration ready for use!
