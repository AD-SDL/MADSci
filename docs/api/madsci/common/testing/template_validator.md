Module madsci.common.testing.template_validator
===============================================
Template Validator for MADSci.

Validates that templates can be instantiated and produce valid output.

Classes
-------

`TemplateValidationResult(template_name: str, success: bool, errors: list[str] = <factory>, warnings: list[str] = <factory>, generated_files: list[pathlib.Path] = <factory>, validation_details: dict[str, typing.Any] = <factory>)`
:   Result of validating a template.

    ### Instance variables

    `errors: list[str]`
    :

    `generated_files: list[pathlib.Path]`
    :

    `success: bool`
    :

    `template_name: str`
    :

    `validation_details: dict[str, typing.Any]`
    :

    `warnings: list[str]`
    :

    ### Methods

    `summary(self) ‑> str`
    :   Generate a human-readable summary.

`TemplateValidator(console: rich.console.Console | None = None, verbose: bool = False)`
:   Validates MADSci templates by instantiating them and checking output.
    
    Performs the following validations:
    - Template renders without errors
    - Generated Python files have valid syntax
    - Generated code passes ruff linting
    - (Optional) Generated code can be imported
    
    Initialize the template validator.
    
    Args:
        console: Rich console for output. If None, creates one.
        verbose: If True, print verbose output.

    ### Methods

    `print_results(self, results: list[madsci.common.testing.template_validator.TemplateValidationResult]) ‑> None`
    :   Print validation results in a formatted table.

    `validate_all_templates(self, templates_dir: pathlib.Path, **kwargs: Any) ‑> list[madsci.common.testing.template_validator.TemplateValidationResult]`
    :   Validate all templates in a directory.
        
        Args:
            templates_dir: Directory containing template subdirectories
            **kwargs: Additional arguments passed to validate_template
        
        Returns:
            List of validation results

    `validate_template(self, template_path: pathlib.Path, test_values: dict[str, typing.Any] | None = None, output_dir: pathlib.Path | None = None, check_ruff: bool = True, check_imports: bool = False) ‑> madsci.common.testing.template_validator.TemplateValidationResult`
    :   Validate a template by instantiating it with test values.
        
        Args:
            template_path: Path to the template directory (containing template.yaml)
            test_values: Values to use for template parameters. If None, uses defaults.
            output_dir: Directory for generated output. If None, uses temp dir.
            check_ruff: If True, run ruff check on generated code.
            check_imports: If True, attempt to import generated Python modules.
        
        Returns:
            TemplateValidationResult with details of the validation.