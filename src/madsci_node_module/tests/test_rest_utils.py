"""Shared utilities for MADSci node module tests."""

import contextlib
import time
from typing import Optional

from starlette.testclient import TestClient


def wait_for_node_ready(
    client: TestClient, timeout: float = 10.0, allow_initializing: bool = False
) -> bool:
    """Wait for node to be ready before executing actions.

    Args:
        client: FastAPI test client
        timeout: Maximum time to wait in seconds (increased default to 10s)
        allow_initializing: If True, accept nodes that are initializing but responsive

    Returns:
        True if node is ready, False if timeout
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        with contextlib.suppress(Exception):
            response = client.get("/status")
            if response.status_code == 200:
                status_data = response.json()
                if status_data.get("ready", False):
                    return True
                # If we allow initializing nodes and it's not errored, consider it usable
                if (
                    allow_initializing
                    and status_data.get("initializing", False)
                    and not status_data.get("errored", False)
                ):
                    return True
        time.sleep(0.1)  # Check every 100ms
    return False


def execute_action_and_wait(
    client: TestClient,
    action_name: str,
    parameters: Optional[dict] = None,
    timeout: float = 10.0,
) -> dict:
    """Execute an action and wait for it to complete.

    Args:
        client: FastAPI test client
        action_name: Name of the action to execute
        parameters: Optional parameters for the action
        timeout: Maximum time to wait for completion

    Returns:
        Final action result dict

    Raises:
        AssertionError: If action fails or times out
    """
    if parameters is None:
        parameters = {}

    # Wait for node to be ready first
    assert wait_for_node_ready(client, timeout=timeout), "Node failed to become ready"

    # Create action
    response = client.post(f"/action/{action_name}", json=parameters)
    assert response.status_code == 200, f"Failed to create action: {response.text}"
    action_id = response.json()["action_id"]

    # Start action
    response = client.post(f"/action/{action_name}/{action_id}/start")
    assert response.status_code == 200, f"Failed to start action: {response.text}"

    # Wait for completion
    start_time = time.time()
    while time.time() - start_time < timeout:
        response = client.get(f"/action/{action_id}/result")
        if response.status_code == 200:
            result = response.json()
            if result.get("status") in ["succeeded", "failed", "cancelled"]:
                return result
        time.sleep(0.1)  # Check every 100ms

    raise AssertionError(f"Action {action_name} timed out after {timeout} seconds")
