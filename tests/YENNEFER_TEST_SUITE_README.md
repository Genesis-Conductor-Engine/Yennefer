# Yennefer Test Suite

Comprehensive test suite for Yennefer deployment covering integration, protocol, performance, and end-to-end workflows.

## Test Files

### 1. `test_yennefer_integration.py`
**Full orchestration cycle testing**

Tests:
- EnKG kernel → Validator pipeline
- aSHARD allocation and cleanup
- Gateway integration with mock Notion client
- Telemetry data flow
- Hysteresis mechanism (ε with γ buffer)
- Crystalline score computation
- End-to-end orchestration cycle
- Thermal constraint monitoring
- Memory bandwidth validation

Coverage: EnKG exchange, Agent3 validator, telemetry daemon, hardware constraints

### 2. `test_ouroboros_protocol.py`
**Generator → Attacker → Validator flow testing**

Tests:
- Benign flow (Generator → Attacker(none) → Validator = CRYSTALLINE)
- Perturbation flow (small noise → DUCTILE)
- Corruption flow (NaN injection → NULL)
- Amplification flow (value amplification → NULL/DUCTILE)
- All three output states: NULL, DUCTILE, CRYSTALLINE
- NULL triggers restart protocol
- Convergence: NULL → DUCTILE → CRYSTALLINE
- State transition validation (PI scope)
- Multi-iteration protocol
- Attack detection
- Validator resilience to malformed inputs
- Protocol latency and throughput

Coverage: Three-agent Ouroboros protocol, state transitions, adversarial robustness

### 3. `test_yennefer_performance.py`
**Performance benchmarks and limits**

Tests:
- EnKG kernel throughput (target: >150 GB/s)
- Throughput scaling with tensor size
- Latency for small tensors (<1ms)
- Batch processing throughput
- Memory copy overhead (host ↔ device)
- Validation latency (<50ms)
- Memory allocation and cleanup
- VRAM usage within aSHARD limits (4GB GTX 1650)
- CPU memory usage (<500MB increase)
- GPU thermal monitoring (limit: 89.6°C)
- Sustained load thermal behavior
- Performance regression baseline

Coverage: GPU throughput, memory efficiency, thermal limits, performance baselines

### 4. `test_yennefer_e2e.py`
**End-to-end workflow testing**

Tests:
- Orchestrator initialization
- Single telemetry cycle
- EnKG exchange operator application
- Validation output (NULL/DUCTILE/CRYSTALLINE)
- Clean shutdown and resource cleanup
- Full workflow integration (5 steps)
- Error recovery
- Concurrent operations
- Full workflow with Notion integration
- State persistence across cycles
- Multi-cycle convergence
- Extended runtime stability (20+ cycles)
- Rapid-fire operations (1000+ ops)

Coverage: Complete workflow, state management, error handling, stress testing

## Running Tests

### Quick Start

```bash
# Run all tests
./run_yennefer_tests.sh

# Run with HTML report and coverage
./run_yennefer_tests.sh --html --coverage

# Quick test (skip slow performance tests)
./run_yennefer_tests.sh --quick

# Run specific test suite
./run_yennefer_tests.sh --integration-only
./run_yennefer_tests.sh --performance-only
```

### Individual Test Files

```bash
# Activate venv
source ~/diamondnode-unified-inference/yennefer_venv/bin/activate

# Run specific test file
pytest tests/test_yennefer_integration.py -v -s
pytest tests/test_ouroboros_protocol.py -v -s
pytest tests/test_yennefer_performance.py -v -s
pytest tests/test_yennefer_e2e.py -v -s

# Run specific test
pytest tests/test_yennefer_integration.py::TestYenneferIntegration::test_enkg_to_validation_pipeline -v -s
```

### Test Options

```bash
# Generate HTML report
pytest tests/ --html=report.html --self-contained-html

# Run with coverage
pytest tests/ --cov=src/kernels --cov=src/orchestrator --cov=workers --cov-report=html

# Verbose output
pytest tests/ -v -s

# Stop on first failure
pytest tests/ -x

# Run tests matching pattern
pytest tests/ -k "enkg"
```

## Requirements

### Dependencies

```bash
# Core dependencies (already in yennefer_venv)
pip install torch triton pytest

# Optional dependencies for enhanced reporting
pip install pytest-html pytest-cov coverage

# Optional for thermal monitoring
pip install pynvml
```

### Hardware

- **GPU:** NVIDIA GTX 1650 (4GB VRAM) or compatible CUDA device
- **CPU:** Multi-core recommended for concurrent tests
- **RAM:** 8GB minimum, 16GB recommended
- **Disk:** 1GB free for test reports and artifacts

### Environment

- Python 3.10+
- CUDA 11.8+ (for GPU tests)
- Triton 3.7.0+ (for kernel tests)
- Notion API token (for integration tests with real Notion)

