## 1. Error Classification Helper

- [x] 1.1 Add `_classify_connection_error(exception, host, port, insecure)` helper function to `sila_node_client.py` that inspects exception type/message and returns a category string (`dns_resolution`, `connection_refused`, `connection_timeout`, `tls_error`, `grpc_error`, `unknown`)
- [x] 1.2 Add `_format_connection_error(exception, host, port, insecure)` helper function that builds the enriched multi-line error message with category, target info, TLS mode, diagnostic hint, and original message

## 2. Apply Enriched Errors Across Client Methods

- [x] 2.1 Update `_get_sila_client()` to use `_format_connection_error()` when the SiLA client connection fails
- [x] 2.2 Update `send_action()` exception handler to use `_format_connection_error()` for connection-related exceptions
- [x] 2.3 Update `get_status()` exception handler to use `_format_connection_error()` for connection-related exceptions
- [x] 2.4 Update `get_state()` and `get_info()` exception handlers to use `_format_connection_error()` for connection-related exceptions

## 3. Tests

- [x] 3.1 Add unit tests for `_classify_connection_error()` covering all six error categories (DNS, refused, timeout, TLS, gRPC, unknown)
- [x] 3.2 Add unit tests verifying enriched error messages include host, port, TLS mode, and diagnostic hints
- [x] 3.3 Add/update integration-style tests for `get_status()`, `send_action()`, `get_state()`, and `get_info()` verifying enriched errors on connection failure
