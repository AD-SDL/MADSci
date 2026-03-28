# Location Templates

**Audience**: Equipment Integrator
**Prerequisites**: [Wiring the Node](./05-wiring-the-node.md)
**Time**: ~20 minutes

## Overview

Many laboratory instruments interact with specific physical locations -- deck slots on a liquid handler, sample positions on a plate reader, or waypoints for a robot arm. Each node needs its own "view" of a location: the robot arm needs joint angles and gripper configuration, while the liquid handler needs a deck slot number and plate type.

**Location templates** let you define these per-node facts declaratively on your node class. The framework registers them with the Location Manager at startup, and operators can then create concrete locations by combining templates, binding them to specific node instances, and providing location-specific overrides.

Consider a robot arm that transfers plates between instruments. For every reachable deck slot, the arm needs to know:

- The joint angles or XYZ coordinates to reach that slot
- Which gripper configuration to use (standard, wide, vacuum)
- The maximum payload weight

Rather than hard-coding this data for each location, you define a **representation template** with a JSON Schema, sensible defaults, and a list of fields that must be overridden per-location. Operators then instantiate locations from these templates, supplying only the location-specific values (like joint angles).

The template system has three layers:

1. **Representation templates** -- a single node type's view of a location (e.g., "robotarm_deck_access")
2. **Location templates** -- compose multiple representation templates via abstract role bindings (e.g., "lh_accessible_deck_slot" = liquid handler + robot arm)
3. **Seed files** -- pre-populate the Location Manager with concrete locations on first startup

## Representation Templates

Define `location_representation_templates` as a `ClassVar` on your node class. Each entry is a `NodeRepresentationTemplateDefinition` with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `template_name` | `str` | Unique name for this template (e.g., `"robotarm_deck_access"`) |
| `default_values` | `dict` | Default field values merged with overrides at instantiation |
| `schema_def` | `dict` (optional) | JSON Schema for validating representation data |
| `required_overrides` | `list[str]` (optional) | Fields that must be provided per-location |
| `tags` | `list[str]` (optional) | Tags for discovery and filtering |
| `version` | `str` | Semantic version of this template (default `"1.0.0"`) |
| `description` | `str` (optional) | Human-readable description |

### Complete Example

```python
from typing import ClassVar
from madsci.common.types.node_types import (
    NodeRepresentationTemplateDefinition,
    RestNodeConfig,
)
from madsci.node_module.rest_node_module import RestNode


class RobotArmNode(RestNode):
    config: RestNodeConfig = RestNodeConfig()
    config_model = RestNodeConfig

    location_representation_templates: ClassVar[
        list[NodeRepresentationTemplateDefinition]
    ] = [
        NodeRepresentationTemplateDefinition(
            template_name="robotarm_deck_access",
            default_values={
                "gripper_config": "standard",
                "max_payload": 2.0,
            },
            schema_def={
                "type": "object",
                "properties": {
                    "position": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 4,
                        "description": "Joint angles or XYZ(+rotation) for this location",
                    },
                    "gripper_config": {
                        "type": "string",
                        "enum": ["standard", "wide", "vacuum"],
                        "description": "Gripper configuration to use",
                    },
                    "max_payload": {
                        "type": "number",
                        "minimum": 0,
                        "description": "Maximum payload weight in kg",
                    },
                },
                "required": ["position"],
            },
            required_overrides=["position"],
            tags=["robot_arm", "deck"],
            version="1.1.0",
            description="Robot arm deck access with joint positions",
        ),
    ]
```

Key points:

- **`schema_def`** provides a JSON Schema that the Location Manager and dashboard use to validate data and render form fields. If omitted, representation data is freeform JSON.
- **`default_values`** are merged with overrides when a location is created. In this example, every location gets `gripper_config: "standard"` unless the operator overrides it.
- **`required_overrides`** lists fields that have no sensible default and must be supplied per-location. The `position` field varies for every physical location, so it is required.

## Location Templates

Location templates compose multiple representation templates into a reusable blueprint. They use **abstract role names** instead of concrete node instance names, so the same template works across different lab configurations.

Define `location_templates` as a `ClassVar` on your node class:

