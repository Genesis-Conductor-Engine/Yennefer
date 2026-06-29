#!/usr/bin/env python3
"""
Simple test for Diamond Gateway integration (no dependencies)
"""

import asyncio
import os
import sys
from pathlib import Path

# Add unified_inference to path
sys.path.insert(0, str(Path.home() / "unified_inference"))

try:
    import httpx
except ImportError:
    print("Error: httpx not installed")
    print("Install with: python3 -m pip install --user --break-system-packages httpx")
    sys.exit(1)


def load_env_file(env_path):
    """Simple .env parser (no dependencies)"""
    env_vars = {}
    if not env_path.exists():
        return env_vars
    
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars


async def test_gateway():
    """Test direct gateway connection"""
    print("=" * 70)
    print("Diamond Gateway Integration Test")
    print("=" * 70)
    print()
    
    # Load .env manually
    env_path = Path.home() / ".env"
    env_vars = load_env_file(env_path)
    
    gateway_url = env_vars.get("GATEWAY_URL", "http://127.0.0.1:8000") + "/v1/orchestrate"
    gateway_secret = env_vars.get("GATEWAY_SECRET")
    
    print(f"Gateway URL: {gateway_url}")
    print(f"Gateway Secret: {'✓ configured' if gateway_secret else '✗ MISSING'}")
    print()
    
    if not gateway_secret:
        print("ERROR: GATEWAY_SECRET not found in ~/.env")
        print()
        print("Current .env has:")
        for key in sorted(env_vars.keys()):
            if "SECRET" in key or "KEY" in key or "TOKEN" in key:
                print(f"  {key}: {'✓ set' if env_vars[key] else '✗ empty'}")
        print()
        print("To fix:")
        print("  1. Run: sudo cat /etc/default/diamond-gateway")
        print("  2. Add to ~/.env: GATEWAY_SECRET=<value-from-step-1>")
        return False
    
    print("Testing connection to Diamond Gateway...")
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
                    "context_buffer": "[TEST] Claude orchestrator integration test"
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            print("✓ SUCCESS - Gateway responded!")
            print()
            print("Response Data:")
            print("-" * 70)
            print(f"  Action:           {data.get('action', 'unknown')}")
            print(f"  Session ID:       {data.get('session_id', 'unknown')}")
            print(f"  Hamiltonian (H):  {data.get('hamiltonian', 0.0):.4f}")
            print(f"  VRAM Used:        {data.get('vram_used_mib', 0)} MiB")
            print(f"  VRAM Total:       {data.get('vram_total_mib', 0)} MiB")
            
            vram_used = data.get('vram_used_mib', 0)
            vram_total = data.get('vram_total_mib', 1)
            vram_pct = (vram_used / vram_total) * 100
            print(f"  VRAM Utilization: {vram_pct:.1f}%")
            print("-" * 70)
            print()
            
            # Interpret Hamiltonian
            h = data.get('hamiltonian', 0.0)
            if h < 5:
                status = "OPTIMAL"
                desc = "All models can run concurrently"
                emoji = "🟢"
            elif h < 7.5:
                status = "DYNAMIC"
                desc = "Hot-swap models by priority"
                emoji = "🟡"
            elif h < 8.5:
                status = "SEQUENTIAL"
                desc = "One heavy model at a time"
                emoji = "🟠"
            else:
                status = "CRITICAL"
                desc = "OFFLOAD to Notion required!"
                emoji = "🔴"
            
            print(f"Resource Status: {emoji} {status}")
            print(f"  → {desc}")
            print()
            
            print("=" * 70)
            print("✓ Integration Test: PASSED")
            print("=" * 70)
            print()
            print("Next steps:")
            print("  - The query_vram_status tool now returns real VRAM data")
            print("  - Hamiltonian values reflect actual GPU utilization")
            print("  - OFFLOAD triggers automatically when H > 8.5")
            print()
            
            return True
            
    except httpx.HTTPStatusError as e:
        print(f"✗ HTTP Error: {e.response.status_code}")
        print(f"  Response: {e.response.text}")
        print()
        
        if e.response.status_code == 401:
            print("Authentication failed!")
            print("  → GATEWAY_SECRET in ~/.env doesn't match gateway config")
            print("  → Run: sudo cat /etc/default/diamond-gateway")
            print("  → Update ~/.env with correct value")
        elif e.response.status_code == 404:
            print("Endpoint not found!")
            print("  → Gateway may be running older version")
            print("  → Check: curl http://localhost:8000/health")
        
        return False
        
    except httpx.ConnectError as e:
        print(f"✗ Connection Error: {e}")
        print()
        print("Gateway is not responding. Troubleshooting:")
        print("  1. Check if running:  systemctl status diamond-gateway")
        print("  2. Start if needed:   sudo systemctl start diamond-gateway")
        print("  3. View logs:         sudo journalctl -u diamond-gateway -n 50")
        print()
        
        return False
        
    except Exception as e:
        print(f"✗ Unexpected Error: {type(e).__name__}: {e}")
        return False


async def main():
    success = await test_gateway()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
