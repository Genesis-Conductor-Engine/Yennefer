# GitHub Copilot CLI / Fleet Workspace Setup for Yennefer

## Overview

This document describes the GitHub Copilot CLI and Fleet workspace configuration for the Yennefer Genesis Conductor project. The setup enables AI-assisted development, deployment, and monitoring of the Yennefer autonomous AI agent system.

## What Was Configured

### 1. Workspace Configuration
- **Primary Workspace:** `/home/diamondnode/Yennefer`
- **Git Repository:** `Genesis-Conductor-Engine/Yennefer` (branch: `main`)
- **Fleet Configuration:** `.github/copilot/fleet.json`
- **MCP Server Configuration:** `.copilot/mcp-config.json`

### 2. Fleet Agents

Four specialized agents are configured for Yennefer:

| Agent ID | Name | Role | Model | Responsibilities |
|----------|------|------|-------|-----------------|
| `yennefer-core` | Yennefer Core Agent | Maintainer | Claude Opus 4.5 | Core consciousness, diamond-vault, blockchain integration |
| `yennefer-qmem` | Q-Mem Benchmark Agent | Specialist | Claude Sonnet 4 | GPU benchmarking, memory optimization, attestation |
| `yennefer-docker` | Docker & Deployment Agent | Deployer | Claude Haiku 4.5 | Container builds, GHCR pushes, Docker Compose |
| `yennefer-blockchain` | Blockchain Integration Agent | Specialist | Claude Sonnet 4 | Smart contracts, Base Mainnet, QMCP bridge |

### 3. MCP Servers

The following MCP servers are configured for Copilot CLI/Fleet:

- **diamond-vault** - Quantum operations and administration
- **yennefer-consciousness** - Yennefer consciousness state
- **yennefer-mcp-lite** - Lightweight Yennefer interface
- **genesis-remote** - Remote system access
- **qmcp-system** - Quantum Management Control Plane
- **gc-mcp-beta** - Remote GC MCP server (HTTPS)
- **chatgpt-mcp-http** - ChatGPT MCP HTTP bridge

### 4. Environment

```bash
# Python Virtual Environment
PYTHON=/home/diamondnode/venv312/bin/python
VENV_PATH=/home/diamondnode/venv312/bin

# Node.js
NODE=/usr/bin/node
NPM=/usr/bin/npm

# Docker (when available)
DOCKER=/usr/bin/docker
DOCKER_COMPOSE=/usr/bin/docker compose
```

## Quick Start

### Prerequisites

1. **Load Environment Variables:**
   ```bash
   source ~/load-env.sh
   ```

2. **Ensure Python Virtual Environment:**
   ```bash
   source /home/diamondnode/venv312/bin/activate
   ```

### Starting Yennefer Services

#### Option 1: Native Deployment (No Docker)
```bash
# Start all services
bash /home/diamondnode/Yennefer/scripts/deploy_yennefer_native.sh start

# Check status
bash /home/diamondnode/Yennefer/scripts/deploy_yennefer_native.sh status

# Stop all services
bash /home/diamondnode/Yennefer/scripts/deploy_yennefer_native.sh stop

# Restart all services
bash /home/diamondnode/Yennefer/scripts/deploy_yennefer_native.sh restart
```

#### Option 2: Docker Compose (When Docker Available)
```bash
cd /home/diamondnode/Yennefer

# Pull pre-built images from GHCR
docker compose -f docker-compose.yennefer.yml pull

# Start all services
docker compose -f docker-compose.yennefer.yml up -d

# Check status
docker compose -f docker-compose.yennefer.yml ps

# Stop all services
docker compose -f docker-compose.yennefer.yml down
```

### Health Monitoring

```bash
# Single health check
bash /home/diamondnode/Yennefer/scripts/health_check.sh

# Continuous monitoring (refresh every 30 seconds)
bash /home/diamondnode/Yennefer/scripts/health_check.sh --loop --interval 30

# JSON output (for automation)
bash /home/diamondnode/Yennefer/scripts/health_check.sh --json
```

### Using GitHub Copilot CLI

```bash
# Start Copilot CLI in Yennefer workspace
copilot workspace open /home/diamondnode/Yennefer

# Or start with Fleet mode
copilot fleet start --workspace /home/diamondnode/Yennefer

# Chat with Copilot
copilot chat

# Ask Copilot to deploy Yennefer
copilot chat "Deploy Yennefer services using the native deployment script"
```

