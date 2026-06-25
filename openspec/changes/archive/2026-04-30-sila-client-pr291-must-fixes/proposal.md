## Why

Code review of PR #291 (`feat: add SilaNodeClient for native SiLA2 device integration`) flagged seven must-fix issues spanning correctness, security, and CI reliability. These need to land before the SiLA client merges so that (a) malicious or malformed `action_id`/response keys cannot escape the bytes-extraction directory, (b) `get_info` and short-form command resolution stop matching properties and SDK internals as commands, (c) operators get accurate error messages instead of every failure being labeled a "connection error", and (d) `validate_nb_sila` reliably exercises the full stack on a clean checkout instead of silently false-passing on infra timing or stale state.

## What Changes

- **Path-traversal hardening** in `_extract_bytes_files`: sanitize both `action_id` (subdirectory) and response `key` (filename) with a `_safe_path_component()` helper that uses `Path(...).name` and rejects empty/`.`/`..` values. Files always land inside `sila_files/<sanitized_id>/`.
- **Use SDK type checks for command introspection**: import `ClientObservableCommand` and `ClientUnobservableCommand` from `sila2.client.*`; replace `callable()` heuristics in `_resolve_sila_command` (both dotted and short form) and `get_info` with `isinstance(attr, _SILA_COMMAND_TYPES)`. Properties and SDK internals are correctly excluded.
- **Layered error classification in `send_action`**: split the single `try/except` into three blocks — connection (already enriched by `_get_sila_client`), command resolution, and command execution. Only the execution path enriches errors via `_format_connection_error`, and only when `_classify_connection_error` returns a recognized category (not `"unknown"`). Plain command/argument errors keep their original message.
- **Server startup exits non-zero** on bind failure (`__main__.py`): replace silent `return` with `sys.exit(1)` so docker / `depends_on` see the failure.
- **Healthcheck on `sila_example_server`** in compose: TCP socket probe on port 50052; `notebook_validator.depends_on.sila_example_server` requires `condition: service_healthy`. Convert the existing short-form `depends_on` list to long form (other deps default to `service_started`).
- **`validate_nb_sila` drops `--no-deps`** in `.justfile` so the recipe starts the SiLA server (and its transitive deps) automatically, matching `validate_nb_experiment`.
- **Tests**: add path-traversal coverage; assert `get_info` excludes properties; assert `_resolve_sila_command` rejects non-command callables; fix `test_unknown_action_returns_failed` to actually exercise the unknown-action path; update `test_send_action_enriched_error` and add tests asserting that command-resolution errors and arg errors are NOT enriched.

## Capabilities

### New Capabilities

(none — all changes refine existing behavior)

### Modified Capabilities

- `sila-command-execution`: bytes file extraction must sanitize path components (path-traversal hardening); command resolution (both dotted and short form) must use SiLA SDK command-type checks rather than `callable()`; `send_action` must classify errors into connection vs. resolution vs. execution and only enrich genuine connection failures.
- `sila-server-introspection`: `get_info` must enumerate only SiLA commands (not properties or arbitrary callables) using SDK command-type checks.
- `sila-example-server`: server startup failures must exit non-zero, and the compose service must expose a healthcheck so dependents can wait for `service_healthy`.
- `sila-notebook-validation`: `validate_nb_sila` must work end-to-end without prior `just up` and must wait for `sila_example_server` to be healthy before papermill runs (no `--no-deps`).

## Impact

- **Code**: `src/madsci_client/madsci/client/node/sila_node_client.py`, `src/madsci_client/tests/test_sila_node_client.py`, `examples/example_lab/example_modules/sila_example_server/__main__.py`, `examples/example_lab/compose.yaml`, `.justfile`.
- **APIs**: `send_action` error messages change shape — non-connection failures will no longer carry the `"SiLA connection error (...)"` prefix. Downstream string-matching on that prefix would break (none known).
- **Dependencies**: imports two additional symbols from the existing `sila2` SDK; no new packages.
- **CI**: `validate_nb_sila` will now bring up `sila_example_server` itself (longer wall-clock for that recipe in isolation; no change for `just all` which already brings everything up).
