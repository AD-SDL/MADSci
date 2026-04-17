## ADDED Requirements

### Requirement: Execute unobservable SiLA commands
The SilaNodeClient SHALL accept an `ActionRequest` and execute the corresponding SiLA command on the connected SiLA2 server. For unobservable (synchronous) commands, the client SHALL return an `ActionResult` with status `SUCCEEDED` and the command's response fields in `json_result`.

#### Scenario: Successful unobservable command
- **WHEN** `send_action()` is called with an `ActionRequest` whose `action_name` maps to an unobservable SiLA command
- **THEN** the client SHALL execute the command with `ActionRequest.args` as keyword arguments and return an `ActionResult` with `status=SUCCEEDED` and `json_result` containing the command's response fields as a dict

#### Scenario: Command execution failure
- **WHEN** `send_action()` is called and the SiLA command raises an exception
- **THEN** the client SHALL return an `ActionResult` with `status=FAILED` and the exception captured in `errors`

### Requirement: Execute observable SiLA commands with await
The SilaNodeClient SHALL support observable (long-running) SiLA commands. When `await_result=True`, the client SHALL poll `instance.done` with exponential backoff until the command completes, then call `instance.get_responses()` to retrieve the result. Note: the sila2 SDK's `get_responses()` is non-blocking and raises `CommandExecutionNotFinished` if called before completion — the client MUST poll rather than block.

#### Scenario: Observable command with await
- **WHEN** `send_action()` is called with `await_result=True` and the SiLA command is observable
- **THEN** the client SHALL poll `instance.done` until `True` (up to the configured timeout), then return an `ActionResult` with `status=SUCCEEDED` and the final response in `json_result`

#### Scenario: Observable command timeout
- **WHEN** `send_action()` is called with `await_result=True` and the observable command does not complete within the timeout
- **THEN** the client SHALL return an `ActionResult` with `status=FAILED` and a timeout error in `errors`

### Requirement: Execute observable SiLA commands without await
When `await_result=False`, the client SHALL return immediately with `status=RUNNING` and track the command instance for later retrieval.

#### Scenario: Observable command without await
- **WHEN** `send_action()` is called with `await_result=False` and the SiLA command is observable
- **THEN** the client SHALL return an `ActionResult` with `status=RUNNING` and store the observable instance internally keyed by `action_id`

### Requirement: Retrieve observable command status
The client SHALL allow querying the status of a previously dispatched observable command by checking `instance.done` and `instance.status`.

#### Scenario: Query running command status
- **WHEN** `get_action_status()` is called with an `action_id` of a tracked observable command where `instance.done` is `False`
- **THEN** the client SHALL return `ActionStatus.RUNNING`

#### Scenario: Query unknown action_id
- **WHEN** `get_action_status()` is called with an `action_id` that is not tracked
- **THEN** the client SHALL return `ActionStatus.UNKNOWN`

### Requirement: Retrieve observable command result
The client SHALL allow retrieving the final result of a completed observable command. When the command has FAILED (as determined by `get_action_status`), the returned `ActionResult` SHALL have `status=FAILED`, not `SUCCEEDED`.

#### Scenario: Retrieve completed command result
- **WHEN** `get_action_result()` is called for a completed observable command where `get_action_status` returns `SUCCEEDED`
- **THEN** the client SHALL return an `ActionResult` with `status=SUCCEEDED`, the final response data in `json_result`, and remove the instance from tracking

#### Scenario: Retrieve result of still-running command
- **WHEN** `get_action_result()` is called for a command still in progress
- **THEN** the client SHALL return an `ActionResult` with the current status (e.g., `RUNNING`) and no `json_result`

#### Scenario: Retrieve result of failed command
- **WHEN** `get_action_result()` is called for a completed observable command where `get_action_status` returns `FAILED`
- **THEN** the client SHALL return an `ActionResult` with `status=FAILED`, attempt to retrieve any partial responses via `get_responses()`, and remove the instance from tracking

#### Scenario: Retrieve result of failed command when get_responses raises
- **WHEN** `get_action_result()` is called for a FAILED command and `get_responses()` raises an exception
- **THEN** the client SHALL return an `ActionResult` with `status=FAILED`, the exception captured in `errors`, and remove the instance from tracking

### Requirement: Await observable command result
The client SHALL support blocking until an observable command completes, polling `instance.done` with timeout and exponential backoff.

#### Scenario: Await completes successfully
- **WHEN** `await_action_result()` is called and the command completes before timeout
- **THEN** the client SHALL return the final `ActionResult` with `status=SUCCEEDED`

### Requirement: Resolve action names using dot notation
The client SHALL resolve `ActionRequest.action_name` to a SiLA Feature and Command. Qualified names (`"FeatureName.CommandName"`) SHALL be resolved directly and the resolved attribute MUST be callable. Short-form names (`"CommandName"`) SHALL be searched across all features and resolved if unambiguous; only callable attributes SHALL be considered.

#### Scenario: Qualified action name
- **WHEN** `action_name` is `"GreetingProvider.SayHello"` and `SayHello` is callable
- **THEN** the client SHALL call the `SayHello` command on the `GreetingProvider` feature

#### Scenario: Qualified name resolves to non-callable attribute
- **WHEN** `action_name` is `"GreetingProvider.ServerName"` and `ServerName` is a SiLA property (not callable)
- **THEN** the client SHALL raise a `ValueError` indicating the attribute is not a callable command

#### Scenario: Unambiguous short-form action name
- **WHEN** `action_name` is `"SayHello"` and only one feature exposes that command
- **THEN** the client SHALL resolve and call the command on the correct feature

#### Scenario: Ambiguous short-form action name
- **WHEN** `action_name` is `"DoStuff"` and multiple features expose that command
- **THEN** the client SHALL raise a `ValueError` listing the ambiguous features

#### Scenario: Unknown action name
- **WHEN** `action_name` does not match any command on any feature
- **THEN** the client SHALL return an `ActionResult` with `status=FAILED` and an appropriate error

### Requirement: Map SiLA responses to ActionResult
The client SHALL convert SiLA command response objects to JSON-serializable dicts stored in `ActionResult.json_result`. The internal `_serialize_value()` function SHALL accept a single positional argument (the value to serialize) with no additional keyword arguments. Bytes values SHALL be converted to sentinel dicts for downstream extraction by `_extract_bytes_files()`. The `_extract_bytes_files()` function SHALL document that it only scans top-level keys of the response dict; nested bytes sentinels are not extracted.

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

### Requirement: Document private SiLA SDK attribute usage
The functions `_extract_argument_definitions` and `_is_command_observable` access private attributes of the `sila2` SDK (`_wrapped_command`, `_identifier`, `_description`) and rely on class naming conventions. These usages SHALL be documented with inline comments explaining: (a) what private attribute is accessed, (b) why there is no public API alternative, and (c) how the code degrades gracefully when the attributes are absent or change.

#### Scenario: Private attribute documentation present
- **WHEN** a developer reads `_extract_argument_definitions` or `_is_command_observable`
- **THEN** inline comments SHALL explain the private attribute usage, rationale, and degradation strategy
