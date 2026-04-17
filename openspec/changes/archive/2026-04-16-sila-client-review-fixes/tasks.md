## 1. Fix get_action_result status propagation

- [x] 1.1 In `sila_node_client.py` `get_action_result()`, change the `ActionResult` on line 489 to use the `status` variable from `get_action_status()` instead of hardcoded `ActionStatus.SUCCEEDED`
- [x] 1.2 Add test: `get_action_result` returns `FAILED` status when `get_action_status` reports FAILED (instance.done=True, instance.status contains "error")
- [x] 1.3 Add test: `get_action_result` returns `FAILED` with error details when `get_action_status` is FAILED and `get_responses()` raises an exception

## 2. Add callable guard in qualified name resolution

- [x] 2.1 In `_resolve_sila_command()`, add `callable(command)` check after the `getattr(feature, command_name)` call in the qualified-name (`"Feature.Command"`) path, raising `ValueError` if the attribute exists but is not callable
- [x] 2.2 Add test: qualified name resolving to a non-callable attribute (e.g., a SiLA property) raises `ValueError`

## 3. Align validate_url type signature

- [x] 3.1 Change `SilaNodeClient.validate_url` parameter type from `Any` to `AnyUrl` to match `AbstractNodeClient.validate_url`

## 4. Document private SiLA SDK attribute usage

- [x] 4.1 Add inline comments to `_extract_argument_definitions()` documenting the private attributes accessed (`_wrapped_command`, `_identifier`, `_description`), why there's no public API alternative, and the `contextlib.suppress` degradation strategy
- [x] 4.2 Add inline comments to `_is_command_observable()` documenting the class-name heuristic, why it's used, and how it degrades (returns `False` by default)
