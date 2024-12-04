"""MADSci Configuration Loaders."""

import argparse
import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from madsci.common.types.base_types import BaseModel
from madsci.common.types.node_types import (
    NodeDefinition,
    NodeModuleDefinition,
    get_module_from_node_definition,
)
from madsci.common.types.squid_types import LabDefinition
from madsci.common.utils import search_for_file_pattern


def madsci_definition_loader(
    model: type[BaseModel] = BaseModel,
    definition_file_pattern: str = "*.yaml",
    search_for_file: bool = True,
) -> BaseModel:
    """MADSci Definition Loader. Supports loading from a definition file, environment variables, and command line arguments, in reverse order of priority (i.e. command line arguments override environment variables, which override definition file values)."""

    # Load environment variables from a .env file
    load_dotenv()

    parser = argparse.ArgumentParser(description="MADSci Definition Loader")
    parser.add_argument(
        "--definition",
        type=Path,
        help="The path to the MADSci configuration file.",
    )
    args, _ = parser.parse_known_args()
    definition_file = args.definition
    if not definition_file:
        if not search_for_file:
            raise ValueError(
                "Definition file not specified, please specify a definition file using the --definition argument.",
            )

        # *Load from definition file
        if search_for_file:
            definition_files = search_for_file_pattern(
                definition_file_pattern,
                parents=True,
                children=True,
            )
            if not definition_files:
                raise ValueError(
                    f"No definition files found matching pattern: {definition_file_pattern}. Please specify a valid configuration file path using the --definition argument.",
                )

        definition_file = definition_files[0]

    return model.from_yaml(definition_file)


def lab_definition_loader(
    model: type[BaseModel] = LabDefinition,
    definition_file_pattern: str = "*.lab.yaml",
    **kwargs: Any,
) -> LabDefinition:
    """Lab Definition Loader. Supports loading from a definition file, environment variables, and command line arguments, in reverse order of priority (i.e. command line arguments override environment variables, which override definition file values)."""
    definition = madsci_definition_loader(
        model=model,
        definition_file_pattern=definition_file_pattern,
        **kwargs,
    )
    for field_name, field in definition.lab_config.model_fields.items():
        parser = argparse.ArgumentParser(
            description=f"MADSci Lab Definition Loader for {field_name}",
        )
        parser.add_argument(
            f"--{field_name}",
            type=str,
            help=f"[{field.annotation}] {field.description}",
            default=None,
        )
    args, _ = parser.parse_known_args()
    for field_name in definition.lab_config.model_fields:
        if getattr(args, field_name) is not None:
            setattr(
                definition.lab_config,
                field_name,
                json.loads(getattr(args, field_name)),
            )
    definition.model_validate(definition)
    return definition


def node_definition_loader(
    model: type[BaseModel] = NodeDefinition,
    definition_file_pattern: str = "*.node.yaml",
    **kwargs: Any,
) -> tuple[NodeDefinition, NodeModuleDefinition, dict[str, Any]]:
    """Node Definition Loader. Supports loading from a definition file, environment variables, and command line arguments, in reverse order of priority (i.e. command line arguments override environment variables, which override definition file values)."""

    # * Load the node definition file
    node_definition = madsci_definition_loader(
        model=model,
        definition_file_pattern=definition_file_pattern,
        **kwargs,
    )

    module_definition = get_module_from_node_definition(node_definition)

    combined_config = node_definition.config.copy()

    # * Import any module config from the module definition
    for config_name, config in module_definition.config.items():
        # * Only add the config if it isn't already defined in the node definition
        if config_name not in node_definition.config:
            combined_config[config_name] = config

    # * Load the node configuration from the command line
    parser = argparse.ArgumentParser(description="MADSci Node Definition Loader")
    for field_name, field in combined_config.items():
        parser.add_argument(
            f"--{field_name}",
            type=str,
            help=field.description,
            default=field.default,
            required=False,
        )
    args, _ = parser.parse_known_args()
    config_values = {}
    for arg_name, arg_value in vars(args).items():
        if arg_value is not None:
            try:
                config_values[arg_name] = json.loads(str(arg_value))
            except json.JSONDecodeError:
                config_values[arg_name] = arg_value
        else:
            config_values[arg_name] = field.default

    # * Return the node and module definitions
    return node_definition, module_definition, config_values
