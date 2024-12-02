"""Command Line Interface for managing MADSci Modules."""

from pathlib import Path
from typing import Optional

import click
from click.core import Context
from rich.console import Console
from rich.pretty import pprint

from madsci.common.types.module_types import (
    NODE_MODULE_CONFIG_TEMPLATES,
    NodeModuleDefinition,
    NodeType,
)
from madsci.common.utils import (
    prompt_for_input,
    prompt_from_list,
    prompt_yes_no,
    save_model,
    search_for_file_pattern,
    to_snake_case,
)

console = Console()


class ModuleContext:
    """Context object for module commands."""

    def __init__(self) -> None:
        """Initialize the context object."""
        self.module: Optional[NodeModuleDefinition] = None
        self.path: Optional[Path] = None
        self.quiet: bool = False


pass_module = click.make_pass_decorator(ModuleContext)


def find_module(name: Optional[str], path: Optional[str]) -> ModuleContext:
    """Find a module by name or path."""
    module_context = ModuleContext()

    if path:
        module_context.path = Path(path)
        if module_context.path.exists():
            module_context.module = NodeModuleDefinition.from_yaml(path)
            return module_context

    module_files = search_for_file_pattern("*.module.yaml")
    for module_file in module_files:
        module_def = NodeModuleDefinition.from_yaml(module_file)
        if not name or module_def.module_name == name:
            module_context.path = Path(module_file)
            module_context.module = module_def
            return module_context

    return module_context


@click.group()
@click.option("--name", "-n", type=str, help="Name of the module.")
@click.option("--path", "-p", type=str, help="Path to the module definition file.")
@click.pass_context
def module(ctx: Context, name: Optional[str], path: Optional[str]) -> None:
    """Manage modules."""
    ctx.obj = find_module(name, path)
    ctx.obj.quiet = ctx.parent.params.get("quiet")


@module.command()
@click.option("--name", "-n", type=str, help="The name of the module.")
@click.option("--path", "-p", type=str, help="The path to the module definition file.")
@click.option("--description", "-d", type=str, help="The description of the module.")
@click.option("--module_type", "-t", type=str, help="The type of the module.")
@click.option(
    "--config_template",
    "-c",
    type=str,
    help="The template of the module configuration to use.",
)
@click.pass_context
def create(  # noqa: PLR0913
    ctx: Context,
    name: Optional[str],
    path: Optional[str],
    description: Optional[str],
    module_type: Optional[str],
    config_template: Optional[str],
) -> None:
    """Create a new module."""
    name = name if name else ctx.parent.params.get("name")
    name = (
        name
        if name
        else prompt_for_input("Module Name", required=True, quiet=ctx.obj.quiet)
    )
    description = (
        description
        if description
        else prompt_for_input("Module Description", quiet=ctx.obj.quiet)
    )
    if not module_type or module_type not in [
        module_type.value for module_type in NodeType
    ]:
        module_type = prompt_from_list(
            "Module Type",
            [module_type.value for module_type in NodeType],
            default=NodeType.DEVICE.value,
            quiet=ctx.obj.quiet,
        )
    config_keys = []
    for key in NODE_MODULE_CONFIG_TEMPLATES:
        config_keys.append(key)
    if not config_template or config_template not in config_keys:
        if prompt_yes_no(
            "Do you want to use a configuration template to add configuration options to your module?",
            default="no",
            quiet=ctx.obj.quiet,
        ):
            template_name = prompt_from_list(
                "Module Configuration Template",
                config_keys,
                default=config_keys[0],
            )
            config_template = NODE_MODULE_CONFIG_TEMPLATES[template_name]
        else:
            config_template = []
    else:
        config_template = NODE_MODULE_CONFIG_TEMPLATES[config_template]

    module_definition = NodeModuleDefinition(
        module_name=name,
        module_description=description,
        module_type=module_type,
        config=config_template,
    )
    console.print(module_definition)

    if not path:
        path = ctx.parent.params.get("path")
    if not path:
        default_path = Path.cwd() / f"{to_snake_case(name)}.module.yaml"
        new_path = prompt_for_input(
            "Path to save Module Definition file",
            default=str(default_path),
            quiet=ctx.obj.quiet,
        )
        if new_path:
            path = Path(new_path)
    save_model(path=path, model=module_definition, overwrite_check=not ctx.obj.quiet)

    console.print()
    console.print(
        f"Created module definition: [bold]{module_definition.module_name}[/] ({path}). Next, you can define your module and add commands to control it with 'madsci module add-command'.",
    )
    console.print(
        "[red]Note:[/] You need to define a node before you can use this module, see 'madsci node create'.",
    )


