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
The SilaNodeClient SHALL introspect the SiLA server's implemented features and construct a `NodeInfo` with an `ActionDefinition` for each SiLA command.

#### Scenario: Introspect server features
- **WHEN** `get_info()` is called
- **THEN** the client SHALL return a `NodeInfo` where `actions` contains an `ActionDefinition` for each command, keyed by `"FeatureName.CommandName"`

#### Scenario: Server name resolution
- **WHEN** `get_info()` is called and the SiLA server exposes `SiLAService.ServerName`
- **THEN** the `NodeInfo.node_name` SHALL be set to the server's name

### Requirement: Read SiLA properties via get_state
The SilaNodeClient SHALL read all SiLA property values from the server and return them as a flat dict.

#### Scenario: Read all properties
- **WHEN** `get_state()` is called
- **THEN** the client SHALL return a dict mapping `"FeatureName.PropertyName"` to the current property value for every readable property on the server

#### Scenario: Property read failure
- **WHEN** a specific property raises an error during reading
- **THEN** the client SHALL set that property's value to `None` in the returned dict and continue reading other properties

### Requirement: Declare supported capabilities
The SilaNodeClient SHALL declare its supported capabilities via the `supported_capabilities` class variable.

#### Scenario: Capabilities declaration
- **WHEN** `SilaNodeClient.supported_capabilities` is inspected
- **THEN** it SHALL report `send_action=True`, `get_info=True`, `get_status=True`, `get_state=True`, `get_action_status=True`, `get_action_result=True`, and `action_files=False`, `get_action_history=False`, `send_admin_commands=False`, `set_config=False`, `get_resources=False`, `get_log=False`
