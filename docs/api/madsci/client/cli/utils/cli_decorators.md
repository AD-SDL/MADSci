Module madsci.client.cli.utils.cli_decorators
=============================================
Reusable Click decorators for MADSci CLI commands.

Provides composable decorators that add common options (output format,
service URL, timeout) and error-handling wrappers so individual commands
don't need to duplicate boilerplate.

Functions
---------

`output_options(f: F) ‑> ~F`
:   Add ``--json``, ``--yaml``, and ``-q``/``--quiet`` output-format flags.
    
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

`resolve_service_url(ctx: click.Context, explicit_url: str | None, context_attr: str, default_port: int) ‑> str`
:   Resolve a service URL from explicit option, context, or default.
    
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

`service_url_option(service_name: str, envvar: str, default_port: int) ‑> Callable[[~F], ~F]`
:   Create a ``--<service>-url`` Click option with env-var fallback.
    
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

`timeout_option(default: float = 10.0) ‑> Callable[[~F], ~F]`
:   Add a ``--timeout`` option (in seconds).
    
    Args:
        default: Default timeout value.
    
    Returns:
        Click decorator that injects ``timeout`` as a keyword argument.

`with_service_error_handling(f: F) ‑> ~F`
:   Catch service and HTTP exceptions, print a friendly CLI message.
    
    Translates :class:`MadsciServiceError` and raw ``httpx`` transport
    exceptions into user-friendly error output and exits with code 1.
    
    Usage::
    
        @cli.command()
        @with_service_error_handling
        def my_command():
            ...