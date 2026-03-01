Module madsci.common.local_backends.local_runner
================================================
LocalRunner: single-process orchestrator for all MADSci managers.

Starts all 7 managers in one process with in-memory backends, enabling the
full MADSci stack to run without Docker, Redis, MongoDB, or PostgreSQL.

Usage::

    runner = LocalRunner()
    runner.start()  # Blocks until Ctrl+C

Classes
-------

`LocalRunner(scratch_dir: Optional[Path] = None)`
:   Orchestrates all 7 MADSci managers in a single process with in-memory backends.
    
    Parameters
    ----------
    scratch_dir:
        Directory for SQLite database and local file storage.
        Defaults to ``.madsci/`` in the current working directory.
    
    Initialize the runner with optional scratch directory.

    ### Methods

    `start(self) ‑> None`
    :   Start all managers and block until interrupted.
        
        Each manager binds to its standard port (8000-8006).  Handles
        graceful shutdown on SIGINT/SIGTERM.

    `stop(self) ‑> None`
    :   Request a graceful shutdown (for programmatic usage).