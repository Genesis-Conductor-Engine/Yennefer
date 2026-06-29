# Claude Orchestrator API Reference

Complete API documentation for the Claude Orchestrator component.

## Overview

The Claude Orchestrator provides a natural language interface to the Diamond Node unified inference system. It leverages Claude's AI capabilities with tool execution, prompt caching, and streaming responses.

## Class: `ClaudeOrchestrator`

Main orchestrator class for Claude AI integration.

### Constructor

```python
ClaudeOrchestrator(
    api_key: str,
    model: str = "claude-3-5-sonnet-20241022",
    max_tokens: int = 4096,
    enable_caching: bool = True,
    enable_streaming: bool = True
)
```

**Parameters:**
- `api_key`: Anthropic API key
- `model`: Claude model identifier
- `max_tokens`: Maximum response tokens
- `enable_caching`: Enable prompt caching (default: True)
- `enable_streaming`: Enable streaming responses (default: True)

### Methods

#### `chat()`

Send a message to Claude and execute tools.

```python
async def chat(
    message: str,
    system_prompt: Optional[str] = None,
    tools: Optional[List[Dict]] = None,
    context: Optional[Dict] = None
) -> Dict[str, Any]
```

**Parameters:**
- `message`: User message
- `system_prompt`: Optional system instructions
- `tools`: List of tool definitions (Anthropic format)
- `context`: Additional context data

**Returns:**
```python
{
    "content": str,              # Claude's response
    "tool_calls": List[Dict],    # Executed tools
    "usage": {
        "input_tokens": int,
        "output_tokens": int,
        "cache_read_tokens": int,
        "cache_creation_tokens": int
    },
    "stop_reason": str,
    "model": str
}
```

**Example:**
```python
orchestrator = ClaudeOrchestrator(api_key=os.getenv("ANTHROPIC_API_KEY"))

response = await orchestrator.chat(
    message="Analyze wallet 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    tools=blockchain_tools,
    context={"chain": "ethereum"}
)

print(response["content"])
```

#### `execute_tool()`

Execute a specific tool by name.

```python
async def execute_tool(
    tool_name: str,
    arguments: Dict[str, Any]
) -> Dict[str, Any]
```

**Parameters:**
- `tool_name`: Name of the tool to execute
- `arguments`: Tool arguments

**Returns:**
```python
{
    "tool_name": str,
    "result": Any,
    "error": Optional[str],
    "execution_time": float
}
```

**Example:**
```python
result = await orchestrator.execute_tool(
    tool_name="query_wallet_balance",
    arguments={
        "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        "chain": "ethereum"
    }
)
```

#### `stream_chat()`

Stream Claude's response in real-time.

```python
async def stream_chat(
    message: str,
    system_prompt: Optional[str] = None,
    tools: Optional[List[Dict]] = None
) -> AsyncGenerator[Dict[str, Any], None]
```

**Yields:**
```python
{
    "type": str,  # "text" | "tool_use" | "done"
    "data": Any,
    "metadata": Optional[Dict]
}
```

**Example:**
```python
async for chunk in orchestrator.stream_chat(message="Analyze this portfolio..."):
    if chunk["type"] == "text":
        print(chunk["data"], end="", flush=True)
    elif chunk["type"] == "tool_use":
        print(f"\n[Using tool: {chunk['data']['name']}]")
```

## Tool Definitions

Tools are defined using Anthropic's tool schema format.

### Tool Schema

```python
{
    "name": str,              # Tool identifier
    "description": str,       # What the tool does
    "input_schema": {
        "type": "object",
        "properties": {
            "param_name": {
                "type": str,  # "string" | "number" | "boolean" | "array" | "object"
                "description": str,
                "enum": Optional[List],
                "default": Optional[Any]
            }
        },
        "required": List[str]
    }
}
```

### Built-in Tools

#### Blockchain Tools

```python
BLOCKCHAIN_TOOLS = [
    {
        "name": "query_wallet_balance",
        "description": "Query cryptocurrency wallet balances",
        "input_schema": {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Wallet address"},
                "chain": {"type": "string", "enum": ["ethereum", "polygon", "arbitrum"]}
            },
            "required": ["address"]
        }
    },
    {
        "name": "analyze_portfolio_risk",
        "description": "Analyze portfolio risk metrics",
        "input_schema": {
            "type": "object",
            "properties": {
                "holdings": {"type": "array", "description": "Token holdings"},
                "risk_model": {"type": "string", "default": "monte_carlo"}
            },
            "required": ["holdings"]
        }
    }
]
```

