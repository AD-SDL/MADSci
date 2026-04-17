## Why

PR #291 code review identified several cleanup items in the SilaNodeClient implementation: an unused parameter, a known limitation without documentation, fragile heuristics without comments, overly broad linting suppressions, and a `validate_url` override with unnecessary string fallback logic. These are small fixes that improve code clarity and maintainability before the feature merges.

## What Changes

- Remove unused `action_id` keyword argument from `_serialize_value()` and all call sites
- Add a `# TODO` comment documenting the top-level-only limitation of `_extract_bytes_files()`
- Add a comment explaining the property-detection heuristic in `get_state()`
- Narrow `ruff.toml` per-file-ignores so broad lint suppressions only apply to `**/generated/**/*.py`, not hand-written SiLA example code
- Simplify `validate_url()` override to remove the redundant string-fallback branch, relying on the base class `AnyUrl` contract

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `sila-command-execution`: `_serialize_value` signature changes (unused parameter removed); `_extract_bytes_files` gains documentation of its top-level-only scan limitation
- `sila-server-introspection`: `get_state` property-detection heuristic gains explanatory comment

## Impact

- `src/madsci_client/madsci/client/node/sila_node_client.py` — signature and comment changes
- `ruff.toml` — narrowed per-file-ignores pattern
- No behavioral changes, no API changes, no dependency changes
