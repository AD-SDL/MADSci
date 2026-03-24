"""
Template engine for MADSci.

This module provides the engine for rendering templates into generated projects.
"""

import importlib.resources
import logging
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from jinja2.sandbox import SandboxedEnvironment
from madsci.common.types.template_types import (
    GeneratedProject,
    ParameterType,
    TemplateManifest,
)

logger = logging.getLogger(__name__)


def pascal_case(value: str) -> str:
    """Convert snake_case to PascalCase.

    Args:
        value: A snake_case string.

    Returns:
        The PascalCase version.

    Example:
        >>> pascal_case("my_module_name")
        'MyModuleName'
    """
    return "".join(word.capitalize() for word in value.split("_"))


def camel_case(value: str) -> str:
    """Convert snake_case to camelCase.

    Args:
        value: A snake_case string.

    Returns:
        The camelCase version.

    Example:
        >>> camel_case("my_module_name")
        'myModuleName'
    """
    words = value.split("_")
    return words[0] + "".join(word.capitalize() for word in words[1:])


def kebab_case(value: str) -> str:
    """Convert snake_case to kebab-case.

    Args:
        value: A snake_case string.

    Returns:
        The kebab-case version.

    Example:
        >>> kebab_case("my_module_name")
        'my-module-name'
    """
    return value.replace("_", "-")


class TemplateError(Exception):
    """Base exception for template errors."""


class TemplateValidationError(TemplateError):
    """Validation errors for template parameters."""

    def __init__(self, errors: list[str]) -> None:
        """Initialize with a list of validation errors.

        Args:
            errors: List of validation error messages.
        """
        self.errors = errors
        super().__init__(f"Validation errors: {errors}")


class TemplateHookError(TemplateError):
    """Error running template hook."""


