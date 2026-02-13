"""
Base types for MADSci.
"""

from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, ClassVar, Optional, TypeVar, Union

import yaml
from pydantic import BaseModel, Field, SecretStr
from pydantic.config import ConfigDict
from pydantic_settings import (
    BaseSettings,
    CliSettingsSource,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
    YamlConfigSettingsSource,
)
from sqlmodel import SQLModel

REDACTED_PLACEHOLDER = "***REDACTED***"
"""Placeholder string used when redacting secret field values."""

_T = TypeVar("_T")

PathLike = Union[str, Path]


class MadsciDeveloperSettings(BaseSettings):
    """
    Developer-focused settings for MADSci behavior.

    These settings control development experience features like rich tracebacks.
    All settings use the MADSCI_ prefix for environment variables.

    Environment Variables:
        MADSCI_DISABLE_RICH_TRACEBACKS: Set to true to disable rich tracebacks
            (default: false, rich tracebacks are enabled)
        MADSCI_RICH_TRACEBACKS_SHOW_LOCALS: Set to true to show local variables
            in tracebacks (default: false for security - can leak secrets)

    Note:
        show_locals is disabled by default to prevent accidental exposure of
        sensitive data (tokens, passwords) that may be present in local variables
        during exceptions.
    """

    model_config = SettingsConfigDict(
        env_prefix="MADSCI_",
        env_file=None,
        validate_default=True,
        extra="ignore",
    )

    disable_rich_tracebacks: bool = Field(
        default=False,
        title="Disable Rich Tracebacks",
        description="Disable rich traceback handler for exception output.",
    )
    rich_tracebacks_show_locals: bool = Field(
        default=False,
        title="Show Locals in Rich Tracebacks",
        description=(
            "Show local variables in tracebacks. "
            "Disabled by default for security - can leak sensitive data."
        ),
    )


class MadsciBaseSettings(BaseSettings):
    """
    Base class for all MADSci settings.
    """

    model_config: SettingsConfigDict = SettingsConfigDict(
        env_file=None,
        env_file_encoding="utf-8",
        validate_assignment=True,
        validate_default=True,
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
        cli_parse_args=True,
        cli_ignore_unknown_args=True,
        _env_parse_none_str="null",
    )
    """Configuration for the settings model."""

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Sets the order of settings sources for the settings model."""
        return (
            CliSettingsSource(settings_cls, cli_parse_args=True),
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            JsonConfigSettingsSource(settings_cls),
            TomlConfigSettingsSource(settings_cls),
            YamlConfigSettingsSource(settings_cls),
        )

    def model_dump_safe(
        self,
        include_secrets: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Dump settings data with secret fields redacted by default.

        Secret fields are identified by ``json_schema_extra={"secret": True}``
        or ``SecretStr`` / ``SecretBytes`` type annotations.

        Args:
            include_secrets: If True, include actual secret values.
            **kwargs: Additional keyword arguments forwarded to ``model_dump``.

        Returns:
            dict: Settings with secrets redacted unless ``include_secrets=True``.
        """
        kwargs.setdefault("mode", "json")
        data = self.model_dump(**kwargs)
        if include_secrets:
            return data
        for field_name, field_info in type(self).model_fields.items():
            if field_name not in data:
                continue
            if _is_secret_field(field_info):
                data[field_name] = REDACTED_PLACEHOLDER
        return data


class MadsciSQLModel(SQLModel):
    """
    Parent class for all MADSci data models that are SQLModel-based.
    """

    model_config = ConfigDict(
        validate_assignment=True,
        validate_default=True,
    )
    """Configuration for the SQLModel model."""

    def to_yaml(self, path: PathLike, **kwargs: Any) -> None:
        """
        Allows all derived data models to be exported into yaml.

        kwargs are passed to model_dump
        """
        Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        with Path(path).expanduser().open(mode="w") as fp:
            yaml.dump(
                self.model_dump(mode="json", **kwargs),
                fp,
                indent=2,
                sort_keys=False,
            )

    @classmethod
    def from_yaml(cls: type[_T], path: PathLike) -> _T:
        """
        Allows all derived data models to be loaded from yaml.
        """
        with Path(path).expanduser().open() as fp:
            raw_data = yaml.safe_load(fp)
        return cls.model_validate(raw_data)


