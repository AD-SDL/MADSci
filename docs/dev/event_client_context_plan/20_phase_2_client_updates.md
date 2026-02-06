# Phase 2: Client Updates

**Estimated Effort:** Medium (3-5 days)
**Breaking Changes:** None (backward compatible)
**Prerequisites:** Phase 1 complete

## Goals

- Update `MadsciClientMixin` to be context-aware
- Update `RestNodeClient` to use context
- Update other clients to participate in context
- Maintain full backward compatibility

## 2.0 Implementation Principles

### 2.0.1 Resolution Order

All client `event_client` properties should follow this resolution order:

1. **Explicitly set client** (`_event_client` instance attribute)
2. **Context client** (via `get_event_client()` with component binding)
3. **New client from config** (legacy fallback behavior)

### 2.0.2 Component Context

Each component should add its own identifying context when obtaining a client:

```python
logger = get_event_client(component_type="RestNodeClient", node_url=str(self.url))
```

This ensures logs can be filtered by component even when sharing a parent context.

### 2.0.3 Backward Compatibility

All existing patterns must continue to work:

```python
# Direct instantiation (still works)
client = EventClient(name="my_client")

# Injection (still works)
resource_client = ResourceClient(event_client=my_event_client)

# Mixin usage (still works, now context-aware)
class MyComponent(MadsciClientMixin):
    REQUIRED_CLIENTS = ["event", "resource"]
```

## 2.1 Test Specifications (TDD)

Create `src/madsci_client/tests/test_client_context_integration.py`.

**Note:** These tests build on the Phase 1 tests in the same directory (`test_event_client_context.py`).

