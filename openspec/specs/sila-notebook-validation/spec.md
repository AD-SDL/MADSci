## ADDED Requirements

### Requirement: Notebook demonstrates all supported capabilities
The SiLA notebook SHALL exercise every capability marked as supported in `SilaNodeClient.supported_capabilities`: `get_info`, `get_status`, `get_state`, `send_action` (observable and unobservable), `get_action_status`, `get_action_result`, and `await_action_result`.

#### Scenario: Complete capability coverage
- **WHEN** the notebook is executed end-to-end
- **THEN** every supported SilaNodeClient method SHALL be called at least once with assertions on the results

### Requirement: Notebook validates via papermill
The notebook SHALL execute successfully via papermill with a 120-second per-cell timeout, producing no errors.

#### Scenario: CI validation
- **WHEN** `just validate_nb_sila` is run
- **THEN** papermill SHALL execute the notebook to completion with exit code 0

### Requirement: Justfile integration
The `validate_nb_sila` recipe SHALL be included in the `validate_notebooks` recipe so it runs as part of the standard notebook validation suite.

#### Scenario: Included in validate_notebooks
- **WHEN** `just validate_notebooks` is run
- **THEN** `validate_nb_sila` SHALL be executed alongside the other notebook validation recipes

### Requirement: Notebook is self-contained
The notebook SHALL only depend on the SiLA example server — not on the full manager stack. The `validate_nb_sila` justfile recipe SHALL explicitly start the `sila_example_server` service before running the notebook with `--no-deps`, and stop it afterwards.

#### Scenario: Minimal dependencies
- **WHEN** `validate_nb_sila` runs
- **THEN** the recipe SHALL start `sila_example_server` via `docker compose up -d`, run the notebook with `--no-deps`, and stop the server afterwards. No managers or infrastructure services SHALL be required.

### Requirement: Error handling demonstration
The notebook SHALL demonstrate error handling by showing what happens when a command fails or a server is unreachable.

#### Scenario: Connection error handling
- **WHEN** the notebook attempts to connect to a non-existent SiLA server
- **THEN** the resulting `NodeStatus` SHALL show `errored=True` and `disconnected=True`
