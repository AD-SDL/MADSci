## Why

Connection errors in `SilaNodeClient` currently surface generic exception messages (e.g., `str(e)` from gRPC errors), which often lack actionable context like the target host/port, whether the issue is a DNS failure vs. connection refused vs. TLS mismatch, or what the user should try next. This makes debugging SiLA node connectivity issues unnecessarily difficult, especially in multi-node lab environments.

## What Changes

- Enrich connection error messages in `SilaNodeClient` with structured context: target host, port, TLS mode, and error classification (DNS, refused, timeout, TLS, gRPC-specific).
- Add diagnostic hints to error messages suggesting common fixes (e.g., "check that the SiLA server is running", "verify TLS certificate path").
- Ensure `get_status()`, `send_action()`, and `_get_sila_client()` all produce consistently detailed error information when connections fail.
- Include connection metadata in event log entries for connection failures.

## Capabilities

### New Capabilities
- `sila-connection-diagnostics`: Classify and enrich SiLA connection errors with structured context (host, port, TLS config, error category) and actionable diagnostic hints.

### Modified Capabilities

## Impact

- **Code**: `src/madsci_client/madsci/client/node/sila_node_client.py` — error handling in `_get_sila_client()`, `send_action()`, `get_status()`, `get_state()`, `get_info()`.
- **Types**: `src/madsci_common/madsci/common/types/base_types.py` — may add optional structured fields to `Error` if needed.
- **Tests**: `src/madsci_client/tests/test_sila_node_client.py` — new/updated tests for enriched error messages.
- **Dependencies**: No new dependencies. Uses existing gRPC exception types from `grpc` and `sila2` packages.
