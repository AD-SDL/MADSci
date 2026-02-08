# MADSci Template System Design Document

**Status**: Draft
**Date**: 2026-02-07
**Author**: Claude (AI Assistant)

## Overview

This document defines the design for the MADSci Template System. Templates provide a scaffolding mechanism for generating new MADSci components (nodes, experiments, workflows, labs) from predefined patterns, replacing the current practice of copy-pasting and editing YAML/Python files.

## Problem Statement

### Current State

Users currently create new components by:
1. Finding an existing example (e.g., `example_lab/example_modules/liquidhandler.py`)
2. Copying the file
3. Manually editing to change names, remove unwanted code, add new code
4. Hoping they didn't miss anything

**Problems:**
1. Error-prone manual editing
2. Examples may contain outdated patterns
3. No validation that result is correct
4. No guidance on what to change
5. Users may not know which example to start from

### Goals

1. **Zero copy-paste**: `madsci new node` generates a complete, working node
2. **Guided creation**: Interactive prompts for required information
3. **Best practices built-in**: Templates embody current best practices
4. **Validated output**: Generated code passes linting and tests
5. **Customizable**: Users can create and share custom templates

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Template System Architecture                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                           Template Registry                              ││
│  │                                                                          ││
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         ││
│  │  │ Bundled         │  │ User            │  │ Remote          │         ││
│  │  │ Templates       │  │ Templates       │  │ Templates       │         ││
│  │  │ (in package)    │  │ (~/.madsci/     │  │ (git repos)     │         ││
│  │  │                 │  │  templates/)    │  │                 │         ││
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘         ││
│  │                                                                          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                          Template Engine                                 ││
│  │                                                                          ││
│  │  1. Load template manifest                                               ││
│  │  2. Collect parameter values (interactive or CLI)                       ││
│  │  3. Validate parameters                                                  ││
│  │  4. Render Jinja2 templates                                              ││
│  │  5. Write output files                                                   ││
│  │  6. Run post-generation hooks                                            ││
│  │                                                                          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         Generated Output                                 ││
│  │                                                                          ││
│  │  my_node/                                                                ││
│  │  ├── my_node.py         # Main node implementation                      ││
│  │  ├── config.py          # Node configuration                            ││
│  │  ├── tests/                                                              ││
│  │  │   └── test_my_node.py                                                 ││
│  │  └── README.md          # Documentation                                  ││
│  │                                                                          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Template Structure

### Template Directory Layout

```
templates/
├── module/                         # Complete module repositories
│   ├── basic/
│   │   ├── template.yaml           # Template manifest
│   │   ├── {{module_name}}_module/ # Output directory (templated name)
│   │   │   ├── src/
│   │   │   │   ├── {{module_name}}_rest_node.py.j2
│   │   │   │   ├── {{module_name}}_interface.py.j2
│   │   │   │   ├── {{module_name}}_fake_interface.py.j2
│   │   │   │   └── {{module_name}}_types.py.j2
│   │   │   ├── tests/
│   │   │   │   ├── test_{{module_name}}_node.py.j2
│   │   │   │   └── test_{{module_name}}_interface.py.j2
│   │   │   ├── Dockerfile.j2
│   │   │   ├── pyproject.toml.j2
│   │   │   └── README.md.j2
│   │   └── hooks/
│   │       └── post_generate.py    # Optional post-generation script
│   ├── device/
│   │   └── ...                     # Standard device lifecycle (init, shutdown, status)
│   ├── instrument/
│   │   └── ...                     # Measurement devices (measure, calibrate)
│   ├── liquid_handler/
│   │   └── ...                     # Pipetting operations
│   ├── robot_arm/
│   │   └── ...                     # Pick/place/move operations
│   └── camera/
│       └── ...                     # Image capture/analysis
├── interface/                      # Interface variants for existing modules
│   ├── fake/
│   │   ├── template.yaml
│   │   └── {{module_name}}_fake_interface.py.j2
│   ├── sim/
│   │   ├── template.yaml
│   │   └── {{module_name}}_sim_interface.py.j2
│   └── mock/
│       ├── template.yaml
│       └── {{module_name}}_mock_interface.py.j2
├── node/                           # Node-only templates (when interface exists)
│   └── basic/
│       └── ...                     # Just the REST node server
├── experiment/
│   ├── script/
│   ├── notebook/
│   ├── tui/
│   └── node/
├── workflow/
│   ├── basic/
│   └── multi_step/
├── lab/
│   ├── minimal/
│   ├── standard/
│   └── distributed/
└── workcell/
    └── basic/
```