class MadsciBaseModel(BaseModel):
    """
    Parent class for all MADSci data models.
    """

    _mongo_excluded_fields: ClassVar[list[str]] = []
    """Fields to exclude from insertion into MongoDB."""

    model_config = ConfigDict(
        validate_assignment=True,
        validate_default=True,
    )

    @classmethod
    def from_yaml(cls: type[_T], path: PathLike) -> _T:
        """
        Allows all derived data models to be loaded from yaml.
        """
        with Path(path).expanduser().open() as fp:
            raw_data = yaml.safe_load(fp)
        return cls.model_validate(raw_data)

    def model_dump_yaml(self, include_secrets: bool = True) -> str:
        """Convert the model to a YAML string.

        Args:
            include_secrets: If False, redact secret field values.

        Returns:
            YAML string representation of the model
        """
        if include_secrets:
            dump = self.model_dump(mode="json")
        else:
            dump = self.model_dump_safe(include_secrets=False)
        return yaml.dump(
            dump,
            indent=2,
            sort_keys=False,
        )

    def model_dump_safe(
        self,
        include_secrets: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Dump model data with secret fields redacted by default.

        This method provides a safe way to export model data without
        accidentally exposing sensitive values. Secret fields are identified
        by:
        - Fields typed as ``SecretStr`` / ``SecretBytes``
        - Fields with ``json_schema_extra={"secret": True}`` metadata

        Args:
            include_secrets: If True, include actual secret values.
                Defaults to False (secrets are replaced with
                ``***REDACTED***``).
            **kwargs: Additional keyword arguments forwarded to
                ``model_dump(mode="json", ...)``.

        Returns:
            dict: Model data with secrets redacted unless
                ``include_secrets=True``.
        """
        kwargs.setdefault("mode", "json")
        data = self.model_dump(**kwargs)
        if include_secrets:
            return data
        return self._redact_secrets(data)

    def _redact_secrets(self, data: dict[str, Any]) -> dict[str, Any]:
        """Redact secret fields in a dumped data dict.

        Walks through the model's field metadata to find fields that are
        ``SecretStr``, ``SecretBytes``, or annotated with
        ``json_schema_extra={"secret": True}``, and replaces their values
        with ``***REDACTED***``.
        """
        for field_name, field_info in type(self).model_fields.items():
            if field_name not in data:
                continue
            if _is_secret_field(field_info):
                data[field_name] = REDACTED_PLACEHOLDER
            elif isinstance(data[field_name], dict) and hasattr(
                field_info, "annotation"
            ):
                # If the field is a nested model, recurse
                value = getattr(self, field_name, None)
                if isinstance(value, MadsciBaseModel):
                    data[field_name] = value.model_dump_safe(include_secrets=False)
        return data

    def to_yaml(
        self, path: PathLike, include_secrets: bool = True, **kwargs: Any
    ) -> None:
        """Export the model to a YAML file.

        Args:
            path: File path to write to.
            include_secrets: If False, redact secret field values.
                Defaults to True for backwards compatibility with
                internal serialization (e.g., definition file round-trips).
            **kwargs: Additional keyword arguments forwarded to
                ``model_dump``.
        """
        Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        if include_secrets:
            dump = self.model_dump(mode="json", **kwargs)
        else:
            dump = self.model_dump_safe(include_secrets=False, **kwargs)
        with Path(path).expanduser().open(mode="w") as fp:
            yaml.dump(
                dump,
                fp,
                indent=2,
                sort_keys=False,
            )

    def to_mongo(self) -> dict[str, Any]:
        """
        Convert the model to a MongoDB-compatible dictionary.
        """
        json_data = self.model_dump(mode="json", by_alias=True)
        for field in self.__pydantic_fields__:
            if field in self._mongo_excluded_fields:
                json_data.pop(field, None)
        return json_data


def _is_secret_field(field_info: Any) -> bool:
    """Check whether a Pydantic FieldInfo represents a secret field.

    A field is considered secret if:
    - Its annotation is ``SecretStr`` or ``SecretBytes``
    - It has ``json_schema_extra={"secret": True}`` metadata
    """
    from pydantic import SecretBytes  # noqa: PLC0415

    # Check annotation type
    annotation = getattr(field_info, "annotation", None)
    if annotation is not None:
        # Handle Optional[SecretStr] etc. by checking origin and args
        origin = getattr(annotation, "__origin__", None)
        if origin is Union:
            args = getattr(annotation, "__args__", ())
            if any(a is SecretStr or a is SecretBytes for a in args):
                return True
        if annotation is SecretStr or annotation is SecretBytes:
            return True

    # Check json_schema_extra metadata
    extra = getattr(field_info, "json_schema_extra", None)
    return bool(isinstance(extra, dict) and extra.get("secret"))


class Error(MadsciBaseModel):
    """A MADSci Error"""

    message: Optional[str] = Field(
        title="Message",
        description="The error message.",
        default=None,
    )
    logged_at: datetime = Field(
        title="Logged At",
        description="The timestamp of when the error was logged.",
        default_factory=datetime.now,
    )
    error_type: Optional[str] = Field(
        title="Error Type",
        description="The type of error.",
        default=None,
    )

    @classmethod
    def from_exception(cls, exception: Exception) -> "Error":
        """Create an error from an exception."""
        return cls(message=str(exception), error_type=type(exception).__name__)


PositiveInt = Annotated[int, Field(ge=0)]
PositiveNumber = Annotated[Union[float, int], Field(ge=0)]
