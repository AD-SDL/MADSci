"""
MADSci Resource Templates - Simple File-Based Approach

Templates are automatically available when imported - no manual registration needed.
Simple interface: import templates, see what's available, create resources.
"""
# flake8: noqa

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from madsci.common.types.resource_types import RESOURCE_TYPE_MAP
from madsci.common.types.resource_types.definitions import ResourceDefinitions
from madsci.common.types.resource_types.resource_enums import ResourceTypeEnum


class TemplateSource(str, Enum):
    """Source of a resource template."""

    NODE = "node"
    MANAGER = "manager"
    EXPERIMENT = "experiment"
    SYSTEM = "system"
    USER = "user"


@dataclass
class ResourceTemplate:
    """
    A resource template with default values and constraints.

    Define these in files just like ResourceTypes - simple and maintainable.
    """

    # Required fields (no defaults) must come first
    template_name: str
    display_name: str
    base_type: ResourceTypeEnum

    # Optional fields (with defaults) come after
    description: str = ""
    resource_class: Optional[str] = None  # Custom type name if applicable
    default_values: dict[str, Any] = field(default_factory=dict)
    required_overrides: list[str] = field(
        default_factory=list
    )  # Fields user must provide
    source: TemplateSource = TemplateSource.USER
    tags: list[str] = field(default_factory=list)


class TemplateRegistry:
    """Simple registry that auto-manages templates."""

    def __init__(self):
        self._templates: dict[str, ResourceTemplate] = {}

    def _auto_register(self, template: ResourceTemplate) -> None:
        """Internal method for auto-registration."""
        self._templates[template.template_name] = template

    def add_template(self, template: ResourceTemplate) -> None:
        """Add a new template (for dynamic additions)."""
        self._templates[template.template_name] = template

    def get(self, template_name: str) -> Optional[ResourceTemplate]:
        """Get a template by name."""
        return self._templates.get(template_name)

    def get_all_templates(self) -> dict[str, ResourceTemplate]:
        """Get all templates as a dictionary."""
        return self._templates.copy()

    def get_template_names(self) -> list[str]:
        """Get list of all template names."""
        return list(self._templates.keys())

    def get_templates_by_category(self) -> dict[str, list[str]]:
        """Get templates organized by category (base_type)."""
        categories = {}
        for name, template in self._templates.items():
            category = template.base_type.value
            if category not in categories:
                categories[category] = []
            categories[category].append(name)
        return categories

    def get_templates_by_tags(self, tags: list[str]) -> list[str]:
        """Get template names that have any of the specified tags."""
        matching = []
        for name, template in self._templates.items():
            if any(tag in template.tags for tag in tags):
                matching.append(name)
        return matching

    def list_templates(self, **filters) -> list[ResourceTemplate]:
        """list templates with optional filtering."""
        templates = list(self._templates.values())

        if "source" in filters:
            templates = [t for t in templates if t.source == filters["source"]]
        if "base_type" in filters:
            templates = [t for t in templates if t.base_type == filters["base_type"]]
        if "tags" in filters:
            filter_tags = filters["tags"]
            templates = [
                t for t in templates if any(tag in t.tags for tag in filter_tags)
            ]

        return templates


_template_registry = TemplateRegistry()


def create_resource_from_template(
    template_name: str, resource_name: str, **overrides
) -> ResourceDefinitions:
    """
    Create a ResourceDefinition from a template.

    Simple function that merges template defaults with user overrides.
    """
    template = _template_registry.get(template_name)
    if not template:
        available = _template_registry.get_template_names()
        raise ValueError(
            f"Template '{template_name}' not found. Available: {available}"
        )

    # Check required overrides
    missing_required = [
        field for field in template.required_overrides if field not in overrides
    ]
    if missing_required:
        raise ValueError(f"Missing required fields: {missing_required}")

    # Start with template defaults
    resource_data = template.default_values.copy()

    # Add resource name and type info
    resource_data["resource_name"] = resource_name
    resource_data["base_type"] = template.base_type
    if template.resource_class:
        resource_data["resource_class"] = template.resource_class

    # Apply user overrides
    resource_data.update(overrides)

    if template.base_type not in RESOURCE_TYPE_MAP:
        raise ValueError(f"Unknown base type: {template.base_type}")

    definition_class = RESOURCE_TYPE_MAP[template.base_type]["definition"]

    # Create and return the resource
    return definition_class.model_validate(resource_data)


def add_template(template: ResourceTemplate) -> None:
    """
    Add a new template dynamically.

    This could be enhanced to write to template files for persistence.
    """
    _template_registry.add_template(template)


def validate_resource_against_template(
    resource: ResourceDefinitions, template_name: str
) -> bool:
    """Validate that a resource matches a template's expectations."""
    template = _template_registry.get(template_name)
    if not template:
        return False

    # Basic type checking
    if resource.base_type != template.base_type:
        return False

    if (
        template.resource_class
        and getattr(resource, "resource_class", None) != template.resource_class
    ):
        return False

    return True


# Convenience functions for easy access to templates
def get_all_templates() -> dict[str, ResourceTemplate]:
    """Get all available templates as a dictionary."""
    return _template_registry.get_all_templates()


def get_template_names() -> list[str]:
    """Get list of all available template names."""
    return _template_registry.get_template_names()


def get_templates_by_category() -> dict[str, list[str]]:
    """Get templates organized by resource type."""
    return _template_registry.get_templates_by_category()


def get_templates_by_tags(tags: list[str]) -> list[str]:
    """Get template names that match any of the given tags."""
    return _template_registry.get_templates_by_tags(tags)


def get_template_info(template_name: str) -> Optional[dict[str, Any]]:
    """Get detailed information about a template."""
    template = _template_registry.get(template_name)
    if not template:
        return None

    return {
        "name": template.template_name,
        "display_name": template.display_name,
        "description": template.description,
        "base_type": template.base_type.value,
        "resource_class": template.resource_class,
        "default_values": template.default_values,
        "required_overrides": template.required_overrides,
        "source": template.source.value,
        "tags": template.tags,
    }


def list_templates(**filters) -> list[ResourceTemplate]:
    """list available templates with optional filtering."""
    return _template_registry.list_templates(**filters)


# Auto-registration helper (used internally by template definition files)
def _auto_register_template(template: ResourceTemplate) -> None:
    """Internal function for auto-registering templates when modules are imported."""
    _template_registry._auto_register(template)
