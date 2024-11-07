"""Base module interface and helper classes."""

import inspect
import threading
from typing import Any, Dict, List, Optional

from madsci.common.definition_loaders import module_definition_loader
from madsci.common.types.action_types import (
    ActionDefinition,
    ActionRequest,
    ActionResponse,
    ActionStatus,
)
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.base_types import Error
from madsci.common.types.module_types import (
    AdminCommands,
    ModuleDefinition,
    ModuleInfo,
    ModuleInterfaceCapabilities,
    ModuleSetConfigResponse,
    NodeStatus,
)

MODULE_INTERFACE_MAP = {}  # * Map of module types to module interfaces, add your module interface to this map to if it isn't a subclass of BaseModuleInterface


class BaseModuleInterface:
    """Base Module Interface, protocol agnostic, all module interfaces should inherit from or be based on this."""

    url_protocols: List[str] = []
    """The protocol(s) to use for module URL's using this interface."""

    supported_capabilities: ModuleInterfaceCapabilities = ModuleInterfaceCapabilities()
    """The capabilities supported by this module interface. Note that some capabilities may be supported by the module, but not by the interface (i.e. the 'resources' capability is not implemented at the interface level)."""

    def __init__(self, module: ModuleDefinition):
        """Initialize the module interface."""
        self.module = module

    def send_action(self, name: str, args: None, files: None) -> ActionResponse:
        """Perform an action on the module."""
        raise NotImplementedError(
            "send_action not implemented by this module interface"
        )

    def get_action(self, action_id: str) -> ActionResponse:
        """Get the status of an action on the module."""
        raise NotImplementedError(
            "get_action is not implemented by this module interface"
        )

    def get_status(self) -> NodeStatus:
        """Get the status of the module."""
        raise NotImplementedError(
            "get_status is not implemented by this module interface"
        )

    def get_state(self) -> Dict[str, Any]:
        """Get the state of the module."""
        raise NotImplementedError(
            "get_state is not implemented by this module interface"
        )

    def get_info(self) -> ModuleInfo:
        """Get information about the module."""
        raise NotImplementedError(
            "get_info is not implemented by this module interface"
        )

    def set_config(self, config_key: str, config_value: Any) -> ModuleSetConfigResponse:
        """Set configuration values of the module."""
        raise NotImplementedError(
            "set_config is not implemented by this module interface"
        )

    def send_admin_command(self, admin_command: AdminCommands) -> AdminCommandResponse:
        """Perform an administrative command on the module."""
        raise NotImplementedError(
            "send_admin_command is not implemented by this module interface"
        )


