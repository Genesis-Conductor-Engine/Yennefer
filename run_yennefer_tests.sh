#!/bin/bash
# @Igor Holt
# Yennefer Test Suite Runner
# Runs all Yennefer tests and generates comprehensive report

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directories
REPO_ROOT="/home/diamondnode/diamondnode-unified-inference"
TESTS_DIR="$REPO_ROOT/tests"
REPORTS_DIR="$REPO_ROOT/test_results"
VENV_PATH="$REPO_ROOT/yennefer_venv"

# Test files
INTEGRATION_TEST="$TESTS_DIR/test_yennefer_integration.py"
OUROBOROS_TEST="$TESTS_DIR/test_ouroboros_protocol.py"
PERFORMANCE_TEST="$TESTS_DIR/test_yennefer_performance.py"
E2E_TEST="$TESTS_DIR/test_yennefer_e2e.py"

# Report files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
REPORT_FILE="$REPORTS_DIR/yennefer_test_report_${TIMESTAMP}.txt"
HTML_REPORT="$REPORTS_DIR/yennefer_test_report_${TIMESTAMP}.html"
COVERAGE_DIR="$REPORTS_DIR/coverage_${TIMESTAMP}"

# Create reports directory
mkdir -p "$REPORTS_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Yennefer Test Suite Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Report directory: $REPORTS_DIR"
echo "Report file: $REPORT_FILE"
echo ""

# Function to run test and capture results
run_test() {
    local test_file=$1
    local test_name=$2
    local test_flags=$3
    
    echo -e "${YELLOW}Running $test_name...${NC}"
    echo ""
    
    # Activate venv and run test
    source "$VENV_PATH/bin/activate"
    
    if pytest "$test_file" -v -s $test_flags 2>&1 | tee -a "$REPORT_FILE"; then
        echo -e "${GREEN}✓ $test_name PASSED${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}✗ $test_name FAILED${NC}"
        echo ""
        return 1
    fi
}

# Function to check environment
check_environment() {
    echo -e "${BLUE}Checking environment...${NC}"
    
    # Check venv
    if [ ! -d "$VENV_PATH" ]; then
        echo -e "${RED}✗ Virtual environment not found at $VENV_PATH${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Virtual environment found${NC}"
    
    # Check Python
    source "$VENV_PATH/bin/activate"
    PYTHON_VERSION=$(python --version 2>&1)
    echo -e "${GREEN}✓ Python: $PYTHON_VERSION${NC}"
    
    # Check CUDA
    if python -c "import torch; print('CUDA available:', torch.cuda.is_available())" 2>&1 | grep -q "True"; then
        CUDA_VERSION=$(python -c "import torch; print(torch.version.cuda)" 2>/dev/null || echo "N/A")
        echo -e "${GREEN}✓ CUDA available (version: $CUDA_VERSION)${NC}"
    else
        echo -e "${YELLOW}⚠ CUDA not available (some tests will be skipped)${NC}"
    fi
    
    # Check Triton
    if python -c "import triton" 2>/dev/null; then
        echo -e "${GREEN}✓ Triton available${NC}"
    else
        echo -e "${YELLOW}⚠ Triton not available (will use CPU fallback)${NC}"
    fi
    
    echo ""
}

# Function to generate HTML report
generate_html_report() {
    echo -e "${BLUE}Generating HTML report...${NC}"
    
    source "$VENV_PATH/bin/activate"
    
    # Run pytest with HTML generation
    pytest "$TESTS_DIR/test_yennefer_integration.py" \
           "$TESTS_DIR/test_ouroboros_protocol.py" \
           "$TESTS_DIR/test_yennefer_performance.py" \
           "$TESTS_DIR/test_yennefer_e2e.py" \
           --html="$HTML_REPORT" --self-contained-html \
           -v 2>&1 || true
    
    if [ -f "$HTML_REPORT" ]; then
        echo -e "${GREEN}✓ HTML report generated: $HTML_REPORT${NC}"
    else
        echo -e "${YELLOW}⚠ HTML report generation skipped (pytest-html not installed)${NC}"
    fi
}

