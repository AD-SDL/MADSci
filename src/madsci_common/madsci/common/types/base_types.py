"""
Base types for MADSci.
"""

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, ClassVar, Generic, Optional, TypeVar, Union

import yaml
from pydantic import AnyUrl, model_validator
from pydantic.config import ConfigDict
from pydantic.fields import PrivateAttr, PydanticUndefined
from sqlmodel import Field, SQLModel
from ulid import ULID

_T = TypeVar("_T")

PathLike = Union[str, Path]


def new_ulid_str() -> str:
    """
    Generate a new ULID string.
    """
    return str(ULID())


@dataclass
class LoadConfig:
    """
    Configuration for how a model field should be loaded from a definition file, command line arg, or environment variable.
    """

    use_fields_as_cli_args: bool = False
    """Whether to use this field's model's fields as CLI arguments."""
    use_fields_as_env_vars: bool = False
    """Whether to use this field's model's fields as environment variables."""


class BaseModel(SQLModel, use_enum_values=True):
    """
    Parent class for all MADSci data models.
    """

    _definition_path: Optional[PathLike] = PrivateAttr(
        default=None,
    )
    """The path from which this model was loaded."""
    _definition_file_patterns: ClassVar[list[str]] = []
    """File patterns to search for when loading the model definition from a file."""
    _definition_cli_flags: ClassVar[list[str]] = ["--definition"]
    """CLI flags to use when loading the model definition from a file."""
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
        with Path(path).expanduser().open(mode="w") as fp:
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
        with Path(path).expanduser().open() as fp:
            raw_data = yaml.safe_load(fp)
        model_instance = cls.model_validate(raw_data)
        model_instance._definition_path = path
        return model_instance

    def to_mongo(self) -> dict[str, Any]:
        """
        Convert the model to a MongoDB-compatible dictionary.
        """
        json_data = self.model_dump(mode="json", by_alias=True)
        for field in self.__pydantic_fields__:
            if field in self._mongo_excluded_fields:
                json_data.pop(field, None)
        return json_data

    @classmethod
    def load_model(
        cls: type[_T],
        default_path: Optional[PathLike] = None,
        search_filesystem: Optional[bool] = True,
        require_unique: Optional[bool] = False,
        path_from_cli_arg: Optional[bool] = True,
        set_fields_from_cli: Optional[bool] = True,
    ) -> _T:
        """
        Load a model from a definition file, optionally setting fields via
        command line and environment variable overrides.
        """
        from madsci.client.event_client import default_logger

        model_instance = None

        # * Load definition via CLI argument(s) defined in model
        if path_from_cli_arg:
            model_instance = cls.load_from_file_path()

        # * Load definition from filesystem search, looking for files matching the model's definition file pattern(s)
        if search_filesystem and model_instance is None:
            model_instance = cls.search_for_definition_file(require_unique)

        # * Load definition from default path
        if model_instance is None and default_path:
            try:
                path = Path(default_path)
                if path.exists():
                    model_instance = cls.from_yaml(path)
            except Exception as e:
                default_logger.log_error(
                    f"Failed to load model {cls.__name__} from {path}: {e}"
                )

        # TODO: Set fields from environment variables

        if set_fields_from_cli:
            definition_path = (
                model_instance._definition_path if model_instance else None
            )
            model_instance = cls.set_fields_from_cli(model_instance)
            model_instance._definition_path = definition_path

        # * If no definition was loaded, raise an error
        if model_instance is None:
            raise ValueError(f"Failed to load model {cls.__name__}")
        return model_instance

    @classmethod
    def search_for_definition_file(cls, require_unique: bool = False) -> _T:
        """
        Searches for a definition file for this model on the filesystem.
        Matching files are determined by the class variable _definition_file_patterns.
        """
        from madsci.client.event_client import default_logger
        from madsci.common.utils import search_for_file_pattern

        model_instance = None

        definition_files = []
        try:
            for pattern in cls._definition_file_patterns:
                definition_files.extend(
                    search_for_file_pattern(pattern, parents=True, children=True)
                )
            validated_definitions = []
            for definition_file in definition_files:
                try:
                    validated_definitions.append(cls.from_yaml(definition_file))
                except Exception as e:
                    default_logger.log_debug(
                        f"Failed to load model {cls.__name__} from {definition_file}: {e}"
                    )
            if require_unique and len(validated_definitions) > 1:
                raise ValueError(
                    f"Multiple definitions found for {cls.__name__}: {[vd._definition_path for vd in validated_definitions]}"
                )
            if len(validated_definitions) == 0:
                raise FileNotFoundError(
                    f"No valid definition files found for {cls.__name__}"
                )
            model_instance = validated_definitions[0]
        except Exception as e:
            default_logger.log_error(
                f"Failed to load model {cls.__name__} from filesystem search: {e}"
            )
        return model_instance

    @classmethod
    def load_from_file_path(cls: _T) -> _T:
        """
        Loads the model from a definition file who's path is specifed by CLI arg.
        The flag(s) are determined by the class variable _definition_cli_flags.
        """
        from madsci.client.event_client import default_logger

        model_instance = None

        if not cls._definition_cli_flags:
            default_logger.log_warning(
                "No CLI flags defined for model definition, but path_from_cli_arg is True."
            )
        else:
            parser = argparse.ArgumentParser()
            parser.add_argument(
                *cls._definition_cli_flags,
                type=str,
                help="Path to the model definition.",
                dest="definition",
            )
            args, _ = parser.parse_known_args()
            if args.definition:
                try:
                    model_instance = cls.from_yaml(args.definition)
                except Exception as e:
                    default_logger.log_error(
                        f"Failed to load model {cls.__name__} from {args.definition}: {e}"
                    )

        return model_instance

    @classmethod
    def set_fields_from_cli(
        cls: type[_T],
        model_instance: Optional[_T] = None,
        override_defaults: dict[str, Any] = {},
    ) -> _T:
        """
        Set fields for this model from CLI arguments.

        Args:
            model_instance: Updates this model instance from the CLI if passed, otherwise
                creates a new instance.
            override_defaults: A dictionary mapping field names to default values, to override the model's own defaults.
        """
        parser = argparse.ArgumentParser()
        combined_defaults = {}
        if model_instance is not None:
            combined_defaults = model_instance.model_dump(
                mode="json", exclude_unset=True
            )
        combined_defaults.update(override_defaults)
        field_hierarchy = cls._parser_from_fields(parser, combined_defaults)
        args, _ = parser.parse_known_args()
        return cls._from_cli_args(args, field_hierarchy)

    @classmethod
    def _add_to_parser(
        cls: type[_T],
        field: Any,
        field_name: str,
        parser: argparse.ArgumentParser,
        defaults: dict[str, Any] = {},
    ) -> None:
        """adds arguments to parser"""
        default = None
        required = False
        if field_name in defaults:
            default = defaults[field_name]
        elif field.default_factory:
            default = field.default_factory()
        elif field.default != PydanticUndefined:
            default = field.default
        elif field.is_required():
            required = True
        parser.add_argument(
            f"--{field_name}",
            help=field.description,
            default=default,
            required=required,
        )

    @classmethod
    def _parser_from_fields(
        cls: type[_T],
        parser: argparse.ArgumentParser,
        override_defaults: dict[str, Any] = {},
    ) -> dict[str, str]:
        """
        Extract CLI arguments from this model's fields. Adds arguments to the passed-in ArgumentParser, and returns a nested dictionary mapping arg keys to fields for later reconstruction.
        """
        field_hierarchy = {}
        for field_name, field in cls.__pydantic_fields__.items():
            # * Check if the field is a model that we should use the sub-fields of
            for info in field.metadata:
                if isinstance(info, LoadConfig) and info.use_fields_as_cli_args:
                    # * Add sub-model's fields as individual CLI arguments
                    cls._add_to_parser(field, field_name, parser, override_defaults)
                    field_hierarchy[field_name] = field.annotation._parser_from_fields(
                        parser, override_defaults.get(field_name, {})
                    )
                    break
            else:
                # * Otherwise, add the field as a CLI argument
                cls._add_to_parser(field, field_name, parser, override_defaults)
                field_hierarchy[field_name] = field_name
        return field_hierarchy

    @classmethod
    def _from_cli_args(
        cls: type[_T], args: argparse.Namespace, field_hierarchy: dict
    ) -> _T:
        """
        Create a model instance from CLI arguments. Recursively construct sub-models as needed.
        """
        field_values = {}
        for field_name, _ in cls.__pydantic_fields__.items():
            if field_name in args:
                if isinstance(field_hierarchy.get(field_name), dict):
                    field_values[field_name] = cls.__pydantic_fields__[
                        field_name
                    ].annotation._from_cli_args(args, field_hierarchy[field_name])
                else:
                    field_values[field_name] = getattr(args, field_name)
        return cls(**field_values)


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
        default=None,
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


PositiveInt = Annotated[int, Field(ge=0)]
PositiveNumber = Annotated[Union[float, int], Field(ge=0)]
