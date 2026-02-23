Module madsci.common.templates
==============================
Template system for MADSci.

This module provides scaffolding for generating new MADSci components
(modules, nodes, experiments, workflows, labs) from predefined templates.

Example:
    from madsci.common.templates import TemplateRegistry, TemplateEngine

    # List available templates
    registry = TemplateRegistry()
    templates = registry.list_templates(category="module")

    # Get and render a template
    engine = registry.get_template("module/device")
    result = engine.render(
        output_dir=Path("./my_project"),
        parameters={"module_name": "my_device"},
    )

Sub-modules
-----------
* madsci.common.templates.engine
* madsci.common.templates.registry

Classes
-------

`TemplateEngine(template_dir: pathlib.Path, *, sandboxed: bool = False)`
:   Engine for rendering MADSci templates.

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

    Initialize the template engine.

    Args:
        template_dir: Path to the template directory containing template.yaml.
        sandboxed: If True, use Jinja2's SandboxedEnvironment to restrict
            template code execution.  Recommended for user/remote templates.

    Raises:
        TemplateError: If the template manifest cannot be loaded.

    ### Methods

    `get_default_values(self) ‑> dict[str, typing.Any]`
    :   Get default values for all parameters.

        Returns:
            Dictionary of parameter names to their default values.

    `render(self, output_dir: pathlib.Path, parameters: dict[str, typing.Any], dry_run: bool = False) ‑> madsci.common.types.template_types.GeneratedProject`
    :   Render template to output directory.

        Args:
            output_dir: Directory to write output files.
            parameters: Parameter values.
            dry_run: If True, don't write files, just return what would be created.

        Returns:
            GeneratedProject with details of what was created.

        Raises:
            TemplateValidationError: If parameter validation fails.
            TemplateHookError: If a post-generation hook fails.

    `validate_parameters(self, values: dict[str, typing.Any]) ‑> list[str]`
    :   Validate parameter values against manifest.

        Args:
            values: Parameter values to validate.

        Returns:
            List of validation error messages (empty if valid).

`TemplateError(*args, **kwargs)`
:   Base exception for template errors.

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException

    ### Descendants

    * madsci.common.templates.engine.TemplateHookError
    * madsci.common.templates.engine.TemplateValidationError

`TemplateHookError(*args, **kwargs)`
:   Error running template hook.

    ### Ancestors (in MRO)

    * madsci.common.templates.engine.TemplateError
    * builtins.Exception
    * builtins.BaseException

`TemplateNotFoundError(*args, **kwargs)`
:   Template not found in registry.

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException

`TemplateRegistry(user_template_dir: pathlib.Path | None = None)`
:   Registry for discovering and loading templates.

    Templates can come from three sources:
    1. Bundled templates (shipped with MADSci)
    2. User templates (~/.madsci/templates/)
    3. Remote templates (installed from git repos)

    Example:
        registry = TemplateRegistry()

        # List all templates
        templates = registry.list_templates()

        # Filter by category
        module_templates = registry.list_templates(category="module")

        # Get a specific template
        engine = registry.get_template("module/device")

        # Install from remote
        registry.install_template("https://github.com/org/my-templates.git")

    Initialize the template registry.

    Args:
        user_template_dir: Directory for user templates.
                          Defaults to ~/.madsci/templates/.

    ### Methods

    `get_template(self, template_id: str) ‑> madsci.common.templates.engine.TemplateEngine`
    :   Get a template engine by ID.

        Args:
            template_id: Template identifier (e.g., "module/device").

        Returns:
            TemplateEngine for the template.

        Raises:
            TemplateNotFoundError: If template is not found.
            ValueError: If template_id format is invalid.

    `install_template(self, source: str, name: str | None = None, local: bool = False) ‑> pathlib.Path`
    :   Install a template from a source.

        Args:
            source: Path to template directory or git URL.
            name: Optional name override for the installed template.
            local: If True, treat source as local path (for air-gapped environments).

        Returns:
            Path to installed template.

        Raises:
            TemplateNotFoundError: If source path doesn't exist.
            TemplateError: If template is invalid or installation fails.

    `list_templates(self, category: madsci.common.types.template_types.TemplateCategory | None = None, tags: list[str] | None = None) ‑> list[madsci.common.types.template_types.TemplateInfo]`
    :   List available templates.

        Args:
            category: Filter by category (module, node, experiment, etc.).
            tags: Filter by tags (templates matching any tag are included).

        Returns:
            List of template info objects.

    `uninstall_template(self, template_id: str) ‑> bool`
    :   Uninstall a user-installed template.

        Args:
            template_id: Template identifier to uninstall.

        Returns:
            True if template was uninstalled, False if not found.

        Note:
            Bundled templates cannot be uninstalled.

`TemplateValidationError(errors: list[str])`
:   Validation errors for template parameters.

    Initialize with a list of validation errors.

    Args:
        errors: List of validation error messages.

    ### Ancestors (in MRO)

    * madsci.common.templates.engine.TemplateError
    * builtins.Exception
    * builtins.BaseException
