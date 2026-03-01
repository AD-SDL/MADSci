"""Canonical resolution for the ``.madsci/`` project directory.

Every MADSci component that needs to read or write files within the
``.madsci/`` directory tree should use the functions in this module rather
than constructing paths manually.  This ensures consistent, predictable
behaviour across the CLI, managers, nodes, and tests.

Resolution algorithm (``find_madsci_dir``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Walk up from *start_dir* (defaults to ``MADSCI_SETTINGS_DIR`` env var,
   then CWD) looking for a directory that already contains ``.madsci/``.
2. If no ``.madsci/`` sentinel is found, look for ``.git/`` as a secondary
   project-root boundary and return ``{git_parent}/.madsci/``.
3. Fall back to ``~/.madsci/``.

Walk-up boundaries (same as ``settings_dir.walk_up_find``):
- ``~`` (home directory) — searched, but parents above it are not.
- Filesystem root.
- ``max_levels`` limit (default 10).

The resolved path is logged at DEBUG level so operators can always tell
which ``.madsci/`` directory is in effect.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────

SENTRY_DIR_NAME: str = ".madsci"
"""Name of the sentinel / project directory."""

# Standard subdirectory names inside ``.madsci/``.
SUBDIR_PIDS: str = "pids"
SUBDIR_LOGS: str = "logs"
SUBDIR_BACKUPS: str = "backups"
SUBDIR_TEMPLATES: str = "templates"
SUBDIR_DATAPOINTS: str = "datapoints"
SUBDIR_WORKCELLS: str = "workcells"
SUBDIR_MONGODB: str = "mongodb"
SUBDIR_POSTGRESQL: str = "postgresql"
SUBDIR_REDIS: str = "redis"

REGISTRY_FILE: str = "registry.json"
"""Default registry filename inside ``.madsci/``."""

STANDARD_SUBDIRS: tuple[str, ...] = (
    SUBDIR_PIDS,
    SUBDIR_LOGS,
    SUBDIR_BACKUPS,
    SUBDIR_TEMPLATES,
    SUBDIR_DATAPOINTS,
    SUBDIR_WORKCELLS,
)
"""Subdirectories created by ``ensure_madsci_dir``."""

_MAX_LEVELS: int = 10
"""Default maximum walk-up levels."""


# ── Core Functions ─────────────────────────────────────────────────────────


def _resolve_start_dir(start_dir: str | Path | None) -> Path:
    """Resolve the starting directory for walk-up search."""
    if start_dir is not None:
        return Path(start_dir).expanduser().resolve()
    env_val = os.environ.get("MADSCI_SETTINGS_DIR")
    if env_val:
        return Path(env_val).expanduser().resolve()
    return Path.cwd().resolve()


def _maybe_auto_create(target: Path, auto_create: bool) -> None:
    """Create a ``.madsci/`` directory if it doesn't exist and auto_create is set."""
    if auto_create and not target.is_dir():
        target.mkdir(parents=True, exist_ok=True)
        logger.info(
            "Auto-created %s — run 'madsci init' for full scaffolding.",
            target,
        )


def find_madsci_dir(
    start_dir: str | Path | None = None,
    *,
    auto_create: bool = False,
    max_levels: int = _MAX_LEVELS,
) -> Path:
    """Resolve the canonical ``.madsci/`` directory.

    Parameters
    ----------
    start_dir:
        Directory to start the walk-up search from.  Defaults to the
        ``MADSCI_SETTINGS_DIR`` environment variable, then ``Path.cwd()``.
    auto_create:
        If ``True`` and the resolved ``.madsci/`` directory does not exist,
        create it and log an INFO message suggesting ``madsci init``.
    max_levels:
        Maximum number of parent directories to check.

    Returns
    -------
    Path
        Absolute path to the ``.madsci/`` directory.
    """
    current = _resolve_start_dir(start_dir)
    home = Path.home().resolve()
    git_candidate: Path | None = None

    for _ in range(max_levels + 1):
        madsci_dir = current / SENTRY_DIR_NAME
        if madsci_dir.is_dir():
            logger.debug(
                "Using project .madsci/ at %s (found via sentinel)", madsci_dir
            )
            return madsci_dir

        # Remember the first .git/ boundary we see
        if git_candidate is None and (current / ".git").exists():
            git_candidate = current / SENTRY_DIR_NAME

        # Boundaries
        if current == home:
            break
        parent = current.parent
        if parent == current:
            break
        current = parent

    # Secondary: .git/ boundary
    if git_candidate is not None:
        logger.debug(
            "Using .madsci/ at %s (inferred from .git/ boundary)", git_candidate
        )
        _maybe_auto_create(git_candidate, auto_create)
        return git_candidate

    # Fallback: ~/.madsci/
    fallback = home / SENTRY_DIR_NAME
    logger.debug("Using global .madsci/ at %s (fallback)", fallback)
    _maybe_auto_create(fallback, auto_create)
    return fallback


def get_madsci_subdir(
    subdir_name: str,
    start_dir: str | Path | None = None,
    *,
    create: bool = True,
) -> Path:
    """Return a subdirectory within the resolved ``.madsci/`` directory.

    Parameters
    ----------
    subdir_name:
        Name of the subdirectory (e.g. ``"pids"``, ``"logs"``).
    start_dir:
        Forwarded to :func:`find_madsci_dir`.
    create:
        If ``True``, create the subdirectory (and parent ``.madsci/``) if
        they do not exist.

    Returns
    -------
    Path
        Absolute path to the subdirectory.
    """
    madsci_dir = find_madsci_dir(start_dir, auto_create=create)
    subdir = madsci_dir / subdir_name
    if create:
        subdir.mkdir(parents=True, exist_ok=True)
    return subdir


def get_global_madsci_subdir(
    subdir_name: str,
    *,
    create: bool = True,
) -> Path:
    """Return a subdirectory within ``~/.madsci/``.

    Use this for user-level resources shared across all projects (e.g.
    templates).

    Parameters
    ----------
    subdir_name:
        Name of the subdirectory.
    create:
        If ``True``, create the subdirectory if it does not exist.

    Returns
    -------
    Path
        Absolute path to ``~/.madsci/{subdir_name}``.
    """
    madsci_dir = Path.home() / SENTRY_DIR_NAME
    subdir = madsci_dir / subdir_name
    if create:
        subdir.mkdir(parents=True, exist_ok=True)
    return subdir


def ensure_madsci_dir(path: str | Path | None = None) -> Path:
    """Initialize a ``.madsci/`` directory with standard subdirectories.

    Parameters
    ----------
    path:
        Parent directory in which to create ``.madsci/``.
        Defaults to ``Path.cwd()``.

    Returns
    -------
    Path
        Absolute path to the created ``.madsci/`` directory.
    """
    base = Path(path).resolve() if path else Path.cwd().resolve()
    madsci_dir = base / SENTRY_DIR_NAME
    madsci_dir.mkdir(parents=True, exist_ok=True)

    for subdir in STANDARD_SUBDIRS:
        (madsci_dir / subdir).mkdir(exist_ok=True)

    registry_path = madsci_dir / REGISTRY_FILE
    if not registry_path.exists():
        registry_path.write_text(json.dumps({"entries": {}}, indent=2) + "\n")

    return madsci_dir
