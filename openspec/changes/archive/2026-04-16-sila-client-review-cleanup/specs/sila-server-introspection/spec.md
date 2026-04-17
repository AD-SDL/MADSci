## MODIFIED Requirements

### Requirement: Read SiLA properties via get_state
The SilaNodeClient SHALL read all SiLA property values from the server and return them as a flat dict. The property-detection heuristic (`hasattr(attr, "get") and not callable(attr)`) SHALL be documented with an inline comment explaining: (a) why this heuristic is used, (b) that it depends on SiLA SDK implementation details, and (c) that the `contextlib.suppress(Exception)` wrapper protects against misclassification.

#### Scenario: Read all properties
- **WHEN** `get_state()` is called
- **THEN** the client SHALL return a dict mapping `"FeatureName.PropertyName"` to the current property value for every readable property on the server

#### Scenario: Property read failure
- **WHEN** a specific property raises an error during reading
- **THEN** the client SHALL set that property's value to `None` in the returned dict and continue reading other properties

#### Scenario: Property detection heuristic documented
- **WHEN** a developer reads the `get_state()` method
- **THEN** an inline comment SHALL explain the property-detection heuristic, its SDK dependency, and the error-suppression safety net
