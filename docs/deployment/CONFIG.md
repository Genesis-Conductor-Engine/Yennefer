# Configuration Management for Claude Orchestrator

This document describes the production-ready configuration management system for the Unified Inference System.

## Overview

The configuration system provides:
- **Environment-based configuration** (DEV, STAGING, PRODUCTION)
- **Secure secret management** via .env files
- **Type-safe configuration classes**
- **Health checks** for all system components
- **Retry policies** with exponential backoff
- **Rate limiting** controls

## Quick Start

### 1. Install Dependencies

```bash
pip install python-dotenv aiohttp
```

### 2. Create Configuration File

Copy the example configuration:

```bash
cp unified_inference/.env.example ~/.env
```

Edit `~/.env` and add your API keys:

```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
GATEWAY_SECRET=your-gateway-secret
```

### 3. Test Configuration

```bash
cd ~/unified_inference
python config.py
```

### 4. Run Health Check

```bash
cd ~/unified_inference
python health_check.py
```

## Configuration Files

### Environment Files

| File | Purpose | Priority |
|------|---------|----------|
| `~/.env` | Base configuration (all environments) | Low |
| `~/.env.production` | Production overrides | High |
| `~/.env.staging` | Staging overrides | High |

The system loads:
1. Base `.env` file first
2. Environment-specific file (`.env.production` or `.env.staging`) overrides base

### Selecting Environment

Set the `ENVIRONMENT` variable:

```bash
# Development (default)
ENVIRONMENT=dev

# Staging
ENVIRONMENT=staging

# Production
ENVIRONMENT=production
```

Or set it at runtime:

```bash
ENVIRONMENT=production python claude_orchestrator.py
```

## Configuration Classes

### APIConfig

API keys and model settings:

```python
from config import get_config

config = get_config()
print(config.api.claude_model)           # claude-opus-4-7
print(config.api.max_tokens_streaming)   # 64000
print(config.api.anthropic_api_key)      # Your API key
```

**Environment Variables:**
- `ANTHROPIC_API_KEY` (required)
- `GATEWAY_SECRET` (required for gateway operations)
- `INFURA_API_KEY` (optional, for blockchain tools)
- `ALCHEMY_API_KEY` (optional, for blockchain tools)
- `CLAUDE_MODEL` (default: claude-opus-4-7)
- `MAX_TOKENS_STREAMING` (default: 64000)
- `MAX_TOKENS_SYNC` (default: 16000)

### RateLimitConfig

Rate limiting controls:

```python
config.rate_limit.requests_per_minute    # 60
config.rate_limit.max_concurrent_requests # 5
config.rate_limit.burst_allowance        # 10
```

**Environment Variables:**
- `RATE_LIMIT_PER_MINUTE` (default: 60)
- `MAX_CONCURRENT_REQUESTS` (default: 5)
- `BURST_ALLOWANCE` (default: 10)

### TimeoutConfig

Timeout settings for all operations:

```python
config.timeout.request_timeout      # 300 seconds
config.timeout.gateway_timeout      # 30 seconds
config.timeout.cuda_q_timeout       # 120 seconds
config.timeout.yolo_timeout         # 60 seconds
config.timeout.qwen_timeout         # 180 seconds
```

**Environment Variables:**
- `REQUEST_TIMEOUT` (default: 300)
- `HEALTH_CHECK_TIMEOUT` (default: 10)
- `CUDA_Q_TIMEOUT` (default: 120)
- `YOLO_TIMEOUT` (default: 60)
- `QWEN_TIMEOUT` (default: 180)
- `GATEWAY_TIMEOUT` (default: 30)

### RetryConfig

Retry policy with exponential backoff:

```python
config.retry.max_retries           # 3
config.retry.backoff_base          # 2 (exponential: 2^n)
config.retry.backoff_max           # 60 seconds
config.retry.retry_on_timeout      # True
config.retry.retry_on_rate_limit   # True

# Calculate backoff delay
delay = config.retry.get_backoff_delay(attempt=2)  # Returns 4 seconds (2^2)
```

**Environment Variables:**
- `MAX_RETRIES` (default: 3)
- `RETRY_BACKOFF_BASE` (default: 2)
- `RETRY_BACKOFF_MAX` (default: 60)
- `RETRY_ON_TIMEOUT` (default: true)
- `RETRY_ON_RATE_LIMIT` (default: true)

### GatewayConfig

Diamond Gateway endpoints:

```python
config.gateway.gateway_url          # http://127.0.0.1:8000
config.gateway.health_url           # http://127.0.0.1:8000/health
config.gateway.metrics_url          # http://127.0.0.1:8000/metrics
config.gateway.orchestrate_url      # http://127.0.0.1:8000/v1/orchestrate
```

