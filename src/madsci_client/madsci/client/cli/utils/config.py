"""CLI configuration management.

This module provides configuration handling for the MADSci CLI.
"""

from pathlib import Path
from typing import Optional

import toml
from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MadsciCLIConfig(BaseSettings):
    """Configuration for MADSci CLI.

    Configuration is loaded from multiple sources in order of precedence:
    1. Command-line arguments
    2. Environment variables (MADSCI_ prefix)
    3. Configuration file (~/.madsci/config.toml or local .madsci/config.toml)
    4. Default values
    """

    model_config = SettingsConfigDict(
        env_prefix="MADSCI_",
        env_file=None,
        validate_default=True,
        extra="ignore",
    )

    # Service URLs
    lab_url: AnyUrl = Field(
        default="http://localhost:8000/",
        description="Lab Manager URL.",
    )
    event_manager_url: AnyUrl = Field(
        default="http://localhost:8001/",
        description="Event Manager URL.",
    )
    experiment_manager_url: AnyUrl = Field(
        default="http://localhost:8002/",
        description="Experiment Manager URL.",
    )
    resource_manager_url: AnyUrl = Field(
        default="http://localhost:8003/",
        description="Resource Manager URL.",
    )
    data_manager_url: AnyUrl = Field(
        default="http://localhost:8004/",
        description="Data Manager URL.",
    )
    workcell_manager_url: AnyUrl = Field(
        default="http://localhost:8005/",
        description="Workcell Manager URL.",
    )
    location_manager_url: AnyUrl = Field(
        default="http://localhost:8006/",
        description="Location Manager URL.",
    )

    # Registry settings
    registry_path: Path = Field(
        default_factory=lambda: Path.home() / ".madsci" / "registry.json",
        description="Path to local ID registry file.",
    )

    # Output preferences
    default_output_format: str = Field(
        default="text",
        description="Default output format (text, json, yaml).",
    )
    color_enabled: bool = Field(
        default=True,
        description="Enable colored output.",
    )

    # Template settings
    template_dir: Optional[Path] = Field(
        default=None,
        description="Custom template directory.",
    )

    @classmethod
    def get_config_paths(cls) -> list[Path]:
        """Get list of possible config file paths in order of precedence.

        Returns:
            List of Path objects to check for config files.
        """
        return [
            Path.cwd() / ".madsci" / "config.toml",
            Path.home() / ".madsci" / "config.toml",
        ]

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "MadsciCLIConfig":
        """Load configuration from file or defaults.

        Args:
            config_path: Optional explicit path to config file.

        Returns:
            MadsciCLIConfig instance with loaded values.
        """
        config_data = {}

        # Determine config file to use
        if config_path:
            path = Path(config_path).expanduser()
            if path.exists():
                config_data = cls._load_toml(path)
        else:
            # Check standard locations
            for path in cls.get_config_paths():
                if path.exists():
                    config_data = cls._load_toml(path)
                    break

        return cls(**config_data)

    @classmethod
    def _load_toml(cls, path: Path) -> dict:
        """Load configuration from a TOML file.

        Args:
            path: Path to TOML config file.

        Returns:
            Dictionary of configuration values.
        """
        try:
            with path.open() as f:
                return toml.load(f)
        except Exception:
            return {}

    def save(self, path: Optional[Path] = None) -> None:
        """Save configuration to a TOML file.

        Args:
            path: Path to save to. Defaults to ~/.madsci/config.toml.
        """
        if path is None:
            path = Path.home() / ".madsci" / "config.toml"

        path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict, handling special types
        data = {}
        for field_name in self.model_fields:
            value = getattr(self, field_name)
            if isinstance(value, Path) or hasattr(value, "__str__"):
                data[field_name] = str(value)
            else:
                data[field_name] = value

        with path.open("w") as f:
            toml.dump(data, f)