```python
from madsci.common.types.node_types import NodeLocationTemplateDefinition

class LiquidHandlerNode(RestNode):
    # ... representation templates defined above ...

    location_templates: ClassVar[list[NodeLocationTemplateDefinition]] = [
        NodeLocationTemplateDefinition(
            template_name="lh_accessible_deck_slot",
            description="Deck slot accessible by both liquid handler and robot arm",
            representation_templates={
                "deck_controller": "lh_deck_repr",
                "transfer_arm": "robotarm_deck_access",
            },
            resource_template_name="location_container",
            tags=["liquid_handler", "deck", "accessible"],
            version="1.0.0",
        ),
    ]
```

The `representation_templates` mapping uses abstract role names as keys:

- `"deck_controller"` -- the liquid handler that owns this deck slot
- `"transfer_arm"` -- the robot arm that can access this slot

When a location is instantiated from this template, the operator provides **node bindings** that map roles to concrete node instances (e.g., `deck_controller: liquidhandler_1`, `transfer_arm: robotarm_1`).

## Template Registration

The `template_handler()` method on `AbstractNode` automatically registers all templates with the Location Manager and Resource Manager at startup. It runs before `startup_handler()`, so your templates are available by the time your node initializes.

Registration is **idempotent**: if the template already exists with the same version, it is not re-created. If the version number has increased, the template is updated.

Errors are handled **per-template** and are non-blocking -- a single failed registration (e.g., because the Location Manager is temporarily unreachable) does not prevent the node from starting. Failed registrations are logged as warnings.

You do not need to call `template_handler()` yourself; the framework invokes it automatically.

## Seed Files

For labs with many pre-defined locations, you can supply a `locations.yaml` seed file that the Location Manager loads on first startup (when its database is empty). The seed file can define representation templates, location templates, and concrete locations in one place.

### Example `locations.yaml`

```yaml
# Representation templates (registered first)
representation_templates:
  - template_name: robotarm_deck_access
    description: "Robot arm access to a deck slot"
    default_values:
      gripper_config: standard
      max_payload: 2.0
    required_overrides:
      - position
    tags: [robot_arm, deck]
    version: "1.0.0"

  - template_name: lh_deck_repr
    description: "Liquid handler deck slot representation"
    default_values:
      deck_type: standard
      max_plates: 1
    required_overrides:
      - deck_position
    tags: [liquid_handler, deck]
    version: "1.0.0"

# Location templates (compose representation templates)
location_templates:
  - template_name: lh_accessible_deck_slot
    description: "Deck slot accessible by liquid handler and robot arm"
    resource_template_name: location_container
    representation_templates:
      deck_controller: lh_deck_repr
      transfer_arm: robotarm_deck_access
    tags: [liquid_handler, deck, accessible]
    version: "1.0.0"

# Concrete locations (reference templates with node bindings)
locations:
  - location_name: liquidhandler_1.deck_1
    template_name: lh_accessible_deck_slot
    description: "Deck 1 on liquidhandler_1"
    node_bindings:
      deck_controller: liquidhandler_1
      transfer_arm: robotarm_1
    representation_overrides:
      deck_controller:
        deck_position: 1
      transfer_arm:
        position: [10, 15, 5]

  # Inline locations (no template) are also supported
  - location_name: storage_rack
    description: "Storage rack accessible by robot arm"
    representations:
      robotarm_1:
        gripper_config: wide
        position: [30, 25, 10]
    resource_template_name: location_container
```

Configure the seed file path in `settings.yaml`:

```yaml
location_seed_locations_file: locations.yaml
```

The seed file is processed once when the Location Manager database is empty. After that, locations are managed through the API or dashboard.

## NodeInfo Discovery

When a node starts, it populates its `NodeInfo` with the declared templates. Consumers (other services, the dashboard, scripts) can discover a node's templates by querying the `/info` endpoint:

```bash
curl http://localhost:2002/info | jq '.location_representation_templates'
```

The `NodeInfo` model exposes two fields:

- `location_representation_templates` -- list of `NodeRepresentationTemplateDefinition`
- `location_templates` -- list of `NodeLocationTemplateDefinition`

This allows the dashboard and other tools to present template-aware forms without hard-coding knowledge of specific node types.