**Environment Variables:**
- `GATEWAY_URL` (default: http://127.0.0.1:8000)

## Health Checks

The health check module verifies all system components:

```bash
python health_check.py
```

### Components Checked

| Component | Status | Critical? |
|-----------|--------|-----------|
| Configuration | Valid/Invalid | ✓ Yes |
| Diamond Gateway | Healthy/Unhealthy | ✓ Yes |
| CUDA-Q | Available/Unavailable | ✗ No |
| Xinference | Running/Not Running | ✗ No |

**Exit Codes:**
- `0`: System is ready (all critical components healthy)
- `1`: System is degraded (critical component failed)

### Programmatic Health Check

```python
from health_check import HealthChecker
import asyncio

async def check_system():
    checker = HealthChecker()
    result = await checker.check_all()
    
    print(f"Status: {result['status']}")
    print(f"Ready: {result['ready']}")
    print(f"Gateway: {result['components']['gateway']['status']}")

asyncio.run(check_system())
```

## Usage in Code

### Basic Usage

```python
from config import get_config
from claude_orchestrator import ClaudeOrchestrator

# Load configuration (uses environment variables)
config = get_config()

# Create orchestrator with config
orchestrator = ClaudeOrchestrator()

# Config is automatically loaded in orchestrator
print(orchestrator.model)        # claude-opus-4-7
print(orchestrator.max_tokens)   # 64000
```

### Environment-Specific Configuration

```python
from config import init_config

# Force production environment
config = init_config(environment="production")

# Reload configuration
config = get_config(reload=True)
```

### Export Configuration (Safe)

```python
config = get_config()
config_dict = config.to_dict()

# Returns sanitized config (no secrets)
print(config_dict['api']['has_anthropic_key'])  # True/False
print(config_dict['rate_limit']['requests_per_minute'])  # 60
```

## Production Deployment

### 1. Create Production Configuration

```bash
cat > ~/.env.production << 'EOF'
ENVIRONMENT=production
ANTHROPIC_API_KEY=sk-ant-api03-prod-...
GATEWAY_SECRET=production-secret-here
CLAUDE_MODEL=claude-opus-4-7
MAX_TOKENS_STREAMING=64000
RATE_LIMIT_PER_MINUTE=100
MAX_RETRIES=5
REQUEST_TIMEOUT=600
GATEWAY_URL=https://gateway.production.example.com
EOF
```

### 2. Set Environment

```bash
export ENVIRONMENT=production
```

### 3. Verify Configuration

```bash
python config.py
python health_check.py
```

### 4. Run Orchestrator

```bash
python claude_orchestrator.py
```

## Security Best Practices

### ✓ DO

- Store secrets in `.env` files in home directory
- Use environment-specific files for production
- Add `.env*` to `.gitignore`
- Use strong, unique secrets
- Rotate API keys regularly
- Set restrictive file permissions: `chmod 600 ~/.env*`

### ✗ DON'T

- Commit `.env` files to version control
- Share API keys or secrets
- Use development secrets in production
- Hardcode secrets in code
- Log secrets or API keys
- Use weak or default secrets

## Troubleshooting

### Configuration Not Loading

**Problem:** Environment variables not being read

**Solution:**
1. Check `.env` file exists: `ls -la ~/.env`
2. Check file permissions: `chmod 600 ~/.env`
3. Verify ENVIRONMENT variable: `echo $ENVIRONMENT`
4. Test loading: `python config.py`

### Health Check Fails

**Problem:** Health check returns "degraded" status

**Solution:**
1. Check gateway is running: `sudo systemctl status diamond-gateway`
2. Test gateway manually: `curl http://localhost:8000/health`
3. Verify API key: `python -c "from config import get_config; c=get_config(); print('✓' if c.api.anthropic_api_key else '✗')"`
4. Check logs: `sudo journalctl -u diamond-gateway -n 50`

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'dotenv'`

**Solution:**
```bash
pip install python-dotenv aiohttp
```

### Gateway Authentication Fails

**Problem:** Gateway returns 401 or 403

**Solution:**
1. Check `GATEWAY_SECRET` matches: `/etc/default/diamond-gateway`
2. Verify in config: `python -c "from config import get_config; print(get_config().api.gateway_secret)"`
3. Test manually: `curl -H "Authorization: Bearer $GATEWAY_SECRET" http://localhost:8000/metrics`

## Configuration Reference

See `.env.example` for complete configuration options with documentation.

## Files

| File | Description |
|------|-------------|
| `config.py` | Configuration management module |
| `health_check.py` | Health check module |
| `.env.example` | Example configuration file |
| `CONFIG.md` | This documentation |
| `~/.env` | Base environment configuration |
| `~/.env.production` | Production overrides |
| `~/.env.staging` | Staging overrides |

## API Reference

### Config Class

```python
class Config:
    environment: Environment      # DEV, STAGING, or PRODUCTION
    api: APIConfig               # API keys and model settings
    rate_limit: RateLimitConfig  # Rate limiting
    timeout: TimeoutConfig       # Timeouts
    retry: RetryConfig           # Retry policy
    gateway: GatewayConfig       # Gateway endpoints
    notion: NotionConfig         # Notion integration
    
    def to_dict(self) -> Dict[str, Any]:
        """Export config (sanitized, no secrets)"""
```

### Functions

```python
def get_config(reload: bool = False) -> Config:
    """Get global config instance"""

def init_config(environment: Optional[str] = None) -> Config:
    """Initialize config with specific environment"""
```

### HealthChecker Class

```python
class HealthChecker:
    async def check_gateway(self) -> Dict[str, Any]:
        """Check Diamond Gateway health"""
    
    def check_cuda_q(self) -> Dict[str, Any]:
        """Check CUDA-Q availability"""
    
    async def check_xinference(self) -> Dict[str, Any]:
        """Check Xinference status"""
    
    def check_config(self) -> Dict[str, Any]:
        """Validate configuration"""
    
    async def check_all(self) -> Dict[str, Any]:
        """Run all health checks"""
```

## Support

For issues or questions:
1. Check this documentation
2. Run health check: `python health_check.py`
3. Verify configuration: `python config.py`
4. Check gateway logs: `sudo journalctl -u diamond-gateway -f`
