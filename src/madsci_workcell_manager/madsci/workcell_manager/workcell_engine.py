"""
Engine Class and associated helpers and data
"""

import concurrent
import importlib
import time
import traceback
from datetime import datetime
from typing import Optional, Union

from madsci.client.data_client import DataClient
from madsci.client.event_client import EventClient
from madsci.client.location_client import LocationClient
from madsci.client.node.abstract_node_client import AbstractNodeClient
from madsci.client.resource_client import ResourceClient
from madsci.common.nodes import check_node_capability
from madsci.common.ownership import ownership_context
from madsci.common.types.action_types import (
    ActionDatapoints,
    ActionFiles,
    ActionRequest,
    ActionResult,
    ActionStatus,
)
from madsci.common.types.base_types import Error
from madsci.common.types.datapoint_types import (
    DataPoint,
    DataPointTypeEnum,
    FileDataPoint,
    ValueDataPoint,
)
from madsci.common.types.event_types import Event, EventType
from madsci.common.types.node_types import Node, NodeStatus
from madsci.common.types.parameter_types import (
    ParameterFeedForwardFile,
    ParameterFeedForwardJson,
)
from madsci.common.types.step_types import Step
from madsci.common.types.workflow_types import Workflow
from madsci.common.utils import threaded_daemon
from madsci.workcell_manager.state_handler import WorkcellStateHandler
from madsci.workcell_manager.workcell_actions import workcell_action_dict
from madsci.workcell_manager.workcell_utils import (
    find_node_client,
)
from madsci.workcell_manager.workflow_utils import (
    cancel_active_workflows,
    prepare_workflow_step,
)


