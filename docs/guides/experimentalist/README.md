# Experimentalist Guide

This guide is for the **Experimentalist** persona - scientists who run experiments and work with data in MADSci-powered laboratories.

## Guide Contents

1. [Running Experiments](01-running-experiments.md) - Using workflows and experiment scripts
2. [Working with Data](02-working-with-data.md) - Querying and exporting experimental data
3. [Managing Resources](03-managing-resources.md) - Tracking samples and materials
4. [Experiment Design](04-experiment-design.md) - Best practices for experimental protocols
5. [Jupyter Notebooks](05-jupyter-notebooks.md) - Interactive experimentation

## Who is an Experimentalist?

An Experimentalist:

- Designs and runs experiments
- Works with experimental data
- Manages laboratory resources and samples
- Uses workflows to automate protocols
- Often works in Jupyter notebooks

## Quick Start

### Running a Workflow

```python
from madsci.client.workcell_client import WorkcellClient

client = WorkcellClient()
result = client.start_workflow(
    "my_experiment.workflow.yaml",
    parameters={"sample_count": 5}
)

# Wait for completion
final = client.wait_for_workflow(result.workflow_run_id)
print(f"Result: {final.outputs}")
```

### Running an Experiment Script

```python
from madsci.experiment_application import ExperimentScript
from madsci.common.types.experiment_types import ExperimentDesign

class MyExperiment(ExperimentScript):
    experiment_design = ExperimentDesign(
        experiment_name="My Experiment",
        experiment_description="Simple data collection",
    )

    def run_experiment(self):
        # Your experiment logic here
        return {"result": "success"}

if __name__ == "__main__":
    MyExperiment.main()
```

### Querying Data

```python
from madsci.client.data_client import DataClient

client = DataClient()

# Get recent data
data = client.query(
    collection="temperature_readings",
    filter={"experiment_id": "exp-123"},
    limit=100,
)

for record in data:
    print(f"{record['timestamp']}: {record['value']}°C")
```

### Managing Resources

```python
from madsci.client.resource_client import ResourceClient

client = ResourceClient()

# Find available samples
samples = client.query_resources(
    template_name="sample_tube",
    status="available",
)

# Reserve a sample for your experiment
client.update_status(samples[0].resource_id, "reserved")
```

## Key Concepts

### Experiment Modalities

| Modality | Use Case | Best For |
|----------|----------|----------|
| `ExperimentScript` | Simple automation | One-off experiments |
| `ExperimentNotebook` | Jupyter integration | Interactive exploration |
| `ExperimentTUI` | Terminal interface | Monitoring during runs |
| `ExperimentNode` | Server mode | Scheduled/triggered experiments |

### Workflows vs. Scripts

| Approach | When to Use |
|----------|-------------|
| **Workflows** (YAML) | Repeatable protocols, standard procedures |
| **Scripts** (Python) | Custom logic, complex decisions, data analysis |

### Data Organization

| Collection | Purpose |
|------------|--------|
| `experiment_runs` | Experiment metadata and status |
| `workflow_results` | Workflow execution results |
| `measurements` | Raw measurement data |
| `files` | Large data files (SeaweedFS) |

### Resource Lifecycle

```
available → reserved → in_use → processed → available
                               └→ consumed (for consumables)
```

## Common Tasks

### Check Experiment Status

```python
from madsci.client.experiment_client import ExperimentClient

client = ExperimentClient()

# List your experiments
experiments = client.list_experiments(limit=10)
for exp in experiments:
    print(f"{exp.name}: {exp.status}")

# Get details of specific experiment
details = client.get_experiment("exp-123")
print(f"Started: {details.started_at}")
print(f"Status: {details.status}")
```

### Export Data

```python
import pandas as pd
from madsci.client.data_client import DataClient

client = DataClient()
data = client.query(collection="measurements", filter={"experiment_id": "exp-123"})

# Convert to DataFrame
df = pd.DataFrame(data)
df.to_csv("experiment_results.csv", index=False)
```

### Download Files

```python
from madsci.client.data_client import DataClient

client = DataClient()

# List files for an experiment
files = client.list_files(experiment_id="exp-123")

# Download a file
for file in files:
    client.download_file(file.file_id, f"./downloads/{file.filename}")
```

### View Events/Logs

```python
from madsci.client.event_client import EventClient

client = EventClient()

# Get events for your experiment
events = client.query_events(
    filter={"experiment_id": "exp-123"},
    limit=50,
)

for event in events:
    print(f"[{event.level}] {event.timestamp}: {event.message}")
```

## Tips for Success

### 1. Start Small

- Test with single samples before batch processing
- Use fake interfaces during development
- Run dry-run workflows first

### 2. Log Everything

```python
from madsci.client.event_client import EventClient

logger = EventClient(name="my_experiment")
logger.info("Starting sample processing", sample_count=10)
```

### 3. Track Resources

- Always update resource status when using samples
- Use barcodes for physical tracking
- Record resource locations after moves

### 4. Handle Errors Gracefully

```python
try:
    result = client.start_workflow("experiment.yaml")
    final = client.wait_for_workflow(result.workflow_run_id, timeout=3600)
except TimeoutError:
    logger.error("Workflow timed out")
    # Handle timeout...
except Exception as e:
    logger.error("Workflow failed", error=str(e))
    # Handle error...
```

### 5. Use Jupyter for Exploration

```python
# In notebook
from madsci.experiment_application import ExperimentNotebook

exp = MyExperiment()
exp.start()

# Interactive cells...
result = exp.take_reading()
exp.display(result)

exp.end()
```

## Prerequisites

- Python 3.10+
- Access to a running MADSci lab
- Basic Python and Jupyter skills
- Understanding of your experiment protocols
