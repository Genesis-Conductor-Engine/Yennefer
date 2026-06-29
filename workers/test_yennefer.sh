#!/bin/bash
# Test runner for Yennefer Telemetry components
# Run from: ~/diamondnode-unified-inference

set -e

echo "=== Yennefer Telemetry System Tests ==="
echo ""

echo "Test 1: Thermodynamic Simulator"
echo "--------------------------------"
python3 workers/thermodynamic_simulator.py
echo ""

echo "Test 2: Notion Sanitizer"
echo "------------------------"
python3 workers/notion_sanitizer.py
echo ""

echo "Test 3: Daemon Dry Run (single cycle, no Notion POST)"
echo "------------------------------------------------------"
echo "Simulating single telemetry cycle..."
python3 -c "
import sys
sys.path.insert(0, '.')
from workers.yennefer_telemetry_daemon import YenneferTelemetryDaemon

daemon = YenneferTelemetryDaemon()
metrics = daemon.compute_metrics()

print(f'Metrics computed:')
print(f'  η_thermo: {metrics[\"eta_thermo\"]:.4f}')
print(f'  ε: {metrics[\"epsilon\"]:.4f}')
print(f'  γ: {metrics[\"gamma\"]:.4f}')
print(f'  Δq: {metrics[\"delta_q\"]:.4f}')
print(f'  VRAM JAX: {metrics[\"vram_jax_pct\"]:.2f}%')
print(f'  CUDA-Q Status: {metrics[\"cuda_q_kernel_status\"]}')
print(f'  Crystalline Score: {metrics[\"crystalline_score\"]:.4f}')
print(f'  Hold Cycles: {metrics[\"hold_cycles\"]}')
"

echo ""
echo "=== All Tests Passed ==="
echo ""
echo "Next steps:"
echo "1. Install dependencies: pip install notion-client pyyaml numpy"
echo "2. Set NOTION_TOKEN in /etc/default/yennefer-telemetry"
echo "3. Deploy service: sudo cp deployment/yennefer-telemetry.service /etc/systemd/system/"
echo "4. Enable service: sudo systemctl enable --now yennefer-telemetry"
echo "5. Check logs: sudo journalctl -u yennefer-telemetry -f"
