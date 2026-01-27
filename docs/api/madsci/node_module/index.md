Module madsci.node_module
=========================
Package for MADSci Node and Node Module helper classes.

Sub-modules
-----------
* madsci.node_module.abstract_node_module
* madsci.node_module.helpers
* madsci.node_module.rest_node_module
* madsci.node_module.type_analyzer

Functions
---------

`action(*args: Any, **kwargs: Any) ‑> Callable`
:   Decorator to mark a method as an action handler.

    This decorator adds metadata to the decorated function, indicating that it is
    an action handler within the MADSci framework. The metadata includes the action
    name, description, and whether the action is blocking.

    Keyword Args:
        name (str, optional): The name of the action. Defaults to the function name.
        description (str, optional): A description of the action. Defaults to the function docstring.
        blocking (bool, optional): Indicates if the action is blocking. Defaults to False.

    Returns:
        Callable: The decorated function with added metadata.

Classes
-------

`AbstractNode(node_definition: madsci.common.types.node_types.NodeDefinition | None = None, node_config: madsci.common.types.node_types.NodeConfig | None = None)`
:   Base Node implementation, protocol agnostic, all node class definitions should inherit from or be based on this.

    Note that this class is abstract: it is intended to be inherited from, not used directly.

    Initialize the node class.

    ### Ancestors (in MRO)

    * madsci.client.client_mixin.MadsciClientMixin

    ### Descendants

    * madsci.node_module.rest_node_module.RestNode

    ### Class variables

    `REQUIRED_CLIENTS: ClassVar[list[str]]`
    :

    `action_handlers: ClassVar[dict[str, callable]]`
    :   The handlers for the actions that the node supports.

    `action_history: ClassVar[dict[str, list[madsci.common.types.action_types.ActionResult]]]`
    :   The history of the actions that the node has performed.

    `config: ClassVar[madsci.common.types.node_types.NodeConfig]`
    :   The node configuration.

    `config_model: ClassVar[type[madsci.common.types.node_types.NodeConfig]]`
    :   The node config model class. This is the class that will be used to instantiate self.config.

    `logger: ClassVar[madsci.client.event_client.EventClient]`
    :   The event logger for this node

    `module_version: ClassVar[str]`
    :   The version of the module. Should match the version in the node definition.

    `node_definition: ClassVar[madsci.common.types.node_types.NodeDefinition]`
    :   The node definition.

    `node_state: ClassVar[dict[str, Any]]`
    :   The state of the node.

    `node_status: ClassVar[madsci.common.types.node_types.NodeStatus]`
    :   The status of the node.

    `supported_capabilities: ClassVar[madsci.common.types.node_types.NodeClientCapabilities]`
    :   The default supported capabilities of this node module class.

    ### Methods

    `create_and_upload_file_datapoint(self, file_path: str | pathlib.Path, label: str | None = None) ‑> str`
    :   Create a FileDataPoint and upload it to the data manager.

        Args:
            file_path: Path to the file to store
            label: Optional label for the datapoint

        Returns:
            The ULID string ID of the uploaded datapoint

    `create_and_upload_value_datapoint(self, value: Any, label: str | None = None) ‑> str`
    :   Create a ValueDataPoint and upload it to the data manager.

        Args:
            value: JSON-serializable value to store
            label: Optional label for the datapoint

        Returns:
            The ULID string ID of the uploaded datapoint

    `get_action_history(self, action_id: str | None = None) ‑> dict[str, list[madsci.common.types.action_types.ActionResult]]`
    :   Get the action history for the node or a specific action run.

    `get_action_result(self, action_id: str) ‑> madsci.common.types.action_types.ActionResult`
    :   Get the most up-to-date result of an action on the node.

    `get_action_status(self, action_id: str) ‑> madsci.common.types.action_types.ActionStatus`
    :   Get the status of an action on the node.

    `get_info(self) ‑> madsci.common.types.node_types.NodeInfo`
    :   Get information about the node.

    `get_log(self) ‑> dict[str, madsci.common.types.event_types.Event]`
    :   Return the log of the node

    `get_state(self) ‑> dict[str, typing.Any]`
    :   Get the state of the node.

    `get_status(self) ‑> madsci.common.types.node_types.NodeStatus`
    :   Get the status of the node.

    `lock(self) ‑> bool`
    :   Admin command to lock the node.

    `run_action(self, action_request: madsci.common.types.action_types.ActionRequest) ‑> madsci.common.types.action_types.ActionResult`
    :   Run an action on the node.

    `run_admin_command(self, admin_command: madsci.common.types.admin_command_types.AdminCommands) ‑> madsci.common.types.admin_command_types.AdminCommandResponse`
    :   Run the specified administrative command on the node.

    `set_config(self, new_config: dict[str, typing.Any]) ‑> madsci.common.types.node_types.NodeSetConfigResponse`
    :   Set configuration values of the node.

    `shutdown_handler(self) ‑> None`
    :   Called to shut down the node. Should be used to clean up any resources.

    `start_node(self) ‑> None`
    :   Called once to start the node.

    `startup_handler(self) ‑> None`
    :   Called to (re)initialize the node. Should be used to open connections to devices or initialize any other resources.

    `state_handler(self) ‑> None`
    :   Called periodically to update the node state. Should set `self.node_state`

    `status_handler(self) ‑> None`
    :   Called periodically to update the node status. Should set `self.node_status`

    `unlock(self) ‑> bool`
    :   Admin command to unlock the node.

    `upload_datapoint(self, datapoint: madsci.common.types.datapoint_types.DataPoint) ‑> str`
    :   Upload a datapoint to the data manager and return its ID.

        Args:
            datapoint: DataPoint object to upload

        Returns:
            The ULID string ID of the uploaded datapoint

        Raises:
            Exception: If upload fails

    `upload_datapoints(self, datapoints: list[madsci.common.types.datapoint_types.DataPoint]) ‑> list[str]`
    :   Upload multiple datapoints to the data manager and return their IDs.

        Args:
            datapoints: List of DataPoint objects to upload

        Returns:
            List of ULID string IDs of the uploaded datapoints

        Raises:
            Exception: If any upload fails

