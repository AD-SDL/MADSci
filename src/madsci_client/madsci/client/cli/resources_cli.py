"""CLI for interacting with resources."""

from pathlib import Path
from typing import Optional

import click
from click.core import Context
from madsci.common.types.resource_types import (
    RESOURCE_TYPE_MAP,
)
from madsci.common.types.resource_types.custom_types import (
    ResourceTypeEnum,
)
from madsci.common.types.resource_types.definitions import (
    ResourceDefinition,
    ResourceFile,
)
from madsci.common.utils import (
    prompt_for_input,
    prompt_from_list,
    prompt_from_pydantic_model,
    prompt_yes_no,
    save_model,
    search_for_file_pattern,
)
from rich.console import Console
from rich.pretty import pprint

console = Console()


class ResourceContext:
    """Context object for resource commands."""

    def __init__(self) -> None:
        """Initialize the context object."""
        self.resource_file: Optional[ResourceFile] = None
        self.path: Optional[Path] = None


pass_resource = click.make_pass_decorator(ResourceContext)


def find_resource_file(path: Optional[str]) -> ResourceContext:
    """Find a resource file by path."""
    resource_context = ResourceContext()

    if path:
        resource_context.path = Path(path)
        if resource_context.path.exists():
            resource_context.resource_file = ResourceFile.from_yaml(path)
            return resource_context

    # Search for any resource file
    resource_files = search_for_file_pattern("*.resources.yaml")
    if resource_files:
        resource_context.path = Path(resource_files[0])
        resource_context.resource_file = ResourceFile.from_yaml(resource_files[0])

    return resource_context


@click.group()
@click.option("--path", "-p", type=str, help="Path to the resource definition file.")
@click.pass_context
def resource(ctx: Context, path: Optional[str]) -> None:
    """Manage resources."""
    ctx.obj = find_resource_file(path)


@resource.command()
@click.pass_context
def create(ctx: Context) -> None:
    """Create a new resource file."""
    path = ctx.parent.params.get("path")
    if not path:
        default_path = Path.cwd() / "default.resources.yaml"
        new_path = prompt_for_input(
            "Path to save Resource Definition file",
            default=str(default_path),
        )
        if new_path:
            path = Path(new_path)

    resource_file = ResourceFile()
    save_model(path=path, model=resource_file)
    console.print(f"Created resource file: {path}")


@resource.command()
def list() -> None:
    """List all resource files and their contents."""
    resource_files = search_for_file_pattern("*.resources.yaml")

    if resource_files:
        for resource_file in sorted(set(resource_files)):
            resource_def = ResourceFile.from_yaml(resource_file)
            console.print(f"\n[bold]Resource File[/]: {resource_file}")

            if resource_def.resource_types:
                console.print("\n[bold]Resource Types:[/]")
                for resource_type in resource_def.resource_types:
                    console.print(
                        f"  [bold]{resource_type.type_name}[/]: {resource_type.type_description}",
                    )

            if resource_def.default_resources:
                console.print("\n[bold]Default Resources:[/]")
                for resource in resource_def.default_resources:
                    console.print(
                        f"  [bold]{resource.resource_name}[/]: {resource.resource_description or 'No description'}",
                    )
    else:
        console.print("No resource files found")


@resource.group(name="type")
def resource_type() -> None:
    """Manage resource types within a resource file."""


@resource_type.command()
@click.option("--name", "-n", type=str, help="Name of the resource type.")
@click.option("--description", "-d", type=str, help="Description of the resource type.")
@click.option("--base-type", "-b", type=str, help="Base type of the resource.")
@pass_resource
def add(
    ctx: ResourceContext,
    name: Optional[str],
    description: Optional[str],
    base_type: Optional[str],
) -> None:
    """Add a new resource type to the resource file."""
    if not ctx.resource_file or not ctx.path:
        console.print(
            "No resource file found. Create one with 'madsci resource create' first.",
        )
        return

    if not name:
        name = prompt_for_input("Resource Type Name", required=True)
    if not description:
        description = prompt_for_input("Resource Type Description")
    if not base_type or base_type not in ResourceTypeEnum:
        base_type = prompt_from_list(
            "Base Type",
            [e.value for e in ResourceTypeEnum],
            default=ResourceTypeEnum.resource.value,
        )
    # *Get the appropriate type definition class
    type_def_class = RESOURCE_TYPE_MAP[base_type]["definition"]

    # *Create the type definition with the fields we've collected
    type_def = type_def_class(
        **prompt_from_pydantic_model(
            type_def_class,
            "Resource Type Definition",
            type_name=name,
            type_description=description,
            base_type=base_type,
        ),
    )

    # *Check if type already exists
    if any(rt.type_name == name for rt in ctx.resource_file.resource_types):
        if not prompt_yes_no(
            f"Resource type '{name}' already exists. Overwrite?",
            default=False,
        ):
            return
        # *Remove existing type
        ctx.resource_file.resource_types = [
            rt for rt in ctx.resource_file.resource_types if rt.type_name != name
        ]

    # *Add the type definition to the resource file
    ctx.resource_file.resource_types.append(type_def)
    save_model(ctx.path, ctx.resource_file, overwrite_check=False)
    console.print(f"Added resource type: [bold]{name}[/]")