class TemplateEngine:
    """Engine for rendering MADSci templates.

    This class handles loading a template, validating parameters, and
    rendering the template files to an output directory.

    Example:
        engine = TemplateEngine(Path("templates/module/device"))

        # Get default parameter values
        defaults = engine.get_default_values()

        # Validate custom parameters
        errors = engine.validate_parameters({"module_name": "my_device"})

        # Render the template
        result = engine.render(
            output_dir=Path("./output"),
            parameters={"module_name": "my_device"},
        )
    """

    def __init__(self, template_dir: Path, *, sandboxed: bool = False) -> None:
        """Initialize the template engine.

        Args:
            template_dir: Path to the template directory containing template.yaml.
            sandboxed: If True, use Jinja2's SandboxedEnvironment to restrict
                template code execution.  Recommended for user/remote templates.

        Raises:
            TemplateError: If the template manifest cannot be loaded.
        """
        self.template_dir = template_dir
        self._sandboxed = sandboxed
        self.manifest = self._load_manifest()
        self._jinja_env = self._create_jinja_env()

    def _load_manifest(self) -> TemplateManifest:
        """Load template manifest from template.yaml.

        Returns:
            The parsed template manifest.

        Raises:
            TemplateError: If the manifest file is not found or invalid.
        """
        manifest_path = self.template_dir / "template.yaml"
        if not manifest_path.exists():
            raise TemplateError(f"Template manifest not found: {manifest_path}")

        return TemplateManifest.from_yaml(manifest_path)

    def _create_jinja_env(self) -> Environment:
        """Create Jinja2 environment with custom filters.

        Returns:
            Configured Jinja2 environment.
        """
        env_kwargs = {
            "loader": FileSystemLoader(str(self.template_dir)),
            "undefined": StrictUndefined,
            "keep_trailing_newline": True,
            "trim_blocks": True,
            "lstrip_blocks": True,
        }
        if self._sandboxed:
            env = SandboxedEnvironment(**env_kwargs)
        else:
            env = Environment(**env_kwargs)  # noqa: S701 - trusted bundled templates

        # Add custom filters
        env.filters["pascal_case"] = pascal_case
        env.filters["camel_case"] = camel_case
        env.filters["kebab_case"] = kebab_case
        # Note: "upper" and "lower" are Jinja2 built-in filters.

        return env

    def _resolve_skills_dir(self) -> Path | None:
        """Resolve the _skills/ directory containing bundled agent skills.

        Walks up from the template directory to find _skills/ in bundled_templates,
        falling back to importlib.resources for installed packages.

        Returns:
            Path to _skills/ directory, or None if not found.
        """
        # Walk up from template_dir looking for _skills/ sibling
        current = self.template_dir
        for _ in range(5):
            candidate = current.parent / "_skills"
            if candidate.is_dir():
                return candidate
            current = current.parent

        # Fallback: use importlib.resources
        try:
            resource = (
                importlib.resources.files("madsci.common")
                / "bundled_templates"
                / "_skills"
            )
            path = Path(str(resource))
            if path.is_dir():
                return path
        except (TypeError, FileNotFoundError):
            pass

        return None

    def validate_parameters(self, values: dict[str, Any]) -> list[str]:  # noqa: C901, PLR0912
        """Validate parameter values against manifest.

        Args:
            values: Parameter values to validate.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        for param in self.manifest.parameters:
            value = values.get(param.name)

            # Check required
            if param.required and value is None:
                errors.append(f"Required parameter '{param.name}' is missing")
                continue

            if value is None:
                continue

            # Type-specific validation
            if param.type == ParameterType.STRING:
                if not isinstance(value, str):
                    errors.append(f"Parameter '{param.name}' must be a string")
                    continue
                if param.pattern and not re.match(param.pattern, value):
                    errors.append(
                        f"Parameter '{param.name}' does not match pattern: {param.pattern}"
                    )
                if param.min_length is not None and len(value) < param.min_length:
                    errors.append(
                        f"Parameter '{param.name}' is too short (min: {param.min_length})"
                    )
                if param.max_length is not None and len(value) > param.max_length:
                    errors.append(
                        f"Parameter '{param.name}' is too long (max: {param.max_length})"
                    )

            elif param.type == ParameterType.PATH:
                if not isinstance(value, str):
                    errors.append(f"Parameter '{param.name}' must be a string")
                elif "\x00" in value:
                    errors.append(
                        f"Parameter '{param.name}' contains invalid null byte"
                    )

            elif param.type in (ParameterType.INTEGER, ParameterType.FLOAT):
                if not isinstance(value, (int, float)):
                    errors.append(f"Parameter '{param.name}' must be a number")
                    continue
                if param.min is not None and value < param.min:
                    errors.append(
                        f"Parameter '{param.name}' is below minimum: {param.min}"
                    )
                if param.max is not None and value > param.max:
                    errors.append(
                        f"Parameter '{param.name}' is above maximum: {param.max}"
                    )

            elif param.type == ParameterType.CHOICE:
                valid_values = [c.value for c in param.choices or []]
                if value not in valid_values:
                    errors.append(
                        f"Parameter '{param.name}' must be one of: {valid_values}"
                    )

            elif param.type == ParameterType.MULTI_CHOICE:
                if not isinstance(value, list):
                    errors.append(f"Parameter '{param.name}' must be a list")
                    continue
                valid_values = [c.value for c in param.choices or []]
                for v in value:
                    if v not in valid_values:
                        errors.append(
                            f"Parameter '{param.name}' contains invalid value: {v}"
                        )

            elif param.type == ParameterType.BOOLEAN:
                if not isinstance(value, bool):
                    errors.append(f"Parameter '{param.name}' must be a boolean")

        return errors

    def get_default_values(self) -> dict[str, Any]:
        """Get default values for all parameters.

        Returns:
            Dictionary of parameter names to their default values.
        """
        defaults: dict[str, Any] = {}

        for param in self.manifest.parameters:
            if param.default is not None:
                defaults[param.name] = param.default
            elif param.type == ParameterType.MULTI_CHOICE:
                # Default to choices marked as default
                defaults[param.name] = [
                    c.value for c in (param.choices or []) if c.default
                ]

        return defaults

    def render(  # noqa: C901, PLR0912, PLR0915
        self,
        output_dir: Path,
        parameters: dict[str, Any],
        dry_run: bool = False,
    ) -> GeneratedProject:
        """Render template to output directory.

        Args:
            output_dir: Directory to write output files.
            parameters: Parameter values.
            dry_run: If True, don't write files, just return what would be created.

        Returns:
            GeneratedProject with details of what was created.

        Raises:
            TemplateValidationError: If parameter validation fails.
            TemplateHookError: If a post-generation hook fails.
        """
        # Merge with defaults
        values = self.get_default_values()
        values.update(parameters)

        # Add metadata to template context
        values["template_name"] = self.manifest.name
        values["template_version"] = self.manifest.version

        # Validate
        errors = self.validate_parameters(values)
        if errors:
            raise TemplateValidationError(errors)

        files_created: list[Path] = []

        for file_spec in self.manifest.files:
            # Check condition
            if file_spec.condition:
                condition_template = self._jinja_env.from_string(file_spec.condition)
                condition_result = condition_template.render(**values).strip().lower()
                if condition_result not in ("true", "1", "yes"):
                    continue

            # Render source path (for resolving the actual file on disk)
            source_path_template = self._jinja_env.from_string(file_spec.source)
            source_path = source_path_template.render(**values)

            # Keep the original (unrendered) source path for Jinja2 template
            # loading, since the files on disk still have {{variable}}
            # placeholders in their names.
            original_source_path = file_spec.source

            # Render destination path
            dest_path_template = self._jinja_env.from_string(file_spec.destination)
            dest_path = dest_path_template.render(**values)

            # Full paths
            source_full = self.template_dir / source_path
            dest_full = output_dir / dest_path

            # Prevent path traversal: rendered source must stay inside template_dir
            if not source_full.resolve().is_relative_to(self.template_dir.resolve()):
                raise TemplateValidationError(
                    [f"Path traversal detected in source: {source_path}"]
                )

            # Prevent path traversal: rendered destination must stay inside output_dir
            if not dest_full.resolve().is_relative_to(output_dir.resolve()):
                raise TemplateValidationError(
                    [f"Path traversal detected in destination: {dest_path}"]
                )

            if not dry_run:
                # Create parent directories
                dest_full.parent.mkdir(parents=True, exist_ok=True)

                # Render and write
                if source_full.suffix == ".j2":
                    # Jinja2 template - use original_source_path since the
                    # file on disk has {{variable}} placeholders in its name
                    template = self._jinja_env.get_template(original_source_path)
                    content = template.render(**values)
                    dest_full.write_text(content)
                else:
                    # Static file - copy as-is
                    shutil.copy2(source_full, dest_full)

                logger.debug("Created file: dest_path=%s", str(dest_full))

            files_created.append(dest_full)

        # Copy agent skills
        skills_included: list[str] = []
        if self.manifest.skills:
            skills_dir = self._resolve_skills_dir()
            if skills_dir:
                for skill_name in self.manifest.skills:
                    skill_source = skills_dir / skill_name / "SKILL.md"
                    if not skill_source.is_file():
                        logger.warning(
                            "Skill not found, skipping: skill_name=%s", skill_name
                        )
                        continue
                    skill_dest = (
                        output_dir / ".agents" / "skills" / skill_name / "SKILL.md"
                    )
                    if not dry_run:
                        skill_dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(skill_source, skill_dest)
                        logger.debug(
                            "Copied skill: skill_name=%s dest=%s",
                            skill_name,
                            str(skill_dest),
                        )
                    files_created.append(skill_dest)
                    skills_included.append(skill_name)
            else:
                logger.warning("Skills directory not found, skipping skill copying")

        # Run post-generation hooks
        hooks_executed: list[str] = []
        if not dry_run and self.manifest.hooks:
            for hook in self.manifest.hooks.get("post_generate", []):
                # Render command
                cmd_template = self._jinja_env.from_string(hook.command)
                cmd = cmd_template.render(**values)

                try:
                    # Tokenize the command to avoid shell injection.
                    # shlex.split + shell=False prevents user-supplied
                    # template values from being interpreted as shell syntax.
                    subprocess.run(  # noqa: S603
                        shlex.split(cmd),
                        shell=False,
                        cwd=output_dir,
                        check=not hook.continue_on_error,
                        capture_output=True,
                    )
                    hooks_executed.append(cmd)
                    logger.debug("Executed hook: cmd=%s", cmd)
                except subprocess.CalledProcessError as e:
                    if not hook.continue_on_error:
                        raise TemplateHookError(
                            f"Hook failed: {cmd}\n{e.stderr.decode() if e.stderr else ''}"
                        ) from e

        logger.info(
            "Generated files from template: files_count=%d template_name=%s",
            len(files_created),
            self.manifest.name,
        )

        return GeneratedProject(
            template_name=self.manifest.name,
            template_version=self.manifest.version,
            output_directory=output_dir,
            files_created=files_created,
            parameters_used=values,
            hooks_executed=hooks_executed,
            skills_included=skills_included,
        )
