"""
State management for the WorkcellManager
"""

import warnings
from typing import Any, Callable, Optional, Union

import redis
from madsci.client.resource_client import ResourceClient
from madsci.common.types.location_types import Location
from madsci.common.types.node_types import Node, NodeDefinition
from madsci.common.types.resource_types import Resource
from madsci.common.types.workcell_types import (
    WorkcellDefinition,
    WorkcellState,
    WorkcellStatus,
)
from madsci.common.types.workflow_types import Workflow
from pottery import InefficientAccessWarning, RedisDict, RedisList, Redlock
from pydantic import AnyUrl, ValidationError


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
        self._workcell_id = workcell_definition.workcell_id
        self._workcell_definition_path = workcell_definition._definition_path
        self._redis_host = workcell_definition.config.redis_host
        self._redis_port = workcell_definition.config.redis_port
        self._redis_password = workcell_definition.config.redis_password
        self._redis_connection = redis_connection
        self.shutdown = False
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
            if isinstance(value, NodeDefinition):
                node = Node(node_url=value.node_url)
            elif isinstance(value, (AnyUrl, str)):
                node = Node(node_url=AnyUrl(value))
            self.set_node(key, node)
        # * Initialize Locations and Resources
        self.initialize_locations_and_resources(resource_client)
        updated_workcell = self.get_workcell_definition()
        if self._workcell_definition_path is not None:
            updated_workcell.to_yaml(self._workcell_definition_path)
        status = self.get_workcell_status()
        status.initializing = False
        self.set_workcell_status(status)
        self.mark_state_changed()

    def initialize_locations_and_resources(
        self, resource_client: Optional[ResourceClient] = None
    ) -> None:
        """Set the workcell's location based on the location definitions in the workcell, and create resources if necessary/possible"""
        workcell = self.get_workcell_definition()
        for index in range(len(workcell.locations)):
            location_definition = workcell.locations[index]
            if (
                location_definition.resource_definition is not None
                and resource_client is not None
                and location_definition.resource_id is None
            ):
                resource = Resource.discriminate(
                    location_definition.resource_definition
                )

                resource = resource_client.add_resource(resource)
                location_definition.resource_id = resource.resource_id
            try:
                # * Update existing location if it exists
                existing_location = self.get_location(location_definition.location_id)
                existing_location = existing_location.model_copy(
                    update=location_definition.model_dump()
                )
                self.set_location(existing_location)
            except KeyError:
                # * Create new location if it doesn't exist
                self.set_location(Location.model_validate(location_definition))
            workcell.locations[index] = location_definition
        self.set_workcell_definition(workcell)

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
    def _workflows(self) -> RedisDict:
        return RedisDict(
            key=f"{self._workcell_prefix}:workflows", redis=self._redis_client
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
    def get_workflow(self, workflow_id: Union[str, str]) -> Workflow:
        """
        Returns a workflow by ID
        """
        return Workflow.model_validate(self._workflows[str(workflow_id)])

    def get_workflows(self) -> dict[str, Workflow]:
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

    def get_workflow_queue(self) -> list[Workflow]:
        """
        Returns the workflow queue
        """
        return [self.get_workflow(wf_id) for wf_id in self._workflow_queue]

    def update_workflow_queue(self) -> None:
        """
        Sets the workflow queue based on the current state of the workflows
        """
        self._workflow_queue.clear()
        for wf in self.get_workflows().values():
            if wf.status.is_active:
                self._workflow_queue.append(wf.workflow_id)
        self.mark_state_changed()

    def set_workflow(self, wf: Workflow, mark_state_changed: bool = True) -> None:
        """
        Sets a workflow by ID
        """
        if isinstance(wf, Workflow):
            wf_dump = wf.model_dump(mode="json")
        else:
            wf_dump = Workflow.model_validate(wf).model_dump(mode="json")
        self._workflows[str(wf_dump["workflow_id"])] = wf_dump
        if mark_state_changed:
            self.mark_state_changed()

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
