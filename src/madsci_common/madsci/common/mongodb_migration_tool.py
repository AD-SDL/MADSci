"""MongoDB migration tool for MADSci databases with backup, schema management, and CLI."""

import hashlib
import json
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from madsci.client.event_client import EventClient
from madsci.common.mongodb_version_checker import MongoDBVersionChecker
from madsci.common.types.mongodb_migration_types import (
    IndexDefinition,
    MongoDBMigrationSettings,
    MongoDBSchema,
)
from pydantic import AnyUrl
from pymongo import MongoClient


class MongoDBMigrator:
    """Handles MongoDB schema migrations for MADSci with backup and restore capabilities."""

    def __init__(
        self,
        settings: MongoDBMigrationSettings,
        logger: Optional[EventClient] = None,
    ) -> None:
        """
        Initialize the MongoDB migrator.

        Args:
            settings: Migration configuration settings
            logger: Optional logger instance
        """
        self.settings = settings
        self.db_url = str(settings.mongo_db_url)
        self.database_name = settings.database
        self.schema_file_path = settings.get_effective_schema_file_path()
        self.logger = logger or EventClient()

        # Initialize MongoDB connection
        self.client = MongoClient(self.db_url)
        self.database = self.client[self.database_name]

        # Use configured backup directory (with ~ expansion)
        raw_backup = Path(self.settings.backup_dir)
        self.backup_dir = (
            raw_backup if raw_backup.is_absolute() else Path.cwd() / raw_backup
        )
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Using backup directory: {self.backup_dir}")
        # Initialize version checker
        self.version_checker = MongoDBVersionChecker(
            db_url=self.db_url,
            database_name=self.database_name,
            schema_file_path=str(self.schema_file_path),
            backup_dir=str(self.backup_dir),
            logger=self.logger,
        )

    @property
    def parsed_db_url(self) -> AnyUrl:
        """Parse MongoDB connection URL using pydantic AnyUrl."""
        return self.settings.mongo_db_url

    def __del__(self) -> None:
        """Cleanup MongoDB client and version checker resources."""
        if hasattr(self, "version_checker") and self.version_checker:
            # Version checker now has its own __del__ method
            pass
        if hasattr(self, "client") and self.client:
            self.client.close()
            if hasattr(self, "logger") and self.logger:
                self.logger.debug("MongoDB migrator client disposed")

    def load_expected_schema(self) -> MongoDBSchema:
        """Load the expected schema from the schema.json file."""
        try:
            if not self.schema_file_path.exists():
                raise FileNotFoundError(
                    f"Schema file not found: {self.schema_file_path}"
                )

            schema = MongoDBSchema.from_file(str(self.schema_file_path))
            self.logger.info(f"Loaded schema from {self.schema_file_path}")
            return schema

        except Exception as e:
            self.logger.error(f"Error loading schema file: {e}")
            raise RuntimeError(f"Cannot load schema file: {e}") from e

    def get_current_database_schema(self) -> MongoDBSchema:
        """Get the current database schema using Pydantic models."""
        try:
            current_version = self.version_checker.get_database_version()
            version_str = str(current_version) if current_version else "0.0.0"

            return MongoDBSchema.from_mongodb_database(
                database_name=self.database_name,
                mongo_client=self.client,
                schema_version=version_str,
            )

        except Exception as e:
            self.logger.error(f"Error getting current database schema: {e}")
            raise

    def create_backup(self) -> Path:
        """Create a backup of the current database using mongodump."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_filename = f"{self.database_name}_backup_{timestamp}"
        backup_path = self.backup_dir / backup_filename

        # Build mongodump command
        mongodump_cmd = ["mongodump"]

        # Add connection parameters
        if self.parsed_db_url.host:
            port = self.parsed_db_url.port or 27017
            mongodump_cmd.extend(["--host", f"{self.parsed_db_url.host}:{port}"])

        if self.parsed_db_url.username:
            mongodump_cmd.extend(["--username", self.parsed_db_url.username])

        if self.parsed_db_url.password:
            mongodump_cmd.extend(["--password", self.parsed_db_url.password])

        # Specify database and output directory
        mongodump_cmd.extend(["--db", self.database_name, "--out", str(backup_path)])

        try:
            self.logger.info(f"Creating database backup: {backup_path}")
            result = subprocess.run(  # noqa
                mongodump_cmd, capture_output=True, text=True, check=True
            )

            if result.returncode == 0:
                self.logger.info(
                    f"Database backup completed successfully: {backup_path}"
                )

                # Validate backup integrity
                self._validate_backup_integrity(backup_path)

                return backup_path
            raise RuntimeError(f"mongodump failed: {result.stderr}")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Backup failed: {e.stderr}")
            raise RuntimeError(f"Database backup failed: {e}") from e
        except FileNotFoundError as fe:
            raise RuntimeError(
                f"mongodump command not found. Please ensure MongoDB tools are installed. {fe}"
            ) from fe

    def restore_from_backup(self, backup_path: Path) -> None:
        """Restore database from a backup directory using mongorestore."""
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup directory not found: {backup_path}")

        # The backup path should contain a subdirectory with the database name
        db_backup_path = backup_path / self.database_name
        if not db_backup_path.exists():
            raise FileNotFoundError(f"Database backup not found in: {db_backup_path}")

        # Build mongorestore command
        mongorestore_cmd = ["mongorestore"]

        # Add connection parameters
        if self.parsed_db_url.host:
            port = self.parsed_db_url.port or 27017
            mongorestore_cmd.extend(["--host", f"{self.parsed_db_url.host}:{port}"])

        if self.parsed_db_url.username:
            mongorestore_cmd.extend(["--username", self.parsed_db_url.username])

        if self.parsed_db_url.password:
            mongorestore_cmd.extend(["--password", self.parsed_db_url.password])

        # Drop existing database and restore
        mongorestore_cmd.extend(
            [
                "--drop",  # Drop existing collections before restoring
                "--db",
                self.database_name,
                str(db_backup_path),
            ]
        )

        try:
            self.logger.info(f"Restoring database from backup: {backup_path}")
            result = subprocess.run(  # noqa
                mongorestore_cmd, capture_output=True, text=True, check=True
            )

            if result.returncode == 0:
                self.logger.info("Database restore completed successfully")
            else:
                raise RuntimeError(f"mongorestore failed: {result.stderr}")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Restore failed: {e.stderr}")
            raise RuntimeError(f"Database restore failed: {e}") from e

    def apply_schema_migrations(self) -> None:
        """Apply schema migrations based on the expected schema."""
        try:
            expected_schema = self.load_expected_schema()

            self.logger.info("Applying schema migrations...")

            for collection_name, collection_def in expected_schema.collections.items():
                self._ensure_collection_exists(collection_name)
                self._ensure_indexes_exist(collection_name, collection_def.indexes)

            self.version_checker.create_schema_versions_collection()

            self.logger.info("Schema migrations applied successfully")

        except Exception as e:
            self.logger.error(f"Schema migration failed: {traceback.format_exc()}")
            raise RuntimeError(f"Schema migration failed: {e}") from e

    def _ensure_collection_exists(self, collection_name: str) -> None:
        """Ensure a collection exists, create it if it doesn't."""
        try:
            if collection_name not in self.database.list_collection_names():
                self.database.create_collection(collection_name)
                self.logger.info(f"Created collection: {collection_name}")
            else:
                self.logger.info(f"Collection already exists: {collection_name}")
        except Exception as e:
            self.logger.error(f"Error creating collection {collection_name}: {e}")
            raise

    def _ensure_indexes_exist(
        self, collection_name: str, expected_indexes: List[Any]
    ) -> None:
        """Ensure all expected indexes exist on a collection."""
        try:
            collection = self.database[collection_name]
            existing_indexes = {idx["name"] for idx in collection.list_indexes()}

            for index_def in expected_indexes:
                # Handle both dict and IndexDefinition objects
                if isinstance(index_def, dict):
                    # Convert dict to IndexDefinition for consistent handling
                    index_definition = IndexDefinition(**index_def)
                else:
                    index_definition = index_def

                index_name = index_definition.name

                if index_name not in existing_indexes:
                    keys = index_definition.get_keys_as_tuples()
                    index_options = index_definition.to_mongo_format()

                    collection.create_index(keys, **index_options)
                    self.logger.info(
                        f"Created index: {index_name} on collection {collection_name}"
                    )
                else:
                    self.logger.info(
                        f"Index already exists: {index_name} on collection {collection_name}"
                    )

        except Exception as e:
            self.logger.error(
                f"Error ensuring indexes for collection {collection_name}: {e}"
            )
            raise

    def validate_schema(self) -> Dict[str, Any]:
        """
        Validate current database schema against expected schema.

        Returns:
            Dictionary with validation results and differences
        """
        try:
            expected_schema = self.load_expected_schema()
            current_schema = self.get_current_database_schema()

            differences = expected_schema.compare_with_database_schema(current_schema)

            has_differences = (
                bool(differences["missing_collections"])
                or bool(differences["extra_collections"])
                or bool(differences["collection_differences"])
            )

            return {
                "valid": not has_differences,
                "differences": differences,
                "expected_version": str(expected_schema.schema_version),
                "current_version": str(current_schema.schema_version),
            }

        except Exception as e:
            self.logger.error(f"Schema validation failed: {e}")
            raise

    def run_migration(self, target_version: Optional[str] = None) -> None:
        """Run the complete migration process."""
        try:
            # Use expected schema version as target if not specified
            if target_version is None:
                target_version = str(self.version_checker.get_expected_schema_version())

            expected_schema_version = self.version_checker.get_expected_schema_version()
            current_db_version = self.version_checker.get_database_version()

            self.logger.info(
                f"Starting migration of {self.database_name} to version {target_version}"
            )
            self.logger.info(f"Expected schema version: {expected_schema_version}")
            self.logger.info(
                f"Current database version: {current_db_version or 'None'}"
            )

            # ALWAYS CREATE BACKUP FIRST
            backup_path = self.create_backup()

            try:
                # ALWAYS apply schema migrations - this will create collections and indexes as needed
                self.apply_schema_migrations()

                # Record new version in our tracking system
                migration_notes = f"MongoDB schema migration from {current_db_version or 'unversioned'} to {target_version}"
                self.version_checker.record_version(target_version, migration_notes)

                self.logger.info(
                    f"Migration completed successfully to version {target_version}"
                )

            except Exception as migration_error:
                self.logger.error(f"Migration failed: {migration_error}")
                self.logger.info("Attempting to restore from backup...")

                try:
                    self.restore_from_backup(backup_path)
                    self.logger.info("Database restored from backup successfully")
                except Exception as restore_error:
                    self.logger.error(
                        f"CRITICAL: Backup restore also failed: {restore_error}"
                    )
                    self.logger.error("Manual intervention required!")

                raise migration_error

        except Exception as e:
            self.logger.error(f"Migration process failed: {e}")
            raise

    def _verify_backup_completion(self, backup_path: Path) -> bool:
        """Verify that MongoDB backup completed successfully."""
        if not backup_path.exists():
            return False

        # Check if backup directory contains database subdirectory
        db_backup_path = backup_path / self.database_name
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
        sha256_hash = hashlib.sha256()

        # Generate checksum based on all BSON files in the backup
        db_backup_path = backup_path / self.database_name
        bson_files = sorted(db_backup_path.glob("*.bson"))

        for bson_file in bson_files:
            with bson_file.open("rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)

        checksum = sha256_hash.hexdigest()

        # Save checksum to file
        checksum_file = backup_path / "backup.checksum"
        checksum_file.write_text(checksum)

        self.logger.info(f"Generated backup checksum: {checksum}")
        return checksum

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

    def _generate_backup_checksum_inline(self, backup_path: Path) -> str:
        """Generate checksum without saving to file (for validation)."""
        sha256_hash = hashlib.sha256()

        # Generate checksum based on all BSON files in the backup
        db_backup_path = backup_path / self.database_name
        bson_files = sorted(db_backup_path.glob("*.bson"))

        for bson_file in bson_files:
            with bson_file.open("rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)

        return sha256_hash.hexdigest()

    def _test_backup_restore(self, backup_path: Path) -> bool:
        """Test MongoDB backup by attempting restore to temporary database."""
        test_db_name = f"test_restore_{int(time.time())}"

        try:
            # Build mongorestore command for test database
            mongorestore_cmd = ["mongorestore"]

            # Add connection parameters
            if self.parsed_db_url.host:
                port = self.parsed_db_url.port or 27017
                mongorestore_cmd.extend(["--host", f"{self.parsed_db_url.host}:{port}"])

            if self.parsed_db_url.username:
                mongorestore_cmd.extend(["--username", self.parsed_db_url.username])

            if self.parsed_db_url.password:
                mongorestore_cmd.extend(["--password", self.parsed_db_url.password])

            # Restore to test database
            db_backup_path = backup_path / self.database_name
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
                test_client = MongoClient(self.db_url)
                test_client.drop_database(test_db_name)
                test_client.close()
            except Exception as e:
                self.logger.warning(
                    f"Failed to clean up test database {test_db_name}: {e}"
                )

    def _create_backup_metadata(self, backup_path: Path) -> None:
        """Create metadata file for MongoDB backup."""
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "database_version": self.version_checker.get_database_version(),
            "madsci_version": self.version_checker.get_expected_schema_version(),
            "backup_size": sum(
                f.stat().st_size for f in backup_path.rglob("*") if f.is_file()
            ),
            "checksum": self._generate_backup_checksum_inline(backup_path),
            "database_name": self.database_name,
            "collections_count": len(
                list((backup_path / self.database_name).glob("*.bson"))
            ),
        }

        metadata_file = backup_path / "backup_metadata.json"
        metadata_file.write_text(json.dumps(metadata, indent=2))

        self.logger.info(f"Created backup metadata: {metadata_file}")

    def _validate_backup_integrity(self, backup_path: Path) -> bool:
        """Perform comprehensive MongoDB backup validation."""
        self.logger.info(f"Validating backup integrity: {backup_path}")

        # Step 1: Verify backup completion
        if not self._verify_backup_completion(backup_path):
            raise RuntimeError(f"Backup completion verification failed: {backup_path}")

        # Step 2: Generate and save checksum
        self._generate_backup_checksum(backup_path)

        # Step 3: Test restorability
        if not self._test_backup_restore(backup_path):
            raise RuntimeError(f"Backup restore test failed: {backup_path}")

        # Step 4: Create metadata
        self._create_backup_metadata(backup_path)

        self.logger.info("Backup integrity validation passed")
        return True

    def _verify_restore_success(self, backup_path: Path) -> bool:
        """Verify that MongoDB restore operation was successful."""
        try:
            # Check that collections exist and have expected structure
            db_backup_path = backup_path / self.database_name
            bson_files = list(db_backup_path.glob("*.bson"))

            for bson_file in bson_files:
                collection_name = bson_file.stem
                # Verify collection exists in database
                if collection_name not in self.database.list_collection_names():
                    self.logger.error(
                        f"Collection {collection_name} not found after restore"
                    )
                    return False

                # Basic document count check (could be enhanced)
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

    def _get_available_backups(self) -> List[Path]:
        """Get list of available MongoDB backup directories."""
        if not self.backup_dir.exists():
            return []

        backups = []
        for item in self.backup_dir.iterdir():
            if (
                item.is_dir()
                and item.name.startswith("madsci_backup_")
                and (item / self.database_name).exists()
            ):
                backups.append(item)

        # Sort by modification time (newest first)
        backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return backups

    def _rotate_old_backups(self, max_backups: int = 10) -> None:
        """Remove old MongoDB backup directories according to retention policy."""
        backups = self._get_available_backups()

        if len(backups) <= max_backups:
            return

        # Remove excess backups (oldest first)
        backups_to_remove = backups[max_backups:]

        for backup_path in backups_to_remove:
            try:
                # Remove entire backup directory tree
                import shutil  # noqa: PLC0415

                shutil.rmtree(backup_path)
                self.logger.info(f"Removed old backup: {backup_path}")
            except Exception as e:
                self.logger.warning(f"Failed to remove old backup {backup_path}: {e}")


def handle_migration_commands(
    settings: MongoDBMigrationSettings,
    version_checker: MongoDBVersionChecker,
    migrator: MongoDBMigrator,
    logger: EventClient,
) -> None:
    """Handle different migration command options."""
    if settings.check_version:
        # Just check version compatibility
        needs_migration, expected_schema_version, db_version = (
            version_checker.is_migration_needed()
        )

        logger.info(f"Expected schema version: {expected_schema_version}")
        logger.info(f"Database version: {db_version or 'None'}")
        logger.info(f"Migration needed: {needs_migration}")

        if needs_migration:
            logger.info("Migration is required")
            sys.exit(1)  # Exit with error code if migration needed
        else:
            logger.info("No migration required")

    elif settings.restore_from:
        # Restore from backup
        backup_path = Path(settings.restore_from)
        migrator.restore_from_backup(backup_path)
        logger.info("Restore completed successfully")

    elif settings.backup_only:
        # Just create backup
        backup_path = migrator.create_backup()
        logger.info(f"Backup created: {backup_path}")

    else:
        # Run full migration
        migrator.run_migration(settings.target_version)
        logger.info("Migration completed successfully")


def main() -> None:  # noqa
    """Command line interface for the MongoDB migration tool."""
    logger = EventClient()

    try:
        settings = MongoDBMigrationSettings()

        logger.info(f"Using database: {settings.database}")
        logger.info(f"Using schema file: {settings.get_effective_schema_file_path()}")

        migrator = MongoDBMigrator(settings, logger)

        if getattr(settings, "validate_schema", False):
            validation_result = migrator.validate_schema()

            if validation_result["valid"]:
                logger.info(
                    "Schema validation passed - database matches expected schema"
                )
            else:
                logger.log_warning("Schema validation failed - differences detected:")
                diff = validation_result["differences"]

                if diff["missing_collections"]:
                    logger.log_warning(
                        f"Missing collections: {diff['missing_collections']}"
                    )

                if diff["extra_collections"]:
                    logger.log_warning(
                        f"Extra collections: {diff['extra_collections']}"
                    )

                if diff["collection_differences"]:
                    for coll_name, coll_diff in diff["collection_differences"].items():
                        logger.log_warning(f"Collection '{coll_name}' differences:")
                        if coll_diff["missing_indexes"]:
                            logger.log_warning(
                                f"  Missing indexes: {coll_diff['missing_indexes']}"
                            )
                        if coll_diff["extra_indexes"]:
                            logger.log_warning(
                                f"  Extra indexes: {coll_diff['extra_indexes']}"
                            )
                        if coll_diff["different_indexes"]:
                            logger.log_warning(
                                f"  Different indexes: {len(coll_diff['different_indexes'])}"
                            )

                sys.exit(1)
        else:
            handle_migration_commands(
                settings, migrator.version_checker, migrator, logger
            )

    except KeyboardInterrupt:
        logger.info("Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration tool failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    """Entry point for the migration tool."""
    main()
