## MODIFIED Requirements

### Requirement: Map SiLA responses to ActionResult
The client SHALL convert SiLA command response objects to JSON-serializable dicts stored in `ActionResult.json_result`. The internal `_serialize_value()` function SHALL accept a single positional argument (the value to serialize) with no additional keyword arguments. Bytes values SHALL be converted to sentinel dicts for downstream extraction by `_extract_bytes_files()`. The `_extract_bytes_files()` function SHALL document that it only scans top-level keys of the response dict; nested bytes sentinels are not extracted.

#### Scenario: Named response fields
- **WHEN** a SiLA command returns a response with named fields (e.g., `SayHello_Responses(Greeting="Hello")`)
- **THEN** `json_result` SHALL be `{"Greeting": "Hello"}`

#### Scenario: No response
- **WHEN** a SiLA command returns no response (void command)
- **THEN** `json_result` SHALL be `{}`

#### Scenario: _serialize_value signature
- **WHEN** `_serialize_value()` is called
- **THEN** it SHALL accept only the value to serialize and no `action_id` keyword argument

#### Scenario: _extract_bytes_files limitation documented
- **WHEN** a developer reads `_extract_bytes_files()`
- **THEN** a TODO comment SHALL note that only top-level keys are scanned and nested bytes sentinels are left in-place
