#!/usr/bin/env python3
"""
Test client for agent state WebSocket endpoint.
Run this while web_ui.py is running to verify WebSocket functionality.
"""

import asyncio
import json
import websockets
from datetime import datetime

async def test_agent_state_websocket():
    """Connect to agent state WebSocket and print messages."""
    uri = "ws://localhost:8080/ws/agent-state"
    
    print(f"[{datetime.now().isoformat()}] Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"[{datetime.now().isoformat()}] Connected!")
            
            # Receive messages for 30 seconds
            timeout = 30
            start_time = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                try:
                    message = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=6.0
                    )
                    data = json.loads(message)
                    
                    msg_type = data.get("type")
                    timestamp = data.get("timestamp")
                    
                    if msg_type == "connection":
                        print(f"\n✅ [{timestamp}] CONNECTION:")
                        print(f"   {json.dumps(data['data'], indent=2)}")
                    
                    elif msg_type == "heartbeat":
                        uptime = data.get("data", {}).get("uptime", 0)
                        connections = data.get("data", {}).get("connections", 0)
                        print(f"💓 [{timestamp}] HEARTBEAT (uptime: {uptime:.1f}s, connections: {connections})")
                    
                    elif msg_type == "state_update":
                        print(f"\n🔄 [{timestamp}] STATE UPDATE:")
                        print(f"   {json.dumps(data['data'], indent=2)}")
                    
                    elif msg_type == "activity":
                        activity = data.get("data", {}).get("activity")
                        print(f"\n⚡ [{timestamp}] ACTIVITY: {activity}")
                    
                    elif msg_type == "action":
                        action = data.get("data", {}).get("action")
                        duration = data.get("data", {}).get("duration_ms")
                        print(f"\n✓ [{timestamp}] ACTION: {action} (duration: {duration}ms)")
                    
                    else:
                        print(f"\n❓ [{timestamp}] UNKNOWN TYPE: {msg_type}")
                        print(f"   {json.dumps(data, indent=2)}")
                
                except asyncio.TimeoutError:
                    print(f"⏱️  [{datetime.now().isoformat()}] No message received (timeout)")
                    continue
            
            print(f"\n[{datetime.now().isoformat()}] Test completed after {timeout}s")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    print("=" * 70)
    print("Agent State WebSocket Test Client")
    print("=" * 70)
    print("\nThis will connect to the agent state WebSocket and display messages.")
    print("Make sure web_ui.py is running on localhost:8080\n")
    
    asyncio.run(test_agent_state_websocket())
