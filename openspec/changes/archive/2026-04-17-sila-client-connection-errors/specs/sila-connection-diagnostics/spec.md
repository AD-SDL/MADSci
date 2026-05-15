## ADDED Requirements

### Requirement: Connection errors SHALL include target host and port
All connection-related errors produced by `SilaNodeClient` SHALL include the target host and port in the error message.

#### Scenario: DNS resolution failure includes target
- **WHEN** `SilaNodeClient` encounters a DNS resolution failure connecting to host `my-sila-server` on port `50052`
- **THEN** the error message SHALL contain `my-sila-server` and `50052`

#### Scenario: Connection refused includes target
- **WHEN** `SilaNodeClient` encounters a connection refused error connecting to host `192.168.1.10` on port `50051`
- **THEN** the error message SHALL contain `192.168.1.10` and `50051`

### Requirement: Connection errors SHALL include TLS mode
All connection-related errors produced by `SilaNodeClient` SHALL indicate whether TLS was enabled or disabled for the attempted connection.

#### Scenario: Insecure connection error shows TLS disabled
- **WHEN** `SilaNodeClient` is configured with `insecure=True` and a connection error occurs
- **THEN** the error message SHALL indicate that TLS is disabled

#### Scenario: Secure connection error shows TLS enabled
- **WHEN** `SilaNodeClient` is configured with `insecure=False` and a connection error occurs
- **THEN** the error message SHALL indicate that TLS is enabled

### Requirement: Connection errors SHALL be classified by category
`SilaNodeClient` SHALL classify connection errors into one of the following categories: `dns_resolution`, `connection_refused`, `connection_timeout`, `tls_error`, `grpc_error`, or `unknown`.

#### Scenario: DNS failure classified
- **WHEN** a connection error with message containing "DNS resolution failed" is encountered
- **THEN** the error SHALL be classified as `dns_resolution`

#### Scenario: Connection refused classified
- **WHEN** a connection error with message containing "Connection refused" is encountered
- **THEN** the error SHALL be classified as `connection_refused`

#### Scenario: Timeout classified
- **WHEN** a `TimeoutError` or an error with message containing "Deadline exceeded" is encountered
- **THEN** the error SHALL be classified as `connection_timeout`

#### Scenario: TLS error classified
- **WHEN** a connection error with message containing "SSL", "TLS", or "certificate" is encountered
- **THEN** the error SHALL be classified as `tls_error`

#### Scenario: Unrecognized error falls back to unknown
- **WHEN** a connection error does not match any known category
- **THEN** the error SHALL be classified as `unknown` and the original exception message SHALL be preserved

### Requirement: Connection errors SHALL include diagnostic hints
Each classified connection error SHALL include a short diagnostic hint suggesting what the user should check or try next.

#### Scenario: DNS error provides hostname hint
- **WHEN** a `dns_resolution` error occurs
- **THEN** the error message SHALL include a hint to check the hostname spelling and DNS configuration

#### Scenario: Connection refused provides server-running hint
- **WHEN** a `connection_refused` error occurs
- **THEN** the error message SHALL include a hint to check that the SiLA server is running on the target host and port

#### Scenario: Timeout provides network hint
- **WHEN** a `connection_timeout` error occurs
- **THEN** the error message SHALL include a hint to check network connectivity and firewall rules

#### Scenario: TLS error provides certificate hint
- **WHEN** a `tls_error` occurs
- **THEN** the error message SHALL include a hint to verify TLS configuration, the `insecure` setting, and certificate path

### Requirement: Enriched errors SHALL apply consistently across client methods
The connection error enrichment SHALL apply in `_get_sila_client()`, `send_action()`, `get_status()`, `get_state()`, and `get_info()`.

#### Scenario: get_status returns enriched error on connection failure
- **WHEN** `get_status()` fails to connect to the SiLA server
- **THEN** the returned `NodeStatus.errors` list SHALL contain an `Error` with an enriched message including host, port, and diagnostic hint

#### Scenario: send_action returns enriched error on connection failure
- **WHEN** `send_action()` fails to connect to the SiLA server
- **THEN** the returned `ActionResult.errors` list SHALL contain an `Error` with an enriched message including host, port, and diagnostic hint

### Requirement: Original exception information SHALL be preserved
The enriched error message SHALL always include the original exception message, so no diagnostic information is lost.

#### Scenario: Original message preserved in enriched error
- **WHEN** a connection error with original message `"failed to connect to all addresses; last error: UNAVAILABLE"` is encountered
- **THEN** the enriched error message SHALL contain the original text `"failed to connect to all addresses; last error: UNAVAILABLE"`
