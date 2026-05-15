---
name: madsci-experiments
description: Working with MADSci experiment modalities and the experiment lifecycle. Use when creating, modifying, or debugging experiments using ExperimentScript, ExperimentNotebook, ExperimentTUI, or ExperimentNode.
---

# MADSci Experiments

MADSci provides four experiment modalities, all built on `ExperimentBase` which uses `MadsciClientMixin` (composition, not RestNode inheritance). Choose the right modality for your use case, then implement `run_experiment()`.

## Key Files

| File | Purpose |
|------|---------|
| `src/madsci_experiment_application/madsci/experiment_application/experiment_base.py` | Base class, lifecycle, context manager |
| `src/madsci_experiment_application/madsci/experiment_application/experiment_script.py` | Simple run-once modality |
| `src/madsci_experiment_application/madsci/experiment_application/experiment_notebook.py` | Jupyter notebook modality |
| `src/madsci_experiment_application/madsci/experiment_application/experiment_tui.py` | Terminal UI modality |
| `src/madsci_experiment_application/madsci/experiment_application/experiment_node.py` | REST server modality |
| `src/madsci_common/madsci/common/types/experiment_types.py` | ExperimentDesign, Experiment, ExperimentStatus |
| `src/madsci_client/madsci/client/experiment_client.py` | Experiment Manager HTTP client |
| `src/madsci_client/madsci/client/client_mixin.py` | MadsciClientMixin with 7 lazy client properties |
| `src/madsci_common/madsci/common/bundled_templates/experiment/` | Templates for all 4 modalities |

## Choosing a Modality

| Modality | Best For | Entry Point | Interactive? |
|----------|----------|-------------|-------------|
| **ExperimentScript** | Batch processing, automated pipelines | `run()` or `main()` | No |
| **ExperimentNotebook** | Exploratory analysis, Jupyter workflows | `start()` / `end()` | Yes (cell-by-cell) |
| **ExperimentTUI** | Operator-attended experiments needing pause/cancel | `run_tui()` | Yes (terminal) |
| **ExperimentNode** | Remote-controlled experiments via REST API | `start_server()` | Via HTTP |

## Architecture

```
ExperimentBase (MadsciClientMixin)
  ├── ExperimentScript     # run() -> manage_experiment() -> run_experiment()
  ├── ExperimentNotebook   # start() / end() with Rich display
  ├── ExperimentTUI        # Textual TUI with threading.Event pause/cancel
  └── ExperimentNode       # Wraps RestNode internally, exposes run_experiment as action
```

**Key design choice:** ExperimentBase uses composition (MadsciClientMixin), not inheritance from RestNode. Only ExperimentNode creates a RestNode internally when it needs server capabilities.

## ExperimentDesign vs Experiment

- **ExperimentDesign**: Template/blueprint. Defines experiment_name, description, resource_conditions. Reusable across runs. Can be loaded from YAML.
- **Experiment**: Runtime instance. Has experiment_id (ULID), status, timestamps, ownership. Created by `start_experiment_run()`.

```python
from madsci.common.types.experiment_types import ExperimentDesign

design = ExperimentDesign(
    experiment_name="Synthesis Optimization",
    experiment_description="Optimize reaction conditions for compound X",
)

# Or load from YAML
design = ExperimentDesign.from_yaml("experiment_design.yaml")
```

## ExperimentScript (Simplest Modality)

```python
from madsci.experiment_application.experiment_script import ExperimentScript
from madsci.common.types.experiment_types import ExperimentDesign

class SynthesisExperiment(ExperimentScript):
    experiment_design = ExperimentDesign(
        experiment_name="Synthesis Run",
        experiment_description="Automated synthesis workflow",
    )

    def run_experiment(self, sample_id: str = "default", cycles: int = 3) -> dict:
        """Core experiment logic. Called within manage_experiment() context."""
        results = []
        for i in range(cycles):
            result = self.workcell_client.run_workflow(
                "synthesis", parameters={"sample_id": sample_id, "cycle": i}
            )
            results.append(result)
            self.logger.info("Cycle completed", cycle=i, result=result)

        return {"sample_id": sample_id, "results": results}

if __name__ == "__main__":
    SynthesisExperiment.main(sample_id="ABC123", cycles=5)
```

