# Tutorial 3: Your First Experiment

**Time to Complete**: ~25 minutes
**Prerequisites**: [Tutorial 2: Your First Node](02-first-node.md)
**Docker Required**: No

## What You'll Learn

In this tutorial, you'll:

1. Create an experiment script using the `ExperimentScript` modality
2. Interact with your node from an experiment
3. Understand experiment lifecycle management
4. Capture and display experimental data
5. Learn about different experiment modalities

By the end, you'll have an experiment that collects temperature data from your node.

## Experiment Modalities

MADSci supports different ways of running experiments:

| Modality | Use Case | Key Features |
|----------|----------|-------------|
| **ExperimentScript** | Simple run-once experiments | Minimal setup, `run()` method |
| **ExperimentNotebook** | Interactive Jupyter notebooks | Cell-by-cell execution, rich display |
| **ExperimentTUI** | Interactive terminal apps | Full TUI with controls |
| **ExperimentNode** | Long-running servers | REST API, triggered remotely |

We'll start with `ExperimentScript`, the simplest modality.

## Step 1: Set Up Your Experiment

First, make sure you have the experiment application package installed:

```bash
# In your madsci-tutorial directory
source .venv/bin/activate

# Install the experiment package
pip install madsci-experiment-application
```

## Step 2: Create an Experiment Script

Create a new file called `temperature_study.py`:

```python
"""Temperature collection experiment.

This experiment collects temperature readings from the temp_sensor node
and calculates basic statistics.
"""

import time
from datetime import datetime

import httpx
from madsci.experiment_application import ExperimentScript, ExperimentDesign


class TemperatureStudy(ExperimentScript):
    """A simple experiment that collects temperature data.

    This demonstrates the ExperimentScript modality for
    simple run-once experiments.
    """

    # Define your experiment's design
    experiment_design = ExperimentDesign(
        name="Temperature Study",
        description="Collect and analyze temperature readings",
        version="1.0.0",
    )

    def __init__(self, node_url: str = "http://localhost:2000", num_readings: int = 10):
        super().__init__()
        self.node_url = node_url
        self.num_readings = num_readings
        self.readings: list[dict] = []

    def run(self) -> dict:
        """Main experiment logic.

        This method contains your experimental procedure.
        It's called automatically when you run the experiment.

        Returns:
            Dictionary with experiment results.
        """
        print(f"Starting Temperature Study at {datetime.now()}")
        print(f"Collecting {self.num_readings} readings from {self.node_url}")
        print("-" * 50)

        # Collect temperature readings
        for i in range(self.num_readings):
            reading = self._take_reading()
            if reading:
                self.readings.append(reading)
                print(f"  Reading {i+1}: {reading['value']:.2f}°C")

            # Wait between readings
            if i < self.num_readings - 1:
                time.sleep(1)

        # Calculate statistics
        if self.readings:
            values = [r["value"] for r in self.readings]
            stats = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "mean": sum(values) / len(values),
                "range": max(values) - min(values),
            }
        else:
            stats = {"error": "No readings collected"}

        print("-" * 50)
        print("Experiment complete!")
        print(f"  Collected: {stats.get('count', 0)} readings")
        print(f"  Mean temperature: {stats.get('mean', 'N/A'):.2f}°C")
        print(f"  Range: {stats.get('range', 'N/A'):.3f}°C")

        return {
            "readings": self.readings,
            "statistics": stats,
            "experiment_time": datetime.now().isoformat(),
        }

    def _take_reading(self) -> dict | None:
        """Take a single temperature reading from the node.

        Returns:
            Temperature reading dict or None if failed.
        """
        try:
            response = httpx.post(
                f"{self.node_url}/actions/read_temperature",
                json={},
                timeout=5.0,
            )
            response.raise_for_status()
            result = response.json()

            if result.get("action_response") == "succeeded":
                return result["action_result"]
            else:
                print(f"  Warning: Action failed - {result}")
                return None

        except Exception as e:
            print(f"  Error reading temperature: {e}")
            return None


# Entry point for running the experiment
if __name__ == "__main__":
    # Create and run the experiment
    experiment = TemperatureStudy(num_readings=5)
    results = experiment.main()

    # Optionally save results
    # import json
    # with open("results.json", "w") as f:
    #     json.dump(results, f, indent=2)
```

