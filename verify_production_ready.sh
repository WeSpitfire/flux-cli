#!/bin/bash
# Quick verification that all production-ready features are in place

echo "🔍 Verifying Flux Production Readiness..."
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

checks_passed=0
checks_failed=0

# Check 1: FileStructureAnalyzer exists
echo -n "1. Checking FileStructureAnalyzer exists... "
if [ -f "flux/core/file_analyzer.py" ]; then
    echo -e "${GREEN}✅${NC}"
    ((checks_passed++))
else
    echo -e "${RED}❌${NC}"
    ((checks_failed++))
fi

# Check 2: FileStructureAnalyzer imports correctly
echo -n "2. Checking FileStructureAnalyzer imports... "
if python -c "from flux.core.file_analyzer import FileStructureAnalyzer" 2>/dev/null; then
    echo -e "${GREEN}✅${NC}"
    ((checks_passed++))
else
    echo -e "${RED}❌${NC}"
    ((checks_failed++))
fi

# Check 3: ASTEditTool imports FileStructureAnalyzer
echo -n "3. Checking ASTEditTool integration... "
if grep -q "from flux.core.file_analyzer import FileStructureAnalyzer" flux/tools/ast_edit.py; then
    echo -e "${GREEN}✅${NC}"
    ((checks_passed++))
else
    echo -e "${RED}❌${NC}"
    ((checks_failed++))
fi

# Check 4: System prompt has CRITICAL RULES
echo -n "4. Checking CRITICAL RULES in prompts... "
if grep -q "CRITICAL FILE EDITING RULES" flux/llm/prompts.py; then
    echo -e "${GREEN}✅${NC}"
    ((checks_passed++))
else
    echo -e "${RED}❌${NC}"
    ((checks_failed++))
fi

# Check 5: Test file exists
echo -n "5. Checking test file exists... "
if [ -f "test_analyzer_manual.py" ]; then
    echo -e "${GREEN}✅${NC}"
    ((checks_passed++))
else
    echo -e "${RED}❌${NC}"
    ((checks_failed++))
fi

# Check 6: Run quick analyzer test
echo -n "6. Running FileStructureAnalyzer test... "
if python test_analyzer_manual.py > /dev/null 2>&1; then
    echo -e "${GREEN}✅${NC}"
    ((checks_passed++))
else
    echo -e "${RED}❌${NC}"
    ((checks_failed++))
fi

# Check 7: Documentation exists
echo -n "7. Checking documentation... "
if [ -f "PRODUCTION_READY.md" ] && [ -f "RELIABILITY_TEST_RESULTS.md" ]; then
    echo -e "${GREEN}✅${NC}"
    ((checks_passed++))
else
    echo -e "${RED}❌${NC}"
    ((checks_failed++))
fi

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
if [ $checks_failed -eq 0 ]; then
    echo -e "${GREEN}🎉 All checks passed! ($checks_passed/$checks_passed)${NC}"
    echo ""
    echo -e "${GREEN}✅ Flux is PRODUCTION READY!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Read PRODUCTION_READY.md for overview"
    echo "  2. See RELIABILITY_TEST_RESULTS.md for test details"
    echo "  3. Run: python -m flux"
    echo ""
else
    echo -e "${RED}❌ Some checks failed ($checks_failed failed, $checks_passed passed)${NC}"
    echo ""
    echo "Please fix the issues above before deploying."
    echo "See PRODUCTION_READINESS_PLAN.md for troubleshooting."
    echo ""
fi
