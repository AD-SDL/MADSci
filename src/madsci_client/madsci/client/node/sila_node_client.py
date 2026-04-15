"""SiLA2-based node client implementation.

Connects to SiLA2 servers via gRPC using the sila2 Python SDK.
Requires the 'sila' optional dependency: pip install "madsci.client[sila]"
"""

import concurrent.futures
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
from madsci.common.types.action_types import (
    ActionDefinition,
    ActionRequest,
    ActionResult,
    ActionStatus,
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


def _get_feature_ids(client: Any) -> list[str]:
    """Get the list of implemented feature identifiers from a SiLA client."""
    try:
        return list(client.SiLAService.ImplementedFeatures.get())
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
    """Convert a SiLA value to a JSON-serializable form."""
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if isinstance(value, (list, tuple)):
        return [_serialize_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    if hasattr(value, "_fields"):
        return {f: _serialize_value(getattr(value, f)) for f in value._fields}
    return str(value)


def _is_observable_instance(result: Any) -> bool:
    """Check if a SiLA command result is an observable command instance."""
    return hasattr(result, "status") and hasattr(result, "get_responses")


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
        action_files=False,
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

                self._sila_client = SilaClient(self._host, self._port, **kwargs)
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
            return ActionResult(
                action_id=action_id,
                status=ActionStatus.SUCCEEDED,
                json_result=json_result,
            )

        except Exception as e:
            self.logger.log_error(
                "SiLA command failed",
                event_type=EventType.LOG_ERROR,
                action_id=action_id,
                error=str(e),
                traceback_str=traceback.format_exc(),
            )
            return ActionResult(
                action_id=action_id,
                status=ActionStatus.FAILED,
                errors=[Error.from_exception(e)],
            )

    def _await_observable(
        self,
        instance: Any,
        action_id: str,
        feature_name: str,
        command_name: str,
        timeout: float,
    ) -> ActionResult:
        """Block until an observable SiLA command completes."""
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(instance.get_responses)
                responses = future.result(timeout=timeout)

            json_result = _response_to_dict(responses)
            return ActionResult(
                action_id=action_id,
                status=ActionStatus.SUCCEEDED,
                json_result=json_result,
            )
        except concurrent.futures.TimeoutError:
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
            sila_status = str(instance.status).lower()
            if "error" in sila_status:
                return ActionStatus.FAILED
            if "finished" in sila_status:
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

            with self._commands_lock:
                self._running_commands.pop(action_id, None)

            return ActionResult(
                action_id=action_id,
                status=ActionStatus.SUCCEEDED,
                json_result=json_result,
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
            return NodeStatus(
                errored=True,
                disconnected=True,
                errors=[Error.from_exception(e)],
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
                    if attr is not None and hasattr(attr, "get") and not callable(attr):
                        try:
                            value = attr.get()
                            state[f"{feature_id}.{attr_name}"] = _serialize_value(value)
                        except Exception:
                            state[f"{feature_id}.{attr_name}"] = None
        except Exception as e:
            self.logger.warning(
                "Failed to read SiLA node state",
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
                    actions[qualified_name] = ActionDefinition(
                        name=qualified_name,
                        description=f"SiLA command {attr_name} from feature {feature_id}",
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
    def validate_url(cls, url: Any) -> bool:
        """Check if a url uses the sila:// scheme."""
        if hasattr(url, "scheme"):
            return url.scheme in cls.url_protocols
        return str(url).startswith("sila://")
