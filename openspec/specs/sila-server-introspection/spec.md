## ADDED Requirements

### Requirement: Report node status via get_status
The SilaNodeClient SHALL report the SiLA server's connectivity and busy state as a `NodeStatus`.

#### Scenario: Connected and idle
- **WHEN** `get_status()` is called and the SiLA server is reachable with no running observable commands
- **THEN** the client SHALL return a `NodeStatus` with `busy=False`, `disconnected=False`, `errored=False`

#### Scenario: Connected and busy
- **WHEN** `get_status()` is called and there are tracked running observable commands
- **THEN** the client SHALL return a `NodeStatus` with `busy=True` and `running_actions` containing the active action IDs

#### Scenario: Server unreachable
- **WHEN** `get_status()` is called and the SiLA server cannot be reached
- **THEN** the client SHALL return a `NodeStatus` with `errored=True`, `disconnected=True`, and the connection error in `errors`

### Requirement: Build NodeInfo from SiLA features via get_info
The SilaNodeClient SHALL introspect the SiLA server's implemented features and construct a `NodeInfo` with an `ActionDefinition` for each SiLA command. The client SHALL convert fully qualified identifiers returned by `SiLAService.ImplementedFeatures` (e.g., `"org.madsci/examples/ExampleDevice/v1"`) to short identifiers (e.g., `"ExampleDevice"`) for use as feature attribute names on the SiLA client object.

#### Scenario: Introspect server features
- **WHEN** `get_info()` is called
- **THEN** the client SHALL return a `NodeInfo` where `actions` contains an `ActionDefinition` for each command, keyed by `"FeatureName.CommandName"` using short feature identifiers

#### Scenario: Server name resolution
- **WHEN** `get_info()` is called and the SiLA server exposes `SiLAService.ServerName`
- **THEN** the `NodeInfo.node_name` SHALL be set to the server's name

### Requirement: Populate ActionDefinition args from SiLA command parameters
Each `ActionDefinition` built by `get_info()` SHALL include an `ArgumentDefinition` for every SiLA command parameter, extracted from the command's `_wrapped_command.parameters.fields`. The client SHALL also set the `asynchronous` flag based on whether the SiLA command is observable.

#### Scenario: Command with parameters
- **WHEN** `get_info()` is called and a SiLA command has parameters (e.g., `Greet` with `Name: String`)
- **THEN** the corresponding `ActionDefinition.args` SHALL contain an `ArgumentDefinition` with `name` from `param._identifier`, `description` from `param._description`, `argument_type` from the SiLA data type class name (e.g., `"String"`, `"Integer"`, `"Real"`), and `required=True`

#### Scenario: Observable vs unobservable flag
- **WHEN** `get_info()` is called
- **THEN** `ActionDefinition.asynchronous` SHALL be `True` for observable commands and `False` for unobservable commands

### Requirement: Read SiLA properties via get_state
The SilaNodeClient SHALL read all SiLA property values from the server and return them as a flat dict. The property-detection heuristic (`hasattr(attr, "get") and not callable(attr)`) SHALL be documented with an inline comment explaining: (a) why this heuristic is used, (b) that it depends on SiLA SDK implementation details, and (c) that the `contextlib.suppress(Exception)` wrapper protects against misclassification.

#### Scenario: Read all properties
- **WHEN** `get_state()` is called
- **THEN** the client SHALL return a dict mapping `"FeatureName.PropertyName"` to the current property value for every readable property on the server

#### Scenario: Property read failure
- **WHEN** a specific property raises an error during reading
- **THEN** the client SHALL set that property's value to `None` in the returned dict and continue reading other properties

#### Scenario: Property detection heuristic documented
- **WHEN** a developer reads the `get_state()` method
- **THEN** an inline comment SHALL explain the property-detection heuristic, its SDK dependency, and the error-suppression safety net

### Requirement: Declare supported capabilities
The SilaNodeClient SHALL declare its supported capabilities via the `supported_capabilities` class variable.

#### Scenario: Capabilities declaration
- **WHEN** `SilaNodeClient.supported_capabilities` is inspected
- **THEN** it SHALL report `send_action=True`, `get_info=True`, `get_status=True`, `get_state=True`, `get_action_status=True`, `get_action_result=True`, and `action_files=False`, `get_action_history=False`, `send_admin_commands=False`, `set_config=False`, `get_resources=False`, `get_log=False`
