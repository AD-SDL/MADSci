Module madsci.common.settings_dir
=================================
Settings directory resolution with walk-up file discovery.

Provides utilities for resolving configuration file paths relative to a
"settings directory" rather than the current working directory. Each filename
walks up the directory tree independently, allowing shared configs (e.g.,
``settings.yaml`` in a lab root) to coexist with per-instance configs (e.g.,
``node.settings.yaml`` in a node subdirectory).

Walk-up is only active when explicitly opted in via the ``_settings_dir``
keyword argument to a ``MadsciBaseSettings`` subclass or the
``MADSCI_SETTINGS_DIR`` environment variable. Without either, existing
CWD-relative behavior is preserved exactly.

Functions
---------

`resolve_file_paths(filenames: str | tuple[str, ...] | None, settings_dir: Path) ‑> tuple[pathlib.Path, ...] | None`
:   Resolve configuration file paths using walk-up discovery.

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

`resolve_settings_dir(init_settings_dir: PathLike | None = None) ‑> pathlib.Path`
:   Resolve the settings directory using a priority chain.

    Resolution order:
    1. ``init_settings_dir`` keyword argument (if provided)
    2. ``MADSCI_SETTINGS_DIR`` environment variable (if set)
    3. Current working directory (fallback)

    Returns:
        Absolute resolved ``Path``.

`walk_up_find(filename: str, start_dir: Path, max_levels: int = 10) ‑> pathlib.Path | None`
:   Find a file by walking up from ``start_dir`` toward the filesystem root.

    Args:
        filename: The filename to search for (e.g., ``"settings.yaml"``).
        start_dir: The directory to start searching from.
        max_levels: Maximum number of parent directories to check.

    Returns:
        Absolute path to the found file, or ``None`` if not found.
