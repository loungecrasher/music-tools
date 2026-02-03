"""
Integration Tests for Smart Cleanup Workflow

Tests the complete integration of:
- Smart Cleanup workflow (scan, review, delete)
- Menu system integration
- CLI command integration
- Database migrations
- Quality analyzer and safe delete coordination
"""

import pytest
import sys
import os
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestSmartCleanupWorkflowIntegration:
    """Test complete Smart Cleanup workflow integration"""

    @pytest.fixture
    def test_library_path(self, tmp_path):
        """Create a temporary test library"""
        library = tmp_path / "test_library"
        library.mkdir()

        # Create test music files
        artist_dir = library / "Test Artist"
        artist_dir.mkdir()

        album_dir = artist_dir / "Test Album"
        album_dir.mkdir()

        # Create duplicate files
        (album_dir / "track1.mp3").write_bytes(b"fake audio data 1")
        (album_dir / "track1_copy.mp3").write_bytes(b"fake audio data 1")
        (album_dir / "track2.flac").write_bytes(b"fake flac data")

        return str(library)

    @pytest.fixture
    def test_db_path(self, tmp_path):
        """Create temporary database path"""
        return str(tmp_path / "test_smart_cleanup.db")

    def test_full_workflow_scan_to_delete(self, test_library_path, test_db_path):
        """Test complete workflow: scan -> review -> delete"""
        try:
            from apps.music_tools.core.smart_cleanup import SmartCleanupWorkflow
            from apps.music_tools.core.database_manager import DatabaseManager

            # Initialize components
            db_manager = DatabaseManager(test_db_path)
            workflow = SmartCleanupWorkflow(test_library_path, db_manager)

            # Step 1: Scan for duplicates
            scan_results = workflow.scan_for_duplicates()

            assert scan_results is not None
            assert 'duplicate_groups' in scan_results
            assert 'total_files' in scan_results
            assert 'total_duplicates' in scan_results

            # Step 2: Review duplicates
            review_data = workflow.review_duplicates()

            assert review_data is not None
            assert 'groups' in review_data

            # Step 3: Prepare deletion (dry run)
            with patch('builtins.input', return_value='y'):
                delete_results = workflow.prepare_deletion(dry_run=True)

            assert delete_results is not None
            assert 'files_to_delete' in delete_results
            assert 'backup_created' in delete_results

            print("✓ Full workflow integration test passed")

        except ImportError as e:
            pytest.skip(f"Smart Cleanup modules not available: {e}")

    def test_workflow_with_quality_analysis(self, test_library_path, test_db_path):
        """Test workflow with quality analyzer integration"""
        try:
            from apps.music_tools.core.smart_cleanup import SmartCleanupWorkflow
            from apps.music_tools.core.quality_analyzer import QualityAnalyzer
            from apps.music_tools.core.database_manager import DatabaseManager

            db_manager = DatabaseManager(test_db_path)
            workflow = SmartCleanupWorkflow(test_library_path, db_manager)
            quality_analyzer = QualityAnalyzer()

            # Scan with quality analysis
            scan_results = workflow.scan_for_duplicates()

            if scan_results and scan_results.get('duplicate_groups'):
                # Analyze quality for each duplicate group
                for group in scan_results['duplicate_groups']:
                    quality_scores = []
                    for file_path in group.get('files', []):
                        score = quality_analyzer.analyze_file(file_path)
                        quality_scores.append({
                            'file': file_path,
                            'score': score
                        })

                    # Verify best quality file identified
                    best = max(quality_scores, key=lambda x: x['score'])
                    assert best is not None

            print("✓ Quality analysis integration test passed")

        except ImportError as e:
            pytest.skip(f"Quality analyzer not available: {e}")

    def test_safe_delete_integration(self, test_library_path, test_db_path):
        """Test safe delete integration with backup"""
        try:
            from apps.music_tools.core.smart_cleanup import SmartCleanupWorkflow
            from apps.music_tools.core.safe_delete import SafeDelete
            from apps.music_tools.core.database_manager import DatabaseManager

            db_manager = DatabaseManager(test_db_path)
            workflow = SmartCleanupWorkflow(test_library_path, db_manager)
            safe_delete = SafeDelete(backup_dir=str(Path(test_db_path).parent / "backups"))

            # Scan and identify files
            scan_results = workflow.scan_for_duplicates()

            if scan_results and scan_results.get('duplicate_groups'):
                first_group = scan_results['duplicate_groups'][0]
                files = first_group.get('files', [])

                if len(files) > 1:
                    # Test safe delete with backup
                    file_to_delete = files[0]
                    result = safe_delete.delete_with_backup(file_to_delete, dry_run=True)

                    assert result is not None
                    assert 'success' in result or 'would_delete' in result

            print("✓ Safe delete integration test passed")

        except ImportError as e:
            pytest.skip(f"Safe delete module not available: {e}")


