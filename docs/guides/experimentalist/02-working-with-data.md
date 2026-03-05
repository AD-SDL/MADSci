# Working with Data

**Audience**: Experimentalist
**Prerequisites**: [Running Experiments](./01-running-experiments.md)
**Time**: ~25 minutes

## Overview

MADSci captures data throughout experiment execution via the Data Manager. This guide covers how to query, retrieve, and export your experiment data.

## Data Architecture

```
Experiment Run
  └── Workflow Execution
       └── Step Execution
            └── Action Result
                 ├── Value Datapoints (numbers, strings, JSON)
                 └── File Datapoints (CSVs, images, raw data)
                      └── Stored in MinIO (object storage)
```

Every piece of data in MADSci is a **DataPoint** with:
- A unique ID (ULID)
- A label (human-readable name)
- A value or file reference
- Metadata (timestamp, source, experiment ID, etc.)

## Querying Datapoints

### Using the DataClient

```python
from madsci.client import DataClient

dc = DataClient(data_server_url="http://localhost:8004/")

# Get recent datapoints
datapoints = dc.get_datapoints(number=20)
for dp in datapoints:
    print(f"{dp.datapoint_id}: {dp.label} = {dp.value}")

# Get a specific datapoint
dp = dc.get_datapoint("datapoint_id_here")
print(f"Label: {dp.label}")
print(f"Value: {dp.value}")
print(f"Created: {dp.created_at}")
```

### Query by Selector

```python
# Query by label
temp_data = dc.query_datapoints({"label": "temperature_reading"})

# Query by experiment
exp_data = dc.query_datapoints({"experiment_id": "experiment_id_here"})

# Query by time range
from datetime import datetime, timedelta

recent_data = dc.query_datapoints({
    "created_at": {
        "$gte": (datetime.now() - timedelta(hours=24)).isoformat()
    }
})
```

### Get Datapoints from Workflow Results

```python
from madsci.client import WorkcellClient, DataClient

wc = WorkcellClient(workcell_server_url="http://localhost:8005/")
dc = DataClient(data_server_url="http://localhost:8004/")

# Get workflow result
wf = wc.query_workflow("workflow_id")

# Extract datapoint IDs from action results
for step in wf.steps:
    if hasattr(step, "result") and step.result:
        dp_ids = dc.extract_datapoint_ids_from_action_result(step.result)
        for dp_id in dp_ids:
            dp = dc.get_datapoint(dp_id)
            print(f"  {dp.label}: {dp.value}")
```

## Retrieving File Data

File datapoints (CSVs, images, raw instrument data) are stored in MinIO object storage.

### Download a File

```python
from madsci.client import DataClient

dc = DataClient(data_server_url="http://localhost:8004/")

# Get the datapoint
dp = dc.get_datapoint("file_datapoint_id")

# Download the file
dc.save_datapoint_value("file_datapoint_id", output_filepath="./data/output.csv")
print("File downloaded to ./data/output.csv")
```

### Get File Value Directly

```python
# Get file content as bytes/string
value = dc.get_datapoint_value("file_datapoint_id")
print(f"File content: {value[:200]}...")  # First 200 chars
```

### Batch Download

```python
import os

# Download all datapoints from an experiment
exp_data = dc.query_datapoints({"experiment_id": "exp_id"})

os.makedirs("./experiment_data", exist_ok=True)
for dp_id, dp in exp_data.items():
    if dp.file_path:  # File datapoint
        output = f"./experiment_data/{dp.label}_{dp_id[:8]}.dat"
        dc.save_datapoint_value(dp_id, output_filepath=output)
        print(f"Downloaded: {output}")
    else:  # Value datapoint
        print(f"{dp.label}: {dp.value}")
```

## Uploading Data

You can upload data from experiment scripts:

### Value Datapoints

```python
from madsci.client import DataClient
from madsci.common.types.data_types import DataPoint

dc = DataClient(data_server_url="http://localhost:8004/")

# Submit a value datapoint
dp = DataPoint(
    label="analysis_result",
    value={"mean": 42.5, "std": 1.2, "n": 10},
    description="Statistical analysis of temperature readings",
)
result = dc.submit_datapoint(dp)
print(f"Stored as: {result.datapoint_id}")
```

### File Datapoints

```python
import json
from pathlib import Path

# Create a data file
data = {"readings": [25.1, 25.3, 24.9, 25.0, 25.2]}
data_file = Path("./readings.json")
data_file.write_text(json.dumps(data, indent=2))

# Upload as file datapoint
dp = DataPoint(
    label="raw_readings",
    file_path=str(data_file),
    description="Raw sensor readings in JSON format",
)
result = dc.submit_datapoint(dp)
print(f"Stored as: {result.datapoint_id}")
```

### From Node Actions

Nodes can upload data during action execution (see [Wiring the Node](../integrator/05-wiring-the-node.md)):

```python
# Inside a node action
self.create_and_upload_value_datapoint(
    label="measurement",
    value=42.5,
    description="Temperature measurement",
)

self.create_and_upload_file_datapoint(
    label="spectrum",
    file_path=Path("/tmp/spectrum.csv"),
    description="UV-Vis absorption spectrum",
)
```

## Datapoint Metadata

```python
# Get metadata for a datapoint
meta = dc.get_datapoint_metadata("datapoint_id")
print(f"Created: {meta['created_at']}")
print(f"Source: {meta.get('source', 'unknown')}")
print(f"Size: {meta.get('size', 'N/A')} bytes")

# Batch metadata retrieval
metadata = dc.get_datapoints_metadata(["dp_id_1", "dp_id_2", "dp_id_3"])
for dp_id, meta in metadata.items():
    print(f"{dp_id}: {meta}")
```

## Data Export Patterns

### Export to Pandas DataFrame

```python
import pandas as pd
from madsci.client import DataClient

dc = DataClient(data_server_url="http://localhost:8004/")

# Query datapoints
data = dc.query_datapoints({"label": "temperature_reading"})

# Convert to DataFrame
rows = []
for dp_id, dp in data.items():
    row = {"datapoint_id": dp_id, "label": dp.label}
    if isinstance(dp.value, dict):
        row.update(dp.value)
    else:
        row["value"] = dp.value
    rows.append(row)

df = pd.DataFrame(rows)
print(df.describe())

# Save to CSV
df.to_csv("experiment_data.csv", index=False)
```

### Export to JSON

```python
import json

data = dc.query_datapoints({"experiment_id": "exp_id"})

export = {}
for dp_id, dp in data.items():
    export[dp_id] = {
        "label": dp.label,
        "value": dp.value,
        "description": dp.description,
    }

with open("experiment_export.json", "w") as f:
    json.dump(export, f, indent=2, default=str)
```

## Event Logs as Data

The Event Manager also captures structured events that can be used for analysis:

```python
from madsci.client import EventClient

ec = EventClient()

# Query workflow completion events
events = ec.query_events({
    "event_type": "WORKFLOW_COMPLETE",
    "event_timestamp": {"$gte": "2026-02-01T00:00:00Z"},
})

# Analyze workflow durations
for event_id, event in events.items():
    print(f"{event.event_timestamp}: {event.event_data}")
```

## What's Next?

- [Managing Resources](./03-managing-resources.md) - Track samples and materials
- [Experiment Design](./04-experiment-design.md) - Best practices for structuring experiments
- [Jupyter Notebooks](./05-jupyter-notebooks.md) - Interactive data exploration
