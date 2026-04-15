---
name: galahad
description: How to approach tests, types, lints, and coverage
---

# Coding Agent Quality Rules (Galahad Principle)

Based on Jonathan Lange's "The Galahad Principle":
https://jml.io/galahad-principle/

Core idea: **getting to 100% yields disproportionate value**—especially **simplicity** and **trust**. When checks are truly "all green", any new failure is a strong, unambiguous signal; "absence of evidence becomes evidence of absence".

## Assess Before Applying

Before enforcing these rules strictly, understand the context:

1. **Read project conventions**: Check `tsconfig.json`, `pyproject.toml`, `.eslintrc`, `setup.cfg`, `mypy.ini` for existing standards
2. **Gauge existing tech debt**: If the codebase already has 500 `any` types, don't block progress on fixing all of them
3. **Match scope to task**: A quick bug fix ≠ a new feature ≠ a refactor

When working in a codebase that doesn't meet these standards:
- **Don't make things worse**: No new type escapes, no new skipped tests
- **Opportunistically improve**: Clean up what you touch
- **Don't block the user's goal**: Pragmatic progress beats ideological purity
- **Use code ratchets to improve over time**: Use the "code-ratchets" skill to improve patterns over time

### Discovering project standards

**TypeScript**: Check `tsconfig.json` for `strict`, `noImplicitAny`, `strictNullChecks`. Match existing settings.

**Python**: Check for `mypy.ini`, `pyproject.toml` `[tool.mypy]`, `pyrightconfig.json`. Note the strictness level.

**General**: Look at existing test files for patterns, existing code for style. When in doubt, match what's there.

## Non-negotiables: never evade feedback

Treat **type errors, test failures, pre-commit hooks, lint errors, and coverage warnings** as helpful feedback. Fix root causes.

### Forbidden by default (unless the user explicitly orders it)

- **Type escapes / silencing**
  - TypeScript: `any`, sketchy `unknown` laundering, unchecked casts, `as any`, `@ts-ignore`, disabling strict mode, weakening compiler flags
  - Python: `# type: ignore`, `# pyright: ignore`, `# mypy: ignore-errors`, `cast()` without justification, `Any` in public APIs, disabling type checkers
  - General: `noqa`, pragma comments to silence legitimate warnings
- **Coverage gaming**
  - TypeScript: `/* istanbul ignore */`, `/* c8 ignore */`, artificial exclusions in config
  - Python: `# pragma: no cover`, `# coverage: skip`, excluding entire modules from coverage config
  - General: "generated" file tricks, decorator/macro suppression, lowering coverage thresholds
- **Faking results**
  - Skipping CI steps and claiming success; "snapshotting" coverage; lowering thresholds; marking tests flaky to ignore them

### When user requests conflict with these principles

If the user explicitly asks for a type escape, to skip tests, or similar:

1. **Comply, but note the tradeoff**: "Adding `any` here—this will need cleanup before the type system can catch errors in this area."
2. **Offer alternatives briefly**: "If you prefer, I could extract this to a small typed helper instead."
3. **Don't lecture**: One sentence, then move on.

The user owns the codebase. Your job is to inform, not obstruct.

## Priorities

Type safety is part of correctness and **outranks tests**.

When tradeoffs exist, prioritize in this order:

1. **Type safety / soundness**
2. **Correctness + meaningful tests**
3. **Clarity / maintainability**
4. **Performance**
5. **Backwards compatibility**

Breaking changes are acceptable when they improve verifiability and simplify the system, but:
- Flag breaking changes explicitly to the user
- Prefer non-breaking improvements when effort is similar
- Consider migration paths for public APIs

## Default workflow (when anything fails)

1. **Read the failure output carefully.**
2. **Understand the context**: Why does this code exist? What was the original intent? Check git history or ask if unclear.
3. **Restate the real invariant** being violated in plain English.
4. **Fix the root cause** (not the symptom).
5. **Improve tests** so the behavior is pinned and regressions get caught.
6. **Refactor production code** if needed to make it easy to type-check and validate.

