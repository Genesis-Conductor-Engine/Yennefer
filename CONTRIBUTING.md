# Contributing to Diamond Node

Thank you for your interest in contributing! This guide will help you get started.

## 🚀 Quick Start

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/diamondnode-unified-inference.git`
3. Create a branch: `git checkout -b feature/your-feature`
4. Make your changes
5. Run tests: `pytest tests/`
6. Commit: `git commit -m "feat: add your feature"`
7. Push: `git push origin feature/your-feature`
8. Open a Pull Request

## 📋 Development Setup

### Prerequisites
- Python 3.12+
- Node.js 22+
- NVIDIA GPU (GTX 1650 or better)
- CUDA 12.8+
- 16GB RAM

### Installation
```bash
# Clone repository
git clone https://github.com/your-org/diamondnode-unified-inference.git
cd diamondnode-unified-inference

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install Node.js dependencies
npm install

# Set up environment
cp config/.env.example .env
# Edit .env with your API keys

# Run tests
pytest tests/ -v
npm test
```

## 🎯 Code Standards

### Python
- **Style:** Black (line length 100)
- **Linting:** Ruff
- **Type hints:** Required for all functions
- **Docstrings:** Google style

```bash
# Format code
black src/ tests/ --line-length 100

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

### JavaScript/Node
- **Style:** Prettier
- **Linting:** ESLint
- **Type hints:** JSDoc comments

```bash
# Format
npm run format

# Lint
npm run lint
```

## 🧪 Testing

### Python Tests
```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/unit/test_orchestrator.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

### Integration Tests
```bash
# Requires services running
pytest tests/integration/ -v
```

### Benchmarks
```bash
python tests/benchmarks/orthogonal_test.py
```

## 📝 Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `style:` Code style (formatting)
- `refactor:` Code refactoring
- `test:` Tests
- `chore:` Maintenance

**Examples:**
```
feat: add YOLO11 batch detection support
fix: resolve VRAM memory leak in orchestrator
docs: update installation guide for CUDA 12.8
```

## 🔀 Pull Request Process

1. **Create PR** with descriptive title and description
2. **Link issue** if applicable (`Closes #123`)
3. **Ensure tests pass** (CI will run automatically)
4. **Request review** from maintainers
5. **Address feedback** if needed
6. **Maintainer will merge** once approved

### PR Checklist
- [ ] Tests pass (`pytest tests/`)
- [ ] Code formatted (`black`, `prettier`)
- [ ] Type hints added
- [ ] Documentation updated
- [ ] Commit messages follow convention
- [ ] No secrets in code

## 🐛 Reporting Bugs

Use [GitHub Issues](https://github.com/your-org/diamondnode-unified-inference/issues) with:

- **Description:** What went wrong?
- **Steps to reproduce:** How to trigger the bug
- **Expected behavior:** What should happen
- **Environment:** OS, Python version, GPU
- **Logs:** Error messages, stack traces

## 💡 Feature Requests

Open an issue with:
- **Problem:** What problem does it solve?
- **Solution:** Proposed approach
- **Alternatives:** Other solutions considered
- **Use case:** How would you use it?

## 📖 Documentation

- Update docs/ when adding features
- Include code examples
- Add to docs/README.md index
- Keep README.md up-to-date

## 🎨 Code Review

Reviewers check for:
- **Correctness:** Does it work?
- **Tests:** Are edge cases covered?
- **Style:** Follows code standards?
- **Documentation:** Is it documented?
- **Performance:** Any bottlenecks?
- **Security:** Any vulnerabilities?

## 🙏 Attribution

Contributors are listed in:
- GitHub contributors page
- Release notes
- CONTRIBUTORS.md (coming soon)

## 📧 Questions?

- 💬 Discord: [Join community](#)
- 📧 Email: dev@diamondnode.example.com
- 📖 Docs: [Documentation](docs/)

---

**Thank you for contributing! 🎉**
