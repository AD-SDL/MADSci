"""Command Line Interface for managing MADSci Nodes."""

import contextlib
import os
from pathlib import Path
from typing import Optional

import click
from click.core import Context
from madsci.common.types.node_types import NodeDefinition, NodeType
from madsci.common.types.workcell_types import WorkcellDefinition
from madsci.common.utils import (
    PathLike,
    prompt_for_input,
    prompt_from_list,
    prompt_yes_no,
    relative_path,
    save_model,
    search_for_file_pattern,
    to_snake_case,
)
from rich.console import Console
from rich.pretty import pprint

console = Console()


class NodeContext:
    """Context object for node commands."""

    def __init__(self) -> None:
        """Initialize the context object."""
        self.node_def: Optional[NodeDefinition] = None
        self.path: Optional[Path] = None
        self.workcell_def: Optional[WorkcellDefinition] = None
        self.quiet: bool = False


pass_node = click.make_pass_decorator(NodeContext)


def find_node_template(name: Optional[str], path: Optional[str]) -> NodeContext:
    """Find a node template by name or path."""
    node_context = NodeContext()

    if path:
        node_context.path = Path(path)
        if node_context.path.exists():
            if path.endswith(".node.template.yaml"):
                node_context.node_def = NodeDefinition.from_yaml(path)
            return node_context

    node_template_files = search_for_file_pattern("*.node.template.yaml")
    for node_template_file in node_template_files:
        with contextlib.suppress(Exception):
            node_def = NodeDefinition.from_yaml(node_template_file)
            if not name or node_def.node_name == name:
                node_context.path = Path(node_template_file)
                node_context.node_def = node_def
                return node_context

    return node_context


def find_node(name: Optional[str], path: Optional[str]) -> NodeContext:
    """Find a node by name or path, including within workcell files."""
    node_context = NodeContext()

    if path:
        node_context.path = Path(path)
        if node_context.path.exists():
            if path.endswith(".node.yaml"):
                node_context.node_def = NodeDefinition.from_yaml(path)
            elif path.endswith(".workcell.yaml"):
                node_context.workcell_def = WorkcellDefinition.from_yaml(path)
                node_context.node_def = find_node_in_workcell(
                    name,
                    node_context.workcell_def,
                )
            return node_context

    node_files = search_for_file_pattern("*.node.yaml")
    for node_file in node_files:
        with contextlib.suppress(Exception):
            node_def = NodeDefinition.from_yaml(node_file)
            if not name or node_def.node_name == name:
                node_context.path = Path(node_file)
                node_context.node_def = node_def
                return node_context

    workcell_files = search_for_file_pattern("*.workcell.yaml")
    for workcell_file in workcell_files:
        with contextlib.suppress(Exception):
            workcell_def = WorkcellDefinition.from_yaml(workcell_file)
            node_def = find_node_in_workcell(name, workcell_def)
            if node_def:
                node_context.path = Path(workcell_file)
                node_context.workcell_def = workcell_def
                node_context.node_def = node_def
                return node_context

    return node_context


def find_node_in_workcell(
    name: Optional[str],
    workcell_def: WorkcellDefinition,
) -> Optional[NodeDefinition]:
    """Find a node definition within a workcell."""
    for node in workcell_def.nodes:
        if isinstance(node, NodeDefinition) and (not name or node.node_name == name):
            return node
        if isinstance(node, str) and node.endswith(".node.yaml"):
            node_def = NodeDefinition.from_yaml(node)
            if not name or node_def.node_name == name:
                return node_def
    return None


@click.group()
@click.option("--name", "-n", type=str, help="The name of the node to operate on.")
@click.option(
    "--path",
    "-p",
    type=str,
    help="The path to the node or workcell definition file.",
)
@click.pass_context
def node(ctx: Context, name: Optional[str], path: Optional[str]) -> None:
    """Manage nodes."""
    ctx.obj = find_node(name, path)
    ctx.obj.quiet = ctx.parent.params.get("quiet")