@module.command()
def list() -> None:
    """List all modules."""
    module_files = search_for_file_pattern("*.module.yaml")

    if module_files:
        for module_file in sorted(set(module_files)):
            module_definition = NodeModuleDefinition.from_yaml(module_file)
            console.print(
                f"[bold]{module_definition.module_name}[/]: {module_definition.module_description} ({module_file})",
            )
    else:
        console.print("No module definitions found")


@module.command()
@pass_module
def info(ctx: ModuleContext) -> None:
    """Get information about a module."""
    if ctx.module:
        pprint(ctx.module)
    else:
        console.print(
            "No module found. Specify module by name or path. If you don't have a module file, you can create one with 'madsci module create'.",
        )


@module.command()
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@pass_module
def delete(ctx: ModuleContext, yes: bool) -> None:
    """Delete a module."""
    if ctx.module and ctx.path:
        console.print(f"Deleting module: {ctx.module.module_name} ({ctx.path})")
        if yes or prompt_yes_no("Are you sure?", quiet=ctx.quiet):
            ctx.path.unlink()
            console.print(f"Deleted {ctx.path}")
    else:
        console.print(
            "No module found. Specify module by name or path. If you don't have a module file, you can create one with 'madsci module create'.",
        )


@module.command()
@pass_module
def validate(ctx: ModuleContext) -> None:
    """Validate a module definition file."""
    if ctx.module:
        console.print(ctx.module)
    else:
        console.print(
            "No module found. Specify module by name or path. If you don't have a module definition file, you can create one with 'madsci module create'.",
        )


@module.command()
@click.option("--command_name", "--name", "-n", type=str, required=False)
@click.option("--command", "-c", type=str, required=False)
@pass_module
def add_command(ctx: ModuleContext, command_name: str, command: str) -> None:
    """Add a command to a module definition."""
    if not ctx.module:
        console.print(
            "No module found. Specify module by name or path. If you don't have a module file, you can create one with 'madsci module create'.",
        )
        return

    if not command_name:
        command_name = prompt_for_input("Command Name", required=True)
    if not command:
        command = prompt_for_input("Command", required=True)

    if ctx.module.commands is None:
        ctx.module.commands = {}

    if command_name in ctx.module.commands:
        console.print(
            f"Command [bold]{command_name}[/] already exists in module definition: [bold]{ctx.module.module_name}[/] ({ctx.path})",
        )
        if not prompt_yes_no("Do you want to overwrite it?", default="no"):
            return

    ctx.module.commands[command_name] = command
    save_model(ctx.path, ctx.module, overwrite_check=False)
    console.print(
        f"Added command [bold]{command_name}[/] to module: [bold]{ctx.module.module_name}[/]",
    )


@module.command()
@click.option("--command_name", "--name", "-n", type=str, required=False)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@pass_module
def delete_command(ctx: ModuleContext, command_name: str, yes: bool) -> None:
    """Delete a command from a module definition."""
    quiet = ctx.quiet or yes
    if not ctx.module:
        console.print(
            "No module found. Specify module by name or path. If you don't have a module file, you can create one with 'madsci module create'.",
        )
        return

    if not command_name:
        command_name = prompt_for_input("Command Name", required=True, quiet=quiet)

    if ctx.module.commands and command_name in ctx.module.commands:
        if yes or prompt_yes_no(
            f"Are you sure you want to delete command [bold]{command_name}[/]?",
            default="no",
            quiet=quiet,
        ):
            del ctx.module.commands[command_name]
            save_model(ctx.path, ctx.module, overwrite_check=False)
            console.print(
                f"Deleted command [bold]{command_name}[/] from module: [bold]{ctx.module.module_name}[/]",
            )
    else:
        console.print(
            f"Command [bold]{command_name}[/] not found in module definition: [bold]{ctx.module.module_name}[/] ({ctx.path})",
        )