```python
"""Tests for client context integration."""

import pytest
from unittest.mock import Mock, patch


class TestMadsciClientMixinContextAwareness:
    """Test MadsciClientMixin context-aware behavior."""

    def test_event_client_uses_context_when_available(self):
        """Test that event_client property uses context when available."""
        from madsci.client.client_mixin import MadsciClientMixin
        from madsci.common.context import event_client_context

        class TestComponent(MadsciClientMixin):
            pass

        with event_client_context(name="test", test_id="t-123") as ctx_client:
            component = TestComponent()
            # Should use context client (or bound version)
            logger = component.event_client

            # Should have the test_id in bound context
            assert "test_id" in logger._bound_context or logger is ctx_client

    def test_event_client_falls_back_without_context(self):
        """Test that event_client creates new client when no context."""
        from madsci.client.client_mixin import MadsciClientMixin
        from madsci.common.context import _event_client_context

        # Ensure no context
        _event_client_context.set(None)

        class TestComponent(MadsciClientMixin):
            name = "test_component"

        component = TestComponent()
        logger = component.event_client

        # Should have created a new client
        assert logger is not None
        assert logger.name == "test_component"

    def test_explicit_client_takes_precedence(self):
        """Test that explicitly set client takes precedence over context."""
        from madsci.client.client_mixin import MadsciClientMixin
        from madsci.client.event_client import EventClient
        from madsci.common.context import event_client_context

        explicit_client = EventClient(name="explicit")

        class TestComponent(MadsciClientMixin):
            pass

        with event_client_context(name="context"):
            component = TestComponent()
            component.event_client = explicit_client

            assert component.event_client is explicit_client

    def test_injected_client_via_setup_clients(self):
        """Test that clients injected via setup_clients are used."""
        from madsci.client.client_mixin import MadsciClientMixin
        from madsci.client.event_client import EventClient
        from madsci.common.context import event_client_context

        injected_client = EventClient(name="injected")

        class TestComponent(MadsciClientMixin):
            REQUIRED_CLIENTS = ["event"]

        with event_client_context(name="context"):
            component = TestComponent()
            component.setup_clients(event_client=injected_client)

            assert component.event_client is injected_client

    def test_component_context_added_to_logs(self):
        """Test that component-specific context is added."""
        from madsci.client.client_mixin import MadsciClientMixin
        from madsci.common.context import event_client_context

        class TestComponent(MadsciClientMixin):
            name = "my_component"

            def _get_component_context(self):
                return {
                    "component_type": self.__class__.__name__,
                    "component_name": self.name,
                }

        with event_client_context(name="test") as ctx_client:
            component = TestComponent()
            logger = component.event_client

            # Should have component context bound
            assert "component_type" in logger._bound_context
            assert logger._bound_context["component_type"] == "TestComponent"

    def test_other_clients_share_event_client_from_context(self):
        """Test that resource/workcell/location clients use context event_client."""
        from madsci.client.client_mixin import MadsciClientMixin
        from madsci.common.context import event_client_context

        class TestComponent(MadsciClientMixin):
            REQUIRED_CLIENTS = ["event", "resource"]
            resource_server_url = "http://localhost:8003/"

        with event_client_context(name="test", test_id="t-123"):
            component = TestComponent()
            component.setup_clients()

            # Resource client should have received the context-aware event_client
            # (This test may need adjustment based on actual ResourceClient implementation)
            assert component._event_client is not None


class TestRestNodeClientContextAwareness:
    """Test RestNodeClient context-aware behavior."""

    def test_uses_context_when_available(self):
        """Test that RestNodeClient uses context EventClient."""
        from madsci.client.node.rest_node_client import RestNodeClient
        from madsci.common.context import event_client_context
        from pydantic import AnyUrl

        with event_client_context(name="workflow", workflow_id="wf-123") as ctx_client:
            client = RestNodeClient(url=AnyUrl("http://localhost:8000/"))

            # Logger should include workflow context
            assert "workflow_id" in client.logger._bound_context or \
                   client.logger._bound_context.get("node_url") is not None

    def test_uses_injected_client_when_provided(self):
        """Test that RestNodeClient uses injected EventClient."""
        from madsci.client.node.rest_node_client import RestNodeClient
        from madsci.client.event_client import EventClient
        from madsci.common.context import event_client_context
        from pydantic import AnyUrl

        injected = EventClient(name="injected")

        with event_client_context(name="context"):
            client = RestNodeClient(
                url=AnyUrl("http://localhost:8000/"),
                event_client=injected,
            )

            assert client.logger is injected

    def test_creates_new_client_without_context(self):
        """Test that RestNodeClient creates client when no context."""
        from madsci.client.node.rest_node_client import RestNodeClient
        from madsci.common.context import _event_client_context
        from pydantic import AnyUrl

        _event_client_context.set(None)

        client = RestNodeClient(url=AnyUrl("http://localhost:8000/"))

        assert client.logger is not None

    def test_multiple_instances_share_context_client(self):
        """Test that multiple RestNodeClient instances share context resources."""
        from madsci.client.node.rest_node_client import RestNodeClient
        from madsci.common.context import event_client_context
        from pydantic import AnyUrl

        with event_client_context(name="workflow") as ctx_client:
            client1 = RestNodeClient(url=AnyUrl("http://node1:8000/"))
            client2 = RestNodeClient(url=AnyUrl("http://node2:8000/"))

            # Both should derive from the same context client
            # (sharing underlying resources like log files)
            # The exact assertion depends on implementation,
            # but both loggers should have the workflow context
            assert client1.logger is not None
            assert client2.logger is not None


class TestClientContextPropagation:
    """Test context propagation through client operations."""

    def test_context_propagates_through_nested_clients(self):
        """Test that context propagates through nested client creation."""
        from madsci.client.client_mixin import MadsciClientMixin
        from madsci.common.context import event_client_context, get_event_client

        class OuterComponent(MadsciClientMixin):
            REQUIRED_CLIENTS = ["event"]

            def create_inner(self):
                return InnerComponent()

        class InnerComponent(MadsciClientMixin):
            REQUIRED_CLIENTS = ["event"]

        with event_client_context(name="outer", outer_id="o-123"):
            outer = OuterComponent()
            outer.setup_clients()

            inner = outer.create_inner()
            inner.setup_clients()

            # Inner should have inherited outer context
            assert "outer_id" in inner.event_client._bound_context or \
                   inner.event_client._bound_context.get("component_type") is not None

    def test_context_with_experiment_workflow_node_hierarchy(self):
        """Test realistic experiment -> workflow -> node hierarchy."""
        from madsci.common.context import event_client_context, get_event_client

        logs = []

        with event_client_context(name="experiment", experiment_id="exp-123") as exp_logger:
            logs.append(("experiment", exp_logger._bound_context.copy()))

            with event_client_context(name="workflow", workflow_id="wf-456") as wf_logger:
                logs.append(("workflow", wf_logger._bound_context.copy()))

                with event_client_context(name="step", step_id="step-1") as step_logger:
                    logs.append(("step", step_logger._bound_context.copy()))

        # Verify hierarchy accumulation
        assert logs[0][1].get("experiment_id") == "exp-123"

        assert logs[1][1].get("experiment_id") == "exp-123"
        assert logs[1][1].get("workflow_id") == "wf-456"

        assert logs[2][1].get("experiment_id") == "exp-123"
        assert logs[2][1].get("workflow_id") == "wf-456"
        assert logs[2][1].get("step_id") == "step-1"
```

