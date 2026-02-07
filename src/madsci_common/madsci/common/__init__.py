"""Common code for the MADSci project."""

import os


def _setup_rich_tracebacks() -> None:
    """
    Install rich traceback handler for prettier exception output.

    Controlled by environment variables:
    - DISABLE_MADSCI_RICH_TRACEBACKS: Set to "1" or "true" to disable
      (default: enabled for better developer experience)
    - MADSCI_RICH_TRACEBACKS_SHOW_LOCALS: Set to "1" or "true" to show local
      variables in tracebacks (default: disabled for security - can leak secrets)

    Note:
        show_locals is disabled by default to prevent accidental exposure of
        sensitive data (tokens, passwords) that may be present in local variables
        during exceptions.
    """
    disable_rich = os.environ.get("DISABLE_MADSCI_RICH_TRACEBACKS", "").lower() in (
        "1",
        "true",
    )
    if disable_rich:
        return

    from rich.traceback import install as _install_rich_traceback  # noqa: PLC0415

    # show_locals is disabled by default for security - can leak sensitive data
    show_locals = os.environ.get("MADSCI_RICH_TRACEBACKS_SHOW_LOCALS", "").lower() in (
        "1",
        "true",
    )

    _install_rich_traceback(
        show_locals=show_locals,
        width=120,  # Console width
        extra_lines=3,  # Context lines around the error
        word_wrap=True,  # Wrap long lines
    )


_setup_rich_tracebacks()
