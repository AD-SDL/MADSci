"""utility functions for the workcell"""

import concurrent
import warnings

import requests
import yaml
from madsci.client.node import NODE_CLIENT_MAP, AbstractNodeClient
from madsci.client.resource_client import ResourceClient
from madsci.common.types.node_types import Node, NodeDefinition
from madsci.common.types.resource_types import Resource
from madsci.common.types.workcell_types import WorkcellDefinition, WorkcellLink
from madsci.workcell_manager.redis_handler import WorkcellRedisHandler
from pydantic import AnyUrl


def resolve_workcell_link(workcell_link: WorkcellLink) -> WorkcellDefinition:
    """Resolves the workcell link to a workcell definition"""
    if workcell_link.definition is not None:
        return workcell_link.definition
    if workcell_link.url is not None:
        return WorkcellDefinition.model_validate(
            requests.get(workcell_link.url, timeout=10).json()
        )
    if workcell_link.path is not None:
        return WorkcellDefinition.from_yaml(workcell_link.path)
    return workcell_link.expanduser()


def initialize_workcell(
    state_manager: WorkcellRedisHandler,
    resource_client: ResourceClient,
) -> None:
    """
    Initializes the state of the workcell from the workcell definition.
    """

    workcell = state_manager.get_workcell_definition()
    initialize_workcell_nodes(workcell, state_manager)
    initialize_workcell_resources(workcell, resource_client)
    state_manager.set_workcell_definition(workcell)


def initialize_workcell_nodes(
    workcell: WorkcellDefinition, state_manager: WorkcellRedisHandler
) -> None:
    """create the nodes for the given workcell"""
    for key, value in workcell.nodes.items():
        if type(value) is NodeDefinition:
            node = Node(node_url=value.node_url)
        elif type(value) is AnyUrl or type(value) is str:
            node = Node(node_url=AnyUrl(value))
        state_manager.set_node(key, node)


def initialize_workcell_resources(
    workcell: WorkcellDefinition, resource_client: ResourceClient
) -> None:
    """create the resources for a given workcell definition"""
    for location in workcell.locations:
        if location.resource is not None:
            resource = Resource.discriminate(location.resource)
            resource = resource_client.add_resource(resource)
            location.resource = resource
            with workcell._definition_path.open() as f:
                wc_yaml = yaml.safe_load(f)
            for dict_location in wc_yaml["locations"]:
                if dict_location["location_name"] == location.location_name:
                    dict_location["resource"]["resource_id"] = resource.resource_id
            with workcell._definition_path.open(mode="w") as f:
                yaml.dump(wc_yaml, f, default_flow_style=False)


def find_node_client(url: str) -> AbstractNodeClient:
    """Finds the appropriate node client based on a given node url"""
    for client in NODE_CLIENT_MAP.values():
        if client.validate_url(url):
            return client(url)
    for client in AbstractNodeClient.__subclasses__():
        if client.validate_url(url):
            return client(url)
    return None


def update_active_nodes(state_manager: WorkcellRedisHandler) -> None:
    """Update all active nodes in the workcell."""
    with concurrent.futures.ThreadPoolExecutor() as executor:
        node_futures = []
        for node_name, node in state_manager.get_nodes().items():
            node_future = executor.submit(update_node, node_name, node, state_manager)
            node_futures.append(node_future)

        # Wait for all node updates to complete
        concurrent.futures.wait(node_futures)


def update_node(
    node_name: str, node: Node, state_manager: WorkcellRedisHandler
) -> None:
    """Update a single node's state and about information."""
    try:
        old_status = node.status
        old_info = node.info
        client = find_node_client(node.node_url)
        node.status = client.get_status()
        node.info = client.get_info()
        node.state = client.get_state()
        if old_status != node.status or old_info != node.info:
            with state_manager.wc_state_lock():
                state_manager.set_node(node_name, node)
    except Exception:
        warnings.warn(  # TODO: Replace with event logger
            message=f"Unable to update node {node_name}",
            category=UserWarning,
            stacklevel=1,
        )
