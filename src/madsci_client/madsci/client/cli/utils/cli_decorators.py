"""Reusable Click decorators for MADSci CLI commands.

Provides composable decorators that add common options (output format,
service URL, timeout) and error-handling wrappers so individual commands
don't need to duplicate boilerplate.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, TypeVar

import click
from madsci.common.types.error_types import (
    MadsciServiceError,
    ServiceResponseError,
    ServiceTimeoutError,
    ServiceUnavailableError,
)

F = TypeVar("F", bound=Callable[..., Any])


# ---------------------------------------------------------------------------
# Output-format options
# ---------------------------------------------------------------------------


def output_options(f: F) -> F:
    """Add ``--json``, ``--yaml``, and ``-q``/``--quiet`` output-format flags.

    These options are stored in ``ctx.obj`` so that
    :func:`~madsci.client.cli.utils.output.determine_output_format` can
    read them.  They intentionally mirror the flags on the top-level
    ``madsci`` group, but can be applied to individual sub-commands that
    need standalone format selection.

    Usage::

        @cli.command()
        @output_options
        @click.pass_context
        def my_command(ctx):
            fmt = determine_output_format(ctx)
    """

    @click.option("--json", "json_flag", is_flag=True, help="Output in JSON format.")
    @click.option("--yaml", "yaml_flag", is_flag=True, help="Output in YAML format.")
    @click.option("-q", "--quiet", "quiet_flag", is_flag=True, help="Minimal output.")
    @functools.wraps(f)
    def wrapper(
        *args: Any,
        json_flag: bool = False,
        yaml_flag: bool = False,
        quiet_flag: bool = False,
        **kwargs: Any,
    ) -> Any:
        ctx = click.get_current_context()
        ctx.ensure_object(dict)
        # Merge into ctx.obj (top-level flags may already be set)
        if json_flag:
            ctx.obj["json"] = True
        if yaml_flag:
            ctx.obj["yaml"] = True
        if quiet_flag:
            ctx.obj["quiet"] = True
        return f(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Service-URL option factory
# ---------------------------------------------------------------------------


def service_url_option(
    service_name: str,
    envvar: str,
    default_port: int,
) -> Callable[[F], F]:
    """Create a ``--<service>-url`` Click option with env-var fallback.

    Args:
        service_name: Hyphenated service name (e.g. ``"event-manager"``).
        envvar: Environment variable name for the URL (e.g. ``"EVENT_SERVER_URL"``).
        default_port: Default localhost port number.

    Returns:
        Click decorator that injects the URL as a keyword argument named
        ``<service_name_underscored>_url``.

    Usage::

        @cli.command()
        @service_url_option("event-manager", "EVENT_SERVER_URL", 8001)
        def my_command(event_manager_url: str):
            ...
    """
    param_name = service_name.replace("-", "_") + "_url"
    default_url = f"http://localhost:{default_port}/"

    def decorator(f: F) -> F:
        return click.option(  # type: ignore[return-value]
            f"--{service_name}-url",
            param_name,
            envvar=envvar,
            default=default_url,
            show_default=True,
            help=f"URL for the {service_name.replace('-', ' ')} service.",
        )(f)

    return decorator


# ---------------------------------------------------------------------------
# Service-URL resolution helper
# ---------------------------------------------------------------------------


def resolve_service_url(
    ctx: click.Context,
    explicit_url: str | None,
    context_attr: str,
    default_port: int,
) -> str:
    """Resolve a service URL from explicit option, context, or default.

    Priority order:
    1. ``explicit_url`` (from a CLI option) — highest precedence.
    2. The named attribute on the ``MadsciContext`` stored in ``ctx.obj["context"]``.
    3. ``http://localhost:<default_port>/`` — fallback default.

    Args:
        ctx: Click context.
        explicit_url: URL provided via CLI option (takes precedence).
        context_attr: Attribute name on MadsciContext (e.g. ``"workcell_server_url"``).
        default_port: Default localhost port number.

    Returns:
        Resolved URL string with trailing slash.
    """
    if explicit_url:
        return explicit_url
    context = ctx.obj.get("context") if ctx.obj else None
    if context:
        url = getattr(context, context_attr, None)
        if url:
            return str(url)
    return f"http://localhost:{default_port}/"


# ---------------------------------------------------------------------------
# Timeout option
# ---------------------------------------------------------------------------


def timeout_option(default: float = 10.0) -> Callable[[F], F]:
    """Add a ``--timeout`` option (in seconds).

    Args:
        default: Default timeout value.

    Returns:
        Click decorator that injects ``timeout`` as a keyword argument.
    """

    def decorator(f: F) -> F:
        return click.option(  # type: ignore[return-value]
            "--timeout",
            type=float,
            default=default,
            show_default=True,
            help="Request timeout in seconds.",
        )(f)

    return decorator


# ---------------------------------------------------------------------------
# Service-error handling wrapper
# ---------------------------------------------------------------------------


def with_service_error_handling(f: F) -> F:  # noqa: C901
    """Catch service and HTTP exceptions, print a friendly CLI message.

    Translates :class:`MadsciServiceError` and raw ``httpx`` transport
    exceptions into user-friendly error output and exits with code 1.

    Usage::

        @cli.command()
        @with_service_error_handling
        def my_command():
            ...
    """

    @functools.wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        import httpx

        try:
            return f(*args, **kwargs)
        except ServiceUnavailableError as exc:
            _print_service_error(
                exc,
                "Service unavailable",
                "Is the service running? Check with 'madsci status'.",
            )
        except ServiceTimeoutError as exc:
            _print_service_error(
                exc,
                "Service timeout",
                "The service did not respond in time. Try increasing --timeout.",
            )
        except ServiceResponseError as exc:
            detail = f"HTTP {exc.status_code}"
            if exc.response_body:
                detail += f": {exc.response_body[:200]}"
            _print_service_error(exc, "Service error", detail)
        except MadsciServiceError as exc:
            _print_service_error(exc, "Service error", None)
        except httpx.ConnectError as exc:
            url = str(exc.request.url) if exc.request else "unknown"
            _print_raw_error(
                f"Connection refused: Could not connect to {url}",
                "Is the service running? Check with 'madsci status'.",
            )
        except httpx.TimeoutException as exc:
            url = str(exc.request.url) if exc.request else "unknown"
            _print_raw_error(
                f"Request timed out: {url}",
                "The service did not respond in time. Try increasing --timeout.",
            )
        except httpx.HTTPStatusError as exc:
            url = str(exc.request.url) if exc.request else "unknown"
            body = exc.response.text[:200] if exc.response else ""
            detail = f"HTTP {exc.response.status_code} from {url}"
            if body:
                detail += f": {body}"
            _print_raw_error(detail, None)

    return wrapper  # type: ignore[return-value]


def _print_service_error(
    exc: MadsciServiceError,
    heading: str,
    hint: str | None,
) -> None:
    """Print a formatted service error and exit."""
    click.echo(click.style(f"\u2717 {heading}: {exc}", fg="red"), err=True)
    if hint:
        click.echo(click.style(f"  {hint}", fg="yellow"), err=True)
    raise SystemExit(1)


def _print_raw_error(
    message: str,
    hint: str | None,
) -> None:
    """Print a formatted error message (no MadsciServiceError) and exit."""
    click.echo(click.style(f"\u2717 {message}", fg="red"), err=True)
    if hint:
        click.echo(click.style(f"  {hint}", fg="yellow"), err=True)
    raise SystemExit(1)
