"""TUI module for ExperimentTUI modality.

This module provides the Textual-based TUI application for running
experiments interactively.

Note: This module requires the `textual` package to be installed.
Install with: `pip install madsci[tui]` or `pip install textual`
"""

from .app import ExperimentTUIApp

__all__ = ["ExperimentTUIApp"]
