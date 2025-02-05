"""MADSci Configuration Loaders."""

import argparse
from pathlib import Path
from typing import Any, Optional, Union

from madsci.client.event_client import default_logger
from madsci.common.types.base_types import BaseModel
from madsci.common.types.lab_types import (
    LabDefinition,
    ManagerDefinition,
)
from madsci.common.types.node_types import (
    NodeConfig,
    NodeDefinition,
    NodeModuleDefinition,
    get_module_from_node_definition,
)
from madsci.common.utils import search_for_file_pattern, to_snake_case
from pydantic.fields import PydanticUndefined


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
    config_model: type[NodeConfig] = NodeConfig,
    **kwargs: Any,
) -> tuple[NodeDefinition, NodeModuleDefinition, dict[str, Any]]:
    """Node Definition Loader. Supports loading from a definition file, environment variables, and command line arguments, in reverse order of priority (i.e. command line arguments override environment variables, which override definition file values)."""

    # * Load the node definition file
    node_definition = madsci_definition_loader(
        model=model,
        definition_file_pattern=definition_file_pattern,
        **kwargs,
    )
    if not node_definition:
        default_logger.log_error("No Node Definition found.")
        raise ValueError("No Node Definition found.")
    default_logger.log_debug(f"Node Definition: {node_definition}")

    module_definition = get_module_from_node_definition(node_definition)

    config = load_config(config_model, node_definition.config_defaults)

    # * Return the node and module definitions
    return node_definition, module_definition, config


def load_config(
    config_model: type[BaseModel],
    config_defaults: dict[str, Any],
) -> BaseModel:
    """Load configuration values from the command line, based on the config parameters definition"""
    # * Step 1: Create an argparse parser for the node configuration definition
    parser = argparse.ArgumentParser(description="Node Configuration Loader")

    # * Step 2: Parse the command line args
    for field_name, field in config_model.__pydantic_fields__.items():
        default_override = config_defaults.get(field_name)
        default = None
        required = False
        if default_override:
            default = default_override
        elif field.default_factory:
            default = field.default_factory()
        elif field.default and field.default != PydanticUndefined:
            default = field.default
        elif field.is_required():
            required = True
        parser.add_argument(
            f"--{field_name}",
            type=str,
            help=field.description,
            default=default,
            required=required,
        )
    args, _ = parser.parse_known_args()

    # * Step 3: Try to parse the argparser results into a config dictionary
    config_values = config_model.model_validate(args.__dict__)
    default_logger.log_debug(f"Arg Values: {args}")
    default_logger.log_debug(f"Config Values: {config_values}")
    return config_values


def manager_definition_loader(
    model: type[BaseModel] = ManagerDefinition,
    definition_file_pattern: str = "*.*manager.yaml",
    manager_type: Optional[str] = None,
) -> list[ManagerDefinition]:
    """Loads all Manager Definitions available in the current context"""
    manager_definitions = []

    # * Load from any standalone manager definition files
    try:
        manager_definitions = madsci_definition_loader(
            model=model,
            definition_file_pattern=definition_file_pattern,
            cli_arg=None,
            search_for_file=True,
            return_all=True,
        )
    except Exception as e:
        default_logger.log_error(f"Error loading manager definition(s): {e}.")

    # * Load from the lab manager's managers section
    load_managers_from_lab_definition(manager_definitions)

    # * Upgrade to more specific manager types, where possible
    refined_managers = []
    for manager in manager_definitions:
        for manager_submodel in ManagerDefinition.__subclasses__():
            try:
                if to_snake_case(manager.manager_type) == to_snake_case(
                    manager_submodel.__name__
                ):
                    refined_managers.append(manager_submodel.model_validate(manager))
                    break
            except Exception as e:
                default_logger.log_error(
                    f"Error loading manager definition: {e}. Manager: {manager}"
                )
        else:
            refined_managers.append(manager)

    if manager_type:
        return [
            manager
            for manager in refined_managers
            if to_snake_case(manager.manager_type) == to_snake_case(manager_type)
        ]

    return refined_managers


def load_managers_from_lab_definition(
    manager_definitions: list[ManagerDefinition],
) -> None:
    """
    Loads manager definitions from a lab definition file and appends them to the provided list.

    This function attempts to load a lab manager definition using the `lab_definition_loader` function.
    If a lab manager definition is found, it resolves the managers and appends each manager's definition
    to the provided `manager_definitions` list.

    Args:
        manager_definitions (list[ManagerDefinition]): A list to which the loaded manager definitions will be appended.

    Raises:
        Logs an error message if an exception occurs during the loading process.
    """
    try:
        lab_manager_definition = lab_definition_loader(search_for_file=True)
        if lab_manager_definition:
            lab_manager_definition.resolve_managers()
            for manager in lab_manager_definition.managers.values():
                if manager.definition is not None:
                    manager_definitions.append(
                        ManagerDefinition.from_yaml(manager.definition)
                    )
    except Exception as e:
        default_logger.log_error(f"Error loading lab manager definition: {e}.")