### Run checks in this order

1. **Typecheck**
2. **Unit tests**
3. **Integration tests**
4. **Doc and End-to-End tests**
5. **Lint / pre-commit**
6. **Coverage**

Goal: a repo where "all green" is normal, and any new red is a loud, trustworthy signal.

## What makes a test meaningful

✅ **Meaningful tests**:
- Test observable behavior from the caller's perspective
- Would catch real regressions
- Document intent and edge cases
- Fail when actual bugs are introduced

❌ **Not meaningful**:
- Test implementation details (private methods, internal state)
- Duplicate what the type checker already verifies
- Assert only on mock interactions, not outcomes
- Pass regardless of whether the code works

**The test**: "If this test failed, would I learn something useful about a real bug?"

## Coverage: aim for meaningful, not mechanical

- **Do**: Cover all business logic paths, edge cases, error handling
- **Don't**: Chase 100% by testing trivial getters or truly unreachable defensive code
- **Legitimate exclusions exist**: Platform-specific branches, debug-only code, abstract method stubs
- **The bar**: Would a failure in this line indicate a real bug? If yes, cover it.

Coverage comes from exercising real behavior, not from exclusion comments.

## Handling flaky tests

If a test is genuinely flaky:

1. **Identify the source**: Time-dependence? Race condition? External service? Order-dependence?
2. **Fix the non-determinism**: Inject clocks, add synchronization, mock external calls, isolate state
3. **If unfixable now**: Quarantine in a separate test suite (not skipped, but run separately and tracked)
4. **Never**: Mark as "expected flaky" and leave in the main CI path

## "Hard to test" means refactor

If something is hard to test or hard to type, treat it as a **design smell**.

Refactor towards:
- Smaller pure functions
- Explicit data flow, minimal global state
- Clear boundaries between logic and side effects
- Typed domain models over stringly-typed data
  - TypeScript: strong interfaces/types instead of `Record<string, any>`
  - Python: dataclasses, Pydantic models, or TypedDicts instead of `dict[str, Any]`

## Mocks: use sparingly and explicitly

Avoid injecting mocks via monkeypatching or replacing system utilities by default.

**Preferred approach:**
- Make the function under test able to operate in multiple environments by **passing in the substitutable operations explicitly** (as function parameters or small interfaces)
- Only do this for operations that genuinely need substitution in tests: time, randomness, network, filesystem, process execution
- This makes the injection point **explicit**, documents what varies, and keeps tests honest

**Examples:**

TypeScript:
```typescript
// ❌ Bad: hard-coded dependency, requires monkeypatching to test
function processOrder(orderId: string) {
  const now = new Date();
  const order = database.getOrder(orderId);
  // ...
}

// ✅ Good: explicit dependencies
function processOrder(
  orderId: string,
  deps: { getTime: () => Date; getOrder: (id: string) => Order }
) {
  const now = deps.getTime();
  const order = deps.getOrder(orderId);
  // ...
}
```

Python:
```python
# ❌ Bad: hard-coded dependency, requires monkeypatching to test
def process_order(order_id: str) -> OrderResult:
    now = datetime.now()
    order = database.get_order(order_id)
    # ...

# ✅ Good: explicit dependencies
def process_order(
    order_id: str,
    *,
    get_time: Callable[[], datetime] = datetime.now,
    get_order: Callable[[str], Order] = database.get_order,
) -> OrderResult:
    now = get_time()
    order = get_order(order_id)
    # ...
```

## Summary: what "good" looks like

- Types encode invariants; no "trust me" casts
- Tests assert observable behavior (not implementation trivia)
- Coverage comes from exercising real behavior, not exclusions
- If a thing can't be verified cleanly, refactor until it can
- Progress beats perfection; don't make things worse, do make things better
