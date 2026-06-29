# Diamond Node Unified Inference - Quick Start

## 📍 Repository Location
```
/home/diamondnode/diamondnode-unified-inference/
```

## 🏗️ Project Structure

```
diamondnode-unified-inference/
├── src/                    # Core source code
│   ├── orchestrator/       # Claude orchestrator & configuration
│   ├── models/            # CUDA-Q, waveform equilibrium
│   ├── blockchain/        # Wallet analysis tools
│   └── monitoring/        # Monitoring integrations
├── web/                    # Web interfaces
│   ├── ui/                # FastAPI web UI
│   ├── mcp-apps/          # MCP Apps server
│   └── static/            # HTML/CSS/JS assets
├── tests/                  # Test suites
├── scripts/                # Utility scripts
├── docs/                   # Documentation
└── config/                 # Configuration
```

## 🚀 Quick Commands

### Navigate to repository
```bash
cd ~/diamondnode-unified-inference
```

### Check git status
```bash
git status
git log --oneline
```

### Run web UI
```bash
cd ~/diamondnode-unified-inference
python -m web.ui.web_ui
```

### Run tests
```bash
# Unit tests
python -m pytest tests/unit/

# Integration tests
python -m pytest tests/integration/
```

## 📦 Import Structure

All imports now use the new package structure:

```python
# Orchestrator
from src.orchestrator.claude_orchestrator import ClaudeOrchestrator
from src.orchestrator.config import get_config

# Models
from src.models.waveform_equilibrium import compute_waveform_state
from src.models.mycelial_qubo import solve_qubo

# Blockchain
from src.blockchain.blockchain_tools import get_analyzer
```

## 📚 Documentation

- **Architecture**: `docs/architecture/`
- **Guides**: `docs/guides/`
- **Deployment**: `docs/deployment/`
- **API Docs**: `docs/api/` (coming soon)

## 🔗 Original Files

Original files are preserved in:
- `~/unified_inference/`
- `~/diamond-node/scripts/`

## 🎯 Next Steps

1. [ ] Create comprehensive README.md
2. [ ] Create requirements.txt
3. [ ] Create package.json
4. [ ] Add LICENSE file
5. [ ] Add CONTRIBUTING.md
6. [ ] Set up CI/CD workflows

## 📊 Repository Stats

- **Python files**: 20
- **Documentation**: 19 markdown files
- **Scripts**: 4 shell scripts
- **Git commits**: 3
- **Branch**: master

---

**Last Updated**: Task completed successfully ✅
