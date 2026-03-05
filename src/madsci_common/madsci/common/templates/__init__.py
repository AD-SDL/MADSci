"""
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
"""

from madsci.common.templates.engine import (
    TemplateEngine,
    TemplateError,
    TemplateHookError,
    TemplateValidationError,
)
from madsci.common.templates.registry import TemplateNotFoundError, TemplateRegistry

__all__ = [
    "TemplateEngine",
    "TemplateError",
    "TemplateHookError",
    "TemplateNotFoundError",
    "TemplateRegistry",
    "TemplateValidationError",
]
