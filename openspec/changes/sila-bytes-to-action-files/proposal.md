## Why

SiLA nodes can return binary data (bytes) from commands — e.g., images, raw sensor readings, or instrument output files — but the SilaNodeClient currently converts bytes to a lossy string representation (`str(value)` → `"b'\\x89PNG...'"`) and never populates `ActionResult.files`. This means binary data from SiLA instruments is silently corrupted and inaccessible to downstream experiment logic.

## What Changes

- Detect `bytes` values in SiLA command responses and write them to temporary files on disk.
- Populate `ActionResult.files` (as `ActionFiles`) with paths to those written files, keyed by the SiLA response field name.
- Base64-encode bytes values in `json_result` so they remain JSON-serializable without data loss.
- Set `action_files=True` in `NodeClientCapabilities` for SilaNodeClient.
- Add a configurable temp directory for SiLA action file output (defaulting to a subdirectory of `.madsci/`).
- Add a `GenerateData` command to the SiLA example server that returns `bytes`, providing a runnable reference.
- Extend the SiLA notebook with a section demonstrating the bytes → ActionFiles flow.

## Capabilities

### New Capabilities
- `sila-bytes-handling`: Detect, serialize, and persist bytes data from SiLA command responses as ActionFiles in ActionResults.
- `sila-bytes-example`: Example server command and notebook section demonstrating bytes-to-ActionFiles end-to-end.

### Modified Capabilities
- `sila-command-execution`: ActionResults from SiLA commands will now populate the `files` field when bytes data is present, and `json_result` will contain base64-encoded representations instead of lossy string casts.

## Impact

- **Code**: `sila_node_client.py` — `_serialize_value()`, `_response_to_dict()`, action execution methods, capabilities declaration.
- **Examples**: `sila_example_server/` — new `GenerateData` command in ExampleDevice feature; `sila_node_notebook.ipynb` — new bytes/files section.
- **Types**: No changes to `ActionFiles` or `ActionResult` (they already support the needed structure).
- **Dependencies**: No new external dependencies (uses stdlib `base64`, `tempfile`, `pathlib`).
- **Backwards compatibility**: Responses that previously had lossy string-cast bytes will now have base64-encoded strings in `json_result` — a **behavioral change** but not a breaking API change since the previous output was already unusable.
