"""REST-based node client implementation."""

import tempfile
import time
import traceback
import zipfile
from pathlib import Path
from typing import Any, ClassVar, Optional, Union

from madsci.client.event_client import EventClient
from madsci.client.node.abstract_node_client import (
    AbstractNodeClient,
)
from madsci.common.types.action_types import (
    ActionFiles,
    ActionRequest,
    ActionResult,
    ActionStatus,
    RestActionResult,
)
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.client_types import NodeClientConfig
from madsci.common.types.event_types import Event
from madsci.common.types.node_types import (
    AdminCommands,
    NodeClientCapabilities,
    NodeInfo,
    NodeSetConfigResponse,
    NodeStatus,
)
from madsci.common.types.resource_types import ResourceDataModels
from madsci.common.utils import create_http_session
from pydantic import AnyUrl


def _serialize_for_json(obj: Any) -> Any:
    """
    Recursively serialize Pydantic models and other complex objects for JSON transmission.

    Args:
        obj: The object to serialize

    Returns:
        A JSON-serializable representation of the object
    """
    if hasattr(obj, "model_dump"):
        # This is a Pydantic model - use model_dump(mode="json") for proper serialization
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        # Recursively serialize dictionary values
        return {key: _serialize_for_json(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        # Recursively serialize list/tuple items
        return [_serialize_for_json(item) for item in obj]
    # For primitive types and other objects, return as-is
    return obj


class RestNodeClient(AbstractNodeClient):
    """REST-based node client."""

    url_protocols: ClassVar[list[str]] = ["http", "https"]
    """The protocols supported by this client."""

    supported_capabilities: NodeClientCapabilities = NodeClientCapabilities(
        # *Supported capabilities
        get_info=True,
        get_state=True,
        get_status=True,
        send_action=True,
        get_action_status=True,
        get_action_result=True,
        get_action_history=True,
        action_files=True,
        send_admin_commands=True,
        set_config=True,
        get_log=True,
        # *Unsupported Capabilities
        get_resources=False,
    )

    def __init__(
        self, url: AnyUrl, config: Optional[NodeClientConfig] = None
    ) -> "RestNodeClient":
        """
        Initialize the client.

        Args:
            url: The URL of the node to connect to.
            config: Client configuration for retry and timeout settings. If not provided, uses default NodeClientConfig.
        """
        super().__init__(url)
        self.logger = EventClient()
        self.config = config if config is not None else NodeClientConfig()
        self.session = create_http_session(config=self.config)

    def send_action(
        self,
        action_request: ActionRequest,
        await_result: bool = True,
        timeout: Optional[float] = None,
        request_timeout: Optional[float] = None,
    ) -> ActionResult:
        """
        Perform the action defined by action_request on the specified node.

        Args:
            action_request: The action request to send.
            await_result: Whether to wait for the action to complete.
            timeout: Optional timeout in seconds for waiting for the action to complete.
            request_timeout: Optional timeout override for individual HTTP requests. If None, uses config defaults.
        """
        try:
            # Step 1: Create the action
            action_id = self._create_action(action_request, timeout=request_timeout)

            # Step 2: Upload files if any
            if action_request.files:
                self._upload_action_files(
                    action_request.action_name,
                    action_id,
                    action_request.files,
                    timeout=request_timeout,
                )

            # Step 3: Start the action
            result = self._start_action(
                action_request.action_name, action_id, timeout=request_timeout
            )

            # Step 4: Wait for completion if requested
            if await_result and not result.status.is_terminal:
                result = self.await_action_result_by_name(
                    action_request.action_name,
                    action_id,
                    timeout=timeout,
                    request_timeout=request_timeout,
                )

            return result

        except Exception as e:
            if hasattr(e, "response") and e.response is not None:
                self.logger.error(f"{e.response.status_code}: {e.response.text}")
            else:
                self.logger.error(str(e))
            raise e

    def _create_action(
        self, action_request: ActionRequest, timeout: Optional[float] = None
    ) -> str:
        """
        Create a new action and return the action_id. REST-implementation specific.

        Args:
            action_request: The action request to create.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_data_operations.
        """
        # Convert ActionRequest to RestActionRequest format
        args = dict(action_request.args) if action_request.args else {}

        # Serialize all arguments to ensure Pydantic models are JSON-serializable
        serialized_args = _serialize_for_json(args)
        serialized_var_args = (
            _serialize_for_json(action_request.var_args)
            if action_request.var_args is not None
            else None
        )
        serialized_var_kwargs = (
            _serialize_for_json(action_request.var_kwargs)
            if action_request.var_kwargs is not None
            else None
        )

        request_data = {"args": serialized_args}
        if serialized_var_args is not None:
            request_data["var_args"] = serialized_var_args
        if serialized_var_kwargs is not None:
            request_data["var_kwargs"] = serialized_var_kwargs

        rest_response = self.session.post(
            f"{self.url}/action/{action_request.action_name}",
            json=request_data,
            timeout=timeout or self.config.timeout_data_operations,
        )
        rest_response.raise_for_status()
        response_data = rest_response.json()
        return response_data["action_id"]

    def _upload_action_files(
        self,
        action_name: str,
        action_id: str,
        files: dict[str, Union[str, list[str]]],
        timeout: Optional[float] = None,
    ) -> None:
        """
        Upload files for an action. REST-implementation specific.

        Args:
            action_name: The name of the action.
            action_id: The ID of the action.
            files: Dictionary of file keys to file paths.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_data_operations.
        """
        for file_key, file_value in files.items():
            if isinstance(file_value, list):
                # Handle list[Path] parameters - upload multiple files
                files_to_upload = []
                for file_path in file_value:
                    path = Path(file_path).expanduser()
                    files_to_upload.append(
                        (
                            file_key,
                            (path.name, path.open("rb"), "application/octet-stream"),
                        )
                    )

                try:
                    rest_response = self.session.post(
                        f"{self.url}/action/{action_name}/{action_id}/upload/{file_key}",
                        files=files_to_upload,
                        timeout=timeout or self.config.timeout_data_operations,
                    )
                    rest_response.raise_for_status()
                finally:
                    # Close any opened file handles
                    for _, (_, file_handle, _) in files_to_upload:
                        if hasattr(file_handle, "close"):
                            file_handle.close()
            else:
                # Handle single Path parameters
                with Path(file_value).expanduser().open("rb") as file_handle:
                    rest_response = self.session.post(
                        f"{self.url}/action/{action_name}/{action_id}/upload/{file_key}",
                        files={"file": file_handle},
                        timeout=timeout or self.config.timeout_data_operations,
                    )
                    rest_response.raise_for_status()

    def _start_action(
        self, action_name: str, action_id: str, timeout: Optional[float] = None
    ) -> ActionResult:
        """
        Start an action that has been created. REST-implementation specific.

        Args:
            action_name: The name of the action.
            action_id: The ID of the action.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_data_operations.
        """
        rest_response = self.session.post(
            f"{self.url}/action/{action_name}/{action_id}/start",
            timeout=timeout or self.config.timeout_data_operations,
        )
        rest_response.raise_for_status()
        return self._convert_rest_result_to_action_result(
            rest_response.json(), action_name, action_id, timeout=timeout
        )

    def get_action_status_by_name(
        self, action_name: str, action_id: str, timeout: Optional[float] = None
    ) -> ActionStatus:
        """
        Get the status of an action by action name.

        Args:
            action_name: The name of the action.
            action_id: The ID of the action.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        rest_response = self.session.get(
            f"{self.url}/action/{action_name}/{action_id}/status",
            timeout=timeout or self.config.timeout_default,
        )
        rest_response.raise_for_status()
        return ActionStatus(rest_response.json())

    def _find_file_by_key(self, temp_dir: Path, file_key: str) -> Optional[Path]:
        """Find a file in the temp directory by its key."""
        # Look for file with matching label (with any extension)
        extracted_files = list(temp_dir.glob(f"{file_key}*"))
        if extracted_files:
            return extracted_files[0]

        # Fallback: try exact name
        exact_file = temp_dir / file_key
        if exact_file.exists():
            return exact_file

        # Last fallback: use any available file
        all_files = list(temp_dir.iterdir())
        return all_files[0] if all_files else None

    def _convert_rest_result_to_action_result(
        self,
        rest_result_data: dict,
        action_name: str,
        action_id: str,
        timeout: Optional[float] = None,
    ) -> ActionResult:
        """
        Convert a REST API result (RestActionResult format) to ActionResult format.

        The REST API returns files as a list of strings (file keys), but ActionResult
        expects files to be Path objects or ActionFiles. This method handles the conversion.

        Args:
            rest_result_data: The REST result data.
            action_name: The name of the action.
            action_id: The ID of the action.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_data_operations.
        """
        # First validate as RestActionResult to ensure proper format
        rest_result = RestActionResult.model_validate(rest_result_data)

        # Convert to ActionResult format
        result_data = rest_result.model_dump()

        # Handle files field - fetch actual files if file keys are present
        files_list = result_data.get("files")
        if files_list:
            # Fetch the actual files using the file keys
            try:
                action_files = self._fetch_files_from_keys(
                    action_name, action_id, files_list, timeout=timeout
                )
                result_data["files"] = action_files
            except Exception as e:
                result_data["errors"] = result_data.get("errors", [])
                result_data["errors"].append(
                    f"Error in Client: Failed to fetch files for action {action_name} with ID {action_id}: {e}"
                )
                result_data["files"] = None
        else:
            result_data["files"] = None

        return ActionResult.model_validate(result_data)

    def _fetch_files_from_keys(
        self,
        action_name: str,
        action_id: str,
        file_keys: list[str],
        timeout: Optional[float] = None,
    ) -> Union[Path, ActionFiles, None]:
        """
        Fetch actual files from the server using the provided file keys.

        Args:
            action_name: The name of the action.
            action_id: The ID of the action.
            file_keys: List of file keys to fetch.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_data_operations.
        """
        try:
            # Download the ZIP file containing all files
            zip_path = self._get_action_files_zip(action_id, timeout=timeout)

            # Extract files from ZIP
            with zipfile.ZipFile(zip_path, "r") as zip_file:
                temp_dir = Path(tempfile.mkdtemp())
                zip_file.extractall(temp_dir)

                if len(file_keys) == 1 and file_keys[0] == "file":
                    # Single file case
                    extracted_files = list(temp_dir.iterdir())
                    return extracted_files[0] if extracted_files else None

                # Multiple files case
                downloaded_files = {}
                for file_key in file_keys:
                    file_path = self._find_file_by_key(temp_dir, file_key)
                    if file_path:
                        downloaded_files[file_key] = file_path

                return (
                    ActionFiles.model_validate(downloaded_files)
                    if downloaded_files
                    else None
                )

        except Exception as e:
            self.logger.error(
                f"Failed to fetch files for action {action_name} with ID {action_id}: {traceback.format_exc()}"
            )
            raise e
        finally:
            # Clean up the ZIP file
            if "zip_path" in locals():
                zip_path.unlink(missing_ok=True)

    def get_action_result_by_name(
        self,
        action_name: str,
        action_id: str,
        include_files: bool = True,
        timeout: Optional[float] = None,
    ) -> ActionResult:
        """
        Get the result of an action by name. REST-implementation specific.

        Args:
            action_name: The name of the action.
            action_id: The ID of the action.
            include_files: Whether to include files in the result.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        rest_response = self.session.get(
            f"{self.url}/action/{action_name}/{action_id}/result",
            timeout=timeout or self.config.timeout_default,
        )
        rest_response.raise_for_status()

        # If include_files is False, we can convert directly without fetching files
        if not include_files:
            # Temporarily set files to None in the response data to avoid fetching
            response_data = rest_response.json()
            response_data = response_data.copy()
            response_data["files"] = None
            return self._convert_rest_result_to_action_result(
                response_data, action_name, action_id, timeout=timeout
            )

        return self._convert_rest_result_to_action_result(
            rest_response.json(), action_name, action_id, timeout=timeout
        )

    def _get_action_files_zip(
        self, action_id: str, timeout: Optional[float] = None
    ) -> Path:
        """
        Download all files from an action result as a ZIP. REST-implementation specific.

        Args:
            action_id: Action ID used in the download endpoint
            timeout: Optional timeout override in seconds. If None, uses config.timeout_data_operations.
        """
        rest_response = self.session.get(
            f"{self.url}/action/{action_id}/download",
            timeout=timeout or self.config.timeout_data_operations,
        )
        rest_response.raise_for_status()

        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_file:
            temp_file.write(rest_response.content)
            return Path(temp_file.name)

    def get_action_history(
        self, action_id: Optional[str] = None, timeout: Optional[float] = None
    ) -> dict[str, list[ActionResult]]:
        """
        Get the history of a single action performed on the node, or every action, if no action_id is specified.

        Args:
            action_id: Optional action ID to filter by.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = self.session.get(
            f"{self.url}/action",
            params={"action_id": action_id},
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return response.json()

    def get_action_status(
        self, action_id: str, timeout: Optional[float] = None
    ) -> ActionStatus:
        """
        Get the status of an action on the node.

        Args:
            action_id: The ID of the action.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        rest_response = self.session.get(
            f"{self.url}/action/{action_id}/status",
            timeout=timeout or self.config.timeout_default,
        )
        rest_response.raise_for_status()
        return ActionStatus(rest_response.json())

    def get_action_result(
        self, action_id: str, timeout: Optional[float] = None
    ) -> ActionResult:
        """
        Get the result of an action on the node.

        Note: This method uses the legacy API endpoint and cannot fetch files
        since it lacks the action_name needed for file download URLs.

        Args:
            action_id: The ID of the action.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        rest_response = self.session.get(
            f"{self.url}/action/{action_id}/result",
            timeout=timeout or self.config.timeout_default,
        )
        rest_response.raise_for_status()

        response_data = rest_response.json()
        response_data = response_data.copy()

        # Use dummy values for action_name since files won't be fetched
        return self._convert_rest_result_to_action_result(
            response_data, "action_name", action_id, timeout=timeout
        )

    def await_action_result(
        self,
        action_id: str,
        timeout: Optional[float] = None,
        request_timeout: Optional[float] = None,
    ) -> ActionResult:
        """
        Wait for an action to complete and return the result. Optionally, specify a timeout in seconds.

        Args:
            action_id: The ID of the action.
            timeout: Optional timeout in seconds for waiting for the action to complete.
            request_timeout: Optional timeout override for individual HTTP requests. If None, uses config defaults.
        """
        start_time = time.time()
        interval = 0.25
        while True:
            if timeout is not None and time.time() - start_time > timeout:
                raise TimeoutError("Timed out waiting for action to complete.")
            status = self.get_action_status(action_id, timeout=request_timeout)
            if not status.is_terminal:
                time.sleep(interval)
                interval = (
                    interval * 1.5 if interval < 5 else 5
                )  # * Capped Exponential backoff
                continue
            return self.get_action_result(action_id, timeout=request_timeout)

    def await_action_result_by_name(
        self,
        action_name: str,
        action_id: str,
        timeout: Optional[float] = None,
        request_timeout: Optional[float] = None,
    ) -> ActionResult:
        """
        Wait for an action to complete and return the result. Optionally, specify a timeout in seconds. REST-implementation specific.

        Args:
            action_name: The name of the action.
            action_id: The ID of the action.
            timeout: Optional timeout in seconds for waiting for the action to complete.
            request_timeout: Optional timeout override for individual HTTP requests. If None, uses config defaults.
        """
        start_time = time.time()
        interval = 0.25
        while True:
            if timeout is not None and time.time() - start_time > timeout:
                raise TimeoutError("Timed out waiting for action to complete.")
            status = self.get_action_status_by_name(
                action_name, action_id, timeout=request_timeout
            )
            if not status.is_terminal:
                time.sleep(interval)
                interval = (
                    interval * 1.5 if interval < 5 else 5
                )  # * Capped Exponential backoff
                continue

            # Get the full result with data when the action is complete
            if status == ActionStatus.SUCCEEDED:
                return self.get_action_result_by_name(
                    action_name, action_id, timeout=request_timeout
                )

            # For non-successful terminal states, create a basic ActionResult
            return ActionResult(action_id=action_id, status=status)

    def get_status(self, timeout: Optional[float] = None) -> NodeStatus:
        """
        Get the status of the node.

        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = self.session.get(
            f"{self.url}/status", timeout=timeout or self.config.timeout_default
        )
        response.raise_for_status()
        return NodeStatus.model_validate(response.json())

    def get_state(self, timeout: Optional[float] = None) -> dict[str, Any]:
        """
        Get the state of the node.

        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = self.session.get(
            f"{self.url}/state", timeout=timeout or self.config.timeout_default
        )
        response.raise_for_status()
        return response.json()

    def get_info(self, timeout: Optional[float] = None) -> NodeInfo:
        """
        Get information about the node.

        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = self.session.get(
            f"{self.url}/info", timeout=timeout or self.config.timeout_default
        )
        response.raise_for_status()
        return NodeInfo.model_validate(response.json())

    def set_config(
        self, new_config: dict[str, Any], timeout: Optional[float] = None
    ) -> NodeSetConfigResponse:
        """
        Update configuration values of the node.

        Args:
            new_config: Dictionary of configuration values to update.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_data_operations.
        """
        response = self.session.post(
            f"{self.url}/config",
            json=new_config,
            timeout=timeout or self.config.timeout_data_operations,
        )
        response.raise_for_status()
        return NodeSetConfigResponse.model_validate(response.json())

    def send_admin_command(
        self, admin_command: AdminCommands, timeout: Optional[float] = None
    ) -> AdminCommandResponse:
        """
        Perform an administrative command on the node.

        Args:
            admin_command: The administrative command to send.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = self.session.post(
            f"{self.url}/admin/{admin_command}",
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return AdminCommandResponse.model_validate(response.json())

    def get_resources(self) -> dict[str, ResourceDataModels]:
        """Get the resources of the node."""
        raise NotImplementedError(
            "get_resources is not implemented by this client",
        )
        # TODO: Implement get_resources endpoint

    def get_log(self, timeout: Optional[float] = None) -> dict[str, Event]:
        """
        Get the log from the node.

        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = self.session.get(
            f"{self.url}/log", timeout=timeout or self.config.timeout_default
        )
        response.raise_for_status()
        return response.json()