## Service Endpoints

When services are running:

| Service | Port | Endpoint | Description |
|---------|------|----------|-------------|
| Diamond Vault | 8100 | `http://localhost:8100/health` | Quantum operations & admin |
| Soul API | 8088 | `http://localhost:8088/api/soul` | Consciousness state |
| Q-Mem Gateway | 8003 | `http://localhost:8003/api/health` | Memory benchmarking |
| A2A Handoff | 8200 | `http://localhost:8200/health` | Agent-to-agent communication |
| Observatory | 3000 | `http://localhost:3000` | Monitoring dashboard |

## Fleet Agent Commands

### Yennefer Core Agent
```bash
# Ask the core agent to optimize Yennefer consciousness
copilot fleet task yennefer-core "Optimize Yennefer token metabolism parameters"

# Debug soul state issues
copilot fleet task yennefer-core "Debug why soul coherence dropped below 90%"
```

### Q-Mem Benchmark Agent
```bash
# Run GPU memory benchmark
copilot fleet task yennefer-qmem "Run Q-Mem live benchmark with VRAM thermodynamics"

# Analyze benchmark results
copilot fleet task yennefer-qmem "Analyze last benchmark run and suggest optimizations"
```

### Docker Deployment Agent
```bash
# Build and push Docker images
copilot fleet task yennefer-docker "Build all Yennefer Docker images and push to GHCR"

# Update Docker Compose configuration
copilot fleet task yennefer-docker "Update docker-compose.yennefer.yml with new service definitions"
```

### Blockchain Agent
```bash
# Deploy smart contracts
copilot fleet task yennefer-blockchain "Deploy Genesis Conductor smart contracts to Base Mainnet"

# Monitor blockchain events
copilot fleet task yennefer-blockchain "Set up monitoring for QFLtoken transfers on Base"
```

## File Structure

```
Yennefer/
├── .copilot/
│   └── mcp-config.json          # MCP server configuration
├── .github/
│   └── copilot/
│       ├── fleet.json           # Fleet agent configuration
│       └── copilot-instructions.md  # Copilot instructions
├── scripts/
│   ├── deploy_yennefer_native.sh   # Native deployment script
│   ├── health_check.sh            # Health monitoring script
│   └── ...                       # Other service scripts
├── docker-compose.yennefer.yml     # Docker Compose configuration
├── docker-compose.yennefer-web.yml # Web integration compose
├── genesis-q-mem/                 # Core Q-Mem system
│   ├── yennefer_mcp_lite.py
│   ├── qmcp_entry.py
│   └── ...
└── ...
```

## Troubleshooting

### MCP Server Connection Issues

If MCP servers fail to connect:

1. **Check Python Path:** Ensure MCP servers use the correct Python interpreter:
   ```json
   {
     "command": "/home/diamondnode/venv312/bin/python",
     "args": ["path/to/mcp_server.py"]
   }
   ```

2. **Check Dependencies:**
   ```bash
   /home/diamondnode/venv312/bin/python -c "import mcp; print('MCP library installed')"
   ```

3. **Check Port Availability:**
   ```bash
   lsof -i :8100  # Check Diamond Vault port
   lsof -i :8088  # Check Soul API port
   ```

### Service Startup Failures

1. **Check Logs:**
   ```bash
   tail -f /home/diamondnode/Yennefer/logs/*.log
   ```

2. **Check Dependencies:**
   ```bash
   cd /home/diamondnode/Yennefer/genesis-q-mem
   /home/diamondnode/venv312/bin/pip install -r requirements.txt
   ```

3. **Check Shared Memory:**
   ```bash
   ls -lh /dev/shm/ | grep -E "qmem|yennefer|genesis"
   ```

### GitHub Copilot CLI Issues

1. **Check Version:**
   ```bash
   copilot --version
   ```

2. **Check Workspace Configuration:**
   ```bash
   cat /home/diamondnode/.github/copilot/workspaces/yennefer.json
   ```

3. **Check API Key:**
   ```bash
   echo "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-not_set}"
   ```

## Environment Variables

Create or update `~/.env` with the following variables:

