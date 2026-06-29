# Testing Guide

Complete guide for testing Diamond Node unified inference system.

## Table of Contents

- [Testing Philosophy](#testing-philosophy)
- [Test Structure](#test-structure)
- [Unit Tests](#unit-tests)
- [Integration Tests](#integration-tests)
- [End-to-End Tests](#end-to-end-tests)
- [Benchmarking](#benchmarking)
- [Coverage](#coverage)

## Testing Philosophy

### Principles

1. **Test behavior, not implementation** - Focus on what the code does, not how
2. **Fast and reliable** - Tests should run quickly and produce consistent results
3. **Isolated** - Tests should not depend on each other
4. **Clear failures** - When tests fail, it should be obvious why

### Testing Pyramid

```
        /\
       /E2E\         <- Few, slow, high value
      /------\
     /  INT   \      <- Some, medium speed
    /----------\
   /    UNIT    \    <- Many, fast, focused
  /--------------\
```

- **Unit:** 70% - Fast, isolated function tests
- **Integration:** 20% - Component interaction tests
- **E2E:** 10% - Full system workflow tests

## Test Structure

```
tests/
├── unit/                  # Unit tests
│   ├── test_orchestrator.py
│   ├── test_blockchain_tools.py
│   ├── test_yolo11.py
│   └── test_cuda_q.py
├── integration/           # Integration tests
│   ├── test_api_endpoints.py
│   ├── test_tool_execution.py
│   └── test_mcp_apps.py
├── e2e/                   # End-to-end tests
│   ├── test_portfolio_workflow.py
│   └── test_detection_workflow.py
├── benchmarks/            # Performance benchmarks
│   ├── test_inference_speed.py
│   └── test_optimization_time.py
├── fixtures/              # Test fixtures
│   ├── sample_images/
│   └── mock_data.py
└── conftest.py           # Pytest configuration
```

## Unit Tests

### Running Unit Tests

```bash
# All unit tests
pytest tests/unit/

# Specific file
pytest tests/unit/test_orchestrator.py

# Specific test
pytest tests/unit/test_orchestrator.py::test_chat_basic

# With output
pytest -v -s tests/unit/

# Parallel execution
pytest -n auto tests/unit/
```

### Writing Unit Tests

#### Example: Testing Orchestrator

```python
# tests/unit/test_orchestrator.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.orchestrator import ClaudeOrchestrator

@pytest.fixture
def orchestrator():
    """Create orchestrator instance for testing."""
    return ClaudeOrchestrator(
        api_key="test-key",
        model="claude-3-5-sonnet-20241022"
    )

@pytest.mark.asyncio
async def test_chat_basic(orchestrator, mocker):
    """Test basic chat functionality."""
    # Mock Anthropic API response
    mock_response = {
        "content": [{"text": "Hello!"}],
        "usage": {"input_tokens": 10, "output_tokens": 5},
        "stop_reason": "end_turn"
    }
    
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)
    mocker.patch.object(orchestrator, "client", mock_client)
    
    # Test
    result = await orchestrator.chat(message="Hi")
    
    # Assertions
    assert result["content"] == "Hello!"
    assert result["usage"]["input_tokens"] == 10
    mock_client.messages.create.assert_called_once()

@pytest.mark.asyncio
async def test_chat_with_tools(orchestrator, mocker):
    """Test chat with tool execution."""
    # Mock tool execution
    mock_tool_result = {"balance": 100.5}
    mocker.patch(
        "src.orchestrator.execute_tool",
        AsyncMock(return_value=mock_tool_result)
    )
    
    tools = [
        {
            "name": "get_balance",
            "description": "Get wallet balance",
            "input_schema": {"type": "object", "properties": {}}
        }
    ]
    
    result = await orchestrator.chat(
        message="Check my balance",
        tools=tools
    )
    
    assert "tool_calls" in result
    assert len(result["tool_calls"]) > 0

@pytest.mark.asyncio
async def test_chat_error_handling(orchestrator, mocker):
    """Test error handling in chat."""
    # Mock API error
    mock_client = AsyncMock()
    mock_client.messages.create.side_effect = Exception("API Error")
    mocker.patch.object(orchestrator, "client", mock_client)
    
    # Should raise exception
    with pytest.raises(Exception, match="API Error"):
        await orchestrator.chat(message="Hi")
```

#### Example: Testing Blockchain Tools

```python
# tests/unit/test_blockchain_tools.py
import pytest
from unittest.mock import AsyncMock
from src.blockchain_tools import query_wallet_balance

@pytest.mark.asyncio
async def test_query_wallet_balance_success(mocker):
    """Test successful wallet balance query."""
    # Mock RPC response
    mock_rpc = AsyncMock()
    mock_rpc.eth.get_balance.return_value = 1000000000000000000  # 1 ETH
    mocker.patch("src.blockchain_tools.get_rpc_client", return_value=mock_rpc)
    
    result = await query_wallet_balance(
        address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        chain="ethereum"
    )
    
    assert result["address"] == "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
    assert result["native_balance"]["balance"] == 1.0
    assert result["native_balance"]["symbol"] == "ETH"

@pytest.mark.asyncio
async def test_query_wallet_balance_invalid_address():
    """Test invalid address handling."""
    with pytest.raises(ValueError, match="Invalid address"):
        await query_wallet_balance(
            address="invalid",
            chain="ethereum"
        )
```

### Mocking Best Practices

```python
# Good: Mock external dependencies
mocker.patch("httpx.AsyncClient.post", return_value=mock_response)

# Good: Mock at the boundary
mocker.patch("src.orchestrator.anthropic.Anthropic", return_value=mock_client)

# Bad: Mock internal implementation details
mocker.patch("src.orchestrator._internal_helper")
```

## Integration Tests

### Running Integration Tests

```bash
# All integration tests
pytest tests/integration/

# With real API (requires env vars)
pytest tests/integration/ --use-real-api

# Skip slow tests
pytest tests/integration/ -m "not slow"
```

### Writing Integration Tests

#### Example: API Endpoints

```python
# tests/integration/test_api_endpoints.py
import pytest
from httpx import AsyncClient
from src.main import app

@pytest.fixture
async def client():
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Test /health endpoint."""
    response = await client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded", "unhealthy"]
    assert "components" in data
    assert "metrics" in data

@pytest.mark.asyncio
async def test_chat_endpoint(client, mocker):
    """Test /api/chat endpoint."""
    # Mock Claude API to avoid real API calls
    mock_chat = AsyncMock(return_value={"content": "Test response"})
    mocker.patch("src.orchestrator.ClaudeOrchestrator.chat", mock_chat)
    
    response = await client.post(
        "/api/chat",
        json={"message": "Hello"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "content" in data

@pytest.mark.asyncio
async def test_mcp_apps_endpoint(client):
    """Test /mcp endpoint (JSON-RPC)."""
    response = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "method": "apps/list",
            "params": {},
            "id": 1
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert "result" in data
    assert "apps" in data["result"]
```

#### Example: Tool Execution

```python
# tests/integration/test_tool_execution.py
import pytest
from src.orchestrator import ClaudeOrchestrator
from src.blockchain_tools import BLOCKCHAIN_TOOLS

@pytest.mark.integration
@pytest.mark.asyncio
async def test_orchestrator_with_blockchain_tools(mocker):
    """Test orchestrator executing blockchain tools."""
    orchestrator = ClaudeOrchestrator(api_key="test-key")
    
    # Mock blockchain query
    mock_balance = {
        "address": "0x742d35...",
        "total_usd_value": 50000
    }
    mocker.patch(
        "src.blockchain_tools.query_wallet_balance",
        AsyncMock(return_value=mock_balance)
    )
    
    # Mock Claude response with tool call
    mock_response = {
        "content": "The wallet has $50,000",
        "tool_calls": [
            {
                "name": "query_wallet_balance",
                "arguments": {"address": "0x742d35..."}
            }
        ]
    }
    mocker.patch.object(
        orchestrator,
        "chat",
        AsyncMock(return_value=mock_response)
    )
    
    result = await orchestrator.chat(
        message="Check wallet 0x742d35...",
        tools=BLOCKCHAIN_TOOLS
    )
    
    assert "50,000" in result["content"]
    assert len(result["tool_calls"]) == 1
```

## End-to-End Tests

### Running E2E Tests

```bash
# All E2E tests
pytest tests/e2e/

# Requires real services (API, DB, etc.)
docker-compose -f docker-compose.test.yml up -d
pytest tests/e2e/
docker-compose -f docker-compose.test.yml down
```

### Writing E2E Tests

```python
# tests/e2e/test_portfolio_workflow.py
import pytest
from httpx import AsyncClient

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_portfolio_analysis():
    """Test complete portfolio analysis workflow."""
    client = AsyncClient(base_url="http://localhost:8000")
    
    # 1. Query wallet balance
    response = await client.post(
        "/api/blockchain/query_wallet",
        json={
            "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
            "chain": "ethereum"
        }
    )
    assert response.status_code == 200
    balance = response.json()
    
    # 2. Analyze risk
    response = await client.post(
        "/api/blockchain/analyze_risk",
        json={"holdings": balance["tokens"]}
    )
    assert response.status_code == 200
    risk = response.json()
    
    # 3. Generate AI report with Claude
    response = await client.post(
        "/api/chat",
        json={
            "message": f"Analyze this portfolio: {risk}",
            "tools": []
        }
    )
    assert response.status_code == 200
    report = response.json()
    
    # Verify complete workflow
    assert "risk_score" in risk
    assert "content" in report
    assert len(report["content"]) > 0
```

## Benchmarking

### Performance Benchmarks

```python
# tests/benchmarks/test_inference_speed.py
import pytest
import time
from src.yolo11 import YOLO11Detector

@pytest.mark.benchmark
def test_yolo11_inference_speed(benchmark):
    """Benchmark YOLO11 inference speed."""
    detector = YOLO11Detector(model_path="models/yolo11n.pt")
    
    async def run_detection():
        return await detector.detect(
            image_url="tests/fixtures/sample_images/test.jpg",
            confidence=0.5
        )
    
    result = benchmark(run_detection)
    
    # Assertions
    assert result is not None
    assert benchmark.stats.mean < 0.1  # < 100ms average
```

### Custom Benchmarks

```python
import time
from statistics import mean, stdev

async def benchmark_function(func, iterations=100):
    """Benchmark a function over multiple iterations."""
    times = []
    
    for _ in range(iterations):
        start = time.perf_counter()
        await func()
        end = time.perf_counter()
        times.append(end - start)
    
    return {
        "mean": mean(times),
        "stdev": stdev(times),
        "min": min(times),
        "max": max(times),
        "iterations": iterations
    }

# Usage
async def test_orchestrator_performance():
    orchestrator = ClaudeOrchestrator(api_key="...")
    
    async def chat():
        await orchestrator.chat(message="Hello")
    
    results = await benchmark_function(chat, iterations=50)
    print(f"Mean: {results['mean']*1000:.2f}ms")
    print(f"Stdev: {results['stdev']*1000:.2f}ms")
```

## Coverage

### Running Coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=html tests/

# View HTML report
open htmlcov/index.html

# Terminal report
pytest --cov=src --cov-report=term-missing tests/

# Fail if coverage below threshold
pytest --cov=src --cov-fail-under=80 tests/
```

### Coverage Configuration

```ini
# setup.cfg or pytest.ini
[coverage:run]
source = src/
omit = 
    */tests/*
    */venv/*
    */__pycache__/*

[coverage:report]
precision = 2
show_missing = True
skip_covered = False

[coverage:html]
directory = htmlcov
```

### Coverage Goals

- **Overall:** 80%+
- **Critical paths:** 95%+
- **New code:** 90%+

## Test Fixtures

### Shared Fixtures

```python
# tests/conftest.py
import pytest
from src.orchestrator import ClaudeOrchestrator

@pytest.fixture
def api_key():
    """Provide test API key."""
    return "test-api-key"

@pytest.fixture
def orchestrator(api_key):
    """Provide orchestrator instance."""
    return ClaudeOrchestrator(api_key=api_key)

@pytest.fixture
async def async_client():
    """Provide async HTTP client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def sample_image():
    """Provide sample image path."""
    return "tests/fixtures/sample_images/test.jpg"

@pytest.fixture
def mock_wallet_balance():
    """Provide mock wallet balance data."""
    return {
        "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        "native_balance": {"symbol": "ETH", "balance": 10.5},
        "tokens": [
            {"symbol": "USDC", "balance": 5000, "usd_value": 5000}
        ],
        "total_usd_value": 26000
    }
```

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run tests
        run: |
          pytest tests/ --cov=src --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

## Best Practices

### Test Naming

```python
# Good: Descriptive names
def test_chat_returns_valid_response_with_tool_calls():
    pass

def test_wallet_query_raises_error_on_invalid_address():
    pass

# Bad: Vague names
def test_chat():
    pass

def test_error():
    pass
```

### Arrange-Act-Assert Pattern

```python
async def test_example():
    # Arrange: Set up test data
    orchestrator = ClaudeOrchestrator(api_key="test")
    message = "Hello"
    
    # Act: Execute the operation
    result = await orchestrator.chat(message=message)
    
    # Assert: Verify the outcome
    assert result["content"] is not None
    assert len(result["content"]) > 0
```

### Test Independence

```python
# Good: Tests are independent
def test_a():
    result = function_a()
    assert result == expected

def test_b():
    result = function_b()
    assert result == expected

# Bad: Tests depend on each other
shared_state = None

def test_a():
    global shared_state
    shared_state = function_a()

def test_b():  # Depends on test_a running first!
    result = function_b(shared_state)
```

## Troubleshooting

### Async Tests Not Running

```python
# Install pytest-asyncio
pip install pytest-asyncio

# Mark async tests
@pytest.mark.asyncio
async def test_async_function():
    result = await async_operation()
    assert result is not None
```

### Mocks Not Working

```python
# Ensure you're patching the right location
# Patch where it's used, not where it's defined

# Wrong: Patching definition
mocker.patch("external_lib.function")

# Right: Patching usage
mocker.patch("src.my_module.function")
```

### Flaky Tests

```python
# Add retries for flaky tests
@pytest.mark.flaky(reruns=3, reruns_delay=2)
def test_flaky_operation():
    pass
```

## Related Documentation

- [Development Setup](DEVELOPMENT.md)
- [Contributing Guide](../../CONTRIBUTING.md)
- [API Reference](../api/)

---

**Last updated:** 2025-05-12
