"""utility functions for the workcell"""

from typing import Optional

from madsci.client.event_client import EventClient
from madsci.client.node import NODE_CLIENT_MAP, AbstractNodeClient


def find_node_client(
    url: str, event_client: Optional[EventClient] = None
) -> AbstractNodeClient:
    """Finds the appropriate node client based on a given node url"""
    kwargs = {"event_client": event_client} if event_client else {}
    for client_cls in NODE_CLIENT_MAP.values():
        if client_cls.validate_url(url):
            return client_cls(url, **kwargs)
    for client_cls in AbstractNodeClient.__subclasses__():
        if client_cls.validate_url(url):
            return client_cls(url, **kwargs)
    return None
