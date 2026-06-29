#!/bin/bash
# Quick seed runner - sources common env and runs seed script
# Usage: ./run_seed_telemetry.sh [notion_token]

set -e

cd "$(dirname "$0")/.."

# Activate venv
if [ -d "yennefer_venv" ]; then
    source yennefer_venv/bin/activate
else
    echo "❌ yennefer_venv not found. Run from diamondnode-unified-inference directory."
    exit 1
fi

# Get token from argument or environment
if [ -n "$1" ]; then
    export NOTION_TOKEN="$1"
    echo "Using token from command line argument"
elif [ -n "$NOTION_TOKEN" ]; then
    echo "Using token from NOTION_TOKEN environment variable"
elif [ -f "$HOME/.env" ]; then
    # Try to load from ~/.env
    export $(grep -v '^#' "$HOME/.env" | grep NOTION_TOKEN | xargs 2>/dev/null) || true
    if [ -z "$NOTION_TOKEN" ]; then
        echo "❌ NOTION_TOKEN not found in ~/.env"
        echo ""
        echo "Usage:"
        echo "  1. ./run_seed_telemetry.sh 'secret_your_token_here'"
        echo "  2. export NOTION_TOKEN='secret_your_token_here' && ./run_seed_telemetry.sh"
        echo "  3. Add NOTION_TOKEN to ~/.env and run ./run_seed_telemetry.sh"
        echo ""
        echo "See scripts/SETUP_NOTION_SEED.md for details."
        exit 1
    fi
else
    echo "❌ No NOTION_TOKEN found"
    echo ""
    echo "Usage: ./run_seed_telemetry.sh 'secret_your_token_here'"
    exit 1
fi

echo "🌟 Running Notion Telemetry Seed"
echo "Database: 9a32dcb5-00b6-40d7-bd86-43d93965fa82"
echo ""

# Run seed script
python3 scripts/seed_notion_telemetry.py

echo ""
echo "Running verification..."
echo ""

# Run verification
python3 scripts/verify_notion_seed.py

echo ""
echo "✅ Seed and verification complete!"
