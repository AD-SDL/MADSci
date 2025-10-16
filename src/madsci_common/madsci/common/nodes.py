"""Helpers and utilities for working with MADSci nodes."""

from typing import Optional

from madsci.client.node.abstract_node_client import AbstractNodeClient
from madsci.common.types.node_types import NodeInfo


def check_node_capability(
    node_info: NodeInfo, capability: str, client: Optional[AbstractNodeClient] = None
) -> bool:
    """Check if a node (and/or it's corresponding client) indicates it has a specific capability."""

    node_capability = getattr(node_info.capabilities, capability, None)
    client_capability = (
        getattr(client.supported_capabilities, capability, None) if client else None
    )

    return bool(
        node_capability is True
        or (node_capability is None and client_capability is True)
    )
