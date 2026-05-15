## MODIFIED Requirements

### Requirement: Notebook is self-contained
The notebook SHALL only depend on the SiLA example server — not on the full manager stack. The `validate_nb_sila` justfile recipe SHALL run via `docker compose run notebook_validator papermill ...` WITHOUT the `--no-deps` flag, so that Compose automatically starts `sila_example_server` (and its transitive dependencies) before papermill executes. The `notebook_validator.depends_on.sila_example_server` entry SHALL declare `condition: service_healthy` so papermill waits until the SiLA server's healthcheck reports healthy.

Rationale: previously the recipe used `--no-deps` and required a prior `just up`, which made `validate_nb_sila` silently false-pass on a clean checkout (the notebook would race startup or fail on a missing server). Removing `--no-deps` plus the healthcheck dependency makes the recipe self-sufficient and deterministic.

#### Scenario: Recipe brings up dependencies automatically
- **WHEN** `just validate_nb_sila` is run on a clean checkout (no prior `just up`)
- **THEN** Compose SHALL start `sila_example_server` (and any other declared dependencies of `notebook_validator`), wait for `sila_example_server` to be healthy, then run papermill

#### Scenario: Papermill waits for healthy SiLA server
- **WHEN** `notebook_validator` starts and `sila_example_server` is still in its `start_period`
- **THEN** papermill SHALL NOT begin executing the notebook until `sila_example_server`'s healthcheck transitions to `healthy`

#### Scenario: --no-deps absent from recipe
- **WHEN** the `validate_nb_sila` recipe is inspected
- **THEN** it SHALL NOT include `--no-deps` and SHALL match the structure of `validate_nb_experiment`
