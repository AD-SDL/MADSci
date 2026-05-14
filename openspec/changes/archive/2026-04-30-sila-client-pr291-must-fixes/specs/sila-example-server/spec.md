## ADDED Requirements

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
