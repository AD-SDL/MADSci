"""
Template system types for MADSci.

This module defines the types used by the template system for scaffolding
new MADSci components (modules, nodes, experiments, workflows, labs).
"""

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

from madsci.common.types.base_types import MadsciBaseModel
from pydantic import Field


class ParameterType(str, Enum):
    """Types of template parameters."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    CHOICE = "choice"
    MULTI_CHOICE = "multi_choice"
    PATH = "path"


class TemplateCategory(str, Enum):
    """Categories of templates."""

    MODULE = "module"
    INTERFACE = "interface"
    NODE = "node"
    EXPERIMENT = "experiment"
    WORKFLOW = "workflow"
    LAB = "lab"
    COMM = "comm"
    ADDON = "addon"


class ParameterChoice(MadsciBaseModel):
    """A choice option for choice/multi_choice parameters."""

    value: str = Field(description="The value to use when this choice is selected")
    label: str = Field(description="Human-readable label for the choice")
    description: Optional[str] = Field(
        default=None, description="Detailed description of the choice"
    )
    default: bool = Field(
        default=False, description="Whether this is the default choice"
    )


class TemplateParameter(MadsciBaseModel):
    """Definition of a template parameter."""

    name: str = Field(description="Parameter name (used in templates)")
    type: ParameterType = Field(description="Type of the parameter")
    description: str = Field(description="Human-readable description")
    required: bool = Field(
        default=True, description="Whether the parameter is required"
    )
    default: Optional[Any] = Field(default=None, description="Default value")

    # For string type
    pattern: Optional[str] = Field(
        default=None, description="Regex pattern for validation"
    )
    min_length: Optional[int] = Field(default=None, description="Minimum string length")
    max_length: Optional[int] = Field(default=None, description="Maximum string length")

    # For numeric types
    min: Optional[Union[int, float]] = Field(
        default=None, description="Minimum value (inclusive)"
    )
    max: Optional[Union[int, float]] = Field(
        default=None, description="Maximum value (inclusive)"
    )

    # For choice types
    choices: Optional[list[ParameterChoice]] = Field(
        default=None, description="Available choices"
    )


class TemplateFile(MadsciBaseModel):
    """A file to be generated from template."""

    source: str = Field(description="Relative path to template file")
    destination: str = Field(
        description="Output path (can use template variables like {{name}})"
    )
    condition: Optional[str] = Field(
        default=None, description="Jinja2 condition for inclusion"
    )


class TemplateHook(MadsciBaseModel):
    """A hook to run after generation."""

    command: str = Field(description="Command to execute")
    description: Optional[str] = Field(
        default=None, description="Human-readable description"
    )
    working_directory: Optional[str] = Field(
        default=None, description="Working directory for command"
    )
    continue_on_error: bool = Field(
        default=False, description="Whether to continue if command fails"
    )


class TemplateManifest(MadsciBaseModel):
    """The template.yaml manifest file."""

    name: str = Field(description="Human-readable template name")
    version: str = Field(description="Template version (semver)")
    description: str = Field(description="Template description")
    category: TemplateCategory = Field(
        description="Category (module, node, experiment, etc.)"
    )
    tags: list[str] = Field(default_factory=list, description="Search tags")
    skills: list[str] = Field(
        default_factory=list,
        description="Agent skill names to include in generated project",
    )

    # Optional metadata
    author: Optional[str] = Field(default=None, description="Template author")
    license: Optional[str] = Field(default=None, description="License identifier")
    min_madsci_version: Optional[str] = Field(
        default=None, description="Minimum MADSci version required"
    )
    schema_version: str = Field(
        default="1.0", description="Template schema version for compatibility"
    )

    # Parameters
    parameters: list[TemplateParameter] = Field(
        default_factory=list, description="Parameters that users must provide"
    )

    # Files to generate
    files: list[TemplateFile] = Field(
        default_factory=list, description="Files to generate"
    )

    # Post-generation hooks
    hooks: Optional[dict[str, list[TemplateHook]]] = Field(
        default=None, description="Lifecycle hooks (post_generate, etc.)"
    )

    # Model validation for generated config files
    target_model: Optional[str] = Field(
        default=None,
        description=(
            "Dotted import path to the Pydantic model that template YAML/JSON output "
            "should validate against (e.g., 'madsci.common.types.workflow_types.WorkflowDefinition'). "
            "Used for automated validation of generated config files."
        ),
    )


class GeneratedProject(MadsciBaseModel):
    """Result of template generation."""

    template_name: str = Field(description="Name of template used")
    template_version: str = Field(description="Version of template used")
    output_directory: Path = Field(description="Directory where files were created")
    files_created: list[Path] = Field(
        default_factory=list, description="List of files created"
    )
    parameters_used: dict[str, Any] = Field(
        default_factory=dict, description="Parameter values used"
    )
    hooks_executed: list[str] = Field(
        default_factory=list, description="Hooks that were executed"
    )
    skills_included: list[str] = Field(
        default_factory=list,
        description="Agent skills copied into the generated project",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="When the project was generated",
    )


class TemplateInfo(MadsciBaseModel):
    """Information about an available template."""

    id: str = Field(description="Template identifier (e.g., 'module/device')")
    name: str = Field(description="Human-readable name")
    version: str = Field(description="Template version")
    description: str = Field(description="Template description")
    category: TemplateCategory = Field(description="Template category")
    tags: list[str] = Field(default_factory=list, description="Search tags")
    source: str = Field(description="Source of template (bundled, user, remote)")
    path: Path = Field(description="Path to template directory")
