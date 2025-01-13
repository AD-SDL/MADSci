"""
Engine Class and associated helpers and data
"""

import time
import importlib
import traceback

import requests
import importlib
from madsci.common.types.node_types import Node
from workcell_utils import initialize_workcell, update_active_nodes
from workcell_manager_types import WorkcellManagerDefinition
from redis_handler import WorkcellRedisHandler
from workflow_utils import cancel_active_workflows
from madsci.common.utils import threaded_daemon
from madsci.client.node.abstract_node_client import AbstractNodeClient
from workcell_utils import find_node_client
from redis_handler import WorkcellRedisHandler
from madsci.common.types.action_types import ActionRequest, ActionStatus, ActionResult
from madsci.common.types.workflow_types import WorkflowStatus
from madsci.common.types.step_types import Step
from datetime import datetime

from typing import Optional
class Engine:
    """
    Handles scheduling workflows and executing steps on the workcell.
    Pops incoming workflows off a redis-based queue and executes them.
    """

    def __init__(self, workcell_manager_definition: WorkcellManagerDefinition, state_manager: WorkcellRedisHandler) -> None:
        """Initialize the scheduler."""
        state_manager.clear_state(
            clear_workflows=workcell_manager_definition.plugin_config.clear_workflows
        )
        self.definition = workcell_manager_definition
        self.state_manager = state_manager
        cancel_active_workflows(state_manager)
        scheduler_module = importlib.import_module(self.definition.plugin_config.scheduler)
        self.scheduler = scheduler_module.Scheduler(self.definition, self.state_manager)
        with state_manager.wc_state_lock():
            initialize_workcell(state_manager)
        time.sleep(workcell_manager_definition.plugin_config.cold_start_delay)

        print("Engine initialized, waiting for workflows...")
        #send_event(WorkcellStartEvent(workcell=state_manager.get_workcell()))

    def spin(self) -> None:
        """
        Continuously loop, updating module states every Config.update_interval seconds.
        If the state of the workcell has changed, update the active modules and run the scheduler.
        """
        update_active_nodes(self.state_manager)
        node_tick = time.time()
        scheduler_tick = time.time()
        heartbeat = time.time()
        while True and not self.state_manager.shutdown:
            try:
                if time.time() - heartbeat > 2:
                    heartbeat = time.time()
                    print(f"Heartbeat: {time.time()}")
                if (
                    time.time() - node_tick > self.definition.plugin_config.node_update_interval
                    or self.state_manager.has_state_changed()
                ):
                    if not self.state_manager.paused:
                        update_active_nodes(self.state_manager)
                    node_tick = time.time()
                if time.time() - scheduler_tick > self.definition.plugin_config.scheduler_update_interval:
                    with self.state_manager.wc_state_lock():
                        self.scheduler.run_iteration()
                        self.run_next_step()
                        scheduler_tick = time.time()
            except Exception:
                traceback.print_exc()
                print(
                    f"Error in engine loop, waiting {self.definition.plugin_config.node_update_interval} seconds before trying again."
                )
                time.sleep(self.definition.plugin_config.node_update_interval)

    @threaded_daemon
    def start_engine_thread(self) -> None:
        """Spins the engine in its own thread"""
        self.spin()
    
    def run_next_step(self):
        workflows = self.state_manager.get_all_workflows()
        ready_workflows = filter(lambda wf: wf.scheduler_metadata.ready_to_run, workflows.values())
        sorted_ready_workflows = sorted(ready_workflows, key=lambda wf: wf.scheduler_metadata.priority)
        if len(sorted_ready_workflows) > 0:
            next_wf = sorted_ready_workflows[0]
            next_wf.status = WorkflowStatus.RUNNING
            self.state_manager.set_workflow(next_wf)
            self.run_step(next_wf.workflow_id, next_wf.steps[next_wf.step_index])

    def retry_action(self, node: Node, client: AbstractNodeClient, request: ActionRequest, response: Optional[ActionResult] = None):
        if node.info.capabilities.get_action_result:

            while response is None or response.status not in ["not_ready", "succeeded", "failed"]:
                try:
                    response = client.get_action_result(request.action_id)
                    time.sleep(5)
                except Exception:
                    time.sleep(5)
            return response
        return response
    @threaded_daemon
    def run_step(self, workflow_id: str, step: Step):
        with self.state_manager.wc_state_lock():
            wf = self.state_manager.get_workflow(workflow_id)
            wf.steps[wf.step_index].start_time = datetime.now()
            if wf.step_index == 0:
                wf.start_time = datetime.now()
            self.state_manager.set_workflow(wf)
        node = self.state_manager.get_node(step.node)
        client = find_node_client(node.node_url)
        try:
            request = ActionRequest(action_name=step.action, args=step.args, files=step.files)
            response = client.send_action(request)
        except Exception:
            response = self.retry_action(node, client, request)
        response = self.retry_action(node, client, request, response)
        if response is None:
            response = request.failed()
        with self.state_manager.wc_state_lock():
            wf = self.state_manager.get_workflow(workflow_id)
            if response.status in ["succeeded", "failed"]:
                wf.steps[wf.step_index].status = response.status
                wf.steps[wf.step_index].results[response.action_id] = response
                wf.steps[wf.step_index].end_time = datetime.now()
                if response.status == "succeeded":
                    new_index = wf.step_index + 1
                    if new_index == len(wf.flowdef):
                        wf.status = WorkflowStatus.COMPLETED
                        wf.end_time = datetime.now()
                    else:
                        wf.step_index = new_index
                        if wf.status == WorkflowStatus.RUNNING:
                            wf.status = WorkflowStatus.IN_PROGRESS
                if response.status == "failed":
                    wf.status = WorkflowStatus.FAILED
                    wf.end_time = datetime.now()
            #print(self.state_manager.get_all_workflows())
            #print(wf)
            self.state_manager.set_workflow(wf)
            #print(self.state_manager.get_all_workflows())

                