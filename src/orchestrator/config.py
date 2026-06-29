"""
Production Configuration Management for Claude Orchestrator
Supports DEV, STAGING, and PRODUCTION environments with secure secret management.
"""

import os
import sys
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    print("Warning: python-dotenv not installed. Run: pip install python-dotenv")
    load_dotenv = None


class Environment(Enum):
    """Environment types"""
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class APIConfig:
    """API configuration and authentication"""
    anthropic_api_key: str
    gateway_secret: Optional[str] = None
    infura_api_key: Optional[str] = None
    alchemy_api_key: Optional[str] = None
    claude_model: str = "claude-opus-4-7"
    max_tokens_streaming: int = 64000
    max_tokens_sync: int = 16000
    
    def __post_init__(self):
        if not self.anthropic_api_key:
            print("[Warning] ANTHROPIC_API_KEY is not set. API features will be disabled.")


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    requests_per_minute: int = 60
    max_concurrent_requests: int = 5
    burst_allowance: int = 10
    
    def __post_init__(self):
        if self.requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")


@dataclass
class TimeoutConfig:
    """Timeout configuration for various operations"""
    request_timeout: int = 300  # 5 minutes
    health_check_timeout: int = 10
    cuda_q_timeout: int = 120
    yolo_timeout: int = 60
    qwen_timeout: int = 180
    gateway_timeout: int = 30
    
    def __post_init__(self):
        if self.request_timeout <= 0:
            raise ValueError("request_timeout must be positive")


@dataclass
class RetryConfig:
    """Retry policy configuration"""
    max_retries: int = 3
    backoff_base: int = 2  # Exponential backoff: 2^n seconds
    backoff_max: int = 60  # Max wait between retries
    retry_on_timeout: bool = True
    retry_on_rate_limit: bool = True
    retry_status_codes: list = field(default_factory=lambda: [408, 429, 500, 502, 503, 504])
    
    def get_backoff_delay(self, attempt: int) -> int:
        """Calculate exponential backoff delay"""
        delay = min(self.backoff_base ** attempt, self.backoff_max)
        return delay


@dataclass
class GatewayConfig:
    """Diamond Gateway configuration"""
    gateway_url: str = "http://127.0.0.1:8000"
    health_endpoint: str = "/health"
    metrics_endpoint: str = "/metrics"
    orchestrate_endpoint: str = "/v1/orchestrate"
    
    @property
    def health_url(self) -> str:
        return f"{self.gateway_url}{self.health_endpoint}"
    
    @property
    def metrics_url(self) -> str:
        return f"{self.gateway_url}{self.metrics_endpoint}"
    
    @property
    def orchestrate_url(self) -> str:
        return f"{self.gateway_url}{self.orchestrate_endpoint}"


@dataclass
class NotionConfig:
    """Notion soul-capsule configuration"""
    worker_url: Optional[str] = None
    database_id: str = "21e416066ef1411084d1bbaf67af79d1"
    notion_token: Optional[str] = None


