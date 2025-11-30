"""Standalone PostgreSQL backup and restore tool for MADSci."""

import os
import subprocess
import threading
import urllib.parse as urlparse
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from types import TracebackType

from madsci.client.event_client import EventClient
from madsci.common.backup_tools.backup_manager import BackupManager
from madsci.common.backup_tools.backup_validator import BackupValidator
from madsci.common.backup_tools.base_backup import AbstractBackupTool, BackupInfo
from madsci.common.types.backup_types import PostgreSQLBackupSettings


class BackupLockManager:
    """Manages exclusive locks for backup operations."""

    def __init__(self) -> None:
        """Initialize the backup lock manager."""
        self._locks: Dict[str, threading.Lock] = {}
        self._lock_creation_lock = threading.Lock()

    def acquire_lock(self, db_url: str) -> "BackupLockContext":
        """Acquire lock for a specific database URL."""
        return BackupLockContext(self, db_url)

    def _get_lock(self, db_url: str) -> threading.Lock:
        """Get or create lock for database URL."""
        with self._lock_creation_lock:
            if db_url not in self._locks:
                self._locks[db_url] = threading.Lock()
            return self._locks[db_url]


class BackupLockContext:
    """Context manager for database backup locks."""

    def __init__(self, lock_manager: BackupLockManager, db_url: str) -> None:
        """Initialize the backup lock context."""
        self.lock_manager = lock_manager
        self.db_url = db_url
        self.lock = lock_manager._get_lock(db_url)

    def __enter__(self) -> "BackupLockContext":
        """Acquire the lock."""
        self.lock.acquire()
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional["TracebackType"],
    ) -> None:
        """Release the lock."""
        self.lock.release()


