"""
Engine Class and associated helpers and data
"""

import importlib
import time
import traceback
from datetime import datetime
from typing import Optional

from madsci.client.data_client import DataClient
from madsci.client.event_client import default_logger
from madsci.client.node.abstract_node_client import AbstractNodeClient
from madsci.common.types.action_types import ActionRequest, ActionResult
from madsci.common.types.datapoint_types import FileDataPoint, ValueDataPoint
from madsci.common.types.node_types import Node
from madsci.common.types.step_types import Step
from madsci.common.types.workcell_types import WorkcellDefinition
from madsci.common.types.workflow_types import Workflow, WorkflowStatus
from madsci.common.utils import threaded_daemon
from madsci.workcell_manager.redis_handler import WorkcellRedisHandler
from madsci.workcell_manager.workcell_utils import (
    find_node_client,
    initialize_workcell,
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
        workcell_manager_definition: WorkcellDefinition,
        state_handler: WorkcellRedisHandler,
    ) -> None:
        """Initialize the scheduler."""
        state_handler.clear_state(
            clear_workflows=workcell_manager_definition.config.clear_workflows
        )
        self.definition = workcell_manager_definition
        self.state_handler = state_handler
        cancel_active_workflows(state_handler)
        scheduler_module = importlib.import_module(self.definition.config.scheduler)
        self.scheduler = scheduler_module.Scheduler(self.definition, self.state_handler)
        self.data_client = DataClient(self.definition.config.data_server_url)
        with state_handler.wc_state_lock():
            initialize_workcell(state_handler)
        time.sleep(workcell_manager_definition.config.cold_start_delay)
        default_logger.log_info("Engine initialized, waiting for workflows...")
        # TODO send event

    def spin(self) -> None:
        """
        Continuously loop, updating module states every Config.update_interval seconds.
        If the state of the workcell has changed, update the active modules and run the scheduler.
        """
        update_active_nodes(self.state_handler)
        node_tick = time.time()
        scheduler_tick = time.time()
        heartbeat = time.time()
        while True and not self.state_handler.shutdown:
            try:
                if time.time() - heartbeat > self.definition.config.heartbeat_interval:
                    heartbeat = time.time()
                    default_logger.log_info(f"Heartbeat: {time.time()}")
                if (
                    time.time() - node_tick
                    > self.definition.config.node_update_interval
                    or self.state_handler.has_state_changed()
                ):
                    if not self.state_handler.paused:
                        update_active_nodes(self.state_handler)
                    node_tick = time.time()
                if (
                    time.time() - scheduler_tick
                    > self.definition.config.scheduler_update_interval
                ):
                    with self.state_handler.wc_state_lock():
                        self.scheduler.run_iteration(
                            workflows=self.state_handler.get_all_workflows()
                        )
                        self.run_next_step()
                        scheduler_tick = time.time()
            except Exception:
                traceback.print_exc()
                default_logger.log_error(
                    f"Error in engine loop, waiting {self.definition.config.node_update_interval} seconds before trying again."
                )
                time.sleep(self.definition.config.node_update_interval)

    @threaded_daemon
    def start_engine_thread(self) -> None:
        """Spins the engine in its own thread"""
        self.spin()

    def run_next_step(self) -> None:
        """Runs the next step in the workflow with the highest priority"""
        workflows = self.state_handler.get_all_workflows()
        ready_workflows = filter(
            lambda wf: wf.scheduler_metadata.ready_to_run, workflows.values()
        )
        sorted_ready_workflows = sorted(
            ready_workflows, key=lambda wf: wf.scheduler_metadata.priority, reverse=True
        )
        if len(sorted_ready_workflows) > 0:
            next_wf = sorted_ready_workflows[0]
            next_wf.status = WorkflowStatus.RUNNING
            self.state_handler.set_workflow(next_wf)
            self.run_step(next_wf.workflow_id, next_wf.steps[next_wf.step_index])

    def query_action_result(
        self,
        node: Node,
        client: AbstractNodeClient,
        request: ActionRequest,
        response: Optional[ActionResult] = None,
    ) -> ActionResult:
        """retry an action if it fails"""
        if node.info.capabilities.get_action_result:
            while response is None or response.status not in [
                "not_ready",
                "succeeded",
                "failed",
            ]:
                try:
                    response = client.get_action_result(request.action_id)
                    time.sleep(5)
                except Exception:
                    time.sleep(5)
            return response
        return response

    @threaded_daemon
    def run_step(self, workflow_id: str, step: Step) -> None:
        """Run a step in a seperate thread"""
        with self.state_handler.wc_state_lock():
            wf = self.state_handler.get_workflow(workflow_id)
            wf.steps[wf.step_index].start_time = datetime.now()
            if wf.step_index == 0:
                wf.start_time = datetime.now()
            self.state_handler.set_workflow(wf)
        node = self.state_handler.get_node(step.node)
        client = find_node_client(node.node_url)
        response = None
        try:
            request = ActionRequest(
                action_name=step.action,
                args={**step.args, **step.locations},
                files=step.files,
            )
            response = client.send_action(request)
        except Exception:
            default_logger.log_info("request had exception")
        finally:
            response = self.query_action_result(node, client, request, response)
        if response is None:
            response = request.failed()
        response = self.handle_data_and_files(response)
        with self.state_handler.wc_state_lock():
            wf = self.state_handler.get_workflow(workflow_id)
            if response.status in ["succeeded", "failed"]:
                wf.steps[wf.step_index].status = response.status
                wf.steps[wf.step_index].results[response.action_id] = response
                wf.steps[wf.step_index].end_time = datetime.now()
                if response.status == "succeeded":
                    new_index = wf.step_index + 1
                    if new_index == len(wf.steps):
                        wf.status = WorkflowStatus.COMPLETED
                        wf.end_time = datetime.now()
                    else:
                        wf.step_index = new_index
                        if wf.status == WorkflowStatus.RUNNING:
                            wf.status = WorkflowStatus.IN_PROGRESS
                if response.status == "failed":
                    wf.status = WorkflowStatus.FAILED
                    wf.end_time = datetime.now()
            self.state_handler.set_workflow(wf)

    def handle_data_and_files(
        self, step: Step, wf: Workflow, response: ActionResult
    ) -> ActionResult:
        """create and save datapoints for data returned from step"""
        labeled_data = {}
        if response.data:
            for data_key in response.data:
                if step.data_labels is not None and data_key in step.data_labels:
                    label = step.data_labels[data_key]
                else:
                    label = data_key
                datapoint = ValueDataPoint(
                    label=label,
                    step_id=step.id,
                    workflow_id=wf.workflow_id,
                    experiment_id=wf.experiment_id,
                    value=response.data[data_key],
                )
                self.data_client.submit_datapoint(datapoint)
                labeled_data[label] = datapoint.id
        if response.files:
            for file_key in response.files:
                if step.data_labels is not None and file_key in step.data_labels:
                    label = step.data_labels[file_key]
                else:
                    label = file_key
                datapoint = FileDataPoint(
                    step_id=step.id,
                    workflow_id=wf.workflow_id,
                    experiment_id=wf.experiment_id,
                    label=label,
                    path=str(response.files[file_key]),
                )
                self.data_client.submit_datapoint(datapoint, datapoint.path)
                labeled_data[label] = datapoint.id
        response.data = labeled_data
        return response
