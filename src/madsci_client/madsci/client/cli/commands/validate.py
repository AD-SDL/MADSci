"""MADSci CLI validate command.

Validates MADSci configuration files (settings, manager, node, workflow definitions).
"""

from __future__ import annotations

import fnmatch
import json
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import click

# Patterns for deprecated definition files — still validated but emit deprecation warnings
_DEPRECATED_FILE_PATTERNS = {"*.manager.yaml", "*.node.yaml"}

# Map file-name patterns to the Pydantic model class that validates them.
_FILE_VALIDATORS: list[tuple[str, str, str]] = [
    # (glob pattern, model import path, friendly label)
    (
        "*.manager.yaml",
        "madsci.common.types.manager_types.ManagerDefinition",
        "manager definition",
    ),
    ("*.node.yaml", "madsci.common.types.node_types.NodeDefinition", "node definition"),
    (
        "*.workflow.yaml",
        "madsci.common.types.workflow_types.WorkflowDefinition",
        "workflow definition",
    ),
]


@dataclass
class ValidationResult:
    """Result of validating a single file."""

    path: str
    valid: bool
    file_type: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "path": self.path,
            "valid": self.valid,
            "file_type": self.file_type,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def _import_model(dotted_path: str) -> type:
    """Dynamically import a model class from a dotted path."""
    import importlib

    module_path, _, class_name = dotted_path.rpartition(".")
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def _validate_file(
    file_path: Path, model_path: str, file_type: str
) -> ValidationResult:
    """Validate a single YAML file against its expected Pydantic model."""
    result = ValidationResult(path=str(file_path), valid=False, file_type=file_type)

    # Check if this is a deprecated definition file pattern
    for deprecated_pattern in _DEPRECATED_FILE_PATTERNS:
        if fnmatch.fnmatch(file_path.name, deprecated_pattern):
            result.warnings.append(
                "Definition files are deprecated. Run 'madsci migrate' to convert to settings."
            )
            break

    try:
        model_class = _import_model(model_path)
    except Exception as exc:
        result.errors.append(f"Could not load validator: {exc}")
        return result

    try:
        # Suppress deprecation warnings from model instantiation during validation
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model_class.from_yaml(file_path)
        result.valid = True
    except Exception as exc:
        result.errors.append(str(exc))

    return result


def _scan_and_validate(paths: tuple[str, ...]) -> list[ValidationResult]:
    """Scan paths for known config files and validate each one."""
    results: list[ValidationResult] = []
    dirs_to_scan: list[Path] = []

    for p in paths:
        path = Path(p).resolve()
        if path.is_dir():
            dirs_to_scan.append(path)
        elif path.is_file():
            # Validate the specific file — try to match pattern
            for glob_pat, model_path, label in _FILE_VALIDATORS:
                if fnmatch.fnmatch(path.name, glob_pat):
                    results.append(_validate_file(path, model_path, label))
                    break
            else:
                results.append(
                    ValidationResult(
                        path=str(path),
                        valid=False,
                        file_type="unknown",
                        warnings=[
                            "File does not match any known MADSci config pattern."
                        ],
                    )
                )

    if not dirs_to_scan and not results:
        dirs_to_scan.append(Path.cwd())

    for directory in dirs_to_scan:
        for glob_pat, model_path, label in _FILE_VALIDATORS:
            for match in sorted(directory.rglob(glob_pat)):
                results.append(_validate_file(match, model_path, label))

    return results


def _format_json(results: list[ValidationResult]) -> str:
    """Format results as a JSON string."""
    output = {
        "results": [r.to_dict() for r in results],
        "summary": {
            "total": len(results),
            "valid": sum(1 for r in results if r.valid),
            "errors": sum(1 for r in results if r.errors),
            "warnings": sum(1 for r in results if r.warnings and r.valid),
        },
    }
    return json.dumps(output)


def _print_results(
    results: list[ValidationResult], console: Any
) -> tuple[int, int, int]:
    """Print validation results to the console. Returns (valid, warn, error) counts."""
    console.print("Validating MADSci configuration files...\n")

    for r in results:
        if r.valid and not r.warnings:
            console.print(
                f"  [green]\u2713[/green] {r.path} \u2014 valid ({r.file_type})"
            )
        elif r.valid and r.warnings:
            console.print(f"  [yellow]\u26a0[/yellow] {r.path}")
            for w in r.warnings:
                console.print(f"      {w}")
        else:
            console.print(f"  [red]\u2717[/red] {r.path}")
            for e in r.errors:
                console.print(f"      {e}")

    valid_count = sum(1 for r in results if r.valid)
    warn_count = sum(1 for r in results if r.warnings and r.valid)
    error_count = sum(1 for r in results if r.errors)

    console.print()
    parts = []
    if valid_count:
        parts.append(f"[green]{valid_count} valid[/green]")
    if warn_count:
        parts.append(f"[yellow]{warn_count} warnings[/yellow]")
    if error_count:
        parts.append(f"[red]{error_count} errors[/red]")
    console.print(f"Summary: {', '.join(parts)}")

    return valid_count, warn_count, error_count


@click.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True))
@click.option("--strict", is_flag=True, help="Fail on warnings.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.pass_context
def validate(
    ctx: click.Context,
    paths: tuple[str, ...],
    strict: bool,
    as_json: bool,
) -> None:
    """Validate MADSci configuration files.

    Scans directories (or the current directory) for manager, node, and workflow
    definition YAML files and validates them against their schemas.

    \b
    Examples:
        madsci validate                       Validate current directory
        madsci validate examples/example_lab/  Validate a specific directory
        madsci validate path/to/file.yaml     Validate a single file
        madsci validate --json                Machine-readable output
    """
    from madsci.client.cli.utils.output import get_console

    console = get_console(ctx)

    results = _scan_and_validate(paths)

    if as_json or (ctx.obj and ctx.obj.get("json")):
        console.print_json(_format_json(results))
        return

    if not results:
        console.print("[yellow]No MADSci configuration files found.[/yellow]")
        return

    _valid, warn_count, error_count = _print_results(results, console)

    if error_count > 0 or (strict and warn_count > 0):
        ctx.exit(1)
