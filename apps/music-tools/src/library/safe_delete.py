"""
Safe Deletion Module

Provides safe file deletion with comprehensive validation, backup functionality,
and dry-run capabilities. Implements a 7-point safety checklist to prevent
accidental data loss.

Author: Music Tools Dev Team
Created: 2026-01-08
"""

import os
import shutil
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path
from datetime import datetime
from enum import Enum


# Configure logging
logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Result of a validation check"""
    level: ValidationLevel
    checkpoint: str
    message: str
    details: Optional[Dict[str, Any]] = None

    def is_blocking(self) -> bool:
        """Check if this validation result should block deletion"""
        return self.level == ValidationLevel.ERROR


@dataclass
class DeletionGroup:
    """Represents a group of files where one is kept and others are deleted"""
    keep_file: str
    delete_files: List[str]
    reason: str
    validation_results: List[ValidationResult] = field(default_factory=list)
    group_id: Optional[str] = None

    def __post_init__(self):
        """Generate group ID if not provided"""
        if self.group_id is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            keep_basename = Path(self.keep_file).stem[:20]
            self.group_id = f"{keep_basename}_{timestamp}"

    def is_valid(self) -> bool:
        """Check if group passes all validations"""
        return not any(result.is_blocking() for result in self.validation_results)

    def get_errors(self) -> List[ValidationResult]:
        """Get all error-level validation results"""
        return [r for r in self.validation_results if r.level == ValidationLevel.ERROR]

    def get_warnings(self) -> List[ValidationResult]:
        """Get all warning-level validation results"""
        return [r for r in self.validation_results if r.level == ValidationLevel.WARNING]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'group_id': self.group_id,
            'keep_file': self.keep_file,
            'delete_files': self.delete_files,
            'reason': self.reason,
            'validation_results': [
                {
                    'level': r.level.value,
                    'checkpoint': r.checkpoint,
                    'message': r.message,
                    'details': r.details
                }
                for r in self.validation_results
            ]
        }


@dataclass
class DeletionStats:
    """Statistics from deletion operation"""
    total_groups: int = 0
    successful_deletions: int = 0
    failed_deletions: int = 0
    files_deleted: int = 0
    files_failed: int = 0
    space_freed_bytes: int = 0
    backup_created: bool = False
    backup_path: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    def __str__(self) -> str:
        """Human-readable statistics"""
        lines = [
            f"Deletion Statistics:",
            f"  Total Groups: {self.total_groups}",
            f"  Successful: {self.successful_deletions}",
            f"  Failed: {self.failed_deletions}",
            f"  Files Deleted: {self.files_deleted}",
            f"  Files Failed: {self.files_failed}",
            f"  Space Freed: {self._format_bytes(self.space_freed_bytes)}",
        ]
        if self.backup_created:
            lines.append(f"  Backup: {self.backup_path}")
        if self.errors:
            lines.append(f"  Errors: {len(self.errors)}")
        if self.warnings:
            lines.append(f"  Warnings: {len(self.warnings)}")
        return "\n".join(lines)

    @staticmethod
    def _format_bytes(bytes_size: int) -> str:
        """Format bytes to human-readable size"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} PB"


