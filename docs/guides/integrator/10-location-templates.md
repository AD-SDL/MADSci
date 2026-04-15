# Location Ownership and Templates

**Audience**: Equipment Integrator
**Prerequisites**: [Wiring the Node](./05-wiring-the-node.md)
**Time**: ~25 minutes

## Overview

Many laboratory instruments interact with specific physical locations -- deck slots on a liquid handler, sample positions on a plate reader, or waypoints for a robot arm. MADSci uses a **layered ownership model** to manage these locations:

1. **Node-managed locations** -- intrinsic to a node's hardware, auto-created on startup, lifecycle tied to the node.
2. **Training** -- cross-node representation additions that teach one node how to access another node's locations.
3. **Lab-managed locations** -- defined in a reconcilable lab config file, lifecycle managed by the operator.

Each node needs its own "view" of a location (a **representation**): the robot arm needs joint angles and gripper configuration, while the liquid handler needs a deck slot number and plate type. **Representation templates** define the schema and defaults for these views.

## Location Ownership Model

Every location has a `managed_by` field set to one of two values from the `LocationManagement` enum:

| Value | Meaning | Lifecycle |
|-------|---------|-----------|
| `LocationManagement.NODE` | Created by a node via `intrinsic_locations` | Tied to node startup; auto-created idempotently |
| `LocationManagement.LAB` | Created by lab config or API | Managed by operator/integrator |

Locations also carry an optional `owner` field (`OwnershipInfo`) for provenance tracking. Node-managed locations automatically set `owner.node_id` to the owning node's ID.

## Node-Intrinsic Locations

Nodes declare locations that are intrinsic to their hardware using the `intrinsic_locations` class variable. Each entry is a `NodeIntrinsicLocationDefinition`. On startup, the node's `intrinsic_location_handler()` registers these with the Location Manager via the idempotent `POST /location/init` endpoint.

Location names are **automatically prefixed** with `{node_name}.` to ensure uniqueness across node instances. For example, `location_name="deck_1"` on a node named `liquidhandler_1` becomes `liquidhandler_1.deck_1`.

### NodeIntrinsicLocationDefinition Fields

| Field | Type | Description |
|-------|------|-------------|
| `location_name` | `str` | Suffix for the name (auto-prefixed with `{node_name}.`) |
| `description` | `str` (optional) | Human-readable description |
| `representation_template_name` | `str` | Name of the representation template to use |
| `representation_overrides` | `dict` | Per-location overrides merged with template defaults |
| `resource_template_name` | `str` (optional) | Resource template for creating a resource at this location |
| `resource_template_overrides` | `dict` (optional) | Overrides for the resource template |
| `allow_transfers` | `bool` | Whether this location participates in transfer planning (default `True`) |
| `tags` | `list[str]` (optional) | Tags for categorization |

### Complete Example

```python
from typing import ClassVar

from madsci.common.types.node_types import (
    NodeIntrinsicLocationDefinition,
    NodeRepresentationTemplateDefinition,
    RestNodeConfig,
)
from madsci.node_module.rest_node_module import RestNode


class LiquidHandlerNode(RestNode):
    config: RestNodeConfig = RestNodeConfig()
    config_model = RestNodeConfig

    # Representation templates -- registered by template_handler()
    location_representation_templates: ClassVar[
        list[NodeRepresentationTemplateDefinition]
    ] = [
        NodeRepresentationTemplateDefinition(
            template_name="lh_deck_repr",
            default_values={"deck_type": "standard", "max_plates": 1},
            schema_def={
                "type": "object",
                "properties": {
                    "deck_position": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Deck slot number on the liquid handler",
                    },
                    "deck_type": {
                        "type": "string",
                        "enum": ["standard", "deep_well", "pcr"],
                    },
                },
                "required": ["deck_position"],
            },
            required_overrides=["deck_position"],
            tags=["liquid_handler", "deck"],
            version="1.1.0",
            description="Liquid handler deck slot representation",
        ),
    ]

    # Intrinsic locations -- auto-created on startup with '{node_name}.' prefix
    intrinsic_locations: ClassVar[list[NodeIntrinsicLocationDefinition]] = [
        NodeIntrinsicLocationDefinition(
            location_name=f"deck_{i}",
            description=f"Deck slot {i}",
            representation_template_name="lh_deck_repr",
            representation_overrides={"deck_position": i},
            resource_template_name="liquid_handler_deck_slot",
            allow_transfers=True,
        )
        for i in range(1, 5)
    ]
```

When this node starts as `liquidhandler_1`, four locations are created:
- `liquidhandler_1.deck_1`
- `liquidhandler_1.deck_2`
- `liquidhandler_1.deck_3`
- `liquidhandler_1.deck_4`

