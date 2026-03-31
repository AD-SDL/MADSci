Module madsci.client.cli.commands.new
=====================================
MADSci CLI - Scaffolding commands for creating new components.

This module provides the `madsci new` command group for creating new MADSci
components (modules, interfaces, nodes, experiments, workflows, labs).

Heavy dependencies (template engine, Jinja2, rich) are imported lazily
within functions to reduce CLI startup time.

Functions
---------

`collect_parameters_interactive(engine: TemplateEngine, console: Console) ‑> dict[str, object]`
:   Collect parameter values interactively.
    
    Args:
        engine: Template engine with manifest.
        console: Rich console for output.
    
    Returns:
        Dictionary of parameter names to values.

`display_template_list(templates: list, console: Console, title: str = 'Available Templates') ‑> None`
:   Display a table of available templates.
    
    Args:
        templates: List of TemplateInfo objects.
        console: Rich console for output.
        title: Table title.

`generate_from_template(template_id: str, output_dir: Path, name: Optional[str], no_interactive: bool, console: Console, extra_params: Optional[dict] = None) ‑> GeneratedProject | None`
:   Generate from a template with optional interactive prompts.
    
    Args:
        template_id: Template identifier (e.g., "module/device").
        output_dir: Directory to write output.
        name: Component name (if provided via CLI).
        no_interactive: Skip interactive prompts.
        console: Rich console for output.
        extra_params: Additional parameters to pass.
    
    Returns:
        GeneratedProject on success, None on failure.

`get_console(ctx: click.Context) ‑> Console`
:   Get console from context or create new one.
    
    Delegates to the canonical ``madsci.client.cli.utils.output.get_console``.