@resource_type.command()
@click.argument("name", required=False)
@pass_resource
def delete(ctx: ResourceContext, name: Optional[str]) -> None:
    """Delete a resource type from the resource file."""
    if not ctx.resource_file or not ctx.path:
        console.print(
            "No resource file found. Create one with 'madsci resource create' first.",
        )
        return

    if not ctx.resource_file.resource_types:
        console.print("No resource types defined in this file.")
        return

    if not name:
        name = prompt_from_list(
            "Resource Type to Delete",
            [rt.type_name for rt in ctx.resource_file.resource_types],
            required=True,
        )

    # Find the resource type
    resource_type = next(
        (rt for rt in ctx.resource_file.resource_types if rt.type_name == name),
        None,
    )
    if not resource_type:
        console.print(f"Resource type [bold]{name}[/] not found.")
        return

    # Check if type is used by any default resources
    used_by_resources = [
        r.resource_name
        for r in ctx.resource_file.default_resources
        if r.resource_type == name
    ]
    if used_by_resources:
        console.print(
            f"Cannot delete resource type [bold]{name}[/] as it is used by these resources:",
        )
        for resource_name in used_by_resources:
            console.print(f"  - {resource_name}")
        return

    if prompt_yes_no(f"Delete resource type [bold]{name}[/]?", default=False):
        ctx.resource_file.resource_types = [
            rt for rt in ctx.resource_file.resource_types if rt.type_name != name
        ]
        save_model(ctx.path, ctx.resource_file, overwrite_check=False)
        console.print(f"Deleted resource type: [bold]{name}[/]")


@resource_type.command()
@click.argument("name", required=False)
@pass_resource
def info(ctx: ResourceContext, name: Optional[str]) -> None:
    """Show information about a resource type."""
    if not ctx.resource_file:
        console.print(
            "No resource file found. Create one with 'madsci resource create' first.",
        )
        return

    if not ctx.resource_file.resource_types:
        console.print("No resource types defined in this file.")
        return

    if not name:
        name = prompt_from_list(
            "Resource Type",
            [rt.type_name for rt in ctx.resource_file.resource_types],
            required=True,
        )

    resource_type = next(
        (rt for rt in ctx.resource_file.resource_types if rt.type_name == name),
        None,
    )
    if resource_type:
        pprint(resource_type)
    else:
        console.print(f"Resource type [bold]{name}[/] not found.")


@resource_type.command(name="list")
@pass_resource
def list_types(ctx: ResourceContext) -> None:
    """List all resource types in the file."""
    if not ctx.resource_file:
        console.print(
            "No resource file found. Create one with 'madsci resource create' first.",
        )
        return

    if not ctx.resource_file.resource_types:
        console.print("No resource types defined in this file.")
        return

    console.print("\n[bold]Resource Types:[/]")
    for resource_type in ctx.resource_file.resource_types:
        console.print(
            f"  [bold]{resource_type.type_name}[/] ({resource_type.base_type})",
        )
        if resource_type.type_description:
            console.print(f"    Description: {resource_type.type_description}")
        console.print(f"    Parent Types: {', '.join(resource_type.parent_types)}")


@resource.command()
@pass_resource
def add_resource(ctx: ResourceContext) -> None:
    """Add a new default resource to the resource file."""
    if not ctx.resource_file or not ctx.path:
        console.print(
            "No resource file found. Create one with 'madsci resource create' first.",
        )
        return

    name = prompt_for_input("Resource Name", required=True)
    description = prompt_for_input("Resource Description")

    # * Combine built-in types and custom types for selection
    available_types = [e.value for e in ResourceTypeEnum]
    custom_types = [rt.type_name for rt in ctx.resource_file.resource_types]
    all_types = available_types + custom_types

    resource_type = prompt_from_list(
        "Resource Type",
        all_types,
        default=ResourceTypeEnum.resource.value,
    )

    # * Create the resource definition
    if resource_type in RESOURCE_TYPE_MAP:
        resource_def_class = RESOURCE_TYPE_MAP[resource_type]["definition"]
    else:
        resource_def_class = ResourceDefinition

    resource_def = resource_def_class(
        resource_name=name,
        resource_description=description,
        resource_type=resource_type,
    )

    ctx.resource_file.default_resources.append(resource_def)
    save_model(ctx.path, ctx.resource_file, overwrite_check=False)
    console.print(f"Added default resource: [bold]{name}[/]")


@resource.command(name="info")
@pass_resource
def file_info(ctx: ResourceContext) -> None:
    """Get information about a resource file."""
    if ctx.resource_file:
        pprint(ctx.resource_file)
    else:
        console.print(
            "No resource file found. Create one with 'madsci resource create'.",
        )


@resource.command()
@pass_resource
def validate(ctx: ResourceContext) -> None:
    """Validate a resource file."""
    if ctx.resource_file:
        console.print(ctx.resource_file)
    else:
        console.print(
            "No resource file found. Create one with 'madsci resource create'.",
        )


@resource.command(name="delete")
@pass_resource
def delete_file(ctx: ResourceContext) -> None:
    """Delete a resource file."""
    if ctx.resource_file and ctx.path:
        console.print(f"Deleting resource file: {ctx.path}")
        if prompt_yes_no("Are you sure?"):
            ctx.path.unlink()
            console.print(f"Deleted {ctx.path}")
    else:
        console.print(
            "No resource file found. Create one with 'madsci resource create'.",
        )