**Entry points:**
- `run(*args, **kwargs)`: Instance method. Merges config args with passed args.
- `main(*args, **kwargs)`: Class method. Creates instance and calls `run()`.

**Config class:** `ExperimentScriptConfig` adds `run_args` and `run_kwargs` fields for CLI/env configuration.

## ExperimentNotebook (Jupyter)

Designed for cell-by-cell interactive use in Jupyter notebooks.

```python
# Cell 1: Setup
from my_experiment import MyNotebookExperiment
exp = MyNotebookExperiment()

# Cell 2: Start
exp.start(run_name="Exploration Run 1")

# Cell 3: Execute
result = exp.run_workflow("characterize", parameters={"sample": "S1"})

# Cell 4: Visualize
exp.display(result, title="Characterization Results")

# Cell 5: End
exp.end()
```

**Or use as context manager:**
```python
with MyNotebookExperiment() as exp:
    result = exp.run_workflow("synthesis")
    exp.display(result, title="Results")
```

**Key methods:**
- `start(run_name, run_description)`: Starts experiment, displays status. Returns `self`.
- `end(status)`: Ends experiment, displays summary. Returns `self`.
- `run_workflow(workflow_name, parameters, display_result)`: Convenience wrapper for `workcell_client.run_workflow()`.
- `display(data, title)`: Rich-formatted display (falls back to plain print).

**Config class:** `ExperimentNotebookConfig` adds `rich_output: bool = True` and `auto_display_results: bool = True`.

## ExperimentTUI (Terminal UI)

Interactive terminal interface with pause/cancel controls via Textual.

```python
from madsci.experiment_application.experiment_tui import ExperimentTUI
from madsci.common.types.experiment_types import ExperimentDesign

class OperatorExperiment(ExperimentTUI):
    experiment_design = ExperimentDesign(
        experiment_name="Operator-Assisted Synthesis",
    )

    def run_experiment(self) -> dict:
        results = []
        for step in range(10):
            self.check_experiment_status()  # Handles pause/cancel locally
            result = self.workcell_client.run_workflow("step", parameters={"n": step})
            results.append(result)
        return {"steps_completed": len(results)}

if __name__ == "__main__":
    OperatorExperiment().run_tui()
```

**Thread-safe controls:**
- `request_pause()` / `request_resume()` / `request_cancel()`: Called from TUI thread
- `check_experiment_status()`: Called in experiment thread. Uses `threading.Event` (no server round-trips). Raises `ExperimentCancelledError` if cancelled. Blocks while paused.

**Config class:** `ExperimentTUIConfig` adds `refresh_interval: float = 1.0` and `show_logs: bool = True`.

**Requires:** `pip install textual` (optional dependency).

## ExperimentNode (REST Server)

Exposes `run_experiment()` as a node action, controllable via the workcell manager.

```python
from madsci.experiment_application.experiment_node import ExperimentNode
from madsci.common.types.experiment_types import ExperimentDesign

class RemoteExperiment(ExperimentNode):
    experiment_design = ExperimentDesign(
        experiment_name="Remote Synthesis",
    )

    def run_experiment(self, sample_id: str, temperature: float = 25.0) -> dict:
        return self.workcell_client.run_workflow(
            "process", parameters={"sample_id": sample_id, "temp": temperature}
        )

if __name__ == "__main__":
    RemoteExperiment().start_server()
```

**Internals:** Creates a `RestNode` instance internally. Wraps `run_experiment` as a non-blocking action inside `manage_experiment()` context.

**Config class:** `ExperimentNodeConfig` adds `server_host: str = "0.0.0.0"`, `server_port: int = 6000`, `cors_enabled: bool = True`.

## Lifecycle and Context Manager

### `manage_experiment()` (Recommended)

```python
with self.manage_experiment(run_name="Run 1") as exp:
    # Experiment started, logging context established
    result = exp.workcell_client.run_workflow("my_workflow")
    # On success: end_experiment(COMPLETED) called automatically
    # On exception: handle_exception() called, then re-raised
```

The context manager:
1. Calls `start_experiment_run()` -> registers with Experiment Manager
2. Sets up hierarchical logging context (experiment_id, experiment_name, run_name, experiment_type)
3. Yields `self`
4. On success: `end_experiment(COMPLETED)`
5. On exception: `handle_exception()` then re-raises

