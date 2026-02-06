# Phase 3: Application Integration

**Estimated Effort:** Medium-Large (4-6 days)
**Breaking Changes:** None
**Prerequisites:** Phase 2 complete

## Goals

- Integrate context into `ExperimentApplication`
- Update managers to establish/participate in context
- Update node modules to participate in context
- Demonstrate full hierarchical logging across system

## 3.0 Implementation Principles

### 3.0.1 Entry Points Establish Context

Context should be established at system entry points:

1. **ExperimentApplication.run()** - establishes experiment context
2. **Manager startup** - establishes manager context
3. **Node module startup** - establishes node context
4. **CLI commands** - establish command context

### 3.0.2 Workflow Steps Extend Context

Each workflow step should create a nested context:

```python
for step in workflow.steps:
    with event_client_context(name=f"step.{step.name}", step_id=step.id):
        execute_step(step)
```

### 3.0.3 Cross-Service Context (Future)

Context propagation across HTTP boundaries (via trace headers) is handled by OTEL integration. This phase focuses on in-process context.

## 3.1 Test Specifications (TDD)

Create `src/madsci_experiment_application/tests/test_experiment_context.py`:

```python
"""Tests for ExperimentApplication context integration."""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestExperimentApplicationContext:
    """Test ExperimentApplication establishes proper context."""

    def test_run_establishes_experiment_context(self):
        """Test that run() establishes experiment context."""
        from madsci.common.context import get_event_client_context, has_event_client_context

        contexts_observed = []

        # Mock the workflow execution to capture context
        def mock_execute(*args, **kwargs):
            if has_event_client_context():
                ctx = get_event_client_context()
                contexts_observed.append({
                    "hierarchy": ctx.hierarchy.copy(),
                    "metadata": ctx.metadata.copy(),
                })

        # This test structure depends on actual ExperimentApplication implementation
        # Adjust based on actual class structure
        with patch.object(SomeClass, "execute", mock_execute):
            # Run experiment
            pass

        # Verify context was established
        assert len(contexts_observed) > 0
        assert "experiment" in contexts_observed[0]["hierarchy"][0]

    def test_workflow_steps_have_nested_context(self):
        """Test that each workflow step has properly nested context."""
        from madsci.common.context import event_client_context, get_event_client_context

        step_contexts = []

        # Simulate experiment with workflow steps
        with event_client_context(name="experiment", experiment_id="exp-123"):
            with event_client_context(name="workflow", workflow_id="wf-456"):
                for step_num in range(3):
                    with event_client_context(name=f"step_{step_num}", step_id=f"s-{step_num}"):
                        ctx = get_event_client_context()
                        step_contexts.append({
                            "name": ctx.name,
                            "metadata": ctx.metadata.copy(),
                        })

        # Verify each step had proper context
        assert len(step_contexts) == 3

        for i, ctx in enumerate(step_contexts):
            assert ctx["metadata"]["experiment_id"] == "exp-123"
            assert ctx["metadata"]["workflow_id"] == "wf-456"
            assert ctx["metadata"]["step_id"] == f"s-{i}"
            assert f"step_{i}" in ctx["name"]

    def test_node_actions_inherit_step_context(self):
        """Test that node actions inherit step context."""
        from madsci.common.context import event_client_context, get_event_client

        action_contexts = []

        with event_client_context(name="experiment", experiment_id="exp-123"):
            with event_client_context(name="workflow", workflow_id="wf-456"):
                with event_client_context(name="step", step_id="step-1"):
                    # Simulate node action
                    logger = get_event_client(action_id="action-789")
                    action_contexts.append(logger._bound_context.copy())

        assert len(action_contexts) == 1
        ctx = action_contexts[0]

        # Should have accumulated context
        assert ctx.get("experiment_id") == "exp-123"
        assert ctx.get("workflow_id") == "wf-456"
        assert ctx.get("step_id") == "step-1"
        assert ctx.get("action_id") == "action-789"


class TestManagerContextIntegration:
    """Test manager context integration."""

    def test_manager_establishes_context_on_startup(self):
        """Test that managers establish context during initialization."""
        from madsci.common.context import has_event_client_context

        # This would test actual manager initialization
        # Implementation depends on specific manager structure
        pass

    def test_manager_endpoints_have_request_context(self):
        """Test that manager endpoints operate within request context."""
        # FastAPI/ASGI middleware integration test
        pass


class TestNodeModuleContextIntegration:
    """Test node module context integration."""

    def test_node_action_executes_in_context(self):
        """Test that node actions execute within proper context."""
        from madsci.common.context import event_client_context, get_event_client_context

        with event_client_context(name="node.test_node", node_name="test_node"):
            with event_client_context(name="action.grab", action_name="grab"):
                ctx = get_event_client_context()

                assert "node.test_node" in ctx.name
                assert "action.grab" in ctx.name
                assert ctx.metadata.get("node_name") == "test_node"
                assert ctx.metadata.get("action_name") == "grab"

    def test_action_logs_include_node_context(self):
        """Test that action logs include node context."""
        from madsci.common.context import event_client_context, get_event_client

        with event_client_context(name="node", node_id="node-123"):
            logger = get_event_client()

            # Logger should have node context bound
            assert "node_id" in logger._bound_context
            assert logger._bound_context["node_id"] == "node-123"
```

