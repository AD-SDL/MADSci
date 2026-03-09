"""Database version checking and validation for MADSci."""

import importlib.metadata
from typing import Optional

from madsci.client.event_client import EventClient
from madsci.common.types.event_types import EventType
from madsci.resource_manager.resource_tables import SchemaVersionTable
from pydantic_extra_types.semantic_version import SemanticVersion
from sqlalchemy import inspect
from sqlmodel import Session, create_engine, select


class DatabaseVersionChecker:
    """Handles database version validation and checking."""

    def __init__(self, db_url: str, logger: Optional[EventClient] = None) -> None:
        """Initialize the DatabaseVersionChecker."""
        self.db_url = db_url
        self.logger = logger or EventClient()
        self.engine = create_engine(db_url)

    def __del__(self) -> None:
        """Cleanup database engine resources."""
        if hasattr(self, "engine") and self.engine:
            self.engine.dispose()
            if hasattr(self, "logger") and self.logger:
                self.logger.debug(
                    "Database version checker engine disposed",
                    event_type=EventType.LOG_DEBUG,
                )

    def get_current_madsci_version(self) -> str:
        """Get the current MADSci version from the package."""
        try:
            return importlib.metadata.version("madsci")
        except importlib.metadata.PackageNotFoundError as e:
            self.logger.error(
                "MADSci package not found in the current environment",
                event_type=EventType.MANAGER_ERROR,
                exc_info=True,
            )
            raise RuntimeError(
                "Cannot determine MADSci version: package not found. "
                "Please ensure MADSci is properly installed in the current environment."
            ) from e

    def get_database_version(self) -> Optional[str]:
        """Get the current database schema version."""
        try:
            with Session(self.engine) as session:
                # Check if schema version table exists
                inspector = inspect(self.engine)
                if "madsci_schema_version" not in inspector.get_table_names():
                    return None

                # Get the latest version entry
                statement = select(SchemaVersionTable).order_by(
                    SchemaVersionTable.applied_at.desc()
                )
                result = session.exec(statement).first()
                return result.version if result else None

        except Exception:
            self.logger.error(
                "Error getting database version",
                event_type=EventType.MANAGER_ERROR,
                exc_info=True,
            )
            return None

    def _build_migration_base_args(self) -> list[str]:
        # Do NOT include --backup-dir; let tool use its default
        return [
            "python",
            "-m",
            "madsci.resource_manager.migration_tool",
            "--db_url",
            f"'{self.db_url}'",
        ]

    def _bare_command(self) -> str:
        return " ".join(self._build_migration_base_args())

    def _docker_compose_command(self) -> str:
        # Template with a clear placeholder; no volume flags hardcoded here
        service = "<your_compose_service_name>"
        return f"docker compose run --rm {service} " + " ".join(
            self._build_migration_base_args()
        )

    def _both_commands(self) -> dict[str, str]:
        return {
            "bare_metal": self._bare_command(),
            "docker_compose": self._docker_compose_command(),
        }

    def is_version_tracked(self) -> bool:
        """
        Check if version tracking exists in the database.

        Returns True if the schema version table exists AND has at least one version record.
        Returns False if the table doesn't exist or is empty.
        """
        try:
            with Session(self.engine) as session:
                inspector = inspect(self.engine)
                if "madsci_schema_version" not in inspector.get_table_names():
                    return False

                # Check if table has any records
                statement = select(SchemaVersionTable)
                result = session.exec(statement).first()
                return result is not None

        except Exception:
            return False

    def versions_match(self, version1: str, version2: str) -> bool:
        """
        Check if two versions match based on major.minor comparison only.

        Ignores patch version and pre-release/build metadata.

        Examples:
            1.0.0 == 1.0.1  -> True (same major.minor)
            1.0.0 == 1.1.0  -> False (different minor)
            1.0.0 == 2.0.0  -> False (different major)
        """
        try:
            # For some reason release candidate versions are extracted as 0.0.0rc1 rather than 0.0.0-rc1
            v1_str = (
                version1.replace("rc", "-rc")
                .replace("alpha", "-alpha")
                .replace("beta", "-beta")
            )
            v2_str = (
                version2.replace("rc", "-rc")
                .replace("alpha", "-alpha")
                .replace("beta", "-beta")
            )

            v1 = SemanticVersion.parse(v1_str)
            v2 = SemanticVersion.parse(v2_str)

            # Compare only major and minor versions
            return v1.major == v2.major and v1.minor == v2.minor
        except Exception as e:
            self.logger.warning(
                "Could not parse versions for comparison",
                event_type=EventType.MANAGER_ERROR,
                version1=version1,
                version2=version2,
                error=str(e),
            )
            # If we can't parse, fall back to exact string comparison
            return version1 == version2

    def is_migration_needed(self) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Check if database migration is needed.

        Migration is needed if:
        1. Database exists but has no version tracking, OR
        2. Database has version tracking with major.minor version mismatch

        For fresh databases (no version tracking), migration is required to establish proper schema.

        Returns:
            tuple: (needs_migration, current_madsci_version, database_version)
        """
        current_version = self.get_current_madsci_version()
        db_version = self.get_database_version()

        # If version tracking doesn't exist, migration is needed to set up schema and tracking
        if not self.is_version_tracked():
            cmds = self._both_commands()
            self.logger.warning(
                "No version tracking found; database needs migration to establish schema",
                event_type=EventType.MANAGER_START,
            )
            self.logger.info(
                "To enable version tracking, run the migration tool using one of:",
                event_type=EventType.MANAGER_START,
            )
            self.logger.info(
                "Migration command (bare metal)",
                event_type=EventType.MANAGER_START,
                command=cmds["bare_metal"],
            )
            self.logger.info(
                "Migration command (docker compose)",
                event_type=EventType.MANAGER_START,
                command=cmds["docker_compose"],
            )
            # Optional: explain default backup location without printing a user path
            self.logger.info(
                "Backups default to .madsci/backups/postgresql, resolved via sentry walk-up.",
                event_type=EventType.MANAGER_START,
            )
            return True, current_version, None

        # Version IS tracked - check for mismatch using major.minor comparison
        if not self.versions_match(current_version, db_version):
            self.logger.warning(
                "Version mismatch (major.minor)",
                event_type=EventType.MANAGER_ERROR,
                madsci_version=current_version,
                database_version=db_version,
            )
            return True, current_version, db_version

        self.logger.info(
            "Database schema is compatible with installed MADSci",
            event_type=EventType.MANAGER_START,
            madsci_version=current_version,
            database_version=db_version,
        )
        return False, current_version, db_version

    def validate_or_fail(self) -> None:
        """
        Validate database version compatibility or raise an exception.
        This should be called during server startup.

        Behavior:
        - If completely fresh database (no tables) -> Auto-initialize
        - If version tracking exists and versions match -> Allow server to start
        - If version tracking exists/missing with mismatch -> Raise error, require migration
        """
        needs_migration, madsci_version, db_version = self.is_migration_needed()

        # Handle completely fresh database auto-initialization
        if needs_migration and db_version is None and self.is_fresh_database():
            self.logger.info(
                "Auto-initializing fresh database",
                event_type=EventType.MANAGER_START,
                madsci_version=madsci_version,
            )
            try:
                # Create schema version table and record initial version
                self.create_version_table_if_not_exists()
                self.record_version(
                    madsci_version,
                    f"Auto-initialized schema version {madsci_version}",
                )
                self.logger.info(
                    "Successfully auto-initialized database schema version",
                    event_type=EventType.MANAGER_START,
                    madsci_version=madsci_version,
                )
                return
            except Exception as e:
                self.logger.error(
                    "Failed to auto-initialize database",
                    event_type=EventType.MANAGER_ERROR,
                    error=str(e),
                    exc_info=True,
                )
                raise RuntimeError(f"Failed to auto-initialize database: {e}") from e

        if needs_migration:
            cmds = self._both_commands()
            message = (
                "Database schema version mismatch detected!\n"
                f"MADSci version: {madsci_version}\n"
                f"Database version: {db_version}\n"
                "Run one of:\n"
                f"  • Bare metal:     {cmds['bare_metal']}\n"
                f"  • Docker Compose: {cmds['docker_compose']}\n"
                "Note: backups default to .madsci/backups/postgresql, resolved via sentry walk-up."
            )
            self.logger.error(
                "Database schema version mismatch detected",
                event_type=EventType.MANAGER_ERROR,
            )
            self.logger.error(
                "Database migration required",
                event_type=EventType.MANAGER_ERROR,
                details=message,
            )
            raise RuntimeError(message)

    def create_version_table_if_not_exists(self) -> None:
        """Create the schema version table if it doesn't exist."""
        try:
            SchemaVersionTable.__table__.create(self.engine, checkfirst=True)
            self.logger.info(
                "Schema version table created",
                event_type=EventType.MANAGER_START,
            )
        except Exception as e:
            self.logger.error(
                "Error creating schema version table",
                event_type=EventType.MANAGER_ERROR,
                error=str(e),
                exc_info=True,
            )
            raise

    def record_version(
        self, version: str, migration_notes: Optional[str] = None
    ) -> None:
        """Record a new version in the database."""
        try:
            with Session(self.engine) as session:
                # Check if version already exists
                existing_version = session.exec(
                    select(SchemaVersionTable).where(
                        SchemaVersionTable.version == version
                    )
                ).first()

                if existing_version:
                    # Update existing record
                    existing_version.migration_notes = migration_notes
                    session.add(existing_version)
                    self.logger.info(
                        "Updated existing database version record",
                        event_type=EventType.MANAGER_START,
                        version=version,
                    )
                else:
                    # Create new record
                    version_entry = SchemaVersionTable(
                        version=version, migration_notes=migration_notes
                    )
                    session.add(version_entry)
                    self.logger.info(
                        "Recorded new database version",
                        event_type=EventType.MANAGER_START,
                        version=version,
                    )

                session.commit()
        except Exception as e:
            self.logger.error(
                "Error recording version",
                event_type=EventType.MANAGER_ERROR,
                error=str(e),
                exc_info=True,
            )
            raise

    def is_fresh_database(self) -> bool:
        """
        Check if this is a fresh database with no existing tables.

        Returns True if the database has no tables or only system tables.
        """
        try:
            inspector = inspect(self.engine)
            existing_tables = inspector.get_table_names()

            # Consider it fresh if no resource-related tables exist
            resource_tables = [
                "resource",
                "resource_history",
                "madsci_schema_version",
                "alembic_version",
            ]
            has_resource_tables = any(
                table in existing_tables for table in resource_tables
            )

            if not has_resource_tables:
                self.logger.info(
                    "No existing resource tables found; treating as fresh database",
                    event_type=EventType.MANAGER_START,
                )
                return True

            self.logger.info(
                "Found existing tables",
                event_type=EventType.MANAGER_START,
                tables=existing_tables,
            )
            return False

        except Exception as e:
            self.logger.warning(
                "Could not check database tables",
                event_type=EventType.MANAGER_ERROR,
                error=str(e),
                exc_info=True,
            )
            return False
