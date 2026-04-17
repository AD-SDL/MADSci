"""SiLA2-based node client implementation.

Connects to SiLA2 servers via gRPC using the sila2 Python SDK.
Requires the 'sila' optional dependency: pip install "madsci.client[sila]"
"""

import base64
import contextlib
import threading
import time
import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Optional
from urllib.parse import urlparse

from madsci.client.event_client import EventClient
from madsci.client.node.abstract_node_client import AbstractNodeClient
from madsci.common.context import get_event_client
from madsci.common.sentry import get_madsci_subdir
from madsci.common.types.action_types import (
    ActionDefinition,
    ActionFiles,
    ActionRequest,
    ActionResult,
    ActionStatus,
    ArgumentDefinition,
)
from madsci.common.types.base_types import Error
from madsci.common.types.event_types import EventType
from madsci.common.types.node_types import (
    NodeClientCapabilities,
    NodeInfo,
    NodeStatus,
)
from pydantic import AnyUrl

if TYPE_CHECKING:
    from madsci.common.types.client_types import SilaNodeClientConfig

try:
    from sila2.client import SilaClient

    SILA2_AVAILABLE = True
except ImportError:
    SILA2_AVAILABLE = False
    SilaClient = None  # type: ignore[assignment,misc]

_DEFAULT_SILA_PORT = 50052


def _parse_sila_url(url: str) -> tuple[str, int]:
    """Parse a sila:// URL into (host, port).

    Supports formats:
        sila://192.168.1.100:50052
        sila://hostname:50052
        sila://hostname  (defaults to port 50052)
    """
    parsed = urlparse(url if "://" in url else f"sila://{url}")
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or _DEFAULT_SILA_PORT
    return host, port


def _resolve_sila_command(client: Any, action_name: str) -> tuple[Any, str, str]:
    """Resolve a MADSci action_name to a SiLA feature+command callable.

    Supports two forms:
        "FeatureName.CommandName" -> client.FeatureName.CommandName
        "CommandName" -> searches all features for an unambiguous match

    Returns:
        A tuple (callable, feature_name, command_name).

    Raises:
        ValueError: If the command is not found or is ambiguous.
    """
    if "." in action_name:
        feature_name, command_name = action_name.split(".", 1)
        feature = getattr(client, feature_name, None)
        if feature is None:
            msg = f"SiLA feature '{feature_name}' not found on server"
            raise ValueError(msg)
        command = getattr(feature, command_name, None)
        if command is None:
            msg = f"SiLA command '{command_name}' not found on feature '{feature_name}'"
            raise ValueError(msg)
        if not callable(command):
            msg = (
                f"'{command_name}' on feature '{feature_name}' is not a callable command "
                f"(it may be a SiLA property). Use '.get()' to read properties."
            )
            raise ValueError(msg)
        return command, feature_name, command_name

    # Short form: search all features
    matches: list[tuple[Any, str, str]] = []
    for feature_id in _get_feature_ids(client):
        feature = getattr(client, feature_id, None)
        if feature is None:
            continue
        command = getattr(feature, action_name, None)
        if command is not None and callable(command):
            matches.append((command, feature_id, action_name))

    if len(matches) == 0:
        msg = f"SiLA command '{action_name}' not found on any feature"
        raise ValueError(msg)
    if len(matches) > 1:
        feature_names = [m[1] for m in matches]
        msg = (
            f"Ambiguous command '{action_name}' found on multiple features: "
            f"{feature_names}. Use 'FeatureName.CommandName' to disambiguate."
        )
        raise ValueError(msg)
    return matches[0]


def _fqi_to_short_id(fqi: str) -> str:
    """Extract the short feature identifier from a fully qualified identifier.

    E.g., "org.madsci/examples/ExampleDevice/v1" -> "ExampleDevice"
    """
    parts = str(fqi).split("/")
    # The identifier is the second-to-last part (before the version)
    if len(parts) >= 2:
        return parts[-2]
    return str(fqi)


