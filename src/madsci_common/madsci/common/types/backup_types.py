"""Configuration types for MADSci backup operations."""

from pathlib import Path
from typing import List, Optional, Union

from madsci.common.types.base_types import MadsciBaseSettings
from pydantic import AnyUrl, Field, field_validator


class BaseBackupSettings(MadsciBaseSettings):
    """Common backup configuration settings."""

    backup_dir: Path = Field(
        default=Path(".madsci/backups"),
        title="Backup Directory",
        description="Directory for storing backups",
    )
    max_backups: int = Field(
        default=10,
        ge=0,
        title="Maximum Backups",
        description="Maximum number of backups to retain",
    )
    validate_integrity: bool = Field(
        default=True,
        title="Validate Integrity",
        description="Perform integrity validation after backup",
    )
    compression: bool = Field(
        default=True,
        title="Enable Compression",
        description="Enable backup compression",
    )

    @field_validator("backup_dir", mode="before")
    @classmethod
    def convert_backup_dir_to_path(cls, v: Union[str, Path]) -> Path:
        """Convert backup_dir to Path object."""
        if isinstance(v, str):
            return Path(v)
        return v


class PostgreSQLBackupSettings(
    BaseBackupSettings,
    env_file=(".env", "postgresql_backup.env"),
    toml_file=("settings.toml", "postgresql_backup.settings.toml"),
    yaml_file=("settings.yaml", "postgresql_backup.settings.yaml"),
    json_file=("settings.json", "postgresql_backup.settings.json"),
    env_prefix="POSTGRES_",
):
    """PostgreSQL-specific backup settings."""

    db_url: str = Field(
        title="Database URL", description="PostgreSQL connection URL", alias="db_url"
    )
    backup_format: str = Field(
        default="custom",
        title="Backup Format",
        description="pg_dump format: custom, plain, directory, tar",
    )


class MongoDBBackupSettings(
    BaseBackupSettings,
    env_file=(".env", "mongodb_backup.env"),
    toml_file=("settings.toml", "mongodb_backup.settings.toml"),
    yaml_file=("settings.yaml", "mongodb_backup.settings.yaml"),
    json_file=("settings.json", "mongodb_backup.settings.json"),
    env_prefix="MONGODB_",
):
    """MongoDB-specific backup settings."""

    mongo_db_url: AnyUrl = Field(
        title="MongoDB URL",
        description="MongoDB connection URL",
        alias="mongo_db_url",  # avoid double prefixing
    )
    database: str = Field(title="Database Name", description="Database name to backup")
    collections: Optional[List[str]] = Field(
        default=None,
        title="Collections",
        description="Specific collections to backup (all if None)",
    )
