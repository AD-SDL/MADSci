"""Common code for the MADSci project."""

from rich.traceback import install as _install_rich_traceback

# Install rich traceback handler globally for prettier exception output.
# This provides syntax-highlighted tracebacks with more context when exceptions occur.
_install_rich_traceback(
    show_locals=True,  # Show local variables in tracebacks
    width=120,  # Console width
    extra_lines=3,  # Context lines around the error
    word_wrap=True,  # Wrap long lines
)
