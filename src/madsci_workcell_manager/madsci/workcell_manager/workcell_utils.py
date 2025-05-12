"""utility functions for the workcell"""

from madsci.client.node import NODE_CLIENT_MAP, AbstractNodeClient


def find_node_client(url: str) -> AbstractNodeClient:
    """Finds the appropriate node client based on a given node url"""
    for client in NODE_CLIENT_MAP.values():
        if client.validate_url(url):
            return client(url)
    for client in AbstractNodeClient.__subclasses__():
        if client.validate_url(url):
            return client(url)
    return None
