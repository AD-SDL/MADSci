# Experiment Design Best Practices

**Audience**: Experimentalist
**Prerequisites**: [Running Experiments](./01-running-experiments.md)
**Time**: ~20 minutes

## Overview

Well-designed experiments are easier to run, reproduce, and debug. This guide covers best practices for structuring experiments, workflows, and data collection in MADSci.

## Experiment Structure

### Naming Conventions

Use consistent, descriptive names:

```python
# Good: descriptive, includes key parameters
ExperimentDesign(
    experiment_name="Polymer-A Concentration Sweep",
    experiment_description=(
        "Measure viscosity of Polymer-A at concentrations "
        "1-50 mM in PBS buffer at 25C"
    ),
)

# Bad: vague, no context
ExperimentDesign(
    experiment_name="Test 1",
    experiment_description="Testing",
)
```

### Experiment Hierarchy

Organize related experiments into campaigns:

```
Campaign: "Polymer Characterization Q1 2026"
├── Experiment: "Polymer-A Concentration Sweep"
│   ├── Workflow: prepare_samples
│   ├── Workflow: measure_viscosity (x7 concentrations)
│   └── Workflow: cleanup
├── Experiment: "Polymer-B Concentration Sweep"
│   └── ... (same structure)
└── Experiment: "Polymer Comparison at 10mM"
    └── ... (different workflow)
```

```python
from madsci.client import ExperimentClient
from madsci.common.types.experiment_types import ExperimentalCampaign

ec = ExperimentClient(experiment_server_url="http://localhost:8002/")

# Register a campaign
campaign = ExperimentalCampaign(
    campaign_name="Polymer Characterization Q1 2026",
    campaign_description="Systematic characterization of polymer candidates",
)
campaign = ec.register_campaign(campaign)

# Individual experiments reference the campaign
design = ExperimentDesign(
    experiment_name="Polymer-A Concentration Sweep",
    ownership_info=OwnershipInfo(campaign_id=campaign.campaign_id),
)
```

## Workflow Design

### Keep Workflows Focused

Each workflow should do one logical thing:

```yaml
# Good: focused, reusable
# measure_sample.workflow.yaml
name: Measure Sample
steps:
  - name: pick_up_sample
    node: robotarm_1
    action: pick
    args:
      source: "{{source_location}}"

  - name: place_in_reader
    node: robotarm_1
    action: place
    args:
      destination: "{{reader_location}}"

  - name: measure
    node: platereader_1
    action: measure
    args:
      protocol: "{{protocol}}"

  - name: return_sample
    node: robotarm_1
    action: pick_and_place
    args:
      source: "{{reader_location}}"
      destination: "{{source_location}}"
```

```yaml
# Bad: too many unrelated things in one workflow
# do_everything.workflow.yaml
name: Do Everything
steps:
  - name: calibrate_robot
    # ...
  - name: prepare_reagents
    # ...
  - name: run_all_samples
    # ... (100 steps)
  - name: analyze_data
    # ...
  - name: generate_report
    # ...
```

### Parameterize Workflows

Make workflows reusable with parameters:

```yaml
# Good: parameterized, reusable across experiments
name: Dispense and Measure
parameters:
  sample_id:
    type: string
  volume_ul:
    type: number
    default: 100
  well:
    type: string
    default: "A1"

steps:
  - name: dispense
    node: liquidhandler_1
    action: dispense
    args:
      volume: "{{volume_ul}}"
      destination_well: "{{well}}"

  - name: measure
    node: platereader_1
    action: measure
```

### Handle Errors Gracefully

Design workflows with failure in mind:

```python
class RobustExperiment(ExperimentScript):
    def run_experiment(self):
        results = []

        for sample in self.samples:
            try:
                wf = self.workcell_client.start_workflow(
                    "workflows/measure.workflow.yaml",
                    json_inputs={"sample_id": sample},
                    await_completion=True,
                )

                if wf.status.failed:
                    self.event_client.warning(
                        f"Workflow failed for {sample}, continuing",
                        sample_id=sample,
                        workflow_id=wf.workflow_id,
                    )
                    results.append({"sample": sample, "status": "failed"})
                    continue

                results.append({
                    "sample": sample,
                    "status": "success",
                    "workflow_id": wf.workflow_id,
                })

            except Exception as e:
                self.event_client.error(
                    f"Exception for {sample}: {e}",
                    sample_id=sample,
                )
                results.append({"sample": sample, "status": "error", "error": str(e)})

        return results
```

## Data Collection

### Label Everything

Use descriptive, consistent labels for datapoints:

```python
# Good: descriptive labels with context
self.create_and_upload_value_datapoint(
    label="viscosity_measurement",
    value={
        "viscosity_mPas": 12.5,
        "temperature_C": 25.0,
        "concentration_mM": 10.0,
        "polymer": "Polymer-A",
        "replicate": 1,
    },
    description="Viscosity measurement of Polymer-A at 10mM, 25C",
)

# Bad: generic labels, flat values
self.create_and_upload_value_datapoint(
    label="data",
    value=12.5,
)
```

