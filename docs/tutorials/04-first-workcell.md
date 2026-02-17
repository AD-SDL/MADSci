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
  # MongoDB for Event and Workcell managers
  mongodb:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

  # Redis for Workcell manager queues
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # Event Manager - logging and events
  event_manager:
    image: ghcr.io/ad-sdl/madsci_event_manager:latest
    ports:
      - "8001:8001"
    environment:
      - EVENT_MONGO_DB_URL=mongodb://mongodb:27017
    depends_on:
      - mongodb

  # Workcell Manager - workflow orchestration
  workcell_manager:
    image: ghcr.io/ad-sdl/madsci_workcell_manager:latest
    ports:
      - "8005:8005"
    environment:
      - WORKCELL_MONGO_DB_URL=mongodb://mongodb:27017
      - WORKCELL_REDIS_URL=redis://redis:6379
    depends_on:
      - mongodb
      - redis

volumes:
  mongo_data:
```

Start the services:

```bash
docker compose up -d
```

### Option B: Pure Python (No Docker)

Install the managers locally:

```bash
pip install madsci-event-manager madsci-workcell-manager
```

Start them in separate terminals:

```bash
# Terminal 1: Event Manager (needs MongoDB - use in-memory for testing)
python -m madsci.event_manager

# Terminal 2: Workcell Manager (needs Redis - use in-memory for testing)
python -m madsci.workcell_manager
```

**Note**: Pure Python mode with in-memory storage is for development only. Production should use Docker.

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
description: Collect a sample and measure temperature

# Workflow parameters (can be passed at runtime)
parameters:
  sample_location:
    type: string
    default: "rack_a1"
    description: Location to pick sample from
  measurement_count:
    type: integer
    default: 3
    description: Number of temperature readings to take

steps:
  # Step 1: Move robot to sample location
  - name: move_to_sample
    node: robot_arm
    action: move_to
    args:
      location: "{{ parameters.sample_location }}"

  # Step 2: Pick up the sample
  - name: pick_sample
    node: robot_arm
    action: pick
    args:
      item: "sample_tube"

  # Step 3: Move to the sensor
  - name: move_to_sensor
    node: robot_arm
    action: move_to
    args:
      location: "sensor"

  # Step 4: Take temperature reading
  - name: measure_temperature
    node: temp_sensor
    action: read_temperature
    # Result will be available as steps.measure_temperature.result

  # Step 5: Return sample to storage
  - name: move_to_storage
    node: robot_arm
    action: move_to
    args:
      location: "storage"

  # Step 6: Place sample
  - name: place_sample
    node: robot_arm
    action: place

  # Step 7: Return robot home
  - name: return_home
    node: robot_arm
    action: home

# Output what we collected
outputs:
  temperature:
    source: steps.measure_temperature.result.value
  sample_location:
    source: parameters.sample_location
```

## Step 7: Run the Workflow

### Via Python

```python
from madsci.client.workcell_client import WorkcellClient

# Connect to workcell manager
client = WorkcellClient(base_url="http://localhost:8005")

# Start the workflow
result = client.start_workflow(
    workflow_path="sample_collection.workflow.yaml",
    parameters={
        "sample_location": "rack_b2",
        "measurement_count": 5,
    }
)

print(f"Workflow started: {result.workflow_run_id}")

# Wait for completion and get results
final_result = client.wait_for_workflow(result.workflow_run_id)
print(f"Workflow completed!")
print(f"Temperature: {final_result.outputs['temperature']}°C")
```

### Via CLI (Coming Soon)

```bash
madsci run workflow sample_collection.workflow.yaml \
  --param sample_location=rack_b2 \
  --param measurement_count=5
```

## Step 8: Monitor Workflow Execution

### Check Workflow Status

```python
from madsci.client.workcell_client import WorkcellClient

client = WorkcellClient()

# List recent workflow runs
runs = client.list_workflow_runs(limit=10)
for run in runs:
    print(f"{run.workflow_run_id}: {run.status} - {run.workflow_name}")
```

### View Events

```python
from madsci.client.event_client import EventClient

client = EventClient(base_url="http://localhost:8001")

# Get recent events
events = client.query_events(limit=20)
for event in events:
    print(f"{event.timestamp}: [{event.level}] {event.message}")
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

from madsci.experiment_application import ExperimentScript, ExperimentDesign
from madsci.client.workcell_client import WorkcellClient


class SampleCollectionExperiment(ExperimentScript):
    """Experiment that runs multiple sample collection workflows."""

    experiment_design = ExperimentDesign(
        name="Multi-Sample Collection",
        description="Collect samples from multiple locations",
        version="1.0.0",
    )

    def __init__(
        self,
        workcell_url: str = "http://localhost:8005",
        sample_locations: list[str] = None,
    ):
        super().__init__()
        self.workcell_url = workcell_url
        self.sample_locations = sample_locations or ["rack_a1", "rack_a2", "rack_b1"]
        self.results: list[dict] = []

    def run(self) -> dict:
        """Run sample collection for all locations."""
        client = WorkcellClient(base_url=self.workcell_url)

        print(f"Collecting samples from {len(self.sample_locations)} locations")

        for location in self.sample_locations:
            print(f"\nProcessing {location}...")

            # Start workflow
            run = client.start_workflow(
                workflow_path="sample_collection.workflow.yaml",
                parameters={"sample_location": location},
            )

            # Wait for completion
            result = client.wait_for_workflow(run.workflow_run_id, timeout=60)

            if result.status == "completed":
                temp = result.outputs.get("temperature")
                print(f"  Temperature: {temp}°C")
                self.results.append({
                    "location": location,
                    "temperature": temp,
                    "status": "success",
                })
            else:
                print(f"  Failed: {result.error}")
                self.results.append({
                    "location": location,
                    "status": "failed",
                    "error": str(result.error),
                })

        # Summary
        successful = [r for r in self.results if r["status"] == "success"]
        temps = [r["temperature"] for r in successful]

        summary = {
            "total_samples": len(self.sample_locations),
            "successful": len(successful),
            "failed": len(self.results) - len(successful),
        }

        if temps:
            summary["mean_temperature"] = sum(temps) / len(temps)
            summary["min_temperature"] = min(temps)
            summary["max_temperature"] = max(temps)

        print(f"\nExperiment complete: {summary}")

        return {
            "results": self.results,
            "summary": summary,
        }


if __name__ == "__main__":
    experiment = SampleCollectionExperiment()
    experiment.main()
```

## Workflow Features

### Conditional Steps

```yaml
steps:
  - name: check_temperature
    node: temp_sensor
    action: read_temperature

  - name: alert_if_high
    node: notification_service
    action: send_alert
    condition: "{{ steps.check_temperature.result.value > 30 }}"
    args:
      message: "Temperature too high!"
```

### Parallel Steps

```yaml
steps:
  - name: parallel_readings
    parallel:
      - name: read_sensor_1
        node: temp_sensor_1
        action: read_temperature

      - name: read_sensor_2
        node: temp_sensor_2
        action: read_temperature
```

### Data Passing Between Steps

```yaml
steps:
  - name: first_reading
    node: temp_sensor
    action: read_temperature

  - name: log_reading
    node: data_logger
    action: log
    args:
      value: "{{ steps.first_reading.result.value }}"
      timestamp: "{{ steps.first_reading.result.timestamp }}"
```

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
