#!/bin/bash
# GitHub Repository Push Automation Script
# Run this script after authenticating with: gh auth login --web

set -e  # Exit on error

echo "════════════════════════════════════════════════════════════════"
echo "  Diamond Node Unified Inference - GitHub Push Script"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check if authenticated
echo "→ Checking GitHub authentication..."
if ! gh auth status &>/dev/null; then
    echo "❌ Not authenticated with GitHub"
    echo ""
    echo "Please run first: gh auth login --web"
    exit 1
fi
echo "✅ Authenticated"
echo ""

# Get GitHub username
GITHUB_USER=$(gh api user -q .login)
echo "→ GitHub user: $GITHUB_USER"
echo ""

# Create repository
echo "→ Creating GitHub repository..."
if gh repo create diamondnode-unified-inference \
    --public \
    --source=. \
    --description="Unified ML inference system with Claude Opus orchestration, CUDA-Q quantum optimization, YOLO11 detection, and blockchain analytics" \
    --push; then
    echo "✅ Repository created and code pushed"
else
    echo "⚠️  Repository may already exist or push failed"
    echo "   Attempting to add remote and push..."
    
    if ! git remote get-url origin &>/dev/null; then
        git remote add origin "https://github.com/${GITHUB_USER}/diamondnode-unified-inference.git"
    fi
    
    git push -u origin master
fi
echo ""

# Configure repository - topics
echo "→ Adding repository topics..."
gh repo edit --add-topic ai
gh repo edit --add-topic ml
gh repo edit --add-topic quantum-computing
gh repo edit --add-topic blockchain
gh repo edit --add-topic claude
gh repo edit --add-topic yolo
gh repo edit --add-topic cuda
gh repo edit --add-topic mcp
gh repo edit --add-topic fastapi
echo "✅ Topics added"
echo ""

# Enable features
echo "→ Enabling repository features..."
gh repo edit --enable-issues
gh repo edit --enable-wiki
gh repo edit --enable-projects
echo "✅ Features enabled"
echo ""

# Configure GitHub Pages
echo "→ Configuring GitHub Pages..."
if gh api "repos/${GITHUB_USER}/diamondnode-unified-inference/pages" \
    -X POST \
    -f source[branch]=master \
    -f source[path]=/docs \
    --silent 2>/dev/null; then
    echo "✅ GitHub Pages enabled"
else
    echo "⚠️  GitHub Pages may already be enabled or needs manual setup"
    echo "   Configure manually: Settings > Pages > Source: master / /docs"
fi
echo ""

# Create release
echo "→ Creating v1.0.0 release..."
if git tag v1.0.0 2>/dev/null; then
    git tag -a v1.0.0 -m "Release v1.0.0: Diamond Node Unified Inference System

Initial release with:
- Claude Opus 4.7 orchestrator
- CUDA-Q QAOA optimization (165ms, 91% purity)
- YOLO11 object detection (27.5 FPS)
- Blockchain wallet analytics (4 tools)
- MCP Apps interactive UIs
- Triple monitoring (AppSignal + LangSmith + Vercel)
- Production-ready web dashboard
- Complete documentation (27 files)
" --force
fi

git push origin v1.0.0

gh release create v1.0.0 \
    --title "v1.0.0 - Diamond Node Unified Inference System" \
    --notes "🚀 **Initial Release**

## Features

### Core Infrastructure
- **Claude Opus 4.7 Orchestrator** - Advanced AI decision-making
- **CUDA-Q QAOA Optimization** - 165ms quantum optimization, 91% purity
- **YOLO11 Object Detection** - Real-time detection at 27.5 FPS
- **Blockchain Analytics** - 4-tool wallet analysis suite

### MCP Integration
- Interactive UIs for all capabilities
- Context-aware tool selection
- Real-time status monitoring

### Monitoring & Observability
- AppSignal application monitoring
- LangSmith LLM observability
- Vercel analytics integration

### Documentation
- 27 comprehensive documentation files
- API references for all modules
- Development guides and examples
- Security and contribution guidelines

### Infrastructure
- GitHub Actions CI/CD workflows
- Automated testing and linting
- Security scanning with Dependabot
- Production-ready web dashboard

## Quick Start

\`\`\`bash
git clone https://github.com/${GITHUB_USER}/diamondnode-unified-inference.git
cd diamondnode-unified-inference
pip install -r requirements.txt
python src/orchestrator/claude_orchestrator.py
\`\`\`

See [README.md](README.md) for full documentation.
"

echo "✅ Release v1.0.0 created"
echo ""

# Summary
echo "════════════════════════════════════════════════════════════════"
echo "  🎉 SUCCESS! Repository pushed to GitHub"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Repository URL:"
echo "  https://github.com/${GITHUB_USER}/diamondnode-unified-inference"
echo ""
echo "Next Steps:"
echo "  1. Add secrets (Settings > Secrets and variables > Actions):"
echo "     - ANTHROPIC_API_KEY"
echo "     - GATEWAY_SECRET"
echo "     - LANGSMITH_API_KEY"
echo "     - APPSIGNAL_API_KEY"
echo ""
echo "  2. Verify GitHub Pages (may take a few minutes):"
echo "     https://${GITHUB_USER}.github.io/diamondnode-unified-inference/"
echo ""
echo "  3. Check CI/CD workflows:"
echo "     https://github.com/${GITHUB_USER}/diamondnode-unified-inference/actions"
echo ""
echo "  4. View repository:"
gh repo view --web
echo ""
