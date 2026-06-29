# Copyright (c) 2026 Diamond Node Team
# Licensed under the MIT License - see LICENSE file for details

"""
Bot Protection & Rate Limiting for FastAPI
Comprehensive bot defense using slowapi, token-based auth, and intelligent throttling.

Approach:
- slowapi for distributed-friendly rate limiting (token bucket algorithm)
- Multi-tier IP-based limits (public, authenticated, whitelisted)
- API token authentication for trusted clients
- Security headers to prevent XSS, clickjacking, MIME sniffing
- Request validation and size limits
"""

import os
import time
import hashlib
import secrets
from enum import Enum
from typing import Optional, Dict, Set, Callable
from datetime import datetime, timedelta

from fastapi import Request, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


class RateLimitTier(str, Enum):
    """Rate limit tiers for different client types."""
    PUBLIC = "public"           # 10 req/min - anonymous users
    AUTHENTICATED = "authenticated"  # 100 req/min - valid API token
    WHITELISTED = "whitelisted"     # 1000 req/min - trusted IPs
    INTERNAL = "internal"           # unlimited - internal services


class SecurityConfig:
    """Bot protection configuration."""
    
    def __init__(self):
        # API token authentication
        self.api_tokens: Set[str] = self._load_api_tokens()
        self.token_header = "X-API-Token"
        
        # Whitelisted IPs (internal services, trusted partners)
        self.whitelisted_ips: Set[str] = {
            "127.0.0.1",
            "::1",
            "localhost"
        }
        
        # Rate limits per tier (requests per minute)
        self.rate_limits = {
            RateLimitTier.PUBLIC: "10/minute",
            RateLimitTier.AUTHENTICATED: "100/minute",
            RateLimitTier.WHITELISTED: "1000/minute",
            RateLimitTier.INTERNAL: "100000/minute"
        }
        
        # Request validation
        self.max_content_length = 10 * 1024 * 1024  # 10 MB
        self.max_json_keys = 1000
        self.max_string_length = 100_000
        
        # Security headers
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline'; "
                "connect-src 'self' ws: wss: http://localhost:*; "
                "img-src 'self' data:; "
                "font-src 'self' data:;"
            ),
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }
        
        # Suspicious patterns (common bot signatures)
        self.suspicious_user_agents = [
            "bot", "crawler", "spider", "scraper", "curl", "wget",
            "python-requests", "http.client", "apache-httpclient"
        ]
        
        # Exempt paths from rate limiting (health checks, static assets)
        self.exempt_paths = {
            "/api/health",
            "/health",
            "/static",
            "/favicon.ico"
        }
    
    def _load_api_tokens(self) -> Set[str]:
        """Load API tokens from environment."""
        tokens = set()
        
        # Load from environment variable (comma-separated)
        env_tokens = os.getenv("API_TOKENS", "")
        if env_tokens:
            tokens.update(t.strip() for t in env_tokens.split(",") if t.strip())
        
        # Load individual token (for backward compatibility)
        single_token = os.getenv("API_TOKEN", "")
        if single_token:
            tokens.add(single_token)
        
        # Generate default token for development if none exist
        if not tokens and os.getenv("ENVIRONMENT", "development") == "development":
            default_token = "dev-token-" + secrets.token_urlsafe(32)
            tokens.add(default_token)
            print(f"⚠️  No API tokens configured. Generated development token: {default_token}")
        
        return tokens
    
    def get_client_tier(self, request: Request) -> RateLimitTier:
        """Determine rate limit tier for a client."""
        client_ip = get_remote_address(request)
        
        # Check if internal/whitelisted IP
        if client_ip in self.whitelisted_ips:
            return RateLimitTier.INTERNAL
        
        # Check for valid API token
        token = request.headers.get(self.token_header)
        if token and token in self.api_tokens:
            return RateLimitTier.AUTHENTICATED
        
        # Default to public tier
        return RateLimitTier.PUBLIC
    
    def is_suspicious_request(self, request: Request) -> bool:
        """Check if request exhibits bot-like behavior."""
        user_agent = request.headers.get("user-agent", "").lower()
        
        # No user agent is suspicious
        if not user_agent:
            return True
        
        # Check for known bot signatures
        for pattern in self.suspicious_user_agents:
            if pattern in user_agent:
                return True
        
        return False


