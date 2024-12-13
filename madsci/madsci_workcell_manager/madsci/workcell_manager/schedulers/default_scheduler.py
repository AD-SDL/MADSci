from schedulers.scheduler import AbstractScheduler
from madsci.common.types.workflow_types import WorkflowStatus
from madsci.common.types.node_types import Node
from madsci.common.types.step_types import Step
from madsci.common.utils import threaded_daemon
from madsci.client.node.abstract_node_client import AbstractNodeClient
from workcell_utils import find_node_client
from redis_handler import WorkcellRedisHandler
from madsci.common.types.action_types import ActionRequest, ActionStatus, ActionResult
from datetime import datetime
from typing import Optional


class Scheduler(AbstractScheduler):

    def run_iteration(self):
        workflows = sorted(self.state_handler.get_all_workflows().values(), key=lambda item: item.scheduler_metadata.submitted_time)
        for wf in workflows:
                workflow_id = wf.workflow_id
                if wf.scheduler_metadata.status == WorkflowStatus.NEW:
                    wf.scheduler_metadata.status = WorkflowStatus.QUEUED
                    print(
                        f"Processed new workflow: {wf.name} with id: {workflow_id}"
                    )
                    #send_event(WorkflowQueuedEvent.from_wf_run(wf_run=wf_run))
                    self.state_handler.set_workflow(wf)
                elif wf.scheduler_metadata.status in [
                    WorkflowStatus.QUEUED,
                    WorkflowStatus.IN_PROGRESS,
                ]:
                    step = wf.steps[wf.scheduler_metadata.step_index]
                    if self.check_step(step):

                        #if wf_run.status == WorkflowStatus.QUEUED:
                            #send_event(WorkflowStartEvent.from_wf_run(wf_run=wf_run))
                        wf.scheduler_metadata.status = WorkflowStatus.RUNNING
                        print(
                            f"Starting step {wf.name}.{step.name} for workflow: {workflow_id}"
                        )
                        if wf.scheduler_metadata.step_index == 0:
                            wf.scheduler_metadata.start_time = datetime.now()
                        self.state_handler.set_workflow(wf)
                        self.run_step(workflow_id, step)
    def check_step(self, step: Step):
        return self.resource_checks(step) and self.node_checks(step)
        
    def resource_checks(self, step: Step):
        return True

    def node_checks(self, step: Step):
        node = self.state_handler.get_node(step.node)
        if node.status.ready:
            return True
        return False
    
    def retry_action(self, node: Node, client: AbstractNodeClient, response: Optional[ActionResult] = None):
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
        node = self.state_handler.get_node(step.node)
        client = find_node_client(node.node_url)
        try:
            request = ActionRequest(action_name=step.action, args=step.args, files=step.files)
            response = client.send_action(request)
        except Exception:
            response = self.retry_action(node, client)
        response = self.retry_action(node, client, response)
        with self.state_handler.wc_state_lock():
            wf = self.state_handler.get_workflow(workflow_id)
            if response.status in ["succeeded", "failed"]:
                wf.steps[wf.scheduler_metadata.step_index].status = response.status
                wf.steps[wf.scheduler_metadata.step_index].results[response.action_id] = response
                if response.status == "succeeded":
                    new_index = wf.scheduler_metadata.step_index + 1
                    if new_index == len(wf.flowdef):
                        wf.scheduler_metadata.status = WorkflowStatus.COMPLETED
                    else:
                        wf.scheduler_metadata.step_index = new_index
                        wf.scheduler_metadata.status = WorkflowStatus.QUEUED
                if response.status == "failed":
                    wf.scheduler_metadata.status = WorkflowStatus.FAILED
            #print(self.state_handler.get_all_workflows())
            #print(wf)
            self.state_handler.set_workflow(wf)
            #print(self.state_handler.get_all_workflows())

                
            
    
            
        
            

              
        
        
    

