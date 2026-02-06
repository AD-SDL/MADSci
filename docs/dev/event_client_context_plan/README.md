# Event Client Context System

> **Created:** February 2026
> **Status:** Phase 1 & 2 Complete (Feb 2026)
> **Related:** [OpenTelemetry Integration Plan](../opentelemetry_integration_plan/README.md)

## Implementation Progress

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1: Core Infrastructure | ✅ Complete | Context management functions and `EventClientContext` dataclass |
| Phase 2: Client Updates | ✅ Complete | `MadsciClientMixin`, `RestNodeClient`, and other clients updated |
| Phase 3: Application Integration | ✅ Complete | Experiment/workflow/manager/node context integration |
| Phase 4: Documentation & Migration | ✅ Complete | User documentation and migration guides |

This directory contains the development plan for implementing a hierarchical EventClient context system that propagates through the MADSci system.

## Problem Statement

Currently, MADSci has several issues with EventClient instantiation:

1. **Excessive instantiation**: A new EventClient is created every time certain classes are instantiated (e.g., RestNodeClient), which happens frequently during workflow execution.

2. **Poor name inference**: The stack inspection logic only looks at the immediate caller, leading to generic names like `madsci.client.node.rest_node_client` instead of meaningful hierarchical names.

3. **No hierarchy**: Log files lack context about where in the system hierarchy a log message originated (e.g., which experiment, workflow, or node action triggered it).

4. **Resource waste**: Each EventClient creates its own HTTP session, file handler with rotation, thread for event buffering, and structlog logger instance.

## Solution Overview

Introduce a context-based EventClient system using Python's `contextvars` that:

1. Propagates EventClient instances through the call stack automatically
2. Allows child components to inherit and extend parent context
3. Only creates new EventClients when truly needed
4. Provides hierarchical naming and context binding automatically
5. Maintains full backward compatibility

## Contents

- [Principles & Design Decisions](./00_principles.md)
- [Phase 1: Core Infrastructure](./10_phase_1_core_infrastructure.md)
- [Phase 2: Client Updates](./20_phase_2_client_updates.md)
- [Phase 3: Application Integration](./30_phase_3_application_integration.md)
- [Phase 4: Documentation & Migration](./40_phase_4_documentation.md)
- [Migration Guide](./migration_guide.md)

## Quick Reference

### Primary API

```python
from madsci.common.context import (
    get_event_client,          # Get current context client or create new one
    event_client_context,      # Context manager for establishing/extending context
    has_event_client_context,  # Check if context exists
)

# Basic usage - get client from context (or create if none exists)
logger = get_event_client()
logger.info("Processing...")

# Establish context at application entry point
with event_client_context(name="experiment", experiment_id="exp-123") as logger:
    logger.info("Starting experiment")

    # Nested context inherits parent
    with event_client_context(name="workflow", workflow_id="wf-456") as wf_logger:
        wf_logger.info("Running workflow")  # Has both experiment_id and workflow_id
```

### Migration Pattern

```python
# Before
class MyComponent:
    def __init__(self):
        self.logger = EventClient()  # Creates new client every time

# After
class MyComponent:
    def __init__(self, event_client: Optional[EventClient] = None):
        self.logger = event_client or get_event_client()  # Uses context if available
```