class PostgreSQLBackupTool(AbstractBackupTool):
    """Standalone PostgreSQL backup and restore tool."""

    def __init__(
        self, settings: PostgreSQLBackupSettings, logger: Optional[EventClient] = None
    ) -> None:
        """
        Initialize PostgreSQL backup tool.

        Args:
            settings: PostgreSQL backup configuration
            logger: Optional event client for logging
        """
        self.settings = settings
        self.logger = logger or EventClient()
        self.backup_dir = self._setup_backup_dir()
        self.validator = BackupValidator()
        self.manager = BackupManager()
        self._lock_manager = BackupLockManager()

    def _setup_backup_dir(self) -> Path:
        """Create and return the backup directory."""
        backup_dir = Path(self.settings.backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir

    def _parse_db_url(self) -> Dict[str, str]:
        """Parse database URL into components."""
        parsed = urlparse.urlparse(self.settings.db_url)

        return {
            "host": parsed.hostname or "localhost",
            "port": str(parsed.port or 5432),
            "user": parsed.username or "postgres",
            "password": parsed.password or "",
            "database": parsed.path.lstrip("/") or "postgres",
        }

    def _build_pg_dump_command(
        self, backup_path: Path, backup_format: str
    ) -> List[str]:
        """Build pg_dump command for backup creation."""
        db_info = self._parse_db_url()

        cmd = [
            "pg_dump",
            "-h",
            db_info["host"],
            "-p",
            db_info["port"],
            "-U",
            db_info["user"],
            "-d",
            db_info["database"],
            "--no-password",
            "--verbose",
        ]

        # Add format-specific options
        if backup_format == "custom":
            cmd.extend(["--format=custom", "--file", str(backup_path)])
        elif backup_format == "plain":
            cmd.extend(["--format=plain", "--file", str(backup_path)])
        elif backup_format == "directory":
            cmd.extend(["--format=directory", "--file", str(backup_path)])
        elif backup_format == "tar":
            cmd.extend(["--format=tar", "--file", str(backup_path)])
        else:
            # Default to custom format
            cmd.extend(["--format=custom", "--file", str(backup_path)])

        # Add compression if enabled
        if self.settings.compression and backup_format in ["custom", "tar"]:
            cmd.append("--compress=6")

        return cmd

    def _build_pg_restore_command(
        self, backup_path: Path, target_db: Optional[str] = None
    ) -> List[str]:
        """Build pg_restore command for backup restoration."""
        db_info = self._parse_db_url()

        # Use target_db if provided, otherwise use original database
        database = target_db or db_info["database"]

        return [
            "pg_restore",
            "-h",
            db_info["host"],
            "-p",
            db_info["port"],
            "-U",
            db_info["user"],
            "-d",
            database,
            "--no-password",
            "--verbose",
            "--clean",
            "--if-exists",
            str(backup_path),
        ]

    def _execute_pg_dump(self, backup_path: Path) -> None:
        """Execute pg_dump command to create backup."""
        db_info = self._parse_db_url()

        # Set PGPASSWORD environment variable for pg_dump
        env = os.environ.copy()
        if db_info["password"]:
            env["PGPASSWORD"] = db_info["password"]

        cmd = self._build_pg_dump_command(backup_path, self.settings.backup_format)

        try:
            self.logger.info(f"Creating database backup: {backup_path}")
            # Using subprocess with PostgreSQL tools - command is constructed safely
            result = subprocess.run(  # noqa: S603
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True,
                timeout=3600,  # 1 hour timeout
            )

            if result.returncode == 0:
                self.logger.info(
                    f"Database backup completed successfully: {backup_path}"
                )
            else:
                raise RuntimeError(
                    f"pg_dump failed with return code {result.returncode}: {result.stderr}"
                )

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Backup failed: {e.stderr}")
            raise RuntimeError(f"Database backup failed: {e}") from e
        except subprocess.TimeoutExpired as e:
            self.logger.error("Backup timed out after 1 hour")
            raise RuntimeError("Database backup timed out") from e
        except FileNotFoundError as e:
            raise RuntimeError(
                "pg_dump command not found. Please ensure PostgreSQL client tools are installed."
            ) from e

    def _create_backup_metadata(self, backup_path: Path) -> None:
        """Create metadata file for backup."""
        # Create base metadata using validator
        metadata = self.validator.create_backup_metadata(
            backup_path=backup_path,
            database_version=self._get_database_version(),
            backup_type="postgresql",
            additional_info={
                "backup_format": self.settings.backup_format,
                "compression": self.settings.compression,
            },
        )

        # Save metadata to file
        metadata_path = self.validator.save_metadata(backup_path, metadata)
        self.logger.info(f"Created backup metadata: {metadata_path}")

        # Save checksum to separate file (required for validation)
        checksum = metadata["checksum"]
        checksum_path = self.validator.save_checksum(backup_path, checksum)
        self.logger.info(f"Created backup checksum: {checksum_path}")

    def _get_database_version(self) -> Optional[str]:
        """Get PostgreSQL database version."""
        try:
            db_info = self._parse_db_url()
            env = os.environ.copy()
            if db_info["password"]:
                env["PGPASSWORD"] = db_info["password"]

            cmd = [
                "psql",
                "-h",
                db_info["host"],
                "-p",
                db_info["port"],
                "-U",
                db_info["user"],
                "-d",
                db_info["database"],
                "--no-password",
                "-t",
                "-c",
                "SELECT version();",
            ]

            # Using subprocess with PostgreSQL tools - command is constructed safely
            result = subprocess.run(  # noqa: S603
                cmd, env=env, capture_output=True, text=True, check=True, timeout=30
            )

            return result.stdout.strip() if result.returncode == 0 else None

        except Exception as e:
            self.logger.warning(f"Failed to get database version: {e}")
            return None

    def _generate_backup_path(self, name_suffix: Optional[str] = None) -> Path:
        """Generate backup file path based on format and timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"_{name_suffix}" if name_suffix else ""

        # Determine file extension based on format
        if self.settings.backup_format == "directory":
            backup_filename = f"postgres_backup_{timestamp}{suffix}"
        elif self.settings.backup_format == "tar":
            backup_filename = f"postgres_backup_{timestamp}{suffix}.tar"
        elif self.settings.backup_format == "plain":
            backup_filename = f"postgres_backup_{timestamp}{suffix}.sql"
        else:  # custom format
            backup_filename = f"postgres_backup_{timestamp}{suffix}.dump"

        return self.backup_dir / backup_filename

    def _cleanup_failed_backup(self, backup_path: Path) -> None:
        """Clean up files from a failed backup operation."""
        if backup_path.exists():
            if backup_path.is_dir():
                # Remove directory and contents
                for item in backup_path.rglob("*"):
                    if item.is_file():
                        item.unlink()
                for item in sorted(backup_path.rglob("*"), reverse=True):
                    if item.is_dir():
                        item.rmdir()
                backup_path.rmdir()
            else:
                backup_path.unlink()

        # Also remove metadata if it exists
        metadata_path = backup_path.with_suffix(".metadata.json")
        if metadata_path.exists():
            metadata_path.unlink()

    def create_backup(self, name_suffix: Optional[str] = None) -> Path:
        """
        Create a backup and return the backup path.

        Args:
            name_suffix: Optional suffix to append to backup name

        Returns:
            Path to the created backup
        """
        backup_path = self._generate_backup_path(name_suffix)

        with self._lock_manager.acquire_lock(self.settings.db_url):
            try:
                # Create the backup
                self._execute_pg_dump(backup_path)

                # Create backup metadata (must be done before validation)
                self._create_backup_metadata(backup_path)

                # Validate backup integrity if requested
                if (
                    self.settings.validate_integrity
                    and not self.validate_backup_integrity(backup_path)
                ):
                    raise RuntimeError("Backup integrity validation failed")

                # Rotate old backups if limit is set
                if self.settings.max_backups > 0:
                    self.manager.rotate_backups(
                        self.backup_dir, self.settings.max_backups
                    )

                return backup_path

            except Exception as e:
                # Cleanup failed backup
                self._cleanup_failed_backup(backup_path)
                raise RuntimeError(f"Backup creation failed: {e}") from e

    def restore_from_backup(
        self, backup_path: Path, target_db: Optional[str] = None
    ) -> None:
        """
        Restore database from backup.

        Args:
            backup_path: Path to the backup to restore from
            target_db: Optional target database name (uses default if None)
        """
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        # Validate backup before restore
        if not self.validate_backup_integrity(backup_path):
            raise RuntimeError(f"Backup integrity validation failed: {backup_path}")

        db_info = self._parse_db_url()
        env = os.environ.copy()
        if db_info["password"]:
            env["PGPASSWORD"] = db_info["password"]

        try:
            self.logger.info(f"Restoring database from backup: {backup_path}")

            # Determine restore method based on backup format
            if backup_path.suffix == ".sql" or self.settings.backup_format == "plain":
                # Use psql for plain SQL format
                database = target_db or db_info["database"]
                cmd = [
                    "psql",
                    "-h",
                    db_info["host"],
                    "-p",
                    db_info["port"],
                    "-U",
                    db_info["user"],
                    "-d",
                    database,
                    "--no-password",
                    "-f",
                    str(backup_path),
                ]
            else:
                # Use pg_restore for other formats
                cmd = self._build_pg_restore_command(backup_path, target_db)

            # Using subprocess with PostgreSQL tools - command is constructed safely
            result = subprocess.run(  # noqa: S603
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True,
                timeout=3600,  # 1 hour timeout
            )

            if result.returncode == 0:
                self.logger.info(
                    f"Database restore completed successfully from: {backup_path}"
                )
            else:
                raise RuntimeError(
                    f"Restore failed with return code {result.returncode}: {result.stderr}"
                )

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Restore failed: {e.stderr}")
            raise RuntimeError(f"Database restore failed: {e}") from e
        except subprocess.TimeoutExpired as e:
            self.logger.error("Restore timed out after 1 hour")
            raise RuntimeError("Database restore timed out") from e
        except FileNotFoundError as e:
            tool = "psql" if backup_path.suffix == ".sql" else "pg_restore"
            raise RuntimeError(
                f"{tool} command not found. Please ensure PostgreSQL client tools are installed."
            ) from e

    def validate_backup_integrity(self, backup_path: Path) -> bool:
        """
        Validate backup integrity.

        Args:
            backup_path: Path to the backup to validate

        Returns:
            True if backup is valid and restorable, False otherwise
        """
        try:
            # Check if backup file exists
            if not backup_path.exists():
                self.logger.warning(f"Backup file not found: {backup_path}")
                return False

            # Check if backup file has content
            if backup_path.is_file() and backup_path.stat().st_size == 0:
                self.logger.warning(f"Backup file is empty: {backup_path}")
                return False

            # Validate using comprehensive backup validation
            is_valid, validation_result = self.validator.validate_backup_comprehensive(
                backup_path, expected_backup_type="postgresql"
            )

            if not is_valid:
                self.logger.warning(
                    f"Backup validation failed for {backup_path}: {validation_result}"
                )

            return is_valid

        except Exception as e:
            self.logger.error(f"Backup validation failed: {e}")
            return False

    def list_available_backups(self) -> List[BackupInfo]:
        """
        List available backups with metadata.

        Returns:
            List of BackupInfo objects for available backups
        """
        try:
            all_backups = self.manager.list_backups(self.backup_dir)
            # Filter for PostgreSQL backups only
            return [
                backup for backup in all_backups if backup.backup_type == "postgresql"
            ]
        except Exception as e:
            self.logger.error(f"Failed to list backups: {e}")
            return []

    def delete_backup(self, backup_path: Path) -> None:
        """
        Delete a specific backup.

        Args:
            backup_path: Path to the backup to delete
        """
        try:
            if backup_path.exists():
                if backup_path.is_dir():
                    # Remove directory and contents
                    for item in backup_path.rglob("*"):
                        if item.is_file():
                            item.unlink()
                    for item in sorted(backup_path.rglob("*"), reverse=True):
                        if item.is_dir():
                            item.rmdir()
                    backup_path.rmdir()
                else:
                    backup_path.unlink()

                self.logger.info(f"Deleted backup: {backup_path}")

            # Also delete metadata file
            metadata_path = backup_path.with_suffix(".metadata.json")
            if metadata_path.exists():
                metadata_path.unlink()
                self.logger.info(f"Deleted backup metadata: {metadata_path}")

        except Exception as e:
            self.logger.error(f"Failed to delete backup {backup_path}: {e}")
            raise RuntimeError(f"Failed to delete backup: {e}") from e
