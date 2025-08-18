"""
State management for the WorkcellManager
"""

import warnings
from typing import Any, Callable, Optional, Union

import redis
from fastapi import HTTPException
from madsci.client.resource_client import ResourceClient
from madsci.common.types.location_types import Location
from madsci.common.types.node_types import Node, NodeDefinition
from madsci.common.types.workcell_types import (
    WorkcellDefinition,
    WorkcellManagerSettings,
    WorkcellState,
    WorkcellStatus,
)
from madsci.common.types.workflow_types import Workflow
from pottery import InefficientAccessWarning, RedisDict, RedisList, Redlock
from pydantic import AnyUrl, ValidationError
from pymongo import MongoClient
from pymongo.synchronous.database import Database


class WorkcellStateHandler:
    """
    Manages state for a MADSci Workcell, providing transactional access to reading and writing state with
    optimistic check-and-set and locking.
    """

    state_change_marker = "0"
    _redis_connection: Any = None
    shutdown: bool = False

    def __init__(
        self,
        workcell_definition: Optional[WorkcellDefinition] = None,
        workcell_settings: Optional[WorkcellManagerSettings] = None,
        redis_connection: Optional[Any] = None,
        mongo_connection: Optional[Database] = None,
    ) -> None:
        """
        Initialize a StateManager for a given workcell.
        """
        self.workcell_settings = workcell_settings or WorkcellManagerSettings()
        self._workcell_id = workcell_definition.workcell_id
        self._redis_host = self.workcell_settings.redis_host
        self._redis_port = self.workcell_settings.redis_port
        self._redis_password = self.workcell_settings.redis_password
        self._redis_connection = redis_connection
        if mongo_connection is not None:
            self.db_connection = mongo_connection
        else:
            self.db_client = MongoClient(self.workcell_settings.mongo_url)
            self.db_connection = self.db_client["workcell_manager"]
        self.archived_workflows = self.db_connection["archived_workflows"]
        warnings.filterwarnings("ignore", category=InefficientAccessWarning)
        self.set_workcell_definition(workcell_definition)

    def initialize_workcell_state(
        self, resource_client: Optional[ResourceClient] = None
    ) -> None:
        """
        Initializes the state of the workcell from the workcell definition.
        """
        self.set_workcell_status(WorkcellStatus(initializing=True))
        self._nodes.clear()
        self.state_change_marker = "0"
        # * Initialize Nodes
        for key, value in self.get_workcell_definition().nodes.items():
            self.set_node(key, Node(node_url=AnyUrl(value)))
        # * Initialize Locations and Resources
        self.initialize_locations_and_resources(resource_client)
        # TODO: Update the workcell definition with the new locations and resources
        status = self.get_workcell_status()
        status.initializing = False
        self.set_workcell_status(status)
        self.mark_state_changed()

    def initialize_locations_and_resources(
        self, resource_client: Optional[ResourceClient] = None
    ) -> None:
        """Set the workcell's location based on the location definitions in the workcell, and create resources if necessary/possible"""
        workcell = self.get_workcell_definition()
        for location_definition in workcell.locations:
            resource = None
            if (
                location_definition.resource_definition is not None
                and resource_client is not None
            ):
                resource = resource_client.init_resource(
                    resource_definition=location_definition.resource_definition
                )
            location = Location.model_validate(location_definition.model_dump())
            if resource:
                location.resource_id = resource.resource_id
            self.set_location(location)

    @property
    def _workcell_prefix(self) -> str:
        return f"madsci:workcell:{self._workcell_id}"

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
    def _workcell_definition(self) -> RedisDict:
        return RedisDict(
            key=f"{self._workcell_prefix}:workcell_definition", redis=self._redis_client
        )

    @property
    def _nodes(self) -> RedisDict:
        return RedisDict(key=f"{self._workcell_prefix}:nodes", redis=self._redis_client)

    @property
    def _locations(self) -> RedisDict:
        return RedisDict(
            key=f"{self._workcell_prefix}:locations", redis=self._redis_client
        )

    @property
    def _workflow_queue(self) -> RedisList:
        return RedisList(
            key=f"{self._workcell_prefix}:workflow_queue", redis=self._redis_client
        )

    @property
    def _active_workflows(self) -> RedisDict:
        return RedisDict(
            key=f"{self._workcell_prefix}:active_workflows", redis=self._redis_client
        )

    @property
    def _workcell_status(self) -> RedisDict:
        return RedisDict(
            key=f"{self._workcell_prefix}:status", redis=self._redis_client
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
    def get_workcell_state(self) -> WorkcellState:
        """
        Return the current state of the workcell.
        """
        return WorkcellState(
            status=self.get_workcell_status(),
            workflow_queue=self.get_workflow_queue(),
            workcell_definition=self.get_workcell_definition(),
            nodes=self.get_nodes(),
            locations=self.get_locations(),
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
    def get_workcell_definition(self) -> WorkcellDefinition:
        """
        Returns the current workcell definition as a WorkcellDefinition object
        """
        return WorkcellDefinition.model_validate(self._workcell_definition.to_dict())

    def set_workcell_definition(self, workcell: WorkcellDefinition) -> None:
        """
        Sets the active workcell
        """
        self.clear_workcell_definition()
        self._workcell_definition.update(**workcell.model_dump(mode="json"))

    def clear_workcell_definition(self) -> None:
        """
        Empty the workcell definition
        """
        self._workcell_definition.clear()

    def update_workcell_definition(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> None:
        """
        Updates the workcell definition
        """
        self.set_workcell_definition(
            func(self.get_workcell_definition(), *args, **kwargs)
        )

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

    def get_location(self, location_id: str) -> Location:
        """
        Returns a location by ID
        """
        return Location.model_validate(self._locations[location_id])

    def get_locations(self) -> dict[str, Location]:
        """
        Returns all locations
        """
        valid_locations = {}
        for location in self._locations:
            try:
                valid_locations[location] = Location.model_validate(
                    self._locations[location]
                )
            except ValidationError:
                continue
        return valid_locations

    def set_location(self, location: Union[Location, dict[str, Any]]) -> None:
        """
        Sets a location by ID
        """
        if isinstance(location, Location):
            location_dump = location.model_dump(mode="json")
        else:
            location_dump = Location.model_validate(location).model_dump(mode="json")
        self._locations[location_dump["location_id"]] = location_dump
        self.mark_state_changed()

    def delete_location(self, location_id: str) -> None:
        """
        Deletes a location by ID
        """
        del self._locations[location_id]
        self.mark_state_changed()

    def update_location(
        self, location_id: str, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> None:
        """
        Updates the state of a location.
        """
        self.set_location(func(self.get_location(location_id), *args, **kwargs))
