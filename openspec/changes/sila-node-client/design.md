## Context

MADSci's node client architecture uses URL-scheme-based dispatch: `find_node_client()` iterates registered `AbstractNodeClient` subclasses and matches on `url.scheme`. Currently only `RestNodeClient` exists (claiming `http://` and `https://`). The workcell config stores nodes as `dict[str, AnyUrl]`, and the workcell engine caches clients by URL string.

SiLA 2 is an instrument communication standard built on gRPC. The `unitelabs-sila` Python SDK provides `SilaClient` which connects to a host:port, exposes Features as attributes, and lets you call Commands and read Properties. Commands can be unobservable (synchronous) or observable (long-running with status polling).

Pydantic v2's `AnyUrl` accepts custom schemes — `AnyUrl("sila://host:port")` parses correctly with `.scheme = "sila"`, `.host`, and `.port`. This means the existing dispatch and config infrastructure requires zero changes.

## Goals / Non-Goals

**Goals:**
- Implement `SilaNodeClient(AbstractNodeClient)` that connects to SiLA2 servers via gRPC
- Support sending actions (both observable and unobservable SiLA commands) and getting results
- Support server introspection (features → ActionDefinitions, properties → state)
- Integrate via URL-scheme dispatch with no changes to workcell manager code
- Make `unitelabs-sila` an optional dependency that doesn't affect users who don't need it

**Non-Goals:**
- No `SilaNode` or `SilaNodeModule` helper class (server-side SiLA integration)
- No SiLA Server Discovery (zeroconf) integration — users provide explicit `sila://host:port` URLs
- No file transfer support (SiLA uses binary parameters, a different paradigm from MADSci's file upload/download)
- No DualModeClientMixin / async HTTP support (SiLA uses gRPC, not HTTP)
- No admin command mapping (no standard SiLA equivalent)

## Decisions

### 1. URL scheme: `sila://host:port`

Use `sila://` as the URL scheme, with default port 50052 (SiLA standard). This integrates with the existing `find_node_client()` dispatch without any config or engine changes.

**Alternatives considered:**
- `grpc://` — too generic; not all gRPC servers are SiLA
- Adding a `node_type` field to workcell config — unnecessary complexity when URL scheme works

### 2. Action name format: dot notation

Map SiLA commands to MADSci action names as `"FeatureName.CommandName"` (e.g., `"GreetingProvider.SayHello"`). Also support short-form `"CommandName"` when unambiguous across features, raising `ValueError` on ambiguity.

**Alternatives considered:**
- Slash notation (`Feature/Command`) — less natural, no clear advantage
- Only qualified names — too strict for simple servers with few features

### 3. SiLA SDK: `unitelabs-sila`

Use the `unitelabs-sila` package (actively maintained) rather than the original `sila2` package (maintenance-only).

### 4. Optional dependency with conditional registration

Add `unitelabs-sila` as an optional extra (`pip install "madsci.client[sila]"`). The client module uses a `try/except ImportError` guard with a `SILA2_AVAILABLE` sentinel. Registration in `NODE_CLIENT_MAP` is conditional. Attempting to construct `SilaNodeClient` without the SDK installed raises a clear `ImportError`.

**Alternatives considered:**
- Making it a hard dependency — too heavy (grpcio, lxml, zeroconf) for users who don't need SiLA

### 5. Rename MadsciClientConfig to MadsciHttpClientConfig; separate SiLA config

Rename `MadsciClientConfig` → `MadsciHttpClientConfig` to clarify it's HTTP-specific. Keep a `MadsciClientConfig = MadsciHttpClientConfig` backward-compat alias. `SilaNodeClientConfig` inherits `MadsciBaseSettings` directly — the HTTP-oriented fields (retry, pool, rate limit) are irrelevant for gRPC. SiLA-specific fields: `insecure`, `root_certs_path`, `command_timeout`, `poll_interval`, `poll_backoff_factor`, `max_poll_interval`.

**Alternatives considered:**
- Refactoring into a shared `MadsciClientConfig` base with HTTP and gRPC subclasses — not enough field overlap to justify (timeout semantics differ, retry vs polling are fundamentally different patterns)

### 6. Observable command tracking

Store observable command instances in a `_running_commands: dict[action_id, ...]` dict. When `send_action(await_result=False)`, return `RUNNING` and track the instance. `get_action_status()` and `get_action_result()` poll/retrieve from this dict. `await_action_result()` blocks with exponential backoff.

### 7. Properties via `get_state()`

`get_state()` iterates all SiLA features and reads all property values, returning a dict keyed by `"FeatureName.PropertyName"`. This enables monitoring and debugging. Properties are read on-demand (not cached).

## Risks / Trade-offs

- **SiLA SDK API surface variability** → Pin minimum version in pyproject.toml; validate introspection heuristics against actual SDK during implementation. Prefer `isinstance` checks over `hasattr` where possible.
- **Observable command detection is heuristic** (`hasattr(result, "status") and hasattr(result, "get_responses")`) → Mitigate by checking for SDK-specific types like `ClientObservableCommandInstance` if importable.
- **Memory leak in `_running_commands`** for commands never polled → Acceptable for v1; document that callers should always retrieve results. Add TTL cleanup in a future iteration.
- **Thread safety of SiLA gRPC client** → gRPC channels are thread-safe; protect client creation with `threading.Lock`. Concurrent command execution should work but needs validation.
- **`get_state()` could be slow** on servers with many properties → Acceptable trade-off for v1; callers control when they call it.
