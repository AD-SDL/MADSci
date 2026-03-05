# Running Experiments

**Audience**: Experimentalist
**Prerequisites**: [Tutorial: First Experiment](../../tutorials/03-first-experiment.md)
**Time**: ~25 minutes

## Overview

MADSci supports multiple ways to run experiments, from simple scripts to long-running autonomous campaigns. This guide covers the practical aspects of running experiments day-to-day.

## Experiment Modalities

| Modality | Best For | Requires Server? |
|----------|----------|-------------------|
| `ExperimentScript` | One-off experiments, batch processing | No |
| `ExperimentNotebook` | Exploratory work, interactive analysis | No |
| `ExperimentTUI` | Interactive terminal control | No |
| `ExperimentNode` | Automated campaigns, API-triggered runs | Yes |

## Running Workflows

The most common experiment pattern is submitting workflows to the workcell.

### Submit a Workflow

```python
from madsci.client import WorkcellClient

wc = WorkcellClient(workcell_server_url="http://localhost:8005/")

# Submit and wait for completion
result = wc.start_workflow(
    "workflows/my_workflow.workflow.yaml",
    json_inputs={"sample_id": "SAMPLE-001", "temperature": 37.0},
    await_completion=True,
)

print(f"Status: {result.status}")
print(f"Duration: {result.duration_seconds:.1f}s")
```

### Submit Without Waiting

```python
# Submit and get workflow ID immediately
result = wc.start_workflow(
    "workflows/my_workflow.workflow.yaml",
    json_inputs={"sample_id": "SAMPLE-001"},
    await_completion=False,
)

workflow_id = result.workflow_id
print(f"Submitted: {workflow_id}")

# Check status later
wf = wc.query_workflow(workflow_id)
print(f"Status: {wf.status}")
print(f"Current step: {wf.status.current_step_index}")
```

### Submit Multiple Workflows

```python
# Sequential execution (one after another)
results = wc.submit_workflow_sequence(
    workflows=[
        "workflows/prepare.workflow.yaml",
        "workflows/measure.workflow.yaml",
        "workflows/cleanup.workflow.yaml",
    ],
    json_inputs=[
        {"plate_id": "PLATE-001"},
        {"samples": 96},
        {},
    ],
)

# Parallel execution (all at once)
results = wc.submit_workflow_batch(
    workflows=[
        "workflows/measure.workflow.yaml",
        "workflows/measure.workflow.yaml",
        "workflows/measure.workflow.yaml",
    ],
    json_inputs=[
        {"sample_id": "A1"},
        {"sample_id": "A2"},
        {"sample_id": "A3"},
    ],
)
```

## Using ExperimentScript

For structured, repeatable experiments:

```python
#!/usr/bin/env python3
"""Temperature sweep experiment."""

from madsci.experiment_application import ExperimentScript
from madsci.common.types.experiment_types import ExperimentDesign


class TemperatureSweep(ExperimentScript):
    experiment_design = ExperimentDesign(
        experiment_name="Temperature Sweep",
        experiment_description="Measure response at varying temperatures",
    )

    def run_experiment(self):
        temperatures = [20, 25, 30, 35, 40, 45, 50]
        results = []

        for temp in temperatures:
            # Submit a workflow for each temperature
            wf = self.workcell_client.start_workflow(
                "workflows/measure_at_temp.workflow.yaml",
                json_inputs={"temperature": temp},
                await_completion=True,
            )

            # Collect results
            results.append({
                "temperature": temp,
                "workflow_id": wf.workflow_id,
                "status": str(wf.status),
                "duration": wf.duration_seconds,
            })

            self.event_client.info(
                f"Completed measurement at {temp}C",
                temperature=temp,
                workflow_id=wf.workflow_id,
            )

        return results


if __name__ == "__main__":
    TemperatureSweep.main()
```

Run it:

```bash
python temperature_sweep.py
```

## Monitoring Running Experiments

