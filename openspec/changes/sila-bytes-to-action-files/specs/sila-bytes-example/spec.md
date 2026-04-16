## ADDED Requirements

### Requirement: Example server provides a bytes-returning command
The SiLA example server SHALL include a `GenerateData` unobservable command on the `ExampleDevice` feature that accepts a `NumBytes` integer parameter and returns a `Data` field of type `bytes`.

#### Scenario: GenerateData returns bytes
- **WHEN** `GenerateData(NumBytes=10)` is called on the example server
- **THEN** the response SHALL contain a `Data` field with exactly 10 bytes of deterministic content

#### Scenario: GenerateData with zero bytes
- **WHEN** `GenerateData(NumBytes=0)` is called
- **THEN** the response SHALL contain a `Data` field with empty bytes (`b""`)

### Requirement: Example server GenerateData is documented in the SiLA feature XML
The `GenerateData` command SHALL be defined in the `ExampleDevice.sila.xml` feature definition with a `NumBytes` integer parameter and a `Data` binary response.

#### Scenario: Feature XML includes GenerateData
- **WHEN** a developer reads `ExampleDevice.sila.xml`
- **THEN** the file SHALL contain a command definition for `GenerateData` with parameter and response types documented

### Requirement: Notebook demonstrates bytes-to-ActionFiles flow
The SiLA notebook SHALL include a section after the existing command examples that calls `GenerateData`, inspects the `ActionResult.files` field, and reads the written file back from disk.

#### Scenario: Notebook bytes section executes successfully
- **WHEN** a user runs the bytes section of the notebook against a running example server
- **THEN** the section SHALL show that `ActionResult.files` is an `ActionFiles` instance, display the file path, and verify the file contents match the expected bytes

#### Scenario: Notebook shows base64 in json_result
- **WHEN** a user runs the bytes section of the notebook
- **THEN** the section SHALL show that `json_result` contains a base64-encoded string for the `Data` field
