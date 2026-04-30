## MODIFIED Requirements

### Requirement: Execute unobservable SiLA commands
The SilaNodeClient SHALL accept an `ActionRequest` and execute the corresponding SiLA command on the connected SiLA2 server. For unobservable (synchronous) commands, the client SHALL return an `ActionResult` with status `SUCCEEDED` and the command's response fields in `json_result`. The `send_action` implementation SHALL classify failures into three layered categories so that diagnostic enrichment is applied only when appropriate:

1. **Connection failures** — raised by `_get_sila_client()`. These are already enriched by that helper and SHALL be returned to the caller without further wrapping. The original error message SHALL be preserved.
2. **Command-resolution and argument errors** — raised by `_resolve_sila_command()` or by `dict(action_request.args)`. These are NOT connection errors and SHALL NOT be wrapped with `_format_connection_error`. The `ActionResult.errors[0].message` SHALL be the original exception's `str(e)`.
3. **Command-execution errors** — raised by the underlying SiLA command call. The client SHALL invoke `_classify_connection_error(e)`; only when it returns a category other than `"unknown"` SHALL the error be wrapped with `_format_connection_error`. Otherwise the original exception message SHALL be returned unchanged.

In all three categories, `ActionResult.status` SHALL be `FAILED` and `errors[0].error_type` SHALL be `type(e).__name__`.

#### Scenario: Successful unobservable command
- **WHEN** `send_action()` is called with an `ActionRequest` whose `action_name` maps to an unobservable SiLA command
- **THEN** the client SHALL execute the command with `ActionRequest.args` as keyword arguments and return an `ActionResult` with `status=SUCCEEDED` and `json_result` containing the command's response fields as a dict

#### Scenario: Command execution failure with recognized connection category
- **WHEN** `send_action()` is called and the SiLA command raises an exception that `_classify_connection_error` recognizes (e.g., gRPC `RpcError`, `TimeoutError`, TLS error)
- **THEN** the client SHALL return an `ActionResult` with `status=FAILED` and the exception captured in `errors`, with the message wrapped by `_format_connection_error` (containing target host:port, TLS mode, and a hint)

#### Scenario: Command execution failure with unknown category
- **WHEN** `send_action()` is called and the SiLA command raises an exception that `_classify_connection_error` returns `"unknown"` for (e.g., a SiLA-defined execution error, a `ValueError` raised inside the command body)
- **THEN** the client SHALL return an `ActionResult` with `status=FAILED` and the original `str(e)` as the error message — without the `"SiLA connection error"` prefix

#### Scenario: Command resolution failure not enriched
- **WHEN** `send_action()` is called with an `action_name` that does not match any feature/command on the server
- **THEN** the client SHALL return an `ActionResult` with `status=FAILED` and the original `ValueError` message from `_resolve_sila_command` (e.g., `"SiLA command 'X' not found on any feature"`) — without the `"SiLA connection error"` prefix

#### Scenario: Connection failure during send_action
- **WHEN** `send_action()` is called and `_get_sila_client()` raises (e.g., the server is unreachable)
- **THEN** the client SHALL return an `ActionResult` with `status=FAILED` carrying the already-enriched message from `_get_sila_client` (no double-wrapping)

### Requirement: Resolve action names using dot notation
The client SHALL resolve `ActionRequest.action_name` to a SiLA Feature and Command. Qualified names (`"FeatureName.CommandName"`) SHALL be resolved directly and the resolved attribute MUST be a SiLA command instance — that is, an instance of `sila2.client.client_observable_command.ClientObservableCommand` or `sila2.client.client_unobservable_command.ClientUnobservableCommand`. Short-form names (`"CommandName"`) SHALL be searched across all features and resolved if unambiguous; only attributes that are SiLA command instances SHALL be considered. Mere callability is NOT sufficient — properties, helper methods, and SDK internals MUST be excluded even if they happen to be callable.

The two SDK command base classes SHALL be imported in the existing `try/except ImportError` block alongside `SilaClient`, and exposed via a module-level tuple `_SILA_COMMAND_TYPES` for use in `isinstance(...)` checks. When the SDK is not installed, the tuple SHALL be empty so `isinstance` returns `False` cleanly.

#### Scenario: Qualified action name resolves to SiLA command
- **WHEN** `action_name` is `"GreetingProvider.SayHello"` and `SayHello` is an instance of `ClientUnobservableCommand` (or `ClientObservableCommand`)
- **THEN** the client SHALL call the `SayHello` command on the `GreetingProvider` feature

#### Scenario: Qualified name resolves to a property
- **WHEN** `action_name` is `"GreetingProvider.ServerName"` and `ServerName` is a SiLA property (not a command instance)
- **THEN** the client SHALL raise a `ValueError` indicating the attribute is not a SiLA command

