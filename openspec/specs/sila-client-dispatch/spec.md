## ADDED Requirements

### Requirement: Register sila URL scheme
The SilaNodeClient SHALL declare `url_protocols = ["sila"]` so that the existing `find_node_client()` dispatch mechanism routes `sila://` URLs to it. The `validate_url` class method SHALL accept a `url: AnyUrl` parameter matching the parent `AbstractNodeClient.validate_url` signature.

#### Scenario: URL validation accepts sila scheme
- **WHEN** `SilaNodeClient.validate_url()` is called with a `sila://host:port` `AnyUrl`
- **THEN** it SHALL return `True`

#### Scenario: URL validation rejects non-sila schemes
- **WHEN** `SilaNodeClient.validate_url()` is called with an `http://` or `https://` `AnyUrl`
- **THEN** it SHALL return `False`

#### Scenario: Type signature matches parent class
- **WHEN** static analysis checks `SilaNodeClient.validate_url` against `AbstractNodeClient.validate_url`
- **THEN** the parameter type SHALL be `AnyUrl`, consistent with the parent class

### Requirement: Conditional registration in NODE_CLIENT_MAP
The SilaNodeClient SHALL be registered in `NODE_CLIENT_MAP` only when the `sila2` package is installed. When the package is not installed, the registration SHALL be silently skipped and other node clients SHALL remain unaffected.

#### Scenario: Registration with sila2 installed
- **WHEN** the `sila2` package is importable
- **THEN** `NODE_CLIENT_MAP` SHALL contain `"sila_node_client": SilaNodeClient`

#### Scenario: Registration without sila2 installed
- **WHEN** the `sila2` package is not importable
- **THEN** `NODE_CLIENT_MAP` SHALL not contain a `sila_node_client` entry and no `ImportError` SHALL be raised

### Requirement: Workcell dispatch for sila URLs
The existing `find_node_client()` function SHALL return a `SilaNodeClient` instance when given a `sila://` URL, with no changes to the dispatch function itself.

#### Scenario: Dispatch sila URL
- **WHEN** `find_node_client("sila://192.168.1.100:50052")` is called and `SilaNodeClient` is registered
- **THEN** it SHALL return a `SilaNodeClient` instance connected to host `192.168.1.100` port `50052`

### Requirement: Parse sila URL into host and port
The client SHALL parse `sila://host:port` URLs, defaulting to port `50052` when no port is specified.

#### Scenario: URL with explicit port
- **WHEN** the client is constructed with `sila://192.168.1.100:50055`
- **THEN** it SHALL connect to host `192.168.1.100` on port `50055`

#### Scenario: URL without port
- **WHEN** the client is constructed with `sila://myhost`
- **THEN** it SHALL connect to host `myhost` on port `50052`

### Requirement: Clear error when sila2 not installed
If a user attempts to construct a `SilaNodeClient` but the `sila2` package is not installed, the client SHALL raise an `ImportError` with installation instructions.

#### Scenario: Construction without sila2
- **WHEN** `SilaNodeClient(url="sila://localhost:50052")` is called and `unitelabs-sila` is not installed
- **THEN** an `ImportError` SHALL be raised with a message containing installation instructions

### Requirement: SiLA client configuration
The `SilaNodeClientConfig` SHALL provide SiLA-specific connection settings separate from HTTP client configuration.

#### Scenario: Default insecure connection
- **WHEN** `SilaNodeClientConfig` is instantiated with defaults
- **THEN** `insecure` SHALL be `True` (no TLS)

#### Scenario: TLS configuration
- **WHEN** `SilaNodeClientConfig` is instantiated with `insecure=False` and `root_certs_path` set
- **THEN** the client SHALL use the provided certificates for TLS verification

#### Scenario: Environment variable override
- **WHEN** `SILA_NODE_CLIENT_INSECURE=false` is set in the environment
- **THEN** `SilaNodeClientConfig().insecure` SHALL be `False`