# Function to run coverage analysis
run_coverage() {
    echo -e "${BLUE}Running coverage analysis...${NC}"
    
    source "$VENV_PATH/bin/activate"
    
    # Check if coverage is installed
    if ! python -c "import coverage" 2>/dev/null; then
        echo -e "${YELLOW}⚠ Coverage not installed, skipping coverage analysis${NC}"
        echo "  Install with: pip install coverage pytest-cov"
        return 0
    fi
    
    # Run tests with coverage
    pytest "$TESTS_DIR/test_yennefer_integration.py" \
           "$TESTS_DIR/test_ouroboros_protocol.py" \
           "$TESTS_DIR/test_yennefer_e2e.py" \
           --cov=src/kernels --cov=src/orchestrator --cov=workers \
           --cov-report=html:"$COVERAGE_DIR" \
           --cov-report=term \
           -v 2>&1 | tee -a "$REPORT_FILE" || true
    
    if [ -d "$COVERAGE_DIR" ]; then
        echo -e "${GREEN}✓ Coverage report: $COVERAGE_DIR/index.html${NC}"
    fi
}

# Main execution
main() {
    # Initialize report
    {
        echo "========================================"
        echo "Yennefer Test Suite Report"
        echo "========================================"
        echo "Date: $(date)"
        echo "Host: $(hostname)"
        echo "Repo: $REPO_ROOT"
        echo "========================================"
        echo ""
    } > "$REPORT_FILE"
    
    # Check environment
    check_environment
    
    # Track results
    PASSED=0
    FAILED=0
    SKIPPED=0
    
    # Run integration tests
    if run_test "$INTEGRATION_TEST" "Integration Tests" ""; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    # Run Ouroboros protocol tests
    if run_test "$OUROBOROS_TEST" "Ouroboros Protocol Tests" ""; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    # Run performance tests
    echo -e "${YELLOW}Running Performance Tests (may take several minutes)...${NC}"
    if run_test "$PERFORMANCE_TEST" "Performance Tests" ""; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    # Run E2E tests
    if run_test "$E2E_TEST" "End-to-End Tests" ""; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    
    # Optional: Generate HTML report
    if [ "${GENERATE_HTML:-no}" = "yes" ]; then
        generate_html_report
    fi
    
    # Optional: Run coverage
    if [ "${RUN_COVERAGE:-no}" = "yes" ]; then
        run_coverage
    fi
    
    # Summary
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Test Suite Summary${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    {
        echo ""
        echo "========================================"
        echo "Test Suite Summary"
        echo "========================================"
        echo "Test Suites Passed: $PASSED"
        echo "Test Suites Failed: $FAILED"
        echo "Report: $REPORT_FILE"
        echo "========================================"
    } | tee -a "$REPORT_FILE"
    
    echo ""
    
    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ All test suites passed!${NC}"
        echo ""
        echo -e "${BLUE}Next steps:${NC}"
        echo "  1. Review detailed report: $REPORT_FILE"
        echo "  2. Check performance metrics"
        echo "  3. Update documentation if needed"
        echo ""
        exit 0
    else
        echo -e "${RED}✗ $FAILED test suite(s) failed${NC}"
        echo ""
        echo -e "${BLUE}Troubleshooting:${NC}"
        echo "  1. Review errors in: $REPORT_FILE"
        echo "  2. Check CUDA availability"
        echo "  3. Verify config files"
        echo "  4. Check dependencies"
        echo ""
        exit 1
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --html)
            GENERATE_HTML=yes
            shift
            ;;
        --coverage)
            RUN_COVERAGE=yes
            shift
            ;;
        --integration-only)
            E2E_TEST=""
            PERFORMANCE_TEST=""
            OUROBOROS_TEST=""
            shift
            ;;
        --performance-only)
            INTEGRATION_TEST=""
            E2E_TEST=""
            OUROBOROS_TEST=""
            shift
            ;;
        --quick)
            # Skip slow performance tests
            PERFORMANCE_TEST=""
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --html              Generate HTML report"
            echo "  --coverage          Run coverage analysis"
            echo "  --integration-only  Run only integration tests"
            echo "  --performance-only  Run only performance tests"
            echo "  --quick             Skip slow performance tests"
            echo "  --help              Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                  # Run all tests"
            echo "  $0 --html --coverage                # Run all tests with reports"
            echo "  $0 --quick                          # Quick test (skip performance)"
            echo "  $0 --integration-only               # Only integration tests"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run main
main
