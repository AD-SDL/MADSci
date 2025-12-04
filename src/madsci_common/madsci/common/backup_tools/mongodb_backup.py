"""Standalone MongoDB backup and restore tool."""

import hashlib
import json
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from madsci.client.event_client import EventClient
from madsci.common.backup_tools.backup_manager import BackupManager
from madsci.common.backup_tools.backup_validator import BackupValidator
from madsci.common.backup_tools.base_backup import AbstractBackupTool, BackupInfo
from madsci.common.types.backup_types import MongoDBBackupSettings
from pymongo import MongoClient


class MongoDBBackupTool(AbstractBackupTool):
    """Standalone MongoDB backup and restore tool."""

    def __init__(
        self, settings: MongoDBBackupSettings, logger: Optional[EventClient] = None
    ) -> None:
        """
        Initialize MongoDB backup tool.

        Args:
            settings: MongoDB backup configuration settings
            logger: Optional logger instance
        """
        self.settings = settings
        self.logger = logger or EventClient()
        self.backup_dir = self._setup_backup_dir()
        self.validator = BackupValidator()
        self.manager = BackupManager()

        # Initialize MongoDB connection
        self.client = MongoClient(str(settings.mongo_db_url))
        self.database = self.client[settings.database]

    def _setup_backup_dir(self) -> Path:
        """Set up backup directory, creating it if it doesn't exist."""
        backup_dir = self.settings.backup_dir
        if not backup_dir.is_absolute():
            backup_dir = Path.cwd() / backup_dir

        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir

    def create_backup(self, name_suffix: Optional[str] = None) -> Path:
        """
        Create a MongoDB backup using mongodump.

        Args:
            name_suffix: Optional suffix to add to backup name

        Returns:
            Path to the created backup directory

        Raises:
            RuntimeError: If backup creation fails
        """
        backup_path = self._generate_backup_path(name_suffix)
        mongodump_cmd = self._build_mongodump_command(backup_path)

        # Execute mongodump command
        try:
            self._execute_backup_command(mongodump_cmd, backup_path)
        except FileNotFoundError as fe:
            raise RuntimeError(
                "mongodump command not found. Please ensure MongoDB tools are installed."
            ) from fe
        except subprocess.CalledProcessError as e:
            self._cleanup_failed_backup(backup_path, e)
            raise RuntimeError(f"Database backup failed: {e}") from e

        # Post-process backup (metadata, validation, rotation)
        try:
            self._post_backup_processing(backup_path)
        except Exception as e:
            self._cleanup_failed_backup(backup_path, e)
            raise RuntimeError(f"Backup post-processing failed: {e}") from e

        return backup_path

    def _generate_backup_path(self, name_suffix: Optional[str]) -> Path:
        """Generate backup path with timestamp and optional suffix."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        suffix = f"_{name_suffix}" if name_suffix else ""
        backup_filename = f"{self.settings.database}_backup_{timestamp}{suffix}"
        return self.backup_dir / backup_filename

    def _build_mongodump_command(self, backup_path: Path) -> List[str]:
        """Build the mongodump command with all necessary parameters."""
        mongodump_cmd = ["mongodump"]

        # Add connection parameters
        parsed_url = self.settings.mongo_db_url
        if parsed_url.host:
            port = parsed_url.port or 27017
            mongodump_cmd.extend(["--host", f"{parsed_url.host}:{port}"])

        if parsed_url.username:
            mongodump_cmd.extend(["--username", parsed_url.username])

        if parsed_url.password:
            mongodump_cmd.extend(["--password", parsed_url.password])

        # Specify database and output directory
        mongodump_cmd.extend(
            ["--db", self.settings.database, "--out", str(backup_path)]
        )

        # Add collection filters if specified
        if self.settings.collections:
            for collection in self.settings.collections:
                mongodump_cmd.extend(["--collection", collection])

        return mongodump_cmd

    def _execute_backup_command(
        self, mongodump_cmd: List[str], backup_path: Path
    ) -> None:
        """Execute the mongodump command and validate success."""
        # Ensure backup directory exists (mongodump requires parent directory to exist)
        backup_path.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Creating database backup: {backup_path}")
        result = subprocess.run(  # noqa: S603
            mongodump_cmd, capture_output=True, text=True, check=True
        )

        if result.returncode == 0:
            self.logger.info(f"Database backup completed successfully: {backup_path}")

            # Verify backup directory was created
            if not backup_path.exists():
                raise RuntimeError(
                    f"mongodump reported success but backup directory was not created: {backup_path}. "
                    f"This may indicate a connection issue or empty database."
                )

            # Verify database subdirectory exists
            db_backup_path = backup_path / self.settings.database
            if not db_backup_path.exists():
                # Check if database is empty
                try:
                    collections = list(self.database.list_collection_names())
                    if not collections:
                        raise RuntimeError(
                            f"Cannot backup database '{self.settings.database}': database is empty (no collections). "
                            f"MongoDB does not create backup files for empty databases."
                        )
                except RuntimeError:
                    # Re-raise our own RuntimeError about empty database
                    raise
                except Exception as e:
                    # Log connection errors but continue with generic message
                    self.logger.warning(f"Could not check if database is empty: {e}")

                raise RuntimeError(
                    f"mongodump created backup directory but database subdirectory is missing: {db_backup_path}. "
                    f"Check that database '{self.settings.database}' exists and is accessible."
                )
        else:
            raise RuntimeError(f"mongodump failed: {result.stderr}")

    def _post_backup_processing(self, backup_path: Path) -> None:
        """Handle post-backup validation, metadata creation, and rotation."""
        # Create metadata first (required for validation)
        self._create_backup_metadata(backup_path)

        # Validate backup integrity if enabled
        if self.settings.validate_integrity:
            self._validate_backup_integrity(backup_path)

        # Rotate old backups
        if self.settings.max_backups > 0:
            self.manager.rotate_backups(self.backup_dir, self.settings.max_backups)

    def _cleanup_failed_backup(self, backup_path: Path, error: Exception) -> None:
        """Clean up after a failed backup operation."""
        self.logger.error(f"Backup failed: {error}")
        if backup_path.exists():
            shutil.rmtree(backup_path)

    def restore_from_backup(
        self, backup_path: Path, target_db: Optional[str] = None
    ) -> None:
        """
        Restore database from a backup directory using mongorestore.

        Args:
            backup_path: Path to backup directory
            target_db: Optional target database name (defaults to original database)

        Raises:
            FileNotFoundError: If backup directory doesn't exist
            RuntimeError: If restore operation fails
        """
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup directory not found: {backup_path}")

        # The backup path should contain a subdirectory with the database name
        db_backup_path = backup_path / self.settings.database
        if not db_backup_path.exists():
            raise FileNotFoundError(f"Database backup not found in: {db_backup_path}")

        # Use target database if specified, otherwise use original database
        restore_db = target_db or self.settings.database

        # Build mongorestore command
        mongorestore_cmd = ["mongorestore"]

        # Add connection parameters
        parsed_url = self.settings.mongo_db_url
        if parsed_url.host:
            port = parsed_url.port or 27017
            mongorestore_cmd.extend(["--host", f"{parsed_url.host}:{port}"])

        if parsed_url.username:
            mongorestore_cmd.extend(["--username", parsed_url.username])

        if parsed_url.password:
            mongorestore_cmd.extend(["--password", parsed_url.password])

        # Drop existing database and restore
        mongorestore_cmd.extend(
            [
                "--drop",  # Drop existing collections before restoring
                "--db",
                restore_db,
                str(db_backup_path),
            ]
        )

        try:
            self.logger.info(f"Restoring database from backup: {backup_path}")
            result = subprocess.run(  # noqa: S603
                mongorestore_cmd, capture_output=True, text=True, check=True
            )

            if result.returncode == 0:
                self.logger.info("Database restore completed successfully")
                # Verify restore success
                if not self._verify_restore_success(backup_path):
                    raise RuntimeError("Restore verification failed")
            else:
                raise RuntimeError(f"mongorestore failed: {result.stderr}")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Restore failed: {e.stderr}")
            self._cleanup_failed_restore(backup_path)
            raise RuntimeError(f"Database restore failed: {e}") from e

    def validate_backup_integrity(self, backup_path: Path) -> bool:
        """
        Validate backup integrity using checksums and restore testing.

        Args:
            backup_path: Path to backup directory

        Returns:
            True if backup is valid, False otherwise
        """
        try:
            return self._validate_backup_integrity(backup_path)
        except Exception as e:
            self.logger.error(f"Backup validation failed: {e}")
            return False

    def list_available_backups(self) -> List[BackupInfo]:
        """
        List available backups with metadata.

        Returns:
            List of BackupInfo objects for available backups
        """
        backups = []

        if not self.backup_dir.exists():
            return backups

        for item in self.backup_dir.iterdir():
            if item.is_dir() and (item / self.settings.database).exists():
                # Try to load metadata
                metadata_file = item / "backup_metadata.json"
                if metadata_file.exists():
                    try:
                        metadata = json.loads(metadata_file.read_text())

                        backup_info = BackupInfo(
                            backup_path=item,
                            created_at=datetime.fromisoformat(metadata["timestamp"]),
                            database_version=metadata.get("database_version"),
                            backup_size=metadata["backup_size"],
                            checksum=metadata["checksum"],
                            backup_type="mongodb",
                            is_valid=self._check_backup_validity(item),
                        )
                        backups.append(backup_info)
                    except (json.JSONDecodeError, KeyError) as e:
                        self.logger.warning(f"Invalid metadata for backup {item}: {e}")

        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x.created_at, reverse=True)
        return backups

    def delete_backup(self, backup_path: Path) -> None:
        """
        Delete a specific backup directory.

        Args:
            backup_path: Path to backup directory to delete

        Raises:
            RuntimeError: If deletion fails
        """
        try:
            if backup_path.exists():
                shutil.rmtree(backup_path)
                self.logger.info(f"Deleted backup: {backup_path}")
            else:
                self.logger.warning(f"Backup path does not exist: {backup_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to delete backup {backup_path}: {e}") from e

    def _validate_backup_integrity(self, backup_path: Path) -> bool:
        """Perform comprehensive MongoDB backup validation."""
        self.logger.info(f"Validating backup integrity: {backup_path}")

        # Step 1: Verify backup completion
        if not self._verify_backup_completion(backup_path):
            raise RuntimeError(f"Backup completion verification failed: {backup_path}")

        # Step 2: Check existing checksum (if this is validation of existing backup)
        checksum_file = backup_path / "backup.checksum"
        if checksum_file.exists():
            # Validate existing checksum
            if not self._validate_backup_checksum(backup_path):
                raise RuntimeError(f"Backup checksum validation failed: {backup_path}")
        else:
            # Generate new checksum (if this is backup creation)
            self._generate_backup_checksum(backup_path)

        # Step 3: Test restorability
        if not self._test_backup_restore(backup_path):
            raise RuntimeError(f"Backup restore test failed: {backup_path}")

        self.logger.info("Backup integrity validation passed")
        return True

    def _verify_backup_completion(self, backup_path: Path) -> bool:
        """Verify that MongoDB backup completed successfully."""
        if not backup_path.exists():
            return False

        # Check if backup directory contains database subdirectory
        db_backup_path = backup_path / self.settings.database
        if not db_backup_path.exists():
            return False

        # Check if backup contains collection files
        bson_files = list(db_backup_path.glob("*.bson"))
        if not bson_files:
            self.logger.warning("No BSON files found in backup directory")
            return False

        # Check if backup contains metadata
        metadata_files = list(db_backup_path.glob("*.metadata.json"))
        if not metadata_files:
            self.logger.warning("No metadata files found in backup directory")

        self.logger.info(
            f"Backup verification successful: {len(bson_files)} collections backed up"
        )
        return True

    def _generate_backup_checksum(self, backup_path: Path) -> str:
        """Generate SHA256 checksum for MongoDB backup directory."""
        checksum = self._generate_backup_checksum_inline(backup_path)

        # Save checksum to file
        checksum_file = backup_path / "backup.checksum"
        checksum_file.write_text(checksum)

        self.logger.info(f"Generated backup checksum: {checksum}")
        return checksum

    def _generate_backup_checksum_inline(self, backup_path: Path) -> str:
        """Generate checksum without saving to file (for validation)."""
        sha256_hash = hashlib.sha256()

        # Generate checksum based on all BSON files in the backup
        db_backup_path = backup_path / self.settings.database
        bson_files = sorted(db_backup_path.glob("*.bson"))

        for bson_file in bson_files:
            with bson_file.open("rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)

        return sha256_hash.hexdigest()

    def _validate_backup_checksum(self, backup_path: Path) -> bool:
        """Validate MongoDB backup directory against its checksum."""
        checksum_file = backup_path / "backup.checksum"

        if not checksum_file.exists():
            self.logger.warning("No checksum file found for backup validation")
            return False

        try:
            expected_checksum = checksum_file.read_text().strip()
            actual_checksum = self._generate_backup_checksum_inline(backup_path)

            if expected_checksum == actual_checksum:
                self.logger.info("Backup checksum validation passed")
                return True

            self.logger.error(
                f"Backup checksum validation failed: expected {expected_checksum}, got {actual_checksum}"
            )
            return False

        except Exception as e:
            self.logger.error(f"Error validating backup checksum: {e}")
            return False

    def _test_backup_restore(self, backup_path: Path) -> bool:
        """Test MongoDB backup by attempting restore to temporary database."""
        test_db_name = f"test_restore_{int(time.time())}"

        try:
            # Build mongorestore command for test database
            mongorestore_cmd = ["mongorestore"]

            # Add connection parameters
            parsed_url = self.settings.mongo_db_url
            if parsed_url.host:
                port = parsed_url.port or 27017
                mongorestore_cmd.extend(["--host", f"{parsed_url.host}:{port}"])

            if parsed_url.username:
                mongorestore_cmd.extend(["--username", parsed_url.username])

            if parsed_url.password:
                mongorestore_cmd.extend(["--password", parsed_url.password])

            # Restore to test database
            db_backup_path = backup_path / self.settings.database
            mongorestore_cmd.extend(["--db", test_db_name, str(db_backup_path)])

            result = subprocess.run(  # noqa: S603
                mongorestore_cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=300,
            )

            success = result.returncode == 0
            if success:
                self.logger.info("Backup restore test successful")
            else:
                self.logger.error(f"Backup restore test failed: {result.stderr}")

            return success

        except Exception as e:
            self.logger.error(f"Error testing backup restore: {e}")
            return False
        finally:
            # Clean up test database
            try:
                test_client = MongoClient(str(self.settings.mongo_db_url))
                test_client.drop_database(test_db_name)
                test_client.close()
            except Exception as e:
                self.logger.warning(
                    f"Failed to clean up test database {test_db_name}: {e}"
                )

    def _create_backup_metadata(self, backup_path: Path) -> None:
        """Create metadata file for MongoDB backup."""
        checksum = self._generate_backup_checksum_inline(backup_path)

        metadata = {
            "timestamp": datetime.now().isoformat(),
            "database_version": None,  # MongoDB doesn't have schema versions like PostgreSQL
            "backup_size": sum(
                f.stat().st_size for f in backup_path.rglob("*") if f.is_file()
            ),
            "checksum": checksum,
            "database_name": self.settings.database,
            "collections_count": len(
                list((backup_path / self.settings.database).glob("*.bson"))
            ),
        }

        metadata_file = backup_path / "backup_metadata.json"
        metadata_file.write_text(json.dumps(metadata, indent=2))

        self.logger.info(f"Created backup metadata: {metadata_file}")

        # Save checksum to separate file (required for validation)
        checksum_file = backup_path / "backup.checksum"
        checksum_file.write_text(checksum)
        self.logger.info(f"Created backup checksum: {checksum_file}")

    def _verify_restore_success(self, backup_path: Path) -> bool:
        """Verify that MongoDB restore operation was successful."""
        try:
            # Check that collections exist and have expected structure
            db_backup_path = backup_path / self.settings.database
            bson_files = list(db_backup_path.glob("*.bson"))

            for bson_file in bson_files:
                collection_name = bson_file.stem
                # Verify collection exists in database
                if collection_name not in self.database.list_collection_names():
                    self.logger.error(
                        f"Collection {collection_name} not found after restore"
                    )
                    return False

                # Basic document count check
                doc_count = self.database[collection_name].count_documents({})
                self.logger.info(
                    f"Collection {collection_name} has {doc_count} documents after restore"
                )

            self.logger.info("Restore verification successful")
            return True

        except Exception as e:
            self.logger.error(f"Error verifying restore success: {e}")
            return False

    def _cleanup_failed_restore(self, backup_path: Path) -> None:  # noqa: ARG002
        """Cleanup after a failed MongoDB restore operation."""
        try:
            # Drop all collections to clean state
            for collection_name in self.database.list_collection_names():
                self.database.drop_collection(collection_name)
                self.logger.info(f"Dropped collection {collection_name} during cleanup")

            self.logger.info("Failed restore cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during failed restore cleanup: {e}")

    def _check_backup_validity(self, backup_path: Path) -> bool:
        """Check if a backup is valid by verifying its checksum."""
        try:
            return self._validate_backup_checksum(backup_path)
        except Exception:
            return False