def _get_feature_ids(client: Any) -> list[str]:
    """Get the list of implemented feature short identifiers from a SiLA client.

    The SiLAService returns fully qualified identifiers (e.g.,
    "org.madsci/examples/ExampleDevice/v1"). This function extracts the
    short identifiers (e.g., "ExampleDevice") which are the attribute names
    on the SilaClient object.
    """
    try:
        fqis = client.SiLAService.ImplementedFeatures.get()
        return [_fqi_to_short_id(fqi) for fqi in fqis]
    except Exception:
        return []


def _response_to_dict(response: Any) -> dict[str, Any]:
    """Convert a SiLA command response object to a JSON-serializable dict.

    SiLA responses are namedtuple-like objects with fields named after
    the command's response parameters.
    """
    if response is None:
        return {}
    if isinstance(response, dict):
        return response
    # SiLA responses have _fields (namedtuple-like)
    if hasattr(response, "_fields"):
        return {
            field: _serialize_value(getattr(response, field))
            for field in response._fields
        }
    if hasattr(response, "__dict__"):
        return {
            k: _serialize_value(v)
            for k, v in response.__dict__.items()
            if not k.startswith("_")
        }
    return {"result": str(response)}


def _serialize_value(value: Any) -> Any:
    """Convert a SiLA value to a JSON-serializable form.

    Bytes values are base64-encoded and returned as a sentinel dict
    so that _extract_bytes_files can post-process them into ActionFiles.
    """
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if isinstance(value, bytes):
        return {
            "__madsci_bytes__": True,
            "base64": base64.b64encode(value).decode("ascii"),
            "size": len(value),
        }
    if isinstance(value, (list, tuple)):
        return [_serialize_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    if hasattr(value, "_fields"):
        return {f: _serialize_value(getattr(value, f)) for f in value._fields}
    return str(value)


def _extract_bytes_files(
    json_result: dict[str, Any], action_id: str
) -> tuple[dict[str, Any], ActionFiles | None]:
    """Extract bytes sentinel dicts from a response, write files, and return cleaned result.

    # TODO: Only top-level keys are scanned. Nested bytes sentinels (e.g.,
    # inside sub-namedtuples or nested dicts) are left in-place in json_result
    # and not extracted to files. To support nested bytes, this function would
    # need recursive traversal.

    Scans top-level keys of json_result for sentinel dicts produced by
    _serialize_value when it encounters bytes values. For each sentinel:
    - Writes the decoded bytes to a file in the sila_files/{action_id}/ directory
    - Replaces the sentinel in json_result with the base64 string
    - Collects file paths into an ActionFiles instance

    Returns:
        A tuple of (cleaned_json_result, action_files_or_none).
    """
    file_paths: dict[str, Path] = {}
    cleaned = dict(json_result)

    for key, value in json_result.items():
        if isinstance(value, dict) and value.get("__madsci_bytes__") is True:
            # Write bytes to disk
            output_dir = get_madsci_subdir("sila_files") / action_id
            output_dir.mkdir(parents=True, exist_ok=True)
            file_path = output_dir / f"{key}.bin"
            raw_bytes = base64.b64decode(value["base64"])
            file_path.write_bytes(raw_bytes)

            file_paths[key] = file_path
            cleaned[key] = value["base64"]

    if file_paths:
        return cleaned, ActionFiles(**file_paths)
    return cleaned, None


def _extract_argument_definitions(command_attr: Any) -> dict[str, ArgumentDefinition]:
    """Extract ArgumentDefinition entries from a SiLA client command's wrapped command.

    Accesses ``command_attr._wrapped_command.parameters.fields`` to read
    parameter metadata (identifier, description, data type).

    NOTE: Private SiLA SDK attribute usage
    - ``_wrapped_command``: The underlying protobuf command descriptor. The sila2
      SDK does not expose a public API for reading command parameter metadata;
      this private attribute is the only way to get parameter names, descriptions,
      and types from the client side.
    - ``_identifier`` / ``_description``: Per-parameter metadata on the wrapped
      command's field descriptors. Also private, no public alternative.
    - Graceful degradation: the entire body is wrapped in ``contextlib.suppress``,
      so if these attributes are renamed or removed in a future sila2 version,
      argument extraction silently returns an empty dict and command execution
      still works — only introspection metadata is lost.
    """
    args: dict[str, ArgumentDefinition] = {}
    with contextlib.suppress(Exception):
        wrapped = command_attr._wrapped_command
        for param in wrapped.parameters.fields:
            name = str(getattr(param, "_identifier", "unknown"))
            description = str(getattr(param, "_description", ""))
            arg_type = (
                type(param.data_type).__name__ if hasattr(param, "data_type") else "Any"
            )
            args[name] = ArgumentDefinition(
                name=name,
                description=description,
                argument_type=arg_type,
                required=True,
            )
    return args


def _is_command_observable(command_attr: Any) -> bool:
    """Check if a SiLA client command is observable (vs unobservable).

    NOTE: Class-name heuristic for private SDK types
    The sila2 SDK uses ``ClientObservableCommand`` and
    ``ClientUnobservableCommand`` classes internally. There is no public API
    to query whether a command is observable. We detect it via the class name
    because importing the concrete types would create a hard dependency on
    sila2 internals that may move between releases.

    Degradation: if the SDK renames these classes, this function returns False
    (treating the command as unobservable). The command will still execute
    correctly — only the ``asynchronous`` flag in ``ActionDefinition`` would be
    wrong, which affects UI hints but not execution.
    """
    cls_name = type(command_attr).__name__
    return "Observable" in cls_name and "Unobservable" not in cls_name


def _is_observable_instance(result: Any) -> bool:
    """Check if a SiLA command result is an observable command instance."""
    return hasattr(result, "status") and hasattr(result, "get_responses")


_CONNECTION_ERROR_HINTS: dict[str, str] = {
    "dns_resolution": "Check that the hostname is spelled correctly and DNS is configured.",
    "connection_refused": "Check that the SiLA server is running on the target host and port.",
    "connection_timeout": "Check network connectivity and firewall rules.",
    "tls_error": "Check TLS configuration: verify the 'insecure' setting and certificate path.",
    "grpc_error": "Check gRPC server availability and protocol compatibility.",
    "unknown": "Check server availability and network configuration.",
}


def _classify_connection_error(exception: Exception) -> str:
    """Classify a connection error into a diagnostic category.

    Returns one of: dns_resolution, connection_refused, connection_timeout,
    tls_error, grpc_error, unknown.
    """
    msg = str(exception).lower()
    exc_type = type(exception).__name__.lower()

    if "dns resolution failed" in msg or "name resolution failure" in msg:
        return "dns_resolution"
    if "connection refused" in msg or "connect failed" in msg:
        return "connection_refused"
    if (
        "timeouterror" in exc_type
        or isinstance(exception, TimeoutError)
        or "deadline exceeded" in msg
    ):
        return "connection_timeout"
    if any(term in msg for term in ("ssl", "tls", "certificate")):
        return "tls_error"
    if "rpcerror" in exc_type or "grpc" in msg or "statuscode" in msg:
        return "grpc_error"
    return "unknown"


def _format_connection_error(
    exception: Exception, host: str, port: int, insecure: bool
) -> str:
    """Build an enriched connection error message with diagnostic context."""
    category = _classify_connection_error(exception)
    tls_mode = "disabled" if insecure else "enabled"
    hint = _CONNECTION_ERROR_HINTS[category]
    return (
        f"SiLA connection error ({category}): {exception}\n"
        f"  Target: {host}:{port} (TLS: {tls_mode})\n"
        f"  Hint: {hint}"
    )


class SilaNodeClient(AbstractNodeClient):
    """SiLA2 gRPC-based node client.

    Connects to SiLA2 servers using the sila2 Python SDK. Supports both
    unobservable (synchronous) and observable (long-running) SiLA commands.

    URL scheme: sila://host:port

    Requires the 'sila' optional dependency:
        pip install "madsci.client[sila]"
    """

    url_protocols: ClassVar[list[str]] = ["sila"]

    supported_capabilities: ClassVar[NodeClientCapabilities] = NodeClientCapabilities(
        get_info=True,
        get_state=True,
        get_status=True,
        send_action=True,
        get_action_status=True,
        get_action_result=True,
        get_action_history=False,
        action_files=True,
        send_admin_commands=False,
        set_config=False,
        get_resources=False,
        get_log=False,
    )

    def __init__(
        self,
        url: AnyUrl,
        config: Optional["SilaNodeClientConfig"] = None,
        event_client: Optional[EventClient] = None,
    ) -> None:
        """Initialize the SiLA node client.

        Args:
            url: A sila://host:port URL.
            config: Optional SiLA-specific client configuration.
            event_client: Optional event client for structured logging.

        Raises:
            ImportError: If the sila2 package is not installed.
        """
        if not SILA2_AVAILABLE:
            msg = (
                "The 'sila2' package is required for SilaNodeClient. "
                'Install it with: pip install "madsci.client[sila]"'
            )
            raise ImportError(msg)

        super().__init__(url)

        if event_client is not None:
            self.logger = event_client
        else:
            self.logger = get_event_client()

        if config is None:
            from madsci.common.types.client_types import (  # noqa: PLC0415
                SilaNodeClientConfig,
            )

            config = SilaNodeClientConfig()
        self.config = config

        self._host, self._port = _parse_sila_url(str(url))

        # Lazy SiLA client connection
        self._sila_client: Optional[Any] = None
        self._sila_lock = threading.Lock()

        # Observable command tracking: action_id -> (instance, feature, command)
        self._running_commands: dict[str, tuple[Any, str, str]] = {}
        self._commands_lock = threading.Lock()

    def _get_sila_client(self) -> Any:
        """Get or create the SiLA client connection (thread-safe, lazy)."""
        with self._sila_lock:
            if self._sila_client is None:
                kwargs: dict[str, Any] = {}
                if self.config.insecure:
                    kwargs["insecure"] = True
                elif self.config.root_certs_path:
                    kwargs["root_certs"] = Path(
                        self.config.root_certs_path
                    ).read_bytes()

                try:
                    self._sila_client = SilaClient(self._host, self._port, **kwargs)
                except Exception as e:
                    enriched = _format_connection_error(
                        e, self._host, self._port, self.config.insecure
                    )
                    self.logger.log_error(
                        enriched,
                        event_type=EventType.LOG_ERROR,
                        host=self._host,
                        port=self._port,
                    )
                    raise type(e)(enriched) from e
                self.logger.info(
                    "Connected to SiLA server",
                    event_type=EventType.LOG_INFO,
                    host=self._host,
                    port=self._port,
                )
            return self._sila_client

    # ------------------------------------------------------------------
    # Action execution
    # ------------------------------------------------------------------

    def send_action(
        self,
        action_request: ActionRequest,
        await_result: bool = True,
        timeout: Optional[float] = None,
    ) -> ActionResult:
        """Execute a SiLA command.

        Args:
            action_request: Action to perform. action_name should be either
                "FeatureName.CommandName" or just "CommandName" (if unambiguous).
                args are passed as keyword arguments to the SiLA command.
            await_result: If True, block until the command completes.
            timeout: Timeout in seconds. Defaults to config.command_timeout.
        """
        effective_timeout = timeout or self.config.command_timeout
        action_id = action_request.action_id

        try:
            client = self._get_sila_client()
            command, feature_name, command_name = _resolve_sila_command(
                client, action_request.action_name
            )

            kwargs = dict(action_request.args) if action_request.args else {}

            self.logger.info(
                "Sending SiLA command",
                event_type=EventType.LOG_INFO,
                feature=feature_name,
                command=command_name,
                action_id=action_id,
            )

            result = command(**kwargs)

            if _is_observable_instance(result):
                if await_result:
                    return self._await_observable(
                        result, action_id, feature_name, command_name, effective_timeout
                    )
                # Store for later polling
                with self._commands_lock:
                    self._running_commands[action_id] = (
                        result,
                        feature_name,
                        command_name,
                    )
                return ActionResult(
                    action_id=action_id,
                    status=ActionStatus.RUNNING,
                )

            # Unobservable command — result available immediately
            json_result = _response_to_dict(result)
            json_result, action_files = _extract_bytes_files(json_result, action_id)
            return ActionResult(
                action_id=action_id,
                status=ActionStatus.SUCCEEDED,
                json_result=json_result,
                files=action_files,
            )

        except Exception as e:
            enriched_msg = _format_connection_error(
                e, self._host, self._port, self.config.insecure
            )
            self.logger.log_error(
                enriched_msg,
                event_type=EventType.LOG_ERROR,
                action_id=action_id,
                error=str(e),
                traceback_str=traceback.format_exc(),
            )
            return ActionResult(
                action_id=action_id,
                status=ActionStatus.FAILED,
                errors=[Error(message=enriched_msg, error_type=type(e).__name__)],
            )

    def _await_observable(
        self,
        instance: Any,
        action_id: str,
        feature_name: str,
        command_name: str,
        timeout: float,
    ) -> ActionResult:
        """Block until an observable SiLA command completes by polling instance.done."""
        try:
            start_time = time.time()
            interval = self.config.poll_interval
            while not instance.done:
                if time.time() - start_time > timeout:
                    return ActionResult(
                        action_id=action_id,
                        status=ActionStatus.FAILED,
                        errors=[
                            Error(
                                message=(
                                    f"SiLA observable command '{feature_name}.{command_name}' "
                                    f"timed out after {timeout}s"
                                )
                            )
                        ],
                    )
                time.sleep(interval)
                interval = min(
                    interval * self.config.poll_backoff_factor,
                    self.config.max_poll_interval,
                )

            responses = instance.get_responses()
            json_result = _response_to_dict(responses)
            json_result, action_files = _extract_bytes_files(json_result, action_id)
            return ActionResult(
                action_id=action_id,
                status=ActionStatus.SUCCEEDED,
                json_result=json_result,
                files=action_files,
            )
        except Exception as e:
            return ActionResult(
                action_id=action_id,
                status=ActionStatus.FAILED,
                errors=[Error.from_exception(e)],
            )

    # ------------------------------------------------------------------
    # Action status/result retrieval
    # ------------------------------------------------------------------

    def get_action_status(self, action_id: str) -> ActionStatus:
        """Get the status of an observable SiLA command."""
        with self._commands_lock:
            entry = self._running_commands.get(action_id)

        if entry is None:
            return ActionStatus.UNKNOWN

        instance = entry[0]
        try:
            if instance.done:
                sila_status = str(instance.status).lower()
                if "error" in sila_status:
                    return ActionStatus.FAILED
                return ActionStatus.SUCCEEDED
            return ActionStatus.RUNNING
        except Exception:
            return ActionStatus.UNKNOWN

    def get_action_result(self, action_id: str) -> ActionResult:
        """Get the result of an observable SiLA command."""
        with self._commands_lock:
            entry = self._running_commands.get(action_id)

        if entry is None:
            return ActionResult(
                action_id=action_id,
                status=ActionStatus.UNKNOWN,
                errors=[
                    Error(message=f"No tracked command with action_id '{action_id}'")
                ],
            )

        instance, _feature_name, _command_name = entry

        status = self.get_action_status(action_id)
        if not status.is_terminal:
            return ActionResult(action_id=action_id, status=status)

        try:
            responses = instance.get_responses()
            json_result = _response_to_dict(responses)
            json_result, action_files = _extract_bytes_files(json_result, action_id)

            with self._commands_lock:
                self._running_commands.pop(action_id, None)

            return ActionResult(
                action_id=action_id,
                status=status,
                json_result=json_result,
                files=action_files,
            )
        except Exception as e:
            with self._commands_lock:
                self._running_commands.pop(action_id, None)
            return ActionResult(
                action_id=action_id,
                status=ActionStatus.FAILED,
                errors=[Error.from_exception(e)],
            )

    def await_action_result(
        self, action_id: str, timeout: Optional[float] = None
    ) -> ActionResult:
        """Wait for an observable SiLA command to complete."""
        effective_timeout = timeout or self.config.command_timeout
        start_time = time.time()
        interval = self.config.poll_interval

        while True:
            elapsed = time.time() - start_time
            if elapsed > effective_timeout:
                msg = f"Timed out waiting for SiLA action {action_id} after {effective_timeout}s"
                raise TimeoutError(msg)

            status = self.get_action_status(action_id)
            if status.is_terminal:
                return self.get_action_result(action_id)

            time.sleep(interval)
            interval = min(
                interval * self.config.poll_backoff_factor,
                self.config.max_poll_interval,
            )

    # ------------------------------------------------------------------
    # Server introspection
    # ------------------------------------------------------------------

    def get_status(self) -> NodeStatus:
        """Get the status of the SiLA node."""
        try:
            client = self._get_sila_client()
            # Probe connectivity — this raises if the server is unreachable
            client.SiLAService.ImplementedFeatures.get()

            with self._commands_lock:
                running_ids = set(self._running_commands.keys())

            return NodeStatus(
                busy=len(running_ids) > 0,
                running_actions=running_ids,
            )
        except Exception as e:
            enriched_msg = _format_connection_error(
                e, self._host, self._port, self.config.insecure
            )
            return NodeStatus(
                errored=True,
                disconnected=True,
                errors=[Error(message=enriched_msg, error_type=type(e).__name__)],
            )

    def get_state(self) -> dict[str, Any]:
        """Get the state of the SiLA node by reading all property values.

        Returns a dict mapping "FeatureName.PropertyName" to its current value.
        """
        state: dict[str, Any] = {}
        try:
            client = self._get_sila_client()
            for feature_id in _get_feature_ids(client):
                feature = getattr(client, feature_id, None)
                if feature is None:
                    continue
                for attr_name in dir(feature):
                    if attr_name.startswith("_"):
                        continue
                    attr = getattr(feature, attr_name, None)
                    # Heuristic: SiLA properties have a .get() method but are
                    # not themselves callable, while commands are callable.
                    # This relies on the sila2 SDK's internal type structure;
                    # the try/except below ensures misclassified attributes
                    # just yield None rather than crashing.
                    if attr is not None and hasattr(attr, "get") and not callable(attr):
                        try:
                            value = attr.get()
                            state[f"{feature_id}.{attr_name}"] = _serialize_value(value)
                        except Exception:
                            state[f"{feature_id}.{attr_name}"] = None
        except Exception as e:
            enriched_msg = _format_connection_error(
                e, self._host, self._port, self.config.insecure
            )
            self.logger.warning(
                enriched_msg,
                event_type=EventType.LOG_WARNING,
                error=str(e),
            )
        return state

    def get_info(self) -> NodeInfo:
        """Get information about the SiLA node.

        Introspects the SiLA server's features and commands to build
        ActionDefinition objects.
        """
        client = self._get_sila_client()
        feature_ids = _get_feature_ids(client)

        actions: dict[str, ActionDefinition] = {}
        for feature_id in feature_ids:
            feature = getattr(client, feature_id, None)
            if feature is None:
                continue
            for attr_name in dir(feature):
                if attr_name.startswith("_"):
                    continue
                attr = getattr(feature, attr_name, None)
                if attr is not None and callable(attr):
                    qualified_name = f"{feature_id}.{attr_name}"
                    args = _extract_argument_definitions(attr)
                    is_observable = _is_command_observable(attr)
                    actions[qualified_name] = ActionDefinition(
                        name=qualified_name,
                        description=f"SiLA command {attr_name} from feature {feature_id}",
                        args=args,
                        asynchronous=is_observable,
                    )

        server_name = "SiLA Server"
        with contextlib.suppress(Exception):
            server_name = str(client.SiLAService.ServerName.get())

        return NodeInfo(
            node_name=server_name,
            module_name="sila2",
            node_url=AnyUrl(f"sila://{self._host}:{self._port}"),
            actions=actions,
        )

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the SiLA client connection."""
        with self._sila_lock:
            if self._sila_client is not None:
                if hasattr(self._sila_client, "close"):
                    with contextlib.suppress(Exception):
                        self._sila_client.close()
                self._sila_client = None

        with self._commands_lock:
            self._running_commands.clear()

    @classmethod
    def validate_url(cls, url: AnyUrl) -> bool:
        """Check if a url uses the sila:// scheme."""
        return url.scheme in cls.url_protocols
