## 1. SiLA Example Server

- [x] 1.1 Create `examples/example_lab/example_modules/sila_example_server.py` implementing a SiLA2 server with: an unobservable `Greet` command, an observable `CountDown` command, a `ServerUptime` property, running on port 50052 in insecure mode
- [x] 1.2 Add `sila_example_server` service to `examples/example_lab/compose.yaml`, port 50052, using the `x-madsci-service` template
- [x] 1.3 Add `sila_example: sila://localhost:50052` to `workcell_nodes` in `examples/example_lab/settings.yaml` so it appears in the workcell manager and dashboard
- [x] 1.4 Verify the SiLA server starts and is connectable: `docker compose up sila_example_server`

## 2. SiLA Notebook

- [x] 2.1 Create `examples/notebooks/sila_node_notebook.ipynb` with sections: introduction, connecting to server, `get_info()`, `get_status()`, `get_state()`, unobservable `send_action()`, observable `send_action()` with await, observable polling (`get_action_status`/`get_action_result`), error handling
- [x] 2.2 Add assertions in each notebook cell to validate expected behavior (so papermill catches failures)

## 3. Justfile Integration

- [x] 3.1 Add `validate_nb_sila` recipe to `.justfile` that starts the SiLA server, runs the notebook via papermill, and stops the server
- [x] 3.2 Add `validate_nb_sila` to the `validate_notebooks` recipe dependency list

## 4. Verification

- [x] 4.1 Run `just validate_nb_sila` to confirm the notebook executes successfully via papermill
- [x] 4.2 Run `just validate_notebooks` to confirm no regressions in other notebook validations