### Template Manifest (template.yaml)

```yaml
# templates/node/device/template.yaml
name: "Device Node"
version: "1.0.0"
description: "A node for controlling physical devices with standard lifecycle actions"
category: "node"
tags: ["device", "instrument", "hardware"]

# Author information
author: "MADSci Team"
license: "MIT"

# Minimum MADSci version required
min_madsci_version: "0.2.0"

# Parameters that users must provide
parameters:
  - name: node_name
    type: string
    description: "Name for the node (lowercase, underscores allowed)"
    required: true
    pattern: "^[a-z][a-z0-9_]*$"
    default: "my_device"

  - name: node_description
    type: string
    description: "Human-readable description of the node"
    required: true
    default: "A device node"

  - name: node_type
    type: choice
    description: "Type of node"
    required: true
    choices:
      - value: "device"
        label: "Device"
        description: "Physical instruments and robots"
      - value: "compute"
        label: "Compute"
        description: "Data processing nodes"
      - value: "human"
        label: "Human"
        description: "Manual operation steps"
    default: "device"

  - name: port
    type: integer
    description: "Port number for the node REST API"
    required: true
    default: 2000
    min: 1024
    max: 65535

  - name: include_tests
    type: boolean
    description: "Generate test files"
    required: false
    default: true

  - name: actions
    type: multi_choice
    description: "Actions to include"
    required: false
    choices:
      - value: "initialize"
        label: "Initialize"
        description: "Initialize the device"
        default: true
      - value: "shutdown"
        label: "Shutdown"
        description: "Shutdown the device"
        default: true
      - value: "status"
        label: "Status"
        description: "Get device status"
        default: true
      - value: "reset"
        label: "Reset"
        description: "Reset the device"
        default: false
      - value: "calibrate"
        label: "Calibrate"
        description: "Calibrate the device"
        default: false

# Files to generate
files:
  - source: "{{node_name}}/{{node_name}}.py.j2"
    destination: "{{node_name}}/{{node_name}}.py"

  - source: "{{node_name}}/config.py.j2"
    destination: "{{node_name}}/config.py"

  - source: "{{node_name}}/tests/test_{{node_name}}.py.j2"
    destination: "{{node_name}}/tests/test_{{node_name}}.py"
    condition: "{{ include_tests }}"

  - source: "{{node_name}}/README.md.j2"
    destination: "{{node_name}}/README.md"

# Post-generation hooks
hooks:
  post_generate:
    - command: "ruff format {{node_name}}/"
      description: "Format generated code"
    - command: "ruff check {{node_name}}/ --fix"
      description: "Fix linting issues"
```

---

## Template Content Examples

### Node Template (Python)

