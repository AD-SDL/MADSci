"""Workflow detail screen for MADSci TUI.

Pushed screen showing workflow details, step progress, and control actions.
Opened when a workflow row is selected in :class:`WorkflowsScreen`.
"""

from __future__ import annotations

from typing import Any, ClassVar

from madsci.client.cli.tui.mixins import (
    ActionBarMixin,
    ServiceURLMixin,
    preserve_cursor,
)
from madsci.client.cli.tui.screens.step_detail import StepDetailScreen
from madsci.client.cli.tui.screens.workflows import (
    _build_progress_section,
    _build_timing_section,
    _get_workflow_status_name,
)
from madsci.client.cli.tui.widgets import (
    ActionBar,
    ActionDef,
    DetailPanel,
    DetailSection,
)
from madsci.client.cli.utils.formatting import (
    build_ownership_section,
    format_status_colored,
)
from madsci.client.workcell_client import WorkcellClient
from madsci.common.types.workflow_types import Workflow
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Label


class WorkflowDetailScreen(ActionBarMixin, ServiceURLMixin, Screen):
    """Screen showing details for a single workflow, pushed on top of WorkflowsScreen."""

    BINDINGS: ClassVar[list[BindingType]] = [
        ("r", "refresh", "Refresh"),
        ("p", "pause_workflow", "Pause"),
        ("u", "resume_workflow", "Resume"),
        ("c", "cancel_workflow", "Cancel"),
        ("t", "retry_workflow", "Retry"),
        ("s", "resubmit_workflow", "Resubmit"),
        ("escape", "go_back", "Back"),
    ]

    def __init__(
        self,
        workflow_id: str,
        workflow_data: Workflow,
        **kwargs: Any,
    ) -> None:
        """Initialize the detail screen.

        Args:
            workflow_id: Workflow ID.
            workflow_data: Workflow model instance.
        """
        super().__init__(**kwargs)
        self.workflow_id = workflow_id
        self.workflow_data = workflow_data
        self._workcell_client: WorkcellClient | None = None

    def _get_workcell_client(self) -> WorkcellClient:
        """Get or create the WorkcellClient instance."""
        if self._workcell_client is None:
            url = self.get_service_url("workcell_manager")
            self._workcell_client = WorkcellClient(
                workcell_server_url=url,
            )
        return self._workcell_client

    def compose(self) -> ComposeResult:
        """Compose the detail screen layout."""
        name = self.workflow_data.name or "Workflow"
        with VerticalScroll(id="main-content"):
            yield Label(f"[bold blue]Workflow: {name}[/bold blue]")
            yield Label("")
            yield DetailPanel(
                placeholder="Loading workflow details...",
                id="workflow-detail-panel",
            )
            yield Label("")

            with Vertical(id="steps-section"):
                yield Label("[bold]Steps[/bold]")
                yield DataTable(id="steps-table")

            yield Label("")
            yield ActionBar(
                actions=[
                    ActionDef("p", "Pause", "pause", variant="warning"),
                    ActionDef("u", "Resume", "resume", variant="success"),
                    ActionDef("c", "Cancel", "cancel", variant="error"),
                    ActionDef("t", "Retry", "retry", variant="warning"),
                    ActionDef("s", "Resubmit", "resubmit", variant="primary"),
                ],
                id="workflow-detail-action-bar",
            )
            yield Label("")
            yield Label("[dim]'r' refresh | 'Esc' back[/dim]")

    def on_mount(self) -> None:
        """Set up the steps table and render content."""
        steps_table = self.query_one("#steps-table", DataTable)
        steps_table.add_columns("#", "Name", "Action", "Node", "Status")
        steps_table.cursor_type = "row"

        self._render_details()
        self._render_steps()

    def _render_details(self) -> None:
        """Render the workflow detail panel."""
        panel = self.query_one("#workflow-detail-panel", DetailPanel)
        workflow = self.workflow_data
        status_name = _get_workflow_status_name(workflow.status)
        name = workflow.name or "Unknown"

        general_fields: dict[str, str] = {
            "ID": str(self.workflow_id),
            "Status": format_status_colored(status_name, workflow.status.description),
        }
        if workflow.label:
            general_fields["Label"] = str(workflow.label)

        sections: list[DetailSection] = [DetailSection("General", general_fields)]

        timing_section = _build_timing_section(workflow)
        if timing_section:
            sections.append(timing_section)

        if workflow.parameter_values:
            sections.append(
                DetailSection(
                    "Parameters",
                    {
                        str(k): str(v)[:100]
                        for k, v in workflow.parameter_values.items()
                    },
                )
            )

        if workflow.file_input_paths:
            sections.append(
                DetailSection(
                    "File Inputs",
                    {str(k): str(v) for k, v in workflow.file_input_paths.items()},
                )
            )

        ownership_items = build_ownership_section(
            workflow.model_dump(mode="json"),
        )
        if ownership_items:
            sections.append(DetailSection("Ownership", dict(ownership_items)))

        progress_section = _build_progress_section(workflow)
        if progress_section:
            sections.append(progress_section)

        panel.update_content(title=name, sections=sections)

    def _render_steps(self) -> None:
        """Render the steps table."""
        steps_table = self.query_one("#steps-table", DataTable)
        steps = self.workflow_data.steps

        with preserve_cursor(steps_table):
            steps_table.clear()

            if not steps:
                steps_table.add_row("-", "[dim]No steps[/dim]", "-", "-", "-")
                return

            for i, step in enumerate(steps):
                step_name = step.name or step.action or f"Step {i + 1}"
                action = step.action or "-"
                node = step.node or "-"
                status_display = format_status_colored(step.status.value)
                steps_table.add_row(str(i + 1), step_name, action, node, status_display)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle step row selection -- push step detail screen."""
        table = event.data_table
        row_key = event.row_key

        if not row_key or table.id != "steps-table":
            return

        steps = self.workflow_data.steps
        row = table.get_row(row_key)
        try:
            step_index = int(str(row[0])) - 1
        except (ValueError, IndexError):
            return

        if 0 <= step_index < len(steps):
            step_data = steps[step_index]
            if hasattr(step_data, "model_dump"):
                step_data = step_data.model_dump(mode="json")
            self.app.push_screen(
                StepDetailScreen(
                    workflow_id=self.workflow_id,
                    step_data=step_data,
                    step_index=step_index,
                )
            )

    async def _send_workflow_command(self, command: str) -> None:
        """Send a control command to this workflow.

        Args:
            command: Command to send (pause, resume, cancel, retry, resubmit).
        """
        try:
            client = self._get_workcell_client()
            command_methods = {
                "pause": client.async_pause_workflow,
                "resume": client.async_resume_workflow,
                "cancel": client.async_cancel_workflow,
                "retry": client.async_retry_workflow,
                "resubmit": client.async_resubmit_workflow,
            }
            method = command_methods.get(command)
            if method:
                await method(self.workflow_id)
                self.notify(f"Workflow {command} successful", timeout=2)
                await self.action_refresh()
            else:
                self.notify(f"Unknown command: {command}", timeout=3)
        except Exception as e:
            self.notify(f"Error: {e}", timeout=3)

    async def action_refresh(self) -> None:
        """Re-fetch workflow data and re-render."""
        try:
            client = self._get_workcell_client()
            workflow = await client.async_query_workflow(self.workflow_id)
            if workflow is not None:
                self.workflow_data = workflow
                self._render_details()
                self._render_steps()
                self.notify("Workflow refreshed", timeout=2)
                return
        except Exception:  # noqa: S110
            pass
        self.notify("Could not refresh workflow data", timeout=2)

    async def action_pause_workflow(self) -> None:
        """Pause this workflow."""
        await self._send_workflow_command("pause")

    async def action_resume_workflow(self) -> None:
        """Resume this workflow."""
        await self._send_workflow_command("resume")

    async def action_cancel_workflow(self) -> None:
        """Cancel this workflow."""
        await self._send_workflow_command("cancel")

    async def action_retry_workflow(self) -> None:
        """Retry this workflow."""
        await self._send_workflow_command("retry")

    async def action_resubmit_workflow(self) -> None:
        """Resubmit this workflow."""
        await self._send_workflow_command("resubmit")

    def _get_action_map(self) -> dict:
        """Return action map for the ActionBarMixin dispatcher."""
        return {
            "pause": self.action_pause_workflow,
            "resume": self.action_resume_workflow,
            "cancel": self.action_cancel_workflow,
            "retry": self.action_retry_workflow,
            "resubmit": self.action_resubmit_workflow,
        }

    def action_go_back(self) -> None:
        """Go back to the workflows list."""
        self.app.pop_screen()
