#!/usr/bin/env python3
"""OpenTelemetry Integration Demo for MADSci EventClient.

This script demonstrates the OpenTelemetry integration with MADSci's
EventClient, showing how distributed tracing and log correlation work.

Usage:
    # Ensure you're in the MADSci root directory with the virtual environment active
    python examples/otel_demo.py

This demo will:
1. Initialize OpenTelemetry with console exporter
2. Create a traced "workflow" with multiple spans
3. Show how log entries are correlated with trace context
4. Demonstrate basic metrics recording

Expected output will show:
- Console-formatted spans with trace IDs
- Log entries containing trace_id and span_id
- Metric summaries
"""

import time
from typing import Any

from madsci.client.otel_processors import add_otel_context
from madsci.common.otel import (
    OtelBootstrapConfig,
    configure_otel,
    current_trace_context,
)
from madsci.common.types.event_types import Event, EventType

# Import OTEL configuration and processors
from opentelemetry import metrics, trace


def simulate_workflow_step(
    tracer: Any, meter: Any, step_name: str, duration: float = 0.1
) -> None:
    """Simulate a workflow step with tracing and metrics.

    Args:
        tracer: The OTEL tracer to use
        meter: The OTEL meter to use
        step_name: Name of the step
        duration: Simulated step duration in seconds
    """
    step_counter = meter.create_counter(
        f"madsci.demo.steps.{step_name}",
        description=f"Count of {step_name} executions",
    )
    step_latency = meter.create_histogram(
        f"madsci.demo.latency.{step_name}",
        description=f"Latency of {step_name} in milliseconds",
        unit="ms",
    )

    with tracer.start_as_current_span(f"workflow.step.{step_name}") as span:
        span.set_attribute("step.name", step_name)
        span.set_attribute("step.simulated_duration", duration)

        # Get trace context for logging
        current_trace_context()

        # Simulate work
        start = time.time()
        time.sleep(duration)
        elapsed_ms = (time.time() - start) * 1000

        # Record metrics
        step_counter.add(1)
        step_latency.record(elapsed_ms)

        span.add_event("step_completed", attributes={"elapsed_ms": elapsed_ms})


def demonstrate_event_with_trace_context() -> Event:
    """Show how Event objects can carry trace context."""
    tracer = trace.get_tracer("madsci.demo.events")

    with tracer.start_as_current_span("event.logging.demo") as span:
        ctx = current_trace_context()

        # Create an event with trace context
        event = Event(
            event_type=EventType.LOG_INFO,
            event_data={"message": "Demo event with OTEL context"},
            trace_id=ctx["trace_id"],
            span_id=ctx["span_id"],
        )

        span.add_event(
            "event_created",
            attributes={
                "event_id": event.event_id,
                "event_type": event.event_type.value,
            },
        )

        return event


def demonstrate_structlog_integration() -> None:
    """Show how structlog processors add OTEL context to logs."""
    try:
        import structlog  # noqa: PLC0415
    except ImportError:
        return

    tracer = trace.get_tracer("madsci.demo.structlog")

    # Configure structlog with OTEL processor
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            add_otel_context,  # Add OTEL trace context
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(10),  # DEBUG level
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )

    logger = structlog.get_logger()

    with tracer.start_as_current_span("structlog.demo"):
        logger.info("Log entry with automatic trace context", demo="structlog")
        logger.warning("Another entry", action="demo")


def main() -> None:
    """Run the OpenTelemetry integration demo."""

    # Initialize OTEL with console exporter for demo
    configure_otel(
        OtelBootstrapConfig(
            enabled=True,
            service_name="madsci-otel-demo",
            service_version="1.0.0",
            exporter="console",
        )
    )

    # Get tracer and meter for the demo
    tracer = trace.get_tracer("madsci.demo")
    meter = metrics.get_meter("madsci.demo")

    # Demo: Simulated workflow with tracing

    with tracer.start_as_current_span("workflow.demo") as root_span:
        root_span.set_attribute("workflow.name", "demo-workflow")
        root_span.set_attribute("workflow.steps", 3)

        current_trace_context()

        simulate_workflow_step(tracer, meter, "prepare", 0.05)
        simulate_workflow_step(tracer, meter, "execute", 0.1)
        simulate_workflow_step(tracer, meter, "cleanup", 0.03)

    # Demo: Event with trace context
    demonstrate_event_with_trace_context()

    # Demo: Structlog integration
    demonstrate_structlog_integration()

    # Demo: Context outside of span
    current_trace_context()


if __name__ == "__main__":
    main()