## 2.2 Implementation Tasks

### 2.2.1 Update MadsciClientMixin

Update `src/madsci_client/madsci/client/client_mixin.py`.

**Current implementation reference** (as of Feb 2026):
- `event_client` property is at lines 210-225
- `_create_event_client()` is at lines 227-250
- `_event_client` attribute is at line 77
- `event_client_config` and `event_server_url` are at lines 87-88

**Changes required:**

```python
# Add import at top (after existing imports)
from madsci.common.context import get_event_client, has_event_client_context


# Update the event_client property (replace lines 210-225)
@property
def event_client(self) -> EventClient:
    """
    Get or create the EventClient instance.

    Resolution order:
    1. Explicitly set client (_event_client)
    2. Context client with component binding (if context exists)
    3. New client from config (legacy fallback)

    Returns:
        EventClient: The event client for logging and event management
    """
    if self._event_client is not None:
        return self._event_client

    # Try to use context if available
    if has_event_client_context():
        component_context = self._get_component_context()
        # Get from context with component binding
        # Don't cache this - let context handle lifecycle
        return get_event_client(**component_context)

    # No context - create and cache new client (legacy behavior)
    self._event_client = self._create_event_client()
    return self._event_client

@event_client.setter
def event_client(self, client: EventClient) -> None:
    """Set the EventClient instance explicitly."""
    self._event_client = client


# Add new method _get_component_context() after event_client property
def _get_component_context(self) -> dict[str, Any]:
    """
    Get component-specific context to bind to the EventClient.

    Override in subclasses to add specific context.

    Returns:
        Dictionary of context key-value pairs.

    Example:
        def _get_component_context(self) -> dict[str, Any]:
            return {
                "component_type": "MyComponent",
                "custom_field": self.custom_value,
            }
    """
    context: dict[str, Any] = {}
    if hasattr(self, "name") and self.name:
        context["component_name"] = self.name
    if hasattr(self, "__class__"):
        context["component_type"] = self.__class__.__name__
    return context


# Update _create_event_client() to bind component context (replace lines 227-250)
def _create_event_client(self) -> EventClient:
    """
    Factory method for creating EventClient (legacy fallback).

    This is called when no context is available and no explicit
    client has been set.

    Returns:
        EventClient: A new EventClient instance
    """
    # Use explicit config if provided
    if self.event_client_config is not None:
        return EventClient(config=self.event_client_config)

    # Build config from individual settings
    kwargs: dict[str, Any] = {}

    # Check for event_server_url override
    if hasattr(self, "event_server_url") and self.event_server_url is not None:
        kwargs["event_server_url"] = self.event_server_url

    # Check for name override
    if hasattr(self, "name") and self.name:
        kwargs["name"] = self.name

    # Create client and bind component context
    client = EventClient(**kwargs)
    component_context = self._get_component_context()
    if component_context:
        client = client.bind(**component_context)

    return client
```

**Note:** The existing `_create_event_client()` already handles `event_client_config`, `event_server_url`, and `name`. The changes add context-awareness and component binding.

### 2.2.2 Update RestNodeClient

Update `src/madsci_client/madsci/client/node/rest_node_client.py`.

**Current implementation reference** (as of Feb 2026):
- Class defined at line 59
- `__init__` at lines 82-95
- Current signature: `def __init__(self, url: AnyUrl, config: Optional[RestNodeClientConfig] = None)`
- Logger created at line 93: `self.logger = EventClient()`

**Changes required:**

```python
# Add import at top (with existing imports)
from madsci.common.context import get_event_client
from madsci.client.event_client import EventClient  # May already be imported


# Update __init__ signature and body (replace lines 82-95)
def __init__(
    self,
    url: AnyUrl,
    config: Optional[RestNodeClientConfig] = None,
    event_client: Optional[EventClient] = None,  # NEW PARAMETER
) -> "RestNodeClient":
    """
    Initialize the client.

    Args:
        url: The URL of the node to connect to.
        config: Client configuration for retry and timeout settings.
               If not provided, uses default RestNodeClientConfig.
        event_client: Optional EventClient to use for logging.
                     If not provided, uses context client or creates new.
    """
    super().__init__(url)

    # Use injected client, context client, or create new
    if event_client is not None:
        self.logger = event_client
    else:
        self.logger = get_event_client(
            node_url=str(url),
            component_type="RestNodeClient",
        )

    self.config = config if config is not None else RestNodeClientConfig()
    self.session = create_http_session(config=self.config)
```

