from schedulers.scheduler import AbstractScheduler
from madsci.common.types.step_types import Step

from datetime import datetime
from typing import Optional


class Scheduler(AbstractScheduler):

    def run_iteration(self):
        priority = 0
        workflows = sorted(self.state_handler.get_all_workflows().values(), key=lambda item: item.submitted_time)
        for wf in workflows:
                step = wf.steps[wf.step_index]
                wf.scheduler_metadata.ready_to_run = not(wf.paused) and wf.status in ["queued", "in_progress"] and self.check_step(step)
                wf.scheduler_metadata.priority = priority
                priority -= 1
                self.state_handler.set_workflow_quiet(wf)
    def check_step(self, step: Step):
        return self.resource_checks(step) and self.node_checks(step)
        
    def resource_checks(self, step: Step):
        return True

    def node_checks(self, step: Step):
        node = self.state_handler.get_node(step.node)
        if node is not None and node.status.ready:
            return True
        return False
    
    
            
    
            
        
            

              
        
        
    

