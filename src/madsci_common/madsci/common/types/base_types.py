"""
Base types for MADSci.
"""

from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, ClassVar, Optional, TypeVar, Union

import yaml
from pydantic import BaseModel, Field
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

_T = TypeVar("_T")

PathLike = Union[str, Path]


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
        _env_parse_none_str="None",
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

    def to_mongo(self) -> dict[str, Any]:
        """
        Convert the model to a MongoDB-compatible dictionary.
        """
        json_data = self.model_dump(mode="json", by_alias=True)
        for field in self.__pydantic_fields__:
            if field in self._mongo_excluded_fields:
                json_data.pop(field, None)
        return json_data


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