## Step 3: Run Your Experiment

First, make sure your node is running in another terminal:

```bash
# Terminal 1: Start the node
cd temp_sensor_module
python src/temp_sensor_rest_node.py
```

Then run the experiment:

```bash
# Terminal 2: Run the experiment
python temperature_study.py
```

Output:
```
Starting Temperature Study at 2026-02-09 14:45:00
Collecting 5 readings from http://localhost:2000
--------------------------------------------------
  Reading 1: 22.34°C
  Reading 2: 22.15°C
  Reading 3: 22.48°C
  Reading 4: 21.97°C
  Reading 5: 22.29°C
--------------------------------------------------
Experiment complete!
  Collected: 5 readings
  Mean temperature: 22.25°C
  Range: 0.510°C
```

## Step 4: Create a Notebook Experiment

For interactive exploration, use `ExperimentNotebook`. Create `temperature_notebook.py`:

```python
"""Notebook-style temperature experiment.

Designed for use in Jupyter notebooks with cell-by-cell execution.
"""

import httpx
from madsci.experiment_application import ExperimentNotebook, ExperimentDesign


class TemperatureNotebook(ExperimentNotebook):
    """Interactive notebook experiment for temperature analysis.

    Use this in Jupyter for step-by-step exploration:

        # Cell 1
        exp = TemperatureNotebook()
        exp.start()

        # Cell 2
        reading = exp.take_reading()
        exp.display(reading)

        # Cell 3
        exp.end()
    """

    experiment_design = ExperimentDesign(
        name="Temperature Notebook",
        description="Interactive temperature exploration",
        version="1.0.0",
    )

    def __init__(self, node_url: str = "http://localhost:2000"):
        super().__init__()
        self.node_url = node_url
        self.readings: list[dict] = []

    def take_reading(self) -> dict:
        """Take a single reading (call from notebook cell)."""
        response = httpx.post(
            f"{self.node_url}/actions/read_temperature",
            json={},
            timeout=5.0,
        )
        response.raise_for_status()
        result = response.json()

        if result.get("action_response") == "succeeded":
            reading = result["action_result"]
            self.readings.append(reading)
            return reading

        raise RuntimeError(f"Failed to read: {result}")

    def get_statistics(self) -> dict:
        """Calculate statistics from collected readings."""
        if not self.readings:
            return {"error": "No readings"}

        values = [r["value"] for r in self.readings]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
        }
```

### Using in Jupyter

```python
# Cell 1 - Start experiment
from temperature_notebook import TemperatureNotebook

exp = TemperatureNotebook()
exp.start()  # Initializes experiment session
```

```python
# Cell 2 - Collect some readings
for i in range(5):
    reading = exp.take_reading()
    exp.display(reading)
```

```python
# Cell 3 - Analyze results
stats = exp.get_statistics()
exp.display(stats)
```

```python
# Cell 4 - End experiment
exp.end()  # Closes experiment session
```

## Step 5: Using Templates

Instead of writing from scratch, use the template:

```bash
madsci new experiment --name my_study --template script --output .
```

This generates a ready-to-customize experiment script.

## Understanding Experiment Lifecycle

The `ExperimentScript.main()` method handles lifecycle automatically:

```python
def main(cls) -> dict:
    """
    Internally does:
    1. Creates experiment instance
    2. Calls start_experiment_run() if managers available
    3. Calls run() - your code
    4. Calls end_experiment()
    5. Returns results
    """
```

For `ExperimentNotebook`, you control the lifecycle:

