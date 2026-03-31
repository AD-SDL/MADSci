"""FOSS stack migration tool for MADSci.

Migrates data from the old proprietary infrastructure (MongoDB, Redis, MinIO)
to the new FOSS alternatives (FerretDB, Valkey, SeaweedFS).
"""

import shutil
import subprocess
import tempfile
import time
import urllib.parse as urlparse
from datetime import datetime
from os import environ
from pathlib import Path
from typing import ClassVar, Dict, List, Optional

from madsci.client.event_client import EventClient
from madsci.common.sentry import find_madsci_dir
from madsci.common.types.base_types import MadsciBaseModel, MadsciBaseSettings
from pydantic import AnyUrl, Field

# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


class FossMigrationStepResult(MadsciBaseModel):
    """Result of a single migration step."""

    step: str = Field(title="Step Name", description="Name of the migration step")
    success: bool = Field(title="Success", description="Whether the step succeeded")
    message: str = Field(title="Message", description="Human-readable result message")
    duration_seconds: float = Field(
        default=0.0,
        title="Duration",
        description="Wall-clock seconds the step took",
    )
    error: Optional[str] = Field(
        default=None,
        title="Error",
        description="Error details if the step failed",
    )
    details: Optional[dict] = Field(
        default=None,
        title="Details",
        description="Additional key-value details about the step",
    )


class FossMigrationReport(MadsciBaseModel):
    """Aggregate report for a full FOSS migration run."""

    started_at: datetime = Field(
        default_factory=datetime.now,
        title="Started At",
        description="When the migration started",
    )
    finished_at: Optional[datetime] = Field(
        default=None,
        title="Finished At",
        description="When the migration finished",
    )
    steps: List[FossMigrationStepResult] = Field(
        default_factory=list,
        title="Steps",
        description="Results for each migration step",
    )

    @property
    def all_succeeded(self) -> bool:
        """Return True if every step succeeded (False when no steps recorded)."""
        return bool(self.steps) and all(s.success for s in self.steps)

    @property
    def total_duration_seconds(self) -> float:
        """Total wall-clock duration of all steps."""
        return sum(s.duration_seconds for s in self.steps)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

# Default document databases to migrate (matches MADSci manager defaults).
DEFAULT_DOCUMENT_DBS: List[str] = [
    "madsci_events",
    "madsci_experiments",
    "madsci_data",
    "madsci_workcells",
]


class FossMigrationSettings(
    MadsciBaseSettings,
    env_file=(".env", "foss_migration.env"),
    yaml_file=("settings.yaml", "foss_migration.settings.yaml"),
    json_file=("settings.json", "foss_migration.settings.json"),
    env_prefix="FOSS_MIGRATION_",
):
    """Settings for the FOSS stack migration tool."""

    old_document_db_url: AnyUrl = Field(
        default="mongodb://localhost:27018/",
        title="Old Document DB URL",
        description="MongoDB connection URL for the old (source) database",
        json_schema_extra={"secret": True},
    )
    new_document_db_url: AnyUrl = Field(
        default="mongodb://madsci:madsci@localhost:27017/",
        title="New Document DB URL",
        description="FerretDB connection URL for the new (target) database",
        json_schema_extra={"secret": True},
    )

    old_postgres_url: str = Field(
        default="postgresql://madsci:madsci@localhost:5433/resources",
        title="Old PostgreSQL URL",
        description="PostgreSQL connection URL for the old (source) database",
        json_schema_extra={"secret": True},
    )
    new_postgres_url: str = Field(
        default="postgresql://madsci:madsci@localhost:5434/resources",
        title="New PostgreSQL URL",
        description="PostgreSQL connection URL for the new (target) database",
        json_schema_extra={"secret": True},
    )

    document_db_databases: List[str] = Field(
        default_factory=lambda: list(DEFAULT_DOCUMENT_DBS),
        title="Document Databases",
        description="List of document databases to migrate",
    )

    old_minio_url: AnyUrl = Field(
        default="http://localhost:9002/",
        title="Old MinIO URL",
        description="MinIO endpoint URL for the old (source) object storage",
    )
    new_seaweedfs_url: AnyUrl = Field(
        default="http://localhost:8333/",
        title="New SeaweedFS URL",
        description="SeaweedFS S3 endpoint URL for the new (target) object storage",
    )
    minio_access_key: str = Field(
        default="minioadmin",
        title="MinIO Access Key",
        json_schema_extra={"secret": True},
    )
    minio_secret_key: str = Field(
        default="minioadmin",
        title="MinIO Secret Key",
        json_schema_extra={"secret": True},
    )
    seaweedfs_access_key: str = Field(
        default="madsci",
        title="SeaweedFS Access Key",
        json_schema_extra={"secret": True},
    )
    seaweedfs_secret_key: str = Field(
        default="madsci",
        title="SeaweedFS Secret Key",
        json_schema_extra={"secret": True},
    )

    old_redis_host: str = Field(
        default="localhost",
        title="Old Redis Host",
        description="Redis host for the old (source) cache",
    )
    old_redis_port: int = Field(
        default=6380,
        title="Old Redis Port",
        description="Redis port for the old (source) cache (alternate port to avoid conflict with Valkey)",
    )
    old_redis_password: Optional[str] = Field(
        default=None,
        title="Old Redis Password",
        description="Redis password for the old (source) cache",
        json_schema_extra={"secret": True},
    )

    location_database_name: str = Field(
        default="madsci_locations",
        title="Location Database Name",
        description="Document database name for the Location Manager in the new FOSS stack",
    )

    backup_dir: Path = Field(
        default=Path(".madsci/backups/foss_migration"),
        title="Backup Directory",
        description="Directory for pre-migration backups",
    )

    compose_dir: Path = Field(
        default=Path(),
        title="Compose Directory",
        description="Directory containing Docker Compose files",
    )

    compose_files: List[str] = Field(
        default_factory=lambda: ["compose.infra.yaml"],
        title="Compose Files",
        description="Docker Compose files for the new FOSS infrastructure stack",
    )
    migration_compose_files: List[str] = Field(
        default_factory=lambda: ["compose.migration.yaml"],
        title="Migration Compose Files",
        description="Docker Compose overlay files for old infrastructure containers",
    )
    old_container_services: List[str] = Field(
        default_factory=lambda: [
            "madsci_old_mongodb",
            "madsci_old_postgres",
            "madsci_old_redis",
            "madsci_old_minio",
        ],
        title="Old Container Services",
        description="Docker Compose service names for old infrastructure containers to start during migration",
    )


