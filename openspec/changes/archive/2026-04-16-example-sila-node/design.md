## Context

The example lab at `examples/example_lab/` has 5 REST-based example nodes (liquidhandler x2, robotarm, platereader, advanced_example). Notebooks in `examples/notebooks/` demonstrate REST node usage, experiments, and backups — all validated via `just validate_notebooks` using papermill in Docker.

The SilaNodeClient (`src/madsci_client/madsci/client/node/sila_node_client.py`) supports: `send_action` (observable + unobservable), `get_info`, `get_status`, `get_state`, `get_action_status`, `get_action_result`, `await_action_result`. We need an example server and notebook that exercises all of these.

## Goals / Non-Goals

**Goals:**
- Provide a working SiLA2 server that exercises every supported SilaNodeClient capability
- Create a notebook that serves as both documentation and CI-validated example
- Integrate into the existing example lab Docker Compose and validation pipeline

**Non-Goals:**
- Not a production SiLA instrument driver — just a demonstration server
- Not integrating the SiLA node into workcell workflows (no workflow YAML)
- Not CI-testing the dashboard integration (manual verification only)

## Decisions

### 1. SiLA server implementation: use the sila2 SDK's server API

Build a minimal SiLA2 server using `sila2.server.SilaServer` with a custom Feature containing:
- **Unobservable command** (`Greet`): takes a name parameter, returns a greeting — demonstrates basic send_action
- **Observable command** (`CountDown`): takes a count, emits intermediate responses, finishes — demonstrates observable tracking, await, and polling
- **Unobservable property** (`ServerUptime`): returns seconds since start — demonstrates get_state
- **Observable property** (`CurrentTime`): streams current time — demonstrates property subscription detection in get_state

This covers all supported SilaNodeClient capabilities with minimal complexity.

### 2. Docker Compose service and workcell registration

Add the SiLA server as a Docker service in `compose.yaml` (no profile restriction — it's a regular node like the REST ones). Port 50052 (SiLA default). Uses the same `x-madsci-service` template as other nodes.

Register it in `settings.yaml` under `workcell_nodes` as `sila_example: sila://localhost:50052` so it appears in the workcell manager and is visible on the dashboard alongside the REST nodes. This exercises the full `find_node_client()` dispatch path with a `sila://` URL in production-like configuration.

### 3. Notebook structure mirrors node_notebook.ipynb

Follow the pattern of the existing `node_notebook.ipynb`:
1. Introduction to SiLA2 and the SilaNodeClient
2. Connecting to a SiLA server
3. Server introspection (`get_info`, `get_status`)
4. Reading properties (`get_state`)
5. Sending unobservable commands (`send_action`)
6. Sending observable commands with `await_result=True`
7. Sending observable commands with `await_result=False` + polling
8. Error handling

### 4. Justfile recipe: `validate_nb_sila`

Add a new recipe that starts the SiLA server service and runs the notebook. Include in `validate_notebooks`. Use `--no-deps` since the SiLA notebook doesn't need the full manager stack — just the SiLA server.

## Risks / Trade-offs

- **sila2 SDK server API may differ across versions** → Pin to same version as client dependency (`>=0.10.0`). Test during implementation.
- **SiLA server adds container to example lab** → Mitigated by using `profiles` so it only runs when needed.
- **Notebook cell timeouts** → Observable commands should complete within the 120s papermill timeout. Keep countdown values small (3-5 seconds).