```python
# templates/node/device/{{node_name}}/{{node_name}}.py.j2
"""{{ node_description }}

This module implements a MADSci node for {{ node_name }}.

Generated by: madsci new node --template device
Template version: {{ template_version }}
"""

from madsci.node_module import ActionHandler, RestNode, ActionRequest, ActionResult
from madsci.common.types.node_types import NodeStatus

from .config import {{ node_name | pascal_case }}Config


class {{ node_name | pascal_case }}(RestNode):
    """{{ node_description }}"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config: {{ node_name | pascal_case }}Config = self.config

        # TODO: Initialize your device connection here
        self._device = None

{% if 'initialize' in actions %}
    @ActionHandler(
        description="Initialize the device",
    )
    def initialize(self, action: ActionRequest) -> ActionResult:
        """Initialize the device for operation.

        This action should be called before any other device operations.
        """
        try:
            # TODO: Implement device initialization
            # self._device = DeviceDriver.connect(self.config.device_address)

            return ActionResult.succeeded(
                action=action,
                message="Device initialized successfully",
            )
        except Exception as e:
            return ActionResult.failed(
                action=action,
                message=f"Failed to initialize device: {e}",
            )

{% endif %}
{% if 'shutdown' in actions %}
    @ActionHandler(
        description="Shutdown the device",
    )
    def shutdown(self, action: ActionRequest) -> ActionResult:
        """Safely shutdown the device.

        This action should be called when done using the device.
        """
        try:
            # TODO: Implement device shutdown
            # if self._device:
            #     self._device.disconnect()
            #     self._device = None

            return ActionResult.succeeded(
                action=action,
                message="Device shutdown complete",
            )
        except Exception as e:
            return ActionResult.failed(
                action=action,
                message=f"Failed to shutdown device: {e}",
            )

{% endif %}
{% if 'status' in actions %}
    @ActionHandler(
        description="Get device status",
    )
    def status(self, action: ActionRequest) -> ActionResult:
        """Get current device status."""
        try:
            # TODO: Implement status check
            status_info = {
                "connected": self._device is not None,
                # Add more status fields as needed
            }

            return ActionResult.succeeded(
                action=action,
                message="Status retrieved",
                data=status_info,
            )
        except Exception as e:
            return ActionResult.failed(
                action=action,
                message=f"Failed to get status: {e}",
            )

{% endif %}
{% if 'reset' in actions %}
    @ActionHandler(
        description="Reset the device to its initial state",
    )
    def reset(self, action: ActionRequest) -> ActionResult:
        """Reset the device to its initial state."""
        try:
            # TODO: Implement device reset

            return ActionResult.succeeded(
                action=action,
                message="Device reset complete",
            )
        except Exception as e:
            return ActionResult.failed(
                action=action,
                message=f"Failed to reset device: {e}",
            )

{% endif %}
{% if 'calibrate' in actions %}
    @ActionHandler(
        description="Calibrate the device",
    )
    def calibrate(self, action: ActionRequest) -> ActionResult:
        """Calibrate the device."""
        try:
            # TODO: Implement device calibration

            return ActionResult.succeeded(
                action=action,
                message="Calibration complete",
            )
        except Exception as e:
            return ActionResult.failed(
                action=action,
                message=f"Calibration failed: {e}",
            )

{% endif %}

if __name__ == "__main__":
    node = {{ node_name | pascal_case }}()
    node.start_node()
```

### Node Config Template

```python
# templates/node/device/{{node_name}}/config.py.j2
"""Configuration for {{ node_name }}."""

from pydantic import Field
from madsci.node_module import RestNodeConfig


class {{ node_name | pascal_case }}Config(RestNodeConfig):
    """Configuration for {{ node_name | pascal_case }} node."""

    # Server configuration
    node_url: str = "http://localhost:{{ port }}/"

    # TODO: Add your device-specific configuration here
    # device_address: str = Field(
    #     default="192.168.1.100",
    #     description="IP address or hostname of the device"
    # )
    # device_timeout: float = Field(
    #     default=30.0,
    #     description="Timeout for device operations in seconds"
    # )
```

### Test Template

```python
# templates/node/device/{{node_name}}/tests/test_{{node_name}}.py.j2
"""Tests for {{ node_name }}."""

import pytest
from unittest.mock import MagicMock, patch

from madsci.common.types.action_types import ActionRequest, ActionStatus

from ..{{ node_name }} import {{ node_name | pascal_case }}
from ..config import {{ node_name | pascal_case }}Config


@pytest.fixture
def node():
    """Create a test node instance."""
    config = {{ node_name | pascal_case }}Config(
        node_url="http://localhost:{{ port }}/",
    )
    return {{ node_name | pascal_case }}(config=config)


@pytest.fixture
def action_request():
    """Create a test action request."""
    return ActionRequest(
        action_name="test_action",
    )


class Test{{ node_name | pascal_case }}:
    """Test cases for {{ node_name | pascal_case }}."""

{% if 'initialize' in actions %}
    def test_initialize_success(self, node, action_request):
        """Test successful initialization."""
        action_request.action_name = "initialize"
        result = node.initialize(action_request)

        assert result.status == ActionStatus.SUCCEEDED
        assert "initialized" in result.message.lower()

{% endif %}
{% if 'shutdown' in actions %}
    def test_shutdown_success(self, node, action_request):
        """Test successful shutdown."""
        action_request.action_name = "shutdown"
        result = node.shutdown(action_request)

        assert result.status == ActionStatus.SUCCEEDED

{% endif %}
{% if 'status' in actions %}
    def test_status_returns_data(self, node, action_request):
        """Test status returns expected data."""
        action_request.action_name = "status"
        result = node.status(action_request)

        assert result.status == ActionStatus.SUCCEEDED
        assert result.data is not None
        assert "connected" in result.data

{% endif %}
```

---

## Data Types