# ---------------------------------------------------------------------------
# Migration tool
# ---------------------------------------------------------------------------


class FossMigrationTool:
    """Orchestrates migration from proprietary to FOSS infrastructure."""

    def __init__(
        self,
        settings: Optional[FossMigrationSettings] = None,
        logger: Optional[EventClient] = None,
    ) -> None:
        """Initialize the FOSS migration tool."""
        self.settings = settings or FossMigrationSettings()
        self.logger = logger or EventClient()
        # Resolve the .madsci/ directory via the canonical sentry walk-up
        self._madsci_dir = find_madsci_dir()

        # Warn if compose files cannot be found at the configured compose_dir
        compose_dir = self.settings.compose_dir
        missing = [
            f
            for f in self.settings.compose_files + self.settings.migration_compose_files
            if not (compose_dir / f).exists()
        ]
        if missing:
            self.logger.warning(
                "Some compose files not found in compose_dir; "
                "use --compose-dir or --skip-docker if this is intentional",
                compose_dir=str(compose_dir),
                missing_files=missing,
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _wait_for_service(
        check_fn: "callable",
        timeout: float = 30.0,
        interval: float = 2.0,
    ) -> bool:
        """Poll *check_fn* until it returns truthy or *timeout* expires.

        Args:
            check_fn: Zero-argument callable; should return truthy when the
                service is ready, and raise or return falsy otherwise.
            timeout: Maximum seconds to wait.
            interval: Seconds between poll attempts.

        Returns:
            ``True`` if the service became ready, ``False`` on timeout.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                if check_fn():
                    return True
            except Exception:  # noqa: S110
                pass
            time.sleep(interval)
        return False

    def _check_mongo_connection(self, url: "AnyUrl") -> bool:
        """Return True if a pymongo connection to *url* succeeds."""
        try:
            from pymongo import MongoClient  # noqa: PLC0415

            client = MongoClient(str(url), serverSelectionTimeoutMS=2000)
            client.admin.command("ping")
            client.close()
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def _resolve_data_path(self, *parts: str) -> Path:
        """Resolve a path relative to the .madsci/ directory."""
        return self._madsci_dir / Path(*parts)

    def detect_old_data(self) -> dict[str, bool]:
        """Check which old data directories exist.

        Returns a dict mapping component name to whether data was found.
        """
        # Note: Redis data is detected to support Location Manager migration.
        # Most Redis data is ephemeral, but v0.7.x Location Manager stores
        # primary location data in Redis that must be migrated.
        return {
            "mongodb": self._resolve_data_path("mongodb").exists(),
            "postgresql": self._resolve_data_path("postgresql", "data").exists(),
            "redis": self._resolve_data_path("redis").exists(),
            "minio": self._resolve_data_path("minio").exists(),
        }

    # ------------------------------------------------------------------
    # Prerequisites
    # ------------------------------------------------------------------

    def check_prerequisites(self) -> FossMigrationStepResult:
        """Validate that required CLI tools are available."""
        t0 = time.monotonic()
        missing: list[str] = []

        required_tools = {
            "mongodump": "MongoDB Database Tools",
            "mongorestore": "MongoDB Database Tools",
            "pg_dump": "PostgreSQL client tools",
            "pg_restore": "PostgreSQL client tools",
            "psql": "PostgreSQL client tools",
            "docker": "Docker",
        }

        for tool, package in required_tools.items():
            if shutil.which(tool) is None:
                missing.append(f"{tool} ({package})")

        if missing:
            return FossMigrationStepResult(
                step="check_prerequisites",
                success=False,
                message="Missing required tools",
                duration_seconds=time.monotonic() - t0,
                error=f"Not found on PATH: {', '.join(missing)}",
            )

        return FossMigrationStepResult(
            step="check_prerequisites",
            success=True,
            message="All prerequisite tools found",
            duration_seconds=time.monotonic() - t0,
        )

    # ------------------------------------------------------------------
    # Docker lifecycle
    # ------------------------------------------------------------------

    def _compose_cmd(self, *args: str, include_migration: bool = True) -> list[str]:
        """Build a docker compose command targeting the infrastructure and migration overlays.

        Args:
            *args: Additional arguments to pass to ``docker compose``.
            include_migration: Whether to include migration overlay files.
        """
        compose_dir = self.settings.compose_dir
        cmd = ["docker", "compose"]
        for f in self.settings.compose_files:
            cmd.extend(["-f", str(compose_dir / f)])
        if include_migration:
            for f in self.settings.migration_compose_files:
                cmd.extend(["-f", str(compose_dir / f)])
        cmd.extend(args)
        return cmd

    def _prepare_old_postgres_data(self) -> None:
        """Move old PostgreSQL data to a separate directory for the old container.

        The FOSS stack's new PostgreSQL and the old PostgreSQL cannot share
        the same data directory.  The old container uses
        ``.madsci/postgresql_old/data`` so the live path stays free for the
        new stack (which needs a clean init to install the DocumentDB
        extension used by FerretDB).

        This *renames* (moves) the old data directory so the live path is
        clean for the FOSS PostgreSQL to initialise fresh with DocumentDB
        support.  The pre-migration backup has already preserved a copy.
        """
        src = self._resolve_data_path("postgresql", "data")
        dest_parent = self._madsci_dir / "postgresql_old"
        dest = dest_parent / "data"
        if not src.exists():
            return
        if dest.exists():
            self.logger.info(
                "Old PostgreSQL data already prepared",
                destination=str(dest),
            )
            return
        # Rename .madsci/postgresql/data -> .madsci/postgresql_old/data
        dest_parent.mkdir(parents=True, exist_ok=True)
        src.rename(dest)
        self.logger.info(
            "Moved old PostgreSQL data for migration",
            source=str(src),
            destination=str(dest),
        )

    def _prepare_old_mongodb_data(self) -> None:
        """Remove stale MongoDB lock files that prevent startup after unclean shutdown.

        MongoDB creates ``mongod.lock`` and ``WiredTiger.lock`` files that
        persist after a crash or forced container stop.  Removing them allows
        the old container to start cleanly for migration.
        """
        mongodb_dir = self._resolve_data_path("mongodb")
        if not mongodb_dir.exists():
            return
        for lock_name in ("mongod.lock", "WiredTiger.lock"):
            lock_file = mongodb_dir / lock_name
            if lock_file.exists():
                lock_file.unlink()
                self.logger.info(
                    "Removed stale MongoDB lock file",
                    path=str(lock_file),
                )

    def start_old_containers(self) -> FossMigrationStepResult:
        """Start old MongoDB and PostgreSQL containers via Docker Compose."""
        t0 = time.monotonic()

        # Remove stale MongoDB lock files that would prevent startup.
        try:
            self._prepare_old_mongodb_data()
        except Exception as exc:
            self.logger.warning(
                "Could not prepare old MongoDB data",
                error=str(exc),
            )

        # Ensure old PG data is in its own directory so the new stack can
        # initialise FerretDB cleanly on the live PG data path.
        try:
            self._prepare_old_postgres_data()
        except Exception as exc:
            return FossMigrationStepResult(
                step="start_old_containers",
                success=False,
                message="Failed to prepare old PostgreSQL data",
                duration_seconds=time.monotonic() - t0,
                error=str(exc),
            )

        cmd = self._compose_cmd(
            "up",
            "-d",
            *self.settings.old_container_services,
        )
        try:
            subprocess.run(  # noqa: S603
                cmd, capture_output=True, text=True, check=True, timeout=120
            )
            # Wait for old MongoDB to accept connections
            if not self._wait_for_service(
                lambda: self._check_mongo_connection(self.settings.old_document_db_url),
                timeout=30,
                interval=2,
            ):
                self.logger.warning(
                    "Old MongoDB did not respond to ping within timeout; continuing anyway"
                )
            # Wait for old Redis to accept connections (needed for Location Manager migration)
            if self._resolve_data_path("redis").exists() and not self._wait_for_service(
                lambda: self._check_redis_connection(
                    self.settings.old_redis_host,
                    self.settings.old_redis_port,
                    self.settings.old_redis_password,
                ),
                timeout=15,
                interval=2,
            ):
                self.logger.warning(
                    "Old Redis did not respond to ping within timeout; "
                    "Location Manager data migration may be skipped"
                )
            return FossMigrationStepResult(
                step="start_old_containers",
                success=True,
                message="Old containers started",
                duration_seconds=time.monotonic() - t0,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            return FossMigrationStepResult(
                step="start_old_containers",
                success=False,
                message="Failed to start old containers",
                duration_seconds=time.monotonic() - t0,
                error=str(exc),
            )

    def start_foss_stack(self) -> FossMigrationStepResult:
        """Start the new FOSS infrastructure stack (FerretDB, Valkey, etc.)."""
        t0 = time.monotonic()
        cmd = self._compose_cmd("up", "-d", include_migration=False)
        try:
            subprocess.run(  # noqa: S603
                cmd, capture_output=True, text=True, check=True, timeout=120
            )
            # Wait for FerretDB to accept connections
            if not self._wait_for_service(
                lambda: self._check_mongo_connection(self.settings.new_document_db_url),
                timeout=60,
                interval=2,
            ):
                self.logger.warning(
                    "FerretDB did not respond to ping within timeout; continuing anyway"
                )
            return FossMigrationStepResult(
                step="start_foss_stack",
                success=True,
                message="FOSS infrastructure stack started",
                duration_seconds=time.monotonic() - t0,
            )
        except subprocess.CalledProcessError as exc:
            return FossMigrationStepResult(
                step="start_foss_stack",
                success=False,
                message="Failed to start FOSS stack",
                duration_seconds=time.monotonic() - t0,
                error=f"{exc}\nstderr: {exc.stderr}",
            )
        except FileNotFoundError as exc:
            return FossMigrationStepResult(
                step="start_foss_stack",
                success=False,
                message="Failed to start FOSS stack",
                duration_seconds=time.monotonic() - t0,
                error=str(exc),
            )

    def stop_old_containers(self) -> FossMigrationStepResult:
        """Stop and remove only the old migration containers.

        Uses ``docker compose stop`` + ``docker compose rm -f`` targeting
        specific service names so the FOSS stack keeps running.
        """
        t0 = time.monotonic()
        services = self.settings.old_container_services
        try:
            stop_cmd = self._compose_cmd("stop", *services)
            subprocess.run(  # noqa: S603
                stop_cmd, capture_output=True, text=True, check=True, timeout=60
            )
            rm_cmd = self._compose_cmd("rm", "-f", *services)
            subprocess.run(  # noqa: S603
                rm_cmd, capture_output=True, text=True, check=True, timeout=60
            )
            return FossMigrationStepResult(
                step="stop_old_containers",
                success=True,
                message="Old containers stopped",
                duration_seconds=time.monotonic() - t0,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            return FossMigrationStepResult(
                step="stop_old_containers",
                success=False,
                message="Failed to stop old containers",
                duration_seconds=time.monotonic() - t0,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Pre-migration backup
    # ------------------------------------------------------------------

    def create_pre_migration_backup(self) -> FossMigrationStepResult:
        """Create filesystem-level copies of old data directories."""
        t0 = time.monotonic()
        backup_root = self._madsci_dir / "backups" / "foss_migration"
        backup_root.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_root / f"pre_migration_{timestamp}"
        backup_path.mkdir(parents=True, exist_ok=True)

        copied: list[str] = []
        errors: list[str] = []

        dirs_to_backup = {
            "mongodb": self._resolve_data_path("mongodb"),
            "redis": self._resolve_data_path("redis"),
            "minio": self._resolve_data_path("minio"),
        }

        for name, src in dirs_to_backup.items():
            if src.exists():
                dest = backup_path / name
                try:
                    shutil.copytree(src, dest)
                    copied.append(name)
                except Exception as exc:
                    errors.append(f"{name}: {exc}")

        if errors:
            return FossMigrationStepResult(
                step="create_pre_migration_backup",
                success=False,
                message=f"Backup partially failed: copied {copied}",
                duration_seconds=time.monotonic() - t0,
                error="; ".join(errors),
                details={"backup_path": str(backup_path), "copied": copied},
            )

        return FossMigrationStepResult(
            step="create_pre_migration_backup",
            success=True,
            message=f"Backed up {len(copied)} data directories",
            duration_seconds=time.monotonic() - t0,
            details={"backup_path": str(backup_path), "copied": copied},
        )

    # ------------------------------------------------------------------
    # Document database migration  (mongodump / mongorestore)
    # ------------------------------------------------------------------

    def _parse_mongo_url(self, url: AnyUrl) -> dict:
        """Extract host, port, username, password from a MongoDB-style URL."""
        return {
            "host": url.host or "localhost",
            "port": url.port or 27017,
            "username": url.username or "",
            "password": url.password or "",
        }

    def build_mongodump_command(self, database: str) -> list[str]:
        """Build a mongodump command for the given database on the *old* server."""
        info = self._parse_mongo_url(self.settings.old_document_db_url)
        cmd = [
            "mongodump",
            "--host",
            f"{info['host']}:{info['port']}",
            "--db",
            database,
        ]
        if info["username"]:
            cmd.extend(["--username", info["username"]])
        if info["password"]:
            cmd.extend(["--password", info["password"]])
        if info["username"] or info["password"]:
            cmd.extend(["--authenticationDatabase", "admin"])
        return cmd

    def build_mongorestore_command(self, database: str, dump_path: str) -> list[str]:
        """Build a mongorestore command targeting the *new* FerretDB instance."""
        info = self._parse_mongo_url(self.settings.new_document_db_url)
        cmd = [
            "mongorestore",
            "--host",
            f"{info['host']}:{info['port']}",
            "--drop",
            "--db",
            database,
        ]
        if info["username"]:
            cmd.extend(["--username", info["username"]])
        if info["password"]:
            cmd.extend(["--password", info["password"]])
        if info["username"] or info["password"]:
            cmd.extend(["--authenticationDatabase", "admin"])
        cmd.append(dump_path)
        return cmd

    def migrate_document_databases(self) -> FossMigrationStepResult:
        """Migrate all configured document databases from MongoDB to FerretDB."""
        t0 = time.monotonic()
        migrated: list[str] = []
        errors: list[str] = []

        for db_name in self.settings.document_db_databases:
            try:
                self._migrate_single_document_db(db_name)
                migrated.append(db_name)
            except Exception as exc:
                errors.append(f"{db_name}: {exc}")

        success = len(errors) == 0
        return FossMigrationStepResult(
            step="migrate_document_databases",
            success=success,
            message=(
                f"Migrated {len(migrated)}/{len(self.settings.document_db_databases)} databases"
            ),
            duration_seconds=time.monotonic() - t0,
            error="; ".join(errors) if errors else None,
            details={"migrated": migrated, "failed": errors},
        )

    def _migrate_single_document_db(self, db_name: str) -> None:
        """Dump one database from old MongoDB and restore to FerretDB."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dump_out = str(Path(tmpdir) / "dump")

            # mongodump
            dump_cmd = self.build_mongodump_command(db_name)
            dump_cmd.extend(["--out", dump_out])
            subprocess.run(  # noqa: S603
                dump_cmd, capture_output=True, text=True, check=True, timeout=600
            )

            dump_path = str(Path(dump_out) / db_name)
            if not Path(dump_path).exists():
                self.logger.info(
                    "Skipping empty database",
                    database=db_name,
                )
                return

            # mongorestore
            restore_cmd = self.build_mongorestore_command(db_name, dump_path)
            subprocess.run(  # noqa: S603
                restore_cmd, capture_output=True, text=True, check=True, timeout=600
            )

        self.logger.info("Migrated document database", database=db_name)

    # ------------------------------------------------------------------
    # PostgreSQL migration  (pg_dump / pg_restore)
    # ------------------------------------------------------------------

    def _parse_pg_url(self, url: str) -> dict:
        """Extract host, port, user, password, database from a PostgreSQL URL."""
        parsed = urlparse.urlparse(url)
        return {
            "host": parsed.hostname or "localhost",
            "port": str(parsed.port or 5432),
            "user": parsed.username or "madsci",
            "password": parsed.password or "",
            "database": parsed.path.lstrip("/") or "postgres",
        }

    def build_pg_dump_command(self) -> list[str]:
        """Build a pg_dump command for the old PostgreSQL database."""
        info = self._parse_pg_url(self.settings.old_postgres_url)
        return [
            "pg_dump",
            "-h",
            info["host"],
            "-p",
            info["port"],
            "-U",
            info["user"],
            "-d",
            info["database"],
            "--no-password",
            "--format=custom",
        ]

    def build_pg_restore_command(self, dump_file: str) -> list[str]:
        """Build a pg_restore command for the new PostgreSQL database."""
        info = self._parse_pg_url(self.settings.new_postgres_url)
        return [
            "pg_restore",
            "-h",
            info["host"],
            "-p",
            info["port"],
            "-U",
            info["user"],
            "-d",
            info["database"],
            "--no-password",
            "--clean",
            "--if-exists",
            dump_file,
        ]

    def migrate_postgresql(self) -> FossMigrationStepResult:
        """Migrate PostgreSQL data from old instance to new instance."""
        t0 = time.monotonic()
        old_info = self._parse_pg_url(self.settings.old_postgres_url)
        new_info = self._parse_pg_url(self.settings.new_postgres_url)

        try:
            with tempfile.NamedTemporaryFile(suffix=".dump", delete=False) as tmp:
                dump_file = tmp.name

            try:
                env = environ.copy()
                env["PGPASSWORD"] = old_info["password"]

                dump_cmd = self.build_pg_dump_command()
                dump_cmd.extend(["--file", dump_file])
                subprocess.run(  # noqa: S603
                    dump_cmd,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=600,
                )

                env["PGPASSWORD"] = new_info["password"]
                restore_cmd = self.build_pg_restore_command(dump_file)
                subprocess.run(  # noqa: S603
                    restore_cmd,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=600,
                )
            finally:
                Path(dump_file).unlink(missing_ok=True)

            return FossMigrationStepResult(
                step="migrate_postgresql",
                success=True,
                message=f"Migrated PostgreSQL ({old_info['database']} -> {new_info['database']})",
                duration_seconds=time.monotonic() - t0,
            )

        except subprocess.CalledProcessError as exc:
            return FossMigrationStepResult(
                step="migrate_postgresql",
                success=False,
                message="PostgreSQL migration failed",
                duration_seconds=time.monotonic() - t0,
                error=f"{exc}\nstderr: {exc.stderr}",
            )
        except FileNotFoundError as exc:
            return FossMigrationStepResult(
                step="migrate_postgresql",
                success=False,
                message="PostgreSQL client tools not found",
                duration_seconds=time.monotonic() - t0,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Redis -> Valkey  (Location Manager data migration)
    # ------------------------------------------------------------------

    def _check_redis_connection(
        self, host: str, port: int, password: Optional[str] = None
    ) -> bool:
        """Return True if a Redis connection succeeds."""
        try:
            import redis as redis_lib  # noqa: PLC0415

            client = redis_lib.Redis(
                host=host, port=port, password=password, socket_timeout=2
            )
            client.ping()
            client.close()
            return True
        except Exception:
            return False

    def _discover_location_manager_ids(
        self, host: str, port: int, password: Optional[str] = None
    ) -> list[str]:
        """Discover Location Manager IDs from old Redis keys.

        Scans for keys matching ``madsci:location_manager:*:locations`` and
        extracts the manager ID from the key pattern.
        """
        import redis as redis_lib  # noqa: PLC0415

        client = redis_lib.Redis(host=host, port=port, password=password)
        try:
            keys = client.keys("madsci:location_manager:*:locations")
            manager_ids = []
            for key in keys:
                # Key format: madsci:location_manager:{manager_id}:locations
                key_str = key.decode() if isinstance(key, bytes) else key
                parts = key_str.split(":")
                if len(parts) >= 4:
                    manager_ids.append(parts[2])
            return manager_ids
        finally:
            client.close()

    def migrate_redis_to_valkey(self) -> FossMigrationStepResult:
        """Migrate Location Manager data from old Redis to the new document database.

        Most Redis/Valkey data in MADSci is ephemeral (workcell state) and is
        repopulated automatically by managers on startup.  However, the v0.7.x
        Location Manager stores its **primary location data** in Redis —
        including resource attachments and node representations — which must be
        migrated to the document database used by v0.8.0+.

        Redis 7.4 uses RDB format v12, incompatible with Valkey 8 (RDB v11),
        so file-level migration is not possible.  Instead, this step performs
        an application-level migration: read from old Redis via the Python
        client, write to FerretDB via the LocationMigrator.
        """
        t0 = time.monotonic()
        host = self.settings.old_redis_host
        port = self.settings.old_redis_port
        password = self.settings.old_redis_password

        # Quick checks: skip if no data or Redis unreachable
        skip_reason = self._check_redis_skip_reason(host, port, password)
        if skip_reason is not None:
            return skip_reason

        return self._run_location_migration(host, port, password, t0)

    def _check_redis_skip_reason(
        self,
        host: str,
        port: int,
        password: Optional[str],
    ) -> Optional[FossMigrationStepResult]:
        """Return a skip result if Redis migration should be skipped, else None."""
        t0 = time.monotonic()

        if not self._resolve_data_path("redis").exists():
            return FossMigrationStepResult(
                step="migrate_redis_to_valkey",
                success=True,
                message="No old Redis data directory found; skipping",
                duration_seconds=time.monotonic() - t0,
            )

        if not self._wait_for_service(
            lambda: self._check_redis_connection(host, port, password),
            timeout=15,
            interval=2,
        ):
            return FossMigrationStepResult(
                step="migrate_redis_to_valkey",
                success=True,
                message=(
                    f"Old Redis not reachable at {host}:{port}; "
                    "skipping Location Manager migration (ephemeral data will be repopulated)"
                ),
                duration_seconds=time.monotonic() - t0,
                details={
                    "note": "If you have v0.7.x location data to migrate, start old Redis and re-run this step"
                },
            )

        return None

    def _run_location_migration(
        self,
        host: str,
        port: int,
        password: Optional[str],
        t0: float,
    ) -> FossMigrationStepResult:
        """Discover Location Manager IDs and migrate their data."""
        try:
            manager_ids = self._discover_location_manager_ids(host, port, password)
        except Exception as exc:
            return FossMigrationStepResult(
                step="migrate_redis_to_valkey",
                success=False,
                message="Failed to discover Location Manager IDs from old Redis",
                duration_seconds=time.monotonic() - t0,
                error=str(exc),
            )

        if not manager_ids:
            return FossMigrationStepResult(
                step="migrate_redis_to_valkey",
                success=True,
                message="No Location Manager data found in old Redis; skipping",
                duration_seconds=time.monotonic() - t0,
            )

        try:
            from madsci.common.db_handlers import (  # noqa: PLC0415
                PyCacheHandler,
                PyDocumentStorageHandler,
            )
            from madsci.location_manager.location_migration import (  # noqa: PLC0415
                LocationMigrator,
            )

            cache_handler = PyCacheHandler.from_settings(
                host=host, port=port, password=password
            )
            document_handler = PyDocumentStorageHandler.from_url(
                str(self.settings.new_document_db_url),
                self.settings.location_database_name,
            )

            total_migrated = 0
            total_skipped = 0
            all_errors: list[str] = []

            for manager_id in manager_ids:
                migrator = LocationMigrator(
                    cache_handler=cache_handler,
                    document_handler=document_handler,
                    manager_id=manager_id,
                )
                result = migrator.migrate_from_redis()
                total_migrated += result.migrated
                total_skipped += result.skipped
                all_errors.extend(result.errors)

            cache_handler.close()

            success = len(all_errors) == 0
            return FossMigrationStepResult(
                step="migrate_redis_to_valkey",
                success=success,
                message=(
                    f"Migrated {total_migrated} locations from Redis to document database ({total_skipped} skipped)"
                    if success
                    else f"Location migration partially failed: {total_migrated} migrated, {len(all_errors)} errors"
                ),
                duration_seconds=time.monotonic() - t0,
                error="; ".join(all_errors) if all_errors else None,
                details={
                    "manager_ids": manager_ids,
                    "migrated": total_migrated,
                    "skipped": total_skipped,
                },
            )

        except ImportError as exc:
            return FossMigrationStepResult(
                step="migrate_redis_to_valkey",
                success=False,
                message="Location Manager migration dependencies not available",
                duration_seconds=time.monotonic() - t0,
                error=f"Required packages not installed: {exc}",
            )
        except Exception as exc:
            return FossMigrationStepResult(
                step="migrate_redis_to_valkey",
                success=False,
                message="Location Manager migration failed",
                duration_seconds=time.monotonic() - t0,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # MinIO -> SeaweedFS  (S3 SDK copy)
    # ------------------------------------------------------------------

    @staticmethod
    def _has_user_data_in_minio(minio_path: Path) -> bool:
        """Check if a MinIO data directory contains actual user data.

        The ``.minio.sys`` subdirectory is MinIO internal metadata and does
        not count as user data.  Returns True only if there are entries
        beyond ``.minio.sys``.
        """
        if not minio_path.exists():
            return False
        entries = {e.name for e in minio_path.iterdir()}
        entries.discard(".minio.sys")
        return len(entries) > 0

    def migrate_minio_to_seaweedfs(self) -> FossMigrationStepResult:
        """Copy objects from MinIO to SeaweedFS via the S3-compatible SDK."""
        t0 = time.monotonic()

        # Quick check: if there's no local MinIO data (or only .minio.sys), skip
        minio_path = self._resolve_data_path("minio")
        if not self._has_user_data_in_minio(minio_path):
            reason = (
                "No MinIO data directory found"
                if not minio_path.exists()
                else "MinIO data directory contains only internal metadata"
            )
            return FossMigrationStepResult(
                step="migrate_minio_to_seaweedfs",
                success=True,
                message=f"{reason}; skipping",
                duration_seconds=time.monotonic() - t0,
            )

        try:
            from minio import Minio  # noqa: PLC0415

            old_url = self.settings.old_minio_url
            new_url = self.settings.new_seaweedfs_url

            old_client = Minio(
                f"{old_url.host}:{old_url.port or 9002}",
                access_key=self.settings.minio_access_key,
                secret_key=self.settings.minio_secret_key,
                secure=old_url.scheme == "https",
            )
            new_client = Minio(
                f"{new_url.host}:{new_url.port or 8333}",
                access_key=self.settings.seaweedfs_access_key,
                secret_key=self.settings.seaweedfs_secret_key,
                secure=new_url.scheme == "https",
            )

            try:
                buckets = old_client.list_buckets()
            except Exception as exc:
                return FossMigrationStepResult(
                    step="migrate_minio_to_seaweedfs",
                    success=False,
                    message="Cannot connect to old MinIO instance",
                    duration_seconds=time.monotonic() - t0,
                    error=f"Ensure old MinIO is running and credentials are correct: {exc}",
                )

            if not buckets:
                return FossMigrationStepResult(
                    step="migrate_minio_to_seaweedfs",
                    success=True,
                    message="No buckets found in MinIO; skipping",
                    duration_seconds=time.monotonic() - t0,
                )

            total_objects = 0
            for bucket in buckets:
                if not new_client.bucket_exists(bucket.name):
                    new_client.make_bucket(bucket.name)

                for obj in old_client.list_objects(bucket.name, recursive=True):
                    response = old_client.get_object(bucket.name, obj.object_name)
                    new_client.put_object(
                        bucket.name,
                        obj.object_name,
                        response,
                        length=obj.size,
                    )
                    response.close()
                    response.release_conn()
                    total_objects += 1

            return FossMigrationStepResult(
                step="migrate_minio_to_seaweedfs",
                success=True,
                message=f"Copied {total_objects} objects across {len(buckets)} buckets",
                duration_seconds=time.monotonic() - t0,
                details={
                    "buckets": len(buckets),
                    "objects": total_objects,
                },
            )

        except ImportError:
            return FossMigrationStepResult(
                step="migrate_minio_to_seaweedfs",
                success=False,
                message="minio Python package not installed",
                duration_seconds=time.monotonic() - t0,
                error="Install with: pip install minio",
            )
        except Exception as exc:
            return FossMigrationStepResult(
                step="migrate_minio_to_seaweedfs",
                success=False,
                message="Object storage migration failed",
                duration_seconds=time.monotonic() - t0,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def verify_migration(self) -> FossMigrationStepResult:
        """Connect to each new service and verify data presence."""
        t0 = time.monotonic()
        checks: dict[str, str] = {}
        errors: list[str] = []

        # Document databases
        try:
            from pymongo import MongoClient  # noqa: PLC0415

            client = MongoClient(
                str(self.settings.new_document_db_url),
                serverSelectionTimeoutMS=5000,
            )
            for db_name in self.settings.document_db_databases:
                db = client[db_name]
                collections = db.list_collection_names()
                if collections:
                    total_docs = sum(db[c].count_documents({}) for c in collections)
                    checks[db_name] = (
                        f"{len(collections)} collections, {total_docs} documents"
                    )
                else:
                    checks[db_name] = "empty (no collections)"
            client.close()
        except Exception as exc:
            errors.append(f"Document DB verification failed: {exc}")

        # PostgreSQL
        try:
            new_pg = self._parse_pg_url(self.settings.new_postgres_url)
            env = environ.copy()
            env["PGPASSWORD"] = new_pg["password"]
            result = subprocess.run(  # noqa: S603
                [  # noqa: S607
                    "psql",
                    "-h",
                    new_pg["host"],
                    "-p",
                    new_pg["port"],
                    "-U",
                    new_pg["user"],
                    "-d",
                    new_pg["database"],
                    "--no-password",
                    "-t",
                    "-c",
                    "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';",
                ],
                env=env,
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
            table_count = result.stdout.strip()
            checks["postgresql"] = f"{table_count} public tables"
        except Exception as exc:
            errors.append(f"PostgreSQL verification failed: {exc}")

        # Valkey
        valkey_dir = self._madsci_dir / "valkey"
        if valkey_dir.exists():
            files = list(valkey_dir.iterdir())
            checks["valkey"] = f"{len(files)} files in data dir"
        else:
            checks["valkey"] = "data dir not found"

        success = len(errors) == 0
        return FossMigrationStepResult(
            step="verify_migration",
            success=success,
            message="Verification complete" if success else "Verification found issues",
            duration_seconds=time.monotonic() - t0,
            error="; ".join(errors) if errors else None,
            details=checks,
        )

    # ------------------------------------------------------------------
    # Full orchestration
    # ------------------------------------------------------------------

    STEP_METHODS: ClassVar[Dict[str, str]] = {
        "document-db": "migrate_document_databases",
        "postgresql": "migrate_postgresql",
        "redis": "migrate_redis_to_valkey",
        "object-storage": "migrate_minio_to_seaweedfs",
    }

    def run_full_migration(
        self,
        *,
        skip_backup: bool = False,
        skip_docker: bool = False,
        steps: Optional[List[str]] = None,
    ) -> FossMigrationReport:
        """Run the full migration pipeline.

        Args:
            skip_backup: Skip creating a pre-migration backup.
            skip_docker: Skip starting/stopping old containers.
            steps: If provided, only run these steps (choices from STEP_METHODS).
                   Defaults to all steps.
        """
        report = FossMigrationReport()

        # Prerequisites
        prereq = self.check_prerequisites()
        report.steps.append(prereq)
        if not prereq.success:
            report.finished_at = datetime.now()
            return report

        # Backup
        if not skip_backup:
            backup_result = self.create_pre_migration_backup()
            report.steps.append(backup_result)
            if not backup_result.success:
                report.finished_at = datetime.now()
                return report

        # Start old containers + FOSS stack
        if not skip_docker:
            start_result = self.start_old_containers()
            report.steps.append(start_result)
            if not start_result.success:
                report.finished_at = datetime.now()
                return report

            foss_result = self.start_foss_stack()
            report.steps.append(foss_result)
            if not foss_result.success:
                report.finished_at = datetime.now()
                return report

        # Run migration steps
        selected = steps or list(self.STEP_METHODS.keys())
        for step_name in selected:
            method_name = self.STEP_METHODS.get(step_name)
            if method_name is None:
                report.steps.append(
                    FossMigrationStepResult(
                        step=step_name,
                        success=False,
                        message=f"Unknown step: {step_name}",
                        error=f"Valid steps: {', '.join(self.STEP_METHODS.keys())}",
                    )
                )
                continue
            method = getattr(self, method_name)
            result = method()
            report.steps.append(result)

        # Verification
        verify_result = self.verify_migration()
        report.steps.append(verify_result)

        # Stop old containers
        if not skip_docker:
            stop_result = self.stop_old_containers()
            report.steps.append(stop_result)

        report.finished_at = datetime.now()
        return report
