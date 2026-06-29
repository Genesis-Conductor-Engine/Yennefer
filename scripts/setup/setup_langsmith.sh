#!/bin/bash
# Export LangSmith credentials for Diamond Node

export LANGSMITH_TRACING=true
export LANGSMITH_ENDPOINT=https://api.smith.langchain.com
export LANGSMITH_API_KEY=$YOUR_LANGSMITH_API_KEY
export LANGSMITH_PROJECT=diamondnode

echo "✓ LangSmith environment variables exported"
echo "  Project: diamondnode"
echo "  Dashboard: https://smith.langchain.com/"