class DeletionValidator:
    """
    Implements 7-point safety checklist for file deletions

    Safety Checklist:
    1. Keep file must exist
    2. Must have files to delete (not empty)
    3. Warn if deleting higher bitrate
    4. Verify delete files exist
    5. Never delete all files in group
    6. Check file permissions
    7. Validate sufficient disk space for backup
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.DeletionValidator")

    def validate_group(self, group: DeletionGroup, check_backup_space: bool = True) -> List[ValidationResult]:
        """
        Run all validation checks on a deletion group

        Args:
            group: DeletionGroup to validate
            check_backup_space: Whether to check disk space for backup

        Returns:
            List of ValidationResult objects
        """
        results = []

        # Checkpoint 1: Keep file must exist
        results.append(self._validate_keep_file_exists(group))

        # Checkpoint 2: Must have files to delete
        results.append(self._validate_has_files_to_delete(group))

        # Checkpoint 3: Warn if deleting higher quality
        results.extend(self._validate_no_higher_quality_deletion(group))

        # Checkpoint 4: Verify delete files exist
        results.extend(self._validate_files_exist(group))

        # Checkpoint 5: Never delete all files
        results.append(self._validate_not_deleting_all_files(group))

        # Checkpoint 6: Check file permissions
        results.extend(self._validate_file_permissions(group))

        # Checkpoint 7: Validate backup space (if requested)
        if check_backup_space:
            results.append(self._validate_backup_space(group))

        return results

    def _validate_keep_file_exists(self, group: DeletionGroup) -> ValidationResult:
        """Checkpoint 1: Verify the keep file exists"""
        if not group.keep_file:
            return ValidationResult(
                level=ValidationLevel.ERROR,
                checkpoint="1. Keep File Exists",
                message="Keep file path is empty",
                details={'keep_file': group.keep_file}
            )

        keep_path = Path(group.keep_file)
        if not keep_path.exists():
            return ValidationResult(
                level=ValidationLevel.ERROR,
                checkpoint="1. Keep File Exists",
                message=f"Keep file does not exist: {group.keep_file}",
                details={'keep_file': group.keep_file, 'exists': False}
            )

        if not keep_path.is_file():
            return ValidationResult(
                level=ValidationLevel.ERROR,
                checkpoint="1. Keep File Exists",
                message=f"Keep file path is not a file: {group.keep_file}",
                details={'keep_file': group.keep_file, 'is_file': False}
            )

        return ValidationResult(
            level=ValidationLevel.INFO,
            checkpoint="1. Keep File Exists",
            message=f"Keep file validated: {keep_path.name}",
            details={'keep_file': group.keep_file, 'size_bytes': keep_path.stat().st_size}
        )

    def _validate_has_files_to_delete(self, group: DeletionGroup) -> ValidationResult:
        """Checkpoint 2: Ensure there are files to delete"""
        if not group.delete_files:
            return ValidationResult(
                level=ValidationLevel.ERROR,
                checkpoint="2. Has Files to Delete",
                message="No files marked for deletion",
                details={'delete_count': 0}
            )

        return ValidationResult(
            level=ValidationLevel.INFO,
            checkpoint="2. Has Files to Delete",
            message=f"{len(group.delete_files)} file(s) marked for deletion",
            details={'delete_count': len(group.delete_files)}
        )

    def _validate_no_higher_quality_deletion(self, group: DeletionGroup) -> List[ValidationResult]:
        """Checkpoint 3: Warn if deleting higher bitrate/quality files"""
        results = []

        try:
            keep_bitrate = self._extract_bitrate(group.keep_file)

            for delete_file in group.delete_files:
                delete_bitrate = self._extract_bitrate(delete_file)

                if delete_bitrate and keep_bitrate and delete_bitrate > keep_bitrate:
                    results.append(ValidationResult(
                        level=ValidationLevel.WARNING,
                        checkpoint="3. Quality Check",
                        message=f"Deleting higher bitrate file: {Path(delete_file).name} ({delete_bitrate} kbps) while keeping {Path(group.keep_file).name} ({keep_bitrate} kbps)",
                        details={
                            'keep_file': group.keep_file,
                            'keep_bitrate': keep_bitrate,
                            'delete_file': delete_file,
                            'delete_bitrate': delete_bitrate
                        }
                    ))
        except Exception as e:
            self.logger.debug(f"Could not compare bitrates: {e}")

        if not results:
            results.append(ValidationResult(
                level=ValidationLevel.INFO,
                checkpoint="3. Quality Check",
                message="No higher quality files being deleted",
                details={}
            ))

        return results

    def _validate_files_exist(self, group: DeletionGroup) -> List[ValidationResult]:
        """Checkpoint 4: Verify all files to delete exist"""
        results = []

        for delete_file in group.delete_files:
            delete_path = Path(delete_file)

            if not delete_path.exists():
                results.append(ValidationResult(
                    level=ValidationLevel.ERROR,
                    checkpoint="4. Files Exist",
                    message=f"File marked for deletion does not exist: {delete_file}",
                    details={'delete_file': delete_file, 'exists': False}
                ))
            elif not delete_path.is_file():
                results.append(ValidationResult(
                    level=ValidationLevel.ERROR,
                    checkpoint="4. Files Exist",
                    message=f"Path marked for deletion is not a file: {delete_file}",
                    details={'delete_file': delete_file, 'is_file': False}
                ))

        if not results:
            results.append(ValidationResult(
                level=ValidationLevel.INFO,
                checkpoint="4. Files Exist",
                message=f"All {len(group.delete_files)} file(s) to delete verified",
                details={'verified_count': len(group.delete_files)}
            ))

        return results

    def _validate_not_deleting_all_files(self, group: DeletionGroup) -> ValidationResult:
        """Checkpoint 5: Ensure we're not deleting all files in the group"""
        # This check ensures we always keep at least one file
        if not group.keep_file or not Path(group.keep_file).exists():
            return ValidationResult(
                level=ValidationLevel.ERROR,
                checkpoint="5. Keep At Least One",
                message="Cannot delete all files - keep file is invalid",
                details={'keep_file_valid': False}
            )

        # Check if any delete file is the same as keep file
        keep_path = Path(group.keep_file).resolve()
        for delete_file in group.delete_files:
            delete_path = Path(delete_file).resolve()
            if keep_path == delete_path:
                return ValidationResult(
                    level=ValidationLevel.ERROR,
                    checkpoint="5. Keep At Least One",
                    message="Keep file is also marked for deletion",
                    details={
                        'keep_file': group.keep_file,
                        'conflict_file': delete_file
                    }
                )

        return ValidationResult(
            level=ValidationLevel.INFO,
            checkpoint="5. Keep At Least One",
            message="Keep file will be preserved",
            details={'keep_file': group.keep_file}
        )

    def _validate_file_permissions(self, group: DeletionGroup) -> List[ValidationResult]:
        """Checkpoint 6: Check file permissions for deletion"""
        results = []

        for delete_file in group.delete_files:
            delete_path = Path(delete_file)

            if not delete_path.exists():
                continue  # Already caught by checkpoint 4

            # Check write permission on parent directory
            parent_dir = delete_path.parent
            if not os.access(parent_dir, os.W_OK):
                results.append(ValidationResult(
                    level=ValidationLevel.ERROR,
                    checkpoint="6. File Permissions",
                    message=f"No write permission on directory: {parent_dir}",
                    details={
                        'delete_file': delete_file,
                        'parent_dir': str(parent_dir),
                        'writable': False
                    }
                ))

            # Check write permission on file itself
            if not os.access(delete_path, os.W_OK):
                results.append(ValidationResult(
                    level=ValidationLevel.ERROR,
                    checkpoint="6. File Permissions",
                    message=f"No write permission on file: {delete_file}",
                    details={
                        'delete_file': delete_file,
                        'writable': False
                    }
                ))

        if not results:
            results.append(ValidationResult(
                level=ValidationLevel.INFO,
                checkpoint="6. File Permissions",
                message="All file permissions verified",
                details={'permissions_ok': True}
            ))

        return results

    def _validate_backup_space(self, group: DeletionGroup) -> ValidationResult:
        """Checkpoint 7: Check sufficient disk space for backup"""
        try:
            total_size = 0
            for delete_file in group.delete_files:
                delete_path = Path(delete_file)
                if delete_path.exists():
                    total_size += delete_path.stat().st_size

            # Get available space on the drive containing the first delete file
            if group.delete_files:
                first_file = Path(group.delete_files[0])
                if first_file.exists():
                    stat = shutil.disk_usage(first_file.parent)
                    available_space = stat.free

                    # Require 2x the file size for safety
                    required_space = total_size * 2

                    if available_space < required_space:
                        return ValidationResult(
                            level=ValidationLevel.WARNING,
                            checkpoint="7. Backup Space",
                            message=f"Limited disk space for backup. Available: {DeletionStats._format_bytes(available_space)}, Required: {DeletionStats._format_bytes(required_space)}",
                            details={
                                'available_bytes': available_space,
                                'required_bytes': required_space,
                                'total_size': total_size
                            }
                        )

            return ValidationResult(
                level=ValidationLevel.INFO,
                checkpoint="7. Backup Space",
                message="Sufficient disk space for backup",
                details={'total_size': total_size}
            )

        except Exception as e:
            self.logger.warning(f"Could not check disk space: {e}")
            return ValidationResult(
                level=ValidationLevel.WARNING,
                checkpoint="7. Backup Space",
                message=f"Could not verify disk space: {str(e)}",
                details={'error': str(e)}
            )

    @staticmethod
    def _extract_bitrate(filepath: str) -> Optional[int]:
        """Extract bitrate from filename or metadata (basic implementation)"""
        # Simple pattern matching for common bitrate indicators in filenames
        import re
        filename = Path(filepath).name.lower()

        # Look for patterns like "320kbps", "320k", "320 kbps"
        patterns = [
            r'(\d{3})kbps',
            r'(\d{3})k',
            r'(\d{3})\s*kbps',
        ]

        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                return int(match.group(1))

        return None