# Global security configuration
security_config = SecurityConfig()


def get_rate_limit_key(request: Request) -> str:
    """
    Custom rate limit key function that includes client tier.
    This allows different limits for different client types.
    """
    tier = security_config.get_client_tier(request)
    client_ip = get_remote_address(request)
    return f"{tier.value}:{client_ip}"


# Initialize slowapi rate limiter
limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=["100/minute"],  # Fallback limit
    storage_uri="memory://",  # Use in-memory storage (upgrade to Redis for production cluster)
    headers_enabled=True,  # Add rate limit info to response headers
)


def get_rate_limiter() -> Limiter:
    """Get the global rate limiter instance."""
    return limiter


async def require_api_token(request: Request) -> str:
    """
    FastAPI dependency for endpoints requiring authentication.
    
    Usage:
        @app.get("/api/protected")
        async def protected_endpoint(token: str = Depends(require_api_token)):
            return {"status": "authenticated"}
    """
    token = request.headers.get(security_config.token_header)
    
    if not token or token not in security_config.api_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token


class BotProtectionMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive bot protection middleware.
    
    Features:
    - Request size validation
    - Security headers injection
    - Suspicious pattern detection
    - Content-type validation
    """
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Skip protection for exempt paths
        if any(request.url.path.startswith(path) for path in security_config.exempt_paths):
            response = await call_next(request)
            return self._add_security_headers(response)
        
        # 1. Validate content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > security_config.max_content_length:
            return JSONResponse(
                status_code=413,
                content={
                    "error": "Request entity too large",
                    "max_size_mb": security_config.max_content_length / (1024 * 1024)
                }
            )
        
        # 2. Check for suspicious patterns
        if security_config.is_suspicious_request(request):
            # Don't block, just log and flag for stricter rate limiting
            request.state.suspicious = True
        
        # 3. Validate content-type for POST/PUT requests
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if not content_type or not any(ct in content_type for ct in ["application/json", "multipart/form-data", "application/x-www-form-urlencoded"]):
                return JSONResponse(
                    status_code=415,
                    content={"error": "Unsupported Media Type"}
                )
        
        # Process request
        try:
            response = await call_next(request)
        except RateLimitExceeded as exc:
            # Custom rate limit exceeded response
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "detail": str(exc),
                    "retry_after": 60,
                    "timestamp": datetime.utcnow().isoformat()
                },
                headers={"Retry-After": "60"}
            )
        except Exception as exc:
            # Log unexpected errors
            print(f"❌ Middleware error: {exc}")
            raise
        
        # Add security headers
        response = self._add_security_headers(response)
        
        # Add performance timing header
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        
        return response
    
    def _add_security_headers(self, response):
        """Add security headers to response."""
        for header, value in security_config.security_headers.items():
            response.headers[header] = value
        return response


def create_rate_limit_decorator(tier: RateLimitTier):
    """
    Create a rate limit decorator for a specific tier.
    
    Usage:
        public_limit = create_rate_limit_decorator(RateLimitTier.PUBLIC)
        
        @app.get("/api/public")
        @public_limit
        async def public_endpoint():
            return {"status": "ok"}
    """
    limit_string = security_config.rate_limits[tier]
    return limiter.limit(limit_string)


# Pre-configured decorators for common use cases
public_rate_limit = create_rate_limit_decorator(RateLimitTier.PUBLIC)
authenticated_rate_limit = create_rate_limit_decorator(RateLimitTier.AUTHENTICATED)
whitelisted_rate_limit = create_rate_limit_decorator(RateLimitTier.WHITELISTED)


def get_client_info(request: Request) -> Dict[str, any]:
    """
    Extract client information for logging/analytics.
    
    Returns:
        Dict with IP, user agent, tier, and other metadata
    """
    return {
        "ip": get_remote_address(request),
        "user_agent": request.headers.get("user-agent", "unknown"),
        "tier": security_config.get_client_tier(request).value,
        "suspicious": security_config.is_suspicious_request(request),
        "timestamp": datetime.utcnow().isoformat(),
        "path": request.url.path,
        "method": request.method
    }
