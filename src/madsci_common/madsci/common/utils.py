"""Utilities for the MADSci project."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from madsci.common.types.base_types import BaseModel, PathLike
from pydantic import ValidationError
from pydantic_core._pydantic_core import PydanticUndefined
from rich.console import Console

console = Console()


def utcnow() -> datetime:
    """Return the current UTC time."""

    return datetime.now(timezone.utc)


def localnow() -> datetime:
    """Return the current local time."""

    return datetime.now().astimezone()


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
) -> list[str]:
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

    start_dir = Path.cwd() if not start_dir else Path(start_dir).expanduser()

    results = []
    if children:
        results.extend(Path("./").glob(str(Path("**") / pattern)))
    else:
        results.extend(Path.glob(str(Path("./") / pattern)))
        results.extend(Path("./").glob(pattern))
    if parents:
        for parent in start_dir.parents:
            results.extend(Path(parent).glob(pattern))
    return results


def save_model(path: PathLike, model: BaseModel, overwrite_check: bool = True) -> None:
    """Save a MADSci model to a YAML file, optionally with a check to overwrite if the file already exists."""
    try:
        model.model_validate(model)
    except ValidationError as e:
        raise ValueError(f"Validation error while saving model {model}: {e}") from e
    if (
        Path(path).exists()
        and overwrite_check
        and not prompt_yes_no(f"File already exists: {path}. Overwrite?", default="no")
    ):
        return
    model.to_yaml(path)


def prompt_yes_no(prompt: str, default: str = "no", quiet: bool = False) -> bool:
    """Prompt the user for a yes or no answer."""
    response = str(
        prompt_for_input(
            rf"{prompt} \[y/n]",
            default=default,
            required=False,
            quiet=quiet,
        ),
    ).lower()
    return response in ["y", "yes", "true"]


def prompt_for_input(
    prompt: str,
    default: Optional[str] = None,
    required: bool = False,
    quiet: bool = False,
) -> str:
    """Prompt the user for input."""
    if quiet or not sys.stdin.isatty():
        if default:
            return default
        if required:
            raise ValueError(
                "No input provided and no default value specified for required option.",
            )
        return None
    if not required:
        if default:
            response = console.input(f"{prompt} (optional, default: {default}): ")
        else:
            response = console.input(f"{prompt} (optional): ")
        if not response:
            response = default
    else:
        response = None
        while not response:
            if default:
                response = console.input(f"{prompt} (required, default: {default}): ")
                if not response:
                    response = default
            else:
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

    name = f"{random.choice(adjectives)}_{random.choice(nouns)}"  # noqa: S311
    if prefix:
        name = f"{prefix}_{name}"
    return name


def string_to_bool(string: str) -> bool:
    """Convert a string to a boolean value."""
    from argparse import ArgumentTypeError

    if string.lower() in ("true", "t", "1", "yes", "y"):
        return True
    if string.lower() in ("false", "f", "0", "no", "n"):
        return False
    raise ArgumentTypeError(f"Invalid boolean value: {string}")


def prompt_from_list(
    prompt: str,
    options: list[str],
    default: Optional[str] = None,
    required: bool = False,
    quiet: bool = False,
) -> str:
    """Prompt the user for input from a list of options."""

    # *Print numbered list of options
    if not quiet:
        for i, option in enumerate(options, 1):
            console.print(f"[bold]{i}[/]. {option}")

    # *Allow selection by number or exact match
    def validate_response(response: str) -> Optional[str]:
        if response in options:
            return response
        try:
            idx = int(response)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        except ValueError:
            pass
        return None

    while True:
        try:
            response = validate_response(
                prompt_for_input(
                    prompt,
                    default=default,
                    required=required,
                    quiet=quiet,
                ),
            )
        except ValueError:
            continue
        else:
            break
    return response


def prompt_from_pydantic_model(model: BaseModel, prompt: str, **kwargs: Any) -> str:
    """Prompt the user for input from a pydantic model.

    Args:
        model: The pydantic model to prompt for
        prompt: The prompt to display
        **kwargs: Pre-filled values to skip prompting for

    Returns:
        A dictionary of field values for the model
    """
    result = {}

    # Print header for the prompts
    console.print(f"\n[bold]{prompt}[/]")

    for field_name, field in model.model_fields.items():
        # Skip if value provided in kwargs
        if field_name in kwargs:
            result[field_name] = kwargs[field_name]
            continue

        # Build field prompt
        field_prompt = f"{field.title or field_name}"

        # Add type hint
        type_hint = str(field.annotation).replace("typing.", "")
        field_prompt += f" ({type_hint})"

        # Add description if available
        if field.description:
            field_prompt += f"\n{field.description}"

        # Handle basic fields
        while True:
            try:
                response = prompt_for_input(
                    field_prompt,
                    default=field.default
                    if field.default != PydanticUndefined
                    else None,
                    required=field.is_required,
                )
                if isinstance(response, str):
                    response = json.loads(response)
                result[field_name] = response
            except json.JSONDecodeError as e:
                console.print(
                    f"[bold red]Invalid JSON input for field {field_name}: {e}[/]",
                )
                continue
            else:
                break

    return result


def relative_path(source: Path, target: Path, walk_up: bool = True) -> Path:
    """
    "Backport" of :meth:`pathlib.Path.relative_to` with ``walk_up=True``
    that's not available pre 3.12.

    Return the relative path to another path identified by the passed
    arguments.  If the operation is not possible (because this is not
    related to the other path), raise ValueError.

    The *walk_up* parameter controls whether `..` may be used to resolve
    the path.

    References:
        https://github.com/python/cpython/blob/8a2baedc4bcb606da937e4e066b4b3a18961cace/Lib/pathlib/_abc.py#L244-L270
    Credit: https://github.com/p2p-ld/numpydantic/blob/66fffc49f87bfaaa2f4d05bf1730c343b10c9cc6/src/numpydantic/serialization.py#L107
    """
    if not isinstance(source, Path):
        source = Path(source)
    target_parts = target.parts
    source_parts = source.parts
    anchor0, parts0 = target_parts[0], list(reversed(target_parts[1:]))
    anchor1, parts1 = source_parts[0], list(reversed(source_parts[1:]))
    if anchor0 != anchor1:
        raise ValueError(f"{target!r} and {source!r} have different anchors")
    while parts0 and parts1 and parts0[-1] == parts1[-1]:
        parts0.pop()
        parts1.pop()
    for part in parts1:
        if not part or part == ".":
            pass
        elif not walk_up:
            raise ValueError(f"{target!r} is not in the subpath of {source!r}")
        elif part == "..":
            raise ValueError(f"'..' segment in {source!r} cannot be walked")
        else:
            parts0.append("..")
    return Path(*reversed(parts0))


def threaded_task(func: callable) -> callable:
    """Mark a function as a threaded task, to be run without awaiting. Returns the thread object, so you _can_ await if needed."""

    import functools
    import threading

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> threading.Thread:
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.start()
        return thread

    return wrapper


def threaded_daemon(func: callable) -> callable:
    """Mark a function as a threaded daemon, to be run without awaiting. Returns the thread object, so you _can_ await if needed, and stops when the calling thread terminates."""

    import functools
    import threading

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> threading.Thread:
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread

    return wrapper


def pretty_type_repr(type_hint: Any) -> str:
    """Returns a pretty string representation of a type hint, including subtypes."""
    type_name = type_hint.__name__
    if (
        "__args__" in dir(type_hint) and type_hint.__args__
    ):  # * If the type has subtype info
        type_name += "["
        for subtype in type_hint.__args__:
            type_name += pretty_type_repr(subtype)
        type_name += "]"
    return type_name


@threaded_daemon
def repeat_on_interval(
    interval: float, func: callable, *args: Any, **kwargs: Any
) -> None:
    """Repeat a function on an interval."""
    import time

    while True:
        func(*args, **kwargs)
        time.sleep(interval)