```python
# src/madsci_common/madsci/common/types/template_types.py
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union
from pydantic import Field
from madsci.common.types.base_types import MadsciBaseModel


class ParameterType(str, Enum):
    """Types of template parameters."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    CHOICE = "choice"
    MULTI_CHOICE = "multi_choice"
    PATH = "path"


class ParameterChoice(MadsciBaseModel):
    """A choice option for choice/multi_choice parameters."""
    value: str
    label: str
    description: Optional[str] = None
    default: bool = False


class TemplateParameter(MadsciBaseModel):
    """Definition of a template parameter."""
    name: str
    type: ParameterType
    description: str
    required: bool = True
    default: Optional[Any] = None

    # For string type
    pattern: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None

    # For numeric types
    min: Optional[Union[int, float]] = None
    max: Optional[Union[int, float]] = None

    # For choice types
    choices: Optional[list[ParameterChoice]] = None


class TemplateFile(MadsciBaseModel):
    """A file to be generated from template."""
    source: str  # Relative path to template file
    destination: str  # Output path (can use template variables)
    condition: Optional[str] = None  # Jinja2 condition for inclusion


class TemplateHook(MadsciBaseModel):
    """A hook to run after generation."""
    command: str
    description: Optional[str] = None
    working_directory: Optional[str] = None
    continue_on_error: bool = False


class TemplateManifest(MadsciBaseModel):
    """The template.yaml manifest file."""
    name: str
    version: str
    description: str
    category: str  # node, experiment, workflow, lab, workcell
    tags: list[str] = Field(default_factory=list)

    author: Optional[str] = None
    license: Optional[str] = None
    min_madsci_version: Optional[str] = None

    parameters: list[TemplateParameter] = Field(default_factory=list)
    files: list[TemplateFile] = Field(default_factory=list)

    hooks: Optional[dict[str, list[TemplateHook]]] = None


class GeneratedProject(MadsciBaseModel):
    """Result of template generation."""
    template_name: str
    template_version: str
    output_directory: Path
    files_created: list[Path]
    parameters_used: dict[str, Any]
    hooks_executed: list[str]
```

---

## Template Engine

