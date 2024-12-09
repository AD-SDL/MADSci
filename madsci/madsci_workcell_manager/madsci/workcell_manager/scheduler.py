from madsci.workcell_manager.redis_handler import WorkcellRedisHandler
from madsci.workcell_manager.types import WorkcellManagerDefinition
from madsci.common.types.workflow_types import WorkflowStatus
from madsci.common.types.event_types import Event
from madsci.common.utils import threaded_task
import time
import datetime

def send_event(test: Event):
    pass


class Scheduler: 
    def __init__(self, workcell_manager_definition: WorkcellManagerDefinition):
        self.state_handler = WorkcellRedisHandler(workcell_manager_definition)
        self.workcell_manager_definition = workcell_manager_definition
        self.running = True
    def run_iteration(self):
        pass
    
    @threaded_task
    def start(self):
        while self.running is True:
            self.run_iteration()
            time.sleep(self.workcell_manager_definition.plugin_config.scheduler_interval)
            
class DefaultScheduler(Scheduler):

    def run_iteration(self):
        for run_id, wf_run in self.state_handler.get_all_workflow_runs().items():
                if wf_run.status == WorkflowStatus.NEW:
                    wf_run.status = WorkflowStatus.QUEUED
                    print(
                        f"Processed new workflow: {wf_run.name} with run_id: {run_id}"
                    )
                    #send_event(WorkflowQueuedEvent.from_wf_run(wf_run=wf_run))
                    self.state_handler.set_workflow_run(wf_run)
                elif wf_run.status in [
                    WorkflowStatus.QUEUED,
                    WorkflowStatus.IN_PROGRESS,
                ]:
                    step = wf_run.steps[wf_run.step_index]
                    if check_step(wf_run.experiment_id, run_id, step):
                        module = find_step_module(
                            self.state_handler.get_workcell(), step.module
                        )

                        #if wf_run.status == WorkflowStatus.QUEUED:
                            #send_event(WorkflowStartEvent.from_wf_run(wf_run=wf_run))
                        wf_run.status = WorkflowStatus.RUNNING
                        print(
                            f"Starting step {wf_run.name}.{step.name} for run: {run_id}"
                        )
                        if wf_run.step_index == 0:
                            wf_run.start_time = datetime.now()
                        self.state_handler.set_workflow_run(wf_run)
                        run_step(wf_run=wf_run, module=module)
        

