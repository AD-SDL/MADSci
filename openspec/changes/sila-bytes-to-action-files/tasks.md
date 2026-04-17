## 1. Bytes Serialization

- [x] 1.1 Add `bytes` handling to `_serialize_value()` — detect `bytes` type, base64-encode it, write to disk, and return a sentinel dict with file path and encoded value
- [x] 1.2 Add `_extract_bytes_files()` post-processing function that scans a response dict for sentinel dicts, extracts file paths into an `ActionFiles` instance, and replaces sentinels with base64 strings in `json_result`

## 2. Action Result Integration

- [x] 2.1 Update unobservable command execution path to call `_extract_bytes_files()` after `_response_to_dict()` and populate `ActionResult.files` when bytes are present
- [x] 2.2 Update observable command result retrieval (`get_action_result`, `await_action_result`) to apply the same bytes extraction
- [x] 2.3 Update `NodeClientCapabilities` to set `action_files=True`

## 3. File Output Directory

- [x] 3.1 Add output directory setup using `get_madsci_subdir("sila_files")` with per-action subdirectory creation keyed by `action_id`

## 4. Tests

- [x] 4.1 Test `_serialize_value` with `bytes` input — verify base64 encoding and file creation
- [x] 4.2 Test `_extract_bytes_files` — verify sentinel extraction, ActionFiles construction, and json_result cleanup
- [x] 4.3 Test end-to-end unobservable command with bytes response — verify ActionResult has both `files` and base64 in `json_result`
- [x] 4.4 Test end-to-end observable command with bytes response
- [x] 4.5 Test mixed bytes and non-bytes response fields
- [x] 4.6 Test response with no bytes fields — verify `files` remains `None`
- [x] 4.7 Test `capabilities()` returns `action_files=True`

## 5. Example Server

- [x] 5.1 Add `GenerateData` command definition to `ExampleDevice.sila.xml` with `NumBytes` integer parameter and `Data` binary response
- [x] 5.2 Regenerate the SiLA feature code from the updated XML (or manually update generated types/base class)
- [x] 5.3 Implement `GenerateData` in `exampledevice_impl.py` — return deterministic bytes of length `NumBytes`

## 6. Notebook

- [x] 6.1 Add a "Binary Data / ActionFiles" section to `sila_node_notebook.ipynb` that calls `GenerateData`, inspects `ActionResult.files`, reads the file back, and shows the base64 value in `json_result`
