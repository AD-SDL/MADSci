"""Utilities for the MADSci project."""

from pathlib import Path
from typing import List


def to_snake_case(name: str) -> str:
    """Convert a string to snake case.

    Handles conversion from camelCase and PascalCase to snake_case.
    """
    import re

    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    name = re.sub("([a-z0-9])([A-Z])", r"\1_\2", name)
    return name.lower().replace(" ", "_")


def search_up_and_down_for_pattern(pattern: str) -> List[str]:
    """Search up and down for a pattern."""
    import glob
    import pathlib

    results = []
    results.extend(glob.glob(str(Path("./**") / pattern), recursive=True))
    for parent in pathlib.Path.cwd().parents:
        results.extend(glob.glob(str(parent / pattern), recursive=True))
    return results