### From the CLI

```bash
# Check active workflows
madsci status

# Watch experiment logs
madsci logs --follow --grep "experiment"

# View in TUI
madsci tui
```

### From Python

```python
from madsci.client import WorkcellClient, ExperimentClient

# Check workflow progress
wc = WorkcellClient(workcell_server_url="http://localhost:8005/")
active = wc.get_active_workflows()
for wf_id, wf in active.items():
    completed = len([s for s in wf.steps if s.status == "succeeded"])
    total = len(wf.steps)
    print(f"{wf_id}: {completed}/{total} steps complete")

# Check experiment status
ec = ExperimentClient(experiment_server_url="http://localhost:8002/")
experiments = ec.get_experiments(number=5)
for exp in experiments:
    print(f"{exp.experiment_id}: {exp.status} - {exp.run_name}")
```

## Controlling Running Experiments

### Pause and Resume

```python
from madsci.client import WorkcellClient

wc = WorkcellClient(workcell_server_url="http://localhost:8005/")

# Pause a workflow (finishes current step, then waits)
wc.pause_workflow("workflow_id")

# Resume a paused workflow
wc.resume_workflow("workflow_id")
```

### Cancel

```python
# Cancel a workflow (stops after current step)
wc.cancel_workflow("workflow_id")
```

### Retry Failed Workflows

```python
# Retry from the failed step
retried = wc.retry_workflow(
    "workflow_id",
    index=3,  # Retry from step index 3
    await_completion=True,
)
```

## Workflow Parameters

Workflows accept parameters that are passed to individual steps:

```yaml
# workflows/parameterized.workflow.yaml
name: Parameterized Measurement
parameters:
  sample_id:
    type: string
    description: Sample identifier
  num_replicates:
    type: integer
    default: 3
    description: Number of replicate measurements
  temperature:
    type: number
    default: 25.0
    description: Measurement temperature in Celsius

steps:
  - name: prepare_sample
    node: liquidhandler_1
    action: prepare
    args:
      sample_id: "{{sample_id}}"

  - name: measure
    node: platereader_1
    action: measure
    args:
      replicates: "{{num_replicates}}"
      temperature: "{{temperature}}"
```

Pass parameters when submitting:

```python
result = wc.start_workflow(
    "workflows/parameterized.workflow.yaml",
    json_inputs={
        "sample_id": "SAMPLE-001",
        "num_replicates": 5,
        "temperature": 37.0,
    },
)
```

## Accessing Results

### Workflow Results

```python
# Get completed workflow
wf = wc.query_workflow("workflow_id")

# Access step results
for step in wf.steps:
    print(f"Step: {step.name}")
    print(f"  Status: {step.status}")
    if hasattr(step, "result") and step.result:
        print(f"  Result: {step.result}")

# Get specific datapoints from workflow
datapoint_id = wf.get_datapoint_id("step_name", "result_key")
if datapoint_id:
    from madsci.client import DataClient
    dc = DataClient(data_server_url="http://localhost:8004/")
    dp = dc.get_datapoint(datapoint_id)
    print(f"Value: {dp.value}")
```

### Experiment History

```python
from madsci.client import ExperimentClient

ec = ExperimentClient(experiment_server_url="http://localhost:8002/")

# Get recent experiments
experiments = ec.get_experiments(number=20)
for exp in experiments:
    print(f"{exp.started_at}: {exp.run_name} - {exp.status}")

# Get a specific experiment
exp = ec.get_experiment("experiment_id")
print(f"Design: {exp.experiment_design.experiment_name}")
print(f"Started: {exp.started_at}")
print(f"Ended: {exp.ended_at}")
```

## What's Next?

- [Working with Data](./02-working-with-data.md) - Querying and exporting experiment data
- [Managing Resources](./03-managing-resources.md) - Tracking samples and materials
- [Experiment Design](./04-experiment-design.md) - Best practices for experiment structure
