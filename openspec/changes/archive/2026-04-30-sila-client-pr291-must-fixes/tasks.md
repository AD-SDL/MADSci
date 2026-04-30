## 1. SDK type imports

- [x] 1.1 Extend the `try/except ImportError` block in `src/madsci_client/madsci/client/node/sila_node_client.py` to import `ClientObservableCommand` and `ClientUnobservableCommand` from `sila2.client.client_observable_command` and `sila2.client.client_unobservable_command`
- [x] 1.2 Define module-level `_SILA_COMMAND_TYPES: tuple = (ClientObservableCommand, ClientUnobservableCommand)` in the success branch and `_SILA_COMMAND_TYPES = ()` in the `ImportError` branch

## 2. Path-traversal hardening (issue #1)

- [x] 2.1 Add `_safe_path_component(name: str) -> str` helper in `sila_node_client.py` that returns `Path(name).name` and raises `ValueError` for `None`/empty/`.`/`..`
- [x] 2.2 Update `_extract_bytes_files()` to apply `_safe_path_component(action_id)` for the subdirectory and `_safe_path_component(key)` for each filename component
- [x] 2.3 Add tests in `src/madsci_client/tests/test_sila_node_client.py` (`TestExtractBytesFilesSafety` class):
  - [x] 2.3.1 `action_id="../etc"` writes file under `sila_files/etc/`, not above
  - [x] 2.3.2 `action_id="/abs/path"` writes file under `sila_files/path/`
  - [x] 2.3.3 Response key `"../escaped"` is sanitized to `escaped.bin` inside the per-action directory
  - [x] 2.3.4 `action_id` of `""`, `"."`, or `".."` raises `ValueError`
  - [x] 2.3.5 Response key of `""`, `"."`, or `".."` raises `ValueError`

## 3. Command-type isinstance refinement (issues #2, #3)

- [x] 3.1 In `_resolve_sila_command()` dotted-form branch, replace the `if not callable(command)` check with `if not isinstance(command, _SILA_COMMAND_TYPES)` and refine the error message to "not a SiLA command"
- [x] 3.2 In `_resolve_sila_command()` short-form loop, replace `if command is not None and callable(command)` with `if isinstance(command, _SILA_COMMAND_TYPES)`
- [x] 3.3 In `get_info()`, replace `if attr is not None and callable(attr)` with `if isinstance(attr, _SILA_COMMAND_TYPES)`
- [x] 3.4 Add tests in `test_sila_node_client.py`:
  - [x] 3.4.1 `_resolve_sila_command` short-form: feature exposes a non-command callable named `"X"` → raises "not found" (not selected)
  - [x] 3.4.2 `_resolve_sila_command` dotted-form: attribute exists and is callable but is not a `ClientObservableCommand`/`ClientUnobservableCommand` → raises ValueError ("not a SiLA command")
  - [x] 3.4.3 `_resolve_sila_command` short-form ambiguity: command instances on multiple features → raises with feature list
  - [x] 3.4.4 `_resolve_sila_command` short-form filter: one feature has a command instance, another has a same-named non-command callable → resolves to the command instance unambiguously
  - [x] 3.4.5 `get_info`: feature has both a `ClientObservableCommand` and a `ClientObservableProperty` → only the command appears in `actions`

## 4. Layered error classification in send_action (issue #4)

- [x] 4.1 Restructure `send_action()` in `sila_node_client.py` into three sequential `try/except` blocks: (A) `_get_sila_client()`, (B) `_resolve_sila_command()` + arg prep + log, (C) command invocation + result handling
- [x] 4.2 Block A: catch exception, log, return FAILED with the original (already-enriched) message — do NOT re-wrap
- [x] 4.3 Block B: catch exception, return FAILED with the original `str(e)` and `error_type=type(e).__name__` — no enrichment
- [x] 4.4 Block C: in the except branch, call `_classify_connection_error(e)`; only when the category is NOT `"unknown"` apply `_format_connection_error`; otherwise return FAILED with the original `str(e)`
- [x] 4.5 Update existing test `test_send_action_enriched_error` in `test_sila_node_client.py` (existing `ConnectionError("Connection refused")` still classifies as `connection_refused` so the test continues to assert the enriched format; supplemented by new `TestSendActionErrorLayering::test_recognized_execution_error_is_enriched` using `TimeoutError`)
- [x] 4.6 Fix existing `test_unknown_action_returns_failed`: set `mock_client.NonExistent = None` BEFORE calling `send_action`; assert the error message is the bare `_resolve_sila_command` ValueError text and does NOT contain `"SiLA connection error"`
- [x] 4.7 Add new test `test_send_action_arg_error_not_enriched` (in `TestSendActionErrorLayering`)
- [x] 4.8 Add new test `test_send_action_unknown_command_not_enriched` (in `TestSendActionErrorLayering`)
- [x] 4.9 Add new test `test_send_action_connection_failure_not_double_wrapped` (in `TestSendActionErrorLayering`)

## 5. Server startup exit code (issue #7)

- [x] 5.1 Add `import sys` to `examples/example_lab/example_modules/sila_example_server/__main__.py`
- [x] 5.2 Replace the bare `return` in the `except Exception:` block (currently `__main__.py:55-59`) with `sys.exit(1)` after `logger.exception(...)` and `server.stop()`

## 6. Compose healthcheck (issue #6)

- [x] 6.1 Add a `healthcheck:` block to `sila_example_server` in `examples/example_lab/compose.yaml` (test = Python TCP socket connect to `localhost:50052` with `timeout=2`; `interval: 5s`, `timeout: 3s`, `retries: 5`, `start_period: 5s`)
- [x] 6.2 Convert `notebook_validator.depends_on` from short-form list to long-form mapping
- [x] 6.3 Set `sila_example_server: { condition: service_healthy }` under `notebook_validator.depends_on`; leave other deps at `condition: service_started` to preserve current behavior
- [x] 6.4 Drop the `-vvv` flag from the `sila_example_server` command (now `-v` since the flag is `store_true`)

## 7. Justfile recipe cleanup (issue #5)

- [x] 7.1 Edit `validate_nb_sila` in `.justfile` to remove `--no-deps` so the recipe matches `validate_nb_experiment`'s structure

## 8. Verification

- [x] 8.1 `pytest src/madsci_client/tests/test_sila_node_client.py -v` — all 110 tests pass (was 86; added 24 new tests for path traversal, command-type filtering, error classification)
- [x] 8.2 Pre-commit (ruff check, ruff format, etc.) passes on all modified files
- [ ] 8.3 `just down && just build && just validate_nb_sila` from a clean checkout — papermill exits 0 (deferred — requires Docker stack rebuild; covered by CI on the PR)
- [ ] 8.4 Manual: launch `sila_example_server` with an in-use port → confirm container exits non-zero and the healthcheck reports unhealthy (deferred — covered by CI)
- [x] 8.5 Manual / scripted: confirmed via `TestSendActionErrorLayering::test_unknown_command_not_enriched` and `test_arg_error_not_enriched` that typo'd action names and arg errors return the bare error text, not the connection-error wrapper
- [x] 8.6 Manual: covered by `TestExtractBytesFilesSafety::test_action_id_with_parent_traversal_sanitized` — file lands under `sila_files/etc/k.bin`
