"""CLI utilities for MADSci.

This module provides common utilities for CLI commands, including
output formatting, service health checking, shared formatting, and
reusable Click decorators.
"""

from madsci.client.cli.utils.output import (
    ColumnDef,
    OutputFormat,
    determine_output_format,
    error,
    get_console,
    info,
    output_result,
    success,
    warning,
)

__all__ = [
    "ColumnDef",
    "OutputFormat",
    "determine_output_format",
    "error",
    "get_console",
    "info",
    "output_result",
    "success",
    "warning",
]
