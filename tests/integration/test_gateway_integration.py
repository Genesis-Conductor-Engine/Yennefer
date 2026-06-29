#!/usr/bin/env python3
"""
Test script for Claude Orchestrator + Diamond Gateway integration
Tests the real HTTP connection to the Diamond Gateway API
"""

import asyncio
import sys
import os
from pathlib import Path

# Add unified_inference to path
sys.path.insert(0, str(Path.home() / "unified_inference"))

try:
    import httpx
    # Add src to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
    from orchestrator.config import get_config
except ImportError as e:
    print(f"Error: Missing dependency - {e}")
    print("Install with: pip install httpx python-dotenv")
    sys.exit(1)


async def test_gateway_connection():
    """Test direct connection to Diamond Gateway"""
    print("=" * 60)
    print("Diamond Gateway Integration Test")
    print("=" * 60)
    print()
    
    # Load environment variables manually (avoid config validation)
    from dotenv import load_dotenv
    load_dotenv(Path.home() / ".env")
    
    gateway_url = os.environ.get("GATEWAY_URL", "http://127.0.0.1:8000") + "/v1/orchestrate"
    gateway_secret = os.environ.get("GATEWAY_SECRET")
    
    print(f"Gateway URL: {gateway_url}")
    print(f"Gateway Secret: {'✓ configured' if gateway_secret else '✗ missing'}")
    print()
    
    if not gateway_secret:
        print("ERROR: GATEWAY_SECRET not configured")
        print()
        print("To configure:")
        print("1. Extract secret: sudo cat /etc/default/diamond-gateway")
        print("2. Add to ~/.env: GATEWAY_SECRET=<your-secret>")
        print()
        return False
    
    print("Testing gateway connection...")
    print()
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                gateway_url,
                headers={
                    "Authorization": f"Bearer {gateway_secret}",
                    "Content-Type": "application/json"
                },
                json={
                    "session_id": "test-integration",
                    "context_buffer": "[TEST] Claude orchestrator integration"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            print("✓ Gateway connection successful!")
            print()
            print("Response:")
            print("-" * 60)
            print(f"  Action: {data.get('action', 'unknown')}")
            print(f"  Session ID: {data.get('session_id', 'unknown')}")
            print(f"  Hamiltonian (H): {data.get('hamiltonian', 0.0):.2f}")
            print(f"  VRAM Used: {data.get('vram_used_mib', 0)} MiB")
            print(f"  VRAM Total: {data.get('vram_total_mib', 0)} MiB")
            vram_percent = (data.get('vram_used_mib', 0) / data.get('vram_total_mib', 1)) * 100
            print(f"  VRAM Utilization: {vram_percent:.1f}%")
            print("-" * 60)
            print()
            
            # Interpret Hamiltonian
            h = data.get('hamiltonian', 0.0)
            if h < 5:
                status = "OPTIMAL - All models can run concurrently"
            elif h < 7.5:
                status = "DYNAMIC - Hot-swap by priority"
            elif h < 8.5:
                status = "SEQUENTIAL - One heavy model at a time"
            else:
                status = "CRITICAL - OFFLOAD to Notion required"
            
            print(f"Resource Status: {status}")
            print()
            
            return True
            
    except httpx.HTTPStatusError as e:
        print(f"✗ HTTP Error: {e.response.status_code}")
        print(f"  Response: {e.response.text}")
        print()
        if e.response.status_code == 401:
            print("Authentication failed - check GATEWAY_SECRET")
        return False
        
    except httpx.ConnectError as e:
        print(f"✗ Connection Error: {e}")
        print()
        print("Is the gateway running?")
        print("  Check: systemctl status diamond-gateway")
        return False
        
    except Exception as e:
        print(f"✗ Unexpected Error: {e}")
        return False


async def test_orchestrator_integration():
    """Test ClaudeOrchestrator with real gateway"""
    print()
    print("=" * 60)
    print("Claude Orchestrator Integration Test")
    print("=" * 60)
    print()
    
    try:
        from orchestrator.claude_orchestrator import ClaudeOrchestrator
    except ImportError as e:
        print(f"Error importing ClaudeOrchestrator: {e}")
        return False
    
    # Check for Anthropic API key
    config = get_config()
    if not config.api.anthropic_api_key:
        print("⚠ ANTHROPIC_API_KEY not configured - skipping orchestrator test")
        print("  Set in ~/.env to test full orchestration")
        return None
    
    print("Initializing Claude Orchestrator...")
    orchestrator = ClaudeOrchestrator()
    print("✓ Orchestrator initialized")
    print()
    
    print("Testing query_vram_status tool...")
    result = await orchestrator.execute_tool("query_vram_status", {})
    
    if "error" in result:
        print(f"✗ Tool execution failed: {result['error']}")
        return False
    
    print("✓ Tool execution successful!")
    print()
    print("Result:")
    print("-" * 60)
    print(f"  VRAM Used: {result.get('vram_used_mb', 0)} MiB")
    print(f"  VRAM Total: {result.get('vram_total_mb', 0)} MiB")
    print(f"  VRAM Available: {result.get('available_vram_mb', 0)} MiB")
    print(f"  Hamiltonian: {result.get('hamiltonian', 0.0):.2f}")
    print(f"  Action: {result.get('action', 'unknown')}")
    print(f"  Gateway Status: {result.get('gateway_status', 'unknown')}")
    print("-" * 60)
    print()
    
    return True


async def main():
    """Run all tests"""
    # Test 1: Direct gateway connection
    gateway_ok = await test_gateway_connection()
    
    if not gateway_ok:
        print("=" * 60)
        print("Gateway test failed - skipping orchestrator test")
        print("=" * 60)
        sys.exit(1)
    
    # Test 2: Orchestrator integration
    orchestrator_ok = await test_orchestrator_integration()
    
    print()
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Gateway Connection: {'✓ PASS' if gateway_ok else '✗ FAIL'}")
    if orchestrator_ok is not None:
        print(f"Orchestrator Integration: {'✓ PASS' if orchestrator_ok else '✗ FAIL'}")
    else:
        print(f"Orchestrator Integration: ⚠ SKIPPED")
    print("=" * 60)
    print()
    
    if gateway_ok and (orchestrator_ok or orchestrator_ok is None):
        print("✓ Integration is working correctly!")
        print()
        print("Next steps:")
        print("  - Set ANTHROPIC_API_KEY in ~/.env for full orchestration")
        print("  - Run: python3 claude_orchestrator.py")
        print()
        sys.exit(0)
    else:
        print("✗ Integration has issues - see errors above")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
