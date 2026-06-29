#!/bin/bash
# Diamond Node Web UI Installation Script

set -e

echo "================================"
echo "Diamond Node Web UI Installation"
echo "================================"
echo ""

# Check if running as diamondnode user
if [ "$USER" != "diamondnode" ]; then
    echo "Error: This script must be run as the diamondnode user"
    echo "Run: sudo -u diamondnode $0"
    exit 1
fi

# Define paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$HOME/xinference_venv"
SERVICE_FILE="$SCRIPT_DIR/web-ui.service"
SYSTEMD_SERVICE="/etc/systemd/system/web-ui.service"

echo "Step 1: Installing Python dependencies..."
if [ ! -d "$VENV_PATH" ]; then
    echo "Error: Virtual environment not found at $VENV_PATH"
    echo "Please create it first: python3 -m venv $VENV_PATH"
    exit 1
fi

source "$VENV_PATH/bin/activate"

pip install --upgrade pip
pip install fastapi uvicorn[standard] websockets httpx

echo "✓ Dependencies installed"
echo ""

echo "Step 2: Verifying static files..."
if [ ! -f "$SCRIPT_DIR/static/index.html" ]; then
    echo "Error: Static files not found in $SCRIPT_DIR/static/"
    exit 1
fi
echo "✓ Static files verified"
echo ""

echo "Step 3: Creating environment file..."
ENV_FILE="/etc/default/diamond-web-ui"

sudo bash -c "cat > $ENV_FILE" << 'ENVEOF'
# Diamond Node Web UI Environment Variables
GATEWAY_URL=http://127.0.0.1:8000
GATEWAY_SECRET=
ANTHROPIC_API_KEY=
ENVEOF

# Copy secrets from gateway config if available
if [ -f "/etc/default/diamond-gateway" ]; then
    GATEWAY_SECRET=$(grep "^GATEWAY_SECRET=" /etc/default/diamond-gateway | cut -d'=' -f2)
    if [ -n "$GATEWAY_SECRET" ]; then
        sudo sed -i "s|^GATEWAY_SECRET=.*|GATEWAY_SECRET=$GATEWAY_SECRET|" "$ENV_FILE"
        echo "✓ Copied GATEWAY_SECRET from diamond-gateway"
    fi
fi

# Copy Anthropic API key from orchestrator config if available
if [ -f "$SCRIPT_DIR/.env" ]; then
    ANTHROPIC_KEY=$(grep "^ANTHROPIC_API_KEY=" "$SCRIPT_DIR/.env" | cut -d'=' -f2)
    if [ -n "$ANTHROPIC_KEY" ]; then
        sudo sed -i "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$ANTHROPIC_KEY|" "$ENV_FILE"
        echo "✓ Copied ANTHROPIC_API_KEY from .env"
    fi
elif [ -n "$ANTHROPIC_API_KEY" ]; then
    sudo sed -i "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY|" "$ENV_FILE"
    echo "✓ Using ANTHROPIC_API_KEY from environment"
fi

sudo chmod 640 "$ENV_FILE"
echo "✓ Environment file created at $ENV_FILE"
echo ""

echo "Step 4: Installing systemd service..."
sudo cp "$SERVICE_FILE" "$SYSTEMD_SERVICE"
sudo chmod 644 "$SYSTEMD_SERVICE"
sudo systemctl daemon-reload
echo "✓ Systemd service installed"
echo ""

echo "Step 5: Enabling and starting service..."
sudo systemctl enable web-ui.service
sudo systemctl restart web-ui.service

echo "✓ Service started"
echo ""

echo "Step 6: Waiting for service to be ready..."
sleep 3

echo "Step 7: Testing health endpoint..."
if curl -f http://localhost:8080/api/health > /dev/null 2>&1; then
    echo "✓ Health check passed"
else
    echo "⚠ Warning: Health check failed. Check logs with: sudo journalctl -u web-ui -n 50"
fi
echo ""

echo "Step 8: Checking service status..."
sudo systemctl status web-ui.service --no-pager -l || true
echo ""

echo "================================"
echo "Installation Complete!"
echo "================================"
echo ""
echo "Web UI is now running at: http://localhost:8080"
echo ""
echo "Useful commands:"
echo "  - View logs:      sudo journalctl -u web-ui -f"
echo "  - Restart:        sudo systemctl restart web-ui"
echo "  - Stop:           sudo systemctl stop web-ui"
echo "  - Status:         sudo systemctl status web-ui"
echo ""
echo "To access from another machine, set up nginx reverse proxy."
echo "See WEB_UI_SETUP.md for instructions."
echo ""
