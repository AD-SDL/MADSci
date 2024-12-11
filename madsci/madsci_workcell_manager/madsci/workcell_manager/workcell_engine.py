"""
Engine Class and associated helpers and data
"""

import time
import traceback

import requests
import importlib
#from schedulers.default_scheduler import DefaultScheduler
from workcell_utils import initialize_state
from workcell_manager_types import WorkcellManagerDefinition
from redis_handler import WorkcellRedisHandler
from workflow_utils import cancel_active_workflows

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
        cancel_active_workflows(state_manager)
        #self.scheduler = DefaultScheduler()
        with state_manager.wc_state_lock():
            initialize_state(state_manager)
        #time.sleep(workcell_manager_definition.plugin_config.cold_start_delay)

        print("Engine initialized, waiting for workflows...")
        #send_event(WorkcellStartEvent(workcell=state_manager.get_workcell()))

    