#!/usr/bin/env python3
"""
Test script for Agent State API endpoint.
Run this after starting the web UI server.
"""

import httpx
import json
import sys
from datetime import datetime


def test_agent_state_endpoint():
    """Test the /api/agent/state endpoint."""
    
    url = "http://localhost:8080/api/agent/state"
    
    print("Testing Agent State API Endpoint")
    print("=" * 60)
    print(f"URL: {url}")
    print()
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                print("\n✅ Endpoint successful!\n")
                
                # Display key information
                print(f"Agent Status: {data['status']}")
                print(f"Current Activity: {data['current_activity'] or 'None'}")
                print(f"Thinking: {data['thinking'] or 'None'}")
                print()
                
                # State information
                print("State:")
                print(f"  Hamiltonian: {data['state']['hamiltonian']}")
                print(f"  VRAM State: {data['state']['vram_state']}")
                print(f"  Validation State: {data['state']['validation_state']}")
                print(f"  Last Orchestration: {data['state']['last_orchestration'] or 'Never'}")
                print()
                
                # Metrics
                metrics = data['metrics']
                print("Metrics:")
                print(f"  Total Cycles: {metrics['total_cycles']}")
                print(f"  Total Orchestrations: {metrics['total_orchestrations']}")
                print(f"  Uptime: {metrics['uptime_human']}")
                print(f"  Avg Execution Time: {metrics['avg_execution_time_ms']} ms" if metrics['avg_execution_time_ms'] else "  Avg Execution Time: N/A")
                print(f"  Last Execution Time: {metrics['last_execution_time_ms']} ms" if metrics['last_execution_time_ms'] else "  Last Execution Time: N/A")
                print()
                
                # Connections
                connections = data['connections']
                print("Connections:")
                print(f"  Gateway: {connections['gateway']['status']}")
                if connections['gateway']['latency_ms']:
                    print(f"    URL: {connections['gateway']['url']}")
                    print(f"    Latency: {connections['gateway']['latency_ms']:.2f} ms")
                
                print(f"  Claude API: {connections['claude']['status']}")
                if connections['claude']['model']:
                    print(f"    Model: {connections['claude']['model']}")
                
                print(f"  EnKG Kernel: {connections['enkg_kernel']['status']}")
                print(f"    Triton: {connections['enkg_kernel']['triton_available']}")
                print(f"    CUDA: {connections['enkg_kernel']['cuda_available']}")
                print()
                
                # Orchestrator
                orchestrator = data['orchestrator']
                print("Orchestrator:")
                print(f"  Initialized: {orchestrator['initialized']}")
                print(f"  Type: {orchestrator['type'] or 'None'}")
                print()
                
                # Recent actions
                print(f"Recent Actions ({len(data['recent_actions'])}):")
                for action in data['recent_actions'][:5]:  # Show last 5
                    print(f"  - {action['timestamp']}: {action['action']} ({action['status']})")
                    if action.get('details'):
                        for key, value in action['details'].items():
                            print(f"      {key}: {value}")
                print()
                
                print(f"Timestamp: {data['timestamp']}")
                print()
                
                # Full JSON output
                print("Full Response JSON:")
                print("-" * 60)
                print(json.dumps(data, indent=2))
                
                return True
            else:
                print(f"\n❌ Request failed with status {response.status_code}")
                print(response.text)
                return False
                
    except httpx.ConnectError:
        print("\n❌ Connection failed!")
        print("Is the web UI server running?")
        print("Start it with: cd ~/diamondnode-unified-inference/web/ui && ~/venv312/bin/python web_ui.py")
        return False
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = test_agent_state_endpoint()
    sys.exit(0 if success else 1)
