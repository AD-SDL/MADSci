## Context

`SilaNodeClient` wraps gRPC-based SiLA 2 communication. When connections fail, the raw exceptions from `grpc` and `sila2` surface as generic messages like `"failed to connect to all addresses"` or `"DNS resolution failed"`. In a lab with multiple SiLA nodes, operators need to quickly identify *which* node failed, *why* it failed, and *what to try next*. Currently, error messages lack the target host/port, don't classify the failure type, and provide no remediation hints.

The `Error` model (`base_types.py`) already captures `message` and `error_type` but nothing structured about connection context.

## Goals / Non-Goals

**Goals:**
- Classify connection errors into actionable categories (DNS, refused, timeout, TLS, gRPC)
- Include target host, port, and TLS mode in all connection error messages
- Provide short diagnostic hints suggesting next steps
- Apply consistently across `_get_sila_client()`, `send_action()`, `get_status()`, `get_state()`, and `get_info()`

**Non-Goals:**
- Automatic retry or reconnection logic (separate concern)
- Modifying the `Error` base model schema (keep changes localized to SiLA client)
- Health-check or ping infrastructure
- Handling non-connection errors (command failures, serialization issues, etc.)

## Decisions

### 1. Error classification via a helper function, not custom exception classes

Add a `_classify_connection_error(exception, host, port, insecure)` helper function in `sila_node_client.py` that inspects the exception type and message to return a structured error string.

**Rationale**: Custom exception classes would add complexity and require changes across consumers. A helper function keeps the change localized to the SiLA client module while producing rich error messages. The function returns an enriched `Error` object rather than raising a new exception, fitting the existing pattern where `SilaNodeClient` never raises on connection failures.

**Alternatives considered**:
- Custom exception hierarchy — rejected: over-engineering for enriched messages, and `SilaNodeClient` doesn't raise exceptions anyway.
- Adding fields to the `Error` model — rejected: would affect all error consumers for a SiLA-specific concern.

### 2. Error categories

Classify errors based on exception type and message content:

| Category | Detection | Hint |
|----------|-----------|------|
| `dns_resolution` | `"DNS resolution failed"` or `"Name resolution failure"` in message | Check hostname spelling and DNS configuration |
| `connection_refused` | `"Connection refused"` or `"connect failed"` in message | Check that the SiLA server is running on the target host/port |
| `connection_timeout` | `TimeoutError` or `"Deadline exceeded"` in message | Check network connectivity and firewall rules |
| `tls_error` | `"SSL"`, `"TLS"`, `"certificate"` in message | Check TLS configuration; verify `insecure` setting and certificate path |
| `grpc_error` | gRPC status codes from `grpc.RpcError` | Include gRPC status code and details |
| `unknown` | Fallback | Include full exception message |

**Rationale**: These categories cover the common SiLA/gRPC failure modes. Detection via string matching is pragmatic — gRPC doesn't always use typed exceptions for connection-level failures.

### 3. Consistent error format

All enriched connection errors follow this template:
```
SiLA connection error ({category}): {original_message}
  Target: {host}:{port} (TLS: {enabled|disabled})
  Hint: {diagnostic_hint}
```

**Rationale**: A predictable format makes errors grep-able in logs and easy to parse visually. Including the target and TLS mode in every connection error eliminates the most common debugging questions.

## Risks / Trade-offs

- **String matching for classification is fragile** → Mitigation: Fall back to `unknown` category with full original message, so no information is lost even if classification fails. Categories are hints, not guarantees.
- **gRPC error messages may vary across versions** → Mitigation: Match conservatively on stable substrings. Include original message in all cases.
- **Slightly longer error messages** → Acceptable trade-off for actionability. The multi-line format keeps each piece of information on its own line for readability.
