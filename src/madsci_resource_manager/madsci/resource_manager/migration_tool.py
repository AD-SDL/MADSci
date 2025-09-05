"""Database migration tool for MADSci resources."""

import os
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from madsci.client.event_client import EventClient
from madsci.resource_manager.database_version_checker import DatabaseVersionChecker
from madsci.resource_manager.resource_tables import ResourceTable
from madsci.resource_manager.schema_version import SchemaVersionTable
from sqlalchemy import text
from sqlmodel import Session, create_engine


class DatabaseMigrator:
    """Handles database schema migrations for MADSci."""

    def __init__(self, db_url: str, logger: Optional[EventClient] = None):
        self.db_url = db_url
        self.logger = logger or EventClient()
        self.engine = create_engine(db_url)
        self.version_checker = DatabaseVersionChecker(db_url, logger)

        # Parse database connection details for backup
        self.backup_dir = self._get_backup_directory()

    def _get_backup_directory(self) -> Path:
        """Get the backup directory path."""
        repo_path = os.getenv("REPO_PATH", ".")
        backup_dir = Path(repo_path) / ".madsci" / "postgres" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir

    def _parse_db_url(self) -> dict:
        """Parse PostgreSQL connection details from database URL."""
        # postgresql://user:password@host:port/database
        import urllib.parse as urlparse

        parsed = urlparse.urlparse(self.db_url)
        return {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 5432,
            "user": parsed.username or "postgres",
            "password": parsed.password or "",
            "database": parsed.path.lstrip("/") if parsed.path else "resources",
        }

    def create_backup(self) -> Path:
        """Create a backup of the current database."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        db_info = self._parse_db_url()

        backup_filename = f"madsci_backup_{timestamp}.sql"
        backup_path = self.backup_dir / backup_filename

        # Set PGPASSWORD environment variable for pg_dump
        env = os.environ.copy()
        if db_info["password"]:
            env["PGPASSWORD"] = db_info["password"]

        pg_dump_cmd = [
            "pg_dump",
            "-h",
            db_info["host"],
            "-p",
            str(db_info["port"]),
            "-U",
            db_info["user"],
            "-d",
            db_info["database"],
            "--no-password",
            "--verbose",
            "--file",
            str(backup_path),
        ]

        try:
            self.logger.info(f"Creating database backup: {backup_path}")
            result = subprocess.run(
                pg_dump_cmd, env=env, capture_output=True, text=True, check=True
            )

            if result.returncode == 0:
                self.logger.info(
                    f"Database backup completed successfully: {backup_path}"
                )
                return backup_path
            raise RuntimeError(f"pg_dump failed: {result.stderr}")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Backup failed: {e.stderr}")
            raise RuntimeError(f"Database backup failed: {e.stderr}")
        except FileNotFoundError:
            raise RuntimeError(
                "pg_dump command not found. Please ensure PostgreSQL client tools are installed."
            )

    def restore_from_backup(self, backup_path: Path) -> None:
        """Restore database from a backup file."""
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        db_info = self._parse_db_url()

        # Set PGPASSWORD environment variable
        env = os.environ.copy()
        if db_info["password"]:
            env["PGPASSWORD"] = db_info["password"]

        # First, drop and recreate the database
        self._recreate_database(db_info)

        psql_cmd = [
            "psql",
            "-h",
            db_info["host"],
            "-p",
            str(db_info["port"]),
            "-U",
            db_info["user"],
            "-d",
            db_info["database"],
            "--no-password",
            "--file",
            str(backup_path),
        ]

        try:
            self.logger.info(f"Restoring database from backup: {backup_path}")
            result = subprocess.run(
                psql_cmd, env=env, capture_output=True, text=True, check=True
            )

            if result.returncode == 0:
                self.logger.info("Database restore completed successfully")
            else:
                raise RuntimeError(f"psql restore failed: {result.stderr}")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Restore failed: {e.stderr}")
            raise RuntimeError(f"Database restore failed: {e.stderr}")

    def _recreate_database(self, db_info: dict) -> None:
        """Drop and recreate the database for restore."""
        # Connect to postgres database to drop/create target database
        postgres_url = self.db_url.replace(f"/{db_info['database']}", "/postgres")
        postgres_engine = create_engine(postgres_url)

        with postgres_engine.connect() as conn:
            # Terminate existing connections to the target database
            conn.execute(
                text(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{db_info["database"]}'
                AND pid <> pg_backend_pid()
            """)
            )

            # Drop and recreate database
            conn.execute(text(f'DROP DATABASE IF EXISTS "{db_info["database"]}"'))
            conn.execute(text(f'CREATE DATABASE "{db_info["database"]}"'))
            conn.commit()

    def apply_schema_migrations(self, target_version: str) -> None:
        """Apply schema migrations to bring database up to target version."""
        try:
            with Session(self.engine) as session:
                self.logger.info("Applying schema migrations using SQLModel...")

                # Create all tables (this handles new tables and columns)
                ResourceTable.metadata.create_all(self.engine)
                SchemaVersionTable.metadata.create_all(self.engine)

                # Here you could add specific migration logic for complex changes
                # For now, we'll rely on SQLAlchemy's create_all to handle most cases

                self.logger.info("Schema migrations applied successfully")

        except Exception as e:
            self.logger.error(f"Schema migration failed: {traceback.format_exc()}")
            raise RuntimeError(f"Schema migration failed: {e}")

    def run_migration(self, target_version: Optional[str] = None) -> None:
        """Run the complete migration process."""
        try:
            # Determine target version
            if target_version is None:
                target_version = self.version_checker.get_current_madsci_version()

            current_db_version = self.version_checker.get_database_version()

            self.logger.info(f"Starting migration to version {target_version}")
            self.logger.info(
                f"Current database version: {current_db_version or 'None'}"
            )

            # Create backup
            backup_path = self.create_backup()

            try:
                # Apply migrations
                self.apply_schema_migrations(target_version)

                # Record new version
                migration_notes = f"Migrated from {current_db_version or 'unversioned'} to {target_version}"
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


def main():
    """Command line interface for the migration tool."""
    import argparse

    parser = argparse.ArgumentParser(description="MADSci Database Migration Tool")
    parser.add_argument(
        "--db-url",
        required=True,
        help="Database URL (e.g., postgresql://user:pass@localhost:5432/resources)",
    )
    parser.add_argument(
        "--target-version",
        help="Target version to migrate to (defaults to current MADSci version)",
    )
    parser.add_argument(
        "--backup-only",
        action="store_true",
        help="Only create a backup, do not run migration",
    )
    parser.add_argument(
        "--restore-from", help="Restore from specified backup file instead of migrating"
    )

    args = parser.parse_args()

    logger = EventClient()
    migrator = DatabaseMigrator(args.db_url, logger)

    try:
        if args.restore_from:
            backup_path = Path(args.restore_from)
            migrator.restore_from_backup(backup_path)
        elif args.backup_only:
            backup_path = migrator.create_backup()
            print(f"Backup created: {backup_path}")
        else:
            migrator.run_migration(args.target_version)

    except Exception as e:
        logger.error(f"Migration tool failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
