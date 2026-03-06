import re

import pytest
from madsci.client.event_client import EventClient
from madsci.common.otel import OtelBootstrapConfig, configure_otel
from madsci.common.types.event_types import Event, EventClientConfig, EventLogLevel

TRACE_ID_RE = re.compile(r"^[0-9a-f]{32}$")
SPAN_ID_RE = re.compile(r"^[0-9a-f]{16}$")


@pytest.fixture
def otel_test_runtime():
    # Each test gets a deterministic, in-memory OTEL runtime.
    # configure_otel() will reset prior config in test_mode.
    return configure_otel(
        OtelBootstrapConfig(
            enabled=True,
            service_name="madsci.test",
            exporter="none",
            test_mode=True,
        )
    )


@pytest.fixture
def otel_test_client(otel_test_runtime):
    # Ensure client creation happens after OTEL test_mode bootstrap so it reuses
    # the in-memory meter reader.
    _ = otel_test_runtime
    return EventClient(
        config=EventClientConfig(
            event_server_url=None,
            otel_enabled=True,
            otel_exporter="none",
        )
    )


class TestEventClientOtelIntegration:
    def test_otel_disabled_by_default(self) -> None:
        client = EventClient(config=EventClientConfig(event_server_url=None))
        assert client.config.otel_enabled is False
        assert client._otel_runtime is None

    def test_otel_enabled_initializes_runtime(self) -> None:
        client = EventClient(
            config=EventClientConfig(
                event_server_url=None,
                otel_enabled=True,
                otel_exporter="none",
            )
        )
        assert client._otel_runtime is not None
        assert client._otel_runtime.enabled is True

    def test_trace_context_injected_into_event(self, otel_test_client) -> None:
        client = otel_test_client
        assert client._otel_runtime is not None

        tracer = client._otel_runtime.tracer
        with tracer.start_as_current_span("test-span"):
            captured: list[Event] = []

            def _capture(event: Event, retrying: bool = False) -> None:  # noqa: ARG001
                captured.append(event)

            client._send_event_to_event_server = _capture  # type: ignore[method-assign]

            # _maybe_send_to_server short-circuits when no event server is configured.
            # Force an event server so Event creation + send path runs.
            client.event_server = "http://localhost:8001"  # type: ignore[assignment]
            client._maybe_send_to_server("hello", level=EventLogLevel.INFO, foo="bar")

        assert len(captured) == 1
        assert captured[0].trace_id is not None
        assert captured[0].span_id is not None
        assert TRACE_ID_RE.match(captured[0].trace_id)
        assert SPAN_ID_RE.match(captured[0].span_id)

    def test_context_propagated_in_http_headers(self, otel_test_client) -> None:
        client = otel_test_client
        client.event_server = "http://localhost:8001"  # type: ignore[assignment]

        captured_headers: dict[str, str] = {}

        def fake_post(*_args, **kwargs):
            captured_headers.update(kwargs.get("headers") or {})

            class Resp:
                ok = True

            return Resp()

        client.session.post = fake_post  # type: ignore[method-assign]
        assert client._otel_runtime is not None
        with client._otel_runtime.tracer.start_as_current_span("test-span"):
            client._send_event_to_event_server(Event(event_data={}))

        # The exact propagation header depends on propagator config.
        assert any(
            k.lower() in {"traceparent", "b3", "x-b3-traceid"} for k in captured_headers
        )

    def test_metrics_instruments_created(self, otel_test_client) -> None:
        client = otel_test_client

        assert client._otel_runtime is not None
        assert client._otel_event_counter is not None
        assert client._otel_send_latency_histogram is not None
        assert client._otel_buffer_size_gauge is not None
        assert client._otel_retry_counter is not None

    # Metrics collection assertions are covered by
    # test_event_client_otel_metrics_subprocess.py to avoid process-global OTEL
    # provider conflicts.
