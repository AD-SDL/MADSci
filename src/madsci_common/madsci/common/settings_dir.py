"""Settings directory resolution with walk-up file discovery.

Provides utilities for resolving configuration file paths relative to a
"settings directory" rather than the current working directory. Each filename
walks up the directory tree independently, allowing shared configs (e.g.,
``settings.yaml`` in a lab root) to coexist with per-instance configs (e.g.,
``node.settings.yaml`` in a node subdirectory).

Walk-up is only active when explicitly opted in via the ``_settings_dir``
keyword argument to a ``MadsciBaseSettings`` subclass or the
``MADSCI_SETTINGS_DIR`` environment variable. Without either, existing
CWD-relative behavior is preserved exactly.
"""

from __future__ import annotations

import os
from contextvars import ContextVar
from pathlib import Path
from typing import Optional, Union

PathLike = Union[str, Path]

_settings_dir_var: ContextVar[Optional[Path]] = ContextVar(
    "_settings_dir_var", default=None
)
"""ContextVar that passes the resolved settings directory from ``__init__``
to ``settings_customise_sources`` (a classmethod with no instance access).
Thread-safe and async-compatible."""


def resolve_settings_dir(init_settings_dir: PathLike | None = None) -> Path:
    """Resolve the settings directory using a priority chain.

    Resolution order:
    1. ``init_settings_dir`` keyword argument (if provided)
    2. ``MADSCI_SETTINGS_DIR`` environment variable (if set)
    3. Current working directory (fallback)

    Returns:
        Absolute resolved ``Path``.
    """
    if init_settings_dir is not None:
        return Path(init_settings_dir).expanduser().resolve()

    env_val = os.environ.get("MADSCI_SETTINGS_DIR")
    if env_val:
        return Path(env_val).expanduser().resolve()

    return Path.cwd().resolve()


def walk_up_find(filename: str, start_dir: Path, max_levels: int = 10) -> Path | None:
    """Find a file by walking up from ``start_dir`` toward the filesystem root.

    Args:
        filename: The filename to search for (e.g., ``"settings.yaml"``).
        start_dir: The directory to start searching from.
        max_levels: Maximum number of parent directories to check.

    Returns:
        Absolute path to the found file, or ``None`` if not found.
    """
    current = start_dir.resolve()
    for _ in range(max_levels + 1):
        candidate = current / filename
        if candidate.is_file():
            return candidate.resolve()
        parent = current.parent
        if parent == current:
            # Reached filesystem root
            break
        current = parent
    return None


def resolve_file_paths(
    filenames: str | tuple[str, ...] | None,
    settings_dir: Path,
) -> tuple[Path, ...] | None:
    """Resolve configuration file paths using walk-up discovery.

    For each filename:
    - If absolute, use as-is
    - If relative, call ``walk_up_find()`` from ``settings_dir``
    - If not found, resolve to ``settings_dir / filename`` (pydantic-settings
      will skip non-existent files gracefully)

    Args:
        filenames: A single filename, tuple of filenames, or ``None``.
        settings_dir: The starting directory for walk-up resolution.

    Returns:
        Tuple of resolved ``Path`` objects, or ``None`` if input is ``None``.
    """
    if filenames is None:
        return None

    if isinstance(filenames, str):
        filenames = (filenames,)

    resolved: list[Path] = []
    for name in filenames:
        path = Path(name)
        if path.is_absolute():
            resolved.append(path)
        else:
            found = walk_up_find(name, settings_dir)
            if found is not None:
                resolved.append(found)
            else:
                # Fall back to settings_dir / filename; pydantic-settings
                # will skip it if it doesn't exist.
                resolved.append(settings_dir / name)
    return tuple(resolved)
