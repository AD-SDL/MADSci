## ADDED Requirements

### Requirement: Detect bytes in SiLA response values
The `_serialize_value` function SHALL detect `bytes`-typed values in SiLA command responses and handle them distinctly from other types, rather than falling back to `str()`.

#### Scenario: Bytes value detected
- **WHEN** `_serialize_value` receives a value of type `bytes`
- **THEN** it SHALL NOT convert it using `str(value)` and SHALL instead process it as binary data

### Requirement: Write bytes to disk as action files
When a SiLA command response contains one or more `bytes`-valued fields, the SilaNodeClient SHALL write each bytes value to a file on disk and include the file paths in `ActionResult.files` as an `ActionFiles` instance.

#### Scenario: Single bytes field in response
- **WHEN** a SiLA command returns a response with one field containing `bytes` data
- **THEN** the client SHALL write the bytes to a file named `{field_name}.bin` in a per-action subdirectory, and `ActionResult.files` SHALL be an `ActionFiles` with that field name mapped to the file `Path`

#### Scenario: Multiple bytes fields in response
- **WHEN** a SiLA command returns a response with multiple `bytes`-valued fields
- **THEN** the client SHALL write each to a separate file named `{field_name}.bin` and `ActionResult.files` SHALL contain all of them

#### Scenario: Mixed bytes and non-bytes fields
- **WHEN** a SiLA command returns a response with both `bytes` and non-bytes fields
- **THEN** only the `bytes` fields SHALL appear in `ActionResult.files`; non-bytes fields SHALL appear in `json_result` as before

#### Scenario: No bytes fields in response
- **WHEN** a SiLA command returns a response with no `bytes`-valued fields
- **THEN** `ActionResult.files` SHALL remain `None` (no change from current behavior)

### Requirement: Base64-encode bytes in json_result
Bytes values in `json_result` SHALL be replaced with their base64-encoded string representation so that `json_result` remains JSON-serializable without data loss.

#### Scenario: Bytes field base64 encoding
- **WHEN** a SiLA command response contains a `bytes`-valued field
- **THEN** `json_result` SHALL contain the field with its value as a base64-encoded string (using standard base64 alphabet)

### Requirement: Use sentry-managed output directory
The SilaNodeClient SHALL write action files to a directory resolved via `get_madsci_subdir("sila_files")`, with a per-action subdirectory named by `action_id`.

#### Scenario: File output path structure
- **WHEN** bytes data is written for action `action_id="abc123"` with field name `"ImageData"`
- **THEN** the file SHALL be written to `{sila_files_dir}/abc123/ImageData.bin`

### Requirement: Report action_files capability
The SilaNodeClient SHALL report `action_files=True` in its `NodeClientCapabilities`.

#### Scenario: Capabilities include action_files
- **WHEN** `SilaNodeClient.capabilities()` is called
- **THEN** the returned `NodeClientCapabilities` SHALL have `action_files=True`

### Requirement: Handle bytes in observable command results
Bytes handling SHALL apply to both unobservable (synchronous) and observable (asynchronous) command results, including results retrieved via `get_action_result()` and `await_action_result()`.

#### Scenario: Observable command returns bytes
- **WHEN** an observable SiLA command completes and its response contains `bytes` fields
- **THEN** the `ActionResult` returned by `get_action_result()` or `await_action_result()` SHALL include `files` with the bytes written to disk and `json_result` with base64-encoded values
