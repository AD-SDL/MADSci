"""Base module interface and helper classes."""

import inspect
import threading
import time
from functools import wraps
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
    NodeSetConfigResponse,
    NodeStatus,
)
from madsci.common.utils import pretty_type_repr, threaded_task


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
    action_history: Dict[str, List[ActionResponse]] = {}
    """The history of the actions that the module has performed."""

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
        # * Clear the module actions, we'll rebuild them from the action decorators
        self.module_definition.actions = []
        self._lock = threading.Lock()  # Add a lock for thread safety

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
        for config in self.node_definition.node_config.values():
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
        try:
            action_response = self._action_handler(action_request)
        except Exception as e:
            self._exception_handler(e)
            action_response = action_request.failed(error=Error.from_exception(e))
        else:
            if action_response is None:
                # * Assume success if no return value and no exception
                action_response = action_request.succeeded()
            elif not isinstance(action_response, ActionResponse):
                try:
                    action_response = ActionResponse.model_validate(action_response)
                except ValidationError as e:
                    action_response = action_request.failed(
                        error=Error.from_exception(e)
                    )
        finally:
            self.node_status.running_actions.discard(action_request.action_id)
            self.action_history[action_request.action_id].append(action_response)
        return action_response

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
        return self.node_status

    def set_config(self, new_config: Dict[str, Any]) -> NodeSetConfigResponse:
        """Set configuration values of the module."""
        need_reset = False
        errors = []
        for config_key, config_value in new_config.items():
            try:
                if config_key in self.node_definition.node_config:
                    self.config[config_key] = config_value
                else:
                    raise ValueError(f"Invalid config parameter: {config_key}")
                if self.node_definition.node_config[config_key].reset_on_change:
                    need_reset = True
            except Exception as e:
                errors.append(Error.from_exception(e))
        # *Check if all required parameters are set
        for param in self.node_definition.node_config.values():
            if param.required and (
                param.name not in self.config or self.config[param.name] is None
            ):
                self.node_status.waiting_for_config.add(param.name)
            else:
                self.node_status.waiting_for_config.discard(param.name)
        if need_reset:
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

    def get_info(self) -> NodeDefinition:
        """Get information about the module."""
        node_info = NodeDefinition.model_validate(self.node_definition)
        node_info.module_definition = self.module_definition
        node_info.config_values = self.config
        # * Check for the existence of the admin command in the module
        node_info.module_definition.capabilities.admin_commands = set.union(
            node_info.module_definition.capabilities.admin_commands,
            set(
                [
                    admin_command.value
                    for admin_command in AdminCommands
                    if hasattr(self, admin_command.value)
                    and callable(self.__getattribute__(admin_command.value))
                ]
            ),
        )
        return node_info

    def get_state(self) -> Dict[str, Any]:
        """Get the state of the module."""
        return self.node_state

    """------------------------------------------------------------------------------------------------"""
    """Admin Commands"""
    """------------------------------------------------------------------------------------------------"""

    def reset(self) -> AdminCommandResponse:
        """Reset the module."""
        self.shutdown_handler()
        self.startup_handler(self.config)
        return AdminCommandResponse(
            success=True,
            errors=[],
        )

    def shutdown(self) -> AdminCommandResponse:
        """Shutdown the module."""
        self.shutdown_handler()
        return AdminCommandResponse(
            success=True,
            errors=[],
        )

    """------------------------------------------------------------------------------------------------"""
    """Decorators"""
    """------------------------------------------------------------------------------------------------"""

    def action(
        self,
        action_name: Optional[str] = None,
        description: Optional[str] = None,
        blocking: bool = False,
    ):
        """Decorator to mark a method as an action handler.

        Args:
            action_name: Optional name for the action. If not provided, uses the method name
            description: Optional description of the action. If not provided, uses the docstring of the method
            blocking: Whether this action blocks other actions while running
        """

        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            # *Use provided action_name or function name
            nonlocal action_name, description
            if action_name is None:
                action_name = func.__name__
            # * Use provided description or function docstring
            if description is None:
                description = func.__doc__

            # *Register the action handler
            self.action_handlers[action_name] = wrapper

            # *Add action definition if not already present
            if any(a.name == action_name for a in self.module_definition.actions):
                action_def = next(
                    a for a in self.module_definition.actions if a.name == action_name
                )
            else:
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
                        and parameter_name
                        not in [file.name for file in action_def.files]
                        and parameter_name != "state"
                        and parameter_name != "action"
                        and parameter_name != "return"
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
            self.module_definition.actions.append(action_def)

            return wrapper

        return decorator

    """------------------------------------------------------------------------------------------------"""
    """Internal and Private Methods"""
    """------------------------------------------------------------------------------------------------"""

    def _action_handler(self, action_request: ActionRequest) -> ActionResponse:
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

        for arg in self.module_definition.actions[action_request.action_name].args:
            if arg.name not in action_request.args:
                if arg.required:
                    return action_request.failed(
                        error=Error(message=f"Missing required argument '{arg.name}'")
                    )
        for file in self.module_definition.actions[action_request.action_name].files:
            if not any(
                arg_file.filename == file.name for arg_file in action_request.files
            ):
                if file.required:
                    return action_request.failed(
                        error=Error(message=f"Missing required file '{file.name}'")
                    )

        if not self.node_status.ready[0]:
            return action_request.not_ready(
                error=Error(
                    message=f"Module is not ready: {self.node_status.ready[1]}",
                    error_type="ModuleNotReady",
                )
            )

        # * Perform the action here and return result
        with self._lock():
            # * If the action is marked as blocking, set the module status to not ready for the duration of the action, otherwise release the lock immediately
            if action_request.blocking:
                self.node_status.busy = True
                try:
                    result = action_callable(**arg_dict)
                except Exception as e:
                    self._exception_handler(e)
                    result = action_request.failed(error=Error.from_exception(e))
                finally:
                    self.node_status.busy = False
            else:
                self._lock.release()
                try:
                    result = action_callable(**arg_dict)
                except Exception as e:
                    self._exception_handler(e)
                    result = action_request.failed(error=Error.from_exception(e))
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
                error=Error(
                    message=f"Action '{action_request.action_name}' returned an unexpected value: {result}"
                )
            )

    def _exception_handler(self, e: Exception) -> None:
        """Handle an exception."""
        self.node_status.errored = True
        self.node_status.errors.append(Error.from_exception(e))
        return