#### Scenario: Qualified name resolves to a non-command callable
- **WHEN** `action_name` is `"GreetingProvider.helper_method"` and the attribute is callable but is not a SiLA command instance (e.g., a SDK helper or hand-added method)
- **THEN** the client SHALL raise a `ValueError` indicating the attribute is not a SiLA command

#### Scenario: Unambiguous short-form action name
- **WHEN** `action_name` is `"SayHello"` and exactly one feature exposes a SiLA command attribute with that name
- **THEN** the client SHALL resolve and call the command on the correct feature

#### Scenario: Short-form ignores non-command callables
- **WHEN** `action_name` is `"SayHello"` and one feature exposes a `ClientUnobservableCommand` named `SayHello` while another feature exposes a non-command callable named `SayHello` (e.g., a property accessor or SDK internal)
- **THEN** the client SHALL resolve unambiguously to the command instance and ignore the non-command callable

#### Scenario: Ambiguous short-form action name
- **WHEN** `action_name` is `"DoStuff"` and multiple features expose SiLA command instances with that name
- **THEN** the client SHALL raise a `ValueError` listing the ambiguous features

#### Scenario: Unknown action name
- **WHEN** `action_name` does not match any SiLA command on any feature
- **THEN** the client SHALL raise a `ValueError` (surfaced by `send_action` as a non-enriched FAILED result per the layered classification above)

### Requirement: Map SiLA responses to ActionResult
The client SHALL convert SiLA command response objects to JSON-serializable dicts stored in `ActionResult.json_result`. The internal `_serialize_value()` function SHALL accept a single positional argument (the value to serialize) with no additional keyword arguments. Bytes values SHALL be converted to sentinel dicts for downstream extraction by `_extract_bytes_files()`. The `_extract_bytes_files()` function SHALL document that it only scans top-level keys of the response dict; nested bytes sentinels are not extracted.

`_extract_bytes_files()` SHALL sanitize every path component derived from external input before joining it onto the output directory. A helper `_safe_path_component(name)` SHALL:

- Reject `None`, empty strings, `"."`, and `".."` by raising `ValueError`.
- Reduce any other input to `Path(name).name` so embedded path separators (`/`, `\`) and parent-directory references are stripped.

This helper SHALL be applied to BOTH the `action_id` (which becomes the per-action subdirectory under `sila_files/`) AND every response dict `key` whose value is a bytes sentinel (which becomes the `<key>.bin` filename). The intent is that under no input — including a malicious server response — can the written file path escape `get_madsci_subdir("sila_files")/<sanitized_action_id>/`.

#### Scenario: Named response fields
- **WHEN** a SiLA command returns a response with named fields (e.g., `SayHello_Responses(Greeting="Hello")`)
- **THEN** `json_result` SHALL be `{"Greeting": "Hello"}`

#### Scenario: No response
- **WHEN** a SiLA command returns no response (void command)
- **THEN** `json_result` SHALL be `{}`

#### Scenario: _serialize_value signature
- **WHEN** `_serialize_value()` is called
- **THEN** it SHALL accept only the value to serialize and no `action_id` keyword argument

#### Scenario: _extract_bytes_files limitation documented
- **WHEN** a developer reads `_extract_bytes_files()`
- **THEN** a TODO comment SHALL note that only top-level keys are scanned and nested bytes sentinels are left in-place

#### Scenario: Malicious action_id sanitized
- **WHEN** `_extract_bytes_files()` is called with `action_id="../etc"` and a top-level bytes sentinel
- **THEN** the file SHALL be written under `get_madsci_subdir("sila_files")/etc/<key>.bin` — not under any parent directory — and `ActionFiles` SHALL reference that sanitized path

#### Scenario: Absolute path action_id sanitized
- **WHEN** `_extract_bytes_files()` is called with `action_id="/abs/path"`
- **THEN** the file SHALL be written under `get_madsci_subdir("sila_files")/path/<key>.bin` — the leading slash and `abs/` prefix SHALL be stripped

#### Scenario: Malicious response key sanitized
- **WHEN** the response contains a top-level key like `"../escaped"` whose value is a bytes sentinel
- **THEN** the file SHALL be written as `escaped.bin` inside the per-action subdirectory — never outside it

#### Scenario: Empty or dot-only path component rejected
- **WHEN** `_extract_bytes_files()` would derive an empty, `"."`, or `".."` path component from `action_id` or a response key
- **THEN** `_safe_path_component` SHALL raise `ValueError` and `_extract_bytes_files` SHALL propagate it (caught by `send_action`'s exception handling and surfaced as a FAILED result)
