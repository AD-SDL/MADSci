"""MADSci CLI - Scaffolding commands for creating new components.

This module provides the `madsci new` command group for creating new MADSci
components (modules, interfaces, nodes, experiments, workflows, labs).

Heavy dependencies (template engine, Jinja2, rich) are imported lazily
within functions to reduce CLI startup time.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

import click

if TYPE_CHECKING:
    from madsci.common.templates.engine import TemplateEngine
    from madsci.common.types.template_types import GeneratedProject
    from rich.console import Console


def get_console(ctx: click.Context) -> Console:
    """Get console from context or create new one.

    Delegates to the canonical ``madsci.client.cli.utils.output.get_console``.
    """
    from madsci.client.cli.utils.output import get_console as _get_console

    return _get_console(ctx)


def collect_parameters_interactive(  # noqa: C901
    engine: TemplateEngine, console: Console
) -> dict[str, object]:
    """Collect parameter values interactively.

    Args:
        engine: Template engine with manifest.
        console: Rich console for output.

    Returns:
        Dictionary of parameter names to values.
    """
    from madsci.common.types.template_types import ParameterType
    from rich.prompt import Confirm, Prompt

    params: dict[str, object] = {}

    for param in engine.manifest.parameters:
        if param.type == ParameterType.STRING:
            default_str = str(param.default) if param.default else ""
            value = Prompt.ask(
                f"  {param.description}",
                default=default_str or None,
            )
            params[param.name] = value

        elif param.type == ParameterType.INTEGER:
            default_str = str(param.default) if param.default is not None else ""
            value_str = Prompt.ask(
                f"  {param.description}",
                default=default_str or None,
            )
            params[param.name] = int(value_str) if value_str else 0

        elif param.type == ParameterType.FLOAT:
            default_str = str(param.default) if param.default is not None else ""
            value_str = Prompt.ask(
                f"  {param.description}",
                default=default_str or None,
            )
            params[param.name] = float(value_str) if value_str else 0.0

        elif param.type == ParameterType.BOOLEAN:
            default_val = param.default if param.default is not None else False
            value = Confirm.ask(
                f"  {param.description}",
                default=default_val,
            )
            params[param.name] = value

        elif param.type == ParameterType.CHOICE:
            console.print(f"\n  {param.description}:")
            choices = param.choices or []
            for i, choice in enumerate(choices, 1):
                marker = "●" if choice.value == param.default else "○"
                console.print(f"    {marker} {i}. {choice.label}")
                if choice.description:
                    console.print(f"         {choice.description}", style="dim")

            default_idx = next(
                (i for i, c in enumerate(choices, 1) if c.value == param.default),
                1,
            )
            idx = Prompt.ask("  Select", default=str(default_idx))
            params[param.name] = choices[int(idx) - 1].value

        elif param.type == ParameterType.MULTI_CHOICE:
            console.print(f"\n  {param.description}:")
            selected = []
            for choice in param.choices or []:
                if Confirm.ask(f"    Include {choice.label}?", default=choice.default):
                    selected.append(choice.value)
            params[param.name] = selected

        elif param.type == ParameterType.PATH:
            default_str = str(param.default) if param.default else ""
            value = Prompt.ask(
                f"  {param.description}",
                default=default_str or None,
            )
            params[param.name] = value

    return params


def display_template_list(
    templates: list, console: Console, title: str = "Available Templates"
) -> None:
    """Display a table of available templates.

    Args:
        templates: List of TemplateInfo objects.
        console: Rich console for output.
        title: Table title.
    """
    from rich.table import Table

    table = Table(title=title, show_header=True)
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Description")

    for t in templates:
        table.add_row(str(t.id), str(t.name), str(t.description))

    console.print(table)


def generate_from_template(  # noqa: C901, PLR0912
    template_id: str,
    output_dir: Path,
    name: Optional[str],
    no_interactive: bool,
    console: Console,
    extra_params: Optional[dict] = None,
) -> GeneratedProject | None:
    """Generate from a template with optional interactive prompts.

    Args:
        template_id: Template identifier (e.g., "module/device").
        output_dir: Directory to write output.
        name: Component name (if provided via CLI).
        no_interactive: Skip interactive prompts.
        console: Rich console for output.
        extra_params: Additional parameters to pass.

    Returns:
        GeneratedProject on success, None on failure.
    """
    from madsci.common.templates.engine import TemplateError, TemplateValidationError
    from madsci.common.templates.registry import TemplateNotFoundError, TemplateRegistry
    from rich.panel import Panel
    from rich.prompt import Confirm

    registry = TemplateRegistry()

    try:
        engine = registry.get_template(template_id)
    except TemplateNotFoundError as e:
        console.print(f"[red]✗[/red] {e}")
        return None

    # Collect parameters
    if no_interactive:
        params = engine.get_default_values()
        if name:
            # Map the --name CLI flag to the correct template parameter.
            # Strategy: use the template's category to determine the primary
            # name parameter (e.g., "module" -> "module_name"), then fall back
            # to the first parameter if it looks like a name field.
            category = (
                engine.manifest.category.value if engine.manifest.category else ""
            )
            category_name_key = f"{category}_name" if category else ""

            if category_name_key and any(
                p.name == category_name_key for p in engine.manifest.parameters
            ):
                params[category_name_key] = name
            else:
                # Fallback: use the first parameter if it ends with _name
                first_param = (
                    engine.manifest.parameters[0]
                    if engine.manifest.parameters
                    else None
                )
                if first_param and (
                    first_param.name.endswith("_name") or first_param.name == "name"
                ):
                    params[first_param.name] = name
    else:
        console.print(
            Panel(
                f"[bold]{engine.manifest.name}[/bold]\n{engine.manifest.description}",
                title="Template",
            )
        )
        console.print()
        params = collect_parameters_interactive(engine, console)

    # Add extra params
    if extra_params:
        params.update(extra_params)

    # Validate
    errors = engine.validate_parameters(params)
    if errors:
        console.print("[red]✗[/red] Parameter validation failed:")
        for error in errors:
            console.print(f"    • {error}")
        return None

    # Preview
    if not no_interactive:
        console.print("\n[bold]Preview:[/bold]")
        result = engine.render(output_dir, params, dry_run=True)

        for file_path in result.files_created:
            rel_path = file_path.relative_to(output_dir)
            console.print(f"  • {rel_path}")

        if not Confirm.ask("\nCreate these files?", default=True):
            console.print("Cancelled.")
            return None

    # Generate
    try:
        result = engine.render(output_dir, params)
    except TemplateValidationError as e:
        console.print(f"[red]✗[/red] Validation error: {e.errors}")
        return None
    except TemplateError as e:
        console.print(f"[red]✗[/red] Template error: {e}")
        return None

    console.print(f"\n[green]✓[/green] Created {len(result.files_created)} files\n")

    for file_path in result.files_created:
        rel_path = file_path.relative_to(output_dir)
        console.print(f"  • {rel_path}")

    return result


@click.group(invoke_without_command=True)
@click.option(
    "--tui",
    "use_tui",
    is_flag=True,
    help="Launch interactive TUI template browser.",
)
@click.pass_context
def new(ctx: click.Context, use_tui: bool) -> None:
    """Create new MADSci components from templates.

    Generate scaffolding for modules, interfaces, nodes, experiments,
    workflows, and labs using templates.

    \b
    Examples:
        madsci new module                   Interactive module creation
        madsci new module --name my_device  Create with specified name
        madsci new interface --type fake    Add fake interface to module
        madsci new experiment               Create new experiment
        madsci new --tui                    Launch TUI template browser
    """
    if ctx.invoked_subcommand is not None:
        return

    if use_tui:
        _launch_tui_browser(ctx)
    elif not ctx.invoked_subcommand:
        click.echo(ctx.get_help())


def _launch_tui_browser(ctx: click.Context) -> None:
    """Launch the TUI template browser and generate from the selected template."""
    try:
        from madsci.client.cli.tui.screens.new_wizard import TemplateBrowserScreen
        from textual.app import App
    except ImportError as e:
        console = get_console(ctx)
        console.print(
            "[red]Error: TUI dependencies not installed.[/red]\n\n"
            "Install with:\n"
            "  pip install 'madsci.client[tui]'\n\n"
            f"Details: {e}"
        )
        return

    class TemplateBrowserApp(App):
        """Minimal app that runs the template browser screen."""

        TITLE = "MADSci Template Browser"

        def on_mount(self) -> None:
            self.push_screen(TemplateBrowserScreen(), callback=self._on_result)

        def _on_result(self, template_id: str | None) -> None:
            self.exit(template_id)

    app = TemplateBrowserApp()
    template_id = app.run()

    if not template_id:
        return

    console = get_console(ctx)
    output_dir = Path.cwd()

    generate_from_template(
        template_id=template_id,
        output_dir=output_dir,
        name=None,
        no_interactive=False,
        console=console,
    )


@new.command()
@click.argument("directory", required=False, type=click.Path())
@click.option("--name", "-n", help="Module name (lowercase, underscores allowed).")
@click.option(
    "--template",
    "-t",
    default="module/basic",
    help="Template to use (e.g., module/device).",
)
@click.option(
    "--no-interactive",
    is_flag=True,
    help="Skip interactive prompts, use defaults.",
)
@click.pass_context
def module(
    ctx: click.Context,
    directory: Optional[str],
    name: Optional[str],
    template: str,
    no_interactive: bool,
) -> None:
    """Create a new node module from template.

    Creates a complete module repository with node server, interface(s),
    types, tests, and documentation.

    \b
    Templates available:
        module/basic      - Minimal module with one action
        module/device     - Standard device lifecycle (init, shutdown, status)
        module/instrument - Measurement device with calibration

    \b
    Examples:
        madsci new module
        madsci new module --name my_pipette --template module/device
        madsci new module ./my_module --no-interactive
    """
    console = get_console(ctx)

    from madsci.common.templates.registry import TemplateRegistry
    from madsci.common.types.template_types import TemplateCategory
    from rich.prompt import Prompt

    registry = TemplateRegistry()

    # Only prompt for template selection if --template was not explicitly provided
    template_explicitly_set = (
        ctx.get_parameter_source("template") == click.core.ParameterSource.COMMANDLINE
    )
    if not no_interactive and not template_explicitly_set:
        templates = registry.list_templates(category=TemplateCategory.MODULE)

        if templates:
            console.print("\n[bold]Available module templates:[/bold]\n")
            display_template_list(templates, console)
            console.print()

            template = Prompt.ask(
                "Select template",
                default="module/basic",
            )

    # Determine output directory
    output_dir = Path(directory) if directory else Path.cwd()

    result = generate_from_template(
        template_id=template,
        output_dir=output_dir,
        name=name,
        no_interactive=no_interactive,
        console=console,
    )

    if result:
        module_name = result.parameters_used.get("module_name", name or "my_device")
        console.print("\n[bold]Next steps:[/bold]")
        console.print(f"  1. cd {module_name}_module")
        console.print("  2. Implement your interface in src/*_interface.py")
        console.print("  3. Test with fake interface: python src/*_rest_node.py --fake")
        console.print("  4. Run tests: pytest tests/")
        console.print("\n  Documentation: https://ad-sdl.github.io/MADSci/readme/")


@new.command()
@click.argument("module_path", required=False, type=click.Path(exists=True))
@click.option(
    "--type",
    "-t",
    "interface_type",
    type=click.Choice(["fake", "sim", "mock"]),
    default=None,
    help="Interface type to add.",
)
@click.option("--name", "-n", help="Custom interface name.")
@click.option(
    "--no-interactive",
    is_flag=True,
    help="Skip interactive prompts, use defaults.",
)
@click.pass_context
def interface(
    ctx: click.Context,
    module_path: Optional[str],
    interface_type: Optional[str],
    name: Optional[str],
    no_interactive: bool,
) -> None:
    """Add a new interface variant to an existing module.

    Adds a fake, simulation, or mock interface to an existing module
    for testing without hardware.

    \b
    Interface types:
        fake - In-memory simulation for testing without hardware
        sim  - Connects to external physics simulator (e.g., Omniverse)
        mock - Pytest mock wrapper for unit testing

    \b
    Examples:
        madsci new interface                     Interactive mode
        madsci new interface --type fake         Add fake interface
        madsci new interface ./my_module --type sim
    """
    console = get_console(ctx)

    # Determine module path
    path = Path(module_path) if module_path else Path.cwd()

    # Interactive type selection
    if not interface_type and not no_interactive:
        from rich.prompt import Prompt

        console.print("\n[bold]Interface types:[/bold]")
        console.print("  1. fake - In-memory simulation for testing")
        console.print("  2. sim  - External physics simulator connection")
        console.print("  3. mock - Pytest mock wrapper")
        console.print()

        choice = Prompt.ask(
            "Select type", choices=["1", "2", "3", "fake", "sim", "mock"], default="1"
        )
        type_map = {"1": "fake", "2": "sim", "3": "mock"}
        interface_type = type_map.get(choice, choice)

    interface_type = interface_type or "fake"
    template_id = f"interface/{interface_type}"

    result = generate_from_template(
        template_id=template_id,
        output_dir=path,
        name=name,
        no_interactive=no_interactive,
        console=console,
    )

    if result:
        console.print("\n[bold]Next steps:[/bold]")
        console.print(f"  1. Implement {interface_type} behavior in the generated file")
        console.print("  2. Run tests: pytest tests/")
        console.print(
            f"  3. Use {interface_type} interface: python src/*_rest_node.py --{interface_type}"
        )


@new.command()
@click.argument("directory", required=False, type=click.Path())
@click.option("--name", "-n", help="Node name.")
@click.option(
    "--interface-module",
    help="Python module path for existing interface.",
)
@click.option("--port", type=int, default=2000, help="Default port number.")
@click.option(
    "--no-interactive",
    is_flag=True,
    help="Skip interactive prompts, use defaults.",
)
@click.pass_context
def node(
    ctx: click.Context,
    directory: Optional[str],
    name: Optional[str],
    interface_module: Optional[str],
    port: int,
    no_interactive: bool,
) -> None:
    """Create a node server for an existing interface.

    Creates just the REST node server when an interface already exists.
    Most users should use `madsci new module` instead, which creates
    the complete package including node, interface, and types.

    \b
    Examples:
        madsci new node --name my_device --interface-module my_device.interface
    """
    console = get_console(ctx)
    output_dir = Path(directory) if directory else Path.cwd()

    extra_params: dict[str, object] = {"port": port}
    if interface_module:
        extra_params["interface_module"] = interface_module

    result = generate_from_template(
        template_id="node/basic",
        output_dir=output_dir,
        name=name,
        no_interactive=no_interactive,
        console=console,
        extra_params=extra_params,
    )

    if result:
        node_name = result.parameters_used.get("node_name", name or "my_node")
        console.print("\n[bold]Next steps:[/bold]")
        console.print(f"  1. Start the node: python {node_name}.py")
        console.print(f"  2. Test: curl http://localhost:{port}/health")


@new.command()
@click.argument("directory", required=False, type=click.Path())
@click.option("--name", "-n", help="Experiment name.")
@click.option(
    "--modality",
    "-m",
    type=click.Choice(["script", "notebook", "tui", "node"]),
    default="script",
    help="Experiment modality.",
)
@click.option(
    "--no-interactive",
    is_flag=True,
    help="Skip interactive prompts, use defaults.",
)
@click.pass_context
def experiment(
    ctx: click.Context,
    directory: Optional[str],
    name: Optional[str],
    modality: str,
    no_interactive: bool,
) -> None:
    """Create a new experiment from template.

    Creates experiment scaffolding for different execution contexts.

    \b
    Modalities:
        script   - Simple run-once experiment (default)
        notebook - Jupyter-friendly experiment
        tui      - Interactive terminal UI experiment
        node     - REST API server mode experiment

    \b
    Examples:
        madsci new experiment
        madsci new experiment --name my_study --modality script
    """
    console = get_console(ctx)
    output_dir = Path(directory) if directory else Path.cwd()

    template_id = f"experiment/{modality}"

    result = generate_from_template(
        template_id=template_id,
        output_dir=output_dir,
        name=name,
        no_interactive=no_interactive,
        console=console,
    )

    if result:
        exp_name = result.parameters_used.get(
            "experiment_name", name or "my_experiment"
        )
        console.print("\n[bold]Next steps:[/bold]")
        if modality == "script":
            console.print(f"  1. Edit {exp_name}.py to define your experiment logic")
            console.print(f"  2. Run: python {exp_name}.py")
        elif modality == "notebook":
            console.print(f"  1. Open {exp_name}.ipynb in Jupyter")
            console.print("  2. Run cells to execute experiment")


@new.command()
@click.argument("directory", required=False, type=click.Path())
@click.option("--name", "-n", help="Workflow name.")
@click.option(
    "--template",
    "-t",
    default="workflow/basic",
    help="Workflow template.",
)
@click.option(
    "--no-interactive",
    is_flag=True,
    help="Skip interactive prompts, use defaults.",
)
@click.pass_context
def workflow(
    ctx: click.Context,
    directory: Optional[str],
    name: Optional[str],
    template: str,
    no_interactive: bool,
) -> None:
    """Create a new workflow from template.

    Creates workflow YAML files for orchestrating node actions.

    \b
    Templates:
        workflow/basic      - Single-step workflow
        workflow/multi_step - Sequential steps workflow

    \b
    Examples:
        madsci new workflow
        madsci new workflow --name sample_transfer
    """
    console = get_console(ctx)
    output_dir = Path(directory) if directory else Path.cwd()

    result = generate_from_template(
        template_id=template,
        output_dir=output_dir,
        name=name,
        no_interactive=no_interactive,
        console=console,
    )

    if result:
        wf_name = result.parameters_used.get("workflow_name", name or "my_workflow")
        console.print("\n[bold]Next steps:[/bold]")
        console.print(f"  1. Edit {wf_name}.workflow.yaml to define your steps")
        console.print(f"  2. Run: madsci run workflow {wf_name}.workflow.yaml")


@new.command()
@click.argument("directory", required=False, type=click.Path())
@click.option("--name", "-n", help="Lab name.")
@click.option(
    "--template",
    "-t",
    type=click.Choice(["minimal", "standard", "distributed"]),
    default="minimal",
    help="Lab template.",
)
@click.option(
    "--no-interactive",
    is_flag=True,
    help="Skip interactive prompts, use defaults.",
)
@click.pass_context
def lab(
    ctx: click.Context,
    directory: Optional[str],
    name: Optional[str],
    template: str,
    no_interactive: bool,
) -> None:
    """Create a new lab configuration.

    Creates complete lab setup with managers, infrastructure, and configuration.

    \b
    Templates:
        minimal     - Single node, no Docker required (default)
        standard    - All managers with Docker Compose
        distributed - Multi-host deployment configuration

    \b
    Examples:
        madsci new lab --name my_research_lab
        madsci new lab --template standard
    """
    console = get_console(ctx)
    output_dir = Path(directory) if directory else Path.cwd()

    template_id = f"lab/{template}"

    result = generate_from_template(
        template_id=template_id,
        output_dir=output_dir,
        name=name,
        no_interactive=no_interactive,
        console=console,
    )

    if result:
        lab_name = result.parameters_used.get("lab_name", name or "my_lab")
        console.print("\n[bold]Next steps:[/bold]")
        console.print(f"  1. cd {lab_name}")
        if template == "minimal":
            console.print("  2. python -m madsci.squid")
        else:
            console.print("  2. madsci start lab")
        console.print("  3. Open http://localhost:8000 in your browser")
        console.print("\n  Documentation: https://ad-sdl.github.io/MADSci/")


@new.command("list")
@click.option(
    "--category",
    "-c",
    type=click.Choice(["module", "interface", "node", "experiment", "workflow", "lab"]),
    default=None,
    help="Filter by category.",
)
@click.option("--tag", "-t", multiple=True, help="Filter by tag.")
@click.pass_context
def list_templates(
    ctx: click.Context,
    category: Optional[str],
    tag: tuple[str, ...],
) -> None:
    """List available templates.

    \b
    Examples:
        madsci new list
        madsci new list --category module
        madsci new list --tag device
    """
    console = get_console(ctx)

    from madsci.common.templates.registry import TemplateRegistry
    from madsci.common.types.template_types import TemplateCategory
    from rich.table import Table

    registry = TemplateRegistry()

    # Convert category string to enum
    cat_enum = TemplateCategory(category) if category else None
    tags = list(tag) if tag else None

    templates = registry.list_templates(category=cat_enum, tags=tags)

    if not templates:
        console.print("[yellow]No templates found.[/yellow]")
        console.print("\nTemplates may not be installed. Check:")
        console.print("  • ~/.madsci/templates/ for user templates")
        console.print("  • Bundled templates in the madsci_common package")
        return

    console.print("\n[bold]Available Templates[/bold]\n")

    # Group by category
    by_category: dict[str, list] = {}
    for t in templates:
        cat = t.category.value
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(t)

    for cat_name, cat_templates in sorted(by_category.items()):
        table = Table(title=f"{cat_name.title()} Templates", show_header=True)
        table.add_column("ID", style="cyan")
        table.add_column("Name")
        table.add_column("Description")
        table.add_column("Source", style="dim")

        for t in cat_templates:
            table.add_row(t.id, t.name, t.description, t.source)

        console.print(table)
        console.print()
