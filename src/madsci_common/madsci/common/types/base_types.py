"""
Base types for MADSci.
"""

from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, ClassVar, Optional, TypeVar, Union

import yaml
from pydantic import (
    AliasGenerator,
    BaseModel,
    Field,
    SecretStr,
    model_validator,
)
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
        or ``SecretStr`` / ``SecretBytes`` type annotations. Nested models
        are recursively redacted.

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
        return self._redact_secrets(data)

    def _redact_secrets(self, data: dict[str, Any]) -> dict[str, Any]:
        """Redact secret fields in a dumped data dict, recursing into nested models.

        Supports both by_alias=True and by_alias=False dumps by building a mapping
        from all possible keys (field names and serialization aliases) to field info.
        """
        alias_to_field = _build_alias_to_field_map(type(self))

        for key in list(data.keys()):
            if key not in alias_to_field:
                continue
            field_name, field_info = alias_to_field[key]
            if _is_secret_field(field_info):
                data[key] = REDACTED_PLACEHOLDER
            elif isinstance(data[key], dict) and hasattr(field_info, "annotation"):
                value = getattr(self, field_name, None)
                if isinstance(value, (MadsciBaseModel, MadsciBaseSettings)):
                    data[key] = value.model_dump_safe(include_secrets=False)
            elif isinstance(data[key], list):
                values = getattr(self, field_name, None)
                if isinstance(values, list):
                    data[key] = [
                        item.model_dump_safe(include_secrets=False)
                        if isinstance(item, (MadsciBaseModel, MadsciBaseSettings))
                        else item
                        for item in values
                    ]
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

        Supports both by_alias=True and by_alias=False dumps by building a mapping
        from all possible keys (field names and serialization aliases) to field info.
        """
        alias_to_field = _build_alias_to_field_map(type(self))

        for key in list(data.keys()):
            if key not in alias_to_field:
                continue
            field_name, field_info = alias_to_field[key]
            if _is_secret_field(field_info):
                data[key] = REDACTED_PLACEHOLDER
            elif isinstance(data[key], dict) and hasattr(field_info, "annotation"):
                value = getattr(self, field_name, None)
                if isinstance(value, MadsciBaseModel):
                    data[key] = value.model_dump_safe(include_secrets=False)
            elif isinstance(data[key], list):
                values = getattr(self, field_name, None)
                if isinstance(values, list):
                    data[key] = [
                        item.model_dump_safe(include_secrets=False)
                        if isinstance(item, MadsciBaseModel)
                        else item
                        for item in values
                    ]
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


def _build_alias_to_field_map(
    model_cls: type,
) -> dict[str, tuple[str, Any]]:
    """Build a mapping from all possible dump keys to (field_name, field_info).

    This handles both by_alias=True and by_alias=False dumps by mapping:
    - The field name itself
    - Any explicit serialization_alias on the field
    - Any alias generated by the model's alias_generator
    """
    alias_to_field: dict[str, tuple[str, Any]] = {}
    for field_name, field_info in model_cls.model_fields.items():
        alias_to_field[field_name] = (field_name, field_info)
        # Map explicit serialization alias
        if field_info.serialization_alias:
            alias_to_field[field_info.serialization_alias] = (field_name, field_info)
        # Map alias_generator-produced serialization alias
        alias_gen = model_cls.model_config.get("alias_generator")
        if (
            alias_gen
            and hasattr(alias_gen, "serialization_alias")
            and alias_gen.serialization_alias
        ):
            generated = alias_gen.serialization_alias(field_name)
            if generated:
                alias_to_field[generated] = (field_name, field_info)
    return alias_to_field


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


def prefixed_alias_generator(prefix: str) -> AliasGenerator:
    """Create an AliasGenerator that adds prefixed serialization aliases.

    This enables ``model_dump(by_alias=True)`` to produce prefixed keys
    (e.g., ``event_server_url``) while code still uses unprefixed field
    names (e.g., ``server_url``).

    Note:
        Only ``serialization_alias`` is set here.  Setting ``validation_alias``
        would override pydantic-settings' ``env_prefix``, causing ``.env`` files
        to lose their per-manager prefixes.  Instead, use
        :func:`prefixed_model_validator` on the settings class to accept
        prefixed keys from YAML or keyword arguments.

    Args:
        prefix: The prefix to add (e.g., "event"). Trailing underscores are stripped.

    Returns:
        An AliasGenerator that serializes with the prefixed name.
    """
    prefix = prefix.lower().rstrip("_")
    return AliasGenerator(
        serialization_alias=lambda field_name: f"{prefix}_{field_name}",
    )


def prefixed_model_validator(prefix: str) -> Any:
    """Create a ``model_validator(mode='before')`` that accepts prefixed keys.

    When a shared ``settings.yaml`` uses prefixed keys (e.g.,
    ``event_server_url``), this validator strips the prefix so that the
    model can validate them against unprefixed field names (``server_url``).

    The validator preserves precedence: if both ``server_url`` and
    ``event_server_url`` are present, the unprefixed value wins (since env
    vars, which have higher priority, are resolved to unprefixed names by
    pydantic-settings' ``env_prefix``).

    Usage::

        class EventManagerSettings(ManagerSettings, env_prefix="EVENT_", ...):
            model_config = SettingsConfigDict(
                alias_generator=prefixed_alias_generator("event"),
                populate_by_name=True,
            )
            _accept_prefixed_keys = prefixed_model_validator("event")

    Args:
        prefix: The prefix to strip (e.g., "event"). Trailing underscores
            are stripped; matching is case-insensitive.

    Returns:
        A decorated classmethod suitable for use as a Pydantic model validator.
    """
    prefix_with_underscore = prefix.lower().rstrip("_") + "_"

    @model_validator(mode="before")
    @classmethod
    def _accept_prefixed_keys(cls: type, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        result = dict(data)
        for key in list(result.keys()):
            if key.startswith(prefix_with_underscore):
                unprefixed = key[len(prefix_with_underscore) :]
                if unprefixed in cls.model_fields:
                    if unprefixed not in result:
                        # Only use prefixed value when unprefixed is absent
                        result[unprefixed] = result.pop(key)
                    else:
                        # Unprefixed present (e.g., from env var); drop prefixed
                        del result[key]
        return result

    return _accept_prefixed_keys


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
