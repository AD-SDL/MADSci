"""Command Line Interface for managing MADSci Nodes."""

from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.pretty import pprint

from madsci.common.types.module_types import ModuleDefinition
from madsci.common.types.node_types import NodeDefinition
from madsci.common.types.workcell_types import WorkcellDefinition
from madsci.common.utils import (
    prompt_for_input,
    prompt_from_list,
    prompt_yes_no,
    save_model,
    search_for_file_pattern,
    to_snake_case,
)

console = Console()


class NodeContext:
    """Context object for node commands."""

    def __init__(self):
        """Initialize the context object."""
        self.node_def: Optional[NodeDefinition] = None
        self.path: Optional[Path] = None
        self.workcell_def: Optional[WorkcellDefinition] = None


pass_node = click.make_pass_decorator(NodeContext)


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
                    name, node_context.workcell_def
                )
            return node_context

    node_files = search_for_file_pattern("*.node.yaml")
    for node_file in node_files:
        node_def = NodeDefinition.from_yaml(node_file)
        if node_def.node_name == name:
            node_context.path = Path(node_file)
            node_context.node_def = node_def
            return node_context

    workcell_files = search_for_file_pattern("*.workcell.yaml")
    for workcell_file in workcell_files:
        workcell_def = WorkcellDefinition.from_yaml(workcell_file)
        node_def = find_node_in_workcell(name, workcell_def)
        if node_def:
            node_context.path = Path(workcell_file)
            node_context.workcell_def = workcell_def
            node_context.node_def = node_def
            return node_context

    return node_context


def find_node_in_workcell(
    name: Optional[str], workcell_def: WorkcellDefinition
) -> Optional[NodeDefinition]:
    """Find a node definition within a workcell."""
    for node in workcell_def.nodes:
        if isinstance(node, NodeDefinition) and node.node_name == name:
            return node
        elif isinstance(node, str) and node.endswith(".node.yaml"):
            node_def = NodeDefinition.from_yaml(node)
            if node_def.node_name == name:
                return node_def
    return None


@click.group()
@click.option("--name", "-n", type=str, help="The name of the node to operate on.")
@click.option(
    "--path", "-p", type=str, help="The path to the node or workcell definition file."
)
@click.pass_context
def node(ctx, name: Optional[str], path: Optional[str]):
    """Manage nodes."""
    ctx.obj = find_node(name, path)


@node.command()
@click.option("--description", "-d", type=str, help="The description of the node.")
@click.option(
    "--module_name", "-m", type=str, help="The name of the module to use for the node."
)
@click.option(
    "--module_path",
    "-m",
    type=str,
    help="Path to the module definition file to use for the node.",
)
@click.pass_context
def create(
    ctx,
    description: Optional[str],
    module_name: Optional[str],
    module_path: Optional[str],
):
    """Create a new node."""
    name = ctx.parent.params.get("name")
    if not name:
        name = prompt_for_input("Node Name", required=True)
    if not description:
        description = prompt_for_input("Node Description")
    if module_name or module_path:
        from madsci.client.cli.module_cli import find_module

        module_path = find_module(module_name, module_path).path
    else:
        modules = search_for_file_pattern("*.module.yaml")
        if modules:
            module_path = prompt_from_list(
                prompt="Module Definition Files",
                options=modules,
                default=modules[0],
                required=True,
            )
        else:
            console.print(
                "No module definition files found. Please specify a module definition file using --module. If you don't have a module definition file, you can create one with 'madsci module create'."
            )
            return

    node_definition = NodeDefinition(
        node_name=name, description=description, module=Path(module_path).absolute()
    )
    console.print(node_definition)

    path = ctx.parent.params.get("path")
    if not path:
        default_path = Path.cwd() / f"{to_snake_case(name)}.node.yaml"
        new_path = prompt_for_input(
            "Path to save Node Definition file", default=str(default_path)
        )
        if new_path:
            path = Path(new_path)
    path = Path(path).absolute()
    node_definition.module = Path(module_path).absolute().relative_to(path.parent)
    node_definition.node_config = ModuleDefinition.from_yaml(module_path).config
    save_model(path=path, model=node_definition)


@node.command()
def list():
    """List all nodes, including those in workcell files."""
    node_files = search_for_file_pattern("*.node.yaml")
    workcell_files = search_for_file_pattern("*.workcell.yaml")

    nodes_found = False

    if node_files:
        for node_file in sorted(set(node_files)):
            node_definition = NodeDefinition.from_yaml(node_file)
            console.print(
                f"[bold]{node_definition.node_name}[/]: {node_definition.description} ({node_file})"
            )
            nodes_found = True

    for workcell_file in workcell_files:
        workcell_def = WorkcellDefinition.from_yaml(workcell_file)
        for node in workcell_def.nodes:
            if isinstance(node, NodeDefinition):
                console.print(
                    f"[bold]{node.node_name}[/]: {node.description} (in {workcell_file})"
                )
                nodes_found = True

    if not nodes_found:
        console.print("No node definitions found")


@node.command()
@pass_node
def info(ctx: NodeContext):
    """Get information about a node."""
    if ctx.node_def:
        pprint(ctx.node_def)
    else:
        console.print(
            "No node found. Specify node by name or path. If you don't have a node file, you can create one with 'madsci node create'."
        )


@node.command()
@pass_node
def delete(ctx: NodeContext):
    """Delete a node."""
    if ctx.node_def and ctx.path:
        if ctx.workcell_def:
            # Remove node from workcell
            ctx.workcell_def.nodes = [
                node for node in ctx.workcell_def.nodes if node != ctx.node_def
            ]
            save_model(ctx.path, ctx.workcell_def)
            console.print(
                f"Deleted node [bold]{ctx.node_def.node_name}[/] from workcell: [bold]{ctx.path}[/]"
            )
        else:
            # Delete node file
            console.print(f"Deleting node: {ctx.node_def.node_name} ({ctx.path})")
            if prompt_yes_no("Are you sure?"):
                ctx.path.unlink()
                console.print(f"Deleted {ctx.path}")
    else:
        console.print(
            "No node found. Specify node by name or path. If you don't have a node file, you can create one with 'madsci node create'."
        )


@node.command()
@pass_node
def validate(ctx: NodeContext):
    """Validate a node definition file."""
    if ctx.node_def:
        console.print(ctx.node_def)
    else:
        console.print(
            "No node found. Specify node by name or path. If you don't have a node definition file, you can create one with 'madsci node create'."
        )
