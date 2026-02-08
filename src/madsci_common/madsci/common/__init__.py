"""Common code for the MADSci project."""


def _setup_rich_tracebacks() -> None:
    """
    Install rich traceback handler for prettier exception output.

    Controlled by MadsciDeveloperSettings (environment variables with MADSCI_ prefix):
    - MADSCI_DISABLE_RICH_TRACEBACKS: Set to true to disable
      (default: false, rich tracebacks are enabled for better developer experience)
    - MADSCI_RICH_TRACEBACKS_SHOW_LOCALS: Set to true to show local variables
      in tracebacks (default: false for security - can leak secrets)

    Note:
        show_locals is disabled by default to prevent accidental exposure of
        sensitive data (tokens, passwords) that may be present in local variables
        during exceptions.
    """
    from madsci.common.types.base_types import (  # noqa: PLC0415
        MadsciDeveloperSettings,
    )

    settings = MadsciDeveloperSettings()

    if settings.disable_rich_tracebacks:
        return

    from rich.traceback import install as _install_rich_traceback  # noqa: PLC0415

    _install_rich_traceback(
        show_locals=settings.rich_tracebacks_show_locals,
        width=120,  # Console width
        extra_lines=3,  # Context lines around the error
        word_wrap=True,  # Wrap long lines
    )


_setup_rich_tracebacks()
