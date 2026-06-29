# Repository Structure Summary

## Directory Organization

```
diamondnode-unified-inference/
├── .github/workflows/      # CI/CD pipelines (to be added)
├── src/                    # Core source code
│   ├── orchestrator/       # Claude orchestrator & configuration
│   ├── models/            # CUDA-Q, waveform equilibrium
│   ├── blockchain/        # Wallet analysis tools
│   └── monitoring/        # Monitoring integrations (to be added)
├── web/                    # Web interfaces
│   ├── ui/                # FastAPI web UI
│   ├── mcp-apps/          # MCP Apps server
│   └── static/            # HTML/CSS/JS assets
├── config/                 # Configuration files
├── docs/                   # Documentation
│   ├── architecture/      # System design
│   ├── guides/            # Integration guides
│   ├── api/               # API reference (to be added)
│   └── deployment/        # Production deployment docs
├── tests/                  # Test suites
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── benchmarks/        # Performance benchmarks
└── scripts/                # Utility scripts
    ├── setup/             # Installation scripts
    ├── deploy/            # Deployment scripts
    └── utils/             # Utility scripts
```

## File Counts

- **Source Files (src/)**: 11 Python modules
  - orchestrator/: 4 files (orchestrator, config, health_check, langsmith)
  - models/: 2 files (waveform_equilibrium, mycelial_qubo)
  - blockchain/: 1 file (blockchain_tools)
  - monitoring/: 0 files (to be populated from opentelemetry-go)

- **Web Files (web/)**: 6 files
  - ui/: 1 file (web_ui.py)
  - mcp-apps/: 2 files (server + config)
  - static/: 3 files (HTML, CSS, JS)

- **Tests (tests/)**: 4 test files
  - integration/: 3 files (blockchain, gateway tests)
  - unit/: 1 file (waveform_equilibrium_test)

- **Scripts (scripts/)**: 4 shell scripts
  - setup/: 2 files (langsmith, gateway_secret)
  - deploy/: 1 file (install_web_ui)
  - utils/: 1 file (verify_streaming)

- **Documentation (docs/)**: 19 markdown files
  - architecture/: 5 files
  - guides/: 8 files
  - deployment/: 6 files

- **Configuration (config/)**: 1 file (.env.example)

## Git Repository

- **Initialized**: Yes
- **Commits**: 2
  1. Initial .gitignore
  2. Directory structure with all files
- **Branch**: master
- **User**: Diamond Node Team <diamondnode@example.com>

## Next Steps

1. ✅ Directory structure created
2. ✅ Git initialized
3. ✅ Files organized
4. ✅ Initial commits made
5. ⏳ Update import paths in Python files
6. ⏳ Add monitoring files from opentelemetry-go
7. ⏳ Create README.md
8. ⏳ Create requirements.txt
9. ⏳ Create package.json
10. ⏳ Create LICENSE and CONTRIBUTING.md

## Import Path Changes Needed

Files that may need import updates:
- `web/ui/web_ui.py` - imports from orchestrator, models
- `tests/*` - test imports need updating
- Any files importing from flat structure need path updates

Original locations preserved in:
- ~/unified_inference/
- ~/diamond-node/scripts/
- ~/home/diamondnode/