Each is marked `managed_by=NODE` with `owner.node_id` set to the liquid handler's node ID.

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

```python
class RobotArmNode(RestNode):
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
                    },
                    "max_payload": {
                        "type": "number",
                        "minimum": 0,
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

```python
from madsci.common.types.location_types import LocationTemplate

# Location templates can be defined in code, via the API, or in a lab config file.
template = LocationTemplate(
    template_name="lh_accessible_deck_slot",
    description="Deck slot accessible by both liquid handler and robot arm",
    representation_templates={
        "deck_controller": "lh_deck_repr",
        "transfer_arm": "robotarm_deck_access",
    },
    resource_template_name="location_container",
    tags=["liquid_handler", "deck", "accessible"],
    version="1.0.0",
)
```

The `representation_templates` mapping uses abstract role names as keys:

- `"deck_controller"` -- the liquid handler that owns this deck slot
- `"transfer_arm"` -- the robot arm that can access this slot

When a location is instantiated from this template, the operator provides **node bindings** that map roles to concrete node instances (e.g., `deck_controller: liquidhandler_1`, `transfer_arm: robotarm_1`).

## Training

Training teaches a node how to access locations it does not own. For example, a robot arm needs to know the coordinates for reaching a liquid handler's deck slot, but the deck slot is owned by the liquid handler.

Training entries are defined in the lab config file (`locations.yaml`) and applied during reconciliation:

```yaml
training:
  - location_name: liquidhandler_1.deck_1
    node_name: robotarm_1
    representation_template_name: robotarm_deck_access
    overrides:
      position: [10, 15, 5]

  - location_name: liquidhandler_1.deck_3
    node_name: robotarm_1
    representation_template_name: robotarm_deck_access
    overrides:
      position: [20, 15, 5]
```

Each `RepresentationTrainingEntry` has the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `location_name` | `str` | Name of the existing location to add a representation to |
| `node_name` | `str` | Name of the node providing the representation |
| `representation_template_name` | `str` (optional) | Representation template to use for defaults/schema |
| `overrides` | `dict` | Representation values merged with template defaults |

When training is applied, the specified node's representation is added to the location. If a `representation_template_name` is provided, its defaults are merged with the `overrides`; otherwise, the overrides are used as-is.

Training is idempotent -- applying the same entry twice is safe.

## Lab Config File

The `LabLocationConfig` format provides a reconcilable living document for lab-level location management. The Location Manager reads this file (default: `locations.yaml`) on each reconciliation cycle and merges its contents with the live database using desired-state semantics.

### Configuration

Set the file path via the `lab_config_file` setting on `LocationManagerSettings`:

```yaml
# In settings.yaml
location_lab_config_file: locations.yaml
```

Or via environment variable:

```bash
export LOCATION_LAB_CONFIG_FILE=locations.yaml
```

The file is discovered using walk-up search from the current working directory.

### File Format

```yaml
# locations.yaml — LabLocationConfig format

# Lab-level representation templates (optional)
representation_templates:
  - template_name: my_custom_repr
    default_values: { slot_index: 0 }
    version: "1.0.0"

# Reusable location blueprints (optional)
location_templates:
  - template_name: accessible_deck_slot
    representation_templates:
      deck_controller: lh_deck_repr
      transfer_arm: robotarm_deck_access
    version: "1.0.0"

# Cross-node representation additions
training:
  - location_name: liquidhandler_1.deck_1
    node_name: robotarm_1
    representation_template_name: robotarm_deck_access
    overrides:
      position: [10, 15, 5]

# Lab-managed locations (not owned by any node)
locations:
  - location_name: storage_rack
    description: "High-capacity storage accessible only by robot arm"
    representations:
      robotarm_1:
        gripper_config: wide
        max_payload: 10.0
        position: [30, 25, 10]
    resource_template_name: location_container
```

### Reconciliation Semantics

The lab config file uses **desired-state-with-warnings** semantics:

- **Representation templates**: Synced via init (get-or-create, version-update).
- **Location templates**: Synced via init (get-or-create, version-update).
- **Locations**: Get-or-create. Existing locations are not overwritten.
- **Training**: Applied idempotently. If the target location does not yet exist (e.g., the node has not started), the entry is skipped with a warning and retried on the next cycle.

The file is cached by mtime -- the Location Manager only re-reads it when the file modification time changes.

### Reconciliation Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/reconcile` | Manually trigger a reconciliation cycle |
| `GET` | `/reconciliation/status` | Get status of the last reconciliation cycle |

Background reconciliation runs automatically at a configurable interval when `reconciliation_enabled` is `True` (default).

## Template Registration