```python
# src/madsci_common/madsci/common/templates/engine.py
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from madsci.common.types.template_types import (
    TemplateManifest,
    TemplateParameter,
    ParameterType,
    GeneratedProject,
)


def pascal_case(value: str) -> str:
    """Convert snake_case to PascalCase."""
    return "".join(word.capitalize() for word in value.split("_"))


def camel_case(value: str) -> str:
    """Convert snake_case to camelCase."""
    words = value.split("_")
    return words[0] + "".join(word.capitalize() for word in words[1:])


def kebab_case(value: str) -> str:
    """Convert snake_case to kebab-case."""
    return value.replace("_", "-")


class TemplateEngine:
    """Engine for rendering MADSci templates."""

    def __init__(self, template_dir: Path):
        self.template_dir = template_dir
        self.manifest = self._load_manifest()
        self._jinja_env = self._create_jinja_env()

    def _load_manifest(self) -> TemplateManifest:
        """Load template manifest from template.yaml."""
        manifest_path = self.template_dir / "template.yaml"
        if not manifest_path.exists():
            raise TemplateError(f"Template manifest not found: {manifest_path}")

        return TemplateManifest.from_yaml(manifest_path)

    def _create_jinja_env(self) -> Environment:
        """Create Jinja2 environment with custom filters."""
        env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        env.filters["pascal_case"] = pascal_case
        env.filters["camel_case"] = camel_case
        env.filters["kebab_case"] = kebab_case
        env.filters["upper"] = str.upper
        env.filters["lower"] = str.lower

        return env

    def validate_parameters(self, values: dict[str, Any]) -> list[str]:
        """Validate parameter values against manifest.

        Returns:
            List of validation error messages (empty if valid)
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
                if param.pattern and not re.match(param.pattern, value):
                    errors.append(
                        f"Parameter '{param.name}' does not match pattern: {param.pattern}"
                    )
                if param.min_length and len(value) < param.min_length:
                    errors.append(
                        f"Parameter '{param.name}' is too short (min: {param.min_length})"
                    )
                if param.max_length and len(value) > param.max_length:
                    errors.append(
                        f"Parameter '{param.name}' is too long (max: {param.max_length})"
                    )

            elif param.type in (ParameterType.INTEGER, ParameterType.FLOAT):
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
                valid_values = [c.value for c in param.choices or []]
                for v in value:
                    if v not in valid_values:
                        errors.append(
                            f"Parameter '{param.name}' contains invalid value: {v}"
                        )

        return errors

    def get_default_values(self) -> dict[str, Any]:
        """Get default values for all parameters."""
        defaults = {}

        for param in self.manifest.parameters:
            if param.default is not None:
                defaults[param.name] = param.default
            elif param.type == ParameterType.MULTI_CHOICE:
                # Default to choices marked as default
                defaults[param.name] = [
                    c.value for c in (param.choices or []) if c.default
                ]

        return defaults

    def render(
        self,
        output_dir: Path,
        parameters: dict[str, Any],
        dry_run: bool = False,
    ) -> GeneratedProject:
        """Render template to output directory.

        Args:
            output_dir: Directory to write output files
            parameters: Parameter values
            dry_run: If True, don't write files, just return what would be created

        Returns:
            GeneratedProject with details of what was created
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

        files_created = []

        for file_spec in self.manifest.files:
            # Check condition
            if file_spec.condition:
                condition_template = self._jinja_env.from_string(file_spec.condition)
                if not condition_template.render(**values).strip().lower() in ("true", "1", "yes"):
                    continue

            # Render source path
            source_path_template = self._jinja_env.from_string(file_spec.source)
            source_path = source_path_template.render(**values)

            # Render destination path
            dest_path_template = self._jinja_env.from_string(file_spec.destination)
            dest_path = dest_path_template.render(**values)

            # Full paths
            source_full = self.template_dir / source_path
            dest_full = output_dir / dest_path

            if not dry_run:
                # Create parent directories
                dest_full.parent.mkdir(parents=True, exist_ok=True)

                # Render and write
                if source_full.suffix == ".j2":
                    # Jinja2 template
                    template = self._jinja_env.get_template(source_path)
                    content = template.render(**values)
                    dest_full.write_text(content)
                else:
                    # Static file - copy as-is
                    shutil.copy2(source_full, dest_full)

            files_created.append(dest_full)

        # Run post-generation hooks
        hooks_executed = []
        if not dry_run and self.manifest.hooks:
            for hook in self.manifest.hooks.get("post_generate", []):
                # Render command
                cmd_template = self._jinja_env.from_string(hook.command)
                cmd = cmd_template.render(**values)

                try:
                    subprocess.run(
                        cmd,
                        shell=True,
                        cwd=output_dir,
                        check=not hook.continue_on_error,
                        capture_output=True,
                    )
                    hooks_executed.append(cmd)
                except subprocess.CalledProcessError as e:
                    if not hook.continue_on_error:
                        raise TemplateHookError(f"Hook failed: {cmd}\n{e.stderr}")

        return GeneratedProject(
            template_name=self.manifest.name,
            template_version=self.manifest.version,
            output_directory=output_dir,
            files_created=files_created,
            parameters_used=values,
            hooks_executed=hooks_executed,
        )


class TemplateError(Exception):
    """Base exception for template errors."""
    pass


class TemplateValidationError(TemplateError):
    """Validation errors for template parameters."""
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"Validation errors: {errors}")


class TemplateHookError(TemplateError):
    """Error running template hook."""
    pass
```

---

## Template Registry

