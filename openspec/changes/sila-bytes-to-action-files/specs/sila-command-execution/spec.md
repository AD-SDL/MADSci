## MODIFIED Requirements

### Requirement: Map SiLA responses to ActionResult
The client SHALL convert SiLA command response objects to JSON-serializable dicts stored in `ActionResult.json_result`. When response fields contain `bytes` values, they SHALL be base64-encoded in `json_result` and additionally written to disk as files referenced in `ActionResult.files`.

#### Scenario: Named response fields
- **WHEN** a SiLA command returns a response with named fields (e.g., `SayHello_Responses(Greeting="Hello")`)
- **THEN** `json_result` SHALL be `{"Greeting": "Hello"}`

#### Scenario: No response
- **WHEN** a SiLA command returns no response (void command)
- **THEN** `json_result` SHALL be `{}`

#### Scenario: Response with bytes field
- **WHEN** a SiLA command returns a response containing a `bytes`-valued field (e.g., `ReadSensor_Responses(Data=b"\x00\x01\x02")`)
- **THEN** `json_result` SHALL contain the field with its value as a base64-encoded string, and `ActionResult.files` SHALL be an `ActionFiles` with the field name mapped to the file path where the bytes were written