```python
exp = MyExperiment()
exp.start()    # Begin experiment session
# ... your cells ...
exp.end()      # End experiment session

# Or use context manager:
with exp:
    # ... your cells ...
```

## Connecting to Manager Services (Optional)

When running with MADSci manager services, experiments can:

- Log events to Event Manager
- Track runs in Experiment Manager
- Store data in Data Manager
- Use resources from Resource Manager

For now, we're running "standalone" without these services. Tutorial 4 introduces workcells with managers.

## Complete Example: Time Series Collection

Here's a more complete experiment that demonstrates data collection over time:

```python
"""Time series temperature collection experiment."""

import time
import json
from datetime import datetime
from pathlib import Path

import httpx
from madsci.experiment_application import ExperimentScript, ExperimentDesign


class TimeSeriesExperiment(ExperimentScript):
    """Collect temperature readings over time and save to file."""

    experiment_design = ExperimentDesign(
        name="Temperature Time Series",
        description="Collect temperature readings at regular intervals",
        version="1.0.0",
    )

    def __init__(
        self,
        node_url: str = "http://localhost:2000",
        duration_seconds: int = 60,
        interval_seconds: float = 5.0,
        output_dir: str = "./data",
    ):
        super().__init__()
        self.node_url = node_url
        self.duration = duration_seconds
        self.interval = interval_seconds
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def run(self) -> dict:
        """Collect time series data."""
        start_time = datetime.now()
        end_time_target = time.time() + self.duration
        readings = []

        print(f"Collecting data for {self.duration} seconds...")
        print(f"Interval: {self.interval} seconds")

        while time.time() < end_time_target:
            # Take reading
            try:
                response = httpx.post(
                    f"{self.node_url}/actions/read_temperature",
                    json={},
                    timeout=5.0,
                )
                result = response.json()

                if result.get("action_response") == "succeeded":
                    reading = result["action_result"]
                    reading["elapsed_seconds"] = time.time() - (end_time_target - self.duration)
                    readings.append(reading)
                    print(f"  {reading['timestamp']}: {reading['value']:.2f}°C")

            except Exception as e:
                print(f"  Error: {e}")

            # Wait for next interval
            time.sleep(self.interval)

        # Save results
        output_file = self.output_dir / f"timeseries_{start_time:%Y%m%d_%H%M%S}.json"
        results = {
            "experiment": self.experiment_design.name,
            "start_time": start_time.isoformat(),
            "duration_seconds": self.duration,
            "interval_seconds": self.interval,
            "readings": readings,
        }

        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"\nSaved {len(readings)} readings to {output_file}")
        return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--interval", type=float, default=5.0)
    args = parser.parse_args()

    experiment = TimeSeriesExperiment(
        duration_seconds=args.duration,
        interval_seconds=args.interval,
    )
    experiment.main()
```

Run it:

```bash
python timeseries_experiment.py --duration 30 --interval 5
```

## Key Takeaways

1. **ExperimentScript is simplest**: Override `run()` and call `main()`
2. **ExperimentNotebook is interactive**: Use `start()`/`end()` for cell-by-cell work
3. **Experiments work standalone**: No managers required for basic usage
4. **Results are just Python dicts**: Easy to save, analyze, or display
5. **Templates save time**: Use `madsci new experiment` to get started

## What's Next?

### Next Tutorial

**[Tutorial 4: Your First Workcell](04-first-workcell.md)** - Coordinate multiple nodes with workflows and start using manager services.

### Try These Exercises

1. **Add parameters**: Make sample rate configurable from command line
2. **Add visualization**: Use matplotlib to plot temperature over time
3. **Add alerts**: Print a warning if temperature exceeds a threshold
4. **Try notebook mode**: Create a Jupyter notebook using `ExperimentNotebook`

### Reference

- [Experiment Modalities Design](../../docs/designs/experiment_modalities_design.md)
- [ExperimentApplication Documentation](../../src/madsci_experiment_application/README.md)
