# Tutorial 4: Your First Workcell

**Time to Complete**: ~45 minutes
**Prerequisites**: [Tutorial 3: Your First Experiment](03-first-experiment.md)
**Docker Required**: Recommended (but alternatives provided)

## What You'll Learn

In this tutorial, you'll:

1. Create a workcell with multiple nodes
2. Write workflows that coordinate actions across nodes
3. Start essential manager services (Workcell Manager, Event Manager)
4. Run workflows programmatically and via CLI
5. Monitor workflow execution

This is where MADSci's power really shines - coordinating multiple instruments!

## The Workcell Concept

A **workcell** is a collection of nodes that work together. It includes:

- **Nodes**: The instruments in your workcell
- **Workcell Manager**: Orchestrates workflows across nodes
- **Workflows**: Define multi-step protocols

```
┌─────────────────────────────────────────────────────────────────┐
│                         WORKCELL                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│    ┌──────────┐    ┌──────────┐    ┌──────────┐                 │
│    │  Node 1  │    │  Node 2  │    │  Node 3  │                 │
│    │ (Sensor) │    │ (Robot)  │    │ (Reader) │                 │
│    └────▲─────┘    └────▲─────┘    └────▲─────┘                 │
│         │               │               │                        │
│    ─────┴───────────────┴───────────────┴──────                 │
│                         │                                        │
│              ┌──────────┴──────────┐                            │
│              │   Workcell Manager  │                            │
│              │   (Orchestrator)    │                            │
│              └─────────────────────┘                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Step 1: Create a Second Node

Let's add a "robot arm" node to work with our temperature sensor:

```bash
cd madsci-tutorial
source .venv/bin/activate

# Create a simple robot arm module
madsci new module --name robot_arm
```

Follow the prompts, then edit `robot_arm_module/src/robot_arm_rest_node.py`:

```python
"""MADSci REST node for a simulated robot arm."""

from madsci.node_module import RestNode, action
from robot_arm_types import RobotArmNodeConfig
import time


class RobotArmNode(RestNode):
    """A simulated robot arm for material handling."""

    config: RobotArmNodeConfig = RobotArmNodeConfig()
    config_model = RobotArmNodeConfig

    def __init__(self):
        super().__init__()
        self.current_position = "home"
        self.holding = None

    def startup_handler(self) -> None:
        """Initialize robot arm."""
        self.logger.info("Robot arm initialized at home position")

    @action
    def move_to(self, location: str) -> dict:
        """Move the arm to a location.

        Args:
            location: Target location name (e.g., 'sensor', 'analyzer', 'home')

        Returns:
            Status of the move operation.
        """
        self.logger.info(f"Moving from {self.current_position} to {location}")
        time.sleep(0.5)  # Simulate movement time
        self.current_position = location
        return {"status": "completed", "position": location}

    @action
    def pick(self, item: str) -> dict:
        """Pick up an item at current location.

        Args:
            item: Name of item to pick up.

        Returns:
            Status of the pick operation.
        """
        if self.holding:
            return {"status": "error", "message": f"Already holding {self.holding}"}

        self.logger.info(f"Picking up {item} at {self.current_position}")
        time.sleep(0.3)  # Simulate pick time
        self.holding = item
        return {"status": "completed", "holding": item}

    @action
    def place(self) -> dict:
        """Place the currently held item.

        Returns:
            Status of the place operation.
        """
        if not self.holding:
            return {"status": "error", "message": "Not holding anything"}

        item = self.holding
        self.logger.info(f"Placing {item} at {self.current_position}")
        time.sleep(0.3)  # Simulate place time
        self.holding = None
        return {"status": "completed", "placed": item, "location": self.current_position}

    @action
    def home(self) -> dict:
        """Return to home position.

        Returns:
            Status of the home operation.
        """
        self.logger.info("Returning to home")
        time.sleep(0.5)
        self.current_position = "home"
        return {"status": "completed", "position": "home"}

    @action
    def get_status(self) -> dict:
        """Get current robot status.

        Returns:
            Current position and held item.
        """
        return {
            "position": self.current_position,
            "holding": self.holding,
        }


if __name__ == "__main__":
    node = RobotArmNode()
    node.start_server(port=2001)  # Different port than temp sensor
```

Install it:

```bash
cd robot_arm_module
pip install -e .
```

## Step 2: Create a Workcell Configuration

Create a workcell configuration file:

```bash
madsci new workcell --name my_workcell
```

Or create `my_workcell.workcell.yaml` manually:

```yaml
# my_workcell.workcell.yaml
name: my_workcell
description: Tutorial workcell with temperature sensor and robot arm

nodes:
  temp_sensor:
    url: http://localhost:2000
    description: Temperature sensor node

  robot_arm:
    url: http://localhost:2001
    description: Simulated robot arm
```

## Step 3: Start the Manager Services

### Option A: Using Docker (Recommended)

Create a `docker-compose.yaml`:

```yaml
version: "3.8"

