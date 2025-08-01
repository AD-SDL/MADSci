"""
Engine Class and associated helpers and data
"""

import concurrent
import copy
import importlib
import time
import traceback
from datetime import datetime
from typing import Any, Optional

from madsci.client.data_client import DataClient
from madsci.client.event_client import EventClient
from madsci.client.node.abstract_node_client import AbstractNodeClient
from madsci.client.resource_client import ResourceClient
from madsci.common.ownership import ownership_context
from madsci.common.types.action_types import ActionRequest, ActionResult, ActionStatus
from madsci.common.types.base_types import Error
from madsci.common.types.datapoint_types import FileDataPoint, ValueDataPoint
from madsci.common.types.event_types import Event, EventType
from madsci.common.types.node_types import Node, NodeStatus
from madsci.common.types.step_types import Step
from madsci.common.types.workflow_types import (
    Workflow,
)
from madsci.common.utils import threaded_daemon
from madsci.workcell_manager.state_handler import WorkcellStateHandler
from madsci.workcell_manager.workcell_utils import (
    find_node_client,
)
from madsci.workcell_manager.workflow_utils import cancel_active_workflows


class Engine:
    """
    Handles scheduling workflows and executing steps on the workcell.
    Pops incoming workflows off a redis-based queue and executes them.
    """

    def __init__(
        self,
        state_handler: WorkcellStateHandler,
    ) -> None:
        """Initialize the scheduler."""
        self.state_handler = state_handler
        self.workcell_definition = state_handler.get_workcell_definition()
        self.workcell_settings = self.state_handler.workcell_settings
        self.logger = EventClient(
            name=f"workcell.{self.workcell_definition.workcell_name}"
        )
        cancel_active_workflows(state_handler)
        scheduler_module = importlib.import_module(self.workcell_settings.scheduler)
        self.scheduler = scheduler_module.Scheduler(
            self.workcell_definition, self.state_handler
        )
        self.data_client = DataClient()
        self.resource_client = ResourceClient()
        self.logger.log_debug(self.data_client.url)
        with state_handler.wc_state_lock():
            state_handler.initialize_workcell_state(
                self.resource_client,
            )
        time.sleep(self.workcell_settings.cold_start_delay)
        self.logger.log_info("Engine initialized, waiting for workflows...")

    @threaded_daemon
    def spin(self) -> None:
        """
        Continuously loop, updating node states every Config.update_interval seconds.
        If the state of the workcell has changed, update the active modules and run the scheduler.
        """
        self.update_active_nodes(self.state_handler)
        node_tick = time.time()
        scheduler_tick = time.time()
        while True and not self.state_handler.shutdown:
            try:
                self.workcell_definition = self.state_handler.get_workcell_definition()
                if (
                    time.time() - node_tick
                    > self.workcell_settings.node_update_interval
                ):
                    self.update_active_nodes(self.state_handler)
                    node_tick = time.time()
                if (
                    time.time() - scheduler_tick
                    > self.workcell_settings.scheduler_update_interval
                ):
                    with self.state_handler.wc_state_lock():
                        self.state_handler.update_workflow_queue()
                        self.state_handler.archive_terminal_workflows()
                        workflows = self.state_handler.get_workflow_queue()
                        workflow_metadata_map = self.scheduler.run_iteration(
                            workflows=workflows
                        )
                        for workflow in workflows:
                            if workflow.workflow_id in workflow_metadata_map:
                                workflow.scheduler_metadata = workflow_metadata_map[
                                    workflow.workflow_id
                                ]
                                self.state_handler.set_active_workflow(
                                    workflow, mark_state_changed=False
                                )
                            else:
                                workflow.scheduler_metadata.ready_to_run = False
                                self.state_handler.set_active_workflow(
                                    workflow, mark_state_changed=False
                                )
                    if self.state_handler.get_workcell_status().ok:
                        self.run_next_step()
                        scheduler_tick = time.time()
            except Exception as e:
                self.logger.log_error(e)
                self.logger.log_warning(
                    f"Error in engine loop, waiting {self.workcell_settings.node_update_interval} seconds before trying again."
                )
                with self.state_handler.wc_state_lock():
                    workcell_status = self.state_handler.get_workcell_status()
                    workcell_status.errored = True
                    workcell_status.errors.append(Error.from_exception(e))
                    self.state_handler.set_workcell_status(workcell_status)
                time.sleep(self.workcell_settings.node_update_interval)

    def run_next_step(self, await_step_completion: bool = False) -> Optional[Workflow]:
        """Runs the next step in the workflow with the highest priority. Returns information about the workflow it ran, if any."""
        next_wf = None
        with self.state_handler.wc_state_lock():
            workflows = self.state_handler.get_workflow_queue()
            ready_workflows = filter(
                lambda wf: wf.scheduler_metadata.ready_to_run, workflows
            )
            sorted_ready_workflows = sorted(
                ready_workflows,
                key=lambda wf: wf.scheduler_metadata.priority,
                reverse=True,
            )
            while len(sorted_ready_workflows) > 0:
                next_wf = sorted_ready_workflows[0]
                # * Check if the workflow is already complete
                if next_wf.status.current_step_index >= len(next_wf.steps):
                    self.logger.log_warning(
                        f"Workflow {next_wf.workflow_id} has no more steps, marking as completed"
                    )
                    next_wf.status.completed = True
                    self.state_handler.set_active_workflow(next_wf)
                    self._log_workflow_completion(next_wf, "completed")
                    sorted_ready_workflows.pop(0)
                    next_wf = None
                    continue
                next_wf = sorted_ready_workflows[0]
                next_wf.status.running = True
                next_wf.status.has_started = True
                if next_wf.status.current_step_index == 0:
                    next_wf.start_time = datetime.now()
                self.state_handler.set_active_workflow(next_wf)
                break
            else:
                self.logger.log_info("No workflows ready to run")
        if next_wf:
            thread = self.run_step(next_wf.workflow_id)
            if await_step_completion:
                thread.join()
        return next_wf

    @threaded_daemon
    def run_step(self, workflow_id: str) -> None:
        """Run a step in a standalone thread, updating the workflow as needed"""
        try:
            # * Prepare the step
            wf = self.state_handler.get_active_workflow(workflow_id)
            step = wf.steps[wf.status.current_step_index]
            step.start_time = datetime.now()
            self.logger.log_info(
                f"Running step {step.step_id} in workflow {workflow_id}"
            )
            node = self.state_handler.get_node(step.node)
            client = find_node_client(node.node_url)
            wf = self.update_step(wf, step)

            # * Send the action request
            response = None

            # Merge with step.args
            args = {**step.args, **step.locations}
            request = ActionRequest(
                action_name=step.action,
                args=args,
                files=step.files,
            )
            action_id = request.action_id
            try:
                response = client.send_action(request, await_result=False)
            except Exception as e:
                self.logger.log_error(
                    f"Sending Action Request {action_id} for step {step.step_id} triggered exception: {e!s}"
                )
                if response is None:
                    response = request.unknown(errors=[Error.from_exception(e)])
                else:
                    response.errors.append(Error.from_exception(e))

            response = self.handle_response(wf, step, response)
            action_id = response.action_id

            # * Periodically query the action status until complete, updating the workflow as needed
            # * If the node or client supports get_action_result, query the action result
            self.monitor_action_progress(
                wf, step, node, client, response, request, action_id
            )

            # * Finalize the step
            self.finalize_step(workflow_id, step)
            self.logger.log_info(
                f"Completed step {step.step_id} in workflow {workflow_id}"
            )
            self.logger.log_debug(self.state_handler.get_workflow(workflow_id))
        except Exception:
            self.logger.log_error(
                f"Running step in workflow {workflow_id} triggered unhandled exception: {traceback.format_exc()}"
            )

    def monitor_action_progress(
        self,
        wf: Workflow,
        step: Step,
        node: Node,
        client: AbstractNodeClient,
        response: ActionResult,
        request: ActionRequest,
        action_id: str,
    ) -> None:
        """Monitor the progress of the action, querying the action result until it is terminal"""
        interval = 0.25
        retry_count = 0
        while not response.status.is_terminal:
            if node.info.capabilities.get_action_result is False or (
                node.info.capabilities.get_action_result is None
                and client.supported_capabilities.get_action_result is False
            ):
                self.logger.log_warning(
                    f"While running Step {step.step_id} of workflow {wf.workflow_id}, send_action returned a non-terminal response {response}. However, node {step.node} does not support querying an action result."
                )
                break
            try:
                time.sleep(interval)  # * Exponential backoff with cap
                interval = interval * 1.5 if interval < 5 else 5
                response = client.get_action_result(action_id)
                self.handle_response(wf, step, response)
                if (
                    response.status.is_terminal
                    or response.status == ActionStatus.UNKNOWN
                ):
                    # * If the action is terminal or unknown, break out of the loop
                    # * If the action is unknown, that means the node does not have a record of the action
                    break
            except Exception as e:
                self.logger.log_error(
                    f"Querying action {action_id} for step {step.step_id} resulted in exception: {e!s}"
                )
                if response is None:
                    response = request.unknown(errors=[Error.from_exception(e)])
                else:
                    response.errors.append(Error.from_exception(e))
                self.handle_response(wf, step, response)
                if retry_count >= self.workcell_settings.get_action_result_retries:
                    self.logger.log_error(
                        f"Exceeded maximum number of retries for querying action {action_id} for step {step.step_id}"
                    )
                    break
                retry_count += 1

    def finalize_step(self, workflow_id: str, step: Step) -> None:
        """Finalize the step, updating the workflow based on the results (setting status, updating index, etc.)"""
        with self.state_handler.wc_state_lock():
            wf = self.state_handler.get_active_workflow(workflow_id)
            step.end_time = datetime.now()
            wf.steps[wf.status.current_step_index] = step
            wf.status.running = False

            if step.status == ActionStatus.SUCCEEDED:
                new_index = wf.status.current_step_index + 1
                if new_index >= len(wf.steps):
                    wf.status.completed = True
                    wf.end_time = datetime.now()
                else:
                    wf.status.current_step_index = new_index
            elif step.status == ActionStatus.FAILED:
                wf.status.failed = True
                wf.end_time = datetime.now()
            elif step.status == ActionStatus.CANCELLED:
                wf.status.cancelled = True
                wf.end_time = datetime.now()
            elif step.status == ActionStatus.NOT_READY:
                pass
            elif step.status == ActionStatus.UNKNOWN:
                self.logger.log_error(
                    f"Step {step.step_id} in workflow {workflow_id} ended with unknown status"
                )
                wf.status.failed = True
                wf.end_time = datetime.now()
            else:
                self.logger.log_error(
                    f"Step {step.step_id} in workflow {workflow_id} ended with unexpected status {step.status}"
                )
                wf.status.failed = True
                wf.end_time = datetime.now()
            self.state_handler.set_active_workflow(wf)

            if wf.status.completed or wf.status.failed or wf.status.cancelled:
                self._log_workflow_completion(wf)

    def _log_workflow_completion(self, workflow: Workflow) -> None:
        """Log workflow completion event with author and utilization data."""
        try:
            event_data = self._build_workflow_event_data(workflow)
            self._add_error_information(workflow, event_data)
            self._add_ownership_information(workflow, event_data)

            self._log_completion_event(workflow, event_data)

        except Exception as e:
            self.logger.log_error(
                f"Error logging workflow completion for {workflow.workflow_id}: {e}"
            )

    def _build_workflow_event_data(self, workflow: Workflow) -> dict:
        """Build the basic event data for workflow completion."""
        final_status = self._determine_final_status(workflow)
        duration_seconds = self._calculate_duration(workflow)
        author = self._extract_workflow_author(workflow)
        step_stats = self._calculate_step_statistics(workflow)

        return {
            "workflow_id": workflow.workflow_id,
            "workflow_name": workflow.name,
            "author": author,
            "workcell_id": self.workcell_definition.workcell_id,
            "workcell_name": self.workcell_definition.workcell_name,
            "status": final_status,
            "duration_seconds": duration_seconds,
            "total_steps": len(workflow.steps),
            **step_stats,
            "start_time": workflow.start_time.isoformat()
            if workflow.start_time
            else None,
            "end_time": workflow.end_time.isoformat() if workflow.end_time else None,
            "submitted_time": workflow.submitted_time.isoformat()
            if workflow.submitted_time
            else None,
        }

    def _determine_final_status(self, workflow: Workflow) -> str:
        """Determine the final status of the workflow."""
        if workflow.status.completed:
            return "completed"
        if workflow.status.failed:
            return "failed"
        if workflow.status.cancelled:
            return "cancelled"
        return "unknown"

    def _calculate_duration(self, workflow: Workflow) -> Optional[float]:
        """Calculate workflow duration in seconds."""
        if workflow.start_time and workflow.end_time:
            return (workflow.end_time - workflow.start_time).total_seconds()
        return None

    def _calculate_step_statistics(self, workflow: Workflow) -> dict:
        """Calculate statistics about workflow steps."""
        return {
            "completed_steps": sum(
                1 for step in workflow.steps if step.status == ActionStatus.SUCCEEDED
            ),
            "failed_steps": sum(
                1 for step in workflow.steps if step.status == ActionStatus.FAILED
            ),
            "cancelled_steps": sum(
                1 for step in workflow.steps if step.status == ActionStatus.CANCELLED
            ),
        }

    def _add_error_information(self, workflow: Workflow, event_data: dict) -> None:
        """Add error information for failed workflows."""
        if event_data["status"] not in ["failed", "cancelled"] or not workflow.steps:
            return

        failed_step = self._find_failed_step(workflow)
        if not failed_step:
            return

        error_info = self._extract_error_information(failed_step)
        if error_info:
            event_data.update(error_info)

    def _find_failed_step(self, workflow: Workflow) -> Optional[Any]:
        """Find the step that caused the workflow failure."""
        for step in workflow.steps:
            if step.status in [ActionStatus.FAILED, ActionStatus.CANCELLED]:
                return step
        return None

    def _extract_error_information(self, failed_step: Any) -> Optional[dict]:
        """Extract error information from a failed step."""
        if not (failed_step.result and failed_step.result.errors):
            return None

        last_error = failed_step.result.errors[-1]
        return {
            "error_message": last_error.message,
            "error_type": last_error.error_type,
            "failed_step_id": failed_step.step_id,
            "failed_step_name": failed_step.name,
            "failed_node": failed_step.node,
        }

    def _add_ownership_information(self, workflow: Workflow, event_data: dict) -> None:
        """Add ownership information to event data."""
        if not (hasattr(workflow, "ownership_info") and workflow.ownership_info):
            return

        ownership = workflow.ownership_info
        ownership_fields = {
            "experiment_id": "experiment_id",
            "user_id": "user_id",
            "campaign_id": "campaign_id",
        }

        for attr_name, event_key in ownership_fields.items():
            if hasattr(ownership, attr_name):
                value = getattr(ownership, attr_name)
                if value:
                    event_data[event_key] = str(value)

    def _log_completion_event(self, workflow: Workflow, event_data: dict) -> None:
        """Log the completion event and info message."""
        self.logger.log(
            Event(event_type=EventType.WORKFLOW_COMPLETE, event_data=event_data)
        )

        duration_text = (
            f"Duration: {event_data['duration_seconds']:.1f}s"
            if event_data["duration_seconds"]
            else "Duration: Unknown"
        )

        self.logger.log_info(
            f"Logged workflow completion: {workflow.name} ({workflow.workflow_id[-8:]}) - "
            f"Status: {event_data['status']}, Author: {event_data['author'] or 'Unknown'}, "
            f"{duration_text}"
        )

    def extract_workflow_author(self, workflow: Workflow) -> Optional[str]:
        """Extract author from workflow metadata - simplified for Workflow inheriting from WorkflowDefinition."""

        # Try different strategies in order of preference
        author = (
            self._extract_from_workflow_metadata(workflow)
            or self._extract_from_ownership_info(workflow)
            or self._extract_from_workflow_attributes(workflow)
        )

        return self._clean_author_string(author)

    def _extract_from_workflow_metadata(self, workflow: Workflow) -> Optional[str]:
        """Extract author from workflow metadata."""
        if not (hasattr(workflow, "workflow_metadata") and workflow.workflow_metadata):
            return None

        metadata = workflow.workflow_metadata

        # Check if metadata has author attribute
        if hasattr(metadata, "author"):
            return metadata.author

        # Check if metadata is dict with author key
        if isinstance(metadata, dict) and "author" in metadata:
            return metadata["author"]

        return None

    def _extract_from_ownership_info(self, workflow: Workflow) -> Optional[str]:
        """Extract author from ownership info."""
        if not (hasattr(workflow, "ownership_info") and workflow.ownership_info):
            return None

        ownership = workflow.ownership_info
        if hasattr(ownership, "user_id") and ownership.user_id:
            return str(ownership.user_id)

        return None

    def _extract_from_workflow_attributes(self, workflow: Workflow) -> Optional[str]:
        """Extract author from various workflow attributes."""
        author_attributes = ["author", "created_by", "submitted_by", "user", "owner"]

        for attr_name in author_attributes:
            if hasattr(workflow, attr_name):
                attr_value = getattr(workflow, attr_name)
                if attr_value:
                    return str(attr_value)

        return None

    def _clean_author_string(self, author: Optional[str]) -> Optional[str]:
        """Clean and validate author string."""
        if not author:
            return None

        cleaned_author = str(author).strip()

        # Check for invalid values
        invalid_values = {"", "none", "null", "unknown"}
        if cleaned_author.lower() in invalid_values:
            return None

        return cleaned_author

    def update_step(self, wf: Workflow, step: Step) -> None:
        """Update the step in the workflow"""
        with self.state_handler.wc_state_lock():
            wf = self.state_handler.get_workflow(wf.workflow_id)
            wf.steps[wf.status.current_step_index] = step
            self.state_handler.set_active_workflow(wf)
        return wf

    def handle_response(
        self, wf: Workflow, step: Step, response: ActionResult
    ) -> Optional[ActionResult]:
        """Handle the response from the node"""
        response = self.handle_data_and_files(step, wf, response)
        step.status = response.status
        if response.status == ActionStatus.UNKNOWN:
            response.errors.append(
                Error(
                    message="Node returned 'unknown' action status for running action.",
                    error_type="NodeReturnedUnknown",
                )
            )
        step.result = response
        step.history.append(response)
        wf = self.update_step(wf, step)
        return response

    def handle_data_and_files(
        self, step: Step, wf: Workflow, response: ActionResult
    ) -> ActionResult:
        """create and save datapoints for data returned from step"""
        labeled_data = {}
        ownership_info = copy.deepcopy(wf.ownership_info)
        ownership_info.step_id = step.step_id
        ownership_info.node_id = self.state_handler.get_node(step.node).info.node_id
        ownership_info.workflow_id = wf.workflow_id
        if response.data:
            for data_key in response.data:
                if step.data_labels is not None and data_key in step.data_labels:
                    label = step.data_labels[data_key]
                else:
                    label = data_key
                datapoint = ValueDataPoint(
                    label=label,
                    ownership_info=ownership_info,
                    value=response.data[data_key],
                )
                self.data_client.submit_datapoint(datapoint)
                labeled_data[label] = datapoint.datapoint_id
        if response.files:
            for file_key in response.files:
                if step.data_labels is not None and file_key in step.data_labels:
                    label = step.data_labels[file_key]
                else:
                    label = file_key
                datapoint = FileDataPoint(
                    label=label,
                    ownership_info=ownership_info,
                    path=str(response.files[file_key]),
                )
                self.logger.log_debug(
                    "Submitting datapoint: " + str(datapoint.datapoint_id)
                )
                self.data_client.submit_datapoint(datapoint)
                self.logger.log_debug(
                    "Submitted datapoint: " + str(datapoint.datapoint_id)
                )

                labeled_data[label] = datapoint.datapoint_id
        response.data = labeled_data
        return response

    def update_active_nodes(self, state_manager: WorkcellStateHandler) -> None:
        """Update all active nodes in the workcell."""
        with concurrent.futures.ThreadPoolExecutor() as executor:
            node_futures = []
            for node_name, node in state_manager.get_nodes().items():
                node_future = executor.submit(
                    self.update_node, node_name, node, state_manager
                )
                node_futures.append(node_future)

            # Wait for all node updates to complete
            concurrent.futures.wait(node_futures)

    def update_node(
        self, node_name: str, node: Node, state_manager: WorkcellStateHandler
    ) -> None:
        """Update a single node's state and about information."""
        try:
            client = find_node_client(node.node_url)
            node.status = client.get_status()
            node.info = client.get_info()
            node.state = client.get_state()
            with state_manager.wc_state_lock():
                state_manager.set_node(node_name, node)
        except Exception as e:
            error = Error.from_exception(e)
            node.status = NodeStatus(errored=True, errors=[error])
            with state_manager.wc_state_lock():
                state_manager.set_node(node_name, node)
            with ownership_context(
                workcell_id=self.workcell_definition.workcell_id,
                node_id=node.info.node_id if node.info else None,
            ):
                self.logger.log_warning(
                    event=Event(
                        event_type=EventType.NODE_STATUS_UPDATE,
                        event_data=node.status,
                    )
                )
