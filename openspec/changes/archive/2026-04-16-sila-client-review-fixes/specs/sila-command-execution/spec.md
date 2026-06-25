## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Document private SiLA SDK attribute usage
The functions `_extract_argument_definitions` and `_is_command_observable` access private attributes of the `sila2` SDK (`_wrapped_command`, `_identifier`, `_description`) and rely on class naming conventions. These usages SHALL be documented with inline comments explaining: (a) what private attribute is accessed, (b) why there is no public API alternative, and (c) how the code degrades gracefully when the attributes are absent or change.

#### Scenario: Private attribute documentation present
- **WHEN** a developer reads `_extract_argument_definitions` or `_is_command_observable`
- **THEN** inline comments SHALL explain the private attribute usage, rationale, and degradation strategy