## Dashboard Usage

The MADSci dashboard provides a template-aware interface for creating and managing locations:

1. Navigate to the **Locations** tab in the dashboard
2. Click **Create Location from Template** to see available location templates
3. Select a template, provide node bindings (mapping roles to node instances), and fill in required overrides
4. The dashboard renders form fields based on the template's `schema_def`, with defaults pre-populated and required overrides highlighted
5. Submit to create the location with proper representations for each bound node

Existing locations display their template lineage (`location_template_name` and `node_bindings`) for traceability.

## Programmatic Usage

The `LocationClient` provides methods for working with templates programmatically.

### Register Templates

```python
from madsci.client.location_client import LocationClient

client = LocationClient(location_server_url="http://localhost:8006")

# Register a representation template (idempotent)
client.init_representation_template(
    template_name="robotarm_deck_access",
    default_values={"gripper_config": "standard", "max_payload": 2.0},
    schema_def={
        "type": "object",
        "properties": {
            "position": {"type": "array", "items": {"type": "number"}},
            "gripper_config": {"type": "string"},
        },
        "required": ["position"],
    },
    required_overrides=["position"],
    version="1.1.0",
    description="Robot arm deck access representation",
)

# Register a location template (idempotent)
client.init_location_template(
    template_name="lh_accessible_deck_slot",
    representation_templates={
        "deck_controller": "lh_deck_repr",
        "transfer_arm": "robotarm_deck_access",
    },
    resource_template_name="location_container",
    version="1.0.0",
    description="Deck slot accessible by liquid handler and robot arm",
)
```

### Create Locations from Templates

```python
# Create a concrete location from a template
location = client.create_location_from_template(
    location_name="liquidhandler_1.deck_1",
    template_name="lh_accessible_deck_slot",
    node_bindings={
        "deck_controller": "liquidhandler_1",
        "transfer_arm": "robotarm_1",
    },
    representation_overrides={
        "deck_controller": {"deck_position": 1},
        "transfer_arm": {"position": [10, 15, 5]},
    },
    description="Deck 1 on liquidhandler_1",
)
print(location.representations)
# {"liquidhandler_1": {"deck_type": "standard", "max_plates": 1, "deck_position": 1},
#  "robotarm_1": {"gripper_config": "standard", "max_payload": 2.0, "position": [10, 15, 5]}}
```

### Query Templates

```python
# List all registered representation templates
repr_templates = client.get_representation_templates()

# Get a specific template by name
template = client.get_representation_template("robotarm_deck_access")

# List all location templates
loc_templates = client.get_location_templates()
```

## Best Practices

**Use `schema_def` for structured representations.** JSON Schema enables the dashboard to render typed form fields (numbers, enums, arrays) and validates data on the server side. Without a schema, representations are freeform dictionaries that are harder to validate and display.

**Put location-specific values in `required_overrides`.** Fields like `position` or `deck_position` vary per physical location and should not have defaults. Marking them as required overrides ensures operators supply them when creating locations.

**Use `default_values` for configuration that rarely changes.** Gripper type, maximum payload, and similar settings are good candidates for defaults. Operators can still override them per-location when needed.

**Version your templates.** Use semantic versioning (`"1.0.0"`, `"1.1.0"`, etc.) for templates. The `init_*` methods perform version-aware updates: if the registered template has an older version, it is updated; if it has the same or newer version, it is left unchanged. This makes template evolution safe during rolling upgrades.

**Keep representation template names globally unique.** Template names are the primary identifier. Use a prefix based on your node type (e.g., `robotarm_`, `lh_`) to avoid collisions with templates from other node modules.

**Define templates on the node class, not in `startup_handler`.** The `template_handler()` runs before `startup_handler()`, so declarative `ClassVar` definitions are the recommended approach. This keeps template definitions visible in the class definition and ensures they are registered before any startup logic that might depend on them.

## What's Next?

- [Testing Strategies](./06-testing-strategies.md) -- test nodes that use location templates
- [Example Lab README](../../../examples/example_lab/README.md) -- see templates in action in the example lab
- [Node Development Quick Reference](../node_development.md) -- concise template reference
