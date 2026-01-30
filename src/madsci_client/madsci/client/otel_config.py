"""OpenTelemetry configuration for MADSci EventClient.

This module provides OpenTelemetry integration for the EventClient,
including tracing, metrics, and log correlation support.

Example usage:
    from madsci.client.otel_config import OtelManager

    # Initialize OTEL with console exporter (development)
    otel = OtelManager(service_name="my-service", exporter_type="console")
    otel.setup()

    # Get a tracer for creating spans
    tracer = otel.get_tracer("my-module")
    with tracer.start_as_current_span("my-operation"):
        # ... do work ...
        pass

    # Get a meter for recording metrics
    meter = otel.get_meter("my-module")
    counter = meter.create_counter("my.counter")
    counter.add(1)
"""

import logging
from typing import Literal, Optional

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

# Type alias for exporter types
ExporterType = Literal["console", "otlp", "none"]


class OtelManager:
    """Manages OpenTelemetry tracing and metrics configuration.

    This class encapsulates OTEL setup to avoid global state and allow
    for multiple configurations in testing scenarios.

    Attributes:
        service_name: The name of the service for resource identification.
        service_version: The version of the service.
        exporter_type: The type of exporter to use.
        otlp_endpoint: The OTLP collector endpoint (for otlp exporter).

    Example:
        # Development setup with console output
        otel = OtelManager(service_name="my-service", exporter_type="console")
        otel.setup()

        # Production setup with OTLP
        otel = OtelManager(
            service_name="my-service",
            exporter_type="otlp",
            otlp_endpoint="http://otel-collector:4317",
        )
        otel.setup()
    """

    def __init__(
        self,
        service_name: str = "madsci-client",
        service_version: str = "unknown",
        exporter_type: ExporterType = "console",
        otlp_endpoint: Optional[str] = None,
        metric_export_interval_ms: int = 10000,
    ) -> None:
        """Initialize the OtelManager.

        Args:
            service_name: The name of the service for resource identification.
            service_version: The version of the service.
            exporter_type: The type of exporter to use:
                - "console": Print traces/metrics to stdout (development)
                - "otlp": Send to OTLP collector (production)
                - "none": Disable telemetry export
            otlp_endpoint: The OTLP collector endpoint (required if exporter_type="otlp").
            metric_export_interval_ms: Interval in milliseconds for exporting metrics.
        """
        self.service_name = service_name
        self.service_version = service_version
        self.exporter_type = exporter_type
        self.otlp_endpoint = otlp_endpoint
        self.metric_export_interval_ms = metric_export_interval_ms
        self._initialized = False
        self._tracer_provider: Optional[TracerProvider] = None
        self._meter_provider: Optional[MeterProvider] = None
        self._logger = logging.getLogger(__name__)

    def setup(self) -> None:
        """Initialize OpenTelemetry tracing and metrics.

        This method sets up the tracer and meter providers with the
        specified configuration.

        Raises:
            ValueError: If exporter_type is "otlp" but otlp_endpoint is not provided.
        """
        if self._initialized:
            self._logger.warning("OpenTelemetry already initialized, skipping setup")
            return

        # Create resource with service information
        resource = Resource.create(
            {
                "service.name": self.service_name,
                "service.version": self.service_version,
            }
        )

        # Set up tracing
        self._tracer_provider = TracerProvider(resource=resource)
        self._setup_trace_exporter()
        trace.set_tracer_provider(self._tracer_provider)

        # Set up metrics
        self._setup_meter_provider(resource)
        if self._meter_provider is not None:
            metrics.set_meter_provider(self._meter_provider)

        self._initialized = True
        self._logger.info(
            f"OpenTelemetry initialized: service={self.service_name}, "
            f"exporter={self.exporter_type}"
        )

    def _setup_trace_exporter(self) -> None:
        """Set up the trace exporter based on configuration."""
        if self._tracer_provider is None:
            return
        if self.exporter_type == "console":
            span_processor = BatchSpanProcessor(ConsoleSpanExporter())
            self._tracer_provider.add_span_processor(span_processor)
        elif self.exporter_type == "otlp":
            self._setup_otlp_trace_exporter()
        # exporter_type == "none": no span processor added

    def _setup_otlp_trace_exporter(self) -> None:
        """Set up OTLP trace exporter."""
        if self._tracer_provider is None:
            return
        if not self.otlp_endpoint:
            raise ValueError("otlp_endpoint is required when exporter_type is 'otlp'")
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # noqa: PLC0415
                OTLPSpanExporter,
            )

            span_processor = BatchSpanProcessor(
                OTLPSpanExporter(endpoint=self.otlp_endpoint)
            )
            self._tracer_provider.add_span_processor(span_processor)
        except ImportError as e:
            raise ImportError(
                "OTLP exporter requires 'opentelemetry-exporter-otlp' package. "
                "Install with: pip install opentelemetry-exporter-otlp"
            ) from e

    def _setup_meter_provider(self, resource: Resource) -> None:
        """Set up the meter provider based on configuration."""
        if self.exporter_type == "console":
            metric_reader = PeriodicExportingMetricReader(
                ConsoleMetricExporter(),
                export_interval_millis=self.metric_export_interval_ms,
            )
            self._meter_provider = MeterProvider(
                resource=resource, metric_readers=[metric_reader]
            )
        elif self.exporter_type == "otlp":
            self._setup_otlp_meter_provider(resource)
        else:
            # No-op meter provider
            self._meter_provider = MeterProvider(resource=resource)

    def _setup_otlp_meter_provider(self, resource: Resource) -> None:
        """Set up OTLP meter provider."""
        try:
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (  # noqa: PLC0415
                OTLPMetricExporter,
            )

            metric_reader = PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=self.otlp_endpoint),
                export_interval_millis=self.metric_export_interval_ms,
            )
            self._meter_provider = MeterProvider(
                resource=resource, metric_readers=[metric_reader]
            )
        except ImportError as e:
            raise ImportError(
                "OTLP exporter requires 'opentelemetry-exporter-otlp' package. "
                "Install with: pip install opentelemetry-exporter-otlp"
            ) from e

    def get_tracer(self, name: str) -> trace.Tracer:
        """Get a tracer for creating spans.

        Args:
            name: The name of the tracer (typically module name).

        Returns:
            A Tracer instance for creating spans.
        """
        return trace.get_tracer(name)

    def get_meter(self, name: str) -> metrics.Meter:
        """Get a meter for recording metrics.

        Args:
            name: The name of the meter (typically module name).

        Returns:
            A Meter instance for recording metrics.
        """
        return metrics.get_meter(name)

    def shutdown(self) -> None:
        """Shutdown OpenTelemetry providers and flush pending telemetry.

        This should be called during application shutdown to ensure
        all pending spans and metrics are exported.
        """
        if self._tracer_provider:
            self._tracer_provider.shutdown()
        if self._meter_provider:
            self._meter_provider.shutdown()

        self._initialized = False
        self._tracer_provider = None
        self._meter_provider = None


