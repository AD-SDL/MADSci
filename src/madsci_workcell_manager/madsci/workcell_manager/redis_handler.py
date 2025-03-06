"""
State management for the WorkcellManager
"""

import warnings
from typing import Any, Callable, Optional, Union

import redis
from madsci.common.types.base_types import new_ulid_str
from madsci.common.types.node_types import Node, NodeDefinition
from madsci.common.types.workcell_types import WorkcellDefinition
from madsci.common.types.workflow_types import Workflow
from pottery import InefficientAccessWarning, RedisDict, RedisList, Redlock
from pydantic import ValidationError


class WorkcellRedisHandler:
    """
    Manages state for WEI, providing transactional access to reading and writing state with
    optimistic check-and-set and locking.
    """

    state_change_marker = "0"
    _redis_connection: Any = None

    def __init__(
        self,
        workcell_definition: WorkcellDefinition,
        redis_connection: Optional[Any] = None,
    ) -> None:
        """
        Initialize a StateManager for a given workcell.
        """
        self._workcell_name = workcell_definition.workcell_name
        self._redis_host = workcell_definition.config.redis_host
        self._redis_port = workcell_definition.config.redis_port
        self._redis_password = workcell_definition.config.redis_password
        self._redis_connection = redis_connection
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
        return RedisDict(key=f"{self._workcell_prefix}:nodes", redis=self._redis_client)

    @property
    def _workflow_queue(self) -> RedisList:
        return RedisList(
            key=f"{self._workcell_prefix}:workflow_queue", redis=self._redis_client
        )

    @property
    def _workflows(self) -> RedisDict:
        return RedisDict(
            key=f"{self._workcell_prefix}:workflows", redis=self._redis_client
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
    def get_state(self) -> dict[str, dict[Any, Any]]:
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

    def clear_state(self, clear_workflows: bool = False) -> None:
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
    def get_workflow(self, workflow_id: Union[str, str]) -> Workflow:
        """
        Returns a workflow by ID
        """
        return Workflow.model_validate(self._workflows[str(workflow_id)])

    def get_all_workflows(self) -> dict[str, Workflow]:
        """
        Returns all workflow runs
        """
        valid_workflows = {}
        for workflow_id, workflow in self._workflows.to_dict().items():
            try:
                valid_workflows[str(workflow_id)] = Workflow.model_validate(workflow)
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
        self._workflows[str(wf_dump["workflow_id"])] = wf_dump
        self.mark_state_changed()

    def set_workflow_quiet(self, wf: Workflow) -> None:
        """
        Sets a workflow by ID
        """
        if isinstance(wf, Workflow):
            wf_dump = wf.model_dump(mode="json")
        else:
            wf_dump = Workflow.model_validate(wf).model_dump(mode="json")
        self._workflows[str(wf_dump["workflow_id"])] = wf_dump

    def delete_workflow(self, workflow_id: Union[str, str]) -> None:
        """
        Deletes a workflow by ID
        """
        del self._workflows[str(workflow_id)]
        self.mark_state_changed()

    def update_workflow(
        self, workflow_id: str, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> None:
        """
        Updates the state of a workflow.
        """
        self.set_workflow(func(self.get_workflow(workflow_id), *args, **kwargs))

    def get_node(self, node_name: str) -> Node:
        """
        Returns a node by name
        """
        return Node.model_validate(self._nodes[node_name])

    def get_all_nodes(self) -> dict[str, Node]:
        """
        Returns all nodes
        """
        valid_nodes = {}
        for node_name, node in self._nodes.to_dict().items():
            try:
                valid_nodes[str(node_name)] = Node.model_validate(node)
            except ValidationError:
                continue
        return valid_nodes

    def set_node(
        self, node_name: str, node: Union[Node, NodeDefinition, dict[str, Any]]
    ) -> None:
        """
        Sets a node by name
        """
        if isinstance(node, Node):
            node_dump = node.model_dump(mode="json")
        elif isinstance(node, NodeDefinition):
            node_dump = Node.model_validate(node, from_attributes=True).model_dump(
                mode="json"
            )
        else:
            node_dump = Node.model_validate(node).model_dump(mode="json")
        self._nodes[node_name] = node_dump
        self.mark_state_changed()

    def delete_node(self, node_name: str) -> None:
        """
        Deletes a node by name
        """
        del self._nodes[node_name]
        self.mark_state_changed()

    def update_node(
        self, node_name: str, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> None:
        """
        Updates the state of a node.
        """
        self.set_node(node_name, func(self.get_node(node_name), *args, **kwargs))