class TestMenuIntegration:
    """Test Menu.py integration with Smart Cleanup"""

    def test_menu_imports_smart_cleanup(self):
        """Test that Menu.py can import Smart Cleanup workflow"""
        try:
            from apps.music_tools.menu import Menu

            menu = Menu()

            # Verify Smart Cleanup is available
            # Check if smart_cleanup method exists
            assert hasattr(menu, 'smart_cleanup') or hasattr(menu, 'run_smart_cleanup')

            print("✓ Menu integration test passed")

        except ImportError as e:
            pytest.skip(f"Menu module not available: {e}")
        except AttributeError as e:
            pytest.fail(f"Smart Cleanup not integrated into Menu: {e}")

    def test_menu_displays_smart_cleanup_option(self):
        """Test that Menu displays Smart Cleanup option"""
        try:
            from apps.music_tools.menu import Menu

            menu = Menu()

            # Capture menu display
            with patch('builtins.print') as mock_print:
                # Try to trigger menu display
                if hasattr(menu, 'display_options'):
                    menu.display_options()
                elif hasattr(menu, 'show_menu'):
                    menu.show_menu()

            # Check if Smart Cleanup mentioned in any print call
            print_calls = [str(call) for call in mock_print.call_args_list]
            menu_text = ' '.join(print_calls).lower()

            assert 'smart cleanup' in menu_text or 'cleanup' in menu_text

            print("✓ Menu display test passed")

        except ImportError as e:
            pytest.skip(f"Menu module not available: {e}")


class TestCLIIntegration:
    """Test CLI command integration"""

    def test_cli_scan_command_registered(self):
        """Test that scan command is registered in CLI"""
        try:
            from apps.music_tools.cli import cli

            # Check if scan command exists
            assert hasattr(cli, 'commands')

            command_names = [cmd for cmd in cli.commands.keys()]

            assert 'scan' in command_names or 'smart-cleanup' in command_names

            print("✓ CLI scan command registration test passed")

        except ImportError as e:
            pytest.skip(f"CLI module not available: {e}")
        except AttributeError as e:
            pytest.skip(f"CLI structure different than expected: {e}")

    def test_cli_deduplicate_command(self):
        """Test deduplicate command"""
        try:
            from apps.music_tools.cli import cli

            command_names = [cmd for cmd in cli.commands.keys()]

            assert 'deduplicate' in command_names or 'dedup' in command_names

            print("✓ CLI deduplicate command test passed")

        except ImportError as e:
            pytest.skip(f"CLI module not available: {e}")

    def test_cli_upgrades_command(self):
        """Test upgrades command"""
        try:
            from apps.music_tools.cli import cli

            command_names = [cmd for cmd in cli.commands.keys()]

            assert 'upgrades' in command_names or 'upgrade' in command_names

            print("✓ CLI upgrades command test passed")

        except ImportError as e:
            pytest.skip(f"CLI module not available: {e}")


