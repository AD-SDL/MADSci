## MODIFIED Requirements

### Requirement: Build NodeInfo from SiLA features via get_info
The SilaNodeClient SHALL introspect the SiLA server's implemented features and construct a `NodeInfo` with an `ActionDefinition` for each SiLA command. The client SHALL convert fully qualified identifiers returned by `SiLAService.ImplementedFeatures` (e.g., `"org.madsci/examples/ExampleDevice/v1"`) to short identifiers (e.g., `"ExampleDevice"`) for use as feature attribute names on the SiLA client object.

When enumerating attributes on each feature, `get_info()` SHALL include an attribute as an `ActionDefinition` only when it is a SiLA command instance — that is, an instance of `sila2.client.client_observable_command.ClientObservableCommand` or `sila2.client.client_unobservable_command.ClientUnobservableCommand`. Properties (e.g., `ClientObservableProperty`, `ClientUnobservableProperty`), bound helper methods, and SDK internals SHALL be excluded even if they are callable. Mere callability is NOT sufficient.

The SDK command base classes SHALL be imported once at module load alongside `SilaClient` and reused via the same `_SILA_COMMAND_TYPES` tuple referenced by `_resolve_sila_command`.

#### Scenario: Introspect server features
- **WHEN** `get_info()` is called
- **THEN** the client SHALL return a `NodeInfo` where `actions` contains an `ActionDefinition` for each SiLA command instance, keyed by `"FeatureName.CommandName"` using short feature identifiers

#### Scenario: Server name resolution
- **WHEN** `get_info()` is called and the SiLA server exposes `SiLAService.ServerName`
- **THEN** the `NodeInfo.node_name` SHALL be set to the server's name

#### Scenario: Properties excluded from actions
- **WHEN** a feature exposes both a SiLA command (e.g., `Greet` as `ClientUnobservableCommand`) and a SiLA property (e.g., `ServerUptime` as `ClientUnobservableProperty`)
- **THEN** `NodeInfo.actions` SHALL include `"FeatureName.Greet"` but NOT `"FeatureName.ServerUptime"`

#### Scenario: Non-command callables excluded from actions
- **WHEN** a feature exposes a callable attribute that is NOT a SiLA command instance (e.g., an SDK helper method, a property accessor)
- **THEN** the attribute SHALL NOT appear in `NodeInfo.actions`
