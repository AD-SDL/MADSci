"""Settings directory resolution with walk-up file discovery.

Provides utilities for resolving configuration file paths relative to a
"settings directory" rather than the current working directory. Each filename
walks up the directory tree independently, allowing shared configs (e.g.,
``settings.yaml`` in a lab root) to coexist with per-instance configs (e.g.,
``node.settings.yaml`` in a node subdirectory).

Walk-up discovery is enabled by default, starting from the current working
directory. This means settings files placed in parent directories (e.g., a
shared ``settings.yaml`` at the project root) are discovered automatically,
similar to how tools like git, npm, and cargo find their configuration files.

Walk-up stops when any of the following boundaries are reached:
- A ``.madsci/`` directory is found (project root sentinel). The directory
  containing the sentinel is still searched, but parents above it are not.
- The user's home directory (``Path.home()``). The home directory itself is
  searched, but parents above it are not.
- The filesystem root.
- The ``max_levels`` limit.

The starting directory can be overridden via the ``_settings_dir`` keyword
argument to a ``MadsciBaseSettings`` subclass or the
``MADSCI_SETTINGS_DIR`` environment variable.

Extra search directories
~~~~~~~~~~~~~~~~~~~~~~~~

Settings classes can declare ``_extra_search_dirs`` (a tuple of subdirectory
names) to search *below* the settings directory when walk-up discovery does
not find a file. For each filename that is not found via walk-up,
``resolve_file_paths`` checks ``settings_dir / subdir / filename`` for each
subdirectory in order. The first match wins. This allows manager-specific
settings files to live in conventional subdirectories (e.g.,
``managers/events.settings.yaml``) and still be discovered when running from
the lab root.

``ManagerSettings`` sets ``_extra_search_dirs = ("managers", "config")`` by
default, so all manager settings classes automatically search those
subdirectories. Node settings do not set this, keeping their resolution
isolated to their own directory tree.
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

    Walk-up stops at the first boundary encountered:
    - A ``.madsci/`` sentinel directory (project root marker)
    - The user's home directory
    - The filesystem root
    - The ``max_levels`` limit

    The directory containing the boundary is always searched before stopping.

    Args:
        filename: The filename to search for (e.g., ``"settings.yaml"``).
        start_dir: The directory to start searching from.
        max_levels: Maximum number of parent directories to check.

    Returns:
        Absolute path to the found file, or ``None`` if not found.
    """
    current = start_dir.resolve()
    home = Path.home().resolve()
    for _ in range(max_levels + 1):
        candidate = current / filename
        if candidate.is_file():
            return candidate.resolve()
        # Stop if this directory contains a .madsci sentinel
        if (current / ".madsci").is_dir():
            break
        # Stop if we've reached the home directory (already searched it)
        if current == home:
            break
        parent = current.parent
        if parent == current:
            # Reached filesystem root
            break
        current = parent
    return None


def resolve_file_paths(
    filenames: str | tuple[str, ...] | None,
    settings_dir: Path,
    extra_search_dirs: tuple[str, ...] = (),
) -> tuple[Path, ...] | None:
    """Resolve configuration file paths using walk-up discovery.

    For each filename:
    - If absolute, use as-is
    - If relative, call ``walk_up_find()`` from ``settings_dir``
    - If not found via walk-up and ``extra_search_dirs`` is non-empty,
      check ``settings_dir / subdir / filename`` for each subdirectory
      in order; first match wins
    - If still not found, resolve to ``settings_dir / filename``
      (pydantic-settings will skip non-existent files gracefully)

    Args:
        filenames: A single filename, tuple of filenames, or ``None``.
        settings_dir: The starting directory for walk-up resolution.
        extra_search_dirs: Subdirectory names to check under
            ``settings_dir`` when walk-up does not find the file.

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
                # Check extra search directories under settings_dir
                subdir_match = _find_in_extra_dirs(
                    name, settings_dir, extra_search_dirs
                )
                if subdir_match is not None:
                    resolved.append(subdir_match)
                else:
                    # Fall back to settings_dir / filename; pydantic-settings
                    # will skip it if it doesn't exist.
                    resolved.append(settings_dir / name)
    return tuple(resolved)


def _find_in_extra_dirs(
    filename: str,
    settings_dir: Path,
    extra_search_dirs: tuple[str, ...],
) -> Path | None:
    """Check subdirectories under ``settings_dir`` for a file.

    Args:
        filename: The filename to look for.
        settings_dir: The base directory.
        extra_search_dirs: Subdirectory names to check.

    Returns:
        Absolute path to the first match, or ``None``.
    """
    for subdir in extra_search_dirs:
        candidate = settings_dir / subdir / filename
        if candidate.is_file():
            return candidate.resolve()
    return None
