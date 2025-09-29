"""Helper methods used by the MADSci node module implementations."""

import inspect
import json
import tempfile
from pathlib import Path, PureWindowsPath
from typing import Any, Callable
from zipfile import ZipFile

import regex
from madsci.common.types.action_types import (
    ActionDatapoints,
    ActionFiles,
    ActionJSON,
    ActionResult,
    ActionResultDefinition,
    DatapointActionResultDefinition,
    FileActionResultDefinition,
    JSONActionResultDefinition,
)
from madsci.common.types.datapoint_types import (
    FileDataPoint,
    ObjectStorageDataPoint,
    ValueDataPoint,
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
        func.__madsci_action_result_definitions__ = parse_results(func)
        return func

    # * If the decorator is used without arguments, return the decorator function
    if len(args) == 1 and callable(args[0]):
        return decorator(args[0])
    return decorator


def split_top_level(s: str) -> list[str]:  # noqa C901
    """
    Splits a string into top-level key-value pairs while keeping
    nested braces/parentheses intact.
    """
    parts = []
    current = []
    depth_curly = 0
    depth_paren = 0
    in_string = False
    escape = False

    for ch in s:
        if escape:
            current.append(ch)
            escape = False
            continue

        if ch == "\\":
            current.append(ch)
            escape = True
            continue

        if ch in {'"', "'"}:  # toggle string state
            in_string = not in_string
            current.append(ch)
            continue

        if not in_string:
            if ch == "{":
                depth_curly += 1
            elif ch == "}":
                depth_curly -= 1
            elif ch == "(":
                depth_paren += 1
            elif ch == ")":
                depth_paren -= 1
            elif ch == "," and depth_curly == 0 and depth_paren == 0:
                # Top-level comma → split
                parts.append("".join(current).strip())
                current = []
                continue

        current.append(ch)

    if current:
        parts.append("".join(current).strip())

    return parts


def get_named_input(main_string: str, plural: str) -> list[str]:
    """gets a named input to an action_result constructor and returns a list of the keys provided"""
    result_list = []
    data = regex.search(plural + r"=(\{(?:[^{}]|(?1))*\})", main_string)
    singular = plural[:-1] if plural[-1] == "s" else plural
    if data is not None:
        data = data.group(0)[len(plural) + 2 : -1]
        data = split_top_level(data)
        if len(data) > 0:
            for datum in data:
                name = datum.split(":")[0]
                if (name[0] == '"' and name[-1] == '"') or (
                    name[0] == "'" and name[-1] == "'"
                ):
                    result_list.append(name[1:-1])
                else:
                    string1 = f"{singular} label : "
                    string2 = f"{name} threw an error, default {singular} labels should be a constant string, not parameterized or variables"
                    raise ValueError(string1.capitalize() + string2)
    return result_list


def parse_result(returned: Any) -> list[ActionResultDefinition]:
    """Parse a single result from an Action"""

    if issubclass(returned, ActionFiles):
        for key, value in returned.__annotations__.items():
            if value is not Path:
                raise ValueError(
                    f"All fields in an ActionFiles subclass must be of type Path, but field {key} is of type {value}",
                )
        return [
            FileActionResultDefinition(result_label=key)
            for key in returned.__annotations__
        ]
    if issubclass(returned, ActionJSON):
        return [
            JSONActionResultDefinition(result_label=key, data_type=value.__name__)
            for key, value in returned.__annotations__.items()
        ]
    if issubclass(returned, ActionDatapoints):
        for key, value in returned.__annotations__.items():
            if value not in [FileDataPoint, ValueDataPoint, ObjectStorageDataPoint]:
                raise ValueError(
                    f"All fields in an ActionDatapoints subclass must be datapoints but field {key} is of type {value}",
                )
        return [
            DatapointActionResultDefinition(result_label=key)
            for key in returned.__annotations__
        ]
    if returned not in [str, int, float, bool, dict, list]:
        raise ValueError(
            f"Action return type must be a subclass of ActionFiles, ActionJSON, ActionDatapoints, Path, str, int, float, bool, dict, or list but got {returned}",
        )

    return [
        JSONActionResultDefinition(result_label="data", data_type=returned.__name__)
    ]


def parse_results(func: Callable) -> list[ActionResultDefinition]:
    """Get the resulting data from an Action"""
    returned = inspect.signature(func).return_annotation

    if returned is inspect.Signature.empty or returned is None:
        return []
    if getattr(returned, "__origin__", None) is tuple:
        result_definitions = []
        for result in returned.__args__:
            result_definitions.extend(parse_result(result))
    elif returned is Path:
        result_definitions = [FileActionResultDefinition(result_label="file")]
    else:
        result_definitions = parse_result(returned)
    return result_definitions


def action_response_to_headers(action_response: ActionResult) -> dict[str, str]:
    """Converts the response to a dictionary of headers"""
    if isinstance(action_response.files, ActionFiles):
        files_serializeable = action_response.files.model_dump(mode="json")

    if isinstance(action_response.files, Path):
        files_serializeable = str(action_response.files)
    if isinstance(action_response.datapoints, ActionDatapoints):
        action_response.datapoints = action_response.datapoints.model_dump(mode="json")
    if isinstance(action_response.json_data, ActionJSON):
        action_response.json_data = action_response.json_data.model_dump(mode="json")
    return {
        "x-madsci-action-id": action_response.action_id,
        "x-madsci-status": action_response.status.value,
        "x-madsci-datapoints": json.dumps(action_response.datapoints),
        "x-madsci-errors": json.dumps(action_response.errors),
        "x-madsci-files": json.dumps(files_serializeable),
        "x-madsci-json_data": json.dumps(action_response.json_data),
    }


class ActionResultWithFiles(FileResponse):
    """Action response from a REST-based node."""

    @classmethod
    def from_action_response(cls: Any, action_response: ActionResult) -> ActionResult:
        """Create an ActionResultWithFiles from an ActionResult."""

        if isinstance(action_response.files, Path):
            return ActionResultWithFiles(
                path=action_response.files,
                headers=action_response_to_headers(action_response),
            )
        action_response_dict = action_response.files.model_dump()
        with tempfile.NamedTemporaryFile(
            suffix=".zip",
            delete=False,
        ) as temp_zipfile_path:
            temp_zip = ZipFile(temp_zipfile_path.name, "w")
            for file in action_response_dict:
                temp_zip.write(
                    action_response_dict[file],
                    PureWindowsPath(action_response_dict[file]).name,
                )
                action_response_dict[file] = str(
                    PureWindowsPath(action_response_dict[file]).name,
                )
            action_response.files = ActionFiles.model_validate(
                action_response_dict,
            )
            return ActionResultWithFiles(
                path=temp_zipfile_path.name,
                headers=action_response_to_headers(action_response),
            )
