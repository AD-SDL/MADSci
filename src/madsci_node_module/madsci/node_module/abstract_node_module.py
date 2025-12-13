"""Base Node Module helper classes."""

import contextlib
import inspect
import threading
import traceback
from pathlib import Path
from typing import (
    Annotated,
    Any,
    Callable,
    ClassVar,
    Optional,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from madsci.client.client_mixin import MadsciClientMixin
from madsci.client.event_client import (
    EventClient,
)
from madsci.client.node.abstract_node_client import AbstractNodeClient
from madsci.common.exceptions import (
    ActionNotImplementedError,
)
from madsci.common.ownership import global_ownership_info
from madsci.common.types.action_types import (
    ActionDatapoints,
    ActionDefinition,
    ActionFiles,
    ActionJSON,
    ActionRequest,
    ActionResult,
    ActionStatus,
    ArgumentDefinition,
    FileArgumentDefinition,
    LocationArgumentDefinition,
)
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.base_types import Error
from madsci.common.types.datapoint_types import DataPoint, FileDataPoint, ValueDataPoint
from madsci.common.types.event_types import Event, EventType
from madsci.common.types.node_types import (
    AdminCommands,
    NodeCapabilities,
    NodeClientCapabilities,
    NodeConfig,
    NodeDefinition,
    NodeInfo,
    NodeSetConfigResponse,
    NodeStatus,
)
from madsci.common.utils import (
    pretty_type_repr,
    repeat_on_interval,
    threaded_daemon,
    to_snake_case,
)
from madsci.node_module.type_analyzer import analyze_type
from pydantic import BaseModel, ValidationError
from semver import Version


class AbstractNode(MadsciClientMixin):
    """
    Base Node implementation, protocol agnostic, all node class definitions should inherit from or be based on this.

    Note that this class is abstract: it is intended to be inherited from, not used directly.
    """

    # Client configuration for MadsciClientMixin
    REQUIRED_CLIENTS: ClassVar[list[str]] = ["event", "resource", "data"]

    node_definition: ClassVar[NodeDefinition] = None
    """The node definition."""
    node_status: ClassVar[NodeStatus] = NodeStatus(
        initializing=True,
    )
    """The status of the node."""
    node_state: ClassVar[dict[str, Any]] = {}
    """The state of the node."""
    action_handlers: ClassVar[dict[str, callable]] = {}
    """The handlers for the actions that the node supports."""
    action_history: ClassVar[dict[str, list[ActionResult]]] = {}
    """The history of the actions that the node has performed."""
    logger: ClassVar[EventClient] = EventClient()
    """The event logger for this node"""
    module_version: ClassVar[str] = "0.0.1"
    """The version of the module. Should match the version in the node definition."""
    supported_capabilities: ClassVar[NodeClientCapabilities] = (
        AbstractNodeClient.supported_capabilities
    )
    """The default supported capabilities of this node module class."""
    config: ClassVar[NodeConfig] = NodeConfig()
    """The node configuration."""
    config_model: ClassVar[type[NodeConfig]] = NodeConfig
    """The node config model class. This is the class that will be used to instantiate self.config."""
    _action_lock: ClassVar[threading.Lock] = threading.Lock()
    """Ensures only one blocking action can run at a time."""

    def __init__(
        self,
        node_definition: Optional[NodeDefinition] = None,
        node_config: Optional[NodeConfig] = None,
    ) -> "AbstractNode":
        """Initialize the node class."""

        self.config = node_config or self.config
        if not self.config:
            self.config = self.config_model()
        self.node_definition = node_definition
        if self.node_definition is None:
            node_definition_path = getattr(
                self.config, "node_definition", "default.node.yaml"
            )
            if not Path(node_definition_path).exists():
                self.logger.warning(
                    f"Node definition file '{node_definition_path}' not found, using default node definition."
                )
                module_name = to_snake_case(self.__class__.__name__)
                node_name = str(Path(node_definition_path).stem)
                self.node_definition = NodeDefinition(
                    node_name=node_name, module_name=module_name
                )
            else:
                self.node_definition = NodeDefinition.from_yaml(node_definition_path)
        global_ownership_info.node_id = self.node_definition.node_id
        self._configure_clients()

        # * Check Node Version
        if (
            Version.parse(self.module_version).compare(
                self.node_definition.module_version
            )
            < 0
        ):
            self.logger.warning(
                "The module version in the Node Module's source code does not match the version specified in your Node Definition. Your module may have been updated. We recommend checking to ensure compatibility, and then updating the version in your node definition to match."
            )

        # * Synthesize the node info
        self.node_info = NodeInfo.from_node_def_and_config(
            self.node_definition, self.config
        )

        # * Combine the node definition and classes's capabilities
        self._populate_capabilities()

        # * Add the action decorators to the node (and node info)
        for action_callable in self.__class__.__dict__.values():
            if hasattr(action_callable, "__is_madsci_action__"):
                self._add_action(
                    func=action_callable,
                    action_name=action_callable.__madsci_action_name__,
                    description=action_callable.__madsci_action_description__,
                    blocking=action_callable.__madsci_action_blocking__,
                    result_definitions=action_callable.__madsci_action_result_definitions__,
                )

        # * Save the node info and update definition, if possible
        if self.config.update_node_files:
            self._update_node_info_and_definition()

    """------------------------------------------------------------------------------------------------"""
    """Node Lifecycle and Public Methods"""
    """------------------------------------------------------------------------------------------------"""

    def start_node(self) -> None:
        """Called once to start the node."""

        global_ownership_info.node_id = self.node_definition.node_id
        # * Update EventClient with logging parameters
        self._configure_clients()

        # * Log startup info
        self.logger.debug(f"{self.node_definition=}")

        # * Kick off the startup logic in a separate thread
        # * This allows implementations to start servers, listeners, etc.
        # * in parrallel
        self._startup()

    def status_handler(self) -> None:
        """Called periodically to update the node status. Should set `self.node_status`"""

    def state_handler(self) -> None:
        """Called periodically to update the node state. Should set `self.node_state`"""

    def startup_handler(self) -> None:
        """Called to (re)initialize the node. Should be used to open connections to devices or initialize any other resources."""

    def shutdown_handler(self) -> None:
        """Called to shut down the node. Should be used to clean up any resources."""

    """------------------------------------------------------------------------------------------------"""
    """Interface Methods"""
    """------------------------------------------------------------------------------------------------"""

    def get_action_history(
        self, action_id: Optional[str] = None
    ) -> dict[str, list[ActionResult]]:
        """Get the action history for the node or a specific action run."""
        if action_id:
            history_entry = self.action_history.get(action_id, None)
            if history_entry is None:
                history_entry = [
                    ActionResult(
                        status=ActionStatus.UNKNOWN,
                        errors=Error(
                            message=f"Action history for action with id '{action_id}' not found",
                            error_type="ActionHistoryNotFound",
                        ),
                    )
                ]
            return {action_id: history_entry}
        return self.action_history

    def run_action(self, action_request: ActionRequest) -> ActionResult:
        """Run an action on the node."""
        self.node_status.running_actions.add(action_request.action_id)
        arg_dict = {}
        self._extend_action_history(action_request.not_started())
        try:
            # * Parse the action arguments and check for required arguments
            arg_dict = self._parse_action_args(action_request)
            self._check_required_args(action_request)
        except Exception as e:
            # * If there was an error in parsing the action arguments, log the error and return a failed action response
            # * but don't set the node to errored
            self.node_status.running_actions.discard(action_request.action_id)
            self._exception_handler(e, set_node_errored=False)
            self._extend_action_history(
                action_request.failed(errors=Error.from_exception(e))
            )
        else:
            if not self.node_status.ready:
                self._extend_action_history(
                    action_request.not_ready(
                        errors=Error(
                            message=f"Node is not ready: {self.node_status.description}",
                            error_type="NodeNotReady",
                        ),
                    )
                )
                self.node_status.running_actions.discard(action_request.action_id)
            else:
                try:
                    # * Run the action in a separate thread
                    self._extend_action_history(action_request.running())
                    self._action_thread(
                        action_request,
                        self.action_handlers.get(action_request.action_name),
                        arg_dict,
                    )
                except Exception as e:
                    # * If there was an error in running the action, log the error and return a failed action response
                    # * and set the node to errored, as the node has failed to run a supposedly valid action request
                    self._exception_handler(e)
                    self._extend_action_history(
                        action_request.failed(errors=Error.from_exception(e))
                    )
                    self.node_status.running_actions.discard(action_request.action_id)
        return self.get_action_result(action_request.action_id)

    def get_action_status(self, action_id: str) -> ActionStatus:
        """Get the status of an action on the node."""
        if action_id in self.action_history and len(self.action_history[action_id]) > 0:
            return self.action_history[action_id][-1].status
        return ActionStatus.UNKNOWN

    def get_action_result(self, action_id: str) -> ActionResult:
        """Get the most up-to-date result of an action on the node."""
        if action_id in self.action_history and len(self.action_history[action_id]) > 0:
            return self.action_history[action_id][-1]
        return ActionResult(
            status=ActionStatus.UNKNOWN,
            errors=Error(
                message=f"Action history for action with id '{action_id}' not found",
                error_type="ActionHistoryNotFound",
            ),
        )

    def get_status(self) -> NodeStatus:
        """Get the status of the node."""
        return self.node_status

    def set_config(self, new_config: dict[str, Any]) -> NodeSetConfigResponse:
        """Set configuration values of the node."""

        try:
            for key, value in new_config.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                else:
                    raise ValueError(
                        f"Configuration key '{key}' is not valid for this node."
                    )
            return NodeSetConfigResponse(
                success=True,
            )
        except ValidationError as e:
            return NodeSetConfigResponse(success=True, errors=Error.from_exception(e))

    def run_admin_command(self, admin_command: AdminCommands) -> AdminCommandResponse:
        """Run the specified administrative command on the node."""
        if hasattr(self, admin_command) and callable(
            self.__getattribute__(admin_command),
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
                    f"Admin command {admin_command} returned an unexpected value: {response}",
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
                        message=f"Admin command {admin_command} not implemented by this node",
                        error_type="AdminCommandNotImplemented",
                    ),
                ],
            )

    def get_info(self) -> NodeInfo:
        """Get information about the node."""
        return self.node_info

    def get_state(self) -> dict[str, Any]:
        """Get the state of the node."""
        return self.node_state

    def get_log(self) -> dict[str, Event]:
        """Return the log of the node"""
        return self.logger.get_log()

    """------------------------------------------------------------------------------------------------"""
    """Admin Commands"""
    """------------------------------------------------------------------------------------------------"""

    def lock(self) -> bool:
        """Admin command to lock the node."""
        self.node_status.locked = True
        self.logger.info("Node locked")
        return True

    def unlock(self) -> bool:
        """Admin command to unlock the node."""
        self.node_status.locked = False
        self.logger.info("Node unlocked")
        return True

    """------------------------------------------------------------------------------------------------"""
    """Internal and Private Methods"""
    """------------------------------------------------------------------------------------------------"""

    def _configure_clients(self) -> None:
        """
        Configure the event and resource clients using MadsciClientMixin.

        This method initializes the clients required for node operation:
        - EventClient for logging
        - ResourceClient for resource management
        - DataClient for data storage
        """
        # Set the name for the EventClient
        if hasattr(self, "node_definition") and self.node_definition:
            self.name = f"node.{self.node_definition.node_name}"

        # Initialize all required clients using the mixin
        self.setup_clients()

        # Maintain backward compatibility: logger is an alias for event_client
        self.logger = self.event_client

    def _add_action(
        self,
        func: Callable,
        action_name: str,
        description: str,
        blocking: bool = True,
        result_definitions: list[str] = [],
    ) -> None:
        """Add an action to the node module.

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
            results=result_definitions,
        )
        # *Create basic action definition from function signature
        signature = inspect.signature(func)

        # Check for *args and **kwargs support
        for param in signature.parameters.values():
            if param.kind == inspect.Parameter.VAR_POSITIONAL:
                action_def.accepts_var_args = True
            elif param.kind == inspect.Parameter.VAR_KEYWORD:
                action_def.accepts_var_kwargs = True
        if signature.parameters:
            for parameter_name, parameter_type in get_type_hints(
                func,
                include_extras=True,
            ).items():
                self.logger.debug(
                    f"Adding parameter {parameter_name} of type {parameter_type} to action {action_name}",
                )
                if parameter_name == "return":
                    # TODO: Extract the return type and add it to the action definition
                    continue
                if (
                    parameter_name not in action_def.args
                    and parameter_name
                    not in [file.name for file in action_def.files.values()]
                    and parameter_name != "action"
                ):
                    self._parse_action_arg(
                        action_def, signature, parameter_name, parameter_type
                    )
        self.node_info.actions[action_name] = action_def

    def _is_file_type(self, type_hint: Any) -> bool:
        """Check if a type hint represents a file parameter.

        Now uses TypeAnalyzer for robust type detection at any nesting level.

        Args:
            type_hint: The type hint to check

        Returns:
            True if the type represents a file parameter (Path, list[Path], etc.)
        """
        try:
            type_info = analyze_type(type_hint)
            return type_info.special_type == "file"
        except (ValueError, TypeError):
            return False

    def _contains_location_argument(self, type_hint: Any) -> bool:
        """Check if a type hint contains LocationArgument.

        Now uses TypeAnalyzer for robust type detection at any nesting level.

        Args:
            type_hint: The type hint to check

        Returns:
            True if the type is or contains LocationArgument
        """
        try:
            type_info = analyze_type(type_hint)
            return type_info.special_type == "location"
        except (ValueError, TypeError):
            return False

    def _parse_action_arg(
        self,
        action_def: ActionDefinition,
        signature: inspect.Signature,
        parameter_name: str,
        parameter_type: Any,
    ) -> None:
        """Parse a function argument into a MADSci ArgumentDefinition.

        Now uses TypeAnalyzer for robust handling of complex nested type hints.
        Supports arbitrary nesting of Optional, Annotated, Union, list, etc.
        """
        # Analyze the type hint to get complete information
        type_info = analyze_type(parameter_type)

        # Check for special definition metadata
        file_definition = next(
            (m for m in type_info.metadata if isinstance(m, FileArgumentDefinition)),
            None,
        )
        location_definition = next(
            (
                m
                for m in type_info.metadata
                if isinstance(m, LocationArgumentDefinition)
            ),
            None,
        )
        arg_definition = next(
            (
                m
                for m in type_info.metadata
                if isinstance(m, ArgumentDefinition)
                and not isinstance(
                    m, (FileArgumentDefinition, LocationArgumentDefinition)
                )
            ),
            None,
        )

        annotated_as_file = file_definition is not None
        annotated_as_location = location_definition is not None
        annotated_as_arg = arg_definition is not None

        # Extract description from metadata
        # Priority: definition.description > string metadata > ""
        description = ""
        if annotated_as_file and file_definition and file_definition.description:
            description = file_definition.description
        elif (
            annotated_as_location
            and location_definition
            and location_definition.description
        ):
            description = location_definition.description
        elif annotated_as_arg and arg_definition and arg_definition.description:
            description = arg_definition.description
        else:
            # Fall back to first string in metadata
            description = next(
                (m for m in type_info.metadata if isinstance(m, str)),
                "",
            )

        # Validate that parameter isn't annotated as multiple types
        if sum([annotated_as_file, annotated_as_arg, annotated_as_location]) > 1:
            raise ValueError(
                f"Parameter '{parameter_name}' is annotated as multiple types of argument. "
                f"This is not allowed.",
            )

        # Get parameter info for default value and required status
        parameter_info = signature.parameters[parameter_name]
        default = (
            None
            if parameter_info.default == inspect.Parameter.empty
            else parameter_info.default
        )

        # Determine if parameter is required:
        # - If type is Optional and parameter has a default, it's not required
        # - If type is Optional but no default, it's still required (explicit None must be passed)
        # - If type is not Optional but has a default, it's not required
        # - If type is not Optional and no default, it's required
        has_default = parameter_info.default != inspect.Parameter.empty
        is_required = not (type_info.is_optional or has_default)

        # Classify parameter based on special type or annotation
        if annotated_as_file or (
            type_info.special_type == "file" and not annotated_as_arg
        ):
            # File parameter (Path, list[Path], etc.)
            action_def.files[parameter_name] = FileArgumentDefinition(
                name=parameter_name,
                required=is_required,
                description=description,
            )
        elif annotated_as_location or type_info.special_type == "location":
            # Location parameter (LocationArgument)
            action_def.locations[parameter_name] = LocationArgumentDefinition(
                name=parameter_name,
                required=is_required,
                description=description,
            )
        else:
            # Regular argument
            action_def.args[parameter_name] = ArgumentDefinition(
                name=parameter_name,
                argument_type=pretty_type_repr(type_info.base_type),
                default=default,
                required=is_required,
                description=description,
            )

    def _parse_action_args(
        self,
        action_request: ActionRequest,
    ) -> Union[ActionResult, tuple[callable, dict[str, Any]]]:
        """Parse the arguments for an action request."""
        action_callable = self._get_action_callable(action_request.action_name)
        parameters = inspect.signature(action_callable).parameters

        # Analyze function signature for special parameter types
        param_analysis = self._analyze_function_parameters(parameters)

        # Set up base arguments (action, self)
        arg_dict = self._setup_base_arguments(
            action_request, parameters, param_analysis
        )

        # Process regular arguments and files based on function signature
        self._process_regular_arguments(
            arg_dict, action_request, parameters, param_analysis
        )

        # Handle variable arguments (*args, **kwargs)
        self._process_variable_arguments(
            arg_dict, action_request, param_analysis, parameters
        )

        # Validate any arguments that expect a Pydantic BaseModel (LocationArgument, etc.)
        return self._validate_pydantic_arguments(action_callable, arg_dict)

    def _get_action_callable(self, action_name: str) -> Callable:
        """Get the callable for an action, raising an error if not found."""
        action_callable = self.action_handlers.get(action_name, None)
        if action_callable is None:
            raise ActionNotImplementedError(
                f"Action {action_name} not implemented by this node",
            )
        return action_callable

    def _analyze_function_parameters(self, parameters: dict) -> dict[str, Any]:
        """Analyze function parameters to detect *args and **kwargs."""
        # Get ordered list of regular parameters (excluding *args, **kwargs, self, action)
        regular_params = []
        positional_before_varargs = []
        keyword_only_after_varargs = []

        var_args_found = False

        for param_name, param in parameters.items():
            if param_name in ("self", "action"):
                continue

            if param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
                regular_params.append(param_name)
                if not var_args_found:
                    positional_before_varargs.append(param_name)

            elif param.kind == inspect.Parameter.VAR_POSITIONAL:
                var_args_found = True

            elif param.kind == inspect.Parameter.KEYWORD_ONLY:
                keyword_only_after_varargs.append(param_name)

        return {
            "has_var_kwargs": any(
                param.kind == inspect.Parameter.VAR_KEYWORD
                for param in parameters.values()
            ),
            "has_var_args": any(
                param.kind == inspect.Parameter.VAR_POSITIONAL
                for param in parameters.values()
            ),
            "regular_params_order": regular_params,
            "positional_before_varargs": positional_before_varargs,
            "keyword_only_after_varargs": keyword_only_after_varargs,
        }

    def _setup_base_arguments(
        self,
        action_request: ActionRequest,
        parameters: dict,
        param_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        """Set up base arguments like 'action' and 'self' if needed by the function."""
        arg_dict = {}
        if parameters.__contains__("action"):
            arg_dict["action"] = action_request

        # Only add 'self' to kwargs if we don't have *args
        # (with *args, self will be the first positional argument)
        if parameters.__contains__("self") and not param_analysis["has_var_args"]:
            arg_dict["self"] = self

        return arg_dict

    def _process_regular_arguments(
        self,
        arg_dict: dict[str, Any],
        action_request: ActionRequest,
        parameters: dict,
        param_analysis: dict[str, Any],
    ) -> None:
        """Process regular arguments and files based on function signature."""
        if param_analysis["has_var_kwargs"] and param_analysis["has_var_args"]:
            # Function has both *args and **kwargs
            # Only add args that won't be handled positionally by *args
            for arg_name, arg_value in action_request.args.items():
                if arg_name not in param_analysis["positional_before_varargs"]:
                    arg_dict[arg_name] = arg_value
            arg_dict.update({file.filename: file.file for file in action_request.files})
        elif param_analysis["has_var_kwargs"]:
            # Function has **kwargs, so we can pass all action args and files
            arg_dict.update(action_request.args)
            arg_dict.update({file.filename: file.file for file in action_request.files})
        elif param_analysis["has_var_args"]:
            # Function has *args - only pass files as keyword arguments here
            # Regular args will be handled specially in _process_variable_arguments
            arg_dict.update({file.filename: file.file for file in action_request.files})
        else:
            # Pass only explicit arguments, dropping extras
            self._process_explicit_arguments(arg_dict, action_request, parameters)

    def _process_explicit_arguments(
        self,
        arg_dict: dict[str, Any],
        action_request: ActionRequest,
        parameters: dict,
    ) -> None:
        """Process only explicit arguments that match function parameters."""
        for arg_name, arg_value in action_request.args.items():
            if arg_name in parameters:
                arg_dict[arg_name] = arg_value
            else:
                self.logger.log_warning(f"Ignoring unexpected argument {arg_name}")

        for file in action_request.files:
            if file in parameters:
                arg_dict[file] = action_request.files[file]
            else:
                self.logger.log_warning(f"Ignoring unexpected file {file}")

    def _validate_var_args_compatibility(
        self,
        action_request: ActionRequest,
        param_analysis: dict[str, Any],
        parameters: dict,
    ) -> None:
        """Validate that *args usage won't cause parameter conflicts."""
        if not param_analysis["has_var_args"] or not action_request.var_args:
            return

        # Check for optional parameters with defaults that aren't provided
        missing_optional_params = []
        for param_name in param_analysis["positional_before_varargs"]:
            param = parameters[param_name]
            if (
                param_name not in action_request.args
                and param.default != inspect.Parameter.empty
            ):
                missing_optional_params.append(param_name)

        if missing_optional_params:
            raise ValueError(
                f"Action '{action_request.action_name}' has *args but optional parameters "
                f"{missing_optional_params} with defaults are not provided. This would cause "
                f"var_args {action_request.var_args} to be incorrectly assigned to these "
                f"parameters instead of going to *args. Solutions: "
                f"1) Provide values for {missing_optional_params}, "
                f"2) Use **kwargs instead of *args, or "
                f"3) Make parameters before *args required (no defaults)."
            )

    def _process_variable_arguments(
        self,
        arg_dict: dict[str, Any],
        action_request: ActionRequest,
        param_analysis: dict[str, Any],
        parameters: dict,
    ) -> None:
        """Process variable arguments (*args, **kwargs) if present."""
        # Handle **kwargs
        if param_analysis["has_var_kwargs"] and action_request.var_kwargs:
            arg_dict.update(action_request.var_kwargs)

        # Handle *args with safety validation
        if param_analysis["has_var_args"]:
            # Validate compatibility first
            self._validate_var_args_compatibility(
                action_request, param_analysis, parameters
            )

            var_args = []

            # Always add self as first argument if the function expects it
            if "self" in parameters:
                var_args.append(self)

            # Add regular parameters that come before *args as positional arguments
            # in the correct order to avoid "multiple values for argument" errors
            for param_name in param_analysis["positional_before_varargs"]:
                if param_name != "self" and param_name in action_request.args:
                    var_args.append(action_request.args[param_name])

            # Add actual var_args from the request (these go to *args)
            if action_request.var_args:
                var_args.extend(action_request.var_args)

            # Include keyword-only parameters in arg_dict for *args functions
            for param_name in param_analysis["keyword_only_after_varargs"]:
                if param_name in action_request.args and param_name not in arg_dict:
                    arg_dict[param_name] = action_request.args[param_name]

            # Store the args list
            if var_args:
                arg_dict["__madsci_var_args__"] = var_args

    def _extract_pydantic_types_from_hint(
        self, type_hint: Any
    ) -> list[type[BaseModel]]:
        """
        Extract all Pydantic BaseModel types from a type hint.

        Handles:
        - Direct BaseModel subclasses
        - Optional[BaseModel] (Union[BaseModel, None])
        - Union[BaseModel, OtherType, ...]
        - Annotated[BaseModel, ...]

        Args:
            type_hint: The type hint to analyze

        Returns:
            List of BaseModel subclass types found in the hint
        """
        pydantic_types = []

        # Handle Annotated types - extract the actual type
        origin = get_origin(type_hint)
        if origin is Annotated:
            type_hint = get_args(type_hint)[0]
            origin = get_origin(type_hint)

        # Handle Union types (including Optional)
        if origin is Union:
            for arg in get_args(type_hint):
                # Skip None type
                if arg is type(None):
                    continue
                # Check if it's a BaseModel subclass
                try:
                    if isinstance(arg, type) and issubclass(arg, BaseModel):
                        pydantic_types.append(arg)
                except TypeError:
                    # issubclass raises TypeError if arg is not a class
                    pass
        else:
            # Direct type - check if it's a BaseModel subclass
            try:
                if isinstance(type_hint, type) and issubclass(type_hint, BaseModel):
                    pydantic_types.append(type_hint)
            except TypeError:
                pass

        return pydantic_types

    def _validate_pydantic_arguments(
        self,
        action_callable: Callable,
        arg_dict: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Validate and convert any arguments expected as Pydantic BaseModel instances.

        This handles LocationArgument and any other BaseModel subclasses that may be
        passed as dictionaries from deserialized JSON payloads. It properly handles:
        - Direct BaseModel types: LocationArgument, CustomModel, etc.
        - Optional[BaseModel]: Optional[LocationArgument], etc.
        - Union[BaseModel, OtherType]: Union[LocationArgument, str], etc.

        If the action function declares a parameter with a BaseModel type (directly or
        within Optional/Union) and the corresponding value in arg_dict is a dictionary,
        this function uses Pydantic's model_validate to reconstruct the proper model instance.

        Raises:
            ValueError: If the input dictionary fails validation for the expected model.

        Returns:
            dict[str, Any]: The updated argument dictionary with validated BaseModel objects.
        """
        type_hints = get_type_hints(action_callable)
        for name, expected_type in type_hints.items():
            # Skip if no value provided for this parameter
            if name not in arg_dict:
                continue

            value = arg_dict[name]

            # Skip if value is not a dict (already the right type or None)
            if not isinstance(value, dict):
                continue

            # Extract all Pydantic types from the hint
            pydantic_types = self._extract_pydantic_types_from_hint(expected_type)

            # If we found Pydantic types, try to validate
            for pydantic_type in pydantic_types:
                try:
                    # Try to validate the dict as this Pydantic type
                    arg_dict[name] = pydantic_type.model_validate(value)
                    # If successful, break (we found the right type)
                    break
                except ValidationError:
                    # This type didn't work, try the next one
                    continue
            else:
                # If we had pydantic types but none validated successfully
                if pydantic_types:
                    # Try the first one again to get the proper error message
                    try:
                        arg_dict[name] = pydantic_types[0].model_validate(value)
                    except ValidationError as e:
                        raise ValueError(
                            f"Invalid {pydantic_types[0].__name__} for parameter '{name}': {e}"
                        ) from e

        return arg_dict

    def _process_result(
        self, result: Any, action_request: ActionRequest
    ) -> ActionResult:
        """Process the result of an action and convert it to an ActionResult if necessary."""
        datapoints = None
        json_result = None
        files = None
        if isinstance(result, ActionResult):
            result.action_id = action_request.action_id
            return result
        if not isinstance(result, tuple):
            result = (result,)

        # Parse the result tuple into separate components
        json_data, files, datapoints = self._parse_result_components(result)

        # Set json_result to the parsed data (could be primitive, dict, or None)
        json_result = json_data

        return ActionResult(
            status=ActionStatus.SUCCEEDED,
            action_id=action_request.action_id,
            json_result=json_result,
            files=files,
            datapoints=datapoints,
        )

    def _parse_result_components(self, result: tuple) -> tuple[Any, Any, Any]:
        """Parse result tuple into JSON data, files, and datapoints."""
        json_components = []
        files = None
        datapoints = None

        for value in result:
            json_component, file_component, datapoint_component = (
                self._parse_single_result_value(value)
            )

            if json_component is not None:
                json_components.append(json_component)
            if file_component is not None:
                files = file_component
            if datapoint_component is not None:
                datapoints = datapoint_component

        json_data = self._combine_json_components(json_components)
        return json_data, files, datapoints

    def _parse_single_result_value(self, value: Any) -> tuple[Any, Any, Any]:
        """Parse a single result value into JSON, files, and datapoints components.

        Returns:
            Tuple of (json_component, file_component, datapoint_component)
        """
        if isinstance(value, ActionJSON):
            return self._parse_action_json(value), None, None
        if isinstance(value, ActionFiles):
            return None, value, None
        if isinstance(value, ActionDatapoints):
            return None, None, value
        if isinstance(value, Path):
            return None, value, None
        if self._is_pydantic_model(value):
            return value.model_dump(mode="json"), None, None
        # For primitive values, return them directly
        return value, None, None

    def _parse_action_json(self, action_json: "ActionJSON") -> list[dict]:
        """Parse ActionJSON subclass into list of key-value dictionaries."""
        json_data_dict = action_json.model_dump(mode="json")
        json_components = []
        for key, val in json_data_dict.items():
            if key != "type":  # Skip the type field
                json_components.append({key: val})
        return json_components

    def _is_pydantic_model(self, value: Any) -> bool:
        """Check if a value is a Pydantic model."""
        return hasattr(value, "model_dump") and hasattr(value, "model_json_schema")

    def _combine_json_components(self, json_components: list) -> Any:
        """Combine multiple JSON components into final JSON result.

        Args:
            json_components: List of JSON components (primitives, dicts, or lists)

        Returns:
            Combined JSON result (None, single value, or combined dict)
        """
        if len(json_components) == 0:
            return None
        if len(json_components) == 1:
            component = json_components[0]
            # Handle ActionJSON case where we get a list of dicts
            if isinstance(component, list) and len(component) == 1:
                return component[0]
            return component
        # Multiple components - combine into a dictionary
        json_data = {}
        for i, component in enumerate(json_components):
            if isinstance(component, list):
                # Handle ActionJSON components (list of dicts)
                for item in component:
                    if isinstance(item, dict):
                        json_data.update(item)
            elif isinstance(component, dict):
                json_data.update(component)
            else:
                # Multiple primitives - use indexed keys
                json_data[f"result_{i}"] = component
        return json_data

    @threaded_daemon
    def _action_thread(
        self,
        action_request: ActionRequest,
        action_callable: callable,
        arg_dict: dict[str, Any],
    ) -> None:
        try:
            with (
                self._action_lock
                if self.node_info.actions[action_request.action_name].blocking
                else contextlib.nullcontext()
            ):
                try:
                    if self.node_info.actions[action_request.action_name].blocking:
                        self.node_status.busy = True

                    # Handle var_args specially if present
                    if "__madsci_var_args__" in arg_dict:
                        var_args = arg_dict.pop("__madsci_var_args__")
                        result = action_callable(*var_args, **arg_dict)
                    else:
                        result = action_callable(**arg_dict)
                except Exception as e:
                    self._exception_handler(e)
                    result = action_request.failed(errors=Error.from_exception(e))
                finally:
                    if self.node_info.actions[action_request.action_name].blocking:
                        self.node_status.busy = False
        finally:
            self.node_status.running_actions.discard(action_request.action_id)
        try:
            action_result = self._process_result(result, action_request)

        except ValidationError:
            action_result = action_request.unknown(
                errors=Error(
                    message=f"Action '{action_request.action_name}' returned an unexpected value: {result}.",
                ),
            )
        self._extend_action_history(action_result)

    def _exception_handler(self, e: Exception, set_node_errored: bool = True) -> None:
        """Handle an exception."""
        if set_node_errored:
            self.node_status.errored = True
        madsci_error = Error.from_exception(e)

        self.node_status.errors.append(madsci_error)
        if len(self.node_status.errors) > 100:
            self.node_status.errors = self.node_status.errors[1:]
        self.logger.error(
            Event(event_type=EventType.NODE_ERROR, event_data=madsci_error)
        )
        self.logger.error(traceback.format_exc())

    def _update_status(self) -> None:
        """Update the node status."""
        try:
            self.status_handler()
        except Exception as e:
            self._exception_handler(e)

    def _update_state(self) -> None:
        """Update the node state."""
        try:
            self.state_handler()
        except Exception as e:
            self._exception_handler(e)

    def _populate_capabilities(self) -> None:
        """Populate the node capabilities based on the node definition and the supported capabilities of the class."""
        if self.node_info.capabilities is None:
            self.node_info.capabilities = NodeCapabilities()
        for field in self.supported_capabilities.__pydantic_fields__:
            if getattr(self.node_info.capabilities, field) is None:
                setattr(
                    self.node_info.capabilities,
                    field,
                    getattr(self.supported_capabilities, field),
                )

        # * Add the admin commands to the node info
        self.node_info.capabilities.admin_commands = set.union(
            self.node_info.capabilities.admin_commands,
            {
                admin_command.value
                for admin_command in AdminCommands
                if hasattr(self, admin_command.value)
                and callable(self.__getattribute__(admin_command.value))
            },
        )

    def _update_node_info_and_definition(self) -> None:
        """Update the node info and definition files, if possible."""
        try:
            self.node_definition.to_yaml(self.config.node_definition)
            if not self.config.node_info_path:
                self.node_info_path = Path(self.config.node_definition).with_name(
                    f"{self.node_definition.node_name}.info.yaml"
                )
            self.node_info.to_yaml(self.node_info_path, exclude={"config_values"})
        except Exception as e:
            self.logger.warning(
                f"Failed to update node info file: {e}",
            )

    def _check_required_args(self, action_request: ActionRequest) -> None:
        """Check that all required arguments are present in the action request."""
        missing_args = [
            arg_name
            for arg_name, arg_def in self.node_info.actions[
                action_request.action_name
            ].args.items()
            if arg_def.required
            and arg_name not in action_request.args
            and arg_name not in action_request.files
        ]
        if missing_args:
            raise ValueError(
                f"Missing required arguments for action '{action_request.action_name}': {missing_args}"
            )

    def upload_datapoint(self, datapoint: DataPoint) -> str:
        """Upload a datapoint to the data manager and return its ID.

        Args:
            datapoint: DataPoint object to upload

        Returns:
            The ULID string ID of the uploaded datapoint

        Raises:
            Exception: If upload fails
        """
        if not isinstance(datapoint, DataPoint):
            raise ValueError("Expected DataPoint object")

        uploaded_datapoint = self.data_client.submit_datapoint(datapoint)
        return uploaded_datapoint.datapoint_id

    def upload_datapoints(self, datapoints: list[DataPoint]) -> list[str]:
        """Upload multiple datapoints to the data manager and return their IDs.

        Args:
            datapoints: List of DataPoint objects to upload

        Returns:
            List of ULID string IDs of the uploaded datapoints

        Raises:
            Exception: If any upload fails
        """
        uploaded_ids = []
        for datapoint in datapoints:
            uploaded_id = self.upload_datapoint(datapoint)
            uploaded_ids.append(uploaded_id)
        return uploaded_ids

    def create_and_upload_value_datapoint(
        self, value: Any, label: Optional[str] = None
    ) -> str:
        """Create a ValueDataPoint and upload it to the data manager.

        Args:
            value: JSON-serializable value to store
            label: Optional label for the datapoint

        Returns:
            The ULID string ID of the uploaded datapoint
        """
        datapoint = ValueDataPoint(value=value, label=label)
        return self.upload_datapoint(datapoint)

    def create_and_upload_file_datapoint(
        self, file_path: Union[str, Path], label: Optional[str] = None
    ) -> str:
        """Create a FileDataPoint and upload it to the data manager.

        Args:
            file_path: Path to the file to store
            label: Optional label for the datapoint

        Returns:
            The ULID string ID of the uploaded datapoint
        """
        datapoint = FileDataPoint(path=Path(file_path), label=label)
        return self.upload_datapoint(datapoint)

    @threaded_daemon
    def _startup(self) -> None:
        """The startup thread for the node."""
        try:
            # * Create a clean status and mark the node as initializing
            self.node_status.initializing = True
            self.node_status.errored = False
            self.node_status.locked = False
            self.node_status.paused = False
            self.node_status.stopped = False
            self.startup_handler()
            # * Start status and state update loops
            repeat_on_interval(
                getattr(self.config, "status_update_interval", 2.0), self._update_status
            )
            repeat_on_interval(
                getattr(self.config, "state_update_interval", 2.0), self._update_state
            )

        except Exception as exception:
            # * Handle any exceptions that occurred during startup
            self._exception_handler(exception)
            self.node_status.errored = True
        else:
            self.logger.info(
                Event(
                    event_type=EventType.NODE_START,
                    event_data=self.node_definition.model_dump(mode="json"),
                )
            )
        finally:
            # * Mark the node as no longer initializing
            self.node_status.initializing = False

    def _extend_action_history(self, action_result: ActionResult) -> None:
        """Extend the action history with a new action result."""
        existing_history = self.action_history.get(action_result.action_id, None)
        if existing_history is None:
            self.action_history[action_result.action_id] = [action_result]
        else:
            self.action_history[action_result.action_id].append(action_result)
        self.logger.info(
            Event(
                event_type=EventType.ACTION_STATUS_CHANGE,
                event_data=action_result,
            )
        )