#### YOLO11 Tools

```python
VISION_TOOLS = [
    {
        "name": "detect_objects",
        "description": "Detect objects in an image using YOLO11",
        "input_schema": {
            "type": "object",
            "properties": {
                "image_url": {"type": "string"},
                "confidence": {"type": "number", "default": 0.5}
            },
            "required": ["image_url"]
        }
    }
]
```

## Configuration Options

Configure the orchestrator via environment variables or constructor parameters.

### Environment Variables

```bash
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-3-5-sonnet-20241022
CLAUDE_MAX_TOKENS=4096
CLAUDE_ENABLE_CACHING=true
CLAUDE_ENABLE_STREAMING=true
```

### Runtime Configuration

```python
config = {
    "cache_ttl": 300,           # Cache TTL in seconds
    "max_tool_iterations": 5,   # Max tool calls per conversation
    "timeout": 60,              # Request timeout
    "retry_attempts": 3,        # Retry on failure
    "log_level": "INFO"
}

orchestrator = ClaudeOrchestrator(
    api_key=api_key,
    **config
)
```

## Prompt Caching

The orchestrator automatically caches system prompts and tool definitions.

### Cache Behavior

- **System prompts:** Cached for 5 minutes
- **Tool definitions:** Cached for 5 minutes
- **Context data:** Not cached (unique per request)

### Cache Metrics

```python
response = await orchestrator.chat(message="...")

print(f"Cache read tokens: {response['usage']['cache_read_tokens']}")
print(f"Cache creation tokens: {response['usage']['cache_creation_tokens']}")

# Calculate savings
savings = response['usage']['cache_read_tokens'] * 0.9  # 90% discount
print(f"Token cost savings: {savings}")
```

## Error Handling

All methods raise structured exceptions:

```python
from src.orchestrator.exceptions import (
    OrchestratorError,
    ToolExecutionError,
    APIError
)

try:
    response = await orchestrator.chat(message="...")
except ToolExecutionError as e:
    print(f"Tool failed: {e.tool_name} - {e.message}")
except APIError as e:
    print(f"API error: {e.status_code} - {e.message}")
except OrchestratorError as e:
    print(f"General error: {e}")
```

## Performance Optimization

### Best Practices

1. **Use prompt caching:** Include static context in system prompts
2. **Batch tool calls:** Execute multiple tools in one conversation turn
3. **Stream responses:** Use `stream_chat()` for better UX
4. **Reuse instances:** Create one orchestrator per session

### Example: Optimized Workflow

```python
# Create once per session
orchestrator = ClaudeOrchestrator(
    api_key=api_key,
    enable_caching=True,
    enable_streaming=True
)

# Reuse system prompt (cached)
system_prompt = """
You are a blockchain analytics assistant with access to:
- Wallet balance queries
- Portfolio risk analysis
- Gas fee optimization
- NFT metadata lookup
"""

# Multiple queries in same session
for user_query in user_queries:
    response = await orchestrator.chat(
        message=user_query,
        system_prompt=system_prompt,  # Cached after first call
        tools=blockchain_tools         # Cached after first call
    )
    process_response(response)
```

## Integration Examples

### FastAPI Endpoint

```python
from fastapi import FastAPI, HTTPException
from src.orchestrator import ClaudeOrchestrator

app = FastAPI()
orchestrator = ClaudeOrchestrator(api_key=os.getenv("ANTHROPIC_API_KEY"))

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        response = await orchestrator.chat(
            message=request.message,
            tools=request.tools,
            context=request.context
        )
        return response
    except OrchestratorError as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### CLI Interface

```python
async def main():
    orchestrator = ClaudeOrchestrator(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    print("Diamond Node AI Assistant")
    print("Type 'exit' to quit\n")
    
    while True:
        message = input("You: ")
        if message.lower() == "exit":
            break
        
        async for chunk in orchestrator.stream_chat(message=message):
            if chunk["type"] == "text":
                print(chunk["data"], end="", flush=True)
        print("\n")

if __name__ == "__main__":
    asyncio.run(main())
```

## Related Documentation

- [Streaming Implementation](../guides/STREAMING_IMPLEMENTATION.md)
- [Tool Development Guide](../guides/TOOL_DEVELOPMENT.md)
- [Prompt Caching Best Practices](../guides/PROMPT_CACHING.md)

---

**Last updated:** 2025-05-12
