"""MADSci Configuration Loaders."""

import argparse
from pathlib import Path
from typing import Any, Optional, Union

from madsci.client.event_client import default_logger
from madsci.common.types.base_types import BaseModel
from madsci.common.types.config_types import (
    ConfigNamespaceDefinition,
    ConfigParameterDefinition,
)
from madsci.common.types.node_types import (
    NodeDefinition,
    NodeModuleDefinition,
    get_module_from_node_definition,
)
from madsci.common.types.squid_types import (
    MANAGER_TYPE_DEFINITION_MAP,
    LabDefinition,
    ManagerDefinition,
)
from madsci.common.utils import search_for_file_pattern
from pydantic import AnyUrl


def madsci_definition_loader(
    model: type[BaseModel] = BaseModel,
    definition_file_pattern: str = "*.yaml",
    search_for_file: bool = True,
    return_all: bool = False,
    cli_arg: Optional[str] = "definition",
) -> Optional[Union[BaseModel, list[BaseModel]]]:
    """MADSci Definition Loader. Supports loading from a definition file, environment variables, and command line arguments, in reverse order of priority (i.e. command line arguments override environment variables, which override definition file values)."""

    definition_files = []
    if cli_arg:
        parser = argparse.ArgumentParser(description="MADSci Definition Loader")
        parser.add_argument(
            f"--{cli_arg}",
            type=Path,
            help="The path to the MADSci configuration file.",
        )
        args, _ = parser.parse_known_args()
        if args.definition:
            definition_files.append(args.definition)

    # *Load from definition file
    if search_for_file:
        definition_files.extend(
            search_for_file_pattern(
                definition_file_pattern,
                parents=True,
                children=True,
            )
        )

    if return_all:
        return [model.from_yaml(file) for file in definition_files]
    return model.from_yaml(definition_files[0]) if definition_files else None


def lab_definition_loader(
    model: type[BaseModel] = LabDefinition,
    definition_file_pattern: str = "*.lab.yaml",
    **kwargs: Any,
) -> LabDefinition:
    """Lab Definition Loader. Supports loading from a definition file, environment variables, and command line arguments, in reverse order of priority (i.e. command line arguments override environment variables, which override definition file values)."""
    return madsci_definition_loader(
        model=model,
        definition_file_pattern=definition_file_pattern,
        **kwargs,
    )


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
    default_logger.log_debug(f"Node Definition: {node_definition}")

    module_definition = get_module_from_node_definition(node_definition)

    config_definition = node_definition.config.copy()

    # * Import any module config from the module definition
    for config_name, config in module_definition.config.items():
        # * Only add the config if it isn't already defined in the node definition
        if config_name not in node_definition.config:
            config_definition[config_name] = config

    config_values = load_config(config_definition)

    # * Return the node and module definitions
    return node_definition, module_definition, config_values


def load_config(
    config_definition: dict[
        str, Union[ConfigParameterDefinition, ConfigNamespaceDefinition]
    ],
) -> dict[str, Any]:
    """Load configuration values from the command line, based on the config parameters definition"""
    # * Step 1: Create an argparse parser for the node configuration definition
    parser = argparse.ArgumentParser(description="MADSci Node Definition Loader")

    # * Step 2: Parse the command line args
    for field_name, field in config_definition.items():
        build_argparser_from_config_definition(parser, field_name, field)
    args, _ = parser.parse_known_args()

    # * Step 3: Try to parse the argparser results into a config dictionary
    config_values = parse_args_to_config(config_definition, args)
    default_logger.log_debug(f"Arg Values: {args}")
    default_logger.log_debug(f"Config Values: {config_values}")
    return config_values


def build_argparser_from_config_definition(
    parser: argparse.ArgumentParser,
    field_name: str,
    field: Union[ConfigParameterDefinition, ConfigNamespaceDefinition],
) -> None:
    """Creates argparse args for each config parameter, recursively for nested namespaces"""
    if isinstance(field, ConfigNamespaceDefinition):
        for sub_field_name, sub_field in field.parameters.items():
            build_argparser_from_config_definition(
                parser, f"{field_name}_{sub_field_name}", sub_field
            )
    else:
        parser.add_argument(
            f"--{field_name}",
            type=str,
            help=field.description,
            default=field.default if hasattr(field, "default") else None,
            required=False,
        )


def parse_args_to_config(
    config_definition: dict[
        str, Union[ConfigParameterDefinition, ConfigNamespaceDefinition]
    ],
    args: argparse.Namespace,
    prefix: str = "",
) -> dict[str, Any]:
    """Parses argparse args into a config dictionary, recursively for nested namespaces."""
    config_values = {}
    for field_name, field in config_definition.items():
        if isinstance(field, ConfigNamespaceDefinition):
            config_values[field_name] = parse_args_to_config(
                field.parameters, args, prefix=f"{prefix}{field_name}_"
            )
        else:
            config_values[field_name] = getattr(args, f"{prefix}{field_name}")
    return config_values


def manager_definition_loader(
    model: type[BaseModel] = ManagerDefinition,
    definition_file_pattern: str = "*.*manager.yaml",
) -> list[ManagerDefinition]:
    """Loads all Manager Definitions available in the current context"""

    # * Load from any standalone manager definition files
    manager_definitions = madsci_definition_loader(
        model=model,
        definition_file_pattern=definition_file_pattern,
        cli_arg=None,
        search_for_file=True,
        return_all=True,
    )

    # * Load from the lab manager's managers section
    lab_manager_definition = lab_definition_loader(search_for_file=True)
    if lab_manager_definition:
        for manager in lab_manager_definition.managers.values():
            if isinstance(manager, ManagerDefinition):
                manager_definitions.append(manager)
            elif isinstance(manager, AnyUrl):
                # TODO: Support querying manager definition from URL, skip for now
                pass
            elif isinstance(manager, (Path, str)):
                manager_definitions.append(ManagerDefinition.from_yaml(manager))

    # * Upgrade to more specific manager types, where possible
    refined_managers = []
    for manager in manager_definitions:
        if manager.manager_type in MANAGER_TYPE_DEFINITION_MAP:
            refined_managers.append(
                MANAGER_TYPE_DEFINITION_MAP[manager.manager_type].model_validate(
                    manager
                )
            )
        else:
            refined_managers.append(manager)

    return refined_managers
