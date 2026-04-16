Module madsci.client.node.sila_node_client
==========================================
SiLA2-based node client implementation.

Connects to SiLA2 servers via gRPC using the sila2 Python SDK.
Requires the 'sila' optional dependency: pip install "madsci.client[sila]"

Classes
-------

`SilaNodeClient(url: pydantic.networks.AnyUrl, config: ForwardRef('SilaNodeClientConfig') | None = None, event_client: madsci.client.event_client.EventClient | None = None)`
:   SiLA2 gRPC-based node client.
    
    Connects to SiLA2 servers using the sila2 Python SDK. Supports both
    unobservable (synchronous) and observable (long-running) SiLA commands.
    
    URL scheme: sila://host:port
    
    Requires the 'sila' optional dependency:
        pip install "madsci.client[sila]"
    
    Initialize the SiLA node client.
    
    Args:
        url: A sila://host:port URL.
        config: Optional SiLA-specific client configuration.
        event_client: Optional event client for structured logging.
    
    Raises:
        ImportError: If the sila2 package is not installed.

    ### Ancestors (in MRO)

    * madsci.client.node.abstract_node_client.AbstractNodeClient

    ### Static methods

    `validate_url(url: pydantic.networks.AnyUrl) ‑> bool`
    :   Check if a url uses the sila:// scheme.

    ### Methods

    `await_action_result(self, action_id: str, timeout: float | None = None) ‑> madsci.common.types.action_types.ActionResult`
    :   Wait for an observable SiLA command to complete.

    `close(self) ‑> None`
    :   Close the SiLA client connection.

    `get_action_result(self, action_id: str) ‑> madsci.common.types.action_types.ActionResult`
    :   Get the result of an observable SiLA command.

    `get_action_status(self, action_id: str) ‑> madsci.common.types.action_types.ActionStatus`
    :   Get the status of an observable SiLA command.

    `get_info(self) ‑> madsci.common.types.node_types.NodeInfo`
    :   Get information about the SiLA node.
        
        Introspects the SiLA server's features and commands to build
        ActionDefinition objects.

    `get_state(self) ‑> dict[str, typing.Any]`
    :   Get the state of the SiLA node by reading all property values.
        
        Returns a dict mapping "FeatureName.PropertyName" to its current value.

    `get_status(self) ‑> madsci.common.types.node_types.NodeStatus`
    :   Get the status of the SiLA node.

    `send_action(self, action_request: madsci.common.types.action_types.ActionRequest, await_result: bool = True, timeout: float | None = None) ‑> madsci.common.types.action_types.ActionResult`
    :   Execute a SiLA command.
        
        Args:
            action_request: Action to perform. action_name should be either
                "FeatureName.CommandName" or just "CommandName" (if unambiguous).
                args are passed as keyword arguments to the SiLA command.
            await_result: If True, block until the command completes.
            timeout: Timeout in seconds. Defaults to config.command_timeout.