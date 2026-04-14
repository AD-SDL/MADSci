"""Action executor screen for MADSci TUI.

Provides an interactive screen for selecting and executing actions on
a MADSci node, with JSON argument input and result display.
"""

import asyncio
import json
from typing import Any, ClassVar

from madsci.client.cli.tui.widgets import DetailPanel, DetailSection
from madsci.client.cli.utils.formatting import format_status_colored
from madsci.client.node.rest_node_client import RestNodeClient
from madsci.common.types.action_types import ActionRequest, ActionResult, ActionStatus
from pydantic import AnyUrl
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Select


class ActionExecutorScreen(Screen):
    """Interactive action execution on a node.

    Allows the user to select an action from a dropdown, provide JSON
    arguments, execute the action, and view the result in a detail panel.
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        ("escape", "go_back", "Back"),
    ]

    def __init__(
        self,
        node_name: str,
        node_url: str,
        actions: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Initialize the action executor screen.

        Args:
            node_name: Name of the target node.
            node_url: Base URL of the target node.
            actions: Dict mapping action names to action definitions.
            **kwargs: Additional keyword arguments forwarded to Screen.
        """
        super().__init__(**kwargs)
        self.node_name = node_name
        self.node_url = node_url
        self.actions = actions
        self._node_client: RestNodeClient | None = None

    def _get_node_client(self) -> RestNodeClient:
        """Get or create the RestNodeClient instance."""
        if self._node_client is None:
            self._node_client = RestNodeClient(url=AnyUrl(self.node_url))
        return self._node_client

    def compose(self) -> ComposeResult:
        """Compose the action executor layout."""
        with VerticalScroll(id="main-content"):
            yield Label(f"[bold blue]Execute Action on {self.node_name}[/bold blue]")
            yield Label("")

            # Action selector
            yield Label("[bold]Select Action:[/bold]")
            options = [(name, name) for name in self.actions]
            yield Select(options, id="action-select", prompt="Choose an action...")
            yield Label("")

            # Description display
            yield Label(
                "[dim]Select an action to see its description[/dim]",
                id="action-description",
            )
            yield Label("")

            # Arguments input
            yield Label("[bold]Arguments (JSON):[/bold]")
            yield Input(placeholder='{"key": "value"}', id="args-input")
            yield Label("")

            # Execute button
            yield Button("Execute", id="execute-btn", variant="primary")
            yield Label("")

            # Result panel
            yield DetailPanel(
                placeholder="Result will appear here after execution",
                id="action-result",
            )
            yield Label("")
            yield Label("[dim]'Esc' back[/dim]")

    def on_select_changed(self, event: Select.Changed) -> None:
        """Update description when action selection changes.

        Args:
            event: The select changed event.
        """
        selected = event.value
        desc_label = self.query_one("#action-description", Label)

        if selected and selected != Select.BLANK:
            action_def = self.actions.get(str(selected), {})
            if isinstance(action_def, dict):
                desc = action_def.get("description", "No description available")
                # Show parameter info if available
                args = action_def.get("args", {})
                param_info = ""
                if args:
                    if isinstance(args, dict):
                        param_names = list(args.keys())
                    elif isinstance(args, list):
                        param_names = [
                            a.get("name", f"arg{i}") if isinstance(a, dict) else str(a)
                            for i, a in enumerate(args)
                        ]
                    else:
                        param_names = []
                    if param_names:
                        param_info = (
                            f"\n[dim]Parameters: {', '.join(param_names)}[/dim]"
                        )
                desc_label.update(f"[dim]{desc}[/dim]{param_info}")
            else:
                desc_label.update("[dim]No description available[/dim]")
        else:
            desc_label.update("[dim]Select an action to see its description[/dim]")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: The button pressed event.
        """
        if event.button.id == "execute-btn":
            self.run_worker(self._execute_action(), exclusive=True)

    async def _execute_action(self) -> None:
        """Execute the selected action on the node."""
        select = self.query_one("#action-select", Select)
        args_input = self.query_one("#args-input", Input)
        result_panel = self.query_one("#action-result", DetailPanel)
        execute_btn = self.query_one("#execute-btn", Button)

        action_name = select.value
        if not action_name or action_name == Select.BLANK:
            self.notify("Select an action first", timeout=2)
            return

        action_name = str(action_name)

        # Parse arguments
        args: dict[str, Any] = {}
        if args_input.value.strip():
            try:
                args = json.loads(args_input.value)
            except json.JSONDecodeError as e:
                self.notify(f"Invalid JSON: {e}", timeout=3)
                return

        # Execute action
        execute_btn.disabled = True
        try:
            client = self._get_node_client()
            action_request = ActionRequest(
                action_name=action_name,
                args=args,
            )

            # Send action (creates and starts it)
            result = await client.async_send_action(action_request)
            self.notify(f"Action started: {result.action_id}", timeout=2)

            # Poll for result (30s timeout)
            for _ in range(60):
                await asyncio.sleep(0.5)
                result = await client.async_get_action_result_by_name(
                    action_name,
                    result.action_id,
                    include_files=True,
                )
                if result.status.is_terminal:
                    self._show_result(result_panel, action_name, result)
                    return

            self.notify("Action timed out (30s)", timeout=3)

        except Exception as e:
            self.notify(f"Error: {e}", timeout=3)
        finally:
            execute_btn.disabled = False

    def _show_result(
        self,
        panel: DetailPanel,
        action_name: str,
        result: ActionResult,
    ) -> None:
        """Display the action result in the detail panel.

        Args:
            panel: The DetailPanel to update.
            action_name: Name of the executed action.
            result: ActionResult model instance from the node.
        """
        sections: list[DetailSection] = []

        # General result section
        action_status: ActionStatus = result.status
        status_value = action_status.value
        general: dict[str, str] = {
            "Action": action_name,
            "Status": format_status_colored(status_value, status_value),
        }
        if result.action_id:
            general["Action ID"] = str(result.action_id)
        sections.append(DetailSection("Result", general))

        # Data section
        data = result.json_result
        if data and isinstance(data, dict):
            sections.append(
                DetailSection(
                    "Data",
                    {str(k): str(v)[:200] for k, v in data.items()},
                )
            )

        # Files section
        files = result.files
        if files is not None:
            files_dict = files.model_dump() if hasattr(files, "model_dump") else {}
            if files_dict:
                sections.append(
                    DetailSection(
                        "Files",
                        {str(k): str(v)[:200] for k, v in files_dict.items()},
                    )
                )

        # Errors section
        if result.errors:
            error_fields: dict[str, str] = {}
            for i, e in enumerate(result.errors[:10]):
                err_msg = e.message or str(e)
                error_fields[f"Error {i + 1}"] = f"[red]{err_msg[:200]}[/red]"
            sections.append(DetailSection("Errors", error_fields))

        panel.update_content(title=f"Result: {action_name}", sections=sections)

    async def on_unmount(self) -> None:
        """Clean up client connections when screen is unmounted."""
        for attr_name in list(vars(self)):
            if attr_name.endswith("_client"):
                client = getattr(self, attr_name, None)
                if client is not None and hasattr(client, "close"):
                    client.close()

    def action_go_back(self) -> None:
        """Go back to the nodes screen."""
        self.app.pop_screen()
