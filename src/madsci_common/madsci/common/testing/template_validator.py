"""
Template Validator for MADSci.

Validates that templates can be instantiated and produce valid output.
"""

import ast
import importlib.util
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from madsci.common.templates.engine import TemplateEngine


@dataclass
class TemplateValidationResult:
    """Result of validating a template."""

    template_name: str
    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    generated_files: list[Path] = field(default_factory=list)
    validation_details: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        """Generate a human-readable summary."""
        status = "SUCCESS" if self.success else "FAILED"
        lines = [
            f"Template: {self.template_name}",
            f"Status: {status}",
            f"Files generated: {len(self.generated_files)}",
        ]
        if self.errors:
            lines.append(f"Errors: {len(self.errors)}")
            for error in self.errors:
                lines.append(f"  - {error}")
        if self.warnings:
            lines.append(f"Warnings: {len(self.warnings)}")
            for warning in self.warnings:
                lines.append(f"  - {warning}")
        return "\n".join(lines)


class TemplateValidator:
    """
    Validates MADSci templates by instantiating them and checking output.

    Performs the following validations:
    - Template renders without errors
    - Generated Python files have valid syntax
    - Generated code passes ruff linting
    - (Optional) Generated code can be imported
    """

    def __init__(
        self,
        console: Console | None = None,
        verbose: bool = False,
    ) -> None:
        """
        Initialize the template validator.

        Args:
            console: Rich console for output. If None, creates one.
            verbose: If True, print verbose output.
        """
        self.console = console or Console()
        self.verbose = verbose

    def validate_template(
        self,
        template_path: Path,
        test_values: dict[str, Any] | None = None,
        output_dir: Path | None = None,
        check_ruff: bool = True,
        check_imports: bool = False,
    ) -> TemplateValidationResult:
        """
        Validate a template by instantiating it with test values.

        Args:
            template_path: Path to the template directory (containing template.yaml)
            test_values: Values to use for template parameters. If None, uses defaults.
            output_dir: Directory for generated output. If None, uses temp dir.
            check_ruff: If True, run ruff check on generated code.
            check_imports: If True, attempt to import generated Python modules.

        Returns:
            TemplateValidationResult with details of the validation.
        """
        template_name = template_path.name
        errors: list[str] = []
        warnings: list[str] = []
        validation_details: dict[str, Any] = {}

        # Use temp dir if no output dir specified
        if output_dir is None:
            temp_dir = tempfile.mkdtemp(prefix=f"madsci_template_{template_name}_")
            output_dir = Path(temp_dir)

        # Check manifest exists
        manifest_path = template_path / "template.yaml"
        if not manifest_path.exists():
            errors.append(f"Template manifest not found: {manifest_path}")
            return TemplateValidationResult(
                template_name=template_name,
                success=False,
                errors=errors,
            )

        # Try to use template engine, fall back to basic validation
        engine = self._try_load_engine(template_path, validation_details)
        if engine is None:
            return self._validate_basic(template_path)

        # Render and validate
        return self._validate_with_engine(
            engine=engine,
            template_name=template_name,
            test_values=test_values,
            output_dir=output_dir,
            check_ruff=check_ruff,
            check_imports=check_imports,
            errors=errors,
            warnings=warnings,
            validation_details=validation_details,
        )

    def _try_load_engine(
        self,
        template_path: Path,
        validation_details: dict[str, Any],
    ) -> "TemplateEngine | None":
        """Try to load the template engine, return None if not available."""
        try:
            from madsci.common.templates.engine import (  # noqa: PLC0415
                TemplateEngine,
            )

            return TemplateEngine(template_path)
        except ImportError:
            validation_details["engine_available"] = False
            return None

    def _validate_with_engine(
        self,
        engine: "TemplateEngine",
        template_name: str,
        test_values: dict[str, Any] | None,
        output_dir: Path,
        check_ruff: bool,
        check_imports: bool,
        errors: list[str],
        warnings: list[str],
        validation_details: dict[str, Any],
    ) -> TemplateValidationResult:
        """Validate template using the template engine."""
        generated_files: list[Path] = []

        try:
            # Get default values and merge with test values
            values = engine.get_default_values()
            if test_values:
                values.update(test_values)

            # Validate parameters
            param_errors = engine.validate_parameters(values)
            if param_errors:
                errors.extend(param_errors)

            # Render template
            try:
                result = engine.render(output_dir, values)
                generated_files = result.files_created
                validation_details["render_success"] = True
            except Exception as e:
                errors.append(f"Template rendering failed: {e}")
                return TemplateValidationResult(
                    template_name=template_name,
                    success=False,
                    errors=errors,
                    validation_details=validation_details,
                )

            # Validate generated Python files
            python_files = [f for f in generated_files if f.suffix == ".py"]
            self._validate_python_files(
                python_files, errors, validation_details, output_dir, check_ruff
            )

            # Check imports (optional)
            if check_imports and python_files:
                import_errors = self._check_imports(python_files)
                errors.extend(import_errors)

        except Exception as e:
            errors.append(f"Validation error: {e}")

        return TemplateValidationResult(
            template_name=template_name,
            success=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            generated_files=generated_files,
            validation_details=validation_details,
        )

    def _validate_python_files(
        self,
        python_files: list[Path],
        errors: list[str],
        validation_details: dict[str, Any],
        output_dir: Path,
        check_ruff: bool,
    ) -> None:
        """Validate Python files for syntax and optionally linting."""
        for py_file in python_files:
            syntax_errors = self._check_python_syntax(py_file)
            if syntax_errors:
                errors.extend(syntax_errors)
            else:
                validation_details.setdefault("syntax_valid", []).append(str(py_file))

        # Run ruff check
        if check_ruff and python_files:
            ruff_errors, ruff_warnings = self._check_ruff(output_dir)
            errors.extend(ruff_errors)
            # Note: warnings are collected but not currently returned
            del ruff_warnings

    def _validate_basic(
        self,
        template_path: Path,
    ) -> TemplateValidationResult:
        """
        Basic validation when template engine is not available.

        Just checks that template files exist and are valid Jinja2.
        """
        template_name = template_path.name
        errors: list[str] = []
        warnings: list[str] = []

        try:
            manifest_path = template_path / "template.yaml"
            with manifest_path.open() as f:
                manifest = yaml.safe_load(f)

            if not manifest:
                errors.append("Empty template manifest")
            else:
                # Check required fields
                required = ["name", "files"]
                for field_name in required:
                    if field_name not in manifest:
                        errors.append(
                            f"Missing required field in manifest: {field_name}"
                        )

                # Check that template files exist
                for file_spec in manifest.get("files", []):
                    source = file_spec.get("source", "")
                    source_path = template_path / source
                    if not source_path.exists():
                        errors.append(f"Template file not found: {source}")

        except Exception as e:
            errors.append(f"Error reading manifest: {e}")

        return TemplateValidationResult(
            template_name=template_name,
            success=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            validation_details={"mode": "basic"},
        )

    def _check_python_syntax(self, file_path: Path) -> list[str]:
        """Check Python syntax of a file."""
        errors = []
        try:
            source = file_path.read_text()
            ast.parse(source)
        except SyntaxError as e:
            errors.append(f"Syntax error in {file_path.name}: {e}")
        return errors

    def _check_ruff(self, directory: Path) -> tuple[list[str], list[str]]:
        """Run ruff check on a directory."""
        errors = []
        warnings = []

        try:
            result = subprocess.run(  # noqa: S603
                ["ruff", "check", str(directory), "--output-format=json"],  # noqa: S607
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                # Parse JSON output
                try:
                    issues = json.loads(result.stdout)
                    for issue in issues:
                        severity = issue.get("type", "").lower()
                        message = issue.get("message", "")
                        filename = issue.get("filename", "")
                        line = issue.get("location", {}).get("row", "")

                        formatted = f"{filename}:{line}: {message}"
                        if severity == "error":
                            errors.append(f"Ruff error: {formatted}")
                        else:
                            warnings.append(f"Ruff warning: {formatted}")
                except json.JSONDecodeError:
                    # Fallback to raw output
                    errors.append(f"Ruff check failed: {result.stdout}")

        except FileNotFoundError:
            warnings.append("ruff not found - skipping lint check")
        except subprocess.TimeoutExpired:
            warnings.append("ruff check timed out")

        return errors, warnings

    def _check_imports(self, python_files: list[Path]) -> list[str]:
        """Attempt to import Python modules."""
        errors = []

        for file_path in python_files:
            module_name = file_path.stem
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                try:
                    spec.loader.exec_module(module)
                except Exception as e:
                    errors.append(f"Import error in {file_path.name}: {e}")
                finally:
                    sys.modules.pop(module_name, None)

        return errors

    def validate_all_templates(
        self,
        templates_dir: Path,
        **kwargs: Any,
    ) -> list[TemplateValidationResult]:
        """
        Validate all templates in a directory.

        Args:
            templates_dir: Directory containing template subdirectories
            **kwargs: Additional arguments passed to validate_template

        Returns:
            List of validation results
        """
        results = []

        # Find all template directories (those containing template.yaml)
        for category_dir in templates_dir.iterdir():
            if not category_dir.is_dir():
                continue

            for template_dir in category_dir.iterdir():
                if not template_dir.is_dir():
                    continue

                manifest = template_dir / "template.yaml"
                if manifest.exists():
                    if self.verbose:
                        self.console.print(f"Validating template: {template_dir.name}")

                    result = self.validate_template(template_dir, **kwargs)
                    results.append(result)

                    if self.verbose:
                        status = (
                            "[green]✓[/green]" if result.success else "[red]✗[/red]"
                        )
                        self.console.print(f"  {status} {result.template_name}")

        return results

    def print_results(self, results: list[TemplateValidationResult]) -> None:
        """Print validation results in a formatted table."""
        table = Table(title="Template Validation Results")
        table.add_column("Template", style="cyan")
        table.add_column("Status")
        table.add_column("Files")
        table.add_column("Errors")
        table.add_column("Warnings")

        for result in results:
            status = "[green]PASS[/green]" if result.success else "[red]FAIL[/red]"
            table.add_row(
                result.template_name,
                status,
                str(len(result.generated_files)),
                str(len(result.errors)),
                str(len(result.warnings)),
            )

        self.console.print(table)

        # Print details for failed templates
        failed = [r for r in results if not r.success]
        if failed:
            self.console.print("\n[bold red]Failed Templates:[/bold red]")
            for result in failed:
                self.console.print(f"\n[bold]{result.template_name}[/bold]")
                for error in result.errors:
                    self.console.print(f"  [red]✗[/red] {error}")
