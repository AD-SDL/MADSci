"""Helper methods used by the MADSci node module implementations."""

import json
import tempfile
from pathlib import PureWindowsPath
from typing import Any, Callable
from zipfile import ZipFile

from madsci.common.types.action_types import (
    ActionResult,
)
from starlette.responses import FileResponse


def action(
    *args: Any,
    **kwargs: Any,
) -> Callable:
    """
    Decorator to mark a method as an action handler.

    This decorator adds metadata to the decorated function, indicating that it is
    an action handler within the MADSci framework. The metadata includes the action
    name, description, and whether the action is blocking.

    Keyword Args:
        name (str, optional): The name of the action. Defaults to the function name.
        description (str, optional): A description of the action. Defaults to the function docstring.
        blocking (bool, optional): Indicates if the action is blocking. Defaults to False.

    Returns:
        Callable: The decorated function with added metadata.
    """

    def decorator(func: Callable) -> Callable:
        if not isinstance(func, Callable):
            raise ValueError("The action decorator must be used on a callable object")
        func.__is_madsci_action__ = True

        # *Use provided action_name or function name
        name = kwargs.get("name")
        if not name:
            name = kwargs.get("action_name", func.__name__)
        # * Use provided description or function docstring
        description = kwargs.get("description", func.__doc__)
        blocking = kwargs.get("blocking", False)
        func.__madsci_action_name__ = name
        func.__madsci_action_description__ = description
        func.__madsci_action_blocking__ = blocking
        return func

    # * If the decorator is used without arguments, return the decorator function
    if len(args) == 1 and callable(args[0]):
        return decorator(args[0])
    return decorator


def action_response_to_headers(action_response: ActionResult) -> dict[str, str]:
    """Converts the response to a dictionary of headers"""
    for key in action_response.files:
        action_response.files[key] = str(action_response.files[key])
    return {
        "x-madsci-action-id": action_response.action_id,
        "x-madsci-status": action_response.status.value,
        "x-madsci-datapoints": json.dumps(action_response.datapoints),
        "x-madsci-errors": json.dumps(action_response.errors),
        "x-madsci-files": json.dumps(action_response.files),
        "x-madsci-data": json.dumps(action_response.data),
    }


class ActionResultWithFiles(FileResponse):
    """Action response from a REST-based node."""

    @classmethod
    def from_action_response(cls, action_response: ActionResult) -> ActionResult:
        """Create an ActionResultWithFiles from an ActionResult."""
        if len(action_response.files) == 1:
            return ActionResultWithFiles(
                path=next(iter(action_response.files.values())),
                headers=action_response_to_headers(action_response),
            )

        with tempfile.NamedTemporaryFile(
            suffix=".zip",
            delete=False,
        ) as temp_zipfile_path:
            temp_zip = ZipFile(temp_zipfile_path.name, "w")
            for file in action_response.files:
                temp_zip.write(
                    action_response.files[file],
                    PureWindowsPath(action_response.files[file]).name,
                )
                action_response.files[file] = str(
                    PureWindowsPath(action_response.files[file]).name,
                )

            return ActionResultWithFiles(
                path=temp_zipfile_path.name,
                headers=action_response_to_headers(action_response),
            )
