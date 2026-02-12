"""Canonical OpenTelemetry bootstrap for MADSci.

This module centralizes OpenTelemetry SDK/provider setup so MADSci services and
clients share one consistent initialization behavior.
"""

import contextlib
import logging
from dataclasses import dataclass
from typing import Any, Literal, Optional

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import (
    BatchLogRecordProcessor,
    ConsoleLogRecordExporter,
    SimpleLogRecordProcessor,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    InMemoryMetricReader,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

ExporterType = Literal["console", "otlp", "none"]
OtlpProtocol = Literal["grpc", "http"]


@dataclass(frozen=True)
class OtelBootstrapConfig:
    """Settings for `configure_otel`."""

    enabled: bool
    service_name: str
    service_version: str = "unknown"
    exporter: ExporterType = "console"
    otlp_endpoint: Optional[str] = None
    otlp_protocol: OtlpProtocol = "grpc"
    metric_export_interval_ms: int = 10_000
    test_mode: bool = False


@dataclass
class OtelRuntime:
    """Runtime handles returned by `configure_otel`."""

    enabled: bool
    tracer_provider: Optional[TracerProvider] = None
    meter_provider: Optional[MeterProvider] = None
    logger_provider: Optional[LoggerProvider] = None
    otel_log_handler: Optional[logging.Handler] = None
    in_memory_span_exporter: Optional[InMemorySpanExporter] = None
    in_memory_metric_reader: Optional[InMemoryMetricReader] = None

    @property
    def tracer(self) -> trace.Tracer:
        """Return a tracer bound to this module."""
        return trace.get_tracer(__name__)

    @property
    def meter(self) -> metrics.Meter:
        """Return a meter bound to this module."""
        return metrics.get_meter(__name__)


_logger = logging.getLogger(__name__)
_configured: bool = False
_runtime: Optional[OtelRuntime] = None


def _normalize_otlp_endpoint(endpoint: Optional[str]) -> Optional[str]:
    if endpoint is None:
        return None
    if not endpoint.startswith(("http://", "https://")):
        raise ValueError("OTLP endpoint must start with http:// or https://")
    return endpoint.rstrip("/")


def configure_otel(config: OtelBootstrapConfig) -> OtelRuntime:
    """Configure OpenTelemetry SDK providers.

    This function is idempotent: the first successful configuration wins.
    """
    global _configured, _runtime  # noqa: PLW0603

    if not config.enabled:
        _runtime = OtelRuntime(enabled=False)
        return _runtime

    if config.test_mode and _configured and _runtime is not None:
        # Tests may request a fresh in-memory exporter/reader per test.
        _configured = False
        _runtime = None

    if _configured and _runtime is not None:
        return _runtime

    otlp_endpoint = _normalize_otlp_endpoint(config.otlp_endpoint)

    resource = Resource.create(
        {
            "service.name": config.service_name,
            "service.version": config.service_version,
        }
    )

    tracer_provider, in_memory_span_exporter = _configure_tracing(
        config=config, resource=resource, otlp_endpoint=otlp_endpoint
    )
    trace.set_tracer_provider(tracer_provider)

    meter_provider, in_memory_metric_reader = _configure_metrics(
        config=config, resource=resource, otlp_endpoint=otlp_endpoint
    )
    metrics.set_meter_provider(meter_provider)

    logger_provider, otel_log_handler = _configure_logging(
        config=config, resource=resource, otlp_endpoint=otlp_endpoint
    )

    _runtime = OtelRuntime(
        enabled=True,
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
        logger_provider=logger_provider,
        otel_log_handler=otel_log_handler,
        in_memory_span_exporter=in_memory_span_exporter,
        in_memory_metric_reader=in_memory_metric_reader,
    )
    _configured = True
    _logger.info(
        "OpenTelemetry configured",
        extra={
            "service.name": config.service_name,
            "otel.exporter": config.exporter,
            "otel.protocol": config.otlp_protocol,
            "otel.test_mode": config.test_mode,
        },
    )
    return _runtime


def _configure_tracing(
    *,
    config: OtelBootstrapConfig,
    resource: Resource,
    otlp_endpoint: Optional[str],
) -> tuple[TracerProvider, Optional[InMemorySpanExporter]]:
    tracer_provider = TracerProvider(resource=resource)

    if config.test_mode:
        exporter = InMemorySpanExporter()
        tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
        return tracer_provider, exporter

    if config.exporter == "console":
        tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        return tracer_provider, None

    if config.exporter == "otlp":
        if not otlp_endpoint:
            raise ValueError("otlp_endpoint is required when exporter='otlp'")
        if config.otlp_protocol == "grpc":
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # noqa: PLC0415
                OTLPSpanExporter,
            )

            tracer_provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
            )
            return tracer_provider, None

        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # noqa: PLC0415
            OTLPSpanExporter,
        )

        tracer_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
        )
        return tracer_provider, None

    return tracer_provider, None


