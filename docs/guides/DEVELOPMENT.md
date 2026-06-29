# Development Guide

Complete guide for setting up and developing Diamond Node locally.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Development Environment](#development-environment)
- [Running Services](#running-services)
- [Code Style](#code-style)
- [Debugging](#debugging)
- [Hot Reload](#hot-reload)

## Prerequisites

### System Requirements

- **OS:** Ubuntu 20.04+ / Debian 11+ / macOS 12+
- **Python:** 3.10+
- **Node.js:** 18+
- **CUDA:** 11.8+ (for GPU features)
- **Memory:** 16GB+ RAM
- **GPU:** NVIDIA GPU with 8GB+ VRAM (optional but recommended)

### Required Tools

```bash
# Python tools
python3 --version  # 3.10+
pip3 --version

# Node.js tools
node --version     # 18+
npm --version

# CUDA (optional)
nvcc --version     # 11.8+

# Git
git --version
```

## Initial Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/diamondnode-unified-inference.git
cd diamondnode-unified-inference
```

### 2. Create Python Virtual Environment

```bash
# Create venv
python3 -m venv venv

# Activate
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate   # Windows

# Upgrade pip
pip install --upgrade pip
```

### 3. Install Dependencies

```bash
# Python dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development tools

# Node.js dependencies (for web UI)
cd web
npm install
cd ..
```

### 4. Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit configuration
nano .env
```

**Required environment variables:**

```bash
# Anthropic API
ANTHROPIC_API_KEY=sk-ant-...

# Blockchain RPC
ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/...
ALCHEMY_API_KEY=...

# Optional: Monitoring
APPSIGNAL_API_KEY=...
LANGSMITH_API_KEY=...

# Development
DEBUG=true
LOG_LEVEL=DEBUG
```

### 5. Download Models

```bash
# Create models directory
mkdir -p models

# Download YOLO11 model
wget -O models/yolo11n.pt https://github.com/ultralytics/assets/releases/download/v0.0.0/yolo11n.pt

# Verify
ls -lh models/
```

### 6. Initialize Database

```bash
# Run migrations
python scripts/db_migrate.py

# Seed test data (optional)
python scripts/db_seed.py
```

## Development Environment

### IDE Setup

#### VS Code

Recommended extensions:

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.black-formatter",
    "charliermarsh.ruff",
    "ms-toolsai.jupyter",
    "streetsidesoftware.code-spell-checker"
  ]
}
```

Settings (`.vscode/settings.json`):

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

#### PyCharm

1. Open project
2. Configure interpreter: Settings → Project → Python Interpreter → Add → Virtualenv
3. Enable Black formatter: Settings → Tools → Black
4. Enable Ruff: Settings → Tools → External Tools → Add Ruff

### Directory Structure

```
diamondnode-unified-inference/
├── src/                    # Source code
│   ├── orchestrator/      # Claude orchestrator
│   ├── blockchain_tools/  # Blockchain analytics
│   ├── yolo11/           # Object detection
│   ├── cuda_q/           # Quantum optimization
│   └── mcp_apps/         # MCP apps
├── tests/                 # Test suite
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── web/                   # Web UI
│   ├── src/
│   └── public/
├── docs/                  # Documentation
├── scripts/              # Utility scripts
├── config/               # Configuration files
└── models/               # ML models
```

## Running Services

### Backend API

```bash
# Development mode (auto-reload)
python -m uvicorn src.main:app --reload --port 8000

# With debugging
python -m debugpy --listen 5678 -m uvicorn src.main:app --reload
```

### Web UI

```bash
cd web
npm run dev
```

Access at: http://localhost:3000

### All Services (Docker Compose)

```bash
docker-compose -f docker-compose.dev.yml up
```

Services:
- API: http://localhost:8000
- Web: http://localhost:3000
- Database: localhost:5432
- Redis: localhost:6379

## Code Style

### Python Style Guide

We follow **PEP 8** with some customizations.

#### Formatting with Black

```bash
# Format all files
black src/ tests/

# Check without modifying
black --check src/ tests/
```

#### Linting with Ruff

```bash
# Lint all files
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/
```

#### Type Checking with mypy

```bash
# Type check
mypy src/

# Strict mode
mypy --strict src/
```

### Import Organization

```python
# Standard library
import os
import sys
from typing import Dict, List, Optional

# Third-party
import anthropic
import httpx
from fastapi import FastAPI

# Local
from src.orchestrator import ClaudeOrchestrator
from src.blockchain_tools import query_wallet_balance
```

### Docstrings

Use Google-style docstrings:

```python
async def query_wallet_balance(
    address: str,
    chain: str = "ethereum"
) -> Dict[str, Any]:
    """Query cryptocurrency wallet balances.
    
    Args:
        address: Wallet address (0x...)
        chain: Blockchain network (default: "ethereum")
    
    Returns:
        Dictionary containing balance information:
        - address: Wallet address
        - native_balance: Native token balance
        - tokens: List of ERC-20 tokens
        - total_usd_value: Total portfolio value
    
    Raises:
        InvalidAddressError: If address format is invalid
        RPCError: If RPC request fails
    
    Example:
        >>> result = await query_wallet_balance("0x742d35...")
        >>> print(result['total_usd_value'])
        48500.23
    """
    pass
```

### Code Comments

```python
# Good: Explains WHY
# Cache wallet queries to reduce RPC load and improve response time
@lru_cache(maxsize=100)
async def cached_query(address: str):
    pass

# Bad: Explains WHAT (code is self-explanatory)
# Get the wallet balance
balance = await query_wallet_balance(address)
```

## Debugging

### Python Debugger (pdb)

```python
import pdb

async def problematic_function():
    result = await some_operation()
    pdb.set_trace()  # Breakpoint
    return result
```

### VS Code Debugging

`.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["src.main:app", "--reload"],
      "jinja": true
    },
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal"
    }
  ]
}
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

