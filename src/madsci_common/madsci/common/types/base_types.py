"""
Base types for MADSci.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, Generic, Optional, TypeVar, Union

import yaml
from pydantic import AnyUrl, model_validator
from pydantic.config import ConfigDict
from pydantic.fields import PrivateAttr
from sqlmodel import SQLModel
from sqlmodel.main import Field
from ulid import ULID

_T = TypeVar("_T")

PathLike = Union[str, Path]


def new_ulid_str() -> str:
    """
    Generate a new ULID string.
    """
    return str(ULID())


class BaseModel(SQLModel, use_enum_values=True):
    """
    Parent class for all MADSci data models.
    """

    _definition_path: Optional[PathLike] = PrivateAttr(
        default=None,
    )
    _mongo_excluded_fields: ClassVar[list[str]] = []
    """Fields to exclude from insertion into MongoDB."""

    model_config = ConfigDict(
        validate_assignment=True,
    )

    def to_yaml(self, path: PathLike, by_alias: bool = True, **kwargs: Any) -> None:
        """
        Allows all derived data models to be exported into yaml.

        kwargs are passed to model_dump_json
        """
        with Path(path).open(mode="w") as fp:
            yaml.dump(
                self.model_dump(mode="json", by_alias=by_alias, **kwargs),
                fp,
                indent=2,
                sort_keys=False,
            )

    @classmethod
    def from_yaml(cls: type[_T], path: PathLike) -> _T:
        """
        Allows all derived data models to be loaded from yaml.
        """
        with Path(path).open() as fp:
            raw_data = yaml.safe_load(fp)
        model_instance = cls.model_validate(raw_data)
        model_instance._definition_path = path
        return model_instance

    def to_mongo(self) -> dict[str, Any]:
        """
        Convert the model to a MongoDB-compatible dictionary.
        """
        json_data = self.model_dump(mode="json", by_alias=True)
        for field in self.model_fields:
            if field in self._mongo_excluded_fields:
                json_data.pop(field, None)
        return json_data


class ModelLink(BaseModel, Generic[_T]):
    """
    Link to another MADSci object
    """

    url: Optional[AnyUrl] = Field(
        title="Model Definition URL",
        description="The URL to the modeled object.",
        default=None,
    )
    path: Optional[PathLike] = Field(
        title="Model Definition Path",
        description="The path to the model definition.",
        default=None,
    )
    definition: Optional[_T] = Field(
        title="Model Definition",
        description="The actual definition of the model.",
    )

    @model_validator(mode="after")
    def check(self) -> "ModelLink[_T]":
        """
        Ensure that at least one field is set.
        """
        if self.url is None and self.path is None and self.definition is None:
            raise ValueError(
                "At least one field of the link (url, path, or definition) must be set."
            )
        return self

    def resolve(self, path_origin: PathLike = "./") -> "ModelLink[_T]":
        """
        Resolve the link to the actual definition.
        """
        if self.definition is None:
            if self.path:
                if Path(self.path).is_absolute():
                    self.definition = self.definition.from_yaml(self.path)
                else:
                    self.definition = self.definition.from_yaml(
                        Path(path_origin) / self.path
                    )
            if self.url:
                # TODO: Fetch the definition from the URL
                pass


class Error(BaseModel):
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
