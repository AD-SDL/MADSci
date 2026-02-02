# Overview

This document outlines a phased, test-driven development plan for comprehensive OpenTelemetry (OTEL) integration throughout the MADSci ecosystem. Building on the foundational work from the Event Manager Improvement Plan, this effort will:

1. **Complete OTEL integration** in the EventClient and propagate it across all MADSci components
2. **Audit and enhance logging** to ensure all components generate useful, queryable events
3. **Extend EventType coverage** to support comprehensive event-based querying
4. **Add OTEL infrastructure** to the example lab for validation and demonstration

## Goals

By the end of this implementation:

- [ ] **OpenTelemetry Integration**: All MADSci managers and EventClient support optional OTEL tracing
  - Measurable: 100% of manager endpoints instrumented with spans when `otel_enabled=True`
  - Measurable: Trace context propagates across all inter-service HTTP calls
  - Measurable: When OTEL is disabled, no SDK providers/exporters/instrumentation are installed and no background export threads are started
- [ ] **Logging Audit**: All EventClient calls follow structured logging best practices
  - Measurable: 100% of log calls use kwargs instead of f-string formatting for data
  - Measurable: All error logs include `exc_info=True` when an exception is available
  - Measurable: `trace_id`/`span_id` populated in Events when OTEL enabled and span active
- [ ] **EventType Coverage**: All significant operations use appropriate EventType values
  - Measurable: New EventType enum values cover Resource, Location, Data, and Manager lifecycle events
  - Measurable: Audit confirms no operation logs use generic `LOG_INFO` when a specific type exists
- [ ] **Example Lab Infrastructure**: Working OTEL stack with documentation
  - Measurable: `docker compose -f compose.yaml -f compose.otel.yaml up` brings up working stack
  - Measurable: Example workflow produces correlated traces visible in Jaeger
  - Measurable: Metrics visible in Prometheus, logs in Loki, unified dashboard in Grafana
