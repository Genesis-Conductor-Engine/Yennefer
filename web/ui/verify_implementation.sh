#!/bin/bash
# Verification script for agent state WebSocket implementation

echo "======================================================================="
echo "Agent State WebSocket Implementation Verification"
echo "======================================================================="
echo ""

echo "✓ Checking file modifications..."
if grep -q "class AgentStateManager" web_ui.py; then
    echo "  ✅ AgentStateManager class found"
else
    echo "  ❌ AgentStateManager class not found"
    exit 1
fi

if grep -q '@app.websocket("/ws/agent-state")' web_ui.py; then
    echo "  ✅ /ws/agent-state endpoint found"
else
    echo "  ❌ /ws/agent-state endpoint not found"
    exit 1
fi

if grep -q 'agent_state_manager = AgentStateManager()' web_ui.py; then
    echo "  ✅ AgentStateManager instance created"
else
    echo "  ❌ AgentStateManager instance not found"
    exit 1
fi

if grep -q 'broadcast_activity' web_ui.py; then
    echo "  ✅ broadcast_activity integration found"
else
    echo "  ❌ broadcast_activity integration not found"
    exit 1
fi

if grep -q 'broadcast_action' web_ui.py; then
    echo "  ✅ broadcast_action integration found"
else
    echo "  ❌ broadcast_action integration not found"
    exit 1
fi

echo ""
echo "✓ Checking syntax..."
python3 -m py_compile web_ui.py 2>&1
if [ $? -eq 0 ]; then
    echo "  ✅ Syntax check passed"
else
    echo "  ❌ Syntax errors found"
    exit 1
fi

echo ""
echo "✓ Checking test client..."
if [ -x test_agent_state_ws.py ]; then
    echo "  ✅ Test client is executable"
else
    echo "  ❌ Test client not executable"
    exit 1
fi

python3 -m py_compile test_agent_state_ws.py 2>&1
if [ $? -eq 0 ]; then
    echo "  ✅ Test client syntax OK"
else
    echo "  ❌ Test client has syntax errors"
    exit 1
fi

echo ""
echo "✓ Checking documentation..."
if [ -f "WEBSOCKET_AGENT_STATE.md" ]; then
    echo "  ✅ WEBSOCKET_AGENT_STATE.md exists"
else
    echo "  ❌ WEBSOCKET_AGENT_STATE.md not found"
    exit 1
fi

if [ -f "AGENT_STATE_IMPLEMENTATION.md" ]; then
    echo "  ✅ AGENT_STATE_IMPLEMENTATION.md exists"
else
    echo "  ❌ AGENT_STATE_IMPLEMENTATION.md not found"
    exit 1
fi

echo ""
echo "✓ Checking code statistics..."
echo "  Lines in web_ui.py: $(wc -l < web_ui.py)"
echo "  AgentStateManager methods: $(grep -c "    def " web_ui.py || echo 0)"
echo "  WebSocket endpoints: $(grep -c "@app.websocket" web_ui.py)"
echo "  Broadcast calls: $(grep -c "agent_state_manager.broadcast" web_ui.py)"

echo ""
echo "======================================================================="
echo "✅ All verification checks passed!"
echo "======================================================================="
echo ""
echo "Implementation summary:"
echo "  • AgentStateManager class with connection management"
echo "  • /ws/agent-state endpoint with heartbeat support"
echo "  • Integration in /api/chat and /ws/chat endpoints"
echo "  • REST API fallback at /api/agent-state"
echo "  • Test client and comprehensive documentation"
echo ""
echo "To test:"
echo "  1. Start web UI: python web/ui/web_ui.py"
echo "  2. Run test client: python test_agent_state_ws.py"
echo "  3. Trigger activity: curl -X POST http://localhost:8080/api/chat \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"message\": \"test\"}'"
echo ""
