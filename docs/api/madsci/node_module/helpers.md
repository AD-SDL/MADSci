Module madsci.node_module.helpers
=================================
Helper methods used by the MADSci node module implementations.

Functions
---------

`action(*args: Any, **kwargs: Any) ‑> Callable`
:   Decorator to mark a method as an action handler.

    This decorator adds metadata to the decorated function, indicating that it is
    an action handler within the MADSci framework. The metadata includes the action
    name, description, and whether the action is blocking.

    Keyword Args:
        name (str, optional): The name of the action. Defaults to the function name.
        description (str, optional): A description of the action. Defaults to the function docstring.
        blocking (bool, optional): Indicates if the action is blocking. Defaults to False.

    Returns:
        Callable: The decorated function with added metadata.

`create_dynamic_model(type_hint: Type[Any], field_name: str = 'data', model_name: str = 'DynamicModel') ‑> Type[pydantic.main.BaseModel]`
:   Create a dynamic Pydantic model from a Python type hint.

    This function takes a Python type hint and creates a Pydantic model class
    that can validate data of that type. It supports basic types, generic types,
    Optional types, Union types, and existing Pydantic models.

    Args:
        type_hint: The Python type hint to create a model for
        field_name: The name of the field in the generated model (default: "data")
        model_name: The name of the generated model class (default: "DynamicModel")

    Returns:
        A Pydantic model class that validates the specified type

    Examples:
        >>> IntModel = create_dynamic_model(int)
        >>> instance = IntModel(data=42)
        >>> instance.data
        42

        >>> ListModel = create_dynamic_model(List[str], field_name="items")
        >>> instance = ListModel(items=["a", "b", "c"])
        >>> instance.items
        ['a', 'b', 'c']

`get_named_input(main_string: str, plural: str) ‑> list[str]`
:   gets a named input to an action_result constructor and returns a list of the keys provided

`parse_result(returned: Any) ‑> list[madsci.common.types.action_types.ActionResultDefinition]`
:   Parse a single result from an Action.

    Uses TypeAnalyzer for robust type analysis.
    ActionResult subclasses are recognized and return empty list
    as they are handled by the MADSci framework.

`parse_results(func: Callable) ‑> list[madsci.common.types.action_types.ActionResultDefinition]`
:   Get the resulting data from an Action

`split_top_level(s: str) ‑> list[str]`
:   Splits a string into top-level key-value pairs while keeping
    nested braces/parentheses intact.
