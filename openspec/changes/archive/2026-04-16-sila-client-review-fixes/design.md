## Context

PR #291 adds `SilaNodeClient` for native SiLA2 device integration. Code review identified four issues ranging from a correctness bug (FAILED status silently overwritten) to minor consistency gaps. All fixes are localized to `sila_node_client.py` with corresponding test additions.

## Goals / Non-Goals

**Goals:**
- Fix `get_action_result` to propagate FAILED status from `get_action_status` instead of unconditionally returning SUCCEEDED
- Add `callable()` guard in the qualified-name (`Feature.Command`) resolution path to match the short-form path's behavior
- Align `validate_url` type signature with the parent `AbstractNodeClient.validate_url(url: AnyUrl)` signature
- Document private SiLA SDK attribute usage (`_wrapped_command`, `_identifier`, `_description`) with rationale and degradation strategy

**Non-Goals:**
- Changing the `sila2` dependency relationship (workcell manager hard-depends on `madsci.client[sila]` — this is intentional)
- Adding tests for timeout, TLS, or `await_action_result` paths (separate follow-up)
- Refactoring the property-vs-command heuristic in `get_state`

## Decisions

### 1. Propagate `get_action_status` result in `get_action_result`

The current code calls `get_action_status(action_id)`, checks `is_terminal`, but then ignores the returned status and hardcodes `ActionStatus.SUCCEEDED` on line 489. The fix passes the `status` variable through to the `ActionResult`. Additionally, when `status == FAILED`, we still attempt `get_responses()` — this is acceptable because some SiLA servers may provide partial results even on failure, and the `except` block handles the case where `get_responses()` itself throws.

**Alternative considered**: Skip `get_responses()` entirely when FAILED. Rejected because partial responses can be useful for diagnostics, and the try/except already handles failures gracefully.

### 2. Add `callable()` check in qualified name path

The short-form path (line 94) checks `callable(command)` to distinguish SiLA commands from properties. The qualified-name path (line 81) only checks `is not None`. The fix adds the same `callable()` check and raises `ValueError` with a clear message indicating the attribute exists but is not callable (likely a property).

### 3. Change `validate_url` parameter type to `AnyUrl`

The parent class declares `validate_url(cls, url: AnyUrl) -> bool`. The override uses `url: Any`. While the implementation handles both types correctly via `hasattr(url, "scheme")` fallback, the type mismatch violates LSP and confuses static analysis. The fix changes the parameter type to `AnyUrl` while keeping the `hasattr` check internally (since callers in the wild may still pass strings).

### 4. Document private attribute usage with inline comments

The functions `_extract_argument_definitions` and `_is_command_observable` access `_wrapped_command`, `_identifier`, `_description`, and rely on class name patterns. These are internal to the `sila2` SDK. Rather than trying to avoid them (there's no public API for this metadata), we document: what attributes are accessed, why, and how the code degrades gracefully (via `contextlib.suppress` and sensible defaults).

## Risks / Trade-offs

- **[Minimal risk] `get_responses()` on FAILED commands**: Some SiLA servers may raise when `get_responses()` is called after a failure. The existing `except` block already handles this, converting the exception into a FAILED result with error details. No new risk introduced.
- **[No risk] `callable()` check false positives**: A SiLA property that happens to be callable would be incorrectly treated as a command. This is theoretically possible but not observed in practice with the current sila2 SDK — properties expose `.get()` but are not themselves callable.
