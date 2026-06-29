# Claude API Orchestrator - Diamond Node Unified Inference System

## ✅ Installation Complete

**Files Created:**
- `~/unified_inference/claude_orchestrator.py` - Main orchestrator module
- Anthropic SDK v0.101.0 installed

## 🚀 Quick Start

```bash
# Set your Claude API key
export ANTHROPIC_API_KEY="your-api-key-here"

# Run the demo
python3 ~/unified_inference/claude_orchestrator.py
```

## 📋 Features

### **Natural Language Interface**
Ask questions in plain English and Claude routes to the right backend:
- "What's the VRAM status?"
- "Run object detection on image.jpg"
- "Optimize for scientific workload"

### **6 Integrated Tools**
1. **query_vram_status** - Check GPU VRAM, temperature, Hamiltonian
2. **run_cuda_q_qaoa** - Execute quantum optimization (CUDA-Q)
3. **run_yolo11_detection** - Object detection with YOLO11s
4. **query_qwen_chat** - Chat with Qwen 1.5 LLM
5. **optimize_orthogonal_bounds** - Find Pareto-optimal configs
6. **trigger_notion_offload** - Offload context when H > 8.5

### **Claude Opus 4.7 with Adaptive Thinking**
- Model: `claude-opus-4-7`
- Thinking: Adaptive (dynamic reasoning depth)
- Effort: `xhigh` (best for complex orchestration)
- Caching: System prompt cached for 90% cost reduction

## 🎯 Example Usage

```python
from unified_inference.claude_orchestrator import ClaudeOrchestrator
import asyncio

async def demo():
    orchestrator = ClaudeOrchestrator()
    
    # Natural language query
    response = await orchestrator.chat(
        "Check VRAM and tell me if I can run YOLO11 detection"
    )
    print(response)
    
    # Multi-turn conversation
    response = await orchestrator.chat(
        "Now run object detection on /tmp/test.jpg"
    )
    print(response)

asyncio.run(demo())
```

## 📊 Tool Integration Points

### Current Status: Mock Implementations
All tools return mock data. Replace with real API calls:

#### 1. Diamond Gateway Integration
```python
# In execute_tool("query_vram_status")
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/v1/orchestrate",
        headers={"Authorization": f"Bearer {os.environ['GATEWAY_SECRET']}"},
        json={"session_id": "claude-session"}
    )
    return response.json()
```

#### 2. CUDA-Q QAOA Integration
```python
# In execute_tool("run_cuda_q_qaoa")
import subprocess

result = subprocess.run([
    "python", os.path.expanduser("~/diamond-node/scripts/mycelial_qubo.py"),
    "--shots", str(shots),
    "--outer-rounds", str(outer_rounds)
], capture_output=True, text=True)
return json.loads(result.stdout)
```

#### 3. YOLO11 via Xinference
```python
# In execute_tool("run_yolo11_detection")
from xinference.client import Client

client = Client("http://localhost:9997")
model = client.get_model("yolo11s")
result = model.infer(source=image_path)
return result
```

#### 4. Qwen via Xinference
```python
# In execute_tool("query_qwen_chat")
import openai

client = openai.Client(
    api_key="not-empty",
    base_url="http://localhost:9997/v1"
)
response = client.chat.completions.create(
    model="qwen1.5-chat",
    messages=[{"role": "user", "content": message}]
)
return {"response": response.choices[0].message.content}
```

## 🔗 Architecture Integration

### Unified Inference System Stack

```
User Query
    ↓
Claude Orchestrator (Natural Language → Tool Selection)
    ↓
┌──────────────────┬──────────────────┬──────────────────┐
│   CUDA-Q QAOA    │    YOLO11s       │    Qwen 1.5      │
│   124 MB VRAM    │    1.2 GB VRAM   │    2.5 GB VRAM   │
└──────────────────┴──────────────────┴──────────────────┘
    ↓
Diamond Gateway (VRAM Monitoring, H_resource)
    ↓
Notion Bridge (Context Offload when H > 8.5)
```

### Monitoring Integration

```python
# Add to execute_tool() for AppSignal tracking
from opentelemetry import trace, metrics

tracer = trace.get_tracer("claude-orchestrator")
meter = metrics.get_meter("claude-orchestrator")

async def execute_tool(self, tool_name, tool_input):
    with tracer.start_as_current_span("tool_execution",
                                      attributes={"tool": tool_name}):
        result = await self._execute_tool_impl(tool_name, tool_input)
        
        # Track metrics
        counter = meter.create_counter("tool_calls_total")
        counter.add(1, {"tool": tool_name, "status": "success"})
        
        return result
```

## 💰 Cost Optimization

### Prompt Caching
The system prompt (~500 tokens) is cached with 90% cost reduction:

```python
system=[{
    "type": "text", 
    "text": self.system_prompt,
    "cache_control": {"type": "ephemeral"}  # 5-minute TTL
}]
```

**Cost per turn:**
- First message: ~$0.05 (full system prompt)
- Subsequent (within 5 min): ~$0.005 (cached)

### Token Usage
- Input: ~1000-2000 tokens (query + history + tools)
- Output: ~500-1000 tokens (response + tool calls)
- Total per turn: ~$0.02-0.05 (with caching)

## 🎨 Customization

### Change Model
```python
orchestrator = ClaudeOrchestrator()
# Then in chat(), modify:
response = self.client.messages.create(
    model="claude-sonnet-4-6",  # Cheaper option
    # ... rest stays same
)
```

### Adjust Thinking
```python
thinking={"type": "adaptive", "display": "omitted"}  # Hide thinking blocks
# or
thinking={"type": "disabled"}  # No thinking (faster, cheaper)
```

### Modify Effort
```python
output_config={"effort": "high"}  # Balance quality/cost
# Options: "low", "medium", "high", "xhigh", "max"
```

## 📈 Next Steps

1. **Replace Mock Implementations** - Connect to real APIs
2. **Add Streaming** - Use `client.messages.stream()` for real-time UI
3. **Error Handling** - Add retries, fallbacks, rate limit handling
4. **Build Web UI** - FastAPI + WebSocket for chat interface
5. **Expand Tools** - Add more domain-specific capabilities
6. **Multi-Agent** - Use Claude Managed Agents for complex workflows

## 🔐 Security

**API Key Storage:**
```bash
# ~/.bashrc or ~/.profile
export ANTHROPIC_API_KEY="sk-ant-..."
export GATEWAY_SECRET="your-gateway-secret"
```

**Never hardcode API keys in source code.**

## 📚 Documentation

- **Claude API Skill**: `~/.agents/skills/claude-api/`
- **Anthropic SDK**: https://docs.anthropic.com/
- **Diamond Gateway**: `/opt/diamond-gateway/gateway.py`
- **Unified Architecture**: `~/UNIFIED_INFERENCE_ARCHITECTURE.md`

## ✅ Integration Checklist

- [x] Anthropic SDK installed
- [x] Claude orchestrator module created
- [x] 6 tools defined
- [x] Adaptive thinking enabled
- [x] Prompt caching configured
- [x] Mock implementations working
- [ ] Connect to Diamond Gateway
- [ ] Connect to CUDA-Q QAOA
- [ ] Connect to Xinference (YOLO11 + Qwen)
- [ ] Add AppSignal monitoring
- [ ] Add Vercel Analytics tracking
- [ ] Build web UI
- [ ] Deploy to production

---

**Status:** ✅ Claude API Orchestrator ready for integration!
