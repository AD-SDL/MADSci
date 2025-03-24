"""
Engine Class and associated helpers and data
"""

import copy
import importlib
import time
import traceback
from datetime import datetime
from typing import Optional

from madsci.client.data_client import DataClient
from madsci.client.event_client import EventClient
from madsci.client.resource_client import ResourceClient
from madsci.common.types.action_types import ActionRequest, ActionResult, ActionStatus
from madsci.common.types.base_types import Error
from madsci.common.types.datapoint_types import FileDataPoint, ValueDataPoint
from madsci.common.types.step_types import Step
from madsci.common.types.workflow_types import (
    Workflow,
    WorkflowStatus,
)
from madsci.common.utils import threaded_daemon
from madsci.workcell_manager.redis_handler import WorkcellRedisHandler
from madsci.workcell_manager.workcell_utils import (
    find_node_client,
    update_active_nodes,
)
from madsci.workcell_manager.workflow_utils import cancel_active_workflows


class Engine:
    """
    Handles scheduling workflows and executing steps on the workcell.
    Pops incoming workflows off a redis-based queue and executes them.
    """

    def __init__(
        self,
        state_handler: WorkcellRedisHandler,
    ) -> None:
        """Initialize the scheduler."""
        self.state_handler = state_handler
        workcell_definition = state_handler.get_workcell_definition()
        self.logger = EventClient(workcell_definition.config.event_client_config)
        self.logger.source.workcell_id = workcell_definition.workcell_id
        cancel_active_workflows(state_handler)
        scheduler_module = importlib.import_module(workcell_definition.config.scheduler)
        self.scheduler = scheduler_module.Scheduler(
            workcell_definition, self.state_handler
        )
        self.data_client = DataClient(workcell_definition.config.data_server_url)
        self.resource_client = ResourceClient(
            workcell_definition.config.resource_server_url
        )
        self.logger.log_debug(self.data_client.url)
        with state_handler.wc_state_lock():
            state_handler.initialize_workcell_state(
                self.resource_client,
            )
        time.sleep(workcell_definition.config.cold_start_delay)
        self.logger.log_info("Engine initialized, waiting for workflows...")

    @threaded_daemon
    def spin(self) -> None:
        """
        Continuously loop, updating node states every Config.update_interval seconds.
        If the state of the workcell has changed, update the active modules and run the scheduler.
        """
        update_active_nodes(self.state_handler)
        node_tick = time.time()
        scheduler_tick = time.time()
        while True and not self.state_handler.shutdown:
            try:
                self.workcell_definition = self.state_handler.get_workcell_definition()
                if (
                    time.time() - node_tick
                    > self.workcell_definition.config.node_update_interval
                    or self.state_handler.has_state_changed()
                ):
                    update_active_nodes(self.state_handler)
                    node_tick = time.time()
                if (
                    time.time() - scheduler_tick
                    > self.workcell_definition.config.scheduler_update_interval
                ):
                    with self.state_handler.wc_state_lock():
                        workflows = self.state_handler.get_workflows()
                        filtered_workflows = [
                            wf
                            for wf in workflows.values()
                            if wf.status
                            in {WorkflowStatus.QUEUED, WorkflowStatus.IN_PROGRESS}
                        ]
                        workflow_metadata_map = self.scheduler.run_iteration(
                            workflows=filtered_workflows
                        )
                        for workflow_id, workflow in workflows.items():
                            if workflow_id in workflow_metadata_map:
                                workflow.scheduler_metadata = workflow_metadata_map[
                                    workflow_id
                                ]
                                self.state_handler.set_workflow(
                                    workflow, mark_state_changed=False
                                )
                    if self.state_handler.get_workcell_status().ok:
                        self.run_next_step()
                        scheduler_tick = time.time()
            except Exception:
                traceback.print_exc()
                self.logger.log_error(
                    f"Error in engine loop, waiting {self.workcell_definition.config.node_update_interval} seconds before trying again."
                )
                time.sleep(self.workcell_definition.config.node_update_interval)

    def run_next_step(self, await_step_completion: bool = False) -> None:
        """Runs the next step in the workflow with the highest priority"""
        next_wf = None
        with self.state_handler.wc_state_lock():
            workflows = self.state_handler.get_workflows()
            ready_workflows = filter(
                lambda wf: wf.scheduler_metadata.ready_to_run, workflows.values()
            )
            sorted_ready_workflows = sorted(
                ready_workflows,
                key=lambda wf: wf.scheduler_metadata.priority,
                reverse=True,
            )
            if len(sorted_ready_workflows) > 0:
                next_wf = sorted_ready_workflows[0]
                next_wf.status = WorkflowStatus.RUNNING
                if next_wf.step_index == 0:
                    next_wf.start_time = datetime.now()
                self.state_handler.set_workflow(next_wf)
        if (
            next_wf
            and len(next_wf.steps) > 0
            and next_wf.step_index < len(next_wf.steps)
        ):
            thread = self.run_step(next_wf.workflow_id)
            if await_step_completion:
                thread.join()
        else:
            self.logger.log_info("No workflows ready to run")

    @threaded_daemon
    def run_step(self, workflow_id: str) -> None:
        """Run a step in a standalone thread, updating the workflow as needed"""
        try:
            # * Prepare the step
            wf = self.state_handler.get_workflow(workflow_id)
            step = wf.steps[wf.step_index]
            step.start_time = datetime.now()
            self.logger.log_info(
                f"Running step {step.step_id} in workflow {workflow_id}"
            )
            node = self.state_handler.get_node(step.node)
            client = find_node_client(node.node_url)
            wf = self.update_step(wf, step)

            # * Send the action request
            response = None
            request = ActionRequest(
                action_name=step.action,
                args={**step.args, **step.locations},
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
            interval = 0.25
            retry_count = 0
            while not response.status.is_terminal:
                if node.info.capabilities.get_action_result is False or (
                    node.info.capabilities.get_action_result is None
                    and client.supported_capabilities.get_action_result is False
                ):
                    self.logger.log_warning(
                        f"While running Step {step.step_id} of workflow {workflow_id}, send_action returned a non-terminal response {response}. However, node {step.node} does not support querying an action result."
                    )
                    break
                try:
                    time.sleep(interval)  # * Exponential backoff with cap
                    interval = interval * 1.5 if interval < 10 else 10
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
                    if (
                        retry_count
                        >= self.workcell_definition.config.get_action_result_retries
                    ):
                        self.logger.log_error(
                            f"Exceeded maximum number of retries for querying action {action_id} for step {step.step_id}"
                        )
                        break
                    retry_count += 1

            # * Finalize the step
            self.finalize_step(workflow_id, step)
            self.logger.log_info(
                f"Completed step {step.step_id} in workflow {workflow_id}"
            )
        except Exception as e:
            self.logger.log_error(
                f"Running step in workflow {workflow_id} triggered unhandled exception: {e!s}"
            )

    def finalize_step(self, workflow_id: str, step: Step) -> None:
        """Finalize the step, updating the workflow based on the results (setting status, updating index, etc.)"""
        with self.state_handler.wc_state_lock():
            wf = self.state_handler.get_workflow(workflow_id)
            step.end_time = datetime.now()
            wf.steps[wf.step_index] = step
            if step.status == ActionStatus.SUCCEEDED:
                new_index = wf.step_index + 1
                if new_index == len(wf.steps):
                    wf.status = WorkflowStatus.COMPLETED
                    wf.end_time = datetime.now()
                else:
                    wf.step_index = new_index
                    if wf.status == WorkflowStatus.RUNNING:
                        wf.status = WorkflowStatus.IN_PROGRESS
            if step.status == ActionStatus.FAILED:
                wf.status = WorkflowStatus.FAILED
                wf.end_time = datetime.now()
            if step.status == ActionStatus.CANCELLED:
                wf.status = WorkflowStatus.CANCELLED
                wf.end_time = datetime.now()
            self.state_handler.set_workflow(wf)

    def update_step(self, wf: Workflow, step: Step) -> None:
        """Update the step in the workflow"""
        with self.state_handler.wc_state_lock():
            wf = self.state_handler.get_workflow(wf.workflow_id)
            wf.steps[wf.step_index] = step
            self.state_handler.set_workflow(wf)
        return wf

    def handle_response(
        self, wf: Workflow, step: Step, response: Optional[ActionResult]
    ) -> Optional[ActionResult]:
        """Handle the response from the node"""
        if response is not None:
            response = self.handle_data_and_files(step, wf, response)
            step.status = response.status
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