services:
  # FerretDB (document database) for Event and Workcell managers
  madsci_ferretdb:
    image: ghcr.io/ferretdb/ferretdb:latest
    ports:
      - "27017:27017"
    volumes:
      - ferretdb_data:/state

  # Valkey for Workcell manager queues
  madsci_valkey:
    image: valkey/valkey:8-alpine
    ports:
      - "6379:6379"

  # Event Manager - logging and events
  event_manager:
    image: ghcr.io/ad-sdl/madsci_event_manager:latest
    ports:
      - "8001:8001"
    environment:
      - EVENT_DOCUMENT_DB_URL=mongodb://madsci_ferretdb:27017
    depends_on:
      - madsci_ferretdb

  # Workcell Manager - workflow orchestration
  workcell_manager:
    image: ghcr.io/ad-sdl/madsci_workcell_manager:latest
    ports:
      - "8005:8005"
    environment:
      - WORKCELL_DOCUMENT_DB_URL=mongodb://madsci_ferretdb:27017
      - WORKCELL_REDIS_URL=redis://madsci_valkey:6379
    depends_on:
      - madsci_ferretdb
      - madsci_valkey

volumes:
  ferretdb_data:
```

Start the services:

```bash
docker compose up -d
```

### Option B: Pure Python (No Docker)

The easiest way to run managers locally without Docker is using MADSci's built-in local mode, which automatically uses in-memory backends:

```bash
pip install madsci-event-manager madsci-workcell-manager

# Start all managers in-process with in-memory backends
madsci start --mode=local
```

Alternatively, start them individually in separate terminals:

```bash
# Terminal 1: Event Manager
madsci start manager event

# Terminal 2: Workcell Manager
madsci start manager workcell
```

**Note**: Local/in-memory mode is for development only. Production should use Docker with real database backends.

## Step 4: Start Your Nodes

Start both nodes:

```bash
# Terminal 3: Temperature sensor
cd temp_sensor_module
python src/temp_sensor_rest_node.py
```

```bash
# Terminal 4: Robot arm
cd robot_arm_module
python src/robot_arm_rest_node.py --port 2001
```

## Step 5: Verify Everything is Running

```bash
madsci status
```

Output:
```
MADSci Service Status

  Service               URL                       Status
  ─────────────────────────────────────────────────────────────
  Event Manager         http://localhost:8001     ● Online
  Workcell Manager      http://localhost:8005     ● Online

  Nodes:
  temp_sensor           http://localhost:2000     ● Online
  robot_arm             http://localhost:2001     ● Online
```

## Step 6: Create a Workflow

Now the fun part - create a workflow that coordinates both nodes:

```bash
madsci new workflow --name sample_collection
```

Edit `sample_collection.workflow.yaml`:

```yaml
# sample_collection.workflow.yaml
name: sample_collection

metadata:
  description: Collect a sample and measure temperature
  version: 1.0

# Workflow parameters (passed at runtime via json_inputs)
parameters:
  - name: sample_location
    type: string
    default: rack_a1
  - name: measurement_count
    type: integer
    default: 3

steps:
  # Step 1: Move robot to the sample location supplied at runtime
  - name: move_to_sample
    node: robot_arm
    action: move_to
    parameters:           # alias for use_parameters
      args:
        location: sample_location  # references the workflow parameter

  # Step 2: Pick up the sample
  - name: pick_sample
    node: robot_arm
    action: pick
    args:
      item: sample_tube

  # Step 3: Move to the sensor
  - name: move_to_sensor
    node: robot_arm
    action: move_to
    args:
      location: sensor

  # Step 4: Take temperature reading
  - name: measure_temperature
    node: temp_sensor
    action: read_temperature

  # Step 5: Return sample to storage
  - name: move_to_storage
    node: robot_arm
    action: move_to
    args:
      location: storage

  # Step 6: Place sample
  - name: place_sample
    node: robot_arm
    action: place

  # Step 7: Return robot home
  - name: return_home
    node: robot_arm
    action: home
```

## Step 7: Run the Workflow

### Via Python

```python
from madsci.client.workcell_client import WorkcellClient

# Connect to workcell manager
client = WorkcellClient("http://localhost:8005")

# Submit and await the workflow (await_completion is True by default)
workflow = client.start_workflow(
    workflow_definition="sample_collection.workflow.yaml",
    json_inputs={
        "sample_location": "rack_b2",
        "measurement_count": 5,
    },
)

print(f"Workflow {workflow.workflow_id} finished with status: {workflow.status}")

# Each completed step exposes its ActionResult on `step.result`
measure_step = next(s for s in workflow.steps if s.name == "measure_temperature")
temperature = measure_step.result.json_result["value"]  # depends on the node's response shape
print(f"Temperature: {temperature}°C")
```

### Via CLI

```bash
madsci workflow submit sample_collection.workflow.yaml \
  --json-input sample_location=rack_b2 \
  --json-input measurement_count=5
```

## Step 8: Monitor Workflow Execution

### Check Workflow Status

```python
from madsci.client.workcell_client import WorkcellClient

client = WorkcellClient("http://localhost:8005")

