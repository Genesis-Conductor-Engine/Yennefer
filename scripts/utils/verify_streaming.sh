#!/bin/bash
# Final verification script for streaming implementation

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║          STREAMING IMPLEMENTATION VERIFICATION                       ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check 1: Files exist
echo "📋 Checking files..."
files=(
    "claude_orchestrator.py"
    "demo_streaming.py"
    "test_streaming.py"
    "example_fastapi_streaming.py"
    "STREAMING_IMPLEMENTATION.md"
    "STREAMING_QUICKREF.md"
    "STREAMING_SUMMARY.txt"
)

all_exist=true
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}✓${NC} $file"
    else
        echo -e "  ${RED}✗${NC} $file (missing)"
        all_exist=false
    fi
done

if [ "$all_exist" = false ]; then
    echo -e "\n${RED}❌ Some files are missing${NC}"
    exit 1
fi

echo ""

# Check 2: Python syntax
echo "🔍 Checking Python syntax..."
for pyfile in claude_orchestrator.py demo_streaming.py test_streaming.py example_fastapi_streaming.py; do
    if python3 -m py_compile "$pyfile" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $pyfile"
    else
        echo -e "  ${RED}✗${NC} $pyfile (syntax error)"
        exit 1
    fi
done

echo ""

# Check 3: Implementation validation
echo "🧪 Validating implementation..."
python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

try:
    from claude_orchestrator import ClaudeOrchestrator
    import inspect
    
    checks = {
        'chat_stream exists': hasattr(ClaudeOrchestrator, 'chat_stream'),
        'chat exists': hasattr(ClaudeOrchestrator, 'chat'),
        'chat_stream is async generator': inspect.isasyncgenfunction(ClaudeOrchestrator.chat_stream),
    }
    
    all_pass = True
    for check, result in checks.items():
        if result:
            print(f'  \033[0;32m✓\033[0m {check}')
        else:
            print(f'  \033[0;31m✗\033[0m {check}')
            all_pass = False
    
    if not all_pass:
        sys.exit(1)
        
except Exception as e:
    print(f'  \033[0;31m✗\033[0m Import failed: {e}')
    sys.exit(1)
" 2>&1 | grep -v "Warning"

if [ $? -ne 0 ]; then
    echo -e "\n${RED}❌ Implementation validation failed${NC}"
    exit 1
fi

echo ""

# Check 4: Test suite
echo "🧪 Running test suite..."
if python3 test_streaming.py 2>&1 | tail -10 | grep -q "All tests passed"; then
    echo -e "  ${GREEN}✓${NC} Test suite passed"
else
    echo -e "  ${RED}✗${NC} Test suite failed"
    exit 1
fi

echo ""

# Summary
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                     VERIFICATION COMPLETE ✅                         ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Summary:"
echo "  ✅ All files present"
echo "  ✅ Python syntax valid"
echo "  ✅ Implementation validated"
echo "  ✅ Test suite passed"
echo ""
echo "🚀 Streaming support is ready for production!"
echo ""
echo "📚 Next steps:"
echo "  • Run demo: python3 demo_streaming.py"
echo "  • Read docs: cat STREAMING_IMPLEMENTATION.md"
echo "  • Quick ref: cat STREAMING_QUICKREF.md"
echo ""