@node.command()
@click.option("--name", "-n", type=str, help="The name of the node.", required=False)
@click.option(
    "--path",
    "-p",
    type=str,
    help="The path to save the node definition file.",
)
@click.option("--description", "-d", type=str, help="The description of the node.")
@click.option(
    "--template_name",
    type=str,
    help="The name of the node template to use for the node.",
)
@click.option(
    "--template_path",
    type=str,
    help="Path to the node definition template file to use for the node.",
)
@click.option(
    "--standalone",
    "-s",
    is_flag=True,
    help="Don't add node to any workcell.",
)
@click.option(
    "--is_template",
    "-t",
    is_flag=True,
    help="Create a node template.",
)
@click.pass_context
def create(
    ctx: Context,
    name: Optional[str],
    path: Optional[str],
    description: Optional[str],
    template_name: Optional[str],
    template_path: Optional[str],
    standalone: bool,
    is_template: bool,
) -> None:
    """Create a new node."""
    name = name if name else ctx.parent.params.get("name")
    name = (
        name
        if name
        else prompt_for_input("Node Name", required=True, quiet=ctx.obj.quiet)
    )
    description = (
        description
        if description
        else prompt_for_input("Node Description", quiet=ctx.obj.quiet)
    )
    template_definition = get_template_definition(ctx, template_name, template_path)
    if not template_definition and (template_name or template_path):
        return

    if not template_definition:
        module_name = prompt_for_input(
            "Module Name",
            required=True,
            quiet=ctx.obj.quiet,
        )
        node_type = prompt_from_list(
            "Node Type",
            required=False,
            options=[node_type.value for node_type in NodeType],
            default=None,
            quiet=ctx.obj.quiet,
        )
        node_definition = NodeDefinition(
            node_name=name,
            node_description=description,
            is_template=is_template,
            module_name=module_name,
            node_type=node_type,
        )
    else:
        node_definition = NodeDefinition(
            **template_definition.model_dump(exclude={"node_id", "is_template"}),
            node_name=name,
            node_description=description,
            is_template=is_template,
        )
    console.print(node_definition)

    path = path if path else ctx.parent.params.get("path")
    if not path:
        if Path.cwd().name == "nodes":
            default_path = Path.cwd() / f"{to_snake_case(name)}.node.yaml"
        else:
            default_path = Path.cwd() / "nodes" / f"{to_snake_case(name)}.node.yaml"
        new_path = prompt_for_input(
            "Path to save Node Definition file",
            default=str(default_path),
            quiet=ctx.obj.quiet,
        )
        if new_path:
            path = Path(new_path)
        if not path.expanduser().parent.exists():
            console.print(f"Creating directory: {path.parent}")
            path.expanduser().parent.mkdir(parents=True, exist_ok=True)
    save_model(path=path, model=node_definition, overwrite_check=not ctx.obj.quiet)

    # *Handle workcell integration
    if (
        not standalone
        and not is_template
        and prompt_yes_no(
            "Add node to a workcell?",
            default=True,
            quiet=ctx.obj.quiet,
        )
    ):
        add_node_to_workcell(ctx, name, path, node_definition)


def get_template_definition(
    ctx: Context, template_name: Optional[str], template_path: Optional[str]
) -> Optional[NodeDefinition]:
    """Get a node template definition, if applicable."""
    template_definition = None
    if template_name or template_path:
        node_template = find_node_template(template_name, template_path)
        if node_template.node_def:
            template_definition = node_template.node_def
        else:
            console.print(
                f"Node template not found: {template_name or template_path}",
            )
    else:
        node_templates = search_for_file_pattern("*.node.template.yaml")
        if node_templates:
            template_path = prompt_from_list(
                prompt="Node Definition Template Files",
                options=node_templates,
                default=None,
                required=False,
                quiet=ctx.obj.quiet,
            )
            try:
                template_definition = NodeDefinition.from_yaml(template_path)
            except Exception as e:
                console.print(f"Error creating node from template: {e}")
    return template_definition


def add_node_to_workcell(
    ctx: Context,
    name: str,
    path: PathLike,
    node_definition: NodeDefinition,
) -> None:
    """Adds a node definition to a workcell definition's 'nodes' section"""
    workcell_files = search_for_file_pattern("*.workcell.yaml")
    if workcell_files:
        if ctx.obj.quiet:
            # *In quiet mode, automatically add to first workcell
            workcell_path = workcell_files[0]
        else:
            workcell_path = prompt_from_list(
                prompt="Add node to workcell",
                options=workcell_files,
                default=workcell_files[0],
            )

        if workcell_path:
            workcell_def = WorkcellDefinition.from_yaml(workcell_path)
            # *Calculate relative path from workcell to node
            workcell_dir = Path(workcell_path).parent
            rel_path = str(
                relative_path(target=path.absolute(), source=workcell_dir.absolute()),
            )

            # *Add node to workcell if not already present
            workcell_def.nodes[node_definition.node_name] = rel_path
            save_model(workcell_path, workcell_def, overwrite_check=False)
            console.print(
                f"Added node [bold]{name}[/] to workcell: [bold]{workcell_path}[/]",
            )


@node.command()
def list() -> None:
    """List all nodes, including those in workcell files."""
    node_files = search_for_file_pattern("*.node.yaml")
    workcell_files = search_for_file_pattern("*.workcell.yaml")

    nodes_found = False

    if node_files:
        for node_file in sorted(set(node_files)):
            node_definition = NodeDefinition.from_yaml(node_file)
            console.print(
                f"[bold]{node_definition.node_name}[/]: {node_definition.node_description} ({node_file})",
            )
            nodes_found = True

    for workcell_file in workcell_files:
        workcell_def = WorkcellDefinition.from_yaml(workcell_file)
        for node in workcell_def.nodes:
            if isinstance(node, NodeDefinition):
                console.print(
                    f"[bold]{node.node_name}[/]: {node.node_description} (in {workcell_file})",
                )
                nodes_found = True

    if not nodes_found:
        console.print("No node definitions found")


@node.command()
@pass_node
def info(ctx: NodeContext) -> None:
    """Get information about a node."""
    if ctx.node_def:
        pprint(ctx.node_def)
    else:
        console.print(
            "No node found. Specify node by name or path. If you don't have a node file, you can create one with 'madsci node create'.",
        )