Create `src/madsci_common/tests/test_manager_context.py`:

```python
"""Tests for manager base context integration."""

import pytest
from unittest.mock import Mock, patch


class TestAbstractManagerBaseContext:
    """Test AbstractManagerBase context integration."""

    def test_manager_logger_uses_context(self):
        """Test that manager logger uses context system."""
        from madsci.common.context import event_client_context, has_event_client_context

        # When running under test harness with context
        with event_client_context(name="test", test_id="t-123"):
            # Manager should use context logger
            pass  # Implementation-specific test

    def test_manager_startup_log_includes_manager_info(self):
        """Test that manager startup log includes identifying info."""
        # Verify manager name, version, etc. in startup logs
        pass
```

## 3.2 Implementation Tasks

### 3.2.1 Update ExperimentApplication

Update `src/madsci_experiment_application/madsci/experiment_application/experiment_application.py`:

```python
from madsci.common.context import event_client_context, get_event_client


class ExperimentApplication:
    """
    [existing docstring]
    """

    def run(
        self,
        experiment_id: Optional[str] = None,
        # ... other params
    ) -> ExperimentResult:
        """
        Run the experiment with full context propagation.

        All logging within this experiment run will include the experiment
        context, enabling hierarchical log filtering and analysis.
        """
        experiment_id = experiment_id or new_ulid_str()

        with event_client_context(
            name="experiment",
            experiment_id=experiment_id,
            experiment_name=self.name,
            experiment_type=self.__class__.__name__,
        ) as logger:
            logger.info(
                "Starting experiment",
                experiment_id=experiment_id,
            )

            try:
                result = self._execute_experiment(experiment_id)
                logger.info(
                    "Experiment completed",
                    experiment_id=experiment_id,
                    status="success",
                )
                return result
            except Exception as e:
                logger.exception(
                    "Experiment failed",
                    experiment_id=experiment_id,
                    status="failed",
                )
                raise

    def _execute_workflow(
        self,
        workflow: Workflow,
        workflow_run_id: str,
    ) -> WorkflowResult:
        """Execute a workflow with context."""
        with event_client_context(
            name="workflow",
            workflow_id=workflow_run_id,
            workflow_name=workflow.name,
        ) as logger:
            logger.info("Starting workflow")

            for step_index, step in enumerate(workflow.steps):
                self._execute_step(step, step_index)

            logger.info("Workflow completed")

    def _execute_step(
        self,
        step: WorkflowStep,
        step_index: int,
    ) -> StepResult:
        """Execute a workflow step with context."""
        step_id = step.id or f"step-{step_index}"

        with event_client_context(
            name=f"step.{step.name}",
            step_id=step_id,
            step_name=step.name,
            step_index=step_index,
        ) as logger:
            logger.info("Executing step")

            # Execute step actions...
            # Node clients created here will inherit this context

            logger.info("Step completed")
```

### 3.2.2 Update AbstractManagerBase

Update `src/madsci_common/madsci/common/abstract_manager.py` (or equivalent):

```python
from madsci.common.context import event_client_context, get_event_client


class AbstractManagerBase:
    """
    Base class for MADSci manager services.

    [existing docstring]
    """

    def __init__(self, ...):
        # ... existing init ...

        # Use context-aware logger
        self.logger = get_event_client(
            name=self.manager_name,
            manager_type=self.__class__.__name__,
        )

    def run(self, ...):
        """Run the manager with context."""
        with event_client_context(
            name=f"manager.{self.manager_name}",
            manager_name=self.manager_name,
            manager_type=self.__class__.__name__,
        ) as logger:
            logger.info("Manager starting")

            # Start FastAPI app...
            # All request handlers will inherit this context

            return super().run(...)
```

### 3.2.3 Add FastAPI Middleware for Request Context (Optional)

Create middleware to establish per-request context:

