"""MADSci CLI init command.

Interactive lab initialization wizard that scaffolds a new lab directory
using the template engine.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click


def _collect_parameters(
    lab_name: str | None,
    lab_description: str | None,
    no_interactive: bool,
) -> tuple[str, str]:
    """Collect lab name and description via prompts or defaults.

    Args:
        lab_name: Pre-supplied lab name, or None to prompt.
        lab_description: Pre-supplied description, or None to prompt.
        no_interactive: If True, skip prompts and use defaults.

    Returns:
        Tuple of (lab_name, lab_description).
    """
    from rich.prompt import Prompt

    if not no_interactive:
        if not lab_name:
            lab_name = Prompt.ask(
                "  Lab name (lowercase, underscores or hyphens)",
                default="my_lab",
            )
        if not lab_description:
            lab_description = Prompt.ask(
                "  Lab description",
                default="A MADSci self-driving laboratory",
            )
    else:
        lab_name = lab_name or "my_lab"
        lab_description = lab_description or "A MADSci self-driving laboratory"

    return lab_name, lab_description


def _display_results(
    console: Any,
    result: Any,
    output_dir: Path,
    lab_name: str,
) -> None:
    """Display rendered template results and next-steps guidance.

    Args:
        console: Rich console instance.
        result: GeneratedProject from the template engine.
        output_dir: Directory where the lab was created.
        lab_name: Name of the lab.
    """
    from madsci.common.sentry import ensure_madsci_dir

    for path in result.files_created:
        console.print(f"  [green]\u2713[/green] Created {path}")

    if result.skills_included:
        console.print(
            f"  [green]\u2713[/green] Included {len(result.skills_included)} agent skill(s)"
        )

    lab_dir = output_dir / lab_name
    madsci_dir = ensure_madsci_dir(lab_dir)
    console.print(
        f"  [green]\u2713[/green] Initialized {madsci_dir.relative_to(output_dir)}/"
    )

    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print(f"  1. cd {lab_name}")
    console.print("  2. madsci start")
    console.print("  3. Open http://localhost:8000 in your browser")
    console.print()
    console.print("For more information, run:")
    console.print("  madsci --help")


@click.command()
@click.argument("directory", required=False, default=None)
@click.option(
    "--template",
    "template_name",
    type=click.Choice(["minimal"]),
    default="minimal",
    help="Lab template to use.",
)
@click.option("--name", "lab_name", help="Lab name (lowercase, underscores/hyphens).")
@click.option("--description", "lab_description", help="Lab description.")
@click.option(
    "--no-interactive",
    is_flag=True,
    help="Skip interactive prompts; use defaults.",
)
@click.pass_context
def init(
    ctx: click.Context,
    directory: str | None,
    template_name: str,
    lab_name: str | None,
    lab_description: str | None,
    no_interactive: bool,
) -> None:
    """Initialize a new MADSci lab.

    Creates a lab directory with configuration files, example workflows,
    and everything needed to get started.

    \b
    Examples:
        madsci init                          Interactive setup
        madsci init my_lab                   Create in ./my_lab
        madsci init --no-interactive         Use all defaults
        madsci init --name my_lab --no-interactive
    """
    from madsci.client.cli.utils.output import get_console
    from madsci.common.templates.registry import TemplateRegistry
    from rich.panel import Panel

    console = get_console(ctx)

    console.print()
    console.print(
        Panel.fit(
            "[bold blue]MADSci Lab Initialization[/bold blue]",
            border_style="blue",
        )
    )
    console.print()

    lab_name, lab_description = _collect_parameters(
        lab_name, lab_description, no_interactive
    )

    # Determine output directory
    output_dir = Path(directory) if directory else Path.cwd()
    output_dir = output_dir.resolve()

    # Load template and render
    template_id = f"lab/{template_name}"
    registry = TemplateRegistry()

    try:
        engine = registry.get_template(template_id)
    except Exception as exc:
        raise click.ClickException(
            f"Failed to load template '{template_id}': {exc}"
        ) from exc

    parameters = {
        "lab_name": lab_name,
        "lab_description": lab_description,
    }

    # Validate parameters
    errors = engine.validate_parameters(parameters)
    if errors:
        for err in errors:
            console.print(f"  [red]Error:[/red] {err}")
        raise click.ClickException("Invalid parameters. See errors above.")

    console.print(f'Creating lab "[bold]{lab_name}[/bold]" in {output_dir / lab_name}/')
    console.print()

    try:
        result = engine.render(output_dir=output_dir, parameters=parameters)
    except Exception as exc:
        raise click.ClickException(f"Failed to render template: {exc}") from exc

    _display_results(console, result, output_dir, lab_name)