class Engine:
    """
    Handles scheduling workflows and executing steps on the workcell.
    Pops incoming workflows off a redis-based queue and executes them.
    """

    def __init__(
        self, state_handler: WorkcellStateHandler, data_client: DataClient
    ) -> None:
        """Initialize the scheduler."""
        self.state_handler = state_handler
        self.workcell_definition = state_handler.get_workcell_definition()
        self.workcell_settings = self.state_handler.workcell_settings
        self.logger = EventClient(name=f"workcell.{self.workcell_definition.name}")
        cancel_active_workflows(state_handler)
        scheduler_module = importlib.import_module(self.workcell_settings.scheduler)
        self.scheduler = scheduler_module.Scheduler(
            self.workcell_definition, self.state_handler
        )
        self.data_client = data_client
        self.resource_client = ResourceClient()
        self.location_client = LocationClient()
        with state_handler.wc_state_lock():
            state_handler.initialize_workcell_state()
        time.sleep(self.workcell_settings.cold_start_delay)
        self.logger.info("Engine initialized, waiting for workflows...")

    @threaded_daemon
    def spin(self) -> None:
        """
        Continuously loop, updating node states every Config.update_interval seconds.
        If the state of the workcell has changed, update the active modules and run the scheduler.
        """
        self.update_active_nodes(self.state_handler, update_info=True)
        node_tick = time.time()
        info_tick = time.time()
        scheduler_tick = time.time()
        while True and not self.state_handler.shutdown:
            try:
                self.workcell_definition = self.state_handler.get_workcell_definition()

                # Check if it's time to update node info (less frequent)
                should_update_info = (
                    time.time() - info_tick
                    > self.workcell_settings.node_info_update_interval
                )

                if (
                    time.time() - node_tick
                    > self.workcell_settings.node_update_interval
                ):
                    self.update_active_nodes(
                        self.state_handler, update_info=should_update_info
                    )
                    node_tick = time.time()
                    if should_update_info:
                        info_tick = time.time()
                if (
                    time.time() - scheduler_tick
                    > self.workcell_settings.scheduler_update_interval
                ):
                    with self.state_handler.wc_state_lock():
                        self.state_handler.update_workflow_queue()
                        self.state_handler.archive_terminal_workflows()
                        workflows = self.state_handler.get_workflow_queue()
                        workflow_definition_metadata_map = self.scheduler.run_iteration(
                            workflows=workflows
                        )
                        for workflow in workflows:
                            if workflow.workflow_id in workflow_definition_metadata_map:
                                workflow.scheduler_metadata = (
                                    workflow_definition_metadata_map[
                                        workflow.workflow_id
                                    ]
                                )
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
                self.logger.error(e)
                self.logger.warning(
                    f"Error in engine loop, waiting {10 * self.workcell_settings.node_update_interval} seconds before trying again."
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
                    self.logger.warning(
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
                self.logger.info("No workflows ready to run")
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
            step = prepare_workflow_step(
                step=step,
                workcell=self.workcell_definition,
                state_handler=self.state_handler,
                workflow=wf,
                data_client=self.data_client,
                location_client=self.location_client,
            )
            step.start_time = datetime.now()
            self.logger.info(f"Running step {step.step_id} in workflow {workflow_id}")
            if step.node is None:
                step = self.run_workcell_action(step)
            else:
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
                    files=step.file_paths,
                )
                action_id = request.action_id

                # Acquire lock on the node for the entire action duration
                node_lock = self.state_handler.node_lock(step.node)
                if not node_lock.acquire():
                    raise RuntimeError(f"Failed to acquire lock on node {step.node}")

                try:
                    self.logger.log_info(
                        f"Acquired lock on Node {step.node} for Action {action_id} in Step {step.step_id} of Workflow {workflow_id}"
                    )

                    try:
                        response = client.send_action(request, await_result=False)
                    except Exception as e:
                        self.logger.error(
                            f"Sending Action Request {action_id} for step {step.step_id} triggered exception: {e!s}"
                        )
                        if response is None:
                            # Create a running response so monitor_action_progress can try get_action_result
                            # as a fallback in case the action was actually created but the response was lost
                            response = request.running(errors=[Error.from_exception(e)])
                        else:
                            response.errors.append(Error.from_exception(e))

                    response = self.handle_response(wf, step, response)
                    action_id = response.action_id

                    # * Periodically query the action status until complete, updating the workflow as needed
                    # * If the node or client supports get_action_result, query the action result
                    node_lock.release()
                    self.monitor_action_progress(
                        wf, step, node, client, response, request, action_id
                    )
                finally:
                    self.logger.log_info(
                        f"Released lock on Node {step.node} for Action {action_id} in Step {step.step_id} of Workflow {workflow_id}"
                    )
                    if node_lock.locked():
                        node_lock.release()
                # * Finalize the step
            self.finalize_step(workflow_id, step)
            self.logger.info(f"Completed step {step.step_id} in workflow {workflow_id}")
            self.logger.debug(self.state_handler.get_workflow(workflow_id))
        except Exception as e:
            self.logger.error(
                f"Running step in workflow {workflow_id} triggered unhandled exception: {traceback.format_exc()}"
            )
            step.result = ActionResult(
                status=ActionStatus.FAILED,
                errors=Error.from_exception(e),
            )
            wf = self.update_step(wf, step)
            self.finalize_step(workflow_id, step)

    def run_workcell_action(self, step: Step) -> Step:
        """Runs one of the built-in workcell actions"""
        action_callable = workcell_action_dict[step.action]
        step.result = action_callable(**step.args)
        step.status = step.result.status
        return step

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
        interval = 1.0
        retry_count = 0
        while not response.status.is_terminal:
            if not check_node_capability(
                node_info=node.info, client=client, capability="get_action_result"
            ) and not check_node_capability(
                node_info=node.info, client=client, capability="get_action_status"
            ):
                self.logger.warning(
                    f"While running Step {step.step_id} of workflow {wf.workflow_id}, send_action returned a non-terminal response {response}. However, node {step.node} does not support querying an action result."
                )
                break
            try:
                time.sleep(interval)  # * Exponential backoff with cap
                interval = interval * 1.5 if interval < 10.0 else 10.0
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
                self.logger.error(
                    f"Querying action {action_id} for step {step.step_id} resulted in exception: {e!s}"
                )
                if response is None:
                    response = request.unknown(errors=[Error.from_exception(e)])
                else:
                    response.errors.append(Error.from_exception(e))
                self.handle_response(wf, step, response)
                if retry_count >= self.workcell_settings.get_action_result_retries:
                    self.logger.error(
                        f"Exceeded maximum number of retries for querying action {action_id} for step {step.step_id}"
                    )
                    # Set status to UNKNOWN after exhausting retries
                    response = request.unknown(errors=response.errors)
                    self.handle_response(wf, step, response)
                    break
                retry_count += 1

    def update_param_value_from_datapoint(
        self,
        wf: Workflow,
        datapoint: DataPoint,
        parameter: Union[ParameterFeedForwardJson, ParameterFeedForwardFile],
    ) -> Workflow:
        """Updates the parameters in a workflow"""

        if datapoint.data_type == DataPointTypeEnum.JSON:
            wf.parameter_values[parameter.key] = datapoint.value
        elif datapoint.data_type in {
            DataPointTypeEnum.FILE,
            DataPointTypeEnum.OBJECT_STORAGE,
        }:
            wf.file_input_ids[parameter.key] = datapoint.datapoint_id
        return wf

    def finalize_step(self, workflow_id: str, step: Step) -> None:
        """Finalize the step, updating the workflow based on the results (setting status, updating index, etc.)"""
        with self.state_handler.wc_state_lock():
            wf = self.state_handler.get_active_workflow(workflow_id)
            step.end_time = datetime.now()
            wf.steps[wf.status.current_step_index] = step
            wf = self._feed_data_forward(step, wf)
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
                self.logger.error(
                    f"Step {step.step_id} in workflow {workflow_id} ended with unknown status"
                )
                wf.status.failed = True
                wf.end_time = datetime.now()
            else:
                self.logger.error(
                    f"Step {step.step_id} in workflow {workflow_id} ended with unexpected status {step.status}"
                )
                wf.status.failed = True
                wf.end_time = datetime.now()
            self.state_handler.set_active_workflow(wf)

            if wf.status.terminal:
                self.logger.log_info(str(wf))
                self._log_completion_event(wf)

    def _feed_data_forward(self, step: Step, wf: Workflow) -> Workflow:
        """Feed data forward from the completed step to the workflow parameters"""
        for param in wf.parameters.feed_forward:
            if (isinstance(param.step, str) and param.step == step.key) or (
                isinstance(param.step, int)
                and wf.status.current_step_index == param.step
            ):
                if step.result.datapoints:
                    self.logger.log_warning(
                        event=Event(event_data=str(step.result.datapoints))
                    )
                    datapoint_ids = step.result.datapoints.model_dump()
                    # Fetch actual DataPoint objects from data manager using the IDs
                    datapoint_dict = {}
                    for key, datapoint_id in datapoint_ids.items():
                        datapoint = self.data_client.get_datapoint(datapoint_id)
                        datapoint_dict[key] = datapoint
                else:
                    raise ValueError(
                        f"Feed-forward parameter {param.key} specified step {param.step} but step has no datapoints"
                    )
                if param.label is None:
                    self.logger.log_warning(event=Event(event_data=str(datapoint_dict)))
                    if len(datapoint_dict) == 1:
                        datapoint = next(iter(datapoint_dict.values()))
                        wf = self.update_param_value_from_datapoint(
                            wf, datapoint, param
                        )
                    else:
                        raise ValueError(
                            f"Ambiguous feed-forward parameter {param.key}: multiple possible matching labels: {step.result.datapoints.model_dump().keys()}"
                        )
                elif param.label in datapoint_dict:
                    datapoint = datapoint_dict[param.label]
                    wf = self.update_param_value_from_datapoint(wf, datapoint, param)
                elif param.step is not None:
                    raise ValueError(
                        f"Feed-forward parameter {param.key}'s specified label {param.label} not found in step result datapoints: {step.result.datapoints.model_dump().keys()}"
                    )
        return wf

    def _log_completion_event(self, workflow: Workflow) -> None:
        """Log the completion event and info message."""
        try:
            event_data = workflow.model_dump(mode="json")
            self.logger.log(
                Event(event_type=EventType.WORKFLOW_COMPLETE, event_data=event_data)
            )

            duration_text = (
                f"Duration: {event_data['duration_seconds']:.1f}s"
                if event_data["duration_seconds"]
                else "Duration: Unknown"
            )

            self.logger.info(
                f"Logged workflow completion: {workflow.name} ({workflow.workflow_id[-8:]}) - "
                f"Status: {event_data['status']}, Author: {(event_data.get('definition_metadata') or {}).get('author') or 'Unknown'}, "
                f"{duration_text}"
            )
        except Exception as e:
            self.logger.error(
                f"Error logging workflow completion event for workflow {workflow.workflow_id}: {e!s}\n{traceback.format_exc()}"
            )

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
        if (
            len(step.history) == 0
            or step.history[-1].action_id != response.action_id
            or step.history[-1].status != response.status
        ):
            # * Don't append redundant status updates
            step.history.append(response)
        step.last_status_update = datetime.now()
        wf = self.update_step(wf, step)
        return response

    def handle_data_and_files(
        self, step: Step, wf: Workflow, response: ActionResult
    ) -> ActionResult:
        """Upload non-datapoint results as datapoints and consolidate all datapoint IDs.

        This method ensures that all results (JSON data, files) are stored as datapoints
        in the data manager, following the principle of getting data into the data manager ASAP.
        The response datapoints field will contain only ULID strings for efficient storage.
        """
        # Start with existing datapoint IDs (these are already uploaded)
        if response.datapoints:
            datapoint_ids = response.datapoints.model_dump(mode="json")
        else:
            datapoint_ids = {}

        # Set ownership context for all datapoint uploads
        with ownership_context(
            workcell_id=self.workcell_definition.manager_id,
            workflow_id=wf.workflow_id,
            node_id=self.state_handler.get_node(step.node).info.node_id
            if self.state_handler.get_node(step.node).info
            else None,
            step_id=step.step_id,
        ):
            # Upload JSON result as ValueDataPoint if present
            if response.json_result is not None:
                datapoint = ValueDataPoint(
                    label="json_result",
                    value=response.json_result,
                )
                submitted_datapoint = self.data_client.submit_datapoint(datapoint)
                datapoint_ids["json_result"] = submitted_datapoint.datapoint_id
                self.logger.log_debug(
                    f"Uploaded JSON result as datapoint: {submitted_datapoint.datapoint_id}"
                )

            # Upload files as FileDataPoints if present
            if response.files:
                if isinstance(response.files, ActionFiles):
                    # Multiple files in ActionFiles object
                    response_files = response.files.model_dump(mode="json")
                    for file_key, file_path in response_files.items():
                        datapoint = FileDataPoint(
                            label=file_key,
                            path=str(file_path),
                        )
                        submitted_datapoint = self.data_client.submit_datapoint(
                            datapoint
                        )
                        datapoint_ids[file_key] = submitted_datapoint.datapoint_id
                        self.logger.log_debug(
                            f"Uploaded file '{file_key}' as datapoint: {submitted_datapoint.datapoint_id}"
                        )
                else:
                    # Single file Path
                    datapoint = FileDataPoint(
                        label="file",
                        path=str(response.files),
                    )
                    submitted_datapoint = self.data_client.submit_datapoint(datapoint)
                    datapoint_ids["file"] = submitted_datapoint.datapoint_id
                    self.logger.log_debug(
                        f"Uploaded file as datapoint: {submitted_datapoint.datapoint_id}"
                    )

            # Update response to contain only datapoint IDs
            response.datapoints = ActionDatapoints.model_validate(datapoint_ids)

            # Clear the original data now that it's stored as datapoints
            # This ensures we only store IDs in workflows for efficiency
            response.json_result = None
            response.files = None

            return response

    def update_active_nodes(
        self, state_manager: WorkcellStateHandler, update_info: bool = False
    ) -> None:
        """Update all active nodes in the workcell.

        Args:
            state_manager: The workcell state handler
            update_info: Whether to update node info in addition to status and state (default: False)
        """
        with concurrent.futures.ThreadPoolExecutor() as executor:
            node_futures = []
            for node_name, node in state_manager.get_nodes().items():
                node_future = executor.submit(
                    self.update_node, node_name, node, state_manager, update_info
                )
                node_futures.append(node_future)

            # Wait for all node updates to complete
            concurrent.futures.wait(node_futures)

    def update_node(
        self,
        node_name: str,
        node: Node,
        state_manager: WorkcellStateHandler,
        update_info: bool = False,
    ) -> None:
        """Update a single node's status, state, and optionally info.

        Args:
            node_name: The name of the node to update
            node: The node object to update
            state_manager: The workcell state handler
            update_info: Whether to update node info (default: False). Node info changes
                        infrequently, so it's updated less often to reduce network overhead.
        """
        try:
            client = find_node_client(node.node_url)
            node.status = client.get_status()
            if update_info or node.info is None:
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
                workcell_id=self.workcell_definition.manager_id,
                node_id=node.info.node_id if node.info else None,
            ):
                self.logger.warning(
                    event=Event(
                        event_type=EventType.NODE_STATUS_UPDATE,
                        event_data=node.status,
                    )
                )
