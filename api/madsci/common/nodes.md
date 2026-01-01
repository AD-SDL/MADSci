Module madsci.common.nodes
==========================
Helpers and utilities for working with MADSci nodes.

Functions
---------

`check_node_capability(node_info: madsci.common.types.node_types.NodeInfo, capability: str, client: madsci.client.node.abstract_node_client.AbstractNodeClient | None = None) ‑> bool`
:   Check if a node (and/or it's corresponding client) indicates it has a specific capability.