### Manual lifecycle
```python
exp.start_experiment_run(run_name="Manual Run")
try:
    exp.run_experiment()
    exp.end_experiment(status=ExperimentStatus.COMPLETED)
except Exception as e:
    exp.handle_exception(e)
    raise
```

### Exception handling
Override `handle_exception()` for custom behavior:
```python
def handle_exception(self, exception: Exception) -> None:
    if isinstance(exception, RecoverableError):
        self.logger.warning("Recoverable error, retrying", error=str(exception))
        return  # Don't end experiment
    super().handle_exception(exception)  # Logs error + ends with FAILED
```

## ExperimentStatus

```python
class ExperimentStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"
```

## Exception Types

```python
from madsci.common.exceptions import (
    ExperimentCancelledError,    # Raised when experiment cancelled externally
    ExperimentFailedError,       # Raised when experiment fails externally
    ExperimentPauseTimeoutError, # Raised when pause exceeds max_pause_wait
)
```

## Client Access (via MadsciClientMixin)

All experiment modalities provide 7 lazy-initialized client properties:

```python
self.event_client       # EventClient - logging and events
self.logger             # Alias for event_client
self.resource_client    # ResourceClient - inventory
self.data_client        # DataClient - data storage
self.experiment_client  # ExperimentClient - experiment lifecycle
self.workcell_client    # WorkcellClient - workflow execution
self.location_client    # LocationClient - locations
self.lab_client         # LabClient - lab coordination
```

Clients are created on first access. URLs resolved from config or lab context (service discovery).

## Configuration

All configs inherit from `ExperimentBaseConfig` (`MadsciBaseSettings`, env prefix `EXPERIMENT_`):

```python
# Common fields (ExperimentBaseConfig):
lab_server_url: Optional[AnyUrl]         # Lab manager for service discovery
event_server_url: Optional[AnyUrl]       # Override Event Manager URL
experiment_server_url: Optional[AnyUrl]  # Override Experiment Manager URL
workcell_server_url: Optional[AnyUrl]    # Override Workcell Manager URL
data_server_url: Optional[AnyUrl]        # Override Data Manager URL
resource_server_url: Optional[AnyUrl]    # Override Resource Manager URL
location_server_url: Optional[AnyUrl]    # Override Location Manager URL
max_pause_wait: Optional[float]          # Max seconds to wait while paused (None = forever)
```

Config files searched via walk-up: `settings.yaml`, `experiment.settings.yaml`, `.env`, `experiment.env`.

## Creating Experiments from Templates

```bash
madsci new experiment
# Choose modality: script, notebook, tui, node
# Provide: experiment_name, description
```

Templates in `src/madsci_common/madsci/common/bundled_templates/experiment/`:
- `script/` -> `{name}.py`
- `notebook/` -> `{name}.ipynb`
- `tui/` -> `{name}_tui.py`
- `node/` -> `{name}_node.py`

## Checking Experiment Status (Pause/Cancel)

Call `check_experiment_status()` at natural checkpoints in long-running experiments:

```python
def run_experiment(self):
    for batch in batches:
        self.check_experiment_status()  # Blocks if paused, raises if cancelled
        process(batch)
```

**ExperimentTUI behavior:** Uses local `threading.Event` (no network calls).
**Other modalities:** Polls Experiment Manager with exponential backoff (5s -> 60s). Logs "Still waiting" every 5 minutes.

## Common Pitfalls

- **Override `run_experiment()`, not `run()`**: `run()` handles lifecycle; `run_experiment()` is your logic
- **Use `manage_experiment()` context manager**: Ensures proper start/end and exception handling
- **ULID not UUID**: Use `new_ulid_str()` for any IDs you generate
- **Notebook start/end**: Must call `start()` before `run_workflow()` and `end()` when done
- **TUI requires textual**: `pip install textual` or it raises ImportError
- **ExperimentApplication is deprecated**: Use the 4 modalities above instead (removal in v0.8.0)
- **Client URLs**: Set via config, env vars (`EXPERIMENT_EVENT_SERVER_URL`), or lab context (service discovery via `lab_server_url`)
- **AnyUrl trailing slash**: Pydantic's `AnyUrl` always adds a trailing slash
