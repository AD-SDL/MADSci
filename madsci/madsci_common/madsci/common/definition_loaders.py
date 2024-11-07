"""MADSci Configuration Loaders."""

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from madsci.common.types.base_types import BaseModel
from madsci.common.types.module_types import ModuleDefinition
from madsci.common.types.node_types import NodeDefinition
from madsci.common.types.squid_types import LabDefinition
from madsci.common.utils import search_for_file_pattern


def madsci_definition_loader(
    model=BaseModel, definition_file_pattern: str = "*.yaml", **kwargs
) -> BaseModel:
    """MADSci Definition Loader. Supports loading from a definition file, environment variables, and command line arguments, in reverse order of priority (i.e. command line arguments override environment variables, which override definition file values)."""

    # Load environment variables from a .env file
    load_dotenv()

    parser = argparse.ArgumentParser(description="MADSci Definition Loader")
    parser.add_argument(
        "--definition", type=Path, help="The path to the MADSci configuration file."
    )
    for field_name, field in model.model_fields.items():
        parser.add_argument(
            f"--{field_name}",
            type=str,
            help=f"[{field.annotation}] {field.description}",
            default=None,
        )
    args = parser.parse_args()
    definition_file = args.definition

    # *Load from definition file
    if not definition_file:
        definition_files = search_for_file_pattern(
            definition_file_pattern, parents=True, children=True
        )

        if not definition_files:
            raise ValueError(
                f"No configuration files found matching pattern: {definition_file_pattern}. Please specify a valid configuration file path using the --definition argument."
            )

        definition_file = definition_files[0]

    model_instance = model.from_yaml(definition_file)

    # *Load from environment variables
    for field_name in model.model_fields.keys():
        env_var = f"MADSCI_{model.__name__.upper()}_{field_name.upper()}"
        if env_var in os.environ:
            print(f"Loading {field_name} from environment variable {env_var}")
            kwargs[field_name] = json.loads(os.environ[env_var])

    # *Load from command line arguments
    for field_name in model.model_fields.keys():
        if field_name in args and args[field_name] is not None:
            print(f"Loading {field_name} from command line argument {args[field_name]}")
            kwargs[field_name] = json.loads(args[field_name])

    # *Override with kwargs
    for field_name, field in kwargs.items():
        setattr(model_instance, field_name, field)

    return model.model_validate(model_instance)


def lab_definition_loader(
    model=LabDefinition, definition_file_pattern: str = "*.lab.yaml", **kwargs
) -> LabDefinition:
    """Lab Definition Loader. Supports loading from a definition file, environment variables, and command line arguments, in reverse order of priority (i.e. command line arguments override environment variables, which override definition file values)."""
    return madsci_definition_loader(
        model=model, definition_file_pattern=definition_file_pattern, **kwargs
    )


def module_definition_loader(
    model=ModuleDefinition, definition_file_pattern: str = "*.module.yaml", **kwargs
) -> ModuleDefinition:
    """Module Definition Loader. Supports loading from a definition file, environment variables, and command line arguments, in reverse order of priority (i.e. command line arguments override environment variables, which override definition file values)."""
    return madsci_definition_loader(
        model=model, definition_file_pattern=definition_file_pattern, **kwargs
    )


def node_definition_loader(
    model=NodeDefinition, definition_file_pattern: str = "*.node.yaml", **kwargs
) -> NodeDefinition:
    """Node Definition Loader. Supports loading from a definition file, environment variables, and command line arguments, in reverse order of priority (i.e. command line arguments override environment variables, which override definition file values)."""
    return madsci_definition_loader(
        model=model, definition_file_pattern=definition_file_pattern, **kwargs
    )