```python
# src/madsci_common/madsci/common/templates/registry.py
import importlib.resources
from pathlib import Path
from typing import Optional

from madsci.common.types.template_types import TemplateManifest
from .engine import TemplateEngine


class TemplateRegistry:
    """Registry for discovering and loading templates."""

    def __init__(
        self,
        user_template_dir: Optional[Path] = None,
    ):
        self.user_template_dir = user_template_dir or self._default_user_dir()
        self._cache: dict[str, TemplateManifest] = {}

    @staticmethod
    def _default_user_dir() -> Path:
        """Get default user template directory."""
        return Path.home() / ".madsci" / "templates"

    def _bundled_template_dir(self) -> Path:
        """Get bundled template directory from package."""
        # Templates are bundled in madsci_common package
        with importlib.resources.as_file(
            importlib.resources.files("madsci.common") / "templates"
        ) as path:
            return path

    def list_templates(
        self,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> list[dict]:
        """List available templates.

        Args:
            category: Filter by category (node, experiment, etc.)
            tags: Filter by tags

        Returns:
            List of template info dictionaries
        """
        templates = []

        # Scan bundled templates
        bundled_dir = self._bundled_template_dir()
        if bundled_dir.exists():
            templates.extend(self._scan_directory(bundled_dir, "bundled"))

        # Scan user templates
        if self.user_template_dir.exists():
            templates.extend(self._scan_directory(self.user_template_dir, "user"))

        # Apply filters
        if category:
            templates = [t for t in templates if t["category"] == category]

        if tags:
            templates = [
                t for t in templates
                if any(tag in t["tags"] for tag in tags)
            ]

        return templates

    def _scan_directory(self, base_dir: Path, source: str) -> list[dict]:
        """Scan a directory for templates."""
        templates = []

        for category_dir in base_dir.iterdir():
            if not category_dir.is_dir():
                continue

            for template_dir in category_dir.iterdir():
                if not template_dir.is_dir():
                    continue

                manifest_path = template_dir / "template.yaml"
                if not manifest_path.exists():
                    continue

                try:
                    manifest = TemplateManifest.from_yaml(manifest_path)
                    templates.append({
                        "id": f"{category_dir.name}/{template_dir.name}",
                        "name": manifest.name,
                        "version": manifest.version,
                        "description": manifest.description,
                        "category": manifest.category,
                        "tags": manifest.tags,
                        "source": source,
                        "path": template_dir,
                    })
                except Exception:
                    # Skip invalid templates
                    pass

        return templates

    def get_template(
        self,
        template_id: str,
    ) -> TemplateEngine:
        """Get a template engine by ID.

        Args:
            template_id: Template identifier (e.g., "node/device")

        Returns:
            TemplateEngine for the template
        """
        # Parse template ID
        parts = template_id.split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid template ID: {template_id}")

        category, name = parts

        # Check user templates first
        user_path = self.user_template_dir / category / name
        if user_path.exists():
            return TemplateEngine(user_path)

        # Check bundled templates
        bundled_path = self._bundled_template_dir() / category / name
        if bundled_path.exists():
            return TemplateEngine(bundled_path)

        raise TemplateNotFoundError(f"Template not found: {template_id}")

    def install_template(
        self,
        source: str,
        name: Optional[str] = None,
    ) -> Path:
        """Install a template from a source.

        Args:
            source: Path to template directory or git URL
            name: Optional name override

        Returns:
            Path to installed template
        """
        # TODO: Implement template installation from:
        # - Local directory
        # - Git repository
        # - Archive file
        pass


class TemplateNotFoundError(Exception):
    """Template not found in registry."""
    pass
```

---

## CLI Integration

See CLI design document for full command specifications.

```python
# src/madsci_client/madsci/client/cli/commands/new.py
import click
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table

from madsci.common.templates import TemplateRegistry, TemplateEngine
from madsci.common.types.template_types import ParameterType

console = Console()


@click.group()
def new():
    """Create new MADSci components from templates."""
    pass


@new.command()
@click.argument("directory", required=False, type=click.Path())
@click.option("--name", help="Node name")
@click.option("--template", "-t", help="Template to use")
@click.option("--no-interactive", is_flag=True, help="Skip prompts")
@click.pass_context
def node(ctx, directory, name, template, no_interactive):
    """Create a new node from template."""
    registry = TemplateRegistry()

    # List available node templates if not specified
    if not template:
        templates = registry.list_templates(category="node")

        if no_interactive:
            template = "node/basic"
        else:
            console.print("\nAvailable node templates:\n")
            table = Table(show_header=True)
            table.add_column("ID")
            table.add_column("Name")
            table.add_column("Description")

            for t in templates:
                table.add_row(t["id"], t["name"], t["description"])

            console.print(table)
            console.print()

            template = Prompt.ask(
                "Select template",
                default="node/device",
            )

    # Load template
    engine = registry.get_template(template)

    # Collect parameters
    if no_interactive:
        # Use defaults and provided options
        params = engine.get_default_values()
        if name:
            params["node_name"] = name
    else:
        params = collect_parameters_interactive(engine)

    # Determine output directory
    if directory:
        output_dir = Path(directory)
    else:
        output_dir = Path.cwd()

    # Preview
    if not no_interactive:
        console.print("\n[bold]Preview:[/bold]")
        result = engine.render(output_dir, params, dry_run=True)

        for file_path in result.files_created:
            console.print(f"  • {file_path.relative_to(output_dir)}")

        if not Confirm.ask("\nCreate these files?", default=True):
            console.print("Cancelled.")
            return

    # Generate
    result = engine.render(output_dir, params)

    console.print(f"\n[green]✓[/green] Created {len(result.files_created)} files\n")

    for file_path in result.files_created:
        console.print(f"  • {file_path.relative_to(output_dir)}")

    console.print("\n[bold]Next steps:[/bold]")
    console.print(f"  1. cd {params.get('node_name', 'your_node')}")
    console.print("  2. Edit the generated files to implement your logic")
    console.print(f"  3. python {params.get('node_name', 'your_node')}.py")


def collect_parameters_interactive(engine: TemplateEngine) -> dict:
    """Collect parameter values interactively."""
    params = {}

    for param in engine.manifest.parameters:
        if param.type == ParameterType.STRING:
            value = Prompt.ask(
                param.description,
                default=str(param.default) if param.default else None,
            )
            params[param.name] = value

        elif param.type == ParameterType.INTEGER:
            value = Prompt.ask(
                param.description,
                default=str(param.default) if param.default else None,
            )
            params[param.name] = int(value)

        elif param.type == ParameterType.BOOLEAN:
            value = Confirm.ask(
                param.description,
                default=param.default if param.default is not None else False,
            )
            params[param.name] = value

        elif param.type == ParameterType.CHOICE:
            console.print(f"\n{param.description}:")
            for i, choice in enumerate(param.choices or [], 1):
                marker = "●" if choice.value == param.default else "○"
                console.print(f"  {marker} {i}. {choice.label}")
                if choice.description:
                    console.print(f"       {choice.description}")

            default_idx = next(
                (i for i, c in enumerate(param.choices or [], 1)
                 if c.value == param.default),
                1
            )
            idx = Prompt.ask("Select", default=str(default_idx))
            params[param.name] = param.choices[int(idx) - 1].value

        elif param.type == ParameterType.MULTI_CHOICE:
            console.print(f"\n{param.description}:")
            selected = []
            for choice in param.choices or []:
                if Confirm.ask(f"  Include {choice.label}?", default=choice.default):
                    selected.append(choice.value)
            params[param.name] = selected

    return params
```

