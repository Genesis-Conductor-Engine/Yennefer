#!/bin/bash
# Script to extract GATEWAY_SECRET and add it to ~/.env
# Must be run with sudo to read /etc/default/diamond-gateway

set -e

GATEWAY_CONFIG="/etc/default/diamond-gateway"
ENV_FILE="$HOME/.env"

echo "=========================================="
echo "Diamond Gateway Secret Setup"
echo "=========================================="
echo

# Check if gateway config exists
if [ ! -f "$GATEWAY_CONFIG" ]; then
    echo "Error: $GATEWAY_CONFIG not found"
    exit 1
fi

# Check if we can read it (requires sudo)
if [ ! -r "$GATEWAY_CONFIG" ]; then
    echo "Reading gateway secret (requires sudo)..."
    GATEWAY_SECRET=$(sudo grep "^GATEWAY_SECRET=" "$GATEWAY_CONFIG" | cut -d'=' -f2-)
else
    echo "Reading gateway secret..."
    GATEWAY_SECRET=$(grep "^GATEWAY_SECRET=" "$GATEWAY_CONFIG" | cut -d'=' -f2-)
fi

if [ -z "$GATEWAY_SECRET" ]; then
    echo "Error: GATEWAY_SECRET not found in $GATEWAY_CONFIG"
    exit 1
fi

echo "✓ Gateway secret found"

# Create .env if it doesn't exist
if [ ! -f "$ENV_FILE" ]; then
    echo "Creating $ENV_FILE from template..."
    cp ~/unified_inference/.env.example "$ENV_FILE"
    echo "✓ Created $ENV_FILE"
else
    echo "✓ $ENV_FILE already exists"
fi

# Update or add GATEWAY_SECRET
if grep -q "^GATEWAY_SECRET=" "$ENV_FILE"; then
    # Update existing
    sed -i "s|^GATEWAY_SECRET=.*|GATEWAY_SECRET=$GATEWAY_SECRET|" "$ENV_FILE"
    echo "✓ Updated GATEWAY_SECRET in $ENV_FILE"
else
    # Add new
    echo "GATEWAY_SECRET=$GATEWAY_SECRET" >> "$ENV_FILE"
    echo "✓ Added GATEWAY_SECRET to $ENV_FILE"
fi

# Set secure permissions
chmod 600 "$ENV_FILE"
echo "✓ Set secure permissions (600) on $ENV_FILE"

echo
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo
echo "The GATEWAY_SECRET has been configured in $ENV_FILE"
echo "You can now run claude_orchestrator.py with gateway integration."
echo
