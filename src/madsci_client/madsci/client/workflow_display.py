"""Rich workflow status display for terminal, Jupyter, and plain text environments.

Provides a WorkflowDisplay class that renders workflow progress with automatic
environment detection and in-place updates.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Literal, Optional

from madsci.common.types.action_types import ActionStatus

if TYPE_CHECKING:
    from madsci.common.types.workflow_types import Workflow

# Status colors for Rich markup and HTML
STATUS_COLORS: dict[ActionStatus, str] = {
    ActionStatus.SUCCEEDED: "green",
    ActionStatus.FAILED: "red",
    ActionStatus.CANCELLED: "yellow",
    ActionStatus.RUNNING: "blue",
    ActionStatus.PAUSED: "yellow",
    ActionStatus.NOT_STARTED: "dim",
    ActionStatus.NOT_READY: "dim",
    ActionStatus.UNKNOWN: "dim",
}

# Unicode icons for step status
STEP_ICONS: dict[ActionStatus, str] = {
    ActionStatus.SUCCEEDED: "\u2713",  # ✓
    ActionStatus.FAILED: "\u2717",  # ✗
    ActionStatus.RUNNING: "\u25b6",  # ▶
    ActionStatus.PAUSED: "\u2016",  # ‖
    ActionStatus.CANCELLED: "\u25cb",  # ○
    ActionStatus.NOT_STARTED: "\u25cb",  # ○
    ActionStatus.NOT_READY: "\u25cb",  # ○
    ActionStatus.UNKNOWN: "?",
}

DisplayMode = Literal["auto", "rich", "jupyter", "plain"]


def _detect_mode() -> Literal["rich", "jupyter", "plain"]:
    """Auto-detect the best display mode for the current environment."""
    try:
        from IPython import get_ipython  # noqa: PLC0415

        shell = get_ipython()
        if shell is not None and shell.__class__.__name__ == "ZMQInteractiveShell":
            return "jupyter"
    except ImportError:
        pass

    try:
        import rich  # noqa: F401, PLC0415

        return "rich"
    except ImportError:
        pass

    return "plain"


def _format_duration(td: Optional[timedelta]) -> str:
    """Format a timedelta as a human-readable duration string."""
    if td is None:
        return ""
    total_seconds = int(td.total_seconds())
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}h {minutes:02d}m {seconds:02d}s"
    if minutes:
        return f"{minutes:02d}m {seconds:02d}s"
    return f"{seconds}s"


def _elapsed_since(start: Optional[datetime]) -> Optional[timedelta]:
    """Calculate elapsed time since a given start time."""
    if start is None:
        return None
    # Match tz-awareness: naive start (UTC from MongoDB) uses naive now (UTC),
    # tz-aware start uses tz-aware now.
    if start.tzinfo is None:
        return datetime.utcnow() - start
    from madsci.common.utils import localnow  # noqa: PLC0415

    return localnow() - start


def _writeln(text: str) -> None:
    """Write a line to stdout (bypasses ruff T201 print check)."""
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


def _step_duration_label(step: object) -> str:
    """Return a duration label for a step: elapsed for running, final for completed."""
    if step.status == ActionStatus.RUNNING:
        return _format_duration(_elapsed_since(step.start_time)) or "..."
    if step.duration:
        return _format_duration(step.duration)
    return ""


class WorkflowDisplay:
    """Renders workflow progress with Rich Live, Jupyter HTML, or plain text.

    Parameters
    ----------
    mode : DisplayMode
        Display backend. "auto" detects the environment automatically.
    """

    def __init__(self, mode: DisplayMode = "auto") -> None:
        """Initialize the display with the given mode."""
        self._requested_mode = mode
        self._mode: Literal["rich", "jupyter", "plain"] = (
            _detect_mode() if mode == "auto" else mode
        )
        # Rich Live context
        self._live: Optional[object] = None
        # Jupyter display handle
        self._jupyter_handle: Optional[object] = None
        # Track previous plain-text output to avoid repeating identical lines
        self._last_plain_line: Optional[str] = None

    @property
    def mode(self) -> Literal["rich", "jupyter", "plain"]:
        """The resolved display mode."""
        return self._mode

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Begin the live display (Rich) or prepare the display handle (Jupyter)."""
        if self._mode == "rich":
            self._start_rich()
        elif self._mode == "jupyter":
            self._start_jupyter()
        # plain: nothing to prepare

    def update(self, wf: Workflow) -> None:
        """Update the display with the current workflow state."""
        if self._mode == "rich":
            self._update_rich(wf)
        elif self._mode == "jupyter":
            self._update_jupyter(wf)
        else:
            self._update_plain(wf)

    def stop(self, wf: Workflow) -> None:
        """Finalize the display and clean up resources."""
        if self._mode == "rich":
            self._stop_rich(wf)
        elif self._mode == "jupyter":
            self._stop_jupyter(wf)
        else:
            self._stop_plain(wf)

    # ------------------------------------------------------------------
    # Rich backend
    # ------------------------------------------------------------------

    def _start_rich(self) -> None:
        """Start the Rich Live display."""
        from rich.live import Live  # noqa: PLC0415

        self._live = Live("", refresh_per_second=4)
        self._live.start()

    def _update_rich(self, wf: Workflow) -> None:
        """Update the Rich Live display with current workflow state."""
        if self._live is None:
            return
        self._live.update(self._build_rich_renderable(wf))

    def _stop_rich(self, wf: Workflow) -> None:
        """Stop the Rich Live display and print final status."""
        if self._live is None:
            return
        self._live.update(self._build_rich_renderable(wf))
        self._live.stop()
        self._live = None
        self._print_rich_final(wf)

    def _build_rich_renderable(self, wf: Workflow) -> object:
        """Build a Rich Table renderable for the current workflow state."""
        from rich.box import ROUNDED  # noqa: PLC0415
        from rich.table import Table  # noqa: PLC0415
        from rich.text import Text  # noqa: PLC0415

        elapsed = _format_duration(_elapsed_since(wf.start_time))
        total = len(wf.steps)
        completed = wf.completed_steps
        status_desc = wf.status.description

        # Build outer table (single column, acts as a panel)
        outer = Table(
            title=f"Workflow: {wf.name or wf.workflow_id}",
            box=ROUNDED,
            show_header=False,
            title_style="bold",
            expand=False,
            padding=(0, 1),
        )
        outer.add_column(ratio=1)

        # Status line with paused/queued indicator
        status_line = Text()
        status_line.append(f"Status: {status_desc}")
        if wf.status.paused:
            status_line.append("  \u23f8 PAUSED", style="bold yellow")
        elif wf.status.queued:
            status_line.append("  \u23f3 QUEUED", style="bold cyan")
        if elapsed:
            status_line.append(f"  Duration: {elapsed}")
        outer.add_row(status_line)

        # Progress bar
        if total > 0:
            bar_width = 30
            filled = int(bar_width * completed / total)
            bar = "\u2588" * filled + "\u2591" * (bar_width - filled)
            outer.add_row(Text(f"Progress: {bar} {completed}/{total} steps"))

        # Blank separator row
        outer.add_row(Text(""))

        # Step rows
        for i, step in enumerate(wf.steps):
            icon = STEP_ICONS.get(step.status, "?")
            color = STATUS_COLORS.get(step.status, "dim")
            step_name = step.name or step.action or f"Step {i + 1}"
            key_label = f" [{step.key}]" if step.key else ""
            node_label = f"({step.node})" if step.node else ""
            dur = _step_duration_label(step)

            line = Text()
            line.append(f"  {icon} ", style=color)
            line.append(
                f"{i + 1}. {step_name}",
                style="bold" if step.status == ActionStatus.RUNNING else "",
            )
            if key_label:
                line.append(key_label, style="italic dim")
            line.append(" " * max(1, 32 - len(step_name) - len(key_label)))
            if node_label:
                line.append(f"{node_label:<16s} ", style="dim")
            if dur:
                line.append(dur, style="dim")
            outer.add_row(line)

        return outer

    def _print_rich_final(self, wf: Workflow) -> None:
        """Print a Rich panel summarizing the final workflow state."""
        from rich.console import Console  # noqa: PLC0415
        from rich.panel import Panel  # noqa: PLC0415
        from rich.text import Text  # noqa: PLC0415

        elapsed = _format_duration(wf.duration)
        if wf.status.completed:
            style = "bold green"
            title = "Workflow Completed"
            body = f"{wf.name or wf.workflow_id} finished successfully"
        elif wf.status.failed:
            style = "bold red"
            title = "Workflow Failed"
            step_idx = wf.status.current_step_index
            step_name = (
                wf.steps[step_idx].name
                if step_idx < len(wf.steps)
                else f"step {step_idx}"
            )
            body = f"{wf.name or wf.workflow_id} failed on step {step_idx}: {step_name}"
        elif wf.status.cancelled:
            style = "bold yellow"
            title = "Workflow Cancelled"
            body = f"{wf.name or wf.workflow_id} was cancelled"
        else:
            style = "dim"
            title = "Workflow Ended"
            body = wf.status.description

        if elapsed:
            body += f" ({elapsed})"

        console = Console()
        console.print()
        console.print(Panel(Text(body), title=title, style=style, expand=False))

    # ------------------------------------------------------------------
    # Jupyter backend
    # ------------------------------------------------------------------

    def _start_jupyter(self) -> None:
        """Initialize the Jupyter display handle."""
        from IPython.display import HTML, display  # noqa: PLC0415

        self._jupyter_handle = display(HTML(""), display_id=True)

    def _update_jupyter(self, wf: Workflow) -> None:
        """Update the Jupyter display with current workflow state."""
        if self._jupyter_handle is None:
            return
        from IPython.display import HTML  # noqa: PLC0415

        self._jupyter_handle.update(HTML(self._build_jupyter_html(wf)))

    def _stop_jupyter(self, wf: Workflow) -> None:
        """Render the final Jupyter display and release the handle."""
        if self._jupyter_handle is None:
            return
        from IPython.display import HTML  # noqa: PLC0415

        self._jupyter_handle.update(HTML(self._build_jupyter_html(wf)))
        self._jupyter_handle = None

    def _build_jupyter_html(self, wf: Workflow) -> str:
        """Build an HTML string for Jupyter display of workflow state."""
        elapsed = _format_duration(_elapsed_since(wf.start_time))
        total = len(wf.steps)
        completed = wf.completed_steps

        # Overall status color
        if wf.status.completed:
            border_color = "#28a745"
        elif wf.status.failed:
            border_color = "#dc3545"
        elif wf.status.cancelled or wf.status.paused:
            border_color = "#ffc107"
        elif wf.status.running:
            border_color = "#007bff"
        else:
            border_color = "#6c757d"

        # Paused/queued badge
        badge = ""
        if wf.status.paused:
            badge = ' <span style="background:#ffc107;color:#000;padding:1px 6px;border-radius:3px;font-size:11px;margin-left:8px">\u23f8 PAUSED</span>'
        elif wf.status.queued:
            badge = ' <span style="background:#17a2b8;color:#fff;padding:1px 6px;border-radius:3px;font-size:11px;margin-left:8px">\u23f3 QUEUED</span>'

        pct = int(100 * completed / total) if total > 0 else 0

        rows = []
        for i, step in enumerate(wf.steps):
            icon = STEP_ICONS.get(step.status, "?")
            color = {
                ActionStatus.SUCCEEDED: "#28a745",
                ActionStatus.FAILED: "#dc3545",
                ActionStatus.RUNNING: "#007bff",
                ActionStatus.PAUSED: "#ffc107",
                ActionStatus.CANCELLED: "#ffc107",
            }.get(step.status, "#6c757d")
            step_name = step.name or step.action or f"Step {i + 1}"
            key_label = (
                f' <span style="color:#6c757d;font-style:italic">'
                f"[{_html_escape(step.key)}]</span>"
                if step.key
                else ""
            )
            node_label = step.node or ""
            dur = _step_duration_label(step)

            rows.append(
                f'<tr><td style="color:{color};text-align:center;width:30px">'
                f"{icon}</td>"
                f"<td><b>{i + 1}.</b> {_html_escape(step_name)}{key_label}</td>"
                f'<td style="color:#6c757d">{_html_escape(node_label)}</td>'
                f'<td style="color:#6c757d;text-align:right">{dur}</td></tr>'
            )

        table_rows = "\n".join(rows)

        return (
            f'<div style="font-family:monospace;border:2px solid {border_color};'
            f'border-radius:8px;padding:12px;max-width:600px;margin:8px 0">\n'
            f'  <div style="font-weight:bold;font-size:14px;margin-bottom:4px">'
            f"{_html_escape(wf.name or str(wf.workflow_id))}</div>\n"
            f'  <div style="color:#6c757d;margin-bottom:8px">\n'
            f"    {_html_escape(wf.status.description)}"
            f"{f' &mdash; {elapsed}' if elapsed else ''}{badge}\n"
            f"  </div>\n"
            f'  <div style="background:#e9ecef;border-radius:4px;height:8px;'
            f'margin-bottom:10px">\n'
            f'    <div style="background:{border_color};width:{pct}%;height:100%;'
            f'border-radius:4px;transition:width 0.3s"></div>\n'
            f"  </div>\n"
            f'  <div style="color:#6c757d;font-size:12px;margin-bottom:6px">'
            f"{completed}/{total} steps</div>\n"
            f'  <table style="width:100%;border-collapse:collapse;font-size:13px">\n'
            f"    {table_rows}\n"
            f"  </table>\n"
            f"</div>"
        )

    # ------------------------------------------------------------------
    # Plain text backend
    # ------------------------------------------------------------------

    def _update_plain(self, wf: Workflow) -> None:
        """Write a status line to stdout if it has changed."""
        total = len(wf.steps)
        completed = wf.completed_steps
        step_idx = wf.status.current_step_index
        if step_idx < total:
            step = wf.steps[step_idx]
            step_name = step.name or step.action or f"Step {step_idx + 1}"
            key_label = f" [{step.key}]" if step.key else ""
            node_label = f" ({step.node})" if step.node else ""
            dur = _step_duration_label(step)
            dur_label = f" {dur}" if dur else ""
        else:
            step_name = "Workflow End"
            key_label = ""
            node_label = ""
            dur_label = ""

        # Paused/queued indicator
        state_flag = ""
        if wf.status.paused:
            state_flag = " [PAUSED]"
        elif wf.status.queued:
            state_flag = " [QUEUED]"

        line = (
            f"{wf.name or wf.workflow_id}: {wf.status.description}"
            f" \u2014 {step_name}{key_label}{node_label}{dur_label}"
            f" [{completed}/{total}]{state_flag}"
        )
        if line != self._last_plain_line:
            _writeln(line)
            self._last_plain_line = line

    def _stop_plain(self, wf: Workflow) -> None:
        """Write a final summary line for the plain text backend."""
        elapsed = _format_duration(wf.duration)
        suffix = f" ({elapsed})" if elapsed else ""
        if wf.status.completed:
            _writeln(f"{wf.name or wf.workflow_id}: Completed Successfully{suffix}")
        elif wf.status.failed:
            step_idx = wf.status.current_step_index
            step_name = (
                wf.steps[step_idx].name
                if step_idx < len(wf.steps)
                else f"step {step_idx}"
            )
            _writeln(
                f"{wf.name or wf.workflow_id}: Failed on step {step_idx}:"
                f" {step_name}{suffix}"
            )
        elif wf.status.cancelled:
            _writeln(f"{wf.name or wf.workflow_id}: Cancelled{suffix}")

    # ------------------------------------------------------------------
    # Error prompt
    # ------------------------------------------------------------------

    def format_error_prompt(self, wf: Workflow) -> str:
        """Build a formatted error prompt string for user input."""
        status_label = "Failed" if wf.status.failed else "Cancelled"

        if self._mode == "rich":
            from rich.console import Console  # noqa: PLC0415
            from rich.panel import Panel  # noqa: PLC0415
            from rich.text import Text  # noqa: PLC0415

            console = Console()
            body = Text()
            body.append(
                f"Workflow {status_label}\n\n",
                style="bold red" if wf.status.failed else "bold yellow",
            )
            body.append("Options:\n", style="bold")
            body.append(
                "  \u2022 Enter a step index (0-based) to retry from that step\n"
            )
            body.append("  \u2022 Enter -1 to retry from the current step\n")
            body.append("  \u2022 Enter 'c' or press Enter to continue\n")
            console.print(Panel(body, title="Workflow Error", expand=False))
            return ""

        return (
            f"\nWorkflow {status_label}.\n"
            "Options:\n"
            "- Retry from a specific step (Enter the step index, e.g., 1;"
            " 0 for the first step; -1 for the current step)\n"
            "- Enter 'c' or press Enter to continue\n"
        )


def _html_escape(s: str) -> str:
    """Minimal HTML escaping for display text."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