---

## Bundled Templates

### Module Templates

Complete module repositories with node, interface(s), types, tests, and documentation.

| ID | Name | Description | Interface Pattern |
|----|------|-------------|-------------------|
| `module/basic` | Basic Module | Minimal module with one action | Generic |
| `module/device` | Device Module | Standard device lifecycle (init, shutdown, status) | Generic |
| `module/instrument` | Instrument Module | Measurement device with calibration | Generic |
| `module/liquid_handler` | Liquid Handler Module | Pipetting operations | Serial/Socket |
| `module/robot_arm` | Robot Arm Module | Pick and place operations | Socket/SDK |
| `module/camera` | Camera Module | Image capture and analysis | SDK |

**Generated Module Structure:**
```
my_device_module/
├── src/
│   ├── my_device_rest_node.py       # MADSci REST node server
│   ├── my_device_interface.py       # Real hardware interface
│   ├── my_device_fake_interface.py  # Fake interface for testing
│   └── my_device_types.py           # Config, models, types
├── tests/
│   ├── test_my_device_node.py       # Node tests (using fake interface)
│   └── test_my_device_interface.py  # Interface unit tests
├── Dockerfile
├── pyproject.toml
└── README.md
```

### Interface Templates

Add interface variants to existing modules.

| ID | Name | Description |
|----|------|-------------|
| `interface/fake` | Fake Interface | Simulated behavior for testing |
| `interface/sim` | Simulation Interface | Connects to physics simulation (Omniverse) |
| `interface/mock` | Mock Interface | Pytest mock-based interface for unit tests |

### Node Templates

Node-only templates for when an interface already exists (rare use case).

| ID | Name | Description |
|----|------|-------------|
| `node/basic` | Basic Node | Minimal REST node wrapping existing interface |

**Note:** Most users should use `module/*` templates instead, which include the complete package.

### Experiment Templates

| ID | Name | Description |
|----|------|-------------|
| `experiment/script` | Script Experiment | Simple run-once experiment |
| `experiment/notebook` | Notebook Experiment | Jupyter-friendly experiment |
| `experiment/tui` | TUI Experiment | Interactive terminal experiment |
| `experiment/node` | Node Experiment | REST API server mode |

### Workflow Templates

| ID | Name | Description |
|----|------|-------------|
| `workflow/basic` | Basic Workflow | Single-step workflow |
| `workflow/multi_step` | Multi-Step Workflow | Sequential steps |
| `workflow/parallel` | Parallel Workflow | Concurrent execution |

### Lab Templates

| ID | Name | Description |
|----|------|-------------|
| `lab/minimal` | Minimal Lab | Single node, no Docker |
| `lab/standard` | Standard Lab | Full stack with Docker |
| `lab/distributed` | Distributed Lab | Multi-host deployment |

---

