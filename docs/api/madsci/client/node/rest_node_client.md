Module madsci.client.node.rest_node_client
==========================================
REST-based node client implementation.

Classes
-------

`RestNodeClient(url: pydantic.networks.AnyUrl, config: madsci.common.types.client_types.RestNodeClientConfig | None = None)`
:   REST-based node client.

    Initialize the client.

    Args:
        url: The URL of the node to connect to.
        config: Client configuration for retry and timeout settings. If not provided, uses default NodeClientConfig.

    ### Ancestors (in MRO)

    * madsci.client.node.abstract_node_client.AbstractNodeClient

    ### Methods

    `await_action_result(self, action_id: str, timeout: float | None = None, request_timeout: float | None = None) ‑> madsci.common.types.action_types.ActionResult`
    :   Wait for an action to complete and return the result. Optionally, specify a timeout in seconds.

        Args:
            action_id: The ID of the action.
            timeout: Optional timeout in seconds for waiting for the action to complete.
            request_timeout: Optional timeout override for individual HTTP requests. If None, uses config defaults.

    `await_action_result_by_name(self, action_name: str, action_id: str, timeout: float | None = None, request_timeout: float | None = None) ‑> madsci.common.types.action_types.ActionResult`
    :   Wait for an action to complete and return the result. Optionally, specify a timeout in seconds. REST-implementation specific.

        Args:
            action_name: The name of the action.
            action_id: The ID of the action.
            timeout: Optional timeout in seconds for waiting for the action to complete.
            request_timeout: Optional timeout override for individual HTTP requests. If None, uses config defaults.

    `get_action_history(self, action_id: str | None = None, timeout: float | None = None) ‑> dict[str, list[madsci.common.types.action_types.ActionResult]]`
    :   Get the history of a single action performed on the node, or every action, if no action_id is specified.

        Args:
            action_id: Optional action ID to filter by.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_action_result(self, action_id: str, timeout: float | None = None) ‑> madsci.common.types.action_types.ActionResult`
    :   Get the result of an action on the node.

        Note: This method uses the legacy API endpoint and cannot fetch files
        since it lacks the action_name needed for file download URLs.

        Args:
            action_id: The ID of the action.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_action_result_by_name(self, action_name: str, action_id: str, include_files: bool = True, timeout: float | None = None) ‑> madsci.common.types.action_types.ActionResult`
    :   Get the result of an action by name. REST-implementation specific.

        Args:
            action_name: The name of the action.
            action_id: The ID of the action.
            include_files: Whether to include files in the result.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_action_status(self, action_id: str, timeout: float | None = None) ‑> madsci.common.types.action_types.ActionStatus`
    :   Get the status of an action on the node.

        Args:
            action_id: The ID of the action.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_action_status_by_name(self, action_name: str, action_id: str, timeout: float | None = None) ‑> madsci.common.types.action_types.ActionStatus`
    :   Get the status of an action by action name.

        Args:
            action_name: The name of the action.
            action_id: The ID of the action.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_info(self, timeout: float | None = None) ‑> madsci.common.types.node_types.NodeInfo`
    :   Get information about the node.

        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_log(self, timeout: float | None = None) ‑> dict[str, madsci.common.types.event_types.Event]`
    :   Get the log from the node.

        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_state(self, timeout: float | None = None) ‑> dict[str, typing.Any]`
    :   Get the state of the node.

        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_status(self, timeout: float | None = None) ‑> madsci.common.types.node_types.NodeStatus`
    :   Get the status of the node.

        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `send_action(self, action_request: madsci.common.types.action_types.ActionRequest, await_result: bool = True, timeout: float | None = None, request_timeout: float | None = None) ‑> madsci.common.types.action_types.ActionResult`
    :   Perform the action defined by action_request on the specified node.

        Args:
            action_request: The action request to send.
            await_result: Whether to wait for the action to complete.
            timeout: Optional timeout in seconds for waiting for the action to complete.
            request_timeout: Optional timeout override for individual HTTP requests. If None, uses config defaults.

    `send_admin_command(self, admin_command: madsci.common.types.admin_command_types.AdminCommands, timeout: float | None = None) ‑> madsci.common.types.admin_command_types.AdminCommandResponse`
    :   Perform an administrative command on the node.

        Args:
            admin_command: The administrative command to send.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `set_config(self, new_config: dict[str, typing.Any], timeout: float | None = None) ‑> madsci.common.types.node_types.NodeSetConfigResponse`
    :   Update configuration values of the node.

        Args:
            new_config: Dictionary of configuration values to update.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_data_operations.
