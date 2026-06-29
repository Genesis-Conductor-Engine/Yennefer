"""
Health Check Module for Unified Inference System
Checks status of all system components: Gateway, CUDA-Q, Xinference
"""

import asyncio
import aiohttp
import sys
from typing import Dict, Any, Optional
from datetime import datetime

from config import get_config


class HealthChecker:
    """Health checker for all system components"""
    
    def __init__(self):
        self.config = get_config()
    
    async def check_gateway(self) -> Dict[str, Any]:
        """Check Diamond Gateway health"""
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout.health_check_timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.config.gateway.health_url) as resp:
                    if resp.status == 200:
                        return {
                            "status": "healthy",
                            "response_time_ms": 0,  # Could track this
                            "message": "Gateway is responsive"
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "response_code": resp.status,
                            "message": f"Gateway returned status {resp.status}"
                        }
        except asyncio.TimeoutError:
            return {
                "status": "unhealthy",
                "error": "timeout",
                "message": f"Gateway health check timed out after {self.config.timeout.health_check_timeout}s"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(type(e).__name__),
                "message": str(e)
            }
    
    def check_cuda_q(self) -> Dict[str, Any]:
        """Check if CUDA-Q is available"""
        try:
            import cudaq
            return {
                "status": "available",
                "version": getattr(cudaq, "__version__", "unknown"),
                "message": "CUDA-Q import successful"
            }
        except ImportError as e:
            return {
                "status": "unavailable",
                "error": "ImportError",
                "message": "CUDA-Q not installed or not in path"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(type(e).__name__),
                "message": str(e)
            }
    
    async def check_xinference(self) -> Dict[str, Any]:
        """Check if Xinference is running"""
        # Xinference typically runs on localhost:9997
        xinference_url = "http://localhost:9997/v1/models"
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout.health_check_timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(xinference_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            "status": "running",
                            "models": len(data) if isinstance(data, list) else 0,
                            "message": "Xinference is running"
                        }
                    else:
                        return {
                            "status": "error",
                            "response_code": resp.status,
                            "message": f"Xinference returned status {resp.status}"
                        }
        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "message": "Xinference health check timed out"
            }
        except aiohttp.ClientConnectorError:
            return {
                "status": "not_running",
                "message": "Xinference is not running or not accessible"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(type(e).__name__),
                "message": str(e)
            }
    
    def check_config(self) -> Dict[str, Any]:
        """Check configuration validity"""
        issues = []
        
        if not self.config.api.anthropic_api_key:
            issues.append("ANTHROPIC_API_KEY not set")
        
        if not self.config.api.gateway_secret:
            issues.append("GATEWAY_SECRET not set (gateway auth will fail)")
        
        if self.config.rate_limit.requests_per_minute <= 0:
            issues.append("Invalid rate limit configuration")
        
        if issues:
            return {
                "status": "invalid",
                "issues": issues,
                "message": f"Configuration has {len(issues)} issue(s)"
            }
        else:
            return {
                "status": "valid",
                "environment": self.config.environment.value,
                "message": "Configuration is valid"
            }
    
    async def check_all(self) -> Dict[str, Any]:
        """Run all health checks"""
        timestamp = datetime.now().isoformat() + "Z"
        
        # Run checks in parallel
        gateway_task = asyncio.create_task(self.check_gateway())
        xinference_task = asyncio.create_task(self.check_xinference())
        
        # Synchronous checks
        cuda_q_status = self.check_cuda_q()
        config_status = self.check_config()
        
        # Wait for async checks
        gateway_status = await gateway_task
        xinference_status = await xinference_task
        
        # Determine overall health
        # CUDA-Q and Xinference are optional - only config and gateway are critical
        all_healthy = (
            gateway_status.get("status") == "healthy" and
            config_status.get("status") == "valid"
        )
        
        overall_status = "healthy" if all_healthy else "degraded"
        
        return {
            "status": overall_status,
            "timestamp": timestamp,
            "environment": self.config.environment.value,
            "components": {
                "config": config_status,
                "gateway": gateway_status,
                "cuda_q": cuda_q_status,
                "xinference": xinference_status
            },
            "ready": all_healthy
        }


async def main():
    """CLI for health check"""
    checker = HealthChecker()
    
    print("=" * 60)
    print("Unified Inference System Health Check")
    print("=" * 60)
    
    result = await checker.check_all()
    
    print(f"Overall Status: {result['status'].upper()}")
    print(f"Environment: {result['environment']}")
    print(f"Timestamp: {result['timestamp']}")
    print(f"Ready: {'✓' if result['ready'] else '✗'}")
    print()
    
    for component, status in result['components'].items():
        print(f"{component.upper()}:")
        print(f"  Status: {status.get('status', 'unknown')}")
        if 'message' in status:
            print(f"  Message: {status['message']}")
        if 'issues' in status:
            for issue in status['issues']:
                print(f"    - {issue}")
        if 'error' in status:
            print(f"  Error: {status['error']}")
        print()
    
    print("=" * 60)
    
    # Exit with appropriate code
    sys.exit(0 if result['ready'] else 1)


if __name__ == "__main__":
    asyncio.run(main())
