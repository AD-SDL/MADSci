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
The SilaNodeClient SHALL support observable (long-running) SiLA commands. When `await_result=True`, the client SHALL block until the command completes and return the final result.

#### Scenario: Observable command with await
- **WHEN** `send_action()` is called with `await_result=True` and the SiLA command is observable
- **THEN** the client SHALL block until the command finishes (up to the configured timeout) and return an `ActionResult` with `status=SUCCEEDED` and the final response in `json_result`

#### Scenario: Observable command timeout
- **WHEN** `send_action()` is called with `await_result=True` and the observable command does not complete within the timeout
- **THEN** the client SHALL return an `ActionResult` with `status=FAILED` and a timeout error in `errors`

### Requirement: Execute observable SiLA commands without await
When `await_result=False`, the client SHALL return immediately with `status=RUNNING` and track the command instance for later retrieval.

#### Scenario: Observable command without await
- **WHEN** `send_action()` is called with `await_result=False` and the SiLA command is observable
- **THEN** the client SHALL return an `ActionResult` with `status=RUNNING` and store the observable instance internally keyed by `action_id`

### Requirement: Retrieve observable command status
The client SHALL allow querying the status of a previously dispatched observable command.

#### Scenario: Query running command status
- **WHEN** `get_action_status()` is called with an `action_id` of a tracked observable command
- **THEN** the client SHALL return the current `ActionStatus` (`RUNNING`, `SUCCEEDED`, or `FAILED`)

#### Scenario: Query unknown action_id
- **WHEN** `get_action_status()` is called with an `action_id` that is not tracked
- **THEN** the client SHALL return `ActionStatus.UNKNOWN`

### Requirement: Retrieve observable command result
The client SHALL allow retrieving the final result of a completed observable command.

#### Scenario: Retrieve completed command result
- **WHEN** `get_action_result()` is called for a completed observable command
- **THEN** the client SHALL return an `ActionResult` with the final response data and remove the instance from tracking

#### Scenario: Retrieve result of still-running command
- **WHEN** `get_action_result()` is called for a command still in progress
- **THEN** the client SHALL return an `ActionResult` with the current status (e.g., `RUNNING`) and no `json_result`

### Requirement: Await observable command result
The client SHALL support blocking until an observable command completes, with timeout and exponential backoff polling.

#### Scenario: Await completes successfully
- **WHEN** `await_action_result()` is called and the command completes before timeout
- **THEN** the client SHALL return the final `ActionResult` with `status=SUCCEEDED`

### Requirement: Resolve action names using dot notation
The client SHALL resolve `ActionRequest.action_name` to a SiLA Feature and Command. Qualified names (`"FeatureName.CommandName"`) SHALL be resolved directly. Short-form names (`"CommandName"`) SHALL be searched across all features and resolved if unambiguous.

#### Scenario: Qualified action name
- **WHEN** `action_name` is `"GreetingProvider.SayHello"`
- **THEN** the client SHALL call the `SayHello` command on the `GreetingProvider` feature

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
The client SHALL convert SiLA command response objects to JSON-serializable dicts stored in `ActionResult.json_result`.

#### Scenario: Named response fields
- **WHEN** a SiLA command returns a response with named fields (e.g., `SayHello_Responses(Greeting="Hello")`)
- **THEN** `json_result` SHALL be `{"Greeting": "Hello"}`

#### Scenario: No response
- **WHEN** a SiLA command returns no response (void command)
- **THEN** `json_result` SHALL be `{}`
