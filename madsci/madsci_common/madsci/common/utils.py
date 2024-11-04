"""Utilities for the MADSci project."""

from pathlib import Path
from typing import List, Optional

from rich.console import Console

from madsci.common.types import BaseModel, PathLike

console = Console()


def to_snake_case(name: str) -> str:
    """Convert a string to snake case.

    Handles conversion from camelCase and PascalCase to snake_case.
    """
    import re

    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    name = re.sub("([a-z0-9])([A-Z])", r"\1_\2", name)
    return name.lower().replace(" ", "_").replace("__", "_")


def search_for_file_pattern(
    pattern: str,
    start_dir: Optional[PathLike] = None,
    parents: bool = True,
    children: bool = True,
) -> List[str]:
    """
    Search up and down the file tree for a file(s) matching a pattern.

    Args:
        pattern: The pattern to search for. Standard glob patterns are supported.
        start_dir: The directory to start the search in. Defaults to the current directory.
        parents: Whether to search in parent directories.
        children: Whether to search in subdirectories.

    Returns:
        A list of paths to the files that match the pattern.
    """

    import glob

    if not start_dir:
        start_dir = Path.cwd()
    else:
        start_dir = Path(start_dir).resolve()

    results = []
    if children:
        results.extend(glob.glob(str(Path("./**") / pattern), recursive=True))
    else:
        results.extend(glob.glob(str(Path("./") / pattern), recursive=False))
    if parents:
        for parent in start_dir.parents:
            results.extend(glob.glob(str(parent / pattern), recursive=False))
    return results


def save_model(path: PathLike, model: BaseModel, overwrite_check: bool = True) -> None:
    """Save a MADSci model to a YAML file, optionally with a check to overwrite if the file already exists."""
    if Path(path).exists() and overwrite_check:
        if not prompt_yes_no(f"File already exists: {path}. Overwrite?", default="no"):
            return
    model.to_yaml(path)


def prompt_yes_no(prompt: str, default: str = "no") -> bool:
    """Prompt the user for a yes or no answer."""
    response = console.input(f"{prompt} \[y/n] (default: {default}): ").lower()  # noqa: W605
    if not response:
        response = default
    return response in ["y", "yes"]


def prompt_for_input(
    prompt: str, default: Optional[str] = None, required: bool = False
) -> str:
    """Prompt the user for input."""
    if not required:
        if default:
            response = console.input(f"{prompt} (default: {default}): ")
        else:
            response = console.input(f"{prompt} (optional): ")
        if not response:
            response = default
    else:
        response = console.input(f"{prompt} (required): ")
        while not response:
            response = console.input(f"{prompt} (required): ")
    return response


def new_name_str(prefix: str = "") -> str:
    """Generate a new random name string, optionally with a prefix. Make a random combination of an adjective and a noun. Names are not guaranteed to be unique."""
    import random

    adjectives = [
        "happy",
        "clever",
        "bright",
        "swift",
        "calm",
        "bold",
        "eager",
        "fair",
        "kind",
        "proud",
        "brave",
        "wise",
        "quick",
        "sharp",
        "warm",
        "cool",
        "fresh",
        "keen",
        "agile",
        "gentle",
        "noble",
        "merry",
        "lively",
        "grand",
        "smart",
        "witty",
        "jolly",
        "mighty",
        "steady",
        "pure",
        "swift",
        "deft",
        "sage",
        "fleet",
        "spry",
        "bold",
    ]
    nouns = [
        "fox",
        "owl",
        "bear",
        "wolf",
        "hawk",
        "deer",
        "lion",
        "tiger",
        "eagle",
        "whale",
        "seal",
        "dove",
        "swan",
        "crow",
        "duck",
        "horse",
        "mouse",
        "cat",
        "lynx",
        "puma",
        "otter",
        "hare",
        "raven",
        "crane",
        "falcon",
        "badger",
        "marten",
        "stoat",
        "weasel",
        "vole",
        "rabbit",
        "squirrel",
        "raccoon",
        "beaver",
        "moose",
        "elk",
    ]

    name = f"{random.choice(adjectives)}_{random.choice(nouns)}"
    if prefix:
        name = f"{prefix}_{name}"
    return name