```python
# src/madsci_common/madsci/common/middleware/context_middleware.py

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from madsci.common.context import event_client_context
from madsci.common.utils import new_ulid_str


class EventClientContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that establishes EventClient context for each request.

    This enables hierarchical logging where all logs within a request
    share common context (request_id, path, method, etc.).
    """

    def __init__(self, app, manager_name: str = "manager"):
        super().__init__(app)
        self.manager_name = manager_name

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or new_ulid_str()

        with event_client_context(
            name=f"request.{request.method}.{request.url.path}",
            request_id=request_id,
            http_method=request.method,
            http_path=str(request.url.path),
            manager=self.manager_name,
        ):
            response = await call_next(request)
            return response
```

Usage in managers:
```python
from madsci.common.middleware.context_middleware import EventClientContextMiddleware

app = FastAPI()
app.add_middleware(EventClientContextMiddleware, manager_name="event_manager")
```

### 3.2.4 Update AbstractNodeModule

Update `src/madsci_node_module/madsci/node_module/abstract_node_module.py`:

```python
from madsci.common.context import event_client_context, get_event_client


class AbstractNodeModule:
    """
    Base class for MADSci node modules.

    [existing docstring]
    """

    def __init__(self, ...):
        # ... existing init ...

        # Use context-aware logger
        self.logger = get_event_client(
            name=self.node_name,
            node_type=self.__class__.__name__,
        )

    def _execute_action(
        self,
        action_name: str,
        action_id: str,
        action_request: ActionRequest,
    ) -> ActionResult:
        """Execute an action with context."""
        with event_client_context(
            name=f"action.{action_name}",
            action_id=action_id,
            action_name=action_name,
            node_name=self.node_name,
        ) as logger:
            logger.info(
                "Starting action",
                args=action_request.args,
            )

            try:
                result = self._run_action(action_name, action_request)
                logger.info(
                    "Action completed",
                    status=result.status,
                )
                return result
            except Exception as e:
                logger.exception(
                    "Action failed",
                    error=str(e),
                )
                raise
```

## 3.3 Integration Example

This shows how context flows through a complete experiment:

```python
# Example: Full context hierarchy during experiment execution

# 1. ExperimentApplication.run() establishes:
#    hierarchy: ["experiment"]
#    metadata: {experiment_id: "exp-123", experiment_name: "my_experiment"}

# 2. _execute_workflow() adds:
#    hierarchy: ["experiment", "workflow"]
#    metadata: {..., workflow_id: "wf-456", workflow_name: "main_workflow"}

# 3. _execute_step() adds:
#    hierarchy: ["experiment", "workflow", "step.transfer"]
#    metadata: {..., step_id: "step-1", step_name: "transfer"}

# 4. RestNodeClient created during step uses get_event_client():
#    hierarchy: ["experiment", "workflow", "step.transfer"]
#    metadata: {..., component_type: "RestNodeClient", node_url: "http://robot:8000/"}

# 5. Node action execution (on node side):
#    hierarchy: ["node.robot", "action.grab"]
#    metadata: {node_name: "robot", action_id: "action-789", action_name: "grab"}

# Log output:
# [experiment.workflow.step.transfer] Sending action to node | experiment_id=exp-123 workflow_id=wf-456 step_id=step-1 node_url=http://robot:8000/
# [node.robot.action.grab] Executing grab | node_name=robot action_id=action-789
# [node.robot.action.grab] Grab completed | node_name=robot action_id=action-789 status=success
# [experiment.workflow.step.transfer] Action completed | experiment_id=exp-123 workflow_id=wf-456 step_id=step-1 status=success
```

## 3.4 Acceptance Criteria

- [ ] `ExperimentApplication.run()` establishes experiment context
- [ ] Workflow execution creates nested workflow context
- [ ] Each step creates nested step context
- [ ] Node clients created during steps inherit full context
- [ ] Manager base class uses context-aware logging
- [ ] Node modules use context-aware logging
- [ ] Action execution creates action context
- [ ] Request middleware (optional) adds request context
- [ ] All existing tests continue to pass
- [ ] New integration tests pass
- [ ] Log output shows hierarchical context

## 3.5 Verification

To verify the integration works correctly:

1. **Run example lab** with context integration
2. **Execute a workflow** through the system
3. **Examine logs** for proper hierarchy:
   - All logs from same experiment share `experiment_id`
   - Workflow logs include `workflow_id`
   - Step logs include `step_id`
   - Node action logs include `action_id`

4. **Query EventManager** for events:
   - Filter by `experiment_id` returns all related events
   - Filter by `workflow_id` returns workflow-specific events
   - Hierarchical filtering works correctly

5. **Check OTEL traces** (if enabled):
   - `madsci.hierarchy` attribute present
   - Context metadata as span attributes
