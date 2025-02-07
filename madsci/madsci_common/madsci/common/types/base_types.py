"""
Base types for MADSci.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, TypeVar, Union

import yaml
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


class BaseModel(SQLModel, table=False):
    """
    Parent class for all MADSci data models.
    """

    _definition_path: Optional[PathLike] = PrivateAttr(
        default=None,
    )

    model_config = ConfigDict(
        validate_assignment=False,
    )

    def to_yaml(self, path: PathLike, **kwargs: Any) -> None:
        """
        Allows all derived data models to be exported into yaml.

        kwargs are passed to model_dump_json
        """
        with Path(path).open(mode="w") as fp:
            yaml.dump(
                json.loads(self.model_dump_json(**kwargs)),
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
