Module madsci.common.data_manipulation
======================================
Helper functions for manipulating data

Functions
---------

`check_for_parameters(input_string: str, parameter_names: list[str]) ‑> bool`
:   Check if the input string contains any of the parameter names

`value_substitution(input_string: str, input_parameters: dict[str, typing.Any]) ‑> str`
:   Perform $-string and ${}-string substitution on input string, returns string with substituted values

`walk_and_replace(input_dict: dict[str, typing.Any], input_parameters: dict[str, typing.Any]) ‑> dict[str, typing.Any]`
:   Recursively walk the input dictionary and replace all parameters