async def my_function():
    logger.debug("Starting operation")
    logger.info("Processing request")
    logger.warning("High memory usage")
    logger.error("Operation failed", exc_info=True)
```

Configure logging:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)
```

### Request Tracing

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def traced_function():
    with tracer.start_as_current_span("operation_name"):
        result = await expensive_operation()
        return result
```

## Hot Reload

### Python (Uvicorn)

Auto-reload on file changes:

```bash
uvicorn src.main:app --reload
```

### Web UI (Vite)

```bash
cd web
npm run dev
```

Hot module replacement (HMR) enabled by default.

### Docker Compose

Mount source as volume:

```yaml
services:
  api:
    volumes:
      - ./src:/app/src
      - ./tests:/app/tests
    command: uvicorn src.main:app --reload --host 0.0.0.0
```

## Testing During Development

### Run Specific Tests

```bash
# Single test file
pytest tests/unit/test_orchestrator.py

# Single test function
pytest tests/unit/test_orchestrator.py::test_chat

# With output
pytest -v -s tests/unit/test_orchestrator.py
```

### Watch Mode

```bash
# Install pytest-watch
pip install pytest-watch

# Run in watch mode
ptw -- tests/
```

### Coverage

```bash
pytest --cov=src --cov-report=html tests/
open htmlcov/index.html
```

## Common Development Tasks

### Add New Tool

1. Create tool module:
```bash
touch src/tools/my_tool.py
```

2. Implement tool:
```python
async def my_tool(param: str) -> Dict[str, Any]:
    """Tool description."""
    return {"result": "..."}
```

3. Add to tool registry:
```python
# src/tools/__init__.py
from .my_tool import my_tool

TOOLS = [
    {
        "name": "my_tool",
        "description": "...",
        "input_schema": {...}
    }
]
```

4. Add tests:
```python
# tests/unit/test_my_tool.py
async def test_my_tool():
    result = await my_tool("test")
    assert result["result"] == "..."
```

### Add API Endpoint

```python
# src/main.py
from fastapi import FastAPI

app = FastAPI()

@app.post("/api/my-endpoint")
async def my_endpoint(request: MyRequest):
    """Endpoint description."""
    result = await process_request(request)
    return result
```

### Database Migration

```bash
# Create migration
alembic revision -m "Add new column"

# Edit migration file
nano alembic/versions/xxx_add_new_column.py

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Troubleshooting

### "Module not found" Error

```bash
# Ensure venv is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Verify installation
pip list
```

### CUDA Not Available

```bash
# Check CUDA installation
nvcc --version
nvidia-smi

# Reinstall PyTorch with CUDA
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Database Connection Error

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -U postgres -h localhost -p 5432
```

## Performance Profiling

### Python Profiler

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Your code here
await expensive_function()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)  # Top 10 functions
```

### Memory Profiling

```bash
# Install memory_profiler
pip install memory_profiler

# Profile function
python -m memory_profiler src/my_module.py
```

### API Benchmarking

```bash
# Install wrk
sudo apt install wrk

# Benchmark endpoint
wrk -t4 -c100 -d30s http://localhost:8000/api/endpoint
```

## Related Documentation

- [Testing Guide](TESTING.md)
- [Contributing Guide](../../CONTRIBUTING.md)
- [API Reference](../api/)
- [Production Deployment](../deployment/PRODUCTION_DEPLOYMENT_COMPLETE.md)

---

**Last updated:** 2025-05-12