# List currently active workflows
for workflow in client.get_active_workflows():
    print(f"{workflow.workflow_id}: {workflow.status} - {workflow.name}")

# Or query archived (completed) workflows
for workflow in client.get_archived_workflows():
    print(f"{workflow.workflow_id}: {workflow.status} - {workflow.name}")
```

### View Events

```python
from madsci.client.event_client import EventClient

client = EventClient(event_server_url="http://localhost:8001")

# Get the most recent 20 events
events = client.get_events(number=20)
for event in events.values():
    print(f"{event.event_timestamp}: [{event.log_level.name}] {event.event_type} {event.event_data}")
```

### Using the TUI

```bash
madsci tui
```

Navigate to the Logs screen (press `l`) to see real-time events.

## Step 9: Create an Experiment with Workflows

Now integrate workflows into an experiment:

```python
"""Sample collection experiment using workflows."""

from madsci.common.types.experiment_types import ExperimentDesign
from madsci.common.types.workflow_types import WorkflowStatus
from madsci.experiment_application import ExperimentScript


class SampleCollectionExperiment(ExperimentScript):
    """Experiment that runs the sample_collection workflow at multiple locations."""

    experiment_design = ExperimentDesign(
        experiment_name="Multi-Sample Collection",
        experiment_description="Collect samples from multiple locations",
    )

    def run_experiment(
        self,
        sample_locations: list[str] | None = None,
    ) -> dict:
        sample_locations = sample_locations or ["rack_a1", "rack_a2", "rack_b1"]
        results: list[dict] = []

        for location in sample_locations:
            self.logger.info("Processing sample location", location=location)

            workflow = self.workcell_client.start_workflow(
                workflow_definition="sample_collection.workflow.yaml",
                json_inputs={"sample_location": location},
                # Don't raise — we want to record failures and continue
                raise_on_failed=False,
                prompt_on_error=False,
            )

            if workflow.status == WorkflowStatus.COMPLETED:
                measure = next(
                    s for s in workflow.steps if s.name == "measure_temperature"
                )
                temp = measure.result.json_result.get("value") if measure.result else None
                self.logger.info("Reading captured", location=location, temperature=temp)
                results.append({"location": location, "temperature": temp, "status": "success"})
            else:
                self.logger.error(
                    "Workflow failed",
                    location=location,
                    status=workflow.status.value,
                )
                results.append({"location": location, "status": "failed"})

        successful = [r for r in results if r["status"] == "success"]
        temps = [r["temperature"] for r in successful if r["temperature"] is not None]
        summary = {
            "total_samples": len(sample_locations),
            "successful": len(successful),
            "failed": len(results) - len(successful),
        }
        if temps:
            summary["mean_temperature"] = sum(temps) / len(temps)

        return {"results": results, "summary": summary}


if __name__ == "__main__":
    SampleCollectionExperiment.main(lab_server_url="http://localhost:8000")
```

## Workflow Features

### Conditional Steps

Steps support a `conditions` list. Each condition is a structured Pydantic model (resource-in-location, resource-field check, etc.) — not a templated expression. See `madsci.common.types.condition_types` for the supported condition types.

```yaml
steps:
  - name: read_well
    node: platereader_1
    action: read_well
    conditions:
      - condition_type: resource_present
        location_name: platereader_1.plate_carriage
```

### Data Passing Between Steps (Feed-Forward)

To pass an output of one step into a later step, declare a `feed_forward` workflow parameter pointing at the producing step's `key`, then reference that parameter from the consuming step.

```yaml
parameters:
  feed_forward:
    - key: measurement_file
      step: measure          # the key of the step that produces it
      data_type: file
steps:
  - name: Measure
    key: measure
    node: platereader_1
    action: read_plate

  - name: Process Measurement
    node: liquidhandler_1
    action: run_protocol
    files:
      protocol: measurement_file   # consumes the feed-forward parameter
```

For more workflow patterns, see [`docs/guides/workflow_development.md`](../guides/workflow_development.md) and the example workflows in `examples/example_lab/workflows/`.

## Key Takeaways

1. **Workcells coordinate multiple nodes**: One manager, many instruments
2. **Workflows define protocols**: YAML-based, parameterized, reusable
3. **Managers provide infrastructure**: Event logging, workflow orchestration
4. **Experiments can use workflows**: Combine programmatic control with declarative protocols
5. **Start minimal**: You don't need all managers - just what you use

## What's Next?

### Next Tutorial

**[Tutorial 5: Full Lab Setup](05-full-lab.md)** - Deploy a complete lab with all managers, Docker, and monitoring.

### Try These Exercises

1. **Add error handling**: What happens if a node is offline?
2. **Add retries**: Create a workflow step that retries on failure
3. **Add logging**: Log key events to the Event Manager
4. **Create a complex workflow**: Chain multiple workflows together

### Reference

- [Workflow Guide](../guides/workflow_development.md)
- [Workcell Manager Documentation](../../src/madsci_workcell_manager/README.md)
- [Workflow YAML Schema](../../docs/designs/template_system_design.md)