# Module-level singleton for convenience
_default_manager: Optional[OtelManager] = None


def setup_otel(
    service_name: str = "madsci-client",
    service_version: str = "unknown",
    exporter_type: ExporterType = "console",
    otlp_endpoint: Optional[str] = None,
    metric_export_interval_ms: int = 10000,
) -> OtelManager:
    """Initialize OpenTelemetry tracing and metrics using a default manager.

    This is a convenience function that creates and configures a default
    OtelManager instance. For more control, create an OtelManager directly.

    Args:
        service_name: The name of the service for resource identification.
        service_version: The version of the service.
        exporter_type: The type of exporter to use.
        otlp_endpoint: The OTLP collector endpoint (required if exporter_type="otlp").
        metric_export_interval_ms: Interval in milliseconds for exporting metrics.

    Returns:
        The configured OtelManager instance.
    """
    global _default_manager  # noqa: PLW0603
    _default_manager = OtelManager(
        service_name=service_name,
        service_version=service_version,
        exporter_type=exporter_type,
        otlp_endpoint=otlp_endpoint,
        metric_export_interval_ms=metric_export_interval_ms,
    )
    _default_manager.setup()
    return _default_manager


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer for creating spans.

    Args:
        name: The name of the tracer (typically module name).

    Returns:
        A Tracer instance for creating spans.

    Example:
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("my-operation") as span:
            span.set_attribute("key", "value")
    """
    return trace.get_tracer(name)


def get_meter(name: str) -> metrics.Meter:
    """Get a meter for recording metrics.

    Args:
        name: The name of the meter (typically module name).

    Returns:
        A Meter instance for recording metrics.

    Example:
        meter = get_meter(__name__)
        counter = meter.create_counter("my.events.count")
        counter.add(1, {"event.type": "info"})
    """
    return metrics.get_meter(name)


def get_current_trace_context() -> dict[str, Optional[str]]:
    """Get the current trace context for log correlation.

    Returns:
        A dictionary containing trace_id and span_id in hex format,
        or None values if no active span exists.

    Example:
        ctx = get_current_trace_context()
        log_entry["trace_id"] = ctx["trace_id"]
        log_entry["span_id"] = ctx["span_id"]
    """
    span = trace.get_current_span()
    if not span.is_recording():
        return {"trace_id": None, "span_id": None}

    ctx = span.get_span_context()
    return {
        "trace_id": format(ctx.trace_id, "032x"),
        "span_id": format(ctx.span_id, "016x"),
    }


def shutdown_otel() -> None:
    """Shutdown the default OpenTelemetry manager and flush pending telemetry.

    This should be called during application shutdown to ensure
    all pending spans and metrics are exported.
    """
    global _default_manager  # noqa: PLW0603
    if _default_manager:
        _default_manager.shutdown()
        _default_manager = None


def reset_otel() -> None:
    """Reset OpenTelemetry state for testing scenarios.

    This function shuts down any existing OTEL configuration and clears
    the global state, allowing setup_otel() to be called again with
    different configuration.

    This is primarily useful in test fixtures to ensure clean state
    between tests.

    Example:
        @pytest.fixture(autouse=True)
        def reset_otel_between_tests():
            yield
            reset_otel()
    """
    shutdown_otel()
