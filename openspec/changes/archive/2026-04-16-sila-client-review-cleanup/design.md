## Context

PR #291 code review identified five cleanup items in the SilaNodeClient implementation. All changes are non-behavioral: removing dead code, adding documentation comments, tightening linter configuration, and simplifying a method override. The SilaNodeClient and its test suite are already complete and passing.

## Goals / Non-Goals

**Goals:**
- Remove the unused `action_id` parameter from `_serialize_value()` and all call sites
- Document the top-level-only bytes extraction limitation in `_extract_bytes_files()`
- Document the property-detection heuristic in `get_state()`
- Narrow ruff per-file-ignores so hand-written SiLA example code gets standard linting
- Simplify `validate_url()` to remove the string-fallback branch

**Non-Goals:**
- Implementing recursive bytes extraction (documented as future work)
- Changing any runtime behavior
- Modifying test assertions (only call-site updates for the removed parameter)

## Decisions

### 1. Remove `action_id` from `_serialize_value` entirely (not deprecate)
The parameter was never used in the function body — it was threaded through recursive calls but served no purpose. Since this is pre-merge code on a feature branch, there are no external callers to worry about. Clean removal is simpler than deprecation.

### 2. Narrow ruff ignores to `**/sila_example_server/generated/**/*.py`
The current pattern `**/sila_example_server/**/*.py` suppresses naming, annotation, and docstring rules for hand-written files like `exampledevice_impl.py` and `__main__.py`. The generated SiLA SDK code legitimately needs broad suppression (it uses SiLA naming conventions and auto-generated patterns), but hand-written code should follow project standards. Split into two patterns: broad ignores for `generated/`, minimal ignores for the rest.

### 3. Simplify `validate_url` to use parent class pattern
The base class `AbstractNodeClient.validate_url()` accesses `url.scheme` directly. The override adds a `str(url).startswith("sila://")` fallback for when `url` lacks a `.scheme` attribute. Since the type annotation is `AnyUrl`, which always has `.scheme`, the fallback is dead code. Remove it to match the parent class pattern exactly.

## Risks / Trade-offs

- **ruff.toml narrowing**: Hand-written SiLA example files may have existing lint violations that surface. Mitigation: run `ruff check` on those files after the change and fix any issues. The `# noqa: S104` on `0.0.0.0` binding is already present.
- **validate_url simplification**: If any caller passes a raw string instead of `AnyUrl`, it would break. Mitigation: the type annotation and all existing call sites already use `AnyUrl`. The test `test_validates_sila_scheme_string` passes a string, but `AnyUrl` coercion happens at the Pydantic level before reaching `validate_url` in production code. The test should still pass since `hasattr(str, 'scheme')` is False, and the fallback would have kicked in — but we need to verify the test still works with the simplified logic. If it relies on the string fallback, update the test to pass `AnyUrl` instead.
