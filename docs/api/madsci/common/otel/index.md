Module madsci.common.otel
=========================
OpenTelemetry bootstrap and helpers.

This package provides a single canonical OpenTelemetry configuration surface
for MADSci processes.

Sub-modules
-----------
* madsci.common.otel.bootstrap
* madsci.common.otel.fastapi_instrumentation
* madsci.common.otel.propagation
* madsci.common.otel.requests_instrumentation
* madsci.common.otel.tracing

Functions
---------

`add_span_event(name: str, attributes: dict[str, typing.Any] | None = None, span: opentelemetry.trace.span.Span | None = None) ‑> None`
:   Add an event to the current or provided span.
    
    Args:
        name: The event name.
        attributes: Optional event attributes.
        span: The span to add the event to. Uses current span if not provided.
    
    Example:
        add_span_event("cache_hit", {"key": cache_key})
        add_span_event("validation_complete", {"items_validated": 100})

`collect_metrics(runtime: OtelRuntime) ‑> Any | None`
:   Force a synchronous metrics collection for test assertions.
    
    OpenTelemetry's metrics SDK is pull-based; in tests we want deterministic
    reads without background threads.

`configure_otel(config: OtelBootstrapConfig) ‑> madsci.common.otel.bootstrap.OtelRuntime`
:   Configure OpenTelemetry SDK providers.
    
    This function is idempotent: the first successful configuration wins.

`current_trace_context() ‑> dict[str, str | None]`
:   Return the active trace/span ids for log correlation.

`get_current_span() ‑> opentelemetry.trace.span.Span`
:   Get the current active span.
    
    Returns:
        The current Span, or a non-recording span if none is active.

`get_otel_runtime() ‑> madsci.common.otel.bootstrap.OtelRuntime | None`
:   Return the process-global OTEL runtime when configured.

`get_tracer(name: str | None = None) ‑> opentelemetry.trace.Tracer`
:   Get an OpenTelemetry tracer.
    
    Args:
        name: The tracer name. Defaults to "madsci".
    
    Returns:
        An OpenTelemetry Tracer instance.

`inject_headers(headers: MutableMapping[str, str]) ‑> None`
:   Inject trace context into outbound HTTP headers.

`instrument_fastapi(app: FastAPI, *, enabled: bool = True) ‑> bool`
:   Enable OpenTelemetry auto-instrumentation for FastAPI.
    
    Returns True when instrumentation was applied, otherwise False.

`instrument_requests(*, enabled: bool = True) ‑> bool`
:   Enable OpenTelemetry auto-instrumentation for `requests`.
    
    Returns True when instrumentation was applied, otherwise False.

`is_span_recording() ‑> bool`
:   Check if the current span is recording.
    
    Returns:
        True if there's an active recording span, False otherwise.

`safe_span_context(name: str, *, tracer_name: str | None = None, kind: opentelemetry.trace.SpanKind = SpanKind.INTERNAL, attributes: dict[str, typing.Any] | None = None) ‑> Generator[opentelemetry.trace.span.Span | None, None, None]`
:   Context manager that creates a span if OTEL is configured, otherwise no-op.
    
    This is useful for code that may run with or without OTEL configured.
    It never raises exceptions related to tracing.
    
    Args:
        name: The name of the span.
        tracer_name: Optional tracer name. Defaults to "madsci".
        kind: The span kind.
        attributes: Optional dictionary of span attributes.
    
    Yields:
        The created Span object, or None if tracing is not available.
    
    Example:
        with safe_span_context("optional_trace") as span:
            if span:
                span.set_attribute("custom", "value")
            do_work()

`set_span_attributes(attributes: dict[str, typing.Any], span: opentelemetry.trace.span.Span | None = None) ‑> None`
:   Set multiple attributes on the current or provided span.
    
    Args:
        attributes: Dictionary of attributes to set.
        span: The span to set attributes on. Uses current span if not provided.
    
    Example:
        set_span_attributes({
            "user.id": user_id,
            "request.size": len(data),
            "cache.enabled": True,
        })

`set_span_error(span: opentelemetry.trace.span.Span | None = None, exception: BaseException | None = None, message: str | None = None) ‑> None`
:   Set the current or provided span to error status.
    
    Args:
        span: The span to mark as error. Uses current span if not provided.
        exception: Optional exception to record.
        message: Optional error message.
    
    Example:
        try:
            risky_operation()
        except Exception as e:
            set_span_error(exception=e, message="Operation failed")
            raise