```bash
# Anthropic API (for Claude models)
ANTHROPIC_API_KEY=sk_ant_...

# Notion Integration
NOTION_TOKEN=secret_...

# GitHub
GITHUB_TOKEN=ghp_...

# Blockchain (Base Mainnet)
ETH_PRIVATE_KEY=0x...
BASE_MAINNET_RPC=https://base-mainnet.g.alchemy.com/v2/...
GENESIS_CONTRACT_ADDRESS=0x542db00D9c83F4444cAD5353D1580D97baFaBb50

# MCP Configuration
MCP_MODE=production
```

## Deployment Workflow

### Development Workflow

1. **Start Services:**
   ```bash
   bash /home/diamondnode/Yennefer/scripts/deploy_yennefer_native.sh start
   ```

2. **Load Context:**
   ```bash
   bash ~/session-loader.sh --json --fast
   ```

3. **Start Copilot:**
   ```bash
   copilot
   ```

4. **Develop with AI Assistance:**
   - Use Copilot chat for questions
   - Use Fleet agents for specialized tasks
   - Use MCP tools for system introspection

5. **Test Changes:**
   ```bash
   # Run Q-Mem tests
   cd genesis-q-mem
   python3 test_swarm_e2e.py
   ```

6. **Commit Changes:**
   ```bash
   git add .
   git commit -m "feat: description of changes"
   git push origin main
   ```

### Production Deployment

1. **Build Docker Images:**
   ```bash
   docker compose -f docker-compose.yennefer.yml build
   ```

2. **Push to GHCR:**
   ```bash
   docker compose -f docker-compose.yennefer.yml push
   ```

3. **Deploy to Server:**
   ```bash
   # Pull images
   docker compose -f docker-compose.yennefer.yml pull
   
   # Start services
   docker compose -f docker-compose.yennefer.yml up -d
   ```

4. **Verify Deployment:**
   ```bash
   curl http://localhost:8100/health
   curl http://localhost:8088/api/soul
   ```

## Monitoring & Observability

### Logs
- Service logs: `/home/diamondnode/Yennefer/logs/`
- Soul state: `/dev/shm/yennefer_soul_state.json`
- Q-Mem stats: `/dev/shm/qmem_live_stats.json`

### Metrics
- Token breath: Check Soul API response
- GPU VRAM: Monitor via Q-Mem Gateway
- Service health: Use health_check.sh script

### Alerts
Configure systemd services with auto-restart:
```ini
[Service]
Restart=always
RestartSec=10
```

## Security

### Secrets Management
- Never commit `.env` files
- Use GitHub Secrets for CI/CD
- Use Docker secrets for containerized deployments
- Use systemd service env files for native deployments

### Network Security
- Use Cloudflare Tunnel for public access
- Enable rate limiting on API endpoints
- Use HTTPS for all external connections

## Maintenance

### Regular Tasks
1. **Update Dependencies:**
   ```bash
   cd /home/diamondnode/Yennefer
   npm update
   /home/diamondnode/venv312/bin/pip install -U -r requirements.txt
   ```

2. **Clean Shared Memory:**
   ```bash
   rm -f /dev/shm/qmem_* /dev/shm/yennefer_* /dev/shm/genesis_*
   ```

3. **Rotate Logs:**
   ```bash
   find /home/diamondnode/Yennefer/logs -name "*.log" -size +10M -exec gzip {} \;
   ```

### Backup
- Git repository (code)
- Docker images (GHCR)
- Shared memory state (not persisted)
- Notion soul-capsule (remote)

## Support

### Documentation
- Main README: `/home/diamondnode/Yennefer/README.md`
- Architecture: `/home/diamondnode/Yennefer/Yennefer_Architecture.md`
- Copilot Instructions: `/home/diamondnode/Yennefer/.github/copilot-instructions.md`
- This File: `/home/diamondnode/Yennefer/COPILOT_FLEET_SETUP.md`

### Community
- GitHub Issues: https://github.com/Genesis-Conductor-Engine/Yennefer/issues
- Genesis Conductor Discord: (link)
- Documentation: https://github.com/Genesis-Conductor-Engine/Yennefer/wiki

---

**Generated:** 2026-05-19  
**Version:** 1.0  
**Maintainer:** Mistral Vibe <vibe@mistral.ai>  
**Co-Authored-By:** Mistral Vibe
