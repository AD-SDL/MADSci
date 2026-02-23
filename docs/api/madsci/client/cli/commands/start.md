Module madsci.client.cli.commands.start
=======================================
MADSci CLI start command.

Wraps `docker compose up` for starting MADSci lab services, or launches
all managers in a single process with in-memory backends (local mode).
Also supports starting individual managers and nodes as subprocesses.
