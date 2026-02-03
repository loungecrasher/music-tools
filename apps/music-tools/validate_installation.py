#!/usr/bin/env python3
"""
Quick validation script to verify Music Tools consolidation installation.
"""

import sys
from pathlib import Path


def check_file(filepath, description):
    """Check if file exists and is readable."""
    if Path(filepath).exists():
        size = Path(filepath).stat().st_size
        print(f"✅ {description}: {filepath} ({size:,} bytes)")
        return True
    else:
        print(f"❌ {description}: NOT FOUND - {filepath}")
        return False


def test_import(module_path, module_name):
    """Test if a module can be imported."""
    try:
        sys.path.insert(0, str(Path(module_path).parent))
        __import__(module_name)
        print(f"✅ Import {module_name}: SUCCESS")
        return True
    except Exception as e:
        print(f"❌ Import {module_name}: FAILED - {e}")
        return False


print("🧪 MUSIC TOOLS CONSOLIDATION - INSTALLATION VALIDATION")
print("=" * 70)

# Get base directory
base_dir = Path.cwd()
apps_dir = base_dir / "apps" / "music-tools"

print(f"\n📁 Base Directory: {base_dir}")
print(f"📁 Apps Directory: {apps_dir}")
print()

# Check core modules
print("1️⃣  CORE MODULES")
print("-" * 70)
modules_dir = apps_dir / "src" / "library"
check_file(modules_dir / "quality_analyzer.py", "quality_analyzer")
check_file(modules_dir / "safe_delete.py", "safe_delete")
check_file(modules_dir / "quality_models.py", "quality_models")
check_file(modules_dir / "smart_cleanup.py", "smart_cleanup")
print()

# Check menu integration
print("2️⃣  MENU INTEGRATION")
print("-" * 70)
menu_file = apps_dir / "menu.py"
if check_file(menu_file, "menu.py"):
    with open(menu_file) as f:
        content = f.read()
        if "run_smart_cleanup_menu" in content:
            print("   ✅ run_smart_cleanup_menu() function found")
        if "display_enhanced_welcome" in content:
            print("   ✅ display_enhanced_welcome() function found")
print()

# Check CLI commands
print("3️⃣  CLI COMMANDS")
print("-" * 70)
cli_file = apps_dir / "music_tools_cli" / "commands" / "library.py"
if check_file(cli_file, "library.py (CLI)"):
    with open(cli_file) as f:
        content = f.read()
        for cmd in ['scan', 'deduplicate', 'upgrades']:
            if f'@library_app.command("{cmd}")' in content:
                print(f"   ✅ Command '{cmd}' found")
print()

# Check Streamlit app
print("4️⃣  STREAMLIT WEB UI")
print("-" * 70)
check_file(apps_dir / "streamlit_app.py", "streamlit_app.py")
check_file(apps_dir / "run_streamlit.sh", "run_streamlit.sh")
check_file(apps_dir / "STREAMLIT_UI_README.md", "STREAMLIT_UI_README.md")
print()

# Check tests
print("5️⃣  TEST SUITE")
print("-" * 70)
tests_dir = apps_dir / "tests" / "library"
check_file(tests_dir / "conftest.py", "conftest.py")
check_file(tests_dir / "test_quality_analyzer.py", "test_quality_analyzer.py")
check_file(tests_dir / "test_safe_delete.py", "test_safe_delete.py")
check_file(tests_dir / "test_quality_models.py", "test_quality_models.py")
print()

# Check validation scripts
print("6️⃣  VALIDATION SCRIPTS")
print("-" * 70)
scripts_dir = base_dir / "scripts"
check_file(scripts_dir / "validate_consolidation.py", "validate_consolidation.py")
check_file(scripts_dir / "test_e2e_workflow.py", "test_e2e_workflow.py")
check_file(scripts_dir / "quick_check.sh", "quick_check.sh")
print()

# Check documentation
print("7️⃣  DOCUMENTATION")
print("-" * 70)
docs_dir = base_dir / "docs"
check_file(docs_dir / "guides" / "user" / "smart-cleanup.md", "User Guide")
check_file(docs_dir / "guides" / "developer" / "quality-analysis-integration.md", "Developer Guide")
check_file(base_dir / "CHANGELOG_CONSOLIDATION.md", "Consolidation Changelog")
print()

print("=" * 70)
print("✅ Validation complete! Check results above.")
print()
print("To launch the app, run:")
print(f"  cd {apps_dir}")
print("  python3 menu.py")
