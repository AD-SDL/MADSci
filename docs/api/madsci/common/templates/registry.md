Module madsci.common.templates.registry
=======================================
Template registry for MADSci.

This module provides discovery and management of templates from multiple sources:
bundled templates, user templates, and remote templates.

Classes
-------

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
