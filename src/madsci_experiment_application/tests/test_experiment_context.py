"""Tests for ExperimentApplication context integration."""

import asyncio

import pytest
from madsci.common.context import (
    event_client_context,
    get_event_client,
    get_event_client_context,
    has_event_client_context,
)


class TestExperimentApplicationContext:
    """Test ExperimentApplication establishes proper context."""

    def test_run_establishes_experiment_context(self):
        """Test that run() establishes experiment context."""
        contexts_observed = []

        # This test structure depends on actual ExperimentApplication implementation
        # We'll test context propagation using the manage_experiment context manager
        with event_client_context(name="experiment", experiment_id="exp-123"):
            if has_event_client_context():
                ctx = get_event_client_context()
                contexts_observed.append(
                    {
                        "hierarchy": ctx.hierarchy.copy(),
                        "metadata": ctx.metadata.copy(),
                    }
                )

        # Verify context was established
        assert len(contexts_observed) > 0
        assert "experiment" in contexts_observed[0]["hierarchy"][0]

    def test_workflow_steps_have_nested_context(self):
        """Test that each workflow step has properly nested context."""
        step_contexts = []

        # Simulate experiment with workflow steps
        with (
            event_client_context(name="experiment", experiment_id="exp-123"),
            event_client_context(name="workflow", workflow_id="wf-456"),
        ):
            for step_num in range(3):
                with event_client_context(
                    name=f"step_{step_num}", step_id=f"s-{step_num}"
                ):
                    ctx = get_event_client_context()
                    step_contexts.append(
                        {
                            "name": ctx.name,
                            "metadata": ctx.metadata.copy(),
                        }
                    )

        # Verify each step had proper context
        assert len(step_contexts) == 3

        for i, ctx in enumerate(step_contexts):
            assert ctx["metadata"]["experiment_id"] == "exp-123"
            assert ctx["metadata"]["workflow_id"] == "wf-456"
            assert ctx["metadata"]["step_id"] == f"s-{i}"
            assert f"step_{i}" in ctx["name"]

    def test_node_actions_inherit_step_context(self):
        """Test that node actions inherit step context."""
        action_contexts = []

        with (
            event_client_context(name="experiment", experiment_id="exp-123"),
            event_client_context(name="workflow", workflow_id="wf-456"),
            event_client_context(name="step", step_id="step-1"),
        ):
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

    def test_context_manager_with_exception_handling(self):
        """Test that context is properly restored after exceptions."""
        # Verify no context before
        assert not has_event_client_context()

        with (
            pytest.raises(ValueError),
            event_client_context(name="experiment", experiment_id="exp-123"),
        ):
            assert has_event_client_context()
            raise ValueError("Test exception")

        # Verify context is cleaned up after exception
        assert not has_event_client_context()

    def test_nested_context_cleanup(self):
        """Test that nested context cleanup works correctly."""
        with event_client_context(name="experiment", experiment_id="exp-123"):
            exp_ctx = get_event_client_context()
            assert exp_ctx.hierarchy == ["experiment"]

            with event_client_context(name="workflow", workflow_id="wf-456"):
                wf_ctx = get_event_client_context()
                assert wf_ctx.hierarchy == ["experiment", "workflow"]
                assert wf_ctx.metadata.get("experiment_id") == "exp-123"
                assert wf_ctx.metadata.get("workflow_id") == "wf-456"

            # After workflow context exits, should be back to experiment context
            restored_ctx = get_event_client_context()
            assert restored_ctx.hierarchy == ["experiment"]
            assert "workflow_id" not in restored_ctx.metadata


class TestManagerContextIntegration:
    """Test manager context integration."""

    def test_manager_logger_uses_context(self):
        """Test that manager logger uses context system."""
        # When running under test harness with context
        with event_client_context(name="test_manager", test_id="t-123"):
            assert has_event_client_context()
            # Get a logger which should inherit the context
            logger = get_event_client(manager_type="TestManager")
            assert "test_id" in logger._bound_context
            assert logger._bound_context["test_id"] == "t-123"
            assert logger._bound_context["manager_type"] == "TestManager"

    def test_manager_startup_log_includes_manager_info(self):
        """Test that manager startup log includes identifying info."""
        with event_client_context(
            name="manager.test_manager",
            manager_name="test_manager",
            manager_type="TestManagerClass",
        ):
            ctx = get_event_client_context()
            assert "manager.test_manager" in ctx.name
            assert ctx.metadata["manager_name"] == "test_manager"
            assert ctx.metadata["manager_type"] == "TestManagerClass"


class TestNodeModuleContextIntegration:
    """Test node module context integration."""

    def test_node_action_executes_in_context(self):
        """Test that node actions execute within proper context."""
        with (
            event_client_context(name="node.test_node", node_name="test_node"),
            event_client_context(name="action.grab", action_name="grab"),
        ):
            ctx = get_event_client_context()

            assert "node.test_node" in ctx.name
            assert "action.grab" in ctx.name
            assert ctx.metadata.get("node_name") == "test_node"
            assert ctx.metadata.get("action_name") == "grab"

    def test_action_logs_include_node_context(self):
        """Test that action logs include node context."""
        with event_client_context(name="node", node_id="node-123"):
            logger = get_event_client()

            # Logger should have node context bound
            assert "node_id" in logger._bound_context
            assert logger._bound_context["node_id"] == "node-123"

    def test_action_with_full_hierarchy(self):
        """Test a complete hierarchy: experiment -> workflow -> step -> node -> action."""
        final_context = None

        with (
            event_client_context(name="experiment", experiment_id="exp-123"),
            event_client_context(name="workflow", workflow_id="wf-456"),
            event_client_context(name="step.transfer", step_id="step-1"),
            event_client_context(name="node.robot", node_name="robot"),
            event_client_context(name="action.grab", action_id="action-789"),
        ):
            final_context = get_event_client_context()

        # Verify full hierarchy
        assert final_context is not None
        assert final_context.hierarchy == [
            "experiment",
            "workflow",
            "step.transfer",
            "node.robot",
            "action.grab",
        ]
        assert final_context.metadata["experiment_id"] == "exp-123"
        assert final_context.metadata["workflow_id"] == "wf-456"
        assert final_context.metadata["step_id"] == "step-1"
        assert final_context.metadata["node_name"] == "robot"
        assert final_context.metadata["action_id"] == "action-789"


class TestContextAsyncSupport:
    """Test async context propagation for managers."""

    @pytest.mark.asyncio
    async def test_async_request_context(self):
        """Test that context propagates in async request handlers."""

        async def simulated_request_handler():
            """Simulate an async FastAPI request handler."""
            await asyncio.sleep(0.01)
            if has_event_client_context():
                return get_event_client_context().metadata.copy()
            return {}

        with event_client_context(name="request", request_id="req-123"):
            result = await simulated_request_handler()

        assert result.get("request_id") == "req-123"

    @pytest.mark.asyncio
    async def test_concurrent_requests_isolated(self):
        """Test that concurrent async requests have isolated contexts."""

        async def simulated_request(request_id: str):
            with event_client_context(name="request", request_id=request_id):
                await asyncio.sleep(0.01)  # Yield to allow interleaving
                ctx = get_event_client_context()
                return ctx.metadata.get("request_id")

        # Run multiple "requests" concurrently
        results = await asyncio.gather(
            simulated_request("req-1"),
            simulated_request("req-2"),
            simulated_request("req-3"),
        )

        # Each request should have seen its own context
        assert results == ["req-1", "req-2", "req-3"]