### Include Metadata

Attach context to every measurement:

```python
import datetime

measurement = {
    # Primary data
    "absorbance_450nm": 0.342,
    "absorbance_600nm": 0.128,

    # Context
    "sample_id": "SAMPLE-001",
    "plate_id": "PLATE-042",
    "well": "A3",
    "replicate": 2,

    # Conditions
    "temperature_C": 37.0,
    "incubation_time_min": 30,

    # Provenance
    "instrument": "platereader_1",
    "protocol": "abs_scan_v2",
    "timestamp": datetime.datetime.now().isoformat(),
}
```

### Structured vs. File Data

| Use Value Datapoints For | Use File Datapoints For |
|--------------------------|------------------------|
| Single measurements | Raw instrument output files |
| Calculated results | Spectra, chromatograms |
| Status indicators | Images |
| Small data (<10KB) | Large datasets |
| Data you'll query | Data you'll download and process |

## Reproducibility

### Record Parameters

Log all experiment parameters:

```python
class ReproducibleExperiment(ExperimentScript):
    def run_experiment(self):
        params = {
            "concentrations": [1, 5, 10, 25, 50],
            "temperature": 25.0,
            "buffer": "PBS",
            "replicates": 3,
            "protocol_version": "v2.1",
        }

        # Log parameters as a datapoint
        self.event_client.info(
            "Starting experiment with parameters",
            **params,
        )

        # Also store as a queryable datapoint
        self.data_client.submit_datapoint(
            DataPoint(
                label="experiment_parameters",
                value=params,
                description="Full parameter set for this experiment run",
            )
        )

        # Run experiment with recorded parameters
        for conc in params["concentrations"]:
            for rep in range(params["replicates"]):
                self._measure(conc, rep, params["temperature"])
```

### Version Control Workflows

Keep workflow YAML files in version control alongside your experiment scripts. This ensures you can reproduce any past experiment.

### Use Experiment Runs

The Experiment Manager tracks each run with timestamps and status:

```python
class TrackedExperiment(ExperimentScript):
    experiment_design = ExperimentDesign(
        experiment_name="Tracked Experiment",
        experiment_description="Every run is recorded",
    )

    def run_experiment(self):
        # manage_experiment() automatically:
        # 1. Registers the run with Experiment Manager
        # 2. Sets status to IN_PROGRESS
        # 3. Sets status to COMPLETED/FAILED on exit
        # 4. Records start and end times
        with self.manage_experiment():
            result = self.workcell_client.start_workflow(
                "workflows/my_workflow.workflow.yaml",
                await_completion=True,
            )
            return result
```

## Common Patterns

### Sweep Pattern

```python
def sweep_parameter(self, param_name, values, base_inputs):
    """Run a workflow across a range of parameter values."""
    results = []
    for value in values:
        inputs = {**base_inputs, param_name: value}
        wf = self.workcell_client.start_workflow(
            "workflows/measure.workflow.yaml",
            json_inputs=inputs,
            await_completion=True,
        )
        results.append({
            param_name: value,
            "workflow_id": wf.workflow_id,
            "status": "ok" if wf.status.ok else "failed",
        })
    return results
```

### Replicate Pattern

```python
def run_with_replicates(self, inputs, n_replicates=3):
    """Run the same workflow multiple times for statistical power."""
    results = []
    for rep in range(n_replicates):
        wf = self.workcell_client.start_workflow(
            "workflows/measure.workflow.yaml",
            json_inputs={**inputs, "replicate": rep},
            await_completion=True,
        )
        results.append(wf)

        self.event_client.info(
            f"Replicate {rep + 1}/{n_replicates} complete",
            replicate=rep,
            workflow_id=wf.workflow_id,
        )
    return results
```

### Checkpoint Pattern

```python
def run_with_checkpoints(self, samples):
    """Save progress after each sample so we can resume on failure."""
    completed = []

    for i, sample in enumerate(samples):
        self.event_client.info(
            f"Processing sample {i + 1}/{len(samples)}",
            sample_id=sample,
            progress=f"{i + 1}/{len(samples)}",
        )

        wf = self.workcell_client.start_workflow(
            "workflows/process_sample.workflow.yaml",
            json_inputs={"sample_id": sample},
            await_completion=True,
        )

        completed.append(sample)

        # Save checkpoint
        self.data_client.submit_datapoint(
            DataPoint(
                label="experiment_checkpoint",
                value={
                    "completed_samples": completed,
                    "remaining": samples[i + 1:],
                    "total": len(samples),
                },
            )
        )
```

## What's Next?

- [Jupyter Notebooks](./05-jupyter-notebooks.md) - Interactive experimentation
- [Running Experiments](./01-running-experiments.md) - Practical execution guide
- [Working with Data](./02-working-with-data.md) - Data retrieval and export
