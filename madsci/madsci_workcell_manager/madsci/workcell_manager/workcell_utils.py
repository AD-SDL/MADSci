from redis_handler import WorkcellRedisHandler
from pydantic import AnyUrl
from madsci.common.types.workcell_types import WorkcellDefinition
from madsci.common.types.node_types import NodeStatus, Node, NodeDefinition
from madsci.client.node import AbstractNodeClient, NODE_CLIENT_MAP

def initialize_state(state_manager: WorkcellRedisHandler, workcell=None) -> None:
    """
    Initializes the state of the workcell from the workcell definition.
    """

    if not workcell:
        workcell = state_manager.get_workcell()
    initialize_workcell_nodes(workcell)
    initialize_workcell_resources(workcell)

def initialize_workcell_nodes(workcell):
    for value in workcell.nodes.values():
        if type(value) is NodeDefinition:
            url = value.url
        elif type(value) is AnyUrl:
            url = value
        elif type(value) is str:
            url = AnyUrl(value)
        update_node_info(url, workcell)
        update_node_status(url, workcell)


def initialize_workcell_resources(workcell):
    pass

def update_node_info(url: AnyUrl, workcell: WorkcellDefinition):
    client = find_node_client(url)
    print(client.get_info())

def update_node_status(url: AnyUrl, workcell: WorkcellDefinition):
    client = find_node_client(url)
    print(client.get_status())

def find_node_client(url: str) -> AbstractNodeClient:
    """finds the right client for the node url provided"""
    for client in NODE_CLIENT_MAP.values():
        if client.validate_url(url):
            return client(url)
    for client in AbstractNodeClient.__subclasses__():
        if client.validate_url(url):
            return client(url)
    return None
