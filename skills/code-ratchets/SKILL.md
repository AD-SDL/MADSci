---
name: code-ratchets
description: Implement code quality ratchets to prevent proliferation of deprecated patterns. Use when (1) migrating away from legacy code patterns, (2) enforcing gradual codebase improvements, (3) preventing copy-paste proliferation of deprecated practices, or (4) setting up pre-commit hooks to count and limit specific code patterns. A ratchet fails if pattern count exceeds OR falls below expected—ensuring patterns never increase and prompting updates when they decrease.
---

# Code Ratchets

A ratchet is a pre-commit check that counts deprecated patterns in your codebase against a hard-coded expected count. It fails in two cases:
- **Too many instances**: Prevents proliferation via copy-paste
- **Too few instances**: Congratulates you and prompts lowering the expected count

This automates the manual code review process of saying "don't do this, we've stopped doing this."

## Core Workflow

### 1. Identify the Pattern

Define what to count. Patterns work best when they're:
- Simple text or regex matches (grep-able)
- Unambiguous (low false positive rate)
- Discrete instances (countable)

Examples:
- `TODO:` comments
- `# type: ignore` annotations
- `var ` declarations (vs `let`/`const`)
- `Any` type annotations
- Specific function calls: `unsafe_parse(`, `legacy_auth(`
- Import statements: `from old_module import`

### 2. Create the Ratchet Script

Create `scripts/ratchet.py` (or `.sh`):

```python
#!/usr/bin/env python3
"""
Code ratchet: prevents deprecated patterns from proliferating.
Fails if count > expected (proliferation) or count < expected (time to ratchet down).
"""
import subprocess
import sys

# ============================================================
# RATCHET CONFIGURATION - Edit counts here as patterns decrease
# ============================================================
RATCHETS = {
    "TODO comments": {
        "pattern": r"TODO:",
        "expected": 47,
        "glob": "**/*.py",
        "reason": "Resolve TODOs before adding new ones",
    },
    "Type ignores": {
        "pattern": r"# type: ignore",
        "expected": 23,
        "glob": "**/*.py",
        "reason": "Fix type errors instead of ignoring them",
    },
    "Any types": {
        "pattern": r": Any[,\)\]]",
        "expected": 12,
        "glob": "**/*.py",
        "reason": "Use specific types instead of Any",
    },
}


def count_pattern(pattern: str, glob: str) -> int:
    """Count pattern occurrences using grep."""
    try:
        result = subprocess.run(
            ["grep", "-r", "-E", "--include", glob, "-c", pattern, "."],
            capture_output=True,
            text=True,
        )
        # Sum counts from all files (grep -c outputs "filename:count" per file)
        total = sum(
            int(line.split(":")[-1])
            for line in result.stdout.strip().split("\n")
            if line and ":" in line
        )
        return total
    except Exception:
        return 0


def main() -> int:
    failed = False

    for name, config in RATCHETS.items():
        actual = count_pattern(config["pattern"], config["glob"])
        expected = config["expected"]

        if actual > expected:
            print(f"❌ RATCHET FAILED: {name}")
            print(f"   Expected ≤{expected}, found {actual} (+{actual - expected})")
            print(f"   Reason: {config['reason']}")
            print(f"   Pattern: {config['pattern']}")
            print()
            failed = True
        elif actual < expected:
            print(f"🎉 RATCHET DOWN: {name}")
            print(f"   Expected {expected}, found {actual} (-{expected - actual})")
            print(f"   Update expected count in ratchet.py: {expected} → {actual}")
            print()
            failed = True  # Still fail to prompt the update
        else:
            print(f"✓ {name}: {actual}/{expected}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
```

### 3. Configure Pre-commit

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: code-ratchets
        name: Code Ratchets
        entry: python scripts/ratchet.py
        language: python
        pass_filenames: false
        always_run: true
```

Install hooks:
```bash
pip install pre-commit
pre-commit install
```

### 4. Initialize Counts

Run the script once to get current counts, then set those as expected values:

```bash
# Get current counts
grep -r -E "TODO:" --include="*.py" -c . | awk -F: '{sum+=$2} END {print sum}'

# Update RATCHETS dict with actual counts
```

### 5. Maintain the Ratchet

When the ratchet fails with "too few":
1. Celebrate—someone removed deprecated patterns!
2. Update the expected count in the script
3. Commit the updated script

## Alternative: Shell-based Ratchet

For simpler setups, use `scripts/ratchet.sh`:

```bash
#!/bin/bash
set -e

check_ratchet() {
    local name="$1"
    local pattern="$2"
    local expected="$3"
    local glob="$4"
    local reason="$5"

    actual=$(grep -r -E "$pattern" --include="$glob" . 2>/dev/null | wc -l | tr -d ' ')

    if [ "$actual" -gt "$expected" ]; then
        echo "❌ RATCHET FAILED: $name"
        echo "   Expected ≤$expected, found $actual"
        echo "   Reason: $reason"
        exit 1
    elif [ "$actual" -lt "$expected" ]; then
        echo "🎉 RATCHET DOWN: $name"
        echo "   Update expected: $expected → $actual"
        exit 1
    else
        echo "✓ $name: $actual/$expected"
    fi
}

# ============ RATCHET CONFIGURATION ============
check_ratchet "TODO comments" "TODO:" 47 "*.py" "Resolve TODOs first"
check_ratchet "Type ignores" "# type: ignore" 23 "*.py" "Fix type errors"

echo "All ratchets passed!"
```

## Best Practices

1. **Keep patterns simple**: Basic grep/regex. Avoid complex AST analysis—fragility outweighs precision.

2. **One ratchet per concern**: Separate ratchets for separate issues. Easier to track progress.

3. **Document the "why"**: Include `reason` field explaining why the pattern is deprecated.

4. **Fail on decrease**: Always require manual update of expected counts. This creates an audit trail of progress.

5. **Escape hatch**: For exceptional cases, consider allowing bypass via commit message:
   ```python
   # In ratchet.py, check for bypass
   import os
   if os.environ.get("RATCHET_BYPASS"):
       print("⚠️  Ratchet bypassed via RATCHET_BYPASS env var")
       sys.exit(0)
   ```

   Usage: `RATCHET_BYPASS=1 git commit -m "Emergency fix, ratchet bypass justified: ..."`

6. **Gradual rollout**: Start with high counts and let them naturally decrease. Don't set expected=0 on day one.

## Common Ratchet Patterns

| Pattern | Regex | Use Case |
|---------|-------|----------|
| TODO comments | `TODO:` | Track technical debt |
| Type ignores | `# type: ignore` | Enforce typing |
| Any types | `: Any[,\)\]]` | Specific types |
| Console logs | `console\.log\(` | Remove debug code |
| Legacy imports | `from legacy_module` | Track migrations |
| Deprecated calls | `deprecated_func\(` | API migrations |
| Broad exceptions | `except:` or `except Exception:` | Specific exceptions |
| Magic numbers | `\b\d{3,}\b` (tuned) | Named constants |
