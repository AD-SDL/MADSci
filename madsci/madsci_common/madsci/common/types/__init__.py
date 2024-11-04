"""
Base types for MADSci.
"""

import json
from pathlib import Path
from typing import Type, TypeVar, Union

import yaml
from sqlmodel import SQLModel
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

    def to_yaml(self, path: PathLike) -> None:
        """
        Allows all derived data models to be exported into yaml.
        """
        with open(path, mode="w") as fp:
            yaml.dump(json.loads(self.model_dump_json()), fp, indent=2, sort_keys=False)

    @classmethod
    def from_yaml(cls: Type[_T], path: PathLike) -> _T:
        """
        Allows all derived data models to be loaded from yaml.
        """
        with open(path) as fp:
            raw_data = yaml.safe_load(fp)
        return cls(**raw_data)
