Module madsci.common.types.template_types
=========================================
Template system types for MADSci.

This module defines the types used by the template system for scaffolding
new MADSci components (modules, nodes, experiments, workflows, labs).

Classes
-------

`GeneratedProject(**data: Any)`
:   Result of template generation.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `created_at: datetime.datetime`
    :

    `files_created: list[pathlib.Path]`
    :

    `hooks_executed: list[str]`
    :

    `model_config`
    :

    `output_directory: pathlib.Path`
    :

    `parameters_used: dict[str, typing.Any]`
    :

    `skills_included: list[str]`
    :

    `template_name: str`
    :

    `template_version: str`
    :

`ParameterChoice(**data: Any)`
:   A choice option for choice/multi_choice parameters.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `default: bool`
    :

    `description: str | None`
    :

    `label: str`
    :

    `model_config`
    :

    `value: str`
    :

`ParameterType(value, names=None, *, module=None, qualname=None, type=None, start=1)`
:   Types of template parameters.

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `BOOLEAN`
    :

    `CHOICE`
    :

    `FLOAT`
    :

    `INTEGER`
    :

    `MULTI_CHOICE`
    :

    `PATH`
    :

    `STRING`
    :

`TemplateCategory(value, names=None, *, module=None, qualname=None, type=None, start=1)`
:   Categories of templates.

    ### Ancestors (in MRO)

    * builtins.str
    * enum.Enum

    ### Class variables

    `COMM`
    :

    `EXPERIMENT`
    :

    `INTERFACE`
    :

    `LAB`
    :

    `MODULE`
    :

    `NODE`
    :

    `WORKCELL`
    :

    `WORKFLOW`
    :

`TemplateFile(**data: Any)`
:   A file to be generated from template.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `condition: str | None`
    :

    `destination: str`
    :

    `model_config`
    :

    `source: str`
    :

`TemplateHook(**data: Any)`
:   A hook to run after generation.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `command: str`
    :

    `continue_on_error: bool`
    :

    `description: str | None`
    :

    `model_config`
    :

    `working_directory: str | None`
    :

`TemplateInfo(**data: Any)`
:   Information about an available template.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `category: madsci.common.types.template_types.TemplateCategory`
    :

    `description: str`
    :

    `id: str`
    :

    `model_config`
    :

    `name: str`
    :

    `path: pathlib.Path`
    :

    `source: str`
    :

    `tags: list[str]`
    :

    `version: str`
    :

`TemplateManifest(**data: Any)`
:   The template.yaml manifest file.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `author: str | None`
    :

    `category: madsci.common.types.template_types.TemplateCategory`
    :

    `description: str`
    :

    `files: list[madsci.common.types.template_types.TemplateFile]`
    :

    `hooks: dict[str, list[madsci.common.types.template_types.TemplateHook]] | None`
    :

    `license: str | None`
    :

    `min_madsci_version: str | None`
    :

    `model_config`
    :

    `name: str`
    :

    `parameters: list[madsci.common.types.template_types.TemplateParameter]`
    :

    `schema_version: str`
    :

    `skills: list[str]`
    :

    `tags: list[str]`
    :

    `version: str`
    :

`TemplateParameter(**data: Any)`
:   Definition of a template parameter.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * madsci.common.types.base_types.MadsciBaseModel
    * pydantic.main.BaseModel

    ### Class variables

    `choices: list[madsci.common.types.template_types.ParameterChoice] | None`
    :

    `default: Any | None`
    :

    `description: str`
    :

    `max: float | int | None`
    :

    `max_length: int | None`
    :

    `min: float | int | None`
    :

    `min_length: int | None`
    :

    `model_config`
    :

    `name: str`
    :

    `pattern: str | None`
    :

    `required: bool`
    :

    `type: madsci.common.types.template_types.ParameterType`
    :