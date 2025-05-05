"""utility functions for the workcell"""

import concurrent

from madsci.common.types.base_types import Error
from madsci.client.node import NODE_CLIENT_MAP, AbstractNodeClient
from madsci.common.types.node_types import Node, NodeStatus
from madsci.workcell_manager.state_handler import WorkcellStateHandler



def find_node_client(url: str) -> AbstractNodeClient:
    """Finds the appropriate node client based on a given node url"""
    for client in NODE_CLIENT_MAP.values():
        if client.validate_url(url):
            return client(url)
    for client in AbstractNodeClient.__subclasses__():
        if client.validate_url(url):
            return client(url)
    return None



