"""Base module interface and helper classes."""

import inspect
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, get_type_hints

from pydantic import ValidationError
from rich import print

from madsci.common.definition_loaders import (
    node_definition_loader,
)
from madsci.common.types.action_types import (
    ActionArgumentDefinition,
    ActionDefinition,
    ActionFileDefinition,
    ActionRequest,
    ActionResponse,
    ActionStatus,
)
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.base_types import Error
from madsci.common.types.module_types import (
    AdminCommands,
    ModuleDefinition,
)
from madsci.common.types.node_types import (
    NodeDefinition,
    NodeInfo,
    NodeSetConfigResponse,
    NodeStatus,
)
from madsci.common.utils import pretty_type_repr, threaded_daemon, threaded_task


def action(
    func: Callable,
    name: Optional[str] = None,
    description: Optional[str] = None,
    blocking: bool = False,
):
    """Decorator to mark a method as an action handler."""
    func.__is_madsci_action__ = True

    # *Use provided action_name or function name
    if name is None:
        name = func.__name__
    # * Use provided description or function docstring
    if description is None:
        description = func.__doc__
    func.__madsci_action_name__ = name
    func.__madsci_action_description__ = description
    func.__madsci_action_blocking__ = blocking
    return func


class AbstractModule:
    """
    Base Module implementation, protocol agnostic, all module class definitions should inherit from or be based on this.

    Note that this class is abstract: it is intended to be inherited from, not used directly.
    """

    module_definition: ModuleDefinition = None
    """The module definition."""
    node_definition: NodeDefinition = None
    """The node definition."""
    config: Dict[str, Any] = {}
    """The configuration of the module."""
    node_status: NodeStatus = NodeStatus(
        initializing=True,
    )
    """The status of the module."""
    node_state: Dict[str, Any] = {}
    """The state of the module."""
    action_handlers: Dict[str, callable] = {}
    """The handlers for the actions that the module can perform."""
    action_history: Dict[str, ActionResponse] = {}
    """The history of the actions that the module has performed."""
    status_update_interval: float = 5.0
    """The interval at which the status handler is called. Overridable by config."""
    state_update_interval: float = 5.0
    """The interval at which the state handler is called. Overridable by config."""
    node_info_path: Optional[Path] = None
    """The path to the node info file. If unset, defaults to '<node_definition_path>.info.yaml'"""

    def __init__(self):
        """Initialize the module class."""
        (self.node_definition, self.module_definition, self.config) = (
            node_definition_loader()
        )
        assert (
            self.node_definition is not None
        ), "Node definition not found, aborting node initialization"
        assert (
            self.module_definition is not None
        ), "Module definition not found, aborting node initialization"

        # * Synthesize the node info
        self.node_info = NodeInfo.from_node_and_module(
            self.node_definition, self.module_definition, self.config
        )

        # * Add the admin commands to the node info
        self.node_info.capabilities.admin_commands = set.union(
            self.node_info.capabilities.admin_commands,
            set(
                [
                    admin_command.value
                    for admin_command in AdminCommands
                    if hasattr(self, admin_command.value)
                    and callable(self.__getattribute__(admin_command.value))
                ]
            ),
        )
        # * Add the action decorators to the node
        for action_callable in self.__class__.__dict__.values():
            if hasattr(action_callable, "__is_madsci_action__"):
                self._add_action(
                    func=action_callable,
                    action_name=action_callable.__madsci_action_name__,
                    description=action_callable.__madsci_action_description__,
                    blocking=action_callable.__madsci_action_blocking__,
                )

        # * Save the node info
        if self.node_info_path:
            self.node_info.to_yaml(self.node_info_path)
        else:
            if self.node_definition._definition_path:
                self.node_info_path = Path(
                    self.node_definition._definition_path
                ).with_suffix(".info.yaml")
                self.node_info.to_yaml(self.node_info_path, exclude={"config_values"})

        # * Add a lock for thread safety with blocking actions
        self._action_lock = threading.Lock()

    """------------------------------------------------------------------------------------------------"""
    """Node Lifecycle and Public Methods"""
    """------------------------------------------------------------------------------------------------"""

    def start_node(self, config: Dict[str, Any] = {}):
        """Called once to start the node."""
        if self.module_definition._definition_path:
            self.module_definition.to_yaml(self.module_definition._definition_path)
        else:
            print(
                "No definition path set for module, skipping module definition update"
            )
        if self.node_definition._definition_path:
            self.node_definition.to_yaml(self.node_definition._definition_path)
        else:
            print("No definition path set for node, skipping node definition update")

        # *Check for any required config parameters that weren't set
        self.config = {**self.config, **config}
        for config in self.node_definition.config.values():
            if (
                config.required
                and (config.name not in self.config or self.config[config.name] is None)
                and config.default is None
            ):
                print(f"Required config parameter '{config.name}' not set")
                self.node_status.waiting_for_config.add(config.name)
            else:
                self.node_status.waiting_for_config.discard(config.name)

    def status_handler(self):
        """Called periodically to update the node status."""
        pass

    def state_handler(self):
        """Called periodically to update the node state."""
        pass

    def startup_handler(self):
        """Called to (re)initialize the node. Should be used to open connections to devices or initialize any other resources."""
        pass

    def shutdown_handler(self):
        """Called to shut down the node. Should be used to clean up any resources."""
        pass

    """------------------------------------------------------------------------------------------------"""
    """Interface Methods"""
    """------------------------------------------------------------------------------------------------"""

    def get_action_history(self) -> List[str]:
        """Get the action history of the module."""
        return list(self.action_history.keys())

    def run_action(self, action_request: ActionRequest) -> ActionResponse:
        """Run an action on the module."""
        self.node_status.running_actions.add(action_request.action_id)
        action_response = None
        try:
            action_response = self._action_handler(action_request)
        except Exception as e:
            self._exception_handler(e)
            action_response = action_request.failed(errors=Error.from_exception(e))
        else:
            if action_response is None:
                # * Assume success if no return value and no exception
                action_response = action_request.succeeded()
            elif not isinstance(action_response, ActionResponse):
                try:
                    action_response = ActionResponse.model_validate(action_response)
                except ValidationError as e:
                    action_response = action_request.failed(
                        errors=Error.from_exception(e)
                    )
        finally:
            self.node_status.running_actions.discard(action_request.action_id)
            self.action_history[action_request.action_id] = action_response
        return action_response

    def get_action(self, action_id: str) -> ActionResponse:
        """Get the status of an action on the module."""
        if action_id in self.action_history:
            return self.action_history[action_id]
        else:
            return ActionResponse(
                status=ActionStatus.FAILED,
                errors=Error(
                    message=f"Action with id '{action_id}' not found",
                    error_type="ActionNotFound",
                ),
            )

    def get_status(self) -> NodeStatus:
        """Get the status of the module."""
        return self.node_status

    def set_config(self, new_config: Dict[str, Any]) -> NodeSetConfigResponse:
        """Set configuration values of the module."""
        need_reset = False
        errors = []
        for config_key, config_value in new_config.items():
            try:
                if config_key in self.node_definition.config:
                    self.config[config_key] = config_value
                else:
                    raise ValueError(f"Invalid config parameter: {config_key}")
                if self.node_definition.config[config_key].reset_on_change:
                    need_reset = True
            except Exception as e:
                errors.append(Error.from_exception(e))
        # *Check if all required parameters are set
        for param in self.node_definition.config.values():
            if param.required and (
                param.name not in self.config or self.config[param.name] is None
            ):
                self.node_status.waiting_for_config.add(param.name)
            else:
                self.node_status.waiting_for_config.discard(param.name)
        if need_reset and hasattr(self, "reset"):
            # * Reset after a short delay to allow the response to be returned
            @threaded_task
            def schedule_reset():
                time.sleep(2)
                self.reset()

            schedule_reset()
        return NodeSetConfigResponse(
            success=len(errors) == 0,
            errors=errors,
        )

    def run_admin_command(self, admin_command: AdminCommands) -> AdminCommandResponse:
        """Run the specified administrative command on the module."""
        if self.hasattr(admin_command) and callable(
            self.__getattribute__(admin_command)
        ):
            try:
                response = self.__getattribute__(admin_command)()
                if response is None:
                    # * Assume success if no return value
                    response = True
                    return AdminCommandResponse(
                        success=True,
                        errors=[],
                    )
                if isinstance(response, bool):
                    return AdminCommandResponse(
                        success=response,
                        errors=[],
                    )
                if isinstance(response, AdminCommandResponse):
                    return response
                raise ValueError(
                    f"Admin command {admin_command} returned an unexpected value: {response}"
                )
            except Exception as e:
                self._exception_handler(e)
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

    def get_info(self) -> NodeInfo:
        """Get information about the module."""
        return self.node_info

    def get_state(self) -> Dict[str, Any]:
        """Get the state of the module."""
        return self.node_state

    """------------------------------------------------------------------------------------------------"""
    """Internal and Private Methods"""
    """------------------------------------------------------------------------------------------------"""

    def _add_action(
        self, func: Callable, action_name: str, description: str, blocking: bool = False
    ):
        """Add an action to the module.

        Args:
            func: The function to add as an action handler
            action_name: The name of the action
            description: The description of the action
            blocking: Whether this action blocks other actions while running
        """
        # *Register the action handler
        self.action_handlers[action_name] = func

        action_def = ActionDefinition(
            name=action_name,
            description=description,
            blocking=blocking,
            args=[],
            files=[],
        )
        # *Create basic action definition from function signature
        signature = inspect.signature(func)
        if signature.parameters:
            for parameter_name, parameter_type in get_type_hints(
                func, include_extras=True
            ).items():
                if (
                    parameter_name not in action_def.args
                    and parameter_name not in [file.name for file in action_def.files]
                    and parameter_name != "action"
                ):
                    type_hint = parameter_type
                    description = ""
                    annotated_as_file = False
                    annotated_as_arg = False
                    # * If the type hint is an Annotated type, extract the type and description
                    # * Description here means the first string metadata in the Annotated type
                    if type_hint.__name__ == "Annotated":
                        type_hint = get_type_hints(func, include_extras=False)[
                            parameter_name
                        ]
                        description = next(
                            (
                                metadata
                                for metadata in parameter_type.__metadata__
                                if isinstance(metadata, str)
                            ),
                            "",
                        )
                        annotated_as_file = any(
                            isinstance(metadata, ActionFileDefinition)
                            for metadata in parameter_type.__metadata__
                        )
                        annotated_as_arg = not any(
                            isinstance(metadata, ActionArgumentDefinition)
                            for metadata in parameter_type.__metadata__
                        )
                        if annotated_as_file and annotated_as_arg:
                            raise ValueError(
                                f"Parameter '{parameter_name}' is annotated as both a file and an argument. This is not allowed."
                            )
                    if annotated_as_file or (
                        type_hint.__name__
                        in ["Path", "PurePath", "PosixPath", "WindowsPath"]
                        and not annotated_as_arg
                    ):
                        # * Add a file parameter to the action
                        action_def.files[parameter_name] = ActionFileDefinition(
                            name=parameter_name,
                            required=True,
                            description=description,
                        )
                    else:
                        parameter_info = signature.parameters[parameter_name]
                        # * Add an arg to the action
                        default = (
                            None
                            if parameter_info.default == inspect.Parameter.empty
                            else parameter_info.default
                        )

                        action_def.args[parameter_name] = ActionArgumentDefinition(
                            name=parameter_name,
                            type=pretty_type_repr(type_hint),
                            default=default,
                            required=True if default is None else False,
                            description=description,
                        )
        self.node_info.actions[action_name] = action_def

    def _action_handler(self, action_request: ActionRequest) -> ActionResponse:
        """Run an action on the module."""
        action_callable = self.action_handlers.get(action_request.action_name, None)
        if action_callable is None:
            return action_request.failed(
                errors=Error(
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
        if parameters.__contains__("self"):
            arg_dict["self"] = self
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

        for arg in self.node_info.actions[action_request.action_name].args.values():
            if arg.name not in action_request.args:
                if arg.required:
                    return action_request.failed(
                        errors=Error(message=f"Missing required argument '{arg.name}'")
                    )
        for file in self.node_info.actions[action_request.action_name].files.values():
            if not any(
                arg_file.filename == file.name for arg_file in action_request.files
            ):
                if file.required:
                    return action_request.failed(
                        errors=Error(message=f"Missing required file '{file.name}'")
                    )

        if not self.node_status.ready:
            return action_request.not_ready(
                error=Error(
                    message=f"Module is not ready: {self.node_status.description}",
                    error_type="ModuleNotReady",
                )
            )

        # * Perform the action here and return result
        self._action_lock.acquire()
        try:
            # * If the action is marked as blocking, set the module status to not ready for the duration of the action, otherwise release the lock immediately
            if self.node_info.actions[action_request.action_name].blocking:
                self.node_status.busy = True
                try:
                    result = action_callable(**arg_dict)
                except Exception as e:
                    self._exception_handler(e)
                    result = action_request.failed(errors=Error.from_exception(e))
                finally:
                    self.node_status.busy = False
            else:
                if self._action_lock.locked():
                    self._action_lock.release()
                try:
                    result = action_callable(**arg_dict)
                except Exception as e:
                    self._exception_handler(e)
                    result = action_request.failed(errors=Error.from_exception(e))
        finally:
            if self._action_lock.locked():
                self._action_lock.release()
        if isinstance(result, ActionResponse):
            # * Make sure the action ID is set correctly on the result
            result.action_id = action_request.action_id
            return result
        elif result is None:
            # *Assume success if no return value and no exception
            return action_request.succeeded()
        else:
            # * Return a failure if the action returns something unexpected
            return action_request.failed(
                errors=Error(
                    message=f"Action '{action_request.action_name}' returned an unexpected value: {result}"
                )
            )

    def _exception_handler(self, e: Exception) -> None:
        """Handle an exception."""
        self.node_status.errored = True
        self.node_status.errors.append(Error.from_exception(e))
        traceback.print_exc()
        return

    @threaded_daemon
    def _loop_handler(self):
        """Handles calling periodic handlers, like the status and state handlers"""
        last_status_update = 0.0
        last_state_update = 0.0
        while True:
            try:
                status_update_interval = self.config.get(
                    "status_update_interval", self.status_update_interval
                )
                if time.time() - last_status_update > status_update_interval:
                    last_status_update = time.time()
                    self.status_handler()
                state_update_interval = self.config.get(
                    "state_update_interval", self.state_update_interval
                )
                if time.time() - last_state_update > state_update_interval:
                    last_state_update = time.time()
                    self.state_handler()
                time.sleep(0.1)
            except Exception as e:
                self._exception_handler(e)
                time.sleep(0.1)