class SafeDeletionPlan:
    """
    Manages a plan for safely deleting duplicate files

    Features:
    - Group-based deletion management
    - Comprehensive validation
    - Backup functionality
    - Dry-run capability
    - Detailed logging and statistics
    """

    def __init__(self, backup_dir: Optional[str] = None):
        """
        Initialize a safe deletion plan

        Args:
            backup_dir: Optional directory for backing up files before deletion
        """
        self.groups: List[DeletionGroup] = []
        self.backup_dir = backup_dir
        self.validator = DeletionValidator()
        self.logger = logging.getLogger(f"{__name__}.SafeDeletionPlan")

    def add_group(self, keep_file: str, delete_files: List[str], reason: str = "") -> DeletionGroup:
        """
        Add a deletion group to the plan

        Args:
            keep_file: Path to the file to keep
            delete_files: List of file paths to delete
            reason: Reason for this deletion group

        Returns:
            The created DeletionGroup
        """
        group = DeletionGroup(
            keep_file=keep_file,
            delete_files=delete_files,
            reason=reason
        )
        self.groups.append(group)
        self.logger.info(f"Added deletion group: keep={Path(keep_file).name}, delete={len(delete_files)} files")
        return group

    def validate(self, check_backup_space: bool = True) -> Tuple[bool, List[str]]:
        """
        Validate all deletion groups

        Args:
            check_backup_space: Whether to check disk space for backups

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        self.logger.info(f"Validating {len(self.groups)} deletion groups...")

        all_errors = []

        for idx, group in enumerate(self.groups, 1):
            self.logger.debug(f"Validating group {idx}/{len(self.groups)}: {group.group_id}")

            # Run validation checks
            validation_results = self.validator.validate_group(group, check_backup_space)
            group.validation_results = validation_results

            # Collect errors
            errors = group.get_errors()
            if errors:
                for error in errors:
                    error_msg = f"Group {group.group_id}: {error.message}"
                    all_errors.append(error_msg)
                    self.logger.error(error_msg)

            # Log warnings
            warnings = group.get_warnings()
            for warning in warnings:
                self.logger.warning(f"Group {group.group_id}: {warning.message}")

        is_valid = len(all_errors) == 0

        if is_valid:
            self.logger.info(f"Validation passed for all {len(self.groups)} groups")
        else:
            self.logger.error(f"Validation failed with {len(all_errors)} errors")

        return is_valid, all_errors

    def execute(self, dry_run: bool = False, create_backup: bool = True) -> DeletionStats:
        """
        Execute the deletion plan

        Args:
            dry_run: If True, simulate deletion without actually deleting files
            create_backup: If True, backup files before deletion

        Returns:
            DeletionStats object with operation results
        """
        stats = DeletionStats(total_groups=len(self.groups))

        mode = "DRY RUN" if dry_run else "EXECUTION"
        self.logger.info(f"Starting deletion plan {mode} for {len(self.groups)} groups...")

        # Create backup directory if needed
        backup_path = None
        if create_backup and not dry_run and self.backup_dir:
            backup_path = self._create_backup_directory()
            stats.backup_path = backup_path
            self.logger.info(f"Backup directory created: {backup_path}")

        # Process each group
        for idx, group in enumerate(self.groups, 1):
            self.logger.info(f"Processing group {idx}/{len(self.groups)}: {group.group_id}")

            # Skip invalid groups
            if not group.is_valid():
                error_msg = f"Skipping invalid group {group.group_id}"
                self.logger.error(error_msg)
                stats.failed_deletions += 1
                stats.errors.append(error_msg)
                continue

            # Process deletions in this group
            group_success = True
            for delete_file in group.delete_files:
                try:
                    delete_path = Path(delete_file)
                    file_size = delete_path.stat().st_size if delete_path.exists() else 0

                    # Backup if requested
                    if create_backup and backup_path and not dry_run:
                        self._backup_file(delete_file, backup_path)

                    # Delete file
                    if dry_run:
                        self.logger.info(f"[DRY RUN] Would delete: {delete_file}")
                    else:
                        delete_path.unlink()
                        self.logger.info(f"Deleted: {delete_file}")

                    stats.files_deleted += 1
                    stats.space_freed_bytes += file_size

                except Exception as e:
                    error_msg = f"Failed to delete {delete_file}: {str(e)}"
                    self.logger.error(error_msg)
                    stats.files_failed += 1
                    stats.errors.append(error_msg)
                    group_success = False

            if group_success:
                stats.successful_deletions += 1
            else:
                stats.failed_deletions += 1

        # Set backup flag
        if create_backup and backup_path and not dry_run:
            stats.backup_created = True

        # Log summary
        self.logger.info(f"Deletion plan {mode} complete:")
        self.logger.info(str(stats))

        return stats

    def export_to_json(self, filepath: str) -> None:
        """
        Export the deletion plan to a JSON file

        Args:
            filepath: Path where JSON file should be saved
        """
        export_data = {
            'metadata': {
                'created': datetime.now().isoformat(),
                'total_groups': len(self.groups),
                'backup_dir': self.backup_dir
            },
            'groups': [group.to_dict() for group in self.groups]
        }

        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Deletion plan exported to: {filepath}")

    def _create_backup_directory(self) -> str:
        """Create timestamped backup directory"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = Path(self.backup_dir) / f"backup_{timestamp}"
        backup_path.mkdir(parents=True, exist_ok=True)
        return str(backup_path)

    def _backup_file(self, source_file: str, backup_dir: str) -> None:
        """
        Backup a file before deletion

        Args:
            source_file: Path to file to backup
            backup_dir: Directory where backup should be stored
        """
        source_path = Path(source_file)

        # Preserve directory structure in backup
        backup_path = Path(backup_dir) / source_path.name

        # Handle filename conflicts
        counter = 1
        while backup_path.exists():
            stem = source_path.stem
            suffix = source_path.suffix
            backup_path = Path(backup_dir) / f"{stem}_{counter}{suffix}"
            counter += 1

        # Copy file
        shutil.copy2(source_file, backup_path)
        self.logger.debug(f"Backed up: {source_file} -> {backup_path}")


# Convenience functions
def create_deletion_plan(backup_dir: Optional[str] = None) -> SafeDeletionPlan:
    """
    Create a new safe deletion plan

    Args:
        backup_dir: Optional directory for file backups

    Returns:
        New SafeDeletionPlan instance
    """
    return SafeDeletionPlan(backup_dir=backup_dir)


def validate_deletion(keep_file: str, delete_files: List[str]) -> Tuple[bool, List[str]]:
    """
    Quick validation of a single deletion operation

    Args:
        keep_file: File to keep
        delete_files: Files to delete

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    validator = DeletionValidator()
    group = DeletionGroup(keep_file=keep_file, delete_files=delete_files, reason="validation")
    results = validator.validate_group(group, check_backup_space=False)

    errors = [r.message for r in results if r.level == ValidationLevel.ERROR]
    is_valid = len(errors) == 0

    return is_valid, errors
