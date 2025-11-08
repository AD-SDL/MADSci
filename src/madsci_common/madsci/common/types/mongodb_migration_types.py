""" "MongoDB migration configuration types."""

from pathlib import Path
from typing import Any, Optional

from madsci.common.types.base_types import MadsciBaseSettings, PathLike
from pydantic import AliasChoices, AnyUrl, Field, field_validator


class MongoDBMigrationSettings(
    MadsciBaseSettings,
    env_file=(".env", "mongodb.env", "migration.env"),
    toml_file=("settings.toml", "mongodb.settings.toml", "migration.settings.toml"),
    yaml_file=("settings.yaml", "mongodb.settings.yaml", "migration.settings.yaml"),
    json_file=("settings.json", "mongodb.settings.json", "migration.settings.json"),
    env_prefix="MONGODB_MIGRATION_",
):
    """Configuration settings for MongoDB migration operations."""

    mongo_db_url: AnyUrl = Field(
        default=AnyUrl("mongodb://localhost:27017"),
        title="MongoDB URL",
        description="MongoDB connection URL (e.g., mongodb://localhost:27017). "
        "Defaults to localhost MongoDB instance.",
        validation_alias=AliasChoices(
            "mongo_db_url", "MONGODB_URL", "MONGO_URL", "DATABASE_URL", "db_url"
        ),
    )
    database: str = Field(
        title="Database Name",
        description="Database name to migrate (e.g., madsci_events, madsci_data)",
    )
    schema_file: PathLike = Field(
        title="Schema File Path",
        description="Explicit path to schema.json (required).",
        validation_alias=AliasChoices("schema_file", "MONGODB_SCHEMA_FILE"),
    )
    backup_dir: PathLike = Field(
        default=Path(".madsci/mongodb/backups"),
        title="Backup Directory",
        description="Directory where database backups will be stored. Relative to CWD unless absolute is provided.",
    )
    target_version: Optional[str] = Field(
        default=None,
        title="Target Version",
        description="Target version to migrate to (defaults to current MADSci version)",
    )
    backup_only: bool = Field(
        default=False,
        title="Backup Only",
        description="Only create a backup, do not run migration",
    )
    restore_from: Optional[PathLike] = Field(
        default=None,
        title="Restore From",
        description="Restore from specified backup directory instead of migrating",
    )
    check_version: bool = Field(
        default=False,
        title="Check Version Only",
        description="Only check version compatibility, do not migrate",
    )

    @field_validator("backup_dir", mode="before")
    @classmethod
    def _normalize_backup_dir(cls, v: Any) -> Optional[str]:
        """Normalize backup directory path."""
        # do NOT expanduser here; just coerce to str/Path-like
        return str(v) if v is not None else v

    def get_effective_schema_file_path(self) -> Path:
        """Get the effective schema file path as a Path object."""
        p = Path(self.schema_file)
        if not p.exists():
            raise FileNotFoundError(f"Schema file not found: {p}")
        return p
