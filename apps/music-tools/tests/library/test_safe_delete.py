"""
Comprehensive test suite for safe_delete module.

Tests SafeDeletionPlan, DeletionValidator, 7-point safety checklist,
dry-run mode, backup functionality, and JSON export/import.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import sys

# Add project to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.library.safe_delete import (
    SafeDeletionPlan,
    DeletionGroup,
    DeletionValidator,
    ValidationResult,
    ValidationLevel,
    DeletionStats,
    create_deletion_plan,
    validate_deletion,
)


# ==================== DeletionGroup Tests ====================

class TestDeletionGroup:
    """Test DeletionGroup dataclass and validation."""

    def test_deletion_group_creation(self):
        """Test basic DeletionGroup creation."""
        group = DeletionGroup(
            keep_file='/music/keep.flac',
            delete_files=['/music/delete1.mp3', '/music/delete2.mp3'],
            reason='Keep highest quality FLAC'
        )

        assert group.keep_file == '/music/keep.flac'
        assert len(group.delete_files) == 2
        assert group.reason == 'Keep highest quality FLAC'
        assert group.group_id is not None  # Auto-generated

    def test_deletion_group_auto_generates_id(self):
        """Test that group_id is auto-generated if not provided."""
        group1 = DeletionGroup(
            keep_file='/music/song.flac',
            delete_files=['/music/song.mp3'],
            reason='test'
        )

        group2 = DeletionGroup(
            keep_file='/music/song.flac',
            delete_files=['/music/song.mp3'],
            reason='test'
        )

        # IDs should be different (timestamp-based)
        assert group1.group_id != group2.group_id

    def test_deletion_group_custom_id(self):
        """Test DeletionGroup with custom ID."""
        group = DeletionGroup(
            keep_file='/music/keep.flac',
            delete_files=['/music/delete.mp3'],
            reason='test',
            group_id='custom-id-123'
        )

        assert group.group_id == 'custom-id-123'

    def test_deletion_group_is_valid_no_errors(self):
        """Test is_valid returns True when no errors."""
        group = DeletionGroup(
            keep_file='/music/keep.flac',
            delete_files=['/music/delete.mp3'],
            reason='test'
        )

        group.validation_results = [
            ValidationResult(
                level=ValidationLevel.INFO,
                checkpoint='Test',
                message='All good'
            )
        ]

        assert group.is_valid() is True

    def test_deletion_group_is_valid_with_errors(self):
        """Test is_valid returns False when errors present."""
        group = DeletionGroup(
            keep_file='/music/keep.flac',
            delete_files=['/music/delete.mp3'],
            reason='test'
        )

        group.validation_results = [
            ValidationResult(
                level=ValidationLevel.ERROR,
                checkpoint='Test',
                message='Error occurred'
            )
        ]

        assert group.is_valid() is False

    def test_deletion_group_get_errors(self):
        """Test getting only error-level results."""
        group = DeletionGroup(
            keep_file='/music/keep.flac',
            delete_files=['/music/delete.mp3'],
            reason='test'
        )

        group.validation_results = [
            ValidationResult(level=ValidationLevel.ERROR, checkpoint='1', message='Error 1'),
            ValidationResult(level=ValidationLevel.WARNING, checkpoint='2', message='Warning'),
            ValidationResult(level=ValidationLevel.ERROR, checkpoint='3', message='Error 2'),
            ValidationResult(level=ValidationLevel.INFO, checkpoint='4', message='Info'),
        ]

        errors = group.get_errors()

        assert len(errors) == 2
        assert all(r.level == ValidationLevel.ERROR for r in errors)

    def test_deletion_group_get_warnings(self):
        """Test getting only warning-level results."""
        group = DeletionGroup(
            keep_file='/music/keep.flac',
            delete_files=['/music/delete.mp3'],
            reason='test'
        )

        group.validation_results = [
            ValidationResult(level=ValidationLevel.WARNING, checkpoint='1', message='Warning 1'),
            ValidationResult(level=ValidationLevel.ERROR, checkpoint='2', message='Error'),
            ValidationResult(level=ValidationLevel.WARNING, checkpoint='3', message='Warning 2'),
        ]

        warnings = group.get_warnings()

        assert len(warnings) == 2
        assert all(r.level == ValidationLevel.WARNING for r in warnings)

    def test_deletion_group_to_dict(self):
        """Test DeletionGroup serialization to dictionary."""
        group = DeletionGroup(
            keep_file='/music/keep.flac',
            delete_files=['/music/delete.mp3'],
            reason='Quality upgrade',
            group_id='test-123'
        )

        group.validation_results = [
            ValidationResult(
                level=ValidationLevel.INFO,
                checkpoint='Test',
                message='Test message',
                details={'key': 'value'}
            )
        ]

        data = group.to_dict()

        assert data['group_id'] == 'test-123'
        assert data['keep_file'] == '/music/keep.flac'
        assert len(data['delete_files']) == 1
        assert data['reason'] == 'Quality upgrade'
        assert len(data['validation_results']) == 1
        assert data['validation_results'][0]['level'] == 'info'


# ==================== DeletionValidator Tests ====================

class TestDeletionValidator:
    """Test 7-point safety checklist validation."""

    def test_validator_creation(self):
        """Test DeletionValidator instantiation."""
        validator = DeletionValidator()
        assert validator is not None

    def test_checkpoint_1_keep_file_exists(self, tmp_path):
        """Checkpoint 1: Keep file must exist."""
        validator = DeletionValidator()

        # Create a real file
        keep_file = tmp_path / 'keep.flac'
        keep_file.write_text('fake audio data')

        group = DeletionGroup(
            keep_file=str(keep_file),
            delete_files=[str(tmp_path / 'delete.mp3')],
            reason='test'
        )

        result = validator._validate_keep_file_exists(group)

        assert result.level == ValidationLevel.INFO
        assert 'validated' in result.message.lower()

    def test_checkpoint_1_keep_file_not_exists(self):
        """Checkpoint 1: Error when keep file does not exist."""
        validator = DeletionValidator()

        group = DeletionGroup(
            keep_file='/nonexistent/keep.flac',
            delete_files=['/music/delete.mp3'],
            reason='test'
        )

        result = validator._validate_keep_file_exists(group)

        assert result.level == ValidationLevel.ERROR
        assert 'does not exist' in result.message.lower()

    def test_checkpoint_1_keep_file_empty(self):
        """Checkpoint 1: Error when keep file path is empty."""
        validator = DeletionValidator()

        group = DeletionGroup(
            keep_file='',
            delete_files=['/music/delete.mp3'],
            reason='test'
        )

        result = validator._validate_keep_file_exists(group)

        assert result.level == ValidationLevel.ERROR
        assert 'empty' in result.message.lower()

    def test_checkpoint_2_has_files_to_delete(self):
        """Checkpoint 2: Must have files to delete."""
        validator = DeletionValidator()

        group = DeletionGroup(
            keep_file='/music/keep.flac',
            delete_files=['/music/delete.mp3'],
            reason='test'
        )

        result = validator._validate_has_files_to_delete(group)

        assert result.level == ValidationLevel.INFO
        assert '1 file' in result.message

    def test_checkpoint_2_no_files_to_delete(self):
        """Checkpoint 2: Error when no files to delete."""
        validator = DeletionValidator()

        group = DeletionGroup(
            keep_file='/music/keep.flac',
            delete_files=[],  # Empty
            reason='test'
        )

        result = validator._validate_has_files_to_delete(group)

        assert result.level == ValidationLevel.ERROR
        assert 'no files' in result.message.lower()

    def test_checkpoint_3_quality_check_no_issues(self):
        """Checkpoint 3: No warning when deleting lower quality."""
        validator = DeletionValidator()

        group = DeletionGroup(
            keep_file='/music/keep_320.mp3',  # Higher bitrate in name
            delete_files=['/music/delete_128.mp3'],  # Lower bitrate
            reason='test'
        )

        results = validator._validate_no_higher_quality_deletion(group)

        # Should have at least one INFO result
        assert any(r.level == ValidationLevel.INFO for r in results)

    def test_checkpoint_4_files_exist(self, tmp_path):
        """Checkpoint 4: Verify delete files exist."""
        validator = DeletionValidator()

        # Create files
        delete1 = tmp_path / 'delete1.mp3'
        delete2 = tmp_path / 'delete2.mp3'
        delete1.write_text('data')
        delete2.write_text('data')

        group = DeletionGroup(
            keep_file=str(tmp_path / 'keep.flac'),
            delete_files=[str(delete1), str(delete2)],
            reason='test'
        )

        results = validator._validate_files_exist(group)

        # Should have INFO result confirming all files verified
        assert any(r.level == ValidationLevel.INFO and 'verified' in r.message.lower() for r in results)

    def test_checkpoint_4_files_not_exist(self):
        """Checkpoint 4: Error when delete files do not exist."""
        validator = DeletionValidator()

        group = DeletionGroup(
            keep_file='/music/keep.flac',
            delete_files=['/nonexistent/file1.mp3', '/nonexistent/file2.mp3'],
            reason='test'
        )

        results = validator._validate_files_exist(group)

        # Should have ERROR results for missing files
        errors = [r for r in results if r.level == ValidationLevel.ERROR]
        assert len(errors) == 2

    def test_checkpoint_5_not_deleting_all_files(self, tmp_path):
        """Checkpoint 5: Ensure keep file is valid."""
        validator = DeletionValidator()

        keep_file = tmp_path / 'keep.flac'
        keep_file.write_text('data')

        group = DeletionGroup(
            keep_file=str(keep_file),
            delete_files=[str(tmp_path / 'delete.mp3')],
            reason='test'
        )

        result = validator._validate_not_deleting_all_files(group)

        assert result.level == ValidationLevel.INFO
        assert 'preserved' in result.message.lower()

    def test_checkpoint_5_keep_file_in_delete_list(self, tmp_path):
        """Checkpoint 5: Error when keep file is also marked for deletion."""
        validator = DeletionValidator()

        same_file = tmp_path / 'file.mp3'
        same_file.write_text('data')

        group = DeletionGroup(
            keep_file=str(same_file),
            delete_files=[str(same_file)],  # Same file!
            reason='test'
        )

        result = validator._validate_not_deleting_all_files(group)

        assert result.level == ValidationLevel.ERROR
        assert 'also marked for deletion' in result.message.lower()

    def test_checkpoint_6_file_permissions(self, tmp_path):
        """Checkpoint 6: Check file permissions."""
        validator = DeletionValidator()

        delete_file = tmp_path / 'delete.mp3'
        delete_file.write_text('data')

        group = DeletionGroup(
            keep_file=str(tmp_path / 'keep.flac'),
            delete_files=[str(delete_file)],
            reason='test'
        )

        results = validator._validate_file_permissions(group)

        # Should have INFO result confirming permissions OK
        assert any(r.level == ValidationLevel.INFO and 'permissions' in r.message.lower() for r in results)

    def test_checkpoint_7_backup_space_sufficient(self, tmp_path):
        """Checkpoint 7: Check sufficient disk space for backup."""
        validator = DeletionValidator()

        delete_file = tmp_path / 'delete.mp3'
        delete_file.write_bytes(b'data' * 1000)  # Small file

        group = DeletionGroup(
            keep_file=str(tmp_path / 'keep.flac'),
            delete_files=[str(delete_file)],
            reason='test'
        )

        result = validator._validate_backup_space(group)

        # Should be INFO since we have plenty of space
        assert result.level == ValidationLevel.INFO
        assert 'sufficient' in result.message.lower()

    def test_validate_group_all_checkpoints(self, tmp_path):
        """Test running all validation checkpoints."""
        validator = DeletionValidator()

        # Create files
        keep_file = tmp_path / 'keep.flac'
        delete_file = tmp_path / 'delete.mp3'
        keep_file.write_text('keep data')
        delete_file.write_text('delete data')

        group = DeletionGroup(
            keep_file=str(keep_file),
            delete_files=[str(delete_file)],
            reason='test'
        )

        results = validator.validate_group(group, check_backup_space=True)

        # Should have results from all 7 checkpoints
        checkpoints = set(r.checkpoint for r in results)
        assert len(checkpoints) >= 7

        # Should have no blocking errors
        assert not any(r.is_blocking() for r in results)


# ==================== SafeDeletionPlan Tests ====================

class TestSafeDeletionPlan:
    """Test SafeDeletionPlan functionality."""

    def test_deletion_plan_creation(self):
        """Test SafeDeletionPlan instantiation."""
        plan = SafeDeletionPlan()
        assert plan is not None
        assert len(plan.groups) == 0

    def test_deletion_plan_with_backup_dir(self, tmp_path):
        """Test SafeDeletionPlan with backup directory."""
        backup_dir = tmp_path / 'backup'
        plan = SafeDeletionPlan(backup_dir=str(backup_dir))

        assert plan.backup_dir == str(backup_dir)

    def test_add_group(self, tmp_path):
        """Test adding deletion groups to plan."""
        plan = SafeDeletionPlan()

        keep_file = tmp_path / 'keep.flac'
        delete_file = tmp_path / 'delete.mp3'
        keep_file.write_text('data')
        delete_file.write_text('data')

        group = plan.add_group(
            keep_file=str(keep_file),
            delete_files=[str(delete_file)],
            reason='Quality upgrade'
        )

        assert len(plan.groups) == 1
        assert group.keep_file == str(keep_file)
        assert group.reason == 'Quality upgrade'

    def test_validate_plan_success(self, tmp_path):
        """Test validation of valid deletion plan."""
        plan = SafeDeletionPlan()

        keep_file = tmp_path / 'keep.flac'
        delete_file = tmp_path / 'delete.mp3'
        keep_file.write_text('data')
        delete_file.write_text('data')

        plan.add_group(
            keep_file=str(keep_file),
            delete_files=[str(delete_file)],
            reason='test'
        )

        is_valid, errors = plan.validate(check_backup_space=False)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_plan_with_errors(self):
        """Test validation of invalid deletion plan."""
        plan = SafeDeletionPlan()

        # Add group with non-existent files
        plan.add_group(
            keep_file='/nonexistent/keep.flac',
            delete_files=['/nonexistent/delete.mp3'],
            reason='test'
        )

        is_valid, errors = plan.validate(check_backup_space=False)

        assert is_valid is False
        assert len(errors) > 0

    def test_execute_dry_run(self, tmp_path):
        """Test dry-run execution (no actual deletion)."""
        plan = SafeDeletionPlan()

        keep_file = tmp_path / 'keep.flac'
        delete_file = tmp_path / 'delete.mp3'
        keep_file.write_text('keep data')
        delete_file.write_text('delete data')

        plan.add_group(
            keep_file=str(keep_file),
            delete_files=[str(delete_file)],
            reason='test'
        )

        # Validate first
        is_valid, _ = plan.validate(check_backup_space=False)
        assert is_valid

        # Execute in dry-run mode
        stats = plan.execute(dry_run=True, create_backup=False)

        # File should still exist
        assert delete_file.exists()
        assert stats.files_deleted == 1  # Counted but not actually deleted
        assert stats.successful_deletions == 1

    def test_execute_actual_deletion(self, tmp_path):
        """Test actual file deletion."""
        plan = SafeDeletionPlan()

        keep_file = tmp_path / 'keep.flac'
        delete_file = tmp_path / 'delete.mp3'
        keep_file.write_text('keep data')
        delete_file.write_text('delete data')

        plan.add_group(
            keep_file=str(keep_file),
            delete_files=[str(delete_file)],
            reason='test'
        )

        # Validate first
        is_valid, _ = plan.validate(check_backup_space=False)
        assert is_valid

        # Execute actual deletion
        stats = plan.execute(dry_run=False, create_backup=False)

        # File should be deleted
        assert not delete_file.exists()
        assert keep_file.exists()
        assert stats.files_deleted == 1
        assert stats.successful_deletions == 1

    def test_execute_with_backup(self, tmp_path):
        """Test deletion with backup creation."""
        backup_dir = tmp_path / 'backup'
        plan = SafeDeletionPlan(backup_dir=str(backup_dir))

        keep_file = tmp_path / 'keep.flac'
        delete_file = tmp_path / 'delete.mp3'
        keep_file.write_text('keep data')
        delete_file.write_bytes(b'delete data' * 100)

        plan.add_group(
            keep_file=str(keep_file),
            delete_files=[str(delete_file)],
            reason='test'
        )

        # Validate and execute
        is_valid, _ = plan.validate(check_backup_space=False)
        assert is_valid

        stats = plan.execute(dry_run=False, create_backup=True)

        # Original should be deleted
        assert not delete_file.exists()

        # Backup should exist
        assert stats.backup_created
        assert stats.backup_path is not None
        backup_path = Path(stats.backup_path)
        assert backup_path.exists()

        # Check backup file exists
        backup_files = list(backup_path.glob('*.mp3'))
        assert len(backup_files) == 1

    def test_execute_skip_invalid_groups(self, tmp_path):
        """Test that invalid groups are skipped during execution."""
        plan = SafeDeletionPlan()

        # Add valid group
        keep1 = tmp_path / 'keep1.flac'
        delete1 = tmp_path / 'delete1.mp3'
        keep1.write_text('data')
        delete1.write_text('data')

        plan.add_group(
            keep_file=str(keep1),
            delete_files=[str(delete1)],
            reason='valid'
        )

        # Add invalid group (non-existent files)
        plan.add_group(
            keep_file='/nonexistent/keep2.flac',
            delete_files=['/nonexistent/delete2.mp3'],
            reason='invalid'
        )

        # Validate
        is_valid, errors = plan.validate(check_backup_space=False)
        assert is_valid is False  # Overall invalid due to one bad group

        # Execute (should skip invalid group)
        stats = plan.execute(dry_run=False, create_backup=False)

        # Only valid group should be processed
        assert stats.failed_deletions == 1  # Invalid group
        assert stats.files_failed > 0 or stats.failed_deletions > 0

    def test_export_to_json(self, tmp_path):
        """Test exporting deletion plan to JSON."""
        plan = SafeDeletionPlan()

        keep_file = tmp_path / 'keep.flac'
        delete_file = tmp_path / 'delete.mp3'
        keep_file.write_text('data')
        delete_file.write_text('data')

        plan.add_group(
            keep_file=str(keep_file),
            delete_files=[str(delete_file)],
            reason='Quality upgrade'
        )

        # Export to JSON
        json_file = tmp_path / 'plan.json'
        plan.export_to_json(str(json_file))

        # Verify JSON file exists and is valid
        assert json_file.exists()

        with open(json_file, 'r') as f:
            data = json.load(f)

        assert 'metadata' in data
        assert 'groups' in data
        assert data['metadata']['total_groups'] == 1
        assert len(data['groups']) == 1
        assert data['groups'][0]['reason'] == 'Quality upgrade'


# ==================== DeletionStats Tests ====================

class TestDeletionStats:
    """Test DeletionStats reporting."""

    def test_deletion_stats_creation(self):
        """Test DeletionStats instantiation."""
        stats = DeletionStats()

        assert stats.total_groups == 0
        assert stats.successful_deletions == 0
        assert stats.failed_deletions == 0
        assert stats.space_freed_bytes == 0

    def test_deletion_stats_to_dict(self):
        """Test DeletionStats serialization."""
        stats = DeletionStats(
            total_groups=5,
            successful_deletions=4,
            failed_deletions=1,
            files_deleted=8,
            space_freed_bytes=50_000_000
        )

        data = stats.to_dict()

        assert data['total_groups'] == 5
        assert data['successful_deletions'] == 4
        assert data['failed_deletions'] == 1
        assert data['space_freed_bytes'] == 50_000_000

    def test_deletion_stats_str_format(self):
        """Test DeletionStats string formatting."""
        stats = DeletionStats(
            total_groups=3,
            successful_deletions=2,
            files_deleted=4,
            space_freed_bytes=25_000_000
        )

        output = str(stats)

        assert 'Total Groups: 3' in output
        assert 'Successful: 2' in output
        assert 'Files Deleted: 4' in output
        assert 'MB' in output  # Space formatted in MB

    def test_deletion_stats_format_bytes(self):
        """Test bytes formatting helper."""
        assert 'B' in DeletionStats._format_bytes(500)
        assert 'KB' in DeletionStats._format_bytes(2048)
        assert 'MB' in DeletionStats._format_bytes(5_000_000)
        assert 'GB' in DeletionStats._format_bytes(2_000_000_000)


# ==================== Convenience Functions Tests ====================

class TestConvenienceFunctions:
    """Test convenience helper functions."""

    def test_create_deletion_plan(self):
        """Test create_deletion_plan convenience function."""
        plan = create_deletion_plan()
        assert isinstance(plan, SafeDeletionPlan)
        assert plan.backup_dir is None

    def test_create_deletion_plan_with_backup(self, tmp_path):
        """Test create_deletion_plan with backup directory."""
        backup_dir = tmp_path / 'backup'
        plan = create_deletion_plan(backup_dir=str(backup_dir))

        assert isinstance(plan, SafeDeletionPlan)
        assert plan.backup_dir == str(backup_dir)

    def test_validate_deletion_valid(self, tmp_path):
        """Test validate_deletion with valid files."""
        keep_file = tmp_path / 'keep.flac'
        delete_file = tmp_path / 'delete.mp3'
        keep_file.write_text('data')
        delete_file.write_text('data')

        is_valid, errors = validate_deletion(
            keep_file=str(keep_file),
            delete_files=[str(delete_file)]
        )

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_deletion_invalid(self):
        """Test validate_deletion with invalid files."""
        is_valid, errors = validate_deletion(
            keep_file='/nonexistent/keep.flac',
            delete_files=['/nonexistent/delete.mp3']
        )

        assert is_valid is False
        assert len(errors) > 0


# ==================== Edge Cases and Error Handling ====================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_deletion_plan_empty_groups(self):
        """Test deletion plan with no groups."""
        plan = SafeDeletionPlan()

        is_valid, errors = plan.validate()

        assert is_valid is True  # No groups to validate
        assert len(errors) == 0

    def test_deletion_plan_execute_empty(self):
        """Test executing empty deletion plan."""
        plan = SafeDeletionPlan()

        stats = plan.execute(dry_run=True)

        assert stats.total_groups == 0
        assert stats.files_deleted == 0

    def test_backup_file_name_conflict(self, tmp_path):
        """Test backup handles filename conflicts."""
        backup_dir = tmp_path / 'backup'
        plan = SafeDeletionPlan(backup_dir=str(backup_dir))

        # Create files with same name in different locations
        dir1 = tmp_path / 'dir1'
        dir2 = tmp_path / 'dir2'
        dir1.mkdir()
        dir2.mkdir()

        keep = dir1 / 'keep.flac'
        delete1 = dir1 / 'song.mp3'
        delete2 = dir2 / 'song.mp3'  # Same name!

        keep.write_text('keep')
        delete1.write_text('delete1')
        delete2.write_text('delete2')

        plan.add_group(
            keep_file=str(keep),
            delete_files=[str(delete1), str(delete2)],
            reason='test'
        )

        # Execute with backup
        stats = plan.execute(dry_run=False, create_backup=True)

        # Both files should be backed up with different names
        backup_path = Path(stats.backup_path)
        backup_files = list(backup_path.glob('*.mp3'))

        assert len(backup_files) == 2  # Both files backed up


# ==================== Performance Benchmarks ====================

class TestPerformance:
    """Performance benchmark tests."""

    def test_validate_group_performance(self, tmp_path, benchmark):
        """Benchmark validation performance."""
        validator = DeletionValidator()

        keep_file = tmp_path / 'keep.flac'
        delete_files = [tmp_path / f'delete{i}.mp3' for i in range(10)]

        keep_file.write_text('data')
        for f in delete_files:
            f.write_text('data')

        group = DeletionGroup(
            keep_file=str(keep_file),
            delete_files=[str(f) for f in delete_files],
            reason='test'
        )

        # Should complete in < 10ms
        results = benchmark(validator.validate_group, group, False)
        assert len(results) > 0

    def test_execute_plan_performance(self, tmp_path, benchmark):
        """Benchmark execution performance with multiple groups."""
        plan = SafeDeletionPlan()

        # Create 10 groups
        for i in range(10):
            keep = tmp_path / f'keep{i}.flac'
            delete = tmp_path / f'delete{i}.mp3'
            keep.write_text('data')
            delete.write_text('data')

            plan.add_group(
                keep_file=str(keep),
                delete_files=[str(delete)],
                reason=f'test {i}'
            )

        # Validate first
        plan.validate(check_backup_space=False)

        # Benchmark execution
        stats = benchmark(plan.execute, dry_run=True, create_backup=False)
        assert stats.total_groups == 10


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--benchmark-disable'])