`RestNode(*args: Any, **kwargs: Any)`
:   REST-based node implementation with better OpenAPI documentation and result handling.

    Initialize the node class.

    ### Ancestors (in MRO)

    * madsci.node_module.abstract_node_module.AbstractNode
    * madsci.client.client_mixin.MadsciClientMixin

    ### Descendants

    * madsci.experiment_application.experiment_application.ExperimentApplication

    ### Class variables

    `rest_api`
    :   The REST API server for the node.

    ### Methods

    `create_action(self, action_name: str, request_data: dict[str, typing.Any]) ‑> dict[str, str]`
    :   Create a new action and return the action_id.

    `get_action_files_zip(self, _action_name: str, action_id: str) ‑> starlette.responses.FileResponse`
    :   Get all files from an action as a ZIP file.

    `get_action_files_zip_by_id(self, action_id: str) ‑> starlette.responses.FileResponse`
    :   Get all files from an action as a ZIP file using only action_id.

    `get_action_history(self, action_id: str | None = None) ‑> dict[str, list[madsci.common.types.action_types.ActionResult]]`
    :   Get the action history of the node, or of a specific action.

    `get_action_result(self, action_id: str) ‑> madsci.common.types.action_types.ActionResult`
    :   Get the result of an action on the node.

    `get_action_result_dict(self, action_id: str) ‑> dict[str, typing.Any]`
    :   Get the result of an action on the node as a dictionary for API responses.

    `get_log(self) ‑> dict[str, madsci.common.types.event_types.Event]`
    :   Get the log of the node

    `reset(self) ‑> madsci.common.types.admin_command_types.AdminCommandResponse`
    :   Restart the node.

    `run_admin_command(self, admin_command: madsci.common.types.admin_command_types.AdminCommands) ‑> madsci.common.types.admin_command_types.AdminCommandResponse`
    :   Perform an administrative command on the node.

    `shutdown(self, background_tasks: fastapi.background.BackgroundTasks) ‑> madsci.common.types.admin_command_types.AdminCommandResponse`
    :   Shutdown the node.

    `start_action(self, _action_name: str, action_id: str) ‑> dict[str, typing.Any]`
    :   Start an action after all files have been uploaded.

    `start_node(self, testing: bool = False) ‑> None`
    :   Start the node.

    `upload_action_file(self, _action_name: str, action_id: str, file_arg: str, file: fastapi.datastructures.UploadFile) ‑> dict[str, str]`
    :   Upload a single file for a specific action.

    `upload_action_files(self, _action_name: str, action_id: str, file_arg: str, files: list[fastapi.datastructures.UploadFile]) ‑> dict[str, str]`
    :   Upload multiple files for a specific action (for list[Path] parameters).