`span_context(name: str, *, tracer_name: str | None = None, kind: opentelemetry.trace.SpanKind = SpanKind.INTERNAL, attributes: dict[str, typing.Any] | None = None, record_exception: bool = True, set_status_on_exception: bool = True) ‑> Generator[opentelemetry.trace.span.Span, None, None]`
:   Context manager that creates an OpenTelemetry span.
    
    This is a convenience wrapper around tracer.start_as_current_span() that
    handles the common case of creating a span with attributes and automatic
    exception recording.
    
    Args:
        name: The name of the span.
        tracer_name: Optional tracer name. Defaults to "madsci".
        kind: The span kind (INTERNAL, SERVER, CLIENT, PRODUCER, CONSUMER).
        attributes: Optional dictionary of span attributes.
        record_exception: If True, record exceptions as span events.
        set_status_on_exception: If True, set span status to ERROR on exception.
    
    Yields:
        The created Span object.
    
    Example:
        with span_context("process_data", attributes={"data.size": 100}) as span:
            result = process(data)
            span.set_attribute("result.count", len(result))
    
        with span_context("fetch_resource", kind=SpanKind.CLIENT) as span:
            response = requests.get(url)
            span.set_attribute("http.status_code", response.status_code)

`traced_class(name: str | None = None, *, tracer_name: str | None = None, kind: opentelemetry.trace.SpanKind = SpanKind.INTERNAL, attributes: dict[str, typing.Any] | None = None, record_exception: bool = True, set_status_on_exception: bool = True) ‑> Callable[[type], type]`
:   Class decorator that wraps all public methods in OpenTelemetry spans.
    
    This decorator modifies a class so that all public methods (not starting
    with underscore) are automatically traced. The class gains a 'current_span'
    property that returns the active span.
    
    Args:
        name: Base name for spans. Defaults to the class name.
              Method spans will be named "{class_name}.{method_name}".
        tracer_name: Optional tracer name. Defaults to "madsci".
        kind: The span kind for method spans.
        attributes: Optional dictionary of span attributes to add to all spans.
        record_exception: If True, record exceptions as span events.
        set_status_on_exception: If True, set span status to ERROR on exception.
    
    Returns:
        A class decorator.
    
    Example:
        @traced_class(attributes={"component": "data_processor"})
        class DataProcessor:
            def process(self, data):
                # This method is automatically traced
                self.current_span.set_attribute("data.size", len(data))
                return transform(data)
    
            def _helper(self, x):  # Private methods are NOT traced
                return x * 2
    
        @traced_class(name="CustomWorker")
        class Worker:
            def get_span_attributes(self) -> dict:
                # Return instance-specific attributes
                return {"worker.id": self.worker_id}
    
            def work(self):
                # Span includes both class-level and instance attributes
                self.current_span.add_event("started")
                do_work()

`with_span(func: Callable[~P, typing.Any] | None = None, *, name: str | None = None, tracer_name: str | None = None, kind: opentelemetry.trace.SpanKind = SpanKind.INTERNAL, attributes: dict[str, typing.Any] | None = None, record_exception: bool = True, set_status_on_exception: bool = True) ‑> Callable[~P, typing.Any] | Callable[[Callable[~P, typing.Any]], Callable[~P, typing.Any]]`
:   Decorator that wraps a function in an OpenTelemetry span.
    
    This decorator creates a span for each function invocation, automatically
    recording the function name, arguments (optionally), and any exceptions.
    Works with both sync and async functions.
    
    Can be used with or without arguments:
        @with_span
        def my_function(): ...
    
        @with_span(name="custom_span", attributes={"component": "processor"})
        def my_function(): ...
    
    Args:
        func: The function to wrap (when used without parentheses).
        name: Custom span name. Defaults to the function's qualified name.
        tracer_name: Optional tracer name. Defaults to "madsci".
        kind: The span kind (INTERNAL, SERVER, CLIENT, PRODUCER, CONSUMER).
        attributes: Optional dictionary of span attributes to add.
        record_exception: If True, record exceptions as span events.
        set_status_on_exception: If True, set span status to ERROR on exception.
    
    Returns:
        The decorated function that runs within a span.
    
    Example:
        @with_span
        def process_data(data):
            return transform(data)
    
        @with_span(name="fetch_user", kind=SpanKind.CLIENT)
        def get_user(user_id: str):
            return api.fetch(user_id)
    
        @with_span(attributes={"workflow.type": "batch"})
        async def run_batch_workflow():
            await process_batch()

Classes
-------

`OtelBootstrapConfig(enabled: bool, service_name: str, service_version: str = 'unknown', exporter: ExporterType = 'console', otlp_endpoint: Optional[str] = None, otlp_protocol: OtlpProtocol = 'grpc', metric_export_interval_ms: int = 10000, test_mode: bool = False)`
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

`OtelRuntime(enabled: bool, tracer_provider: Optional[TracerProvider] = None, meter_provider: Optional[MeterProvider] = None, logger_provider: Optional[LoggerProvider] = None, in_memory_span_exporter: Optional[InMemorySpanExporter] = None, in_memory_metric_reader: Optional[InMemoryMetricReader] = None)`
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

    `meter: metrics.Meter`
    :   Return a meter bound to this module.

    `meter_provider: opentelemetry.sdk.metrics._internal.MeterProvider | None`
    :

    `tracer: trace.Tracer`
    :   Return a tracer bound to this module.

    `tracer_provider: opentelemetry.sdk.trace.TracerProvider | None`
    :