The `template_handler()` method on `AbstractNode` automatically registers all representation templates with the Location Manager at startup. The `intrinsic_location_handler()` then registers intrinsic locations. Both run before `startup_handler()`, so your templates and locations are available by the time your node initializes.

Registration is **idempotent**: if the template or location already exists with the same version/name, it is not re-created. If a template's version number has increased, the template is updated.

Errors are handled **per-item** and are non-blocking -- a single failed registration (e.g., because the Location Manager is temporarily unreachable) does not prevent the node from starting. Failed registrations are logged as warnings.

You do not need to call `template_handler()` or `intrinsic_location_handler()` yourself; the framework invokes them automatically.

## NodeInfo Discovery

When a node starts, it populates its `NodeInfo` with the declared templates and intrinsic locations. Consumers (other services, the dashboard, scripts) can discover these by querying the `/info` endpoint:

```bash
curl http://localhost:2002/info | jq '.intrinsic_locations'
curl http://localhost:2002/info | jq '.location_representation_templates'
```

The `NodeInfo` model exposes:

- `intrinsic_locations` -- list of `NodeIntrinsicLocationDefinition`
- `location_representation_templates` -- list of `NodeRepresentationTemplateDefinition`

## API Endpoints

### Location Init (Idempotent)

```
POST /location/init
```

Get-or-create a location. If a location with the given name exists, return it unchanged. If it does not exist, create it with lazy resource resolution. Used by nodes to register intrinsic locations.

### Location Filtering

```
GET /locations?managed_by=node
GET /locations?managed_by=lab
```

Filter locations by management type. Useful for dashboards and debugging.

### Health Endpoint

The health endpoint (`GET /health`) includes location management counts:

- `num_node_managed_locations` -- number of locations with `managed_by=NODE`
- `num_lab_managed_locations` -- number of locations with `managed_by=LAB`
- `last_reconciliation_at` -- timestamp of the last reconciliation cycle

## Transfer Planning

Representations enable the Location Manager to plan transfers between locations. When a robot arm has a representation for two deck slots, the transfer planner knows the arm can move items between them.

Training is what makes transfers possible across node boundaries. Without training the robot arm on the liquid handler's deck slots, the transfer planner would not know the arm can reach those locations.

The transfer graph is automatically rebuilt when:
- A new location is created (via API or node startup)
- Lab config reconciliation creates or updates locations
- Training is applied

## Programmatic Usage

The `LocationClient` provides methods for working with the ownership model programmatically.

### Init Locations

```python
from madsci.client.location_client import LocationClient
from madsci.common.types.location_types import LocationManagement

client = LocationClient(location_server_url="http://localhost:8006")

# Idempotent location init (used internally by nodes)
location = client.init_location(
    location_name="mynode.slot_1",
    representations={"mynode": {"slot_index": 1}},
    managed_by=LocationManagement.NODE,
    resource_template_name="plate_nest",
)
```

### Query by Management Type

```python
# Get all node-managed locations
node_locations = client.get_locations(managed_by="node")

# Get all lab-managed locations
lab_locations = client.get_locations(managed_by="lab")
```

### Check Reconciliation Status

```python
import httpx

response = httpx.get("http://localhost:8006/reconciliation/status")
status = response.json()
print(status["last_reconciliation_at"])
print(status["reconciliation_enabled"])
```

## Best Practices

**Declare intrinsic locations on the node class.** If a location is physically part of your hardware (deck slots, sample positions), declare it in `intrinsic_locations`. This ensures locations are created automatically on startup and tied to the node's lifecycle.

**Use training for cross-node access.** When a robot arm needs to access a liquid handler's deck, define training entries in `locations.yaml` rather than hard-coding representations on the liquid handler's intrinsic locations.

**Use `schema_def` for structured representations.** JSON Schema enables the dashboard to render typed form fields and validates data on the server side.

**Put location-specific values in `required_overrides`.** Fields like `position` or `deck_position` vary per physical location and should not have defaults.

**Version your templates.** Use semantic versioning for templates. The init methods perform version-aware updates: if the registered template has an older version, it is updated; if it has the same or newer version, it is left unchanged.

**Keep representation template names globally unique.** Use a prefix based on your node type (e.g., `robotarm_`, `lh_`) to avoid collisions.

**Use lab-managed locations for shared infrastructure.** Storage racks, waste bins, and other locations not intrinsic to any single node belong in the lab config file.

## What's Next?

- [Testing Strategies](./06-testing-strategies.md) -- test nodes that use intrinsic locations
- [Example Lab README](../../../examples/example_lab/README.md) -- see the ownership model in action
- [Node Development Quick Reference](../node_development.md) -- concise template reference
