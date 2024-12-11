"""
StateManager for WEI
"""

import warnings
from typing import Any, Callable, Dict, Union

import redis
from pottery import InefficientAccessWarning, RedisDict, Redlock
from pydantic import ValidationError

from madsci.common.types.workcell_types import WorkcellDefinition
from madsci.common.types.workflow_types import Workflow
from madsci.common.types.base_types import new_ulid_str
from madsci.workcell_manager.workcell_manager_types import WorkcellManagerDefinition


class WorkcellRedisHandler:
    """
    Manages state for WEI, providing transactional access to reading and writing state with
    optimistic check-and-set and locking.
    """

    state_change_marker = "0"
    _redis_connection: Any = None

    def __init__(self, workcell_manager_definition: WorkcellManagerDefinition) -> None:
        """
        Initialize a StateManager for a given workcell.
        """
        self._workcell_name = workcell_manager_definition.plugin_config.workcell_name
        self._redis_host = workcell_manager_definition.plugin_config.redis_host
        self._redis_port = workcell_manager_definition.plugin_config.redis_port
        self._redis_password = workcell_manager_definition.plugin_config.redis_password
        warnings.filterwarnings("ignore", category=InefficientAccessWarning)

    @property
    def _workcell_prefix(self) -> str:
        return f"workcell:{self._workcell_name}"

    @property
    def _redis_client(self) -> Any:
        """
        Returns a redis.Redis client, but only creates one connection.
        MyPy can't handle Redis object return types for some reason, so no type-hinting.
        """
        if self._redis_connection is None:
            self._redis_connection = redis.Redis(
                host=str(self._redis_host),
                port=int(self._redis_port),
                db=0,
                decode_responses=True,
                password=self._redis_password if self._redis_password else None,
            )
        return self._redis_connection

    @property
    def _workcell(self) -> RedisDict:
        return RedisDict(
            key=f"{self._workcell_prefix}:workcell", redis=self._redis_client
        )
    @property
    def _nodes(self) -> RedisDict:
        return RedisDict(
            key=f"{self._workcell_prefix}:nodes", redis=self._redis_client
        )
    @property
    def _workflows(self) -> RedisDict:
        return RedisDict(
            key=f"{self._workcell_prefix}:workflow_runs", redis=self._redis_client
        )


    def wc_state_lock(self) -> Redlock:
        """
        Gets a lock on the workcell's state. This should be called before any state updates are made,
        or where we don't want the state to be changing underneath us (i.e., in the engine).
        """
        return Redlock(
            key=f"{self._workcell_prefix}:state_lock",
            masters={self._redis_client},
            auto_release_time=60,
        )

    # *State Methods
    def get_state(self) -> Dict[str, Dict[Any, Any]]:
        """
        Return a dict containing the current state of the workcell.
        """
        return {
            "status": self.wc_status,
            "error": self.error,
            "nodes": self._nodes.to_dict(),
            "workflows": self._workflow_runs.to_dict(),
            "workcell": self._workcell.to_dict(),
            "paused": self.paused,
            "locked": self.locked,
            "shutdown": self.shutdown,
        }


    @property
    def error(self) -> str:
        """Latest error on the server"""
        return self._redis_client.get(f"{self._workcell_prefix}:error")

    @error.setter
    def error(self, value: str) -> None:
        """Add an error to the workcell's error deque"""
        if self.error != value:
            self.mark_state_changed()
        return self._redis_client.set(f"{self._workcell_prefix}:error", value)

    def clear_state(
        self, clear_workflows: bool = False
    ) -> None:
        """
        Clears the state of the workcell, optionally leaving the locations state intact.
        """
        self._nodes.clear()
        if clear_workflows:
            self._workflows.clear()
        self.state_change_marker = "0"
        self.paused = False
        self.locked = False
        self.shutdown = False
        self.mark_state_changed()

    def mark_state_changed(self) -> int:
        """Marks the state as changed and returns the current state change counter"""
        return int(self._redis_client.incr(f"{self._workcell_prefix}:state_changed"))

    def has_state_changed(self) -> bool:
        """Returns True if the state has changed since the last time this method was called"""
        state_change_marker = self._redis_client.get(
            f"{self._workcell_prefix}:state_changed"
        )
        if state_change_marker != self.state_change_marker:
            self.state_change_marker = state_change_marker
            return True
        return False

    # *Workcell Methods
    def get_workcell(self) -> WorkcellDefinition:
        """
        Returns the current workcell as a Workcell object
        """
        return WorkcellDefinition.model_validate(self._workcell.to_dict())

    def set_workcell(self, workcell: WorkcellDefinition) -> None:
        """
        Sets the active workcell
        """
        self._workcell.update(**workcell.model_dump(mode="json"))

    def clear_workcell(self) -> None:
        """
        Empty the workcell definition
        """
        self._workcell.clear()

    def get_workcell_id(self) -> str:
        """
        Returns the workcell ID
        """
        wc_id = self._redis_client.get(f"{self._workcell_prefix}:workcell_id")
        if wc_id is None:
            self._redis_client.set(
                f"{self._workcell_prefix}:workcell_id", new_ulid_str()
            )
            wc_id = self._redis_client.get(f"{self._workcell_prefix}:workcell_id")
        return wc_id

    # *Workflow Methods
    def get_workflow(self, run_id: Union[str, str]) -> Workflow:
        """
        Returns a workflow by ID
        """
        return Workflow.model_validate(self._workflows[str(run_id)])

    def get_all_workflows(self) -> dict[str, Workflow]:
        """
        Returns all workflow runs
        """
        valid_workflows = {}
        for run_id, workflow in self._workflows.to_dict().items():
            try:
                valid_workflows[str(run_id)] = Workflow.model_validate(
                    workflow
                )
            except ValidationError:
                continue
        return valid_workflows

    def set_workflow(self, wf: Workflow) -> None:
        """
        Sets a workflow by ID
        """
        if isinstance(wf, Workflow):
            wf_dump = wf.model_dump(mode="json")
        else:
            wf_dump = Workflow.model_validate(wf).model_dump(mode="json")
        self._workflows[str(wf_dump["run_id"])] = wf_dump
        self.mark_state_changed()

    def delete_workflow(self, run_id: Union[str, str]) -> None:
        """
        Deletes a workflow by ID
        """
        del self._workflows[str(run_id)]
        self.mark_state_changed()

    def update_workflow(
        self, run_id: str, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> None:
        """
        Updates the state of a workflow.
        """
        self.set_workflow(func(self.get_workflow(run_id), *args, **kwargs))

