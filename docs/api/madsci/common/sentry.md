Module madsci.common.sentry
===========================
Canonical resolution for the ``.madsci/`` project directory.

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

Variables
---------

`REGISTRY_FILE: str`
:   Default registry filename inside ``.madsci/``.

`SENTRY_DIR_NAME: str`
:   Name of the sentinel / project directory.

`STANDARD_SUBDIRS: tuple[str, ...]`
:   Subdirectories created by ``ensure_madsci_dir``.

Functions
---------

`ensure_madsci_dir(path: str | Path | None = None) ‑> pathlib.Path`
:   Initialize a ``.madsci/`` directory with standard subdirectories.

    Parameters
    ----------
    path:
        Parent directory in which to create ``.madsci/``.
        Defaults to ``Path.cwd()``.

    Returns
    -------
    Path
        Absolute path to the created ``.madsci/`` directory.

`find_madsci_dir(start_dir: str | Path | None = None, *, auto_create: bool = False, max_levels: int = 10) ‑> pathlib.Path`
:   Resolve the canonical ``.madsci/`` directory.

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

`get_global_madsci_subdir(subdir_name: str, *, create: bool = True) ‑> pathlib.Path`
:   Return a subdirectory within ``~/.madsci/``.

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

`get_madsci_subdir(subdir_name: str, start_dir: str | Path | None = None, *, create: bool = True) ‑> pathlib.Path`
:   Return a subdirectory within the resolved ``.madsci/`` directory.

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
