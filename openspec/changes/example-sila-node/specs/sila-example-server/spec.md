## ADDED Requirements

### Requirement: Unobservable command support
The example SiLA server SHALL implement at least one unobservable command that accepts parameters and returns a response, to demonstrate `SilaNodeClient.send_action()` with synchronous execution.

#### Scenario: Execute unobservable command
- **WHEN** a SiLA client sends a `Greet` command with a `Name` parameter
- **THEN** the server SHALL return a response containing a greeting string

### Requirement: Observable command support
The example SiLA server SHALL implement at least one observable command that runs for a configurable duration, to demonstrate observable command tracking and polling.

#### Scenario: Execute observable command
- **WHEN** a SiLA client sends a `CountDown` command with a `Count` parameter
- **THEN** the server SHALL execute for approximately `Count` seconds, providing status updates, and return a completion response

### Requirement: Property support
The example SiLA server SHALL expose at least one readable property to demonstrate `SilaNodeClient.get_state()`.

#### Scenario: Read server property
- **WHEN** a SiLA client reads the `ServerUptime` property
- **THEN** the server SHALL return the number of seconds since the server started

### Requirement: SiLAService feature
The example SiLA server SHALL implement the standard SiLAService feature so that `SilaNodeClient.get_info()` can discover all available features and commands.

#### Scenario: Feature discovery
- **WHEN** a SiLA client queries `SiLAService.ImplementedFeatures`
- **THEN** the server SHALL return a list containing the example feature identifier

### Requirement: Docker Compose integration
The example SiLA server SHALL be runnable as a Docker Compose service in the example lab as a regular service (no profile restriction), registered in `settings.yaml` under `workcell_nodes` so it appears on the dashboard.

#### Scenario: Start via Docker Compose
- **WHEN** `docker compose up sila_example_server` is run
- **THEN** the server SHALL start and listen on port 50052

### Requirement: Insecure mode with discovery disabled
The example SiLA server SHALL run without TLS and with SiLA Server Discovery (zeroconf) disabled, since zeroconf does not work in Docker's host network mode.

#### Scenario: Connect without TLS
- **WHEN** `SilaNodeClient` connects with `insecure=True`
- **THEN** the connection SHALL succeed without certificate configuration

#### Scenario: Docker hostname resolution
- **WHEN** the server runs in a Docker container with host network mode
- **THEN** the server SHALL start with `--disable-discovery` to avoid zeroconf hostname resolution failures
