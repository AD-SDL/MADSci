"""Test backup management operations."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from madsci.common.backup_tools.backup_manager import BackupManager
from madsci.common.backup_tools.backup_validator import BackupValidator
from madsci.common.backup_tools.base_backup import BackupInfo


class TestBackupManager:
    """Test backup management operations."""

    @pytest.fixture
    def manager(self):
        """Create BackupManager instance for testing."""
        return BackupManager()

    @pytest.fixture
    def temp_backup_dir(self):
        """Create temporary backup directory with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir)

            # Create several test backup files with metadata
            now = datetime.now()
            validator = BackupValidator()

            for i in range(5):
                backup_time = now - timedelta(days=i)
                backup_file = backup_dir / f"backup_{i}.sql"

                # Create backup file
                backup_file.write_text(
                    f"-- Test backup {i}\nCREATE TABLE test{i} (id INTEGER);"
                )

                # Generate real checksum for the file
                real_checksum = validator.generate_checksum(backup_file)

                # Create metadata file
                metadata = {
                    "timestamp": backup_time.isoformat(),
                    "backup_path": str(backup_file),
                    "backup_size": backup_file.stat().st_size,
                    "database_version": f"1.{i}.0",
                    "backup_type": "postgresql",
                    "is_valid": True,
                    "checksum": real_checksum,
                }

                metadata_file = backup_file.with_suffix(".metadata.json")
                metadata_file.write_text(json.dumps(metadata, indent=2))

                # Create checksum file
                checksum_file = backup_file.with_suffix(".checksum")
                checksum_file.write_text(real_checksum)

            yield backup_dir

    def test_list_backups_sorted_by_date(self, manager, temp_backup_dir):
        """Test backup listing returns backups sorted by modification time."""
        backups = manager.list_backups(temp_backup_dir)

        # Should find 5 backups
        assert len(backups) == 5

        # Should be sorted by creation time (newest first)
        for i in range(len(backups) - 1):
            assert backups[i].created_at >= backups[i + 1].created_at

    def test_list_backups_with_metadata(self, manager, temp_backup_dir):
        """Test backup listing includes metadata information."""
        backups = manager.list_backups(temp_backup_dir)

        for backup in backups:
            assert isinstance(backup, BackupInfo)
            assert backup.backup_path.exists()
            assert backup.created_at is not None
            assert backup.backup_size > 0
            assert backup.database_version is not None
            assert backup.backup_type == "postgresql"
            assert backup.is_valid is True
            assert backup.checksum is not None

    def test_list_backups_empty_directory(self, manager):
        """Test backup listing in empty directory."""
        with tempfile.TemporaryDirectory() as empty_dir:
            backups = manager.list_backups(Path(empty_dir))
            assert backups == []

    def test_list_backups_nonexistent_directory(self, manager):
        """Test backup listing with nonexistent directory."""
        nonexistent_dir = Path("/nonexistent/backup/dir")
        backups = manager.list_backups(nonexistent_dir)
        assert backups == []

    def test_backup_rotation_policies(self, manager, temp_backup_dir):
        """Test backup rotation respects retention policies."""
        # Initially 5 backups
        initial_backups = manager.list_backups(temp_backup_dir)
        assert len(initial_backups) == 5

        # Rotate to keep only 3 backups
        removed_count = manager.rotate_backups(temp_backup_dir, max_backups=3)

        # Should have removed 2 backups
        assert removed_count == 2

        # Should now have only 3 backups
        remaining_backups = manager.list_backups(temp_backup_dir)
        assert len(remaining_backups) == 3

        # Remaining backups should be the 3 newest ones
        for backup in remaining_backups:
            assert backup.backup_path.exists()

    def test_backup_rotation_keeps_newest(self, manager, temp_backup_dir):
        """Test backup rotation keeps newest backups."""
        # Get initial backups (sorted newest first)
        initial_backups = manager.list_backups(temp_backup_dir)
        newest_backup_paths = [b.backup_path for b in initial_backups[:2]]

        # Rotate to keep only 2 backups
        manager.rotate_backups(temp_backup_dir, max_backups=2)

        # Verify the 2 newest backups remain
        remaining_backups = manager.list_backups(temp_backup_dir)
        remaining_paths = [b.backup_path for b in remaining_backups]

        assert len(remaining_paths) == 2
        for path in newest_backup_paths:
            assert path in remaining_paths

    def test_backup_rotation_no_operation_when_under_limit(
        self, manager, temp_backup_dir
    ):
        """Test backup rotation does nothing when under limit."""
        # Try to rotate with higher limit than current count
        removed_count = manager.rotate_backups(temp_backup_dir, max_backups=10)

        # Should not remove any backups
        assert removed_count == 0

        # All 5 backups should still exist
        backups = manager.list_backups(temp_backup_dir)
        assert len(backups) == 5

    def test_backup_rotation_zero_limit(self, manager, temp_backup_dir):
        """Test backup rotation with zero limit removes all backups."""
        removed_count = manager.rotate_backups(temp_backup_dir, max_backups=0)

        # Should remove all 5 backups
        assert removed_count == 5

        # No backups should remain
        backups = manager.list_backups(temp_backup_dir)
        assert len(backups) == 0

    def test_backup_rotation_cleans_associated_files(self, manager, temp_backup_dir):
        """Test backup rotation removes associated metadata and checksum files."""
        # Rotate to keep only 1 backup
        manager.rotate_backups(temp_backup_dir, max_backups=1)

        # Check that removed backups' associated files are also gone
        all_files = list(temp_backup_dir.glob("*"))

        # Should have only 3 files remaining: 1 backup + 1 metadata + 1 checksum
        sql_files = [f for f in all_files if f.suffix == ".sql"]
        json_files = [f for f in all_files if f.suffix == ".json"]
        checksum_files = [f for f in all_files if f.suffix == ".checksum"]

        assert len(sql_files) == 1
        assert len(json_files) == 1
        assert len(checksum_files) == 1

    def test_find_backup_by_criteria(self, manager, temp_backup_dir):
        """Test finding backups by specific criteria."""
        # Find backup by database version
        backup = manager.find_backup_by_version(temp_backup_dir, "1.2.0")
        assert backup is not None
        assert backup.database_version == "1.2.0"

        # Find backup by date range
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        two_days_ago = now - timedelta(days=2)

        recent_backups = manager.find_backups_in_date_range(
            temp_backup_dir, start_date=two_days_ago, end_date=yesterday
        )

        # Should find backups from the specified date range
        assert len(recent_backups) > 0
        for backup in recent_backups:
            assert two_days_ago <= backup.created_at <= yesterday

    def test_backup_validation_status(self, manager, temp_backup_dir):
        """Test checking backup validation status."""
        manager.list_backups(temp_backup_dir)

        # All test backups should be marked as valid
        valid_backups = manager.get_valid_backups(temp_backup_dir)
        invalid_backups = manager.get_invalid_backups(temp_backup_dir)

        assert len(valid_backups) == 5
        assert len(invalid_backups) == 0
        assert all(backup.is_valid for backup in valid_backups)

    def test_backup_size_analysis(self, manager, temp_backup_dir):
        """Test backup size analysis and reporting."""
        total_size = manager.get_total_backup_size(temp_backup_dir)
        avg_size = manager.get_average_backup_size(temp_backup_dir)

        assert total_size > 0
        assert avg_size > 0

        # Average should be total divided by count
        backups = manager.list_backups(temp_backup_dir)
        expected_avg = total_size / len(backups)
        assert abs(avg_size - expected_avg) < 1  # Allow for small floating point errors

    def test_cleanup_incomplete_backups(self, manager, temp_backup_dir):
        """Test cleanup of incomplete backup files."""
        # Create incomplete backup (backup file without metadata)
        incomplete_backup = temp_backup_dir / "incomplete_backup.sql"
        incomplete_backup.write_text("-- Incomplete backup")

        # Create orphaned metadata (metadata without backup file)
        orphaned_metadata = temp_backup_dir / "orphaned.metadata.json"
        orphaned_metadata.write_text('{"backup_path": "/nonexistent/backup.sql"}')

        # Create orphaned checksum file
        orphaned_checksum = temp_backup_dir / "orphaned.checksum"
        orphaned_checksum.write_text("orphaned_checksum")

        # Run cleanup
        cleaned_files = manager.cleanup_incomplete_backups(temp_backup_dir)

        # Should have cleaned up incomplete and orphaned files
        assert len(cleaned_files) >= 3  # At least the 3 files we created
        assert not incomplete_backup.exists()
        assert not orphaned_metadata.exists()
        assert not orphaned_checksum.exists()

    def test_backup_integrity_check(self, manager, temp_backup_dir):
        """Test backup integrity checking across all backups."""
        integrity_report = manager.check_all_backups_integrity(temp_backup_dir)

        assert "total_backups" in integrity_report
        assert "valid_backups" in integrity_report
        assert "invalid_backups" in integrity_report
        assert "corrupted_backups" in integrity_report

        # All test backups should pass integrity check
        assert integrity_report["total_backups"] == 5
        assert integrity_report["valid_backups"] == 5
        assert integrity_report["invalid_backups"] == 0
        assert len(integrity_report["corrupted_backups"]) == 0

    def test_export_backup_inventory(self, manager, temp_backup_dir):
        """Test exporting backup inventory to JSON."""
        inventory = manager.export_backup_inventory(temp_backup_dir)

        assert "backup_directory" in inventory
        assert "total_backups" in inventory
        assert "total_size" in inventory
        assert "backups" in inventory

        assert inventory["backup_directory"] == str(temp_backup_dir)
        assert inventory["total_backups"] == 5
        assert len(inventory["backups"]) == 5

        # Each backup entry should have required fields
        for backup_entry in inventory["backups"]:
            assert "backup_path" in backup_entry
            assert "created_at" in backup_entry
            assert "database_version" in backup_entry
            assert "backup_size" in backup_entry
            assert "backup_type" in backup_entry