## Template Validation

Templates are validated as part of CI:

```python
# tests/templates/test_template_validation.py
import pytest
from pathlib import Path
import tempfile

from madsci.common.templates import TemplateRegistry, TemplateEngine


@pytest.fixture
def registry():
    return TemplateRegistry()


def test_all_templates_have_valid_manifests(registry):
    """All bundled templates should have valid manifests."""
    templates = registry.list_templates()

    for template in templates:
        engine = registry.get_template(template["id"])
        assert engine.manifest is not None
        assert engine.manifest.name
        assert engine.manifest.version


@pytest.mark.parametrize("template_id", [
    "node/basic",
    "node/device",
    "experiment/script",
    "workflow/basic",
])
def test_template_generates_valid_output(registry, template_id):
    """Templates should generate valid, linting-passing code."""
    engine = registry.get_template(template_id)

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        # Use default values
        params = engine.get_default_values()

        # Generate
        result = engine.render(output_dir, params)

        # Check files were created
        assert len(result.files_created) > 0

        # Check Python files are valid syntax
        for file_path in result.files_created:
            if file_path.suffix == ".py":
                compile(file_path.read_text(), file_path, "exec")
```

---

## Dependencies

```toml
# Add to madsci_common/pyproject.toml
dependencies = [
    # ... existing ...
    "jinja2>=3.1.0",  # Template rendering
]
```

---

## Design Decisions

The following decisions have been made based on review:

1. **Template versioning**: Use semantic versioning for the template schema. Each template stores its schema version in `template.yaml` (e.g., `schema_version: "1.0"`). When the schema changes:
   - Minor version bump: New optional fields, backward compatible
   - Major version bump: Breaking changes, old templates need migration
   - The template engine validates schema version and provides clear upgrade guidance

2. **Template inheritance**: **Deferred to later.** While template inheritance would be useful, the added complexity is not justified for the initial implementation. Templates can be self-contained with copy-paste of common patterns. Inheritance can be added in a future version if there's demand.

3. **Remote templates**: **Yes, support git repos.** Users should be able to install templates from git repositories:
   ```bash
   madsci template install https://github.com/org/madsci-templates.git
   madsci template install git@github.com:org/madsci-templates.git --path node/custom
   ```
   Templates will be cloned/downloaded to `~/.madsci/templates/` and registered in the template registry.

4. **Template testing**: See analysis below.

5. **IDE integration**: **Out of scope** for initial implementation. Generating VS Code configuration files (tasks.json, launch.json) could be added as an optional post-generation hook in specific templates later.

---

## Template Testing Analysis

### What "Template Testing" Means

Templates could include their own tests in two ways:

**Option A: Tests for the template itself**
- Verify the template renders correctly with various parameter combinations
- Validate that generated code passes linting
- Check that generated code compiles/parses successfully

**Option B: Tests bundled into generated output**
- The template generates test files alongside the main code
- Users get pre-written tests as part of scaffolding
- Tests serve as examples of how to test the generated component

### Pros and Cons

#### Option A: Template Self-Tests

| Pros | Cons |
|------|------|
| Catches template bugs before users see them | Adds maintenance burden for template authors |
| Can run in CI to prevent template regressions | May slow down template development iteration |
| Increases confidence in template quality | Requires test infrastructure for templates |
| Documents expected template behavior | Tests may become stale if not maintained |

#### Option B: Generated Tests in Output

| Pros | Cons |
|------|------|
| Users get working tests immediately | Users may not want/need tests |
| Tests demonstrate how to test the component | Increases generated code complexity |
| Encourages testing best practices | Tests may not match user's preferred style |
| Tests can verify the generated code works | May conflict with existing test setups |

### Recommendation

**Do both, with different scopes:**

1. **Template validation tests (in CI)**: The MADSci CI pipeline already validates templates by:
   - Rendering with default parameters
   - Checking generated code parses/compiles
   - Running ruff on generated output
   This is implemented in `tests/templates/test_template_validation.py`.

2. **Optional generated tests**: Templates MAY include test file generation, controlled by an `include_tests` parameter (default: `true`). The `condition` feature in template manifests already supports this:
   ```yaml
   files:
     - source: "tests/test_{{node_name}}.py.j2"
       destination: "{{node_name}}/tests/test_{{node_name}}.py"
       condition: "{{ include_tests }}"
   ```

**Decision**: Keep the current approach. Template validation happens in CI. Generated tests are optional and controlled by the `include_tests` parameter.