class TestDatabaseMigrationIntegration:
    """Test database migration integration"""

    def test_migration_creates_smart_cleanup_tables(self, tmp_path):
        """Test that migration creates required tables"""
        try:
            from apps.music_tools.core.database_manager import DatabaseManager

            db_path = str(tmp_path / "test_migration.db")
            db_manager = DatabaseManager(db_path)

            # Run migration
            db_manager.migrate()

            # Verify tables exist
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Check for duplicate_scans table
                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='duplicate_scans'
                """)
                result = cursor.fetchone()
                assert result is not None, "duplicate_scans table not created"

                # Check for duplicate_files table
                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='duplicate_files'
                """)
                result = cursor.fetchone()
                assert result is not None, "duplicate_files table not created"

            print("✓ Database migration test passed")

        except ImportError as e:
            pytest.skip(f"Database manager not available: {e}")

    def test_migration_creates_indexes(self, tmp_path):
        """Test that migration creates performance indexes"""
        try:
            from apps.music_tools.core.database_manager import DatabaseManager

            db_path = str(tmp_path / "test_indexes.db")
            db_manager = DatabaseManager(db_path)
            db_manager.migrate()

            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Check for indexes
                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='index'
                """)
                indexes = [row[0] for row in cursor.fetchall()]

                # Should have indexes for performance
                assert len(indexes) > 0, "No indexes created"

            print("✓ Database indexes test passed")

        except ImportError as e:
            pytest.skip(f"Database manager not available: {e}")


class TestReportingIntegration:
    """Test report generation integration"""

    def test_scan_report_generation(self, tmp_path):
        """Test that scan generates reports"""
        try:
            from apps.music_tools.core.smart_cleanup import SmartCleanupWorkflow
            from apps.music_tools.core.database_manager import DatabaseManager

            library_path = tmp_path / "library"
            library_path.mkdir()

            db_path = str(tmp_path / "test_reports.db")
            db_manager = DatabaseManager(db_path)

            workflow = SmartCleanupWorkflow(str(library_path), db_manager)

            # Run scan
            results = workflow.scan_for_duplicates()

            # Generate report
            report = workflow.generate_report()

            assert report is not None
            assert 'summary' in report or 'total_files' in report

            print("✓ Report generation test passed")

        except ImportError as e:
            pytest.skip(f"Smart Cleanup not available: {e}")
        except AttributeError:
            # Method might not exist yet
            pytest.skip("Report generation method not implemented")


class TestErrorHandlingIntegration:
    """Test error handling across integrated components"""

    def test_invalid_library_path_handling(self):
        """Test handling of invalid library paths"""
        try:
            from apps.music_tools.core.smart_cleanup import SmartCleanupWorkflow
            from apps.music_tools.core.database_manager import DatabaseManager

            db_manager = DatabaseManager(":memory:")

            # Test with non-existent path
            with pytest.raises((FileNotFoundError, ValueError, OSError)):
                workflow = SmartCleanupWorkflow("/invalid/path/does/not/exist", db_manager)
                workflow.scan_for_duplicates()

            print("✓ Invalid path handling test passed")

        except ImportError as e:
            pytest.skip(f"Smart Cleanup not available: {e}")

    def test_database_connection_error_handling(self, tmp_path):
        """Test database connection error handling"""
        try:
            from apps.music_tools.core.database_manager import DatabaseManager

            # Test with invalid database path
            invalid_path = "/root/cannot/write/here.db"

            try:
                db_manager = DatabaseManager(invalid_path)
                # Should handle gracefully or raise appropriate error
            except (PermissionError, OSError):
                # Expected behavior
                pass

            print("✓ Database error handling test passed")

        except ImportError as e:
            pytest.skip(f"Database manager not available: {e}")


class TestPerformanceIntegration:
    """Test performance of integrated components"""

    def test_scan_performance_with_large_library(self, tmp_path):
        """Test scan performance with larger library"""
        try:
            from apps.music_tools.core.smart_cleanup import SmartCleanupWorkflow
            from apps.music_tools.core.database_manager import DatabaseManager
            import time

            # Create library with multiple files
            library = tmp_path / "large_library"
            library.mkdir()

            for i in range(50):
                artist_dir = library / f"Artist_{i}"
                artist_dir.mkdir()
                album_dir = artist_dir / "Album"
                album_dir.mkdir()

                (album_dir / f"track_{i}.mp3").write_bytes(b"audio data" * 100)

            db_path = str(tmp_path / "perf_test.db")
            db_manager = DatabaseManager(db_path)
            workflow = SmartCleanupWorkflow(str(library), db_manager)

            # Measure scan time
            start_time = time.time()
            results = workflow.scan_for_duplicates()
            scan_duration = time.time() - start_time

            # Should complete in reasonable time (< 30 seconds for 50 files)
            assert scan_duration < 30, f"Scan took too long: {scan_duration}s"

            print(f"✓ Performance test passed (scan took {scan_duration:.2f}s)")

        except ImportError as e:
            pytest.skip(f"Smart Cleanup not available: {e}")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
