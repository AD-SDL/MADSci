Module madsci.client.node.abstract_node_client
==============================================
Base node client implementation.

Classes
-------

`AbstractNodeClient(url: pydantic.networks.AnyUrl)`
:   Base Node Client, protocol agnostic, all node clients should inherit from or be based on this.

    Initialize the client.

    ### Descendants

    * madsci.client.node.rest_node_client.RestNodeClient

    ### Class variables

    `supported_capabilities: ClassVar[madsci.common.types.node_types.NodeClientCapabilities]`
    :   The capabilities supported by this node client.

    `url_protocols: ClassVar[list[str]]`
    :   The protocol(s) to use for node URL's using this client.

    ### Static methods

    `validate_url(url: pydantic.networks.AnyUrl) ‑> bool`
    :   check if a url matches this node type

    ### Methods

    `await_action_result(self, action_id: str, timeout: float | None = None) ‑> madsci.common.types.action_types.ActionResult`
    :   Wait for an action to complete and return the result. Optionally, specify a timeout in seconds.

    `get_action_history(self) ‑> dict[str, list[madsci.common.types.action_types.ActionResult]]`
    :   Get the history of a specific action, or all actions run by the node.

    `get_action_result(self, action_id: str) ‑> madsci.common.types.action_types.ActionResult`
    :   Get the result of an action on the node.

    `get_action_status(self, action_id: str) ‑> madsci.common.types.action_types.ActionStatus`
    :   Get the status of an action on the node.

    `get_info(self) ‑> madsci.common.types.node_types.NodeInfo`
    :   Get information about the node.

    `get_log(self) ‑> dict[str, madsci.common.types.event_types.Event]`
    :   Get the log of the node.

    `get_resources(self) ‑> dict[str, madsci.common.types.resource_types.Resource | madsci.common.types.resource_types.Asset | madsci.common.types.resource_types.Consumable | madsci.common.types.resource_types.DiscreteConsumable | madsci.common.types.resource_types.ContinuousConsumable | madsci.common.types.resource_types.Container | madsci.common.types.resource_types.Collection | madsci.common.types.resource_types.Row | madsci.common.types.resource_types.Grid | madsci.common.types.resource_types.VoxelGrid | madsci.common.types.resource_types.Stack | madsci.common.types.resource_types.Queue | madsci.common.types.resource_types.Pool | madsci.common.types.resource_types.Slot]`
    :   Get the resources of the node.

    `get_state(self) ‑> dict[str, typing.Any]`
    :   Get the state of the node.

    `get_status(self) ‑> madsci.common.types.node_types.NodeStatus`
    :   Get the status of the node.

    `send_action(self, action_request: madsci.common.types.action_types.ActionRequest, await_result: bool = True, timeout: float | None = None) ‑> madsci.common.types.action_types.ActionResult`
    :   Perform an action on the node.

    `send_admin_command(self, admin_command: madsci.common.types.admin_command_types.AdminCommands) ‑> madsci.common.types.admin_command_types.AdminCommandResponse`
    :   Perform an administrative command on the node.

    `set_config(self, config_dict: dict[str, typing.Any]) ‑> madsci.common.types.node_types.NodeSetConfigResponse`
    :   Set configuration values of the node.
