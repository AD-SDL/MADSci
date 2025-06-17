"""Resource Template Models for MADSci - Smart defaults and validation for resource creation."""

from typing import Any, Optional

from madsci.common.types.base_types import BaseModel
from madsci.common.types.resource_types import RESOURCE_TYPE_MAP, ResourceDefinition
from madsci.common.types.resource_types.custom_types import CustomResourceTypes
from pydantic import Field, field_validator


class ResourceTemplate(BaseModel):
    """Template for creating ResourceDefinitions with smart defaults."""

    template_name: str = Field(
        title="Template Name",
        description="Unique name for this template",
    )
    template_description: Optional[str] = Field(
        default=None,
        title="Template Description",
        description="Description of what this template is for",
    )
    base_custom_type_name: str = Field(
        title="Base Custom Type Name",
        description="Name of the CustomResourceType this template is based on",
    )
    defaults: dict[str, Any] = Field(
        default_factory=dict,
        title="Default Values",
        description="Default values to apply when creating resources from this template",
    )
    tags: list[str] = Field(
        default_factory=list,
        title="Tags",
        description="Tags for organizing and searching templates",
    )
    created_by: Optional[str] = Field(
        default=None,
        title="Created By",
        description="User who created this template",
    )
    version: str = Field(
        default="1.0.0",
        title="Version",
        description="Version of this template",
    )

    @field_validator("template_name")
    @classmethod
    def validate_template_name(cls, v: str) -> str:
        """Validate template name is not empty."""
        if not v or not v.strip():
            raise ValueError("Template name cannot be empty")
        return v.strip()


class TemplateCreateRequest(BaseModel):
    """Request to create a resource from a template."""

    template_name: str = Field(
        title="Template Name",
        description="Name of the template to use",
    )
    overrides: dict[str, Any] = Field(
        default_factory=dict,
        title="Override Values",
        description="Values to override from the template defaults",
    )
    resource_name: Optional[str] = Field(
        default=None,
        title="Resource Name",
        description="Specific name for the resource (if not provided, will use template defaults)",
    )


class TemplateValidationResult(BaseModel):
    """Result of template validation."""

    is_valid: bool = Field(
        title="Is Valid",
        description="Whether the template/creation request is valid",
    )
    errors: list[str] = Field(
        default_factory=list,
        title="Validation Errors",
        description="List of validation error messages",
    )
    warnings: list[str] = Field(
        default_factory=list,
        title="Validation Warnings",
        description="List of validation warning messages",
    )


def create_resource_from_template(
    template: ResourceTemplate,
    request: TemplateCreateRequest,
    available_custom_types: dict[str, CustomResourceTypes],
) -> ResourceDefinition:
    """
    Create a ResourceDefinition from a template and creation request.

    Args:
        template: The ResourceTemplate to use
        request: The creation request with overrides
        available_custom_types: dict mapping custom type names to CustomResourceType instances

    Returns:
        A properly configured ResourceDefinition instance

    Raises:
        ValueError: If template references unknown custom type or validation fails
    """
    # Look up the referenced custom type
    if template.base_custom_type_name not in available_custom_types:
        raise ValueError(f"Unknown custom type: {template.base_custom_type_name}")

    custom_type = available_custom_types[template.base_custom_type_name]

    # Get the base_type to determine which ResourceDefinition class to use
    base_type = custom_type.base_type
    if base_type not in RESOURCE_TYPE_MAP:
        raise ValueError(f"Unknown base type: {base_type}")

    definition_class = RESOURCE_TYPE_MAP[base_type]["definition"]

    # Start with template defaults
    resource_data = template.defaults.copy()

    # Apply user overrides
    resource_data.update(request.overrides)

    # Set required fields if not already provided
    if request.resource_name:
        resource_data["resource_name"] = request.resource_name

    # Ensure resource_class points to the custom type
    resource_data["resource_class"] = template.base_custom_type_name

    # Ensure base_type matches the custom type
    resource_data["base_type"] = base_type

    # Create and return the ResourceDefinition instance
    return definition_class.model_validate(resource_data)


def validate_template(
    template: ResourceTemplate, available_custom_types: dict[str, CustomResourceTypes]
) -> TemplateValidationResult:
    """
    Validate that a template is properly configured.

    Args:
        template: The ResourceTemplate to validate
        available_custom_types: dict mapping custom type names to CustomResourceType instances

    Returns:
        TemplateValidationResult with validation status and any errors
    """
    errors = []
    warnings = []

    # Check if referenced custom type exists
    if template.base_custom_type_name not in available_custom_types:
        errors.append(
            f"Template references unknown custom type: {template.base_custom_type_name}"
        )
        return TemplateValidationResult(
            is_valid=False, errors=errors, warnings=warnings
        )

    custom_type = available_custom_types[template.base_custom_type_name]

    # Check if base_type is supported
    if custom_type.base_type not in RESOURCE_TYPE_MAP:
        errors.append(f"Custom type has unsupported base_type: {custom_type.base_type}")

    # Try to create a minimal ResourceDefinition to check if defaults are valid
    try:
        definition_class = RESOURCE_TYPE_MAP[custom_type.base_type]["definition"]
        test_data = template.defaults.copy()
        test_data.update(
            {
                "resource_name": "test_validation",
                "resource_class": template.base_custom_type_name,
                "base_type": custom_type.base_type,
            }
        )
        definition_class.model_validate(test_data)
    except Exception as e:
        errors.append(f"Template defaults are invalid: {e!s}")

    return TemplateValidationResult(
        is_valid=len(errors) == 0, errors=errors, warnings=warnings
    )