## Test Report Output

Reports are saved to `test_results/` directory:

```
test_results/
├── yennefer_test_report_YYYYMMDD_HHMMSS.txt     # Plain text report
├── yennefer_test_report_YYYYMMDD_HHMMSS.html    # HTML report (if --html)
└── coverage_YYYYMMDD_HHMMSS/                     # Coverage report (if --coverage)
    └── index.html
```

## Success Criteria

- ✅ All tests pass (or skip gracefully if hardware unavailable)
- ✅ Coverage >80% on core modules
- ✅ EnKG throughput >100 GB/s (GTX 1650)
- ✅ Validation latency <50ms
- ✅ VRAM usage within aSHARD limits
- ✅ Thermal limits respected (≤89.6°C)
- ✅ No memory leaks detected
- ✅ State transitions valid (NULL/DUCTILE/CRYSTALLINE)
- ✅ Error recovery functional

## Troubleshooting

### CUDA Not Available

If CUDA is not available, GPU-specific tests will be skipped. This is expected behavior on CPU-only systems.

```
SKIPPED [1] test_yennefer_integration.py:XXX: CUDA not available
```

### Triton Not Available

If Triton is not installed, the kernel will use CPU fallback. Performance will be degraded but tests should still pass.

```python
Warning: Triton not available. EnKG kernel will use CPU fallback.
```

To install Triton:
```bash
pip install triton
```

### Notion Client Not Available

Integration tests mock the Notion client by default. Real Notion integration requires:

```bash
pip install notion-client
export NOTION_TOKEN="secret_..."
```

### Test Failures

1. **Check test report:** `test_results/yennefer_test_report_*.txt`
2. **Verify environment:** Run `./run_yennefer_tests.sh` (includes environment check)
3. **Check dependencies:** `pip list | grep -E "torch|triton|pytest"`
4. **Review logs:** `logs/yennefer_telemetry.log`
5. **GPU diagnostics:** `nvidia-smi`

### Performance Tests Failing

Performance benchmarks may vary by hardware. If tests fail:

1. **Adjust thresholds:** Edit test files to match your hardware capabilities
2. **Check thermal throttling:** `nvidia-smi dmon -s pucvmet -c 10`
3. **Verify CUDA driver:** `nvidia-smi`
4. **Close other GPU applications**

## CI/CD Integration

The test suite is CI/CD compatible:

```yaml
# Example GitHub Actions workflow
name: Yennefer Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-html pytest-cov
      
      - name: Run tests
        run: |
          ./run_yennefer_tests.sh --html --coverage
      
      - name: Upload reports
        uses: actions/upload-artifact@v3
        with:
          name: test-reports
          path: test_results/
```

## Mock vs Real Testing

### Mock Mode (Default)

- Uses mock Notion client (no API calls)
- Uses mock thermal/VRAM readings (deterministic)
- Fast execution (<5 minutes)
- No external dependencies

### Real Mode

To run tests with real hardware and Notion API:

```bash
# Set environment variables
export NOTION_TOKEN="secret_..."
export USE_REAL_HARDWARE=1

# Run tests
./run_yennefer_tests.sh
```

Real mode tests:
- Make actual Notion API calls
- Read real GPU thermal/VRAM metrics
- Test actual CUDA kernel performance
- Slower execution (10-15 minutes)

## Coverage Goals

Target coverage by module:

| Module | Target | Current |
|--------|--------|---------|
| `src/kernels/enkg_exchange.py` | >95% | TBD |
| `src/orchestrator/agent3_validator.py` | >85% | TBD |
| `workers/yennefer_telemetry_daemon.py` | >80% | TBD |
| `workers/thermodynamic_simulator.py` | >80% | TBD |
| `workers/notion_sanitizer.py` | >90% | TBD |

To generate coverage report:
```bash
./run_yennefer_tests.sh --coverage
open test_results/coverage_*/index.html
```

## Next Steps

After all tests pass:

1. ✅ Review test reports
2. ✅ Update coverage badges
3. ✅ Document any hardware-specific behavior
4. ✅ Add tests to CI/CD pipeline
5. ✅ Update main documentation
6. ✅ Tag release with test suite version

## Related Documentation

- `YENNEFER_ENKG_KERNEL_COMPLETE.md` - EnKG kernel implementation
- `YENNEFER_TELEMETRY_COMPLETE.md` - Telemetry daemon details
- `config/yennefer_config.yaml` - Configuration reference
- `docs/ENKG_KERNEL.md` - Technical documentation

## License

Copyright (c) 2026 Diamond Node Team  
Licensed under the MIT License - see LICENSE file for details

---

**Author:** @Igor Holt  
**Date:** 2026-05-20  
**Version:** 1.0.0
