#!/bin/bash

# Quick Check Script for Smart Cleanup Consolidation
# Validates Python environment and runs basic smoke tests

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Smart Cleanup Quick Check${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Function to print success
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

# Function to print error
print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Function to print info
print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

# Function to print section header
print_section() {
    echo -e "\n${BLUE}[$1]${NC}"
}

# Track overall status
ERRORS=0
WARNINGS=0

# 1. Check Python version
print_section "1/6: Python Version Check"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    print_success "Python 3 found: $PYTHON_VERSION"

    # Check if version is 3.8+
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 8 ]; then
        print_success "Python version is 3.8+ (meets requirements)"
    else
        print_error "Python version is less than 3.8 (required: 3.8+)"
        ERRORS=$((ERRORS + 1))
    fi
else
    print_error "Python 3 not found"
    ERRORS=$((ERRORS + 1))
    exit 1
fi

# 2. Check project structure
print_section "2/6: Project Structure Check"

REQUIRED_DIRS=(
    "apps/music-tools/core"
    "apps/music-tools/tests"
    "scripts"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$PROJECT_ROOT/$dir" ]; then
        print_success "Directory exists: $dir"
    else
        print_error "Directory missing: $dir"
        ERRORS=$((ERRORS + 1))
    fi
done

# 3. Check core modules
print_section "3/6: Core Module Check"

REQUIRED_MODULES=(
    "apps/music-tools/core/smart_cleanup.py"
    "apps/music-tools/core/duplicate_scanner.py"
    "apps/music-tools/core/quality_analyzer.py"
    "apps/music-tools/core/safe_delete.py"
    "apps/music-tools/core/database_manager.py"
)

for module in "${REQUIRED_MODULES[@]}"; do
    if [ -f "$PROJECT_ROOT/$module" ]; then
        print_success "Module exists: $(basename $module)"
    else
        print_error "Module missing: $(basename $module)"
        ERRORS=$((ERRORS + 1))
    fi
done

# 4. Validate Python imports
print_section "4/6: Import Validation"

cd "$PROJECT_ROOT"

# Test imports
python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')

try:
    from apps.music_tools.core.smart_cleanup import SmartCleanupWorkflow
    print('${GREEN}✓${NC} SmartCleanupWorkflow imported successfully')
except ImportError as e:
    print('${RED}✗${NC} Failed to import SmartCleanupWorkflow:', e)
    sys.exit(1)

try:
    from apps.music_tools.core.duplicate_scanner import DuplicateScanner
    print('${GREEN}✓${NC} DuplicateScanner imported successfully')
except ImportError as e:
    print('${YELLOW}⚠${NC} Failed to import DuplicateScanner:', e)

try:
    from apps.music_tools.core.quality_analyzer import QualityAnalyzer
    print('${GREEN}✓${NC} QualityAnalyzer imported successfully')
except ImportError as e:
    print('${YELLOW}⚠${NC} Failed to import QualityAnalyzer:', e)

try:
    from apps.music_tools.core.safe_delete import SafeDelete
    print('${GREEN}✓${NC} SafeDelete imported successfully')
except ImportError as e:
    print('${YELLOW}⚠${NC} Failed to import SafeDelete:', e)

try:
    from apps.music_tools.core.database_manager import DatabaseManager
    print('${GREEN}✓${NC} DatabaseManager imported successfully')
except ImportError as e:
    print('${YELLOW}⚠${NC} Failed to import DatabaseManager:', e)
" 2>&1

if [ $? -ne 0 ]; then
    print_error "Import validation failed"
    ERRORS=$((ERRORS + 1))
fi

# 5. Check dependencies
print_section "5/6: Dependencies Check"

REQUIRED_PACKAGES=(
    "pytest"
    "mutagen"
)

for package in "${REQUIRED_PACKAGES[@]}"; do
    if python3 -c "import $package" 2>/dev/null; then
        print_success "Package installed: $package"
    else
        print_warning "Package not installed: $package (may be optional)"
        WARNINGS=$((WARNINGS + 1))
    fi
done

# 6. Run basic smoke tests
print_section "6/6: Smoke Tests"

# Test 1: Database initialization
print_info "Testing database initialization..."
python3 -c "
import sys
import tempfile
sys.path.insert(0, '$PROJECT_ROOT')

try:
    from apps.music_tools.core.database_manager import DatabaseManager

    with tempfile.NamedTemporaryFile(suffix='.db', delete=True) as f:
        db = DatabaseManager(f.name)
        db.migrate()

    print('${GREEN}✓${NC} Database initialization test passed')
except Exception as e:
    print('${RED}✗${NC} Database initialization test failed:', e)
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    print_success "Database smoke test passed"
else
    print_error "Database smoke test failed"
    ERRORS=$((ERRORS + 1))
fi

# Test 2: Workflow instantiation
print_info "Testing workflow instantiation..."
python3 -c "
import sys
import tempfile
sys.path.insert(0, '$PROJECT_ROOT')

try:
    from apps.music_tools.core.smart_cleanup import SmartCleanupWorkflow
    from apps.music_tools.core.database_manager import DatabaseManager

    with tempfile.TemporaryDirectory() as tmpdir:
        with tempfile.NamedTemporaryFile(suffix='.db', delete=True) as f:
            db = DatabaseManager(f.name)
            workflow = SmartCleanupWorkflow(tmpdir, db)

    print('${GREEN}✓${NC} Workflow instantiation test passed')
except Exception as e:
    print('${RED}✗${NC} Workflow instantiation test failed:', e)
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    print_success "Workflow smoke test passed"
else
    print_error "Workflow smoke test failed"
    ERRORS=$((ERRORS + 1))
fi

# Generate summary
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}CONSOLIDATION STATUS REPORT${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo "Project Root: $PROJECT_ROOT"
echo "Python Version: $PYTHON_VERSION"
echo ""
echo "Results:"
echo -e "${GREEN}Checks Passed${NC}"
echo -e "${RED}Errors: $ERRORS${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ SMART CLEANUP CONSOLIDATION VALIDATED${NC}"
    echo -e "${GREEN}All critical checks passed!${NC}\n"

    echo "Next Steps:"
    echo "  1. Run full validation: python3 scripts/validate_consolidation.py"
    echo "  2. Run integration tests: pytest apps/music-tools/tests/integration/"
    echo "  3. Run E2E test: python3 scripts/test_e2e_workflow.py"
    echo ""
    exit 0
else
    echo -e "${RED}✗ CONSOLIDATION HAS ERRORS${NC}"
    echo -e "${RED}Please fix errors before proceeding${NC}\n"
    exit 1
fi
