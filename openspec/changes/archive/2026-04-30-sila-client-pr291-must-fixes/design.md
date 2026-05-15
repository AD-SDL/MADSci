## Context

PR #291 adds the `SilaNodeClient` and accompanying example server, notebook, and OpenSpec artifacts. A senior code review surfaced seven must-fix issues before merge. They divide into:

- **Security** — path traversal in `_extract_bytes_files` (issue #1).
- **Correctness** — over-broad attribute matching that surfaces SiLA properties and SDK helpers as commands (#2 in `get_info`, #3 in `_resolve_sila_command`); over-broad error wrapping that labels every failure as `"SiLA connection error"` (#4).
- **Operability** — server startup silently exits 0 on bind failure (#7); compose has no healthcheck for the SiLA server (#6); `validate_nb_sila` uses `--no-deps` and silently relies on a prior `just up` (#5).

All seven are local fixes — no architectural changes — but several share machinery (the SDK type checks underpin both #2 and #3; the healthcheck enables removing `--no-deps`). Bundling them into one change keeps the related test/spec deltas coherent and reviewable.

The sila2 SDK exposes `ClientObservableCommand` and `ClientUnobservableCommand` at importable, non-underscored module paths (`sila2.client.client_observable_command`, `sila2.client.client_unobservable_command`). These are the canonical "is this a SiLA command?" check and are part of the SDK's contract. Verified locally via `python -c "from sila2.client.client_observable_command import ClientObservableCommand"`.

## Goals / Non-Goals

**Goals:**
- Eliminate the path-traversal vector in bytes file extraction.
- Make `get_info` and `_resolve_sila_command` enumerate only true SiLA commands.
- Restore truthful error messages for non-connection failures while preserving rich diagnostics for genuine connection issues.
- Make `validate_nb_sila` reliable on a clean checkout via a real healthcheck and removal of `--no-deps`.
- Make SiLA server startup failures visible to the orchestrator.

**Non-Goals:**
- Changing the polling-loop / observable-command structure (review noted duplication between `_await_observable` and `await_action_result` — out of scope).
- Adding nested-bytes extraction (the existing TODO stays).
- Adding warnings for `insecure=True` or flipping its default (out of scope).
- Refactoring `close()` idempotency or adding a `_closed` flag (out of scope).
- Persisting the SiLA server UUID across restarts (separate review item, not must-fix).
- Making `CountDown` cancellable (review noted but not must-fix).

## Decisions

### Decision 1: Use sila2 SDK command base classes for type checks
**What**: Import `ClientObservableCommand` and `ClientUnobservableCommand` once at module load, expose them as a tuple `_SILA_COMMAND_TYPES`, and use `isinstance(attr, _SILA_COMMAND_TYPES)` everywhere we currently use `callable(attr)` to decide whether something is a SiLA command.

**Why**: `callable()` matches any object with `__call__` — properties' `.get()`-bearing wrappers, `_wrapped_command` accessors, `MagicMock` defaults in tests, even `__init_subclass__`. The SDK distinguishes commands and properties via dedicated base classes. `isinstance` against those classes is precise, durable across SDK patch releases (the public class names have been stable), and trivial to read.

**Alternatives considered**:
- *Maintain a hand-rolled name-pattern check* (e.g., `type(attr).__name__ in {"ClientObservableCommand", ...}` — what `_is_command_observable` already does). Rejected: a string check is exactly as fragile as the import but loses the IDE/typing benefit and the early failure on SDK rename.
- *Use a `try: attr._wrapped_command` heuristic*. Rejected: still leaks any object with a `_wrapped_command` attribute, and depends on a private attribute we already document as fragile.

**Risk**: a future sila2 release could move or rename these classes. Mitigation: the `_SILA_COMMAND_TYPES` tuple is empty when the SDK is missing (graceful degradation) and centralized in one place — a future SDK migration touches one line. Existing `_is_command_observable` heuristic is left in place (separate fragility, separate fix later).

### Decision 2: Layered try/except in `send_action`
**What**: Split the single `try/except Exception` at `sila_node_client.py:475-535` into three sequential `try/except` blocks: (A) `_get_sila_client()`, (B) `_resolve_sila_command()` + arg prep + log, (C) command invocation + result handling. Only block C runs `_classify_connection_error` and conditionally enriches via `_format_connection_error`. Blocks A and B pass through the original exception text.

**Why**: The current code wraps every exception — including `ValueError("SiLA command 'X' not found")` and `TypeError("missing required argument")` — as `"SiLA connection error (unknown): ..."`, which is actively misleading. Layering the `try` blocks lets us reflect what actually went wrong: a connection problem, a resolution problem, or an execution problem.

**Alternatives considered**:
- *Whitelist known connection-error exception types upfront* (e.g., catch `grpc.RpcError`, `TimeoutError`, etc., separately). Rejected: gRPC errors are sometimes raised as plain `Exception` subclasses with category info only in the message; the existing `_classify_connection_error` already does this work via string heuristics. Reusing it keeps a single source of truth.
- *Mark errors with a sentinel flag instead of restructuring*. Rejected: adds state, doesn't reduce surface area.

**Risk**: downstream consumers may have started string-matching on the `"SiLA connection error"` prefix already. Mitigation: only one merged change has shipped this code (the PR being reviewed), so no external consumers exist yet. The proposal lists this in **Impact** to flag for reviewers.

### Decision 3: Path sanitization via `Path(name).name`
**What**: Add a `_safe_path_component(name)` helper that returns `Path(name).name` after validating against `None`/empty/`.`/`..`. Apply to both the `action_id` (subdirectory) and every response `key` whose value is a bytes sentinel (filename) inside `_extract_bytes_files()`.

**Why**: `Path(s).name` is stdlib and always returns the LAST path component (with embedded separators stripped). `Path("../etc").name == "etc"`, `Path("/abs/p").name == "p"`, `Path("a/b/c").name == "c"`. It does not allow escape via `..` or `/`. Combined with the explicit reject-list (`""`, `"."`, `".."`), the resulting component is always a single safe segment.

**Alternatives considered**:
- *Require `action_id` to be a ULID* (regex match 26 alphanumeric). Rejected: too strict — would break tests that pass arbitrary strings, and the PR's own action IDs may not be ULIDs in every code path. Defense-in-depth via `.name` is sufficient and minimal.
- *Use `os.path.basename`*. Rejected: behaves the same as `Path(...).name` for our use case; `pathlib` is the project convention.
- *Wrap the write in a `path.resolve().is_relative_to(output_dir)` check*. Rejected: `is_relative_to` requires Python 3.9+ (we have it) but adds I/O (resolves symlinks). Sanitizing the input is cheaper and more direct.

**Risk**: a sanitized `action_id` could collide across different unsanitized inputs (e.g., `"../etc"` and `"/etc"` both become `"etc"`). Mitigation: the only legitimate caller path supplies real action IDs; the sanitization is a hardening step. Collisions are noisy but not security-relevant.

### Decision 4: Healthcheck via Python `socket.connect`
**What**: Add a Compose `healthcheck` to `sila_example_server` that runs `python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('localhost', 50052)); s.close()"`. Promote `notebook_validator.depends_on` to long-form so we can attach `condition: service_healthy` to the SiLA server entry while leaving other dependencies at the default `service_started`.

**Why**: The base `madsci` image ships Python; we cannot rely on `nc`, `curl`, or `grpcurl`. A bare TCP connect is enough to confirm the gRPC server is bound and accepting connections — sufficient because the SiLA server has no other startup phases. Short interval (5s) + small retries (5) keeps the wait bounded.

**Alternatives considered**:
- *gRPC reflection probe* (`grpc_health_probe`). Rejected: requires shipping the binary and configuring gRPC health service in the SiLA server. Overkill for a demo.
- *HTTP probe on a sidecar*. Rejected: adds complexity for marginal value.
- *Shell sleep-then-start*. Rejected: races; that's exactly what this is replacing.

**Risk**: `localhost` inside the container resolves correctly because the compose anchor uses `network_mode: host` — confirmed by the existing `command:` line that binds 0.0.0.0:50052. If networking mode ever changes, the healthcheck must change too. Document inline.

### Decision 5: Drop `--no-deps`, rely on Compose dep graph
**What**: `validate_nb_sila` becomes `docker compose --profile testing run --rm notebook_validator papermill ...` (matching `validate_nb_experiment`). No teardown step.

**Why**: With the healthcheck in place, Compose's dependency-resolution does the right thing automatically. The previous `--no-deps` form relied on a prior `just up` and silently false-passed otherwise. The healthcheck dependency means papermill blocks until the server is up.

**Alternatives considered**:
- *Keep `--no-deps` and add explicit `docker compose up -d sila_example_server` / `docker compose stop sila_example_server` around the run*. Rejected: more steps to maintain, and the existing `Notebook is self-contained` requirement (currently mandating `--no-deps`) was itself the source of the false-pass — fixing the requirement is cleaner than working around it.

**Risk**: the recipe now starts more containers (the transitive deps of `notebook_validator`). Wall-clock impact is bounded — the same containers come up under `just all`. Acceptable.

### Decision 6: `sys.exit(1)` on server startup failure
**What**: Replace `__main__.py:55-59`'s `return` with `sys.exit(1)` after `logger.exception(...)` and `server.stop()`.

**Why**: The current `return` exits 0, which Docker / `depends_on` / the new healthcheck would all interpret as "process completed successfully." `sys.exit(1)` makes the failure observable to the orchestrator and to the new healthcheck (which won't get a chance to probe a server that died on bind).

**Alternatives considered**:
- *Re-raise the exception*. Rejected: the bare traceback isn't more useful than the existing `logger.exception(...)` call, and the explicit exit code documents intent.

## Risks / Trade-offs

- **Test fragility**: existing tests use `MagicMock()` for SiLA command results. After switching to `isinstance(attr, _SILA_COMMAND_TYPES)`, those mocks won't satisfy `isinstance` unless they declare `spec=ClientObservableCommand`. Mitigation: update the affected tests as part of the change; the test plan calls these out explicitly. Mock infrastructure becomes slightly heavier but is more honest about the SDK contract.
- **Error message wire format**: layered classification changes the exact error string for non-connection failures. No external consumer exists yet (PR not merged), but the PR description's "Connection error diagnostics" wording should not be read as a contract for ALL errors. Spec deltas make the new wire format explicit.
- **Healthcheck false-negatives**: if the SiLA server binds the port but is somehow not yet ready to serve gRPC, the TCP probe could pass too early. In practice the sila2 SDK starts gRPC before returning from `start_insecure()`, and the healthcheck `start_period: 5s` plus `interval: 5s` gives multiple chances. Acceptable risk.

## Migration Plan

No data migration required. The change is internal to the SiLA client and example server. Rollout is a single PR push:

1. Land all source changes together (one commit per fix, or one combined commit per OpenSpec convention).
2. Pre-commit hooks pass.
3. `pytest src/madsci_client/tests/test_sila_node_client.py` passes (including new tests).
4. `just down && just build && just validate_nb_sila` passes on a clean checkout.
5. Existing PR #291 is updated with the fixes; review can be re-requested.

Rollback is straightforward — revert the change-set commit. No persistent state involved.
