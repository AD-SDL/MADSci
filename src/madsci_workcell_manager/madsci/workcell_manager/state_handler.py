"""
State management for the WorkcellManager
"""

import warnings
from typing import Any, Callable, Optional, Union

from fastapi import HTTPException
from madsci.common.db_handlers import (
    MongoHandler,
    PyMongoHandler,
    PyRedisHandler,
    RedisHandler,
)
from madsci.common.types.node_types import Node
from madsci.common.types.workcell_types import (
    WorkcellInfo,
    WorkcellManagerSettings,
    WorkcellState,
    WorkcellStatus,
)
from madsci.common.types.workflow_types import Workflow, WorkflowDefinition
from madsci.common.utils import new_ulid_str
from pydantic import AnyUrl, ValidationError


class WorkcellStateHandler:
    """
    Manages state for a MADSci Workcell, providing transactional access to reading and writing state with
    optimistic check-and-set and locking.
    """

    state_change_marker = "0"
    shutdown: bool = False

    def __init__(
        self,
        workcell_settings: Optional[WorkcellManagerSettings] = None,
        workcell_id: Optional[str] = None,
        nodes: Optional[dict[str, str]] = None,
        redis_connection: Optional[Any] = None,
        mongo_connection: Optional[Any] = None,
        redis_handler: Optional[RedisHandler] = None,
        mongo_handler: Optional[MongoHandler] = None,
    ) -> None:
        """
        Initialize a StateManager for a given workcell.
        """
        self.workcell_settings = workcell_settings or WorkcellManagerSettings()
        self._workcell_id = (
            workcell_id or self.workcell_settings.manager_id or new_ulid_str()
        )
        self._nodes_config = nodes or self.workcell_settings.nodes or {}

        # Initialize Redis handler
        if redis_handler is not None:
            self._redis_handler = redis_handler
        elif redis_connection is not None:
            self._redis_handler = PyRedisHandler(redis_connection)
        else:
            self._redis_handler = PyRedisHandler.from_settings(
                host=str(self.workcell_settings.redis_host),
                port=int(self.workcell_settings.redis_port),
                password=self.workcell_settings.redis_password or None,
            )

        # Initialize MongoDB handler
        if mongo_handler is not None:
            self._mongo_handler = mongo_handler
        elif mongo_connection is not None:
            self._mongo_handler = PyMongoHandler(mongo_connection)
        else:
            self._mongo_handler = PyMongoHandler.from_url(
                str(self.workcell_settings.mongo_db_url),
                self.workcell_settings.database_name or "workcell_manager",
            )

        self.archived_workflows = self._mongo_handler.get_collection(
            "archived_workflows"
        )
        self.workflow_definitions = self._mongo_handler.get_collection(
            "workflow_definitions"
        )

        # Suppress InefficientAccessWarning from pottery if using PyRedisHandler
        try:
            from pottery import InefficientAccessWarning  # noqa: PLC0415

            warnings.filterwarnings("ignore", category=InefficientAccessWarning)
        except ImportError:
            pass

    def initialize_workcell_state(self) -> None:
        """
        Initializes the state of the workcell from settings.
        """
        self.set_workcell_status(WorkcellStatus(initializing=True))
        self._nodes.clear()
        self.state_change_marker = "0"

        # Initialize the workcell info in Redis from settings
        workcell_info = WorkcellInfo(
            name=self.workcell_settings.manager_name or "WorkcellManager",
            manager_id=self._workcell_id,
            description=self.workcell_settings.manager_description,
            nodes={k: AnyUrl(v) for k, v in self._nodes_config.items()},
        )
        self.set_workcell_info(workcell_info)

        # * Initialize Nodes
        for key, value in self._nodes_config.items():
            self.set_node(key, Node(node_url=AnyUrl(value)))
        status = self.get_workcell_status()
        status.initializing = False
        self.set_workcell_status(status)
        self.mark_state_changed()

    @property
    def _workcell_prefix(self) -> str:
        return f"madsci:workcell:{self._workcell_id}"

    @property
    def _workcell_info(self) -> Any:
        return self._redis_handler.create_dict(f"{self._workcell_prefix}:workcell_info")

    @property
    def _nodes(self) -> Any:
        return self._redis_handler.create_dict(f"{self._workcell_prefix}:nodes")

    @property
    def _workflow_queue(self) -> Any:
        return self._redis_handler.create_list(
            f"{self._workcell_prefix}:workflow_queue"
        )

    @property
    def _active_workflows(self) -> Any:
        return self._redis_handler.create_dict(
            f"{self._workcell_prefix}:active_workflows"
        )

    @property
    def _workcell_status(self) -> Any:
        return self._redis_handler.create_dict(f"{self._workcell_prefix}:status")

    def wc_state_lock(self) -> Any:
        """
        Gets a lock on the workcell's state. This should be called before any state updates are made,
        or where we don't want the state to be changing underneath us (i.e., in the engine).
        """
        return self._redis_handler.create_lock(
            f"{self._workcell_prefix}:state_lock",
            auto_release_time=60,
        )

    def node_lock(self, node_name: str) -> Any:
        """
        Gets a lock on a specific node's state. This should be called before any state updates are made to a node,
        or where we don't want the node's state to be changing underneath us (i.e., in the engine).
        """
        return self._redis_handler.create_lock(
            f"{self._workcell_prefix}:node:{node_name}:lock",
            auto_release_time=60,
        )

    # *State Methods
    def get_workcell_state(self) -> WorkcellState:
        """
        Return the current state of the workcell.
        """
        return WorkcellState(
            status=self.get_workcell_status(),
            workflow_queue=self.get_workflow_queue(),
            workcell_info=self.get_workcell_info(),
            nodes=self.get_nodes(),
        )

    def get_workcell_status(self) -> WorkcellStatus:
        """Return the current status of the workcell"""
        return WorkcellStatus.model_validate(self._workcell_status)

    def set_workcell_status(self, status: WorkcellStatus) -> None:
        """Set the status of the workcell"""
        self._workcell_status.update(**status.model_dump(mode="json"))
        self.mark_state_changed()

    def update_workcell_status(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> None:
        """Update the status of the workcell"""
        self.set_workcell_status(func(self.get_workcell_status(), *args, **kwargs))

    def mark_state_changed(self) -> int:
        """Marks the state as changed and returns the current state change counter"""
        return int(self._redis_handler.incr(f"{self._workcell_prefix}:state_changed"))

    def has_state_changed(self) -> bool:
        """Returns True if the state has changed since the last time this method was called"""
        state_change_marker = self._redis_handler.get(
            f"{self._workcell_prefix}:state_changed"
        )
        if state_change_marker != self.state_change_marker:
            self.state_change_marker = state_change_marker
            return True
        return False

    # *Workcell Methods
    def get_workcell_info(self) -> WorkcellInfo:
        """
        Returns the current workcell info as a WorkcellInfo object.
        """
        return WorkcellInfo.model_validate(self._workcell_info.to_dict())

    def set_workcell_info(self, workcell: WorkcellInfo) -> None:
        """
        Sets the active workcell info.
        """
        self.clear_workcell_info()
        self._workcell_info.update(**workcell.model_dump(mode="json"))

    def clear_workcell_info(self) -> None:
        """
        Empty the workcell info.
        """
        self._workcell_info.clear()

    def update_workcell_info(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> None:
        """
        Updates the workcell info.
        """
        self.set_workcell_info(func(self.get_workcell_info(), *args, **kwargs))

    # Workflow Definition Method
    def save_workflow_definition(self, workflow_definition: WorkflowDefinition) -> None:
        """move a workflow from redis to mongo"""
        self.workflow_definitions.insert_one(workflow_definition.to_mongo())
        return workflow_definition.workflow_definition_id

    def delete_workflow_definition(self, workflow_definition_id: str) -> None:
        """
        Deletes an active workflow by ID
        """
        self.workflow_definitions.delete_one({"workflow_id": workflow_definition_id})

    def get_workflow_definition(
        self, workflow_definition_id: str
    ) -> WorkflowDefinition:
        """
        Returns a workflow definition by ID
        """
        return WorkflowDefinition.model_validate(
            self.workflow_definitions.find_one(
                {"workflow_definition_id": workflow_definition_id}
            )
        )

    def get_workflow_definitions(
        self, number: int = 20
    ) -> dict[str, WorkflowDefinition]:
        """Get the latest experiments."""
        workflow_definition_list = (
            self.workflow_definitions.find()
            .sort("submitted_time", -1)
            .limit(number)
            .to_list()
        )
        workflow_definitions = {}
        for workflow_defintion in workflow_definition_list:
            valid_workflow_definition = WorkflowDefinition.model_validate(
                workflow_defintion
            )
            workflow_definitions[valid_workflow_definition.workflow_definition_id] = (
                valid_workflow_definition
            )
        return workflow_definitions

    # *Workflow Methods

    def get_workflow(self, workflow_id: str) -> Workflow:
        """Get an experiment by ID."""
        if workflow_id in self._active_workflows:
            workflow = self.get_active_workflow(workflow_id)
            if workflow:
                return workflow
        workflow = self.archived_workflows.find_one({"workflow_id": workflow_id})
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return Workflow.model_validate(workflow)

    def get_active_workflow(self, workflow_id: Union[str, str]) -> Optional[Workflow]:
        """
        Returns a workflow by ID, if it exists in the active workflows.
        """
        try:
            return Workflow.model_validate(self._active_workflows[str(workflow_id)])
        except KeyError:
            return None

    def get_active_workflows(self) -> dict[str, Workflow]:
        """
        Returns all active workflowS
        """
        valid_workflows = {}
        for workflow_id, workflow in self._active_workflows.to_dict().items():
            try:
                valid_workflows[str(workflow_id)] = Workflow.model_validate(workflow)
            except ValidationError:
                continue
        return valid_workflows

    def get_archived_workflows(self, number: int = 20) -> dict[str, Workflow]:
        """Get the latest experiments."""
        workflows_list = (
            self.archived_workflows.find()
            .sort("submitted_time", -1)
            .limit(number)
            .to_list()
        )
        workflows = {}
        for workflow in workflows_list:
            valid_workflow = Workflow.model_validate(workflow)
            workflows[valid_workflow.workflow_id] = valid_workflow
        return workflows

    def get_workflow_queue(self) -> list[Workflow]:
        """
        Returns the workflow queue
        """
        return [
            self.get_active_workflow(wf_id)
            for wf_id in self._workflow_queue
            if self.get_active_workflow(wf_id) is not None
        ]

    def update_workflow_queue(self) -> None:
        """
        Sets the workflow queue based on the current state of the workflows
        """
        for wf_id in self._workflow_queue:
            wf = self.get_active_workflow(wf_id)
            if wf is None or not wf.status.active:
                self._workflow_queue.remove(wf_id)
        self.mark_state_changed()

    def enqueue_workflow(self, workflow_id: str) -> None:
        """add a workflow to the workflow queue"""
        self._workflow_queue.append(workflow_id)

    def set_active_workflow(
        self, wf: Workflow, mark_state_changed: bool = True
    ) -> None:
        """
        Sets a workflow by ID
        """
        if isinstance(wf, Workflow):
            wf_dump = wf.model_dump(mode="json")
        else:
            wf_dump = Workflow.model_validate(wf).model_dump(mode="json")
        self._active_workflows[str(wf_dump["workflow_id"])] = wf_dump
        if mark_state_changed:
            self.mark_state_changed()

    def archive_workflow(self, workflow_id: str) -> None:
        """Move a workflow from redis to mongo"""
        try:
            workflow = self.get_active_workflow(workflow_id)
        except Exception:
            raise ValueError("Workflow is not active!") from None
        self.archived_workflows.insert_one(workflow.to_mongo())
        self.delete_active_workflow(workflow_id)

    def archive_terminal_workflows(self) -> None:
        """Move all completed workflows from redis to mongo"""
        for workflow_id, workflow in self._active_workflows.items():
            if Workflow.model_validate(workflow).status.terminal:
                self.archive_workflow(workflow_id)

    def delete_active_workflow(self, workflow_id: str) -> None:
        """
        Deletes an active workflow by ID
        """
        del self._active_workflows[str(workflow_id)]
        self.mark_state_changed()

    def delete_archived_workflow(self, workflow_id: str) -> None:
        """delete an archived workflow"""
        self.archived_workflows.delete_one({"workflow_id": workflow_id})

    def update_active_workflow(
        self, workflow_id: str, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> None:
        """
        Updates the state of a workflow.
        """
        self.set_active_workflow(
            func(self.get_active_workflow(workflow_id), *args, **kwargs)
        )

    def get_node(self, node_name: str) -> Node:
        """
        Returns a node by name
        """
        return Node.model_validate(self._nodes[node_name])

    def get_nodes(self) -> dict[str, Node]:
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

    def set_node(self, node_name: str, node: Union[Node, dict[str, Any]]) -> None:
        """
        Sets a node by name
        """
        if isinstance(node, Node):
            node_dump = node.model_dump(mode="json")
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

    def close(self) -> None:
        """Release Redis and MongoDB connections."""
        self._redis_handler.close()
        self._mongo_handler.close()
