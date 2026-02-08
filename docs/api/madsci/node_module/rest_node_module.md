Module madsci.node_module.rest_node_module
==========================================
REST-based Node Module helper classes.

Classes
-------

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
