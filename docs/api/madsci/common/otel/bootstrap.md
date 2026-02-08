Module madsci.common.otel.bootstrap
===================================
Canonical OpenTelemetry bootstrap for MADSci.

This module centralizes OpenTelemetry SDK/provider setup so MADSci services and
clients share one consistent initialization behavior.

Functions
---------

`collect_metrics(runtime: madsci.common.otel.bootstrap.OtelRuntime) ‑> Any | None`
:   Force a synchronous metrics collection for test assertions.

    OpenTelemetry's metrics SDK is pull-based; in tests we want deterministic
    reads without background threads.

`configure_otel(config: madsci.common.otel.bootstrap.OtelBootstrapConfig) ‑> madsci.common.otel.bootstrap.OtelRuntime`
:   Configure OpenTelemetry SDK providers.

    This function is idempotent: the first successful configuration wins.

`current_trace_context() ‑> dict[str, str | None]`
:   Return the active trace/span ids for log correlation.

`get_otel_runtime() ‑> madsci.common.otel.bootstrap.OtelRuntime | None`
:   Return the process-global OTEL runtime when configured.

Classes
-------

`OtelBootstrapConfig(enabled: bool, service_name: str, service_version: str = 'unknown', exporter: Literal['console', 'otlp', 'none'] = 'console', otlp_endpoint: str | None = None, otlp_protocol: Literal['grpc', 'http'] = 'grpc', metric_export_interval_ms: int = 10000, test_mode: bool = False)`
:   Settings for `configure_otel`.

    ### Instance variables

    `enabled: bool`
    :

    `exporter: Literal['console', 'otlp', 'none']`
    :

    `metric_export_interval_ms: int`
    :

    `otlp_endpoint: str | None`
    :

    `otlp_protocol: Literal['grpc', 'http']`
    :

    `service_name: str`
    :

    `service_version: str`
    :

    `test_mode: bool`
    :

`OtelRuntime(enabled: bool, tracer_provider: opentelemetry.sdk.trace.TracerProvider | None = None, meter_provider: opentelemetry.sdk.metrics._internal.MeterProvider | None = None, logger_provider: opentelemetry.sdk._logs._internal.LoggerProvider | None = None, otel_log_handler: logging.Handler | None = None, in_memory_span_exporter: opentelemetry.sdk.trace.export.in_memory_span_exporter.InMemorySpanExporter | None = None, in_memory_metric_reader: opentelemetry.sdk.metrics._internal.export.InMemoryMetricReader | None = None)`
:   Runtime handles returned by `configure_otel`.

    ### Instance variables

    `enabled: bool`
    :

    `in_memory_metric_reader: opentelemetry.sdk.metrics._internal.export.InMemoryMetricReader | None`
    :

    `in_memory_span_exporter: opentelemetry.sdk.trace.export.in_memory_span_exporter.InMemorySpanExporter | None`
    :

    `logger_provider: opentelemetry.sdk._logs._internal.LoggerProvider | None`
    :

    `meter: opentelemetry.metrics.Meter`
    :   Return a meter bound to this module.

    `meter_provider: opentelemetry.sdk.metrics._internal.MeterProvider | None`
    :

    `otel_log_handler: logging.Handler | None`
    :

    `tracer: opentelemetry.trace.Tracer`
    :   Return a tracer bound to this module.

    `tracer_provider: opentelemetry.sdk.trace.TracerProvider | None`
    :
