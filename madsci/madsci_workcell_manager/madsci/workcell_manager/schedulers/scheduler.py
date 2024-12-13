from madsci.workcell_manager.redis_handler import WorkcellRedisHandler
from madsci.workcell_manager.workcell_manager_types import WorkcellManagerDefinition
from madsci.common.types.event_types import Event

def send_event(test: Event):
    pass


class AbstractScheduler: 
    def __init__(self, workcell_manager_definition: WorkcellManagerDefinition, state_handler: WorkcellRedisHandler):
        self.state_handler = state_handler
        self.workcell_manager_definition = workcell_manager_definition
        self.running = True
    def run_iteration(self):
        pass
    
    
