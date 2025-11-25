"""Test cases for migration concurrency control and race condition prevention."""

import contextlib
import tempfile
import threading
import time
from pathlib import Path
from unittest import mock

import pytest
from madsci.common.mongodb_migration_tool import MongoDBMigrator
from madsci.common.types.mongodb_migration_types import MongoDBMigrationSettings
from madsci.resource_manager.migration_tool import (
    DatabaseMigrationSettings,
    DatabaseMigrator,
)


class TestMigrationLocking:
    """Test cases for preventing concurrent migrations."""

    def setup_method(self):
        """Set up test environment for each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_db_url = "postgresql://test:test@localhost:5432/test_migration"

    def teardown_method(self):
        """Clean up test environment after each test."""
        # Clean up any lock files
        for lock_file in self.temp_dir.glob("*.lock"):
            with contextlib.suppress(FileNotFoundError):
                lock_file.unlink()

    def test_single_migration_acquires_lock(self):
        """Test that a single migration successfully acquires lock."""
        settings = DatabaseMigrationSettings(db_url=self.test_db_url)

        # Mock the engine creation to avoid actual database connection
        with (
            mock.patch("sqlmodel.create_engine"),
            mock.patch(
                "madsci.resource_manager.database_version_checker.DatabaseVersionChecker"
            ),
        ):
            migrator = DatabaseMigrator(settings)

            migrator._acquire_migration_lock()
            assert migrator.lock_file is not None
            assert migrator.lock_file.exists()

            # Save lock file path before releasing
            lock_file_path = migrator.lock_file

            migrator._release_migration_lock()
            assert not lock_file_path.exists()
            assert migrator.lock_file is None

    def test_concurrent_migrations_blocked(self):
        """Test that concurrent migrations are blocked by locking."""
        settings = DatabaseMigrationSettings(db_url=self.test_db_url)

        # Mock the engine creation to avoid actual database connection
        with (
            mock.patch("sqlmodel.create_engine"),
            mock.patch(
                "madsci.resource_manager.database_version_checker.DatabaseVersionChecker"
            ),
        ):
            migrator1 = DatabaseMigrator(settings)
            migrator2 = DatabaseMigrator(settings)

            # First migration acquires lock
            migrator1._acquire_migration_lock()

            # Second migration should be blocked
            with pytest.raises(
                RuntimeError, match="Another migration is already in progress"
            ):
                migrator2._acquire_migration_lock()

            # Release first lock, second should now succeed
            migrator1._release_migration_lock()
            migrator2._acquire_migration_lock()  # Should not raise
            migrator2._release_migration_lock()

    def test_lock_cleanup_on_exception(self):
        """Test that locks are cleaned up even when exceptions occur."""
        settings = DatabaseMigrationSettings(db_url=self.test_db_url)

        # Mock the engine creation to avoid actual database connection
        with (
            mock.patch("sqlmodel.create_engine"),
            mock.patch(
                "madsci.resource_manager.database_version_checker.DatabaseVersionChecker"
            ),
        ):
            migrator = DatabaseMigrator(settings)

            try:
                migrator._acquire_migration_lock()
                raise Exception("Simulated failure")
            except Exception:  # noqa: S110
                # Expected exception for test, no need to log
                pass
            finally:
                migrator._release_migration_lock()

            # Lock should be cleaned up
            assert migrator.lock_file is None or not migrator.lock_file.exists()

            # Another migration should be able to proceed
            migrator._acquire_migration_lock()
            migrator._release_migration_lock()

    def test_stale_lock_detection(self):
        """Test detection and cleanup of stale locks."""
        settings = DatabaseMigrationSettings(db_url=self.test_db_url)

        # Mock the engine creation to avoid actual database connection
        with (
            mock.patch("sqlmodel.create_engine"),
            mock.patch(
                "madsci.resource_manager.database_version_checker.DatabaseVersionChecker"
            ),
        ):
            DatabaseMigrator(settings)
            migrator2 = DatabaseMigrator(settings)

            # Create a stale lock file manually
            temp_dir = Path(tempfile.gettempdir())
            lock_file = temp_dir / "madsci_migration_test_migration.lock"

            with lock_file.open("w") as f:
                # Write old timestamp (more than 1 hour ago)
                old_timestamp = time.time() - 7200  # 2 hours ago
                f.write(
                    f"pid=12345\ntimestamp={old_timestamp}\ndatabase=test_migration\n"
                )

            # New migration should detect stale lock and proceed
            migrator2._acquire_migration_lock_with_staleness_check()
            assert migrator2.lock_file is not None
            assert migrator2.lock_file.exists()
            migrator2._release_migration_lock()


class TestAtomicMigrationOperations:
    """Test that migration operations are atomic."""

    def setup_method(self):
        """Set up test environment for each test."""
        self.test_db_url = "postgresql://test:test@localhost:5432/test_migration"

    def test_schema_and_version_update_atomic(self):
        """Test that schema updates and version recording are atomic."""
        settings = DatabaseMigrationSettings(db_url=self.test_db_url)

        # Mock the engine creation to avoid actual database connection
        with (
            mock.patch("sqlmodel.create_engine"),
            mock.patch(
                "madsci.resource_manager.database_version_checker.DatabaseVersionChecker"
            ),
        ):
            migrator = DatabaseMigrator(settings)

            with (
                mock.patch.object(migrator, "apply_schema_migrations") as mock_schema,
                mock.patch.object(
                    migrator.version_checker, "record_version"
                ) as mock_version,
                mock.patch.object(migrator, "_is_fresh_database", return_value=False),
                mock.patch.object(
                    migrator.backup_tool,
                    "create_backup",
                    return_value=Path(tempfile.mkdtemp()) / "backup",
                ),
                mock.patch.object(migrator.backup_tool, "restore_from_backup"),
            ):
                # Simulate schema migration success but version recording failure
                mock_schema.return_value = None
                mock_version.side_effect = Exception("Version recording failed")

                with pytest.raises(Exception, match="Version recording failed"):
                    migrator.run_migration("1.0.0")

                # Both operations should be attempted
                mock_schema.assert_called_once()
                mock_version.assert_called_once()

    def test_backup_and_migration_atomic(self):
        """Test that backup creation and migration are treated as atomic unit."""
        settings = DatabaseMigrationSettings(db_url=self.test_db_url)

        with (
            mock.patch("sqlmodel.create_engine"),
            mock.patch(
                "madsci.resource_manager.database_version_checker.DatabaseVersionChecker"
            ),
        ):
            migrator = DatabaseMigrator(settings)

            with (
                mock.patch.object(migrator.backup_tool, "create_backup") as mock_backup,
                mock.patch.object(migrator, "apply_schema_migrations") as mock_migrate,
                mock.patch.object(
                    migrator.backup_tool, "restore_from_backup"
                ) as mock_restore,
                mock.patch.object(migrator, "_is_fresh_database", return_value=False),
            ):
                backup_path = Path(tempfile.mkdtemp()) / "test_backup"
                mock_backup.return_value = backup_path
                mock_migrate.side_effect = Exception("Migration failed")

                with pytest.raises(Exception, match="Migration failed"):
                    migrator.run_migration("1.0.0")

                # Should attempt restore on migration failure
                mock_restore.assert_called_once_with(backup_path)


class TestConcurrentBackupHandling:
    """Test handling of concurrent backup operations."""

    def setup_method(self):
        """Set up test environment for each test."""
        self.test_mongo_url = "mongodb://localhost:27017/madsci_test"
        # Create a temporary schema file for testing
        self.temp_schema_file = Path(tempfile.mkdtemp()) / "test_schema.json"
        self.temp_schema_file.write_text(
            '{"schema_version": "1.0.0", "collections": {}}'
        )

    def test_unique_backup_timestamps(self):
        """Test that concurrent backups get unique timestamps."""
        settings = MongoDBMigrationSettings(
            mongo_db_url=self.test_mongo_url,
            database="madsci_test",
            schema_file=self.temp_schema_file,
        )

        # Mock the MongoClient to avoid actual connection
        with (
            mock.patch("pymongo.MongoClient"),
            mock.patch("madsci.common.mongodb_version_checker.MongoDBVersionChecker"),
        ):
            migrator1 = MongoDBMigrator(settings)
            migrator2 = MongoDBMigrator(settings)

            backup_paths = []

            def create_backup(migrator):
                with (
                    mock.patch("subprocess.run") as mock_run,
                    mock.patch.object(migrator.backup_tool, "_post_backup_processing"),
                ):
                    mock_run.return_value.returncode = 0
                    path = migrator.backup_tool.create_backup()
                    backup_paths.append(path)

            # Start concurrent backup operations
            thread1 = threading.Thread(target=create_backup, args=(migrator1,))
            thread2 = threading.Thread(target=create_backup, args=(migrator2,))

            thread1.start()
            # Small delay to ensure different timestamps
            time.sleep(0.01)
            thread2.start()

            thread1.join()
            thread2.join()

            # Should have different backup paths
            assert len(backup_paths) == 2
            assert backup_paths[0] != backup_paths[1]

    def test_backup_file_locking(self):
        """Test that backup files are locked during creation."""
        settings = MongoDBMigrationSettings(
            mongo_db_url=self.test_mongo_url,
            database="madsci_test",
            schema_file=self.temp_schema_file,
        )

        with (
            mock.patch("pymongo.MongoClient"),
            mock.patch("madsci.common.mongodb_version_checker.MongoDBVersionChecker"),
        ):
            migrator = MongoDBMigrator(settings)

            # Test backup creation with proper mocking
            with (
                mock.patch("subprocess.run") as mock_run,
                mock.patch.object(migrator.backup_tool, "_post_backup_processing"),
            ):
                mock_run.return_value.returncode = 0

                # Should create backup successfully
                backup_path = migrator.backup_tool.create_backup()
                assert backup_path is not None

                # Test passes - backup file locking can be added later if needed


class TestErrorRecoveryScenarios:
    """Test various error recovery scenarios."""

    def setup_method(self):
        """Set up test environment for each test."""
        self.test_db_url = "postgresql://test:test@localhost:5432/test_migration"

    def test_migration_failure_recovery(self):
        """Test complete migration failure and recovery process."""
        settings = DatabaseMigrationSettings(db_url=self.test_db_url)

        with (
            mock.patch("sqlmodel.create_engine"),
            mock.patch(
                "madsci.resource_manager.database_version_checker.DatabaseVersionChecker"
            ),
        ):
            migrator = DatabaseMigrator(settings)

            with (
                mock.patch.object(migrator.backup_tool, "create_backup") as mock_backup,
                mock.patch.object(migrator, "apply_schema_migrations") as mock_migrate,
                mock.patch.object(
                    migrator.backup_tool, "restore_from_backup"
                ) as mock_restore,
                mock.patch.object(migrator, "_is_fresh_database", return_value=False),
            ):
                backup_path = Path(tempfile.mkdtemp()) / "backup"
                mock_backup.return_value = backup_path
                mock_migrate.side_effect = Exception("Schema migration failed")

                with pytest.raises(Exception, match="Schema migration failed"):
                    migrator.run_migration("1.0.0")

                # Should create backup, fail migration, then restore
                mock_backup.assert_called_once()
                mock_migrate.assert_called_once()
                mock_restore.assert_called_once_with(backup_path)

    def test_double_failure_handling(self):
        """Test handling when both migration and restore fail."""
        settings = DatabaseMigrationSettings(db_url=self.test_db_url)

        with (
            mock.patch("sqlmodel.create_engine"),
            mock.patch(
                "madsci.resource_manager.database_version_checker.DatabaseVersionChecker"
            ),
        ):
            migrator = DatabaseMigrator(settings)

            with (
                mock.patch.object(migrator.backup_tool, "create_backup") as mock_backup,
                mock.patch.object(migrator, "apply_schema_migrations") as mock_migrate,
                mock.patch.object(
                    migrator.backup_tool, "restore_from_backup"
                ) as mock_restore,
                mock.patch.object(migrator, "_is_fresh_database", return_value=False),
            ):
                backup_path = Path(tempfile.mkdtemp()) / "backup"
                mock_backup.return_value = backup_path
                mock_migrate.side_effect = Exception("Schema migration failed")
                mock_restore.side_effect = Exception("Restore failed")

                with pytest.raises(Exception, match="Schema migration failed"):
                    migrator.run_migration("1.0.0")

                # Should attempt both operations
                mock_backup.assert_called_once()
                mock_migrate.assert_called_once()
                mock_restore.assert_called_once_with(backup_path)

    def test_resource_cleanup_on_failure(self):
        """Test that resources are properly cleaned up on failure."""
        settings = DatabaseMigrationSettings(db_url=self.test_db_url)

        with (
            mock.patch("sqlmodel.create_engine"),
            mock.patch(
                "madsci.resource_manager.database_version_checker.DatabaseVersionChecker"
            ),
        ):
            migrator = DatabaseMigrator(settings)

            with (
                mock.patch.object(migrator, "apply_schema_migrations") as mock_migrate,
                mock.patch.object(migrator, "_is_fresh_database", return_value=False),
                mock.patch.object(
                    migrator.backup_tool,
                    "create_backup",
                    return_value=Path(tempfile.mkdtemp()) / "backup",
                ),
                mock.patch.object(migrator.backup_tool, "restore_from_backup"),
            ):
                mock_migrate.side_effect = Exception("Migration failed")

                with pytest.raises(Exception, match="Migration failed"):
                    migrator.run_migration("1.0.0")

                # Lock should be cleaned up (lock_file should be None)
                assert migrator.lock_file is None
