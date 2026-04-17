"""MADSci node client implementations."""

from madsci.client.node.abstract_node_client import AbstractNodeClient
from madsci.client.node.rest_node_client import RestNodeClient

NODE_CLIENT_MAP = {
    "rest_node_client": RestNodeClient,
}

# Conditionally register SiLA client if unitelabs-sila is available
try:
    from madsci.client.node.sila_node_client import SILA2_AVAILABLE, SilaNodeClient

    if SILA2_AVAILABLE:
        NODE_CLIENT_MAP["sila_node_client"] = SilaNodeClient
except ImportError:
    pass


__all__ = [
    "NODE_CLIENT_MAP",
    "AbstractNodeClient",
    "RestNodeClient",
]