class BaseModule:
    """Base Module implementation, protocol agnostic, all module class definitions should inherit from or be based on this."""

    module_definition: ModuleDefinition = None
    """The module definition."""
    module_info: Optional[ModuleInfo] = None
    """Information about the module."""
    module_status: NodeStatus = NodeStatus(
        initializing=True,
    )
    """The status of the module."""
    action_handlers: Dict[str, callable] = {}
    """The handlers for the actions that the module can perform."""
    admin_command_handlers: Dict[AdminCommands, callable] = {}
    """The handlers for the administrative commands that the module can perform."""
    module_actions: List[ActionDefinition] = []
    """The actions that the module can perform."""
    action_history: Dict[str, List[ActionResponse]] = {}
    """The history of the actions that the module has performed."""
    running_actions: set[str] = set()
    """The IDs of the actions that are currently running on the module."""
    completed_actions: set[str] = set()
    """The IDs of the actions that have completed on the module."""

    def __init__(self):
        """Initialize the module."""
        self.module_definition = module_definition_loader()
        self._lock = threading.Lock()  # Add a lock for thread safety

    def start_module(self):
        """Start the module."""
        pass

    def run_action(self, action_request: ActionRequest) -> ActionResponse:
        """Run an action on the module."""
        self.module_status.running_actions.add(action_request.action_id)
        action_response = self.action_handler(action_request)
        if action_response.status != ActionStatus.RUNNING:
            self.module_status.running_actions.discard(action_request.action_id)
            self.module_status.completed_actions.add(action_request.action_id)
        self.action_history[action_request.action_id].append(action_response)
        return action_response

    def action_handler(self, action_request: ActionRequest) -> ActionResponse:
        """Run an action on the module."""
        action_callable = self.action_handlers.get(
            action_request.action_name, default=None
        )
        if action_callable is None:
            return action_request.failed(
                error=Error(
                    message=f"Action {action_request.action_name} not implemented by this module",
                    error_type="ActionNotImplemented",
                )
            )
        # * Prepare arguments for the action function.
        # * If the action function has a 'state' or 'action' parameter
        # * we'll pass in our state and action objects.
        arg_dict = {}
        parameters = inspect.signature(action_callable).parameters
        if parameters.__contains__("state"):
            arg_dict["state"] = self.state
        if parameters.__contains__("action"):
            arg_dict["action"] = self.action_request
        if list(parameters.values())[-1].kind == inspect.Parameter.VAR_KEYWORD:
            # * Function has **kwargs, so we can pass all action args and files
            arg_dict = {**arg_dict, **action_request.args}
            arg_dict = {
                **arg_dict,
                **{file.filename: file.file for file in action_request.files},
            }
        else:
            for arg_name, arg_value in action_request.args.items():
                if arg_name in parameters.keys():
                    arg_dict[arg_name] = arg_value
            for file in action_request.files:
                if file.filename in parameters.keys():
                    arg_dict[file.filename] = file

        for arg in self.module_actions[action_request.action_name].args:
            if arg.name not in action_request.args:
                if arg.required:
                    return action_request.failed(
                        error=Error(message=f"Missing required argument '{arg.name}'")
                    )
        for file in self.module_actions[action_request.action_name].files:
            if not any(
                arg_file.filename == file.name for arg_file in action_request.files
            ):
                if file.required:
                    return action_request.failed(
                        error=Error(message=f"Missing required file '{file.name}'")
                    )

        if not self.module_status.is_ready[0]:
            return action_request.not_ready(
                error=Error(
                    message=f"Module is not ready: {self.module_status.is_ready[1]}",
                    error_type="ModuleNotReady",
                )
            )

        # * Perform the action here and return result
        with self._lock():
            # * If the action is blocking, set the module status to not ready for the duration of the action, otherwise release the lock immediately
            if action_request.blocking:
                self.module_status.ready = False
                result = action_callable(**arg_dict)
                self.module_status.ready = True
            else:
                self._lock.release()
                result = action_callable(**arg_dict)
        if isinstance(result, ActionResponse):
            result.action_id = (
                action_request.action_id
            )  # * Make sure the action ID is set correctly on the result
            return result
        elif result is None:
            # *Assume success if no return value and no exception
            return action_request.succeeded()
        else:
            # * Return a failure if the action returns something unexpected
            return action_request.failed(
                error=Error(
                    message=f"Action '{action_request.action_name}' returned an unexpected value: {result}"
                )
            )

    def get_action_response(self, action_id: str) -> ActionResponse:
        """Get the status of an action on the module."""
        if action_id in self.action_history:
            return self.action_history[action_id]
        else:
            return ActionResponse(
                status=ActionStatus.FAILED,
                error=Error(
                    message=f"Action with id '{action_id}' not found",
                    error_type="ActionNotFound",
                ),
            )

    def get_status(self) -> NodeStatus:
        """Get the status of the module."""
        return self.module_status

    def set_config(self, config_key: str, config_value: Any) -> ModuleSetConfigResponse:
        """Set configuration values of the module."""
        self.module_definition.module_config[config_key] = config_value
        return ModuleSetConfigResponse(
            success=True,
        )

    def run_admin_command(self, admin_command: AdminCommands) -> AdminCommandResponse:
        """Run the specified administrative command on the module."""
        if admin_command in self.admin_command_handlers:
            try:
                self.admin_command_handlers[admin_command]()
            except Exception as e:
                return AdminCommandResponse(
                    success=False,
                    errors=[Error.from_exception(e)],
                )
        else:
            return AdminCommandResponse(
                success=False,
                errors=[
                    Error(
                        message=f"Admin command {admin_command} not implemented by this module",
                        error_type="AdminCommandNotImplemented",
                    ),
                ],
            )

    def get_info(self) -> ModuleInfo:
        """Get information about the module."""
        return self.module_info

    def get_state(self) -> Dict[str, Any]:
        """Get the state of the module."""
        return {}
