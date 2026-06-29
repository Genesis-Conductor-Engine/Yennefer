#!/bin/bash
# Deploy Maru Guardian - envelope 0.3.0
# Automated deployment script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "========================================="
echo "Deploying Maru Guardian - Envelope 0.3.0"
echo "========================================="

# Check for NOTION_TOKEN
if [ -z "$NOTION_TOKEN" ]; then
    echo "WARNING: NOTION_TOKEN not set in environment"
    echo "Create /etc/default/maru-guardian with:"
    echo "NOTION_TOKEN=your_token_here"
fi

# Create state directories
echo "Creating state directories..."
sudo mkdir -p /var/maru/reframe_events
sudo mkdir -p /var/maru/audit_logs
sudo chown -R diamondnode:diamondnode /var/maru

# Create log directory
sudo mkdir -p /var/log
sudo touch /var/log/maru_guardian.log
sudo chown diamondnode:diamondnode /var/log/maru_guardian.log

# Verify Python dependencies
echo "Checking Python dependencies..."
python3 -c "import yaml, requests" 2>/dev/null || {
    echo "Installing required Python packages..."
    pip3 install --user pyyaml requests
}

# Install systemd service
echo "Installing systemd service..."
sudo cp "$SCRIPT_DIR/maru-guardian.service" /etc/systemd/system/
sudo systemctl daemon-reload

# Create environment file template if not exists
if [ ! -f /etc/default/maru-guardian ]; then
    echo "Creating environment file template..."
    sudo bash -c 'cat > /etc/default/maru-guardian <<EOF
# Maru Guardian Environment Variables
NOTION_TOKEN=
EOF'
    sudo chmod 600 /etc/default/maru-guardian
    echo "IMPORTANT: Set NOTION_TOKEN in /etc/default/maru-guardian"
fi

# Enable service
echo "Enabling maru-guardian service..."
sudo systemctl enable maru-guardian

# Restart service
echo "Starting maru-guardian service..."
sudo systemctl restart maru-guardian

# Wait for service to start
sleep 5

# Verify service status
echo ""
echo "========================================="
echo "Verifying deployment..."
echo "========================================="
sudo systemctl status maru-guardian --no-pager || true

echo ""
echo "========================================="
echo "Recent logs:"
echo "========================================="
sudo journalctl -u maru-guardian -n 20 --no-pager || true

echo ""
echo "========================================="
echo "Deployment complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Set NOTION_TOKEN in /etc/default/maru-guardian"
echo "2. Restart service: sudo systemctl restart maru-guardian"
echo "3. Monitor logs: sudo journalctl -u maru-guardian -f"
echo ""
echo "Guardian is polling Notion DB every 15 minutes"
echo "Reframe events will be logged to /var/maru/reframe_events/"
echo ""
