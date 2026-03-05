Module madsci.common.templates.engine
=====================================
Template engine for MADSci.

This module provides the engine for rendering templates into generated projects.

Functions
---------

`camel_case(value: str) ‑> str`
:   Convert snake_case to camelCase.
    
    Args:
        value: A snake_case string.
    
    Returns:
        The camelCase version.
    
    Example:
        >>> camel_case("my_module_name")
        'myModuleName'

`kebab_case(value: str) ‑> str`
:   Convert snake_case to kebab-case.
    
    Args:
        value: A snake_case string.
    
    Returns:
        The kebab-case version.
    
    Example:
        >>> kebab_case("my_module_name")
        'my-module-name'

`pascal_case(value: str) ‑> str`
:   Convert snake_case to PascalCase.
    
    Args:
        value: A snake_case string.
    
    Returns:
        The PascalCase version.
    
    Example:
        >>> pascal_case("my_module_name")
        'MyModuleName'

Classes
-------

`TemplateEngine(template_dir: pathlib.Path, *, sandboxed: bool = False)`
:   Engine for rendering MADSci templates.
    
    This class handles loading a template, validating parameters, and
    rendering the template files to an output directory.
    
    Example:
        engine = TemplateEngine(Path("templates/module/device"))
    
        # Get default parameter values
        defaults = engine.get_default_values()
    
        # Validate custom parameters
        errors = engine.validate_parameters({"module_name": "my_device"})
    
        # Render the template
        result = engine.render(
            output_dir=Path("./output"),
            parameters={"module_name": "my_device"},
        )
    
    Initialize the template engine.
    
    Args:
        template_dir: Path to the template directory containing template.yaml.
        sandboxed: If True, use Jinja2's SandboxedEnvironment to restrict
            template code execution.  Recommended for user/remote templates.
    
    Raises:
        TemplateError: If the template manifest cannot be loaded.

    ### Methods

    `get_default_values(self) ‑> dict[str, typing.Any]`
    :   Get default values for all parameters.
        
        Returns:
            Dictionary of parameter names to their default values.

    `render(self, output_dir: pathlib.Path, parameters: dict[str, typing.Any], dry_run: bool = False) ‑> madsci.common.types.template_types.GeneratedProject`
    :   Render template to output directory.
        
        Args:
            output_dir: Directory to write output files.
            parameters: Parameter values.
            dry_run: If True, don't write files, just return what would be created.
        
        Returns:
            GeneratedProject with details of what was created.
        
        Raises:
            TemplateValidationError: If parameter validation fails.
            TemplateHookError: If a post-generation hook fails.

    `validate_parameters(self, values: dict[str, typing.Any]) ‑> list[str]`
    :   Validate parameter values against manifest.
        
        Args:
            values: Parameter values to validate.
        
        Returns:
            List of validation error messages (empty if valid).

`TemplateError(*args, **kwargs)`
:   Base exception for template errors.

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException

    ### Descendants

    * madsci.common.templates.engine.TemplateHookError
    * madsci.common.templates.engine.TemplateValidationError

`TemplateHookError(*args, **kwargs)`
:   Error running template hook.

    ### Ancestors (in MRO)

    * madsci.common.templates.engine.TemplateError
    * builtins.Exception
    * builtins.BaseException

`TemplateValidationError(errors: list[str])`
:   Validation errors for template parameters.
    
    Initialize with a list of validation errors.
    
    Args:
        errors: List of validation error messages.

    ### Ancestors (in MRO)

    * madsci.common.templates.engine.TemplateError
    * builtins.Exception
    * builtins.BaseException