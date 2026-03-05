Module madsci.common.settings_dir
=================================
Settings directory resolution with walk-up file discovery.

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
- A ``.git/`` directory is found (secondary project root boundary). The
  directory containing ``.git/`` is still searched, but parents above it
  are not.
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

Functions
---------

`resolve_file_paths(filenames: str | tuple[str, ...] | None, settings_dir: Path, extra_search_dirs: tuple[str, ...] = ()) ‑> tuple[pathlib.Path, ...] | None`
:   Resolve configuration file paths using walk-up discovery.
    
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
    
    Walk-up stops at the first boundary encountered:
    - A ``.madsci/`` sentinel directory (project root marker)
    - A ``.git/`` directory (secondary project root boundary)
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