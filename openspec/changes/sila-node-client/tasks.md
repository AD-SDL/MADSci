## 1. Rename MadsciClientConfig to MadsciHttpClientConfig

- [x] 1.1 Rename `MadsciClientConfig` to `MadsciHttpClientConfig` in `src/madsci_common/madsci/common/types/client_types.py` and add backward-compat alias `MadsciClientConfig = MadsciHttpClientConfig`
- [x] 1.2 Update all subclasses to inherit from `MadsciHttpClientConfig`: `ExperimentClientConfig`, `DataClientConfig`, `LocationClientConfig`, `WorkcellClientConfig`, `ResourceClientConfig`, `LabClientConfig`, `RestNodeClientConfig` (in `client_types.py`), and `EventClientConfig` (in `event_types.py`)
- [x] 1.3 Update type annotations in `src/madsci_client/madsci/client/http.py`, `src/madsci_common/madsci/common/http_client.py`, and `src/madsci_common/madsci/common/utils.py` to use `MadsciHttpClientConfig`
- [x] 1.4 Update test files: `test_http_mixin.py`, `test_http_client.py`, `test_utils.py` to use `MadsciHttpClientConfig`
- [x] 1.5 Update `pyproject.toml` config export reference and `.env.example` comment

## 2. Dependencies and Configuration

- [x] 2.1 Add `unitelabs-sila` as optional dependency in `src/madsci_client/pyproject.toml` under `[project.optional-dependencies] sila = [...]`
- [x] 2.2 Add `SilaNodeClientConfig` to `src/madsci_common/madsci/common/types/client_types.py` with fields: `insecure`, `root_certs_path`, `command_timeout`, `poll_interval`, `poll_backoff_factor`, `max_poll_interval` (env prefix `SILA_NODE_CLIENT_`)

## 3. Core Client Implementation

- [x] 3.1 Create `src/madsci_client/madsci/client/node/sila_node_client.py` with import guard (`SILA2_AVAILABLE` sentinel), `_parse_sila_url()` helper, and `SilaNodeClient` class skeleton inheriting `AbstractNodeClient` with `url_protocols = ["sila"]` and capabilities declaration
- [x] 3.2 Implement `_resolve_sila_command()` helper: resolve dot-notation (`"Feature.Command"`) and short-form (`"Command"`) action names to SiLA feature+command callables
- [x] 3.3 Implement `_response_to_dict()` helper: convert SiLA namedtuple-like response objects to JSON-serializable dicts
- [x] 3.4 Implement `send_action()`: execute SiLA commands, detect observable vs unobservable, handle `await_result` flag, track observable instances in `_running_commands`
- [x] 3.5 Implement `get_action_status()`, `get_action_result()`, and `await_action_result()`: poll/retrieve tracked observable command state with exponential backoff

## 4. Server Introspection

- [x] 4.1 Implement `get_status()`: probe SiLA server connectivity via `ImplementedFeatures`, report `NodeStatus` with busy/disconnected/errored flags
- [x] 4.2 Implement `get_info()`: introspect SiLA features and commands, build `NodeInfo` with `ActionDefinition` entries keyed by `"Feature.Command"`
- [x] 4.3 Implement `get_state()`: iterate all SiLA features, read property values, return as `{"Feature.Property": value}` dict
- [x] 4.4 Implement `close()`: cleanup SiLA client connection and tracked commands

## 5. Registration and Dispatch

- [x] 5.1 Edit `src/madsci_client/madsci/client/node/__init__.py` to conditionally register `SilaNodeClient` in `NODE_CLIENT_MAP` when `unitelabs-sila` is available

## 6. Tests

- [x] 6.1 Create `src/madsci_client/tests/test_sila_node_client.py` with tests for: import guard, URL validation, URL parsing, action name resolution, response-to-dict conversion
- [x] 6.2 Add tests for `send_action()`: unobservable success, observable with await, observable without await, command failure
- [x] 6.3 Add tests for `get_action_status()`, `get_action_result()`: running/completed/unknown states
- [x] 6.4 Add tests for `get_status()`, `get_info()`, `get_state()`: connected/disconnected, feature introspection, property reading
- [x] 6.5 Add tests for NODE_CLIENT_MAP conditional registration and `find_node_client()` dispatch

## 7. Verification

- [x] 7.1 Run full test suite (`pytest`) to verify no regressions
- [x] 7.2 Run linter (`ruff check`) on all new and modified files
