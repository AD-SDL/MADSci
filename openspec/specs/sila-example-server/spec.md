## Purpose

Defines the example SiLA2 server bundled in the example lab — what features, commands, and properties it exposes for SilaNodeClient validation, and how it integrates with Docker Compose.
## Requirements
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

### Requirement: Server startup failure exits non-zero
The example SiLA server's `__main__` entry point SHALL exit with a non-zero status code when the server fails to start (e.g., port already in use, bind failure). A silent `return` SHALL NOT be used, since that exits 0 and causes Docker / `depends_on` to treat the failure as a healthy startup.

#### Scenario: Bind failure exits non-zero
- **WHEN** the server is launched with a port that cannot be bound (e.g., already in use, privileged port without permission)
- **THEN** the process SHALL exit with a non-zero status code (e.g., via `sys.exit(1)`) after logging the exception

#### Scenario: Successful startup keeps exit 0 path
- **WHEN** the server starts cleanly and is later terminated by SIGTERM or KeyboardInterrupt
- **THEN** the process SHALL exit with status 0 after running `server.stop()` and the shutdown log line

### Requirement: Compose service exposes a healthcheck
The `sila_example_server` Docker Compose service SHALL declare a `healthcheck` that probes the server's listening port (50052 by default) so that dependent services can wait for `condition: service_healthy` before starting work against it. The healthcheck SHALL use a Python-based TCP socket connect (e.g., `python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('localhost', 50052)); s.close()"`) since the base image does not guarantee `nc` and gRPC has no built-in HTTP health endpoint.

#### Scenario: Healthcheck transitions to healthy after startup
- **WHEN** `docker compose up sila_example_server` is run and the SiLA server has bound port 50052
- **THEN** the container's health status SHALL transition to `healthy` within the configured `start_period` + a few intervals

#### Scenario: Healthcheck stays unhealthy if startup fails
- **WHEN** the SiLA server fails to start (e.g., bind error → exit 1 per the requirement above)
- **THEN** the container SHALL not report `healthy`; the startup-failure exit code SHALL surface to `docker compose` so dependent services do not start
