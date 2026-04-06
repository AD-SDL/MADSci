"""MADSci CLI - Unified command-line interface for MADSci operations.

This module provides the main entry point for the MADSci CLI, offering a
comprehensive toolkit for building and operating self-driving laboratories.
"""

import importlib
import importlib.metadata
from typing import ClassVar

import click
from rich.console import Console

try:
    __version__ = importlib.metadata.version("madsci_client")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.6.2"

# Lazy command registry: maps command names to (module_path, attr_name) tuples.
# Commands are only imported when actually invoked.
_LAZY_COMMANDS: dict[str, tuple[str, str]] = {
    "version": ("madsci.client.cli.commands.version", "version"),
    "doctor": ("madsci.client.cli.commands.doctor", "doctor"),
    "status": ("madsci.client.cli.commands.status", "status"),
    "logs": ("madsci.client.cli.commands.logs", "logs"),
    "tui": ("madsci.client.cli.commands.tui", "tui"),
    "registry": ("madsci.client.cli.commands.registry", "registry"),
    "migrate": ("madsci.client.cli.commands.migrate", "migrate"),
    "new": ("madsci.client.cli.commands.new", "new"),
    "add": ("madsci.client.cli.commands.add", "add"),
    "start": ("madsci.client.cli.commands.start", "start"),
    "stop": ("madsci.client.cli.commands.stop", "stop"),
    "init": ("madsci.client.cli.commands.init", "init"),
    "validate": ("madsci.client.cli.commands.validate", "validate"),
    "run": ("madsci.client.cli.commands.run", "run"),
    "completion": ("madsci.client.cli.commands.completion", "completion"),
    "backup": ("madsci.client.cli.commands.backup", "backup"),
    "commands": ("madsci.client.cli.commands.commands", "commands"),
    "config": ("madsci.client.cli.commands.config", "config"),
    "workflow": ("madsci.client.cli.commands.workflow", "workflow"),
}


class _LazyMadsciContext:
    """Proxy that defers MadsciContext instantiation until first attribute access.

    This prevents Pydantic's CliSettingsSource from parsing sys.argv (and
    intercepting --help) during Click's argument processing phase. The real
    MadsciContext is only created when a command callback actually needs it.
    """

    def __init__(self, lab_url_override: str | None = None) -> None:
        object.__setattr__(self, "_ctx", None)
        object.__setattr__(self, "_lab_url_override", lab_url_override)

    def _ensure_init(self) -> "MadsciContext":  # noqa: F821
        ctx = object.__getattribute__(self, "_ctx")
        if ctx is None:
            from madsci.common.context import GlobalMadsciContext
            from madsci.common.types.context_types import MadsciContext

            ctx = MadsciContext(_cli_parse_args=[])
            lab_url = object.__getattribute__(self, "_lab_url_override")
            if lab_url is not None:
                ctx.lab_server_url = lab_url  # type: ignore[assignment]
            GlobalMadsciContext.set_context(ctx)
            object.__setattr__(self, "_ctx", ctx)
        return ctx

    def __getattr__(self, name: str) -> object:
        return getattr(self._ensure_init(), name)

    def __setattr__(self, name: str, value: object) -> None:
        setattr(self._ensure_init(), name, value)

    def __repr__(self) -> str:
        ctx = object.__getattribute__(self, "_ctx")
        if ctx is None:
            return "<LazyMadsciContext (not yet initialized)>"
        return repr(ctx)


class AliasedGroup(click.Group):
    """Click group that supports command aliases and lazy command loading.

    Commands are imported only when they are actually invoked or when
    help text is requested, reducing CLI startup time.
    """

    _aliases: ClassVar[dict[str, str]] = {
        "n": "new",
        "s": "status",
        "l": "logs",
        "doc": "doctor",
        "val": "validate",
        "ui": "tui",
        "cmd": "commands",
        "cfg": "config",
        "wf": "workflow",
    }

    def list_commands(self, ctx: click.Context) -> list[str]:
        """List all available commands, including lazy ones."""
        # Combine eagerly registered commands with lazy ones
        eager = set(super().list_commands(ctx))
        return sorted(eager | set(_LAZY_COMMANDS.keys()))

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        """Resolve command aliases and lazily import commands."""
        # Check if it's an alias
        if cmd_name in self._aliases:
            cmd_name = self._aliases[cmd_name]

        # Try eagerly registered commands first
        cmd = super().get_command(ctx, cmd_name)
        if cmd is not None:
            return cmd

        # Lazily import the command
        if cmd_name in _LAZY_COMMANDS:
            module_path, attr_name = _LAZY_COMMANDS[cmd_name]
            module = importlib.import_module(module_path)
            cmd = getattr(module, attr_name)
            # Cache it so we don't import again
            self.add_command(cmd, cmd_name)
            return cmd

        return None

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        """Resolve command, handling aliases."""
        _, cmd, args = super().resolve_command(ctx, args)
        return cmd.name if cmd else None, cmd, args


@click.group(cls=AliasedGroup)
@click.option(
    "--lab-url",
    envvar="LAB_SERVER_URL",
    default=None,
    help="Lab manager URL.",
)
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase verbosity (can be repeated: -vv, -vvv).",
)
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    help="Suppress non-essential output.",
)
@click.option(
    "--no-color",
    is_flag=True,
    envvar="NO_COLOR",
    help="Disable colored output.",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output in JSON format (where applicable).",
)
@click.option(
    "--yaml",
    "yaml_output",
    is_flag=True,
    help="Output in YAML format (where applicable).",
)
@click.version_option(version=__version__, prog_name="madsci")
@click.pass_context
def madsci(
    ctx: click.Context,
    lab_url: str | None,
    verbose: int,
    quiet: bool,
    no_color: bool,
    json_output: bool,
    yaml_output: bool,
) -> None:
    """MADSci - Modular Autonomous Discovery for Science.

    A comprehensive toolkit for building and operating self-driving laboratories.

    \b
    Quick start:
        madsci init           Initialize a new lab
        madsci start          Start all services
        madsci status         Check service status
        madsci tui            Launch interactive interface

    \b
    For more information:
        madsci <command> --help
        https://ad-sdl.github.io/MADSci/
    """
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Defer MadsciContext creation so Pydantic's CliSettingsSource doesn't
    # parse sys.argv and intercept --help before Click can handle it.
    ctx.obj["context"] = _LazyMadsciContext(lab_url_override=lab_url)

    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet
    ctx.obj["json"] = json_output
    ctx.obj["yaml"] = yaml_output
    ctx.obj["no_color"] = no_color

    # Create console with appropriate settings
    ctx.obj["console"] = Console(
        no_color=no_color,
        quiet=quiet,
        force_terminal=None,  # Auto-detect
    )


def main() -> None:
    """CLI entry point."""
    madsci()


if __name__ == "__main__":
    main()
