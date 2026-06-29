#!/bin/bash
# Yennefer Telemetry Deployment Script

set -e

echo "=== Yennefer Telemetry Deployment ==="
echo ""

# Check we're in the right directory
if [ ! -f "workers/yennefer_telemetry_daemon.py" ]; then
    echo "Error: Must run from ~/diamondnode-unified-inference/"
    exit 1
fi

echo "Step 1: Install Python dependencies..."
if [ -d "yennefer_venv" ]; then
    source yennefer_venv/bin/activate
    pip install --quiet -r requirements.txt
else
    echo "Creating virtual environment..."
    python3 -m venv yennefer_venv
    source yennefer_venv/bin/activate
    pip install --quiet -r requirements.txt
fi

echo "Step 2: Test components..."
python3 workers/thermodynamic_simulator.py > /dev/null 2>&1 && echo "  ✅ Thermodynamic simulator OK"
python3 workers/notion_sanitizer.py > /dev/null 2>&1 && echo "  ✅ Notion sanitizer OK"

echo ""
echo "Step 3: Copy systemd service..."
sudo cp deployment/yennefer-telemetry.service /etc/systemd/system/
echo "  ✅ Service file copied to /etc/systemd/system/"

echo ""
echo "Step 4: Create environment file..."
if [ ! -f "/etc/default/yennefer-telemetry" ]; then
    sudo cp deployment/yennefer-telemetry.env.template /etc/default/yennefer-telemetry
    echo "  ⚠️  Environment file created at /etc/default/yennefer-telemetry"
    echo "  ⚠️  IMPORTANT: Edit this file and add your NOTION_TOKEN!"
    echo "  Run: sudo nano /etc/default/yennefer-telemetry"
else
    echo "  ✅ Environment file already exists"
fi

echo ""
echo "Step 5: Reload systemd..."
sudo systemctl daemon-reload
echo "  ✅ Systemd reloaded"

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Next steps:"
echo "1. Set NOTION_TOKEN: sudo nano /etc/default/yennefer-telemetry"
echo "2. Enable service: sudo systemctl enable yennefer-telemetry"
echo "3. Start service: sudo systemctl start yennefer-telemetry"
echo "4. Check status: sudo systemctl status yennefer-telemetry"
echo "5. View logs: sudo journalctl -u yennefer-telemetry -f"
