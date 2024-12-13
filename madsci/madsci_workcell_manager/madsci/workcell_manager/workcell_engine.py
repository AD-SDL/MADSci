"""
Engine Class and associated helpers and data
"""

import time
import importlib
import traceback

import requests
import importlib
#from schedulers.default_scheduler import DefaultScheduler
from workcell_utils import initialize_workcell, update_active_nodes
from workcell_manager_types import WorkcellManagerDefinition
from redis_handler import WorkcellRedisHandler
from workflow_utils import cancel_active_workflows
from madsci.common.utils import threaded_daemon
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
                    self.scheduler.run_iteration()
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