@node.command()
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@pass_node
def delete(ctx: NodeContext, yes: bool) -> None:
    """Delete a node."""
    if ctx.node_def and ctx.path:
        console.print(f"Deleting node: {ctx.node_def.node_name} ({ctx.path})")
        if yes or ctx.quiet or prompt_yes_no("Are you sure?"):
            # First find all workcells that contain this node
            workcell_files = search_for_file_pattern("*.workcell.yaml")
            for workcell_file in workcell_files:
                workcell_def = WorkcellDefinition.from_yaml(workcell_file)
                if ctx.node_def.node_name in workcell_def.nodes and (
                    yes
                    or ctx.quiet
                    or prompt_yes_no(
                        f"Remove from workcell [bold]{workcell_def.name}[/] ([italic]{workcell_file}[/])?",
                        default=True,
                    )
                ):
                    del workcell_def.nodes[ctx.node_def.node_name]
                    save_model(workcell_file, workcell_def, overwrite_check=False)
                    console.print(f"Removed from workcell: {workcell_file}")

            # Finally delete the node file
            ctx.path.unlink()
            console.print(f"Deleted {ctx.path}")
    else:
        console.print(
            "No node found. Specify node by name or path. If you don't have a node file, you can create one with 'madsci node create'.",
        )


@node.command()
@pass_node
def validate(ctx: NodeContext) -> None:
    """Validate a node definition file."""
    if ctx.node_def:
        console.print(ctx.node_def)
    else:
        console.print(
            "No node found. Specify node by name or path. If you don't have a node definition file, you can create one with 'madsci node create'.",
        )


@node.command()
@click.option("--command_name", "--name", "-n", type=str, required=False)
@click.option("--command", "-c", type=str, required=False)
@pass_node
def add_command(ctx: NodeContext, command_name: str, command: str) -> None:
    """Add a command to a node definition."""
    if not ctx.node_def:
        console.print(
            "No node found. Specify node by name or path. If you don't have a node file, you can create one with 'madsci node create'.",
        )
        return

    if not command_name:
        command_name = prompt_for_input(
            "Command Name",
            required=True,
            quiet=ctx.obj.quiet,
        )
    if not command:
        command = prompt_for_input("Command", required=True, quiet=ctx.obj.quiet)

    if command_name in ctx.node_def.commands:
        console.print(
            f"Command [bold]{command_name}[/] already exists in node definition: [bold]{ctx.node_def.node_name}[/] ({ctx.path})",
        )
        if not prompt_yes_no(
            "Do you want to overwrite it?",
            default="no",
            quiet=ctx.quiet,
        ):
            return

    ctx.node_def.commands[command_name] = command
    save_model(ctx.path, ctx.node_def, overwrite_check=False)
    console.print(
        f"Added command [bold]{command_name}[/] to node: [bold]{ctx.node_def.node_name}[/]",
    )


@node.command()
@click.argument("command_name", type=str)
@pass_node
def run(ctx: NodeContext, command_name: str) -> None:
    """Run a command in a node."""
    if not ctx.node_def:
        console.print(
            "No node found. Specify node by name or path. If you don't have a node file, you can create one with 'madsci node create'.",
        )
        return

    if command_name in ctx.node_def.commands:
        command = ctx.node_def.commands[command_name]
        console.print(
            f"Running command: [bold]{command_name}[/] ({command}) in node: [bold]{ctx.node_def.node_name}[/] ({ctx.path})",
        )
        print(os.popen(command).read())  # noqa: S605,T201
    else:
        console.print(
            f"Command [bold]{command_name}[/] not found in node definition: [bold]{ctx.node_def.node_name}[/] ({ctx.path})",
        )


@node.command()
@click.argument("command_name", type=str, required=False)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@pass_node
def delete_command(ctx: NodeContext, command_name: str, yes: bool) -> None:
    """Delete a command from a node definition."""
    if not ctx.node_def:
        console.print(
            "No node found. Specify node by name or path. If you don't have a node file, you can create one with 'madsci node create'.",
        )
        return

    if not command_name:
        if not ctx.node_def.commands:
            console.print("No commands found in node definition.")
            return
        command_name = prompt_from_list(
            "Select command to delete",
            options=list(ctx.node_def.commands.keys()),
            required=True,
            quiet=ctx.obj.quiet,
        )

    if command_name in ctx.node_def.commands:
        if (
            yes
            or ctx.quiet
            or prompt_yes_no(
                f"Are you sure you want to delete command [bold]{command_name}[/]?",
                default="no",
                quiet=ctx.obj.quiet,
            )
        ):
            del ctx.node_def.commands[command_name]
            save_model(ctx.path, ctx.node_def, overwrite_check=False)
            console.print(
                f"Deleted command [bold]{command_name}[/] from node: [bold]{ctx.node_def.node_name}[/]",
            )
    else:
        console.print(
            f"Command [bold]{command_name}[/] not found in node definition: [bold]{ctx.node_def.node_name}[/] ({ctx.path})",
        )