class Config:
    """
    Main configuration manager.
    Loads environment-specific settings from .env files.
    """
    
    def __init__(self, environment: Optional[str] = None):
        self.environment = self._determine_environment(environment)
        self._load_environment()
        
        # Initialize all configuration sections
        self.api = self._load_api_config()
        self.rate_limit = self._load_rate_limit_config()
        self.timeout = self._load_timeout_config()
        self.retry = self._load_retry_config()
        self.gateway = self._load_gateway_config()
        self.notion = self._load_notion_config()
    
    def _determine_environment(self, env: Optional[str]) -> Environment:
        """Determine the current environment"""
        env_str = env or os.environ.get("ENVIRONMENT", "dev").lower()
        try:
            return Environment(env_str)
        except ValueError:
            print(f"Warning: Unknown environment '{env_str}', defaulting to dev")
            return Environment.DEV
    
    def _load_environment(self):
        """Load environment variables from .env files"""
        if load_dotenv is None:
            return
        
        home_dir = Path.home()
        
        # Load base .env first
        base_env = home_dir / ".env"
        if base_env.exists():
            load_dotenv(base_env, override=False)
        
        # Load environment-specific .env (overrides base)
        if self.environment == Environment.PRODUCTION:
            env_file = home_dir / ".env.production"
        elif self.environment == Environment.STAGING:
            env_file = home_dir / ".env.staging"
        else:
            env_file = base_env  # Use base for dev
        
        if env_file.exists():
            load_dotenv(env_file, override=True)
    
    def _load_api_config(self) -> APIConfig:
        """Load API configuration"""
        return APIConfig(
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            gateway_secret=os.environ.get("GATEWAY_SECRET"),
            infura_api_key=os.environ.get("INFURA_API_KEY"),
            alchemy_api_key=os.environ.get("ALCHEMY_API_KEY"),
            claude_model=os.environ.get("CLAUDE_MODEL", "claude-opus-4-7"),
            max_tokens_streaming=int(os.environ.get("MAX_TOKENS_STREAMING", "64000")),
            max_tokens_sync=int(os.environ.get("MAX_TOKENS_SYNC", "16000"))
        )
    
    def _load_rate_limit_config(self) -> RateLimitConfig:
        """Load rate limit configuration"""
        return RateLimitConfig(
            requests_per_minute=int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60")),
            max_concurrent_requests=int(os.environ.get("MAX_CONCURRENT_REQUESTS", "5")),
            burst_allowance=int(os.environ.get("BURST_ALLOWANCE", "10"))
        )
    
    def _load_timeout_config(self) -> TimeoutConfig:
        """Load timeout configuration"""
        return TimeoutConfig(
            request_timeout=int(os.environ.get("REQUEST_TIMEOUT", "300")),
            health_check_timeout=int(os.environ.get("HEALTH_CHECK_TIMEOUT", "10")),
            cuda_q_timeout=int(os.environ.get("CUDA_Q_TIMEOUT", "120")),
            yolo_timeout=int(os.environ.get("YOLO_TIMEOUT", "60")),
            qwen_timeout=int(os.environ.get("QWEN_TIMEOUT", "180")),
            gateway_timeout=int(os.environ.get("GATEWAY_TIMEOUT", "30"))
        )
    
    def _load_retry_config(self) -> RetryConfig:
        """Load retry policy configuration"""
        return RetryConfig(
            max_retries=int(os.environ.get("MAX_RETRIES", "3")),
            backoff_base=int(os.environ.get("RETRY_BACKOFF_BASE", "2")),
            backoff_max=int(os.environ.get("RETRY_BACKOFF_MAX", "60")),
            retry_on_timeout=os.environ.get("RETRY_ON_TIMEOUT", "true").lower() == "true",
            retry_on_rate_limit=os.environ.get("RETRY_ON_RATE_LIMIT", "true").lower() == "true"
        )
    
    def _load_gateway_config(self) -> GatewayConfig:
        """Load Diamond Gateway configuration"""
        return GatewayConfig(
            gateway_url=os.environ.get("GATEWAY_URL", "http://127.0.0.1:8000")
        )
    
    def _load_notion_config(self) -> NotionConfig:
        """Load Notion configuration"""
        return NotionConfig(
            worker_url=os.environ.get("NOTION_WORKER_URL"),
            database_id=os.environ.get("NOTION_DATABASE_ID", "21e416066ef1411084d1bbaf67af79d1"),
            notion_token=os.environ.get("NOTION_TOKEN")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary (safe - no secrets)"""
        return {
            "environment": self.environment.value,
            "api": {
                "claude_model": self.api.claude_model,
                "max_tokens_streaming": self.api.max_tokens_streaming,
                "max_tokens_sync": self.api.max_tokens_sync,
                "has_gateway_secret": bool(self.api.gateway_secret),
                "has_anthropic_key": bool(self.api.anthropic_api_key),
                "has_infura_key": bool(self.api.infura_api_key),
                "has_alchemy_key": bool(self.api.alchemy_api_key)
            },
            "rate_limit": {
                "requests_per_minute": self.rate_limit.requests_per_minute,
                "max_concurrent_requests": self.rate_limit.max_concurrent_requests,
                "burst_allowance": self.rate_limit.burst_allowance
            },
            "timeout": {
                "request_timeout": self.timeout.request_timeout,
                "health_check_timeout": self.timeout.health_check_timeout,
                "cuda_q_timeout": self.timeout.cuda_q_timeout,
                "yolo_timeout": self.timeout.yolo_timeout,
                "qwen_timeout": self.timeout.qwen_timeout,
                "gateway_timeout": self.timeout.gateway_timeout
            },
            "retry": {
                "max_retries": self.retry.max_retries,
                "backoff_base": self.retry.backoff_base,
                "backoff_max": self.retry.backoff_max
            },
            "gateway": {
                "gateway_url": self.gateway.gateway_url,
                "health_url": self.gateway.health_url
            }
        }


# Global configuration instance
_config: Optional[Config] = None


def get_config(reload: bool = False) -> Config:
    """
    Get the global configuration instance.
    
    Args:
        reload: Force reload configuration from environment
    
    Returns:
        Config instance
    """
    global _config
    if _config is None or reload:
        _config = Config()
    return _config


def init_config(environment: Optional[str] = None) -> Config:
    """
    Initialize configuration with specific environment.
    
    Args:
        environment: Environment name (dev/staging/production)
    
    Returns:
        Config instance
    """
    global _config
    _config = Config(environment)
    return _config


if __name__ == "__main__":
    # CLI for testing configuration
    config = get_config()
    
    print("=" * 60)
    print("Claude Orchestrator Configuration")
    print("=" * 60)
    print(f"Environment: {config.environment.value.upper()}")
    print()
    
    print("API Configuration:")
    print(f"  Model: {config.api.claude_model}")
    print(f"  Max Tokens (streaming): {config.api.max_tokens_streaming}")
    print(f"  Max Tokens (sync): {config.api.max_tokens_sync}")
    print(f"  Anthropic API Key: {'✓' if config.api.anthropic_api_key else '✗'}")
    print(f"  Gateway Secret: {'✓' if config.api.gateway_secret else '✗'}")
    print()
    
    print("Rate Limits:")
    print(f"  Requests/min: {config.rate_limit.requests_per_minute}")
    print(f"  Max concurrent: {config.rate_limit.max_concurrent_requests}")
    print()
    
    print("Timeouts:")
    print(f"  Request: {config.timeout.request_timeout}s")
    print(f"  Gateway: {config.timeout.gateway_timeout}s")
    print(f"  CUDA-Q: {config.timeout.cuda_q_timeout}s")
    print()
    
    print("Retry Policy:")
    print(f"  Max retries: {config.retry.max_retries}")
    print(f"  Backoff: exponential (base={config.retry.backoff_base}, max={config.retry.backoff_max}s)")
    print()
    
    print("Gateway:")
    print(f"  URL: {config.gateway.gateway_url}")
    print(f"  Health: {config.gateway.health_url}")
    print("=" * 60)