**Key change:** Replace `self.logger = EventClient()` with context-aware client acquisition.

### 2.2.3 Update Other Clients

Apply similar pattern to other clients that create EventClients:

**ResourceClient** (`src/madsci_client/madsci/client/resource_client.py`):
```python
def __init__(
    self,
    resource_server_url: Optional[AnyUrl] = None,
    event_client: Optional[EventClient] = None,
    # ... other params
):
    # ... existing setup ...

    if event_client is not None:
        self.logger = event_client
    else:
        self.logger = get_event_client(
            component_type="ResourceClient",
            resource_server=str(self.resource_server_url) if self.resource_server_url else None,
        )
```

**WorkcellClient** (`src/madsci_client/madsci/client/workcell_client.py`):
```python
def __init__(
    self,
    workcell_server_url: Optional[AnyUrl] = None,
    event_client: Optional[EventClient] = None,
    # ... other params
):
    # ... existing setup ...

    if event_client is not None:
        self.logger = event_client
    else:
        self.logger = get_event_client(
            component_type="WorkcellClient",
            workcell_server=str(self.workcell_server_url) if self.workcell_server_url else None,
        )
```

**LocationClient** (`src/madsci_client/madsci/client/location_client.py`):
```python
def __init__(
    self,
    location_server_url: Optional[AnyUrl] = None,
    event_client: Optional[EventClient] = None,
    # ... other params
):
    # ... existing setup ...

    if event_client is not None:
        self.logger = event_client
    else:
        self.logger = get_event_client(
            component_type="LocationClient",
            location_server=str(self.location_server_url) if self.location_server_url else None,
        )
```

### 2.2.4 Update AbstractNodeClient (if applicable)

If `AbstractNodeClient` has logging, update it similarly:

```python
class AbstractNodeClient(ABC):
    def __init__(self, url: AnyUrl, event_client: Optional[EventClient] = None):
        self.url = url
        self._event_client = event_client

    @property
    def logger(self) -> EventClient:
        if self._event_client is None:
            self._event_client = get_event_client(
                component_type=self.__class__.__name__,
                node_url=str(self.url),
            )
        return self._event_client

    @logger.setter
    def logger(self, client: EventClient) -> None:
        self._event_client = client
```

## 2.3 Acceptance Criteria

- [ ] `MadsciClientMixin.event_client` uses context when available
- [ ] `MadsciClientMixin.event_client` falls back to legacy behavior without context
- [ ] `MadsciClientMixin._get_component_context()` provides component-specific context
- [ ] Explicit client setting takes precedence over context
- [ ] Injected clients via `setup_clients()` take precedence
- [ ] `RestNodeClient` accepts optional `event_client` parameter
- [ ] `RestNodeClient` uses context when no explicit client provided
- [ ] `ResourceClient`, `WorkcellClient`, `LocationClient` updated similarly
- [ ] Other clients share event_client when injected via mixin
- [ ] All existing tests continue to pass
- [ ] New context integration tests pass
- [ ] No breaking changes to existing APIs

## 2.4 Migration Notes

### For Developers Using These Clients

**No changes required** for existing code. The updates are backward compatible.

**To opt-in to context propagation**, wrap your entry point:

```python
# Before (works, but each client creates its own EventClient)
resource_client = ResourceClient()
workcell_client = WorkcellClient()

# After (clients share context and hierarchical logging)
with event_client_context(name="my_app", app_id="app-123"):
    resource_client = ResourceClient()   # Uses context
    workcell_client = WorkcellClient()   # Uses same context
```

### For Developers Extending MadsciClientMixin

Override `_get_component_context()` to add custom context:

```python
class MyCustomComponent(MadsciClientMixin):
    def __init__(self, custom_id: str):
        self.custom_id = custom_id

    def _get_component_context(self) -> dict[str, Any]:
        base = super()._get_component_context()
        base["custom_id"] = self.custom_id
        return base
```
