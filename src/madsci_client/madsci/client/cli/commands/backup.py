"""MADSci CLI backup command.

Re-exports the existing backup CLI (``madsci.common.backup_tools.cli``)
under the main ``madsci`` command for discoverability.
"""

from __future__ import annotations

import click


@click.group()
def backup() -> None:
    """Database backup management.

    Create, restore, and validate database backups for MADSci services.
    Supports both PostgreSQL and MongoDB with automatic type detection.

    \b
    Examples:
        madsci backup create  --db-url postgresql://localhost/resources
        madsci backup restore --backup ./backup.dump --db-url postgresql://localhost/resources
        madsci backup validate --backup ./backup.dump --db-url postgresql://localhost/resources
    """


def _register_subcommands() -> None:
    """Lazily register subcommands from the backup tools CLI."""
    from madsci.common.backup_tools.cli import madsci_backup

    # Copy subcommands from the existing backup CLI group
    for name, cmd in madsci_backup.commands.items():
        backup.add_command(cmd, name)


# Register on import so that ``--help`` works.
_register_subcommands()
