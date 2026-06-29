# Bot Protection for Diamond Node Unified Inference

## Overview

Diamond Node Web UI now includes comprehensive bot protection and rate limiting to prevent abuse, ensure fair resource allocation, and protect the inference system from malicious actors.

## Why Not BotID?

**BotID is JavaScript-only** and designed for browser-based client-side protection. Since our FastAPI application is a server-side Python application, we need server-side bot protection. We implemented a comprehensive solution using industry-standard Python libraries.

## Solution: Multi-Layered Bot Protection

### 1. Rate Limiting (slowapi)

**Library:** [slowapi](https://github.com/laurentS/slowapi) - FastAPI/Flask-compatible rate limiting using the token bucket algorithm.

**Features:**
- Token bucket algorithm (industry standard)
- Multi-tier rate limiting based on client type
- Automatic retry-after headers
- In-memory storage (upgrade to Redis for production clusters)

**Rate Limit Tiers:**
| Tier | Rate Limit | How to Qualify |
|------|-----------|----------------|
| Public | 10 req/min | Default for all clients |
| Authenticated | 100 req/min | Include valid `X-API-Token` header |
| Whitelisted | 1000 req/min | IP address in whitelist (internal services) |
| Internal | 100000 req/min | localhost/127.0.0.1 |

### 2. API Token Authentication

**Header:** `X-API-Token`

**Configuration:**
```bash
# Single token
export API_TOKEN="your-secure-token-here"

# Multiple tokens (comma-separated)
export API_TOKENS="token1,token2,token3"
```

**Usage:**
```bash
# Without token (10 req/min)
curl http://localhost:8080/api/chat

# With token (100 req/min)
curl -H "X-API-Token: your-token" http://localhost:8080/api/chat
```

### 3. Security Headers

All responses include security headers to prevent common attacks:

| Header | Value | Purpose |
|--------|-------|---------|
| X-Content-Type-Options | nosniff | Prevent MIME sniffing |
| X-Frame-Options | DENY | Prevent clickjacking |
| X-XSS-Protection | 1; mode=block | XSS protection |
| Strict-Transport-Security | max-age=31536000 | Force HTTPS |
| Content-Security-Policy | default-src 'self' | Restrict resource loading |
| Referrer-Policy | strict-origin-when-cross-origin | Control referrer info |

### 4. Request Validation

**Enforced Limits:**
- Max content length: 10 MB
- Max JSON keys: 1000
- Max string length: 100,000 chars
- Required content-type for POST/PUT/PATCH

### 5. Suspicious Pattern Detection

Automatically flags requests with bot-like signatures:
- Missing user-agent
- Known bot user-agents (curl, wget, python-requests, etc.)
- Suspicious activity patterns

**Note:** Flagged requests are not blocked, but may receive stricter rate limits.

## Endpoints

### Health Check (Exempt from Rate Limiting)
```bash
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "diamond-node-web-ui",
  "version": "1.0.0",
  "timestamp": "2026-05-19T20:41:00.000Z",
  "bot_protection": "enabled"
}
```

### Security Status
```bash
GET /api/security/status
```

**Response:**
```json
{
  "bot_protection": "enabled",
  "your_tier": "public",
  "rate_limit": "10/minute",
  "ip": "127.0.0.1",
  "suspicious": false,
  "features": {
    "rate_limiting": "slowapi",
    "token_auth": "X-API-Token header",
    "security_headers": true,
    "request_validation": true
  },
  "upgrade_info": {
    "authenticated": "Add X-API-Token header for 100 req/min",
    "whitelisted": "Contact admin for IP whitelisting (1000 req/min)"
  }
}
```

### Rate-Limited Endpoints

| Endpoint | Limit | Reason |
|----------|-------|--------|
| `/api/chat` | 10/min | LLM inference is expensive |
| `/api/vram` | 20/min | Monitoring endpoint |
| `/api/tools` | 30/min | Metadata endpoint |
| `/ws/chat` | Custom WebSocket rate limiting | Real-time streaming |

## Rate Limit Response

When rate limit is exceeded, you'll receive:

```json
HTTP/1.1 429 Too Many Requests
Retry-After: 60

{
  "error": "Rate limit exceeded",
  "detail": "10 per 1 minute",
  "retry_after": 60,
  "timestamp": "2026-05-19T20:41:00.000Z"
}
```

## Testing

### 1. Test Health Check (No Rate Limit)
```bash
for i in {1..20}; do
  curl http://localhost:8080/api/health
done
```
**Expected:** All requests succeed

### 2. Test Rate Limit (Public Tier)
```bash
for i in {1..15}; do
  echo "Request $i:"
  curl -s http://localhost:8080/api/chat \
    -H "Content-Type: application/json" \
    -d '{"message":"test"}' | jq .error
  sleep 1
done
```
**Expected:** First 10 succeed, then 429 errors

### 3. Test Authenticated Tier
```bash
export API_TOKEN="your-token-here"

for i in {1..15}; do
  echo "Request $i:"
  curl -s http://localhost:8080/api/chat \
    -H "X-API-Token: $API_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"message":"test"}' | jq .
done
```
**Expected:** All 15 succeed (100/min limit)

### 4. Test Security Headers
```bash
curl -I http://localhost:8080/api/health | grep -E "X-|Content-Security-Policy|Strict-Transport"
```
**Expected:** See all security headers

### 5. Test Suspicious User Agent
```bash
curl -A "curl/7.0" http://localhost:8080/api/security/status | jq .suspicious
```
**Expected:** `true`

## Production Deployment

### 1. Generate Secure API Tokens
```bash
# Generate secure token (Linux/macOS)
openssl rand -base64 32

# Or use Python
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Configure Environment
```bash
# Add to ~/.env or /etc/default/diamond-gateway
export API_TOKENS="token1,token2,token3"
export ENVIRONMENT="production"
```

### 3. Upgrade to Redis (Optional)
For production clusters with multiple workers, upgrade from in-memory to Redis storage:

```python
# In bot_protection.py
limiter = Limiter(
    key_func=get_rate_limit_key,
    storage_uri="redis://localhost:6379",  # Changed from memory://
    headers_enabled=True,
)
```

### 4. Add IP Whitelist
Edit `/home/diamondnode/diamondnode-unified-inference/src/security/bot_protection.py`:

```python
self.whitelisted_ips: Set[str] = {
    "127.0.0.1",
    "::1",
    "10.0.0.5",  # Internal service
    "192.168.1.100",  # Trusted partner
}
```

## Monitoring

### Rate Limit Headers

All responses include rate limit information:
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1621447200
```

### Performance Timing

All responses include processing time:
```
X-Process-Time: 0.0234
```

### Client Information Logging

Use `get_client_info()` for analytics:
```python
from security.bot_protection import get_client_info

@app.get("/api/endpoint")
async def my_endpoint(request: Request):
    client_info = get_client_info(request)
    # Log to monitoring system
    return {"status": "ok"}
```

## Comparison to BotID

| Feature | BotID | Our Solution |
|---------|-------|--------------|
| Runtime | JavaScript (browser) | Python (server) |
| Rate Limiting | ❌ | ✅ slowapi |
| Token Auth | ❌ | ✅ X-API-Token |
| Security Headers | ❌ | ✅ Comprehensive |
| Bot Detection | ✅ ML-based | ✅ Signature-based |
| Multi-tier Limits | ❌ | ✅ 4 tiers |
| WebSocket Support | ❌ | ✅ Custom limiter |

## Troubleshooting

### "Rate limit exceeded" too soon
- Check your tier: `curl http://localhost:8080/api/security/status`
- Add API token if you have one
- Contact admin for IP whitelisting

### "Invalid or missing API token"
- Verify token is correct: `echo $API_TOKEN`
- Check header name: must be `X-API-Token`
- Ensure server has token configured in environment

### Security headers not appearing
- Check middleware order (BotProtectionMiddleware should be first)
- Verify middleware is registered: `app.add_middleware(BotProtectionMiddleware)`

## References

- [slowapi documentation](https://github.com/laurentS/slowapi)
- [OWASP Rate Limiting Guide](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html#rate-limiting)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
