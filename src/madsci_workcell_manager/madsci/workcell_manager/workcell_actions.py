"""Built-in actions for the Workcell Manager, which don't require a node to be specified."""

import time

from madsci.common.types.action_types import ActionResult
from madsci.workcell_manager.workflow_utils import ActionSucceeded


def wait(seconds: int) -> ActionResult:
    """Waits for a specified number of seconds"""
    time.sleep(seconds)
    return ActionSucceeded()


workcell_actions = {"wait": wait}
