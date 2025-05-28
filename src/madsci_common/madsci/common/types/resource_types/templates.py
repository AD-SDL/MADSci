"""Resource Template Models for MADSci - Smart defaults and validation for resource creation."""

from typing import Any, Optional

from madsci.common.types.base_types import BaseModel
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
