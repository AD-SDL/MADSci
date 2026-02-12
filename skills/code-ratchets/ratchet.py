#!/usr/bin/env python3
"""
Code ratchet: prevents deprecated patterns from proliferating.
Fails if count > expected (proliferation) or count < expected (time to ratchet down).

Usage:
    python scripts/ratchet.py           # Run all ratchets
    python scripts/ratchet.py --init    # Print current counts for initialization
"""

import argparse
import re
import sys
from pathlib import Path

from rich import print

# ============================================================
# RATCHET CONFIGURATION - Edit counts here as patterns decrease
# ============================================================
RATCHETS = {
    "TODO comments": {
        "pattern": r"TODO:",
        "expected": 0,  # Set to current count when initializing
        "glob": "*.py",
        "exclude_dirs": [".git", "node_modules", "__pycache__", ".venv", "venv"],
        "reason": "Resolve TODOs before adding new ones",
    },
    "Type ignores": {
        "pattern": r"# type: ignore",
        "expected": 0,
        "glob": "*.py",
        "exclude_dirs": [".git", "node_modules", "__pycache__", ".venv", "venv"],
        "reason": "Fix type errors instead of ignoring them",
    },
    # Add more ratchets here
}


def count_pattern(
    pattern: str, glob: str, exclude_dirs: list[str]
) -> tuple[int, list[str]]:
    """
    Count pattern occurrences using native Python.
    Returns (count, list of matching files with counts).
    """
    try:
        regex = re.compile(pattern)
        matches = []
        total = 0
        exclude_set = set(exclude_dirs)

        for path in Path().rglob(glob):
            # Skip if any parent directory is in exclude list
            if any(part in exclude_set for part in path.parts):
                continue

            # Skip if not a file
            if not path.is_file():
                continue

            try:
                with Path.open(path, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    count = len(regex.findall(content))
                    if count > 0:
                        matches.append(f"  {path}: {count}")
                        total += count
            except (OSError, UnicodeDecodeError):
                # Skip files that can't be read
                continue

        return total, matches
    except re.error as e:
        print(f"Error: Invalid regex pattern '{pattern}': {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error counting pattern: {e}", file=sys.stderr)
        return 0, []


def run_ratchets(verbose: bool = False) -> int:
    """Run all ratchets and return exit code (0 = pass, 1 = fail)."""
    failed = False

    for name, config in RATCHETS.items():
        actual, matches = count_pattern(
            config["pattern"],
            config["glob"],
            config.get("exclude_dirs", []),
        )
        expected = config["expected"]

        if actual > expected:
            print(f"❌ RATCHET FAILED: {name}")
            print(f"   Expected ≤{expected}, found {actual} (+{actual - expected})")
            print(f"   Reason: {config['reason']}")
            print(f"   Pattern: {config['pattern']}")
            if verbose and matches:
                print("   Matches:")
                for match in matches[:10]:  # Limit output
                    print(f"   {match}")
                if len(matches) > 10:
                    print(f"   ... and {len(matches) - 10} more files")
            print()
            failed = True
        elif actual < expected:
            print(f"🎉 RATCHET DOWN: {name}")
            print(f"   Expected {expected}, found {actual} (-{expected - actual})")
            print("   Great progress! Update expected count in ratchet.py:")
            print(f'   "expected": {actual},')
            print()
            failed = True  # Still fail to prompt the update
        else:
            print(f"✓ {name}: {actual}/{expected}")

    return 1 if failed else 0


def init_counts() -> None:
    """Print current counts for all ratchets to help initialization."""
    print("Current pattern counts (use these to initialize your ratchets):\n")

    for name, config in RATCHETS.items():
        actual, matches = count_pattern(
            config["pattern"],
            config["glob"],
            config.get("exclude_dirs", []),
        )
        print(f'"{name}": {{')
        print(f'    "pattern": r"{config["pattern"]}",')
        print(f'    "expected": {actual},  # Current count')
        print(f'    "glob": "{config["glob"]}",')
        print(f'    "exclude_dirs": {config.get("exclude_dirs", [])},')
        print(f'    "reason": "{config["reason"]}",')
        print("},")
        if matches:
            print(
                f"  # Found in: {', '.join(m.split(':')[0].strip() for m in matches[:5])}"
            )
            if len(matches) > 5:
                print(f"  # ... and {len(matches) - 5} more files")
        print()


def main() -> int:
    """Runs the code ratchets based on command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Code ratchet: prevent proliferation of deprecated patterns"
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Print current counts to help initialize ratchet configuration",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show files containing matches when ratchet fails",
    )
    args = parser.parse_args()

    if args.init:
        init_counts()
        return 0

    return run_ratchets(verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
