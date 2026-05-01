## Why

The SilaNodeClient was just added to MADSci but there's no working example showing how to use it. Users need a concrete, runnable demonstration of connecting to a SiLA2 server, sending commands, reading properties, and checking status — all validated in CI to prevent documentation rot.

## What Changes

- Add a standalone SiLA2 example server (`examples/example_lab/example_modules/sila_example_server.py`) that implements a simple Feature with observable and unobservable commands plus properties
- Add the SiLA server as a service in the example lab's Docker Compose, registered in `settings.yaml` as a workcell node (`sila://localhost:50052`) so it appears in the workcell manager and dashboard
- Add a Jupyter notebook (`examples/notebooks/sila_node_notebook.ipynb`) demonstrating all supported SilaNodeClient capabilities
- Add a `validate_nb_sila` recipe to the justfile and include it in `validate_notebooks`

## Capabilities

### New Capabilities
- `sila-example-server`: A minimal SiLA2 server for demonstration and testing, implementing commands and properties that exercise the SilaNodeClient's supported capabilities
- `sila-notebook-validation`: A Jupyter notebook exercising the SilaNodeClient against the example server, validated via papermill as part of the CI notebook checks

### Modified Capabilities
_(none)_

## Impact

- **Code**: New files in `examples/` only — no changes to library source code
- **Docker**: New service in `compose.yaml` for the SiLA example server
- **CI**: `validate_notebooks` justfile recipe gains a new `validate_nb_sila` step
- **Dependencies**: The example lab container needs `sila2` installed (already available via the `[sila]` extra)