def _configure_metrics(
    *,
    config: OtelBootstrapConfig,
    resource: Resource,
    otlp_endpoint: Optional[str],
) -> tuple[MeterProvider, Optional[InMemoryMetricReader]]:
    if config.test_mode:
        reader = InMemoryMetricReader()
        return MeterProvider(resource=resource, metric_readers=[reader]), reader

    if config.exporter == "console":
        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[
                PeriodicExportingMetricReader(
                    ConsoleMetricExporter(),
                    export_interval_millis=config.metric_export_interval_ms,
                )
            ],
        )
        return meter_provider, None

    if config.exporter == "otlp":
        if not otlp_endpoint:
            raise ValueError("otlp_endpoint is required when exporter='otlp'")
        if config.otlp_protocol == "grpc":
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (  # noqa: PLC0415
                OTLPMetricExporter,
            )

            meter_provider = MeterProvider(
                resource=resource,
                metric_readers=[
                    PeriodicExportingMetricReader(
                        OTLPMetricExporter(endpoint=otlp_endpoint),
                        export_interval_millis=config.metric_export_interval_ms,
                    )
                ],
            )
            return meter_provider, None

        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (  # noqa: PLC0415
            OTLPMetricExporter,
        )

        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[
                PeriodicExportingMetricReader(
                    OTLPMetricExporter(endpoint=otlp_endpoint),
                    export_interval_millis=config.metric_export_interval_ms,
                )
            ],
        )
        return meter_provider, None

    return MeterProvider(resource=resource), None


def _configure_logging(
    *,
    config: OtelBootstrapConfig,
    resource: Resource,
    otlp_endpoint: Optional[str],
) -> tuple[LoggerProvider, logging.Handler]:
    """Configure OTEL LoggerProvider with appropriate exporter.

    Returns the LoggerProvider and a logging.Handler that bridges stdlib
    logging to OTEL log records.
    """
    logger_provider = LoggerProvider(resource=resource)

    if config.test_mode:
        # For tests, use a simple processor with console exporter for visibility
        logger_provider.add_log_record_processor(
            SimpleLogRecordProcessor(ConsoleLogRecordExporter())
        )
        set_logger_provider(logger_provider)
        handler = LoggingHandler(logger_provider=logger_provider)
        return logger_provider, handler

    if config.exporter == "console":
        logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(ConsoleLogRecordExporter())
        )
        set_logger_provider(logger_provider)
        handler = LoggingHandler(logger_provider=logger_provider)
        return logger_provider, handler

    if config.exporter == "otlp":
        if not otlp_endpoint:
            raise ValueError("otlp_endpoint is required when exporter='otlp'")
        if config.otlp_protocol == "grpc":
            from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (  # noqa: PLC0415
                OTLPLogExporter,
            )

            logger_provider.add_log_record_processor(
                BatchLogRecordProcessor(OTLPLogExporter(endpoint=otlp_endpoint))
            )
        else:
            from opentelemetry.exporter.otlp.proto.http._log_exporter import (  # noqa: PLC0415
                OTLPLogExporter,
            )

            logger_provider.add_log_record_processor(
                BatchLogRecordProcessor(OTLPLogExporter(endpoint=otlp_endpoint))
            )

        set_logger_provider(logger_provider)
        handler = LoggingHandler(logger_provider=logger_provider)
        return logger_provider, handler

    # exporter == "none" - no exporter, but still provide handler for trace context
    set_logger_provider(logger_provider)
    handler = LoggingHandler(logger_provider=logger_provider)
    return logger_provider, handler


def collect_metrics(runtime: OtelRuntime) -> Optional[Any]:
    """Force a synchronous metrics collection for test assertions.

    OpenTelemetry's metrics SDK is pull-based; in tests we want deterministic
    reads without background threads.
    """

    if runtime.in_memory_metric_reader is None:
        return None

    # The in-memory reader captures metrics on explicit collect.
    with contextlib.suppress(Exception):
        runtime.in_memory_metric_reader.collect()

    data = runtime.in_memory_metric_reader.get_metrics_data()
    if data is not None:
        return data

    # Best-effort flush + collect for SDK versions that buffer observations.
    with contextlib.suppress(Exception):
        runtime.meter_provider.force_flush()  # type: ignore[union-attr]
    with contextlib.suppress(Exception):
        runtime.in_memory_metric_reader.collect()
    return runtime.in_memory_metric_reader.get_metrics_data()


def get_otel_runtime() -> Optional[OtelRuntime]:
    """Return the process-global OTEL runtime when configured."""

    return _runtime


def current_trace_context() -> dict[str, Optional[str]]:
    """Return the active trace/span ids for log correlation."""
    span = trace.get_current_span()
    if not span.is_recording():
        return {"trace_id": None, "span_id": None}
    ctx = span.get_span_context()
    return {
        "trace_id": format(ctx.trace_id, "032x"),
        "span_id": format(ctx.span_id, "016x"),
    }
