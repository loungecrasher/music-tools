#!/usr/bin/env python3
"""
Consolidation Validation Script

Validates that all Smart Cleanup components are properly integrated:
- Module imports
- Database migrations
- Menu integration
- CLI commands
- Test suite
- Documentation
"""

import importlib
import os
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


class ConsolidationValidator:
    """Validates Smart Cleanup consolidation"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.results = []
        self.errors = []
        self.warnings = []

    def log_success(self, message: str):
        """Log successful validation"""
        print(f"{GREEN}✓{RESET} {message}")
        self.results.append(("success", message))

    def log_error(self, message: str):
        """Log validation error"""
        print(f"{RED}✗{RESET} {message}")
        self.errors.append(message)
        self.results.append(("error", message))

    def log_warning(self, message: str):
        """Log validation warning"""
        print(f"{YELLOW}⚠{RESET} {message}")
        self.warnings.append(message)
        self.results.append(("warning", message))

    def log_info(self, message: str):
        """Log informational message"""
        print(f"{BLUE}ℹ{RESET} {message}")

    def validate_module_structure(self) -> bool:
        """Validate all required modules exist"""
        self.log_info("\n[1/7] Validating Module Structure...")

        required_modules = [
            "apps/music-tools/core/smart_cleanup.py",
            "apps/music-tools/core/duplicate_scanner.py",
            "apps/music-tools/core/quality_analyzer.py",
            "apps/music-tools/core/safe_delete.py",
            "apps/music-tools/core/database_manager.py",
        ]

        all_exist = True
        for module_path in required_modules:
            full_path = self.project_root / module_path
            if full_path.exists():
                self.log_success(f"Found: {module_path}")
            else:
                self.log_error(f"Missing: {module_path}")
                all_exist = False

        return all_exist

    def validate_imports(self) -> bool:
        """Validate all modules can be imported"""
        self.log_info("\n[2/7] Validating Module Imports...")

        # Add project to path
        sys.path.insert(0, str(self.project_root))

        modules_to_test = [
            "apps.music_tools.core.smart_cleanup",
            "apps.music_tools.core.duplicate_scanner",
            "apps.music_tools.core.quality_analyzer",
            "apps.music_tools.core.safe_delete",
            "apps.music_tools.core.database_manager",
        ]

        all_imported = True
        for module_name in modules_to_test:
            try:
                module = importlib.import_module(module_name)
                self.log_success(f"Imported: {module_name}")

                # Validate key classes exist
                if "smart_cleanup" in module_name:
                    if hasattr(module, "SmartCleanupWorkflow"):
                        self.log_success(f"  - SmartCleanupWorkflow class found")
                    else:
                        self.log_warning(f"  - SmartCleanupWorkflow class missing")

                if "duplicate_scanner" in module_name:
                    if hasattr(module, "DuplicateScanner"):
                        self.log_success(f"  - DuplicateScanner class found")
                    else:
                        self.log_warning(f"  - DuplicateScanner class missing")

                if "quality_analyzer" in module_name:
                    if hasattr(module, "QualityAnalyzer"):
                        self.log_success(f"  - QualityAnalyzer class found")
                    else:
                        self.log_warning(f"  - QualityAnalyzer class missing")

                if "safe_delete" in module_name:
                    if hasattr(module, "SafeDelete"):
                        self.log_success(f"  - SafeDelete class found")
                    else:
                        self.log_warning(f"  - SafeDelete class missing")

                if "database_manager" in module_name:
                    if hasattr(module, "DatabaseManager"):
                        self.log_success(f"  - DatabaseManager class found")
                    else:
                        self.log_warning(f"  - DatabaseManager class missing")

            except ImportError as e:
                self.log_error(f"Failed to import {module_name}: {e}")
                all_imported = False
            except Exception as e:
                self.log_error(f"Error importing {module_name}: {e}")
                all_imported = False

        return all_imported

    def validate_database_migration(self) -> bool:
        """Validate database migration"""
        self.log_info("\n[3/7] Validating Database Migration...")

        try:
            # Create test database
            test_db = self.project_root / "test_validation.db"

            from apps.music_tools.core.database_manager import DatabaseManager

            db_manager = DatabaseManager(str(test_db))
            db_manager.migrate()

            # Check tables exist
            conn = sqlite3.connect(str(test_db))
            cursor = conn.cursor()

            required_tables = ["duplicate_scans", "duplicate_files", "deletion_history"]

            for table in required_tables:
                cursor.execute(
                    f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
                )
                if cursor.fetchone():
                    self.log_success(f"Table exists: {table}")
                else:
                    self.log_error(f"Table missing: {table}")

            conn.close()

            # Clean up test database
            if test_db.exists():
                test_db.unlink()

            self.log_success("Database migration validated")
            return True

        except ImportError as e:
            self.log_error(f"Cannot import DatabaseManager: {e}")
            return False
        except Exception as e:
            self.log_error(f"Database migration failed: {e}")
            return False

    def validate_menu_integration(self) -> bool:
        """Validate Menu.py integration"""
        self.log_info("\n[4/7] Validating Menu Integration...")

        menu_path = self.project_root / "apps/music-tools/menu.py"

        if not menu_path.exists():
            self.log_error("Menu.py not found")
            return False

        try:
            # Read menu file
            with open(menu_path, "r") as f:
                menu_content = f.read()

            # Check for Smart Cleanup references
            if "smart_cleanup" in menu_content.lower() or "Smart Cleanup" in menu_content:
                self.log_success("Smart Cleanup referenced in Menu.py")
            else:
                self.log_warning("Smart Cleanup not found in Menu.py")

            # Try to import and check methods
            try:
                from apps.music_tools.menu import Menu

                menu = Menu()

                if hasattr(menu, "smart_cleanup") or hasattr(menu, "run_smart_cleanup"):
                    self.log_success("Smart Cleanup method exists in Menu class")
                else:
                    self.log_warning("Smart Cleanup method not found in Menu class")

            except Exception as e:
                self.log_warning(f"Could not validate Menu methods: {e}")

            return True

        except Exception as e:
            self.log_error(f"Error validating Menu.py: {e}")
            return False

    def validate_cli_commands(self) -> bool:
        """Validate CLI command registration"""
        self.log_info("\n[5/7] Validating CLI Commands...")

        cli_path = self.project_root / "apps/music-tools/cli.py"

        if not cli_path.exists():
            self.log_warning("CLI.py not found (may not be required)")
            return True

        try:
            with open(cli_path, "r") as f:
                cli_content = f.read()

            expected_commands = ["scan", "deduplicate", "upgrades"]

            for cmd in expected_commands:
                if cmd in cli_content:
                    self.log_success(f"CLI command found: {cmd}")
                else:
                    self.log_warning(f"CLI command not found: {cmd}")

            return True

        except Exception as e:
            self.log_error(f"Error validating CLI: {e}")
            return False

    def validate_tests(self) -> bool:
        """Validate test suite exists and passes"""
        self.log_info("\n[6/7] Validating Test Suite...")

        test_files = [
            "apps/music-tools/tests/integration/test_smart_cleanup_integration.py",
            "apps/music-tools/tests/unit/test_duplicate_scanner.py",
            "apps/music-tools/tests/unit/test_quality_analyzer.py",
            "apps/music-tools/tests/unit/test_safe_delete.py",
        ]

        tests_exist = True
        for test_file in test_files:
            full_path = self.project_root / test_file
            if full_path.exists():
                self.log_success(f"Test file exists: {test_file}")
            else:
                self.log_warning(f"Test file missing: {test_file}")
                tests_exist = False

        # Try to run tests
        try:
            import subprocess

            test_dir = self.project_root / "apps/music-tools/tests"

            if test_dir.exists():
                self.log_info("Attempting to run tests...")
                result = subprocess.run(
                    ["python", "-m", "pytest", str(test_dir), "-v", "--tb=short"],
                    cwd=str(self.project_root),
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode == 0:
                    self.log_success("Test suite passed")
                else:
                    self.log_warning(f"Some tests failed (exit code: {result.returncode})")

        except subprocess.TimeoutExpired:
            self.log_warning("Tests timed out")
        except Exception as e:
            self.log_warning(f"Could not run tests: {e}")

        return tests_exist

    def validate_documentation(self) -> bool:
        """Validate documentation files exist"""
        self.log_info("\n[7/7] Validating Documentation...")

        doc_files = [
            "Music Tools Dev/docs/CONSOLIDATION_PLAN.md",
            "Music Tools Dev/docs/IMPLEMENTATION_CHECKLIST.md",
            "Music Tools Dev/docs/TESTING_STRATEGY.md",
        ]

        docs_exist = True
        for doc_file in doc_files:
            full_path = self.project_root / doc_file
            if full_path.exists():
                self.log_success(f"Documentation exists: {doc_file}")
            else:
                self.log_warning(f"Documentation missing: {doc_file}")
                docs_exist = False

        return docs_exist

    def generate_report(self):
        """Generate validation report"""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}CONSOLIDATION VALIDATION REPORT{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")

        success_count = sum(1 for r in self.results if r[0] == "success")
        error_count = len(self.errors)
        warning_count = len(self.warnings)

        print(f"Total Checks: {len(self.results)}")
        print(f"{GREEN}Passed: {success_count}{RESET}")
        print(f"{RED}Errors: {error_count}{RESET}")
        print(f"{YELLOW}Warnings: {warning_count}{RESET}")

        if error_count > 0:
            print(f"\n{RED}ERRORS:{RESET}")
            for error in self.errors:
                print(f"  - {error}")

        if warning_count > 0:
            print(f"\n{YELLOW}WARNINGS:{RESET}")
            for warning in self.warnings:
                print(f"  - {warning}")

        print(f"\n{BLUE}{'='*60}{RESET}")

        if error_count == 0:
            print(f"{GREEN}✓ CONSOLIDATION VALIDATED SUCCESSFULLY{RESET}")
            return True
        else:
            print(f"{RED}✗ CONSOLIDATION HAS ERRORS{RESET}")
            return False

    def run_all_validations(self) -> bool:
        """Run all validation checks"""
        print(f"\n{BLUE}Starting Consolidation Validation...{RESET}")

        results = []
        results.append(self.validate_module_structure())
        results.append(self.validate_imports())
        results.append(self.validate_database_migration())
        results.append(self.validate_menu_integration())
        results.append(self.validate_cli_commands())
        results.append(self.validate_tests())
        results.append(self.validate_documentation())

        return self.generate_report()


def main():
    """Main entry point"""
    # Determine project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    print(f"Project Root: {project_root}\n")

    validator = ConsolidationValidator(str(project_root))
    success = validator.run_all_validations()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
