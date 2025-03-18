"""Helper functions for manipulating data"""

import copy
import re
from typing import Any


def walk_and_replace(
    input_dict: dict[str, Any], input_parameters: dict[str, Any]
) -> dict[str, Any]:
    """Recursively walk the input dictionary and replace all parameters"""
    updated_dict = copy.deepcopy(input_dict)
    for key, val in input_dict.items():
        if type(val) is str:
            updated_dict[key] = value_substitution(val, input_parameters)
        elif type(input_dict[key]) is dict:
            updated_dict[key] = walk_and_replace(val, input_parameters)
        if type(key) is str:
            new_key = value_substitution(key, input_parameters)
            updated_dict[new_key] = updated_dict[key]
            if key is not new_key:
                updated_dict.pop(key, None)
    return updated_dict


def value_substitution(input_string: str, input_parameters: dict[str, Any]) -> str:
    """Perform $-string and ${}-string substitution on input string, returns string with substituted values"""
    # * Check if the entire string is a simple parameter reference
    if type(input_string) is str and re.match(r"^\$[A-z0-9_\-]*$", input_string):
        if input_string.strip("$") in input_parameters:
            input_string = input_parameters[input_string.strip("$")]
    else:
        # * Replace all parameter references contained in the string
        working_string = input_string
        for match in re.findall(r"((?<!\$)\$(?!\$)[A-z0-9_\-\{]*)(\})", input_string):
            if match[0][1] == "{":
                # * Matches the form ${parameter}
                param_name = match[0].strip("$")
                param_name = param_name.strip("{")
                if param_name in input_parameters:
                    working_string = re.sub(
                        r"((?<!\$)\$(?!\$)[A-z0-9_\-\{]*)(\})",
                        str(input_parameters[param_name]),
                        working_string,
                    )
                    input_string = working_string
            else:
                raise SyntaxError(
                    "Missing opening { in parameter insertion: " + match[0] + "}"
                )
        for match in re.findall(
            r"((?<!\$)\$(?!\$)[A-z0-9_\-]*)(?![A-z0-9_\-])", input_string
        ):
            # * Matches the form $parameter
            param_name = match.strip("$")
            if param_name in input_parameters:
                working_string = re.sub(
                    r"((?<!\$)\$(?!\$)[A-z0-9_\-]*)(?![A-z0-9_\-])",
                    str(input_parameters[param_name]),
                    working_string,
                )
                input_string = working_string
    return input_string
