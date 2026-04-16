## Why

PR #291 review identified several correctness and consistency issues in the `SilaNodeClient` implementation. Specifically: `get_action_result` silently overwrites a FAILED status with SUCCEEDED, the qualified-name command resolution path skips a `callable()` guard present in the short-form path, the `validate_url` type signature diverges from its parent class, and usage of private SiLA SDK attributes is undocumented. These should be fixed before merging to `unstable`.

## What Changes

- **Fix `get_action_result` status propagation**: When `get_action_status` returns `FAILED`, propagate that status through to the `ActionResult` instead of unconditionally returning `SUCCEEDED`.
- **Add `callable()` check in qualified name resolution**: The `_resolve_sila_command` function's `Feature.Command` path should verify the resolved attribute is callable, matching the behavior of the short-form search path.
- **Align `validate_url` type signature with parent**: Change `SilaNodeClient.validate_url` parameter type from `Any` to `AnyUrl` to match `AbstractNodeClient.validate_url`.
- **Document private SiLA SDK attribute usage**: Add inline comments documenting the reliance on `_wrapped_command`, `_identifier`, and `_description` private attributes, the rationale, and the graceful degradation approach.

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `sila-command-execution`: Fix status propagation in `get_action_result` and add `callable()` guard in qualified name resolution
- `sila-client-dispatch`: Align `validate_url` type signature with parent class

## Impact

- **Code**: `src/madsci_client/madsci/client/node/sila_node_client.py` (4 targeted edits)
- **Tests**: `src/madsci_client/tests/test_sila_node_client.py` (add tests for FAILED status propagation and non-callable qualified name rejection)
- **No API changes**: All fixes are internal correctness improvements; no public interface changes
- **No dependency changes**: No new dependencies or version bumps required
