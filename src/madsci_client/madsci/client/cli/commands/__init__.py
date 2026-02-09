"""MADSci CLI commands.

This module contains all CLI command implementations.
"""

from madsci.client.cli.commands import (
    doctor,
    logs,
    migrate,
    new,
    registry,
    status,
    version,
)

__all__ = [
    "doctor",
    "logs",
    "migrate",
    "new",
    "registry",
    "status",
    "version",
]
