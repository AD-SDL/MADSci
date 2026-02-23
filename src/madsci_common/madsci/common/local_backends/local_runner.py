"""LocalRunner: single-process orchestrator for all MADSci managers.

Starts all 7 managers in one process with in-memory backends, enabling the
full MADSci stack to run without Docker, Redis, MongoDB, or PostgreSQL.

Usage::

    runner = LocalRunner()
    runner.start()  # Blocks until Ctrl+C
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
from pathlib import Path
from typing import Any, Optional

import uvicorn
from madsci.common.local_backends.inmemory_collection import (
    InMemoryMongoClient,
)
from madsci.common.local_backends.inmemory_redis import InMemoryRedisClient

# Default ports for each manager — matches the standard MADSci port assignments.
MANAGER_PORTS = {
    "lab": 8000,
    "event": 8001,
    "experiment": 8002,
    "resource": 8003,
    "data": 8004,
    "workcell": 8005,
    "location": 8006,
}


class LocalRunner:
    """Orchestrates all 7 MADSci managers in a single process with in-memory backends.

    Parameters
    ----------
    scratch_dir:
        Directory for SQLite database and local file storage.
        Defaults to ``.madsci/`` in the current working directory.
    """

    def __init__(
        self,
        scratch_dir: Optional[Path] = None,
    ) -> None:
        """Initialize the runner with optional scratch directory."""
        self.scratch_dir = scratch_dir or Path.cwd() / ".madsci"
        self.scratch_dir.mkdir(parents=True, exist_ok=True)

        # Shared in-memory backends
        self._redis_client = InMemoryRedisClient()
        self._mongo_client = InMemoryMongoClient()

    def _set_environment(self) -> None:
        """Set environment variables so managers and clients discover each other."""
        for name, port in MANAGER_PORTS.items():
            env_key = (
                f"{name.upper()}_SERVER_URL" if name != "lab" else "LAB_SERVER_URL"
            )
            os.environ.setdefault(env_key, f"http://localhost:{port}")

        # Also set context-level URLs for MadsciContext discovery
        os.environ.setdefault(
            "LAB_SERVER_URL", f"http://localhost:{MANAGER_PORTS['lab']}"
        )
        os.environ.setdefault(
            "EVENT_SERVER_URL", f"http://localhost:{MANAGER_PORTS['event']}"
        )
        os.environ.setdefault(
            "EXPERIMENT_SERVER_URL", f"http://localhost:{MANAGER_PORTS['experiment']}"
        )
        os.environ.setdefault(
            "RESOURCE_SERVER_URL", f"http://localhost:{MANAGER_PORTS['resource']}"
        )
        os.environ.setdefault(
            "DATA_SERVER_URL", f"http://localhost:{MANAGER_PORTS['data']}"
        )
        os.environ.setdefault(
            "WORKCELL_SERVER_URL", f"http://localhost:{MANAGER_PORTS['workcell']}"
        )
        os.environ.setdefault(
            "LOCATION_SERVER_URL", f"http://localhost:{MANAGER_PORTS['location']}"
        )

    def _create_managers(self) -> dict[str, Any]:
        """Instantiate each manager with in-memory backends injected."""
        # Lazy imports to avoid circular deps and heavy import overhead at module level
        from madsci.data_manager.data_server import DataManager  # noqa: PLC0415
        from madsci.event_manager.event_server import EventManager  # noqa: PLC0415
        from madsci.experiment_manager.experiment_server import (  # noqa: PLC0415
            ExperimentManager,
        )
        from madsci.location_manager.location_server import (  # noqa: PLC0415
            LocationManager,
        )
        from madsci.resource_manager.resource_interface import (  # noqa: PLC0415
            ResourceInterface,
        )
        from madsci.resource_manager.resource_server import (  # noqa: PLC0415
            ResourceManager,
        )
        from madsci.squid.lab_server import LabManager  # noqa: PLC0415
        from madsci.workcell_manager.workcell_server import (  # noqa: PLC0415
            WorkcellManager,
        )

        # SQLite database path for the Resource Manager
        sqlite_path = self.scratch_dir / "resources.db"
        sqlite_url = f"sqlite:///{sqlite_path}"

        managers: dict[str, Any] = {}

        # Lab Manager (8000) — no database needed
        managers["lab"] = LabManager()

        # Event Manager (8001) — in-memory MongoDB
        managers["event"] = EventManager(
            db_connection=self._mongo_client["events"],
        )

        # Experiment Manager (8002) — in-memory MongoDB
        managers["experiment"] = ExperimentManager(
            db_connection=self._mongo_client["experiments"],
        )

        # Resource Manager (8003) — SQLite via SQLAlchemy
        resource_interface = ResourceInterface(url=sqlite_url)
        managers["resource"] = ResourceManager(
            resource_interface=resource_interface,
        )

        # Data Manager (8004) — in-memory MongoDB (MinIO falls back to filesystem automatically)
        managers["data"] = DataManager(
            db_client=self._mongo_client,
        )

        # Workcell Manager (8005) — in-memory Redis + MongoDB
        managers["workcell"] = WorkcellManager(
            redis_connection=self._redis_client,
            mongo_connection=self._mongo_client["workcell"],
            start_engine=False,
        )

        # Location Manager (8006) — in-memory Redis
        managers["location"] = LocationManager(
            redis_connection=self._redis_client,
        )

        return managers

    def start(self) -> None:
        """Start all managers and block until interrupted.

        Each manager binds to its standard port (8000-8006).  Handles
        graceful shutdown on SIGINT/SIGTERM.
        """
        self._set_environment()
        managers = self._create_managers()

        # Build (manager_name, FastAPI app, port) tuples
        apps: list[tuple[str, Any, int]] = []
        for name, manager in managers.items():
            app = manager.create_server()
            apps.append((name, app, MANAGER_PORTS[name]))

        asyncio.run(self._serve_all(apps))

    async def _serve_all(self, apps: list[tuple[str, Any, int]]) -> None:
        """Run all uvicorn servers concurrently."""
        servers: list[uvicorn.Server] = []
        for _name, app, port in apps:
            config = uvicorn.Config(
                app,
                host="127.0.0.1",
                port=port,
                log_level="info",
            )
            server = uvicorn.Server(config)
            servers.append(server)

        # Install signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()

        def _shutdown() -> None:
            for s in servers:
                s.should_exit = True

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _shutdown)
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                signal.signal(sig, lambda *_: _shutdown())

        # Start all servers concurrently
        await asyncio.gather(*(server.serve() for server in servers))

    def stop(self) -> None:
        """Request a graceful shutdown (for programmatic usage)."""
        sys.exit(0)
