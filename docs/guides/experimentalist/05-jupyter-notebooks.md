# Jupyter Notebooks

**Audience**: Experimentalist
**Prerequisites**: [Running Experiments](./01-running-experiments.md), [Working with Data](./02-working-with-data.md)
**Time**: ~25 minutes

## Overview

Jupyter notebooks are ideal for interactive experimentation, data exploration, and analysis. MADSci provides the `ExperimentNotebook` modality specifically designed for cell-by-cell execution in notebook environments.

## Setup

### Install Dependencies

```bash
pip install madsci_experiment_application jupyter

# Optional: for rich display
pip install rich
```

### Start Jupyter

```bash
jupyter notebook
# or
jupyter lab
```

## Using ExperimentNotebook

The `ExperimentNotebook` class provides a cell-friendly interface:

### Cell 1: Setup

```python
from madsci.experiment_application import ExperimentNotebook
from madsci.common.types.experiment_types import ExperimentDesign

class MyExperiment(ExperimentNotebook):
    experiment_design = ExperimentDesign(
        experiment_name="Interactive Analysis",
        experiment_description="Exploring polymer viscosity data",
    )

exp = MyExperiment()
```

### Cell 2: Start Experiment

```python
exp.start()
# Registers the experiment run with the Experiment Manager
# Displays experiment info
```

### Cell 3: Run Workflows

```python
# Submit a workflow
result = exp.run_workflow(
    "workflows/measure.workflow.yaml",
    json_inputs={"sample_id": "SAMPLE-001", "temperature": 25.0},
)

# Display the result
exp.display(result)
```

### Cell 4: Analyze Results

```python
import pandas as pd

# Access data from the workflow
data = []
for step in result.steps:
    if hasattr(step, "result") and step.result:
        data.append({
            "step": step.name,
            "status": str(step.status),
        })

df = pd.DataFrame(data)
df
```

### Cell 5: Run More Workflows

```python
# Run a sweep
results = []
for temp in [20, 25, 30, 35, 40]:
    wf = exp.run_workflow(
        "workflows/measure.workflow.yaml",
        json_inputs={"sample_id": "SAMPLE-001", "temperature": temp},
    )
    results.append({"temperature": temp, "workflow_id": wf.workflow_id})
    print(f"Completed at {temp}C")

pd.DataFrame(results)
```

### Cell 6: End Experiment

```python
exp.end()
# Marks the experiment as complete
# Displays summary
```

## Context Manager Pattern

Alternatively, use the context manager for automatic cleanup:

```python
with MyExperiment() as exp:
    result = exp.run_workflow(
        "workflows/measure.workflow.yaml",
        json_inputs={"sample_id": "SAMPLE-001"},
    )
    exp.display(result)
# Experiment automatically ended on exit
```

## Using Clients Directly

For more control, use the MADSci clients directly in notebooks:

### Data Exploration

```python
from madsci.client import DataClient
import pandas as pd

dc = DataClient(data_server_url="http://localhost:8004/")

# Query recent datapoints
datapoints = dc.get_datapoints(number=50)

# Convert to DataFrame
rows = []
for dp in datapoints:
    row = {
        "id": dp.datapoint_id,
        "label": dp.label,
        "created": dp.created_at,
    }
    if isinstance(dp.value, dict):
        row.update(dp.value)
    else:
        row["value"] = dp.value
    rows.append(row)

df = pd.DataFrame(rows)
df.head()
```

### Plotting

```python
import matplotlib.pyplot as plt

# Query temperature readings
temp_data = dc.query_datapoints({"label": "temperature_reading"})

temps = [dp.value["temperature"] for dp in temp_data.values()]
times = [dp.created_at for dp in temp_data.values()]

plt.figure(figsize=(10, 4))
plt.plot(times, temps, "o-")
plt.xlabel("Time")
plt.ylabel("Temperature (C)")
plt.title("Temperature Over Time")
plt.grid(True)
plt.show()
```

### Resource Inspection

```python
from madsci.client import ResourceClient

rc = ResourceClient(resource_server_url="http://localhost:8003/")

# Check plate contents
plate = rc.get_resource("plate_id")
print(f"Plate: {plate.resource_name}")
print(f"Type: {plate.base_type}")
print(f"Children: {len(plate.children)} / {plate.capacity}")

# Display as table
if hasattr(plate, "children"):
    for key, child in plate.children.items():
        print(f"  {key}: {child.resource_name if child else 'empty'}")
```

### Event Log Analysis

```python
from madsci.client import EventClient

ec = EventClient()

# Get workflow events
events = ec.query_events({
    "event_type": "WORKFLOW_COMPLETE",
})

# Analyze workflow durations
durations = []
for event_id, event in events.items():
    if "duration" in str(event.event_data):
        durations.append(event.event_data)

if durations:
    df = pd.DataFrame(durations)
    print(df.describe())
```

## Using Interfaces Directly

One of MADSci's design principles is that interfaces are independent of the framework. You can use them directly in notebooks:

```python
# Use a fake interface for development
from my_sensor_fake_interface import MySensorFakeInterface

iface = MySensorFakeInterface()
iface.connect()

# Interactive exploration
reading = iface.read_sensor()
print(f"Temperature: {reading['temperature']:.1f}C")
print(f"Humidity: {reading['humidity']:.1f}%")

# Collect time series
import time

readings = []
for i in range(20):
    r = iface.read_sensor()
    readings.append(r)
    time.sleep(0.5)

iface.disconnect()

# Analyze
df = pd.DataFrame(readings)
df.plot(y=["temperature", "humidity"], figsize=(10, 4))
plt.show()
```

## Notebook Best Practices

### 1. Keep Cells Focused

Each cell should do one thing:
- Cell 1: Imports and setup
- Cell 2: Data loading/query
- Cell 3: Processing
- Cell 4: Visualization
- Cell 5: Cleanup

### 2. Save Results to Files

Don't rely on notebook state for important results:

```python
# Save processed data
df.to_csv("results/experiment_2026-02-09.csv", index=False)

# Save figures
fig.savefig("results/temperature_plot.png", dpi=150, bbox_inches="tight")
```

### 3. Use Markdown Cells for Documentation

Document your experimental protocol, observations, and decisions in markdown cells between code cells.

### 4. Handle Connection Errors

```python
try:
    dc = DataClient(data_server_url="http://localhost:8004/")
    datapoints = dc.get_datapoints(number=10)
    print(f"Connected. {len(datapoints)} datapoints available.")
except Exception as e:
    print(f"Could not connect to Data Manager: {e}")
    print("Is the lab running? Try: docker compose up -d")
```

### 5. Restart Kernel Safely

If you need to restart the kernel, make sure to end any active experiments first:

```python
# Always run this before restarting
if 'exp' in dir() and exp._experiment_id:
    exp.end()
```

## Example Notebooks

The `example_lab/notebooks/` directory contains example notebooks:

| Notebook | Description |
|----------|-------------|
| `experiment_notebook.ipynb` | Full experiment workflow |
| `node_notebook.ipynb` | Direct node interaction |
| `backup_and_migration.ipynb` | Database management |
| `example_utilization_plots.ipynb` | Utilization analytics |

## What's Next?

- [Running Experiments](./01-running-experiments.md) - Script-based experiments
- [Working with Data](./02-working-with-data.md) - Data querying and export
- [Experiment Design](./04-experiment-design.md) - Best practices
