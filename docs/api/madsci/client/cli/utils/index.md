Module madsci.client.cli.utils
==============================
CLI utilities for MADSci.

This module provides common utilities for CLI commands.

Sub-modules
-----------
* madsci.client.cli.utils.config
* madsci.client.cli.utils.output

Functions
---------

`error(console: rich.console.Console, message: str, details: str | None = None) ‑> None`
:   Print error message with red X.

    Args:
        console: Rich console instance.
        message: Error message.
        details: Optional additional details.

`info(console: rich.console.Console, message: str) ‑> None`
:   Print info message with blue info icon.

    Args:
        console: Rich console instance.
        message: Info message.

`success(console: rich.console.Console, message: str) ‑> None`
:   Print success message with green checkmark.

    Args:
        console: Rich console instance.
        message: Message to print.

`warning(console: rich.console.Console, message: str, details: str | None = None) ‑> None`
:   Print warning message with yellow warning sign.

    Args:
        console: Rich console instance.
        message: Warning message.
        details: Optional additional details.

Classes
-------

`MadsciCLIConfig(**values: Any)`
:   Configuration for MADSci CLI.

    Configuration is loaded from multiple sources in order of precedence:
    1. Command-line arguments
    2. Environment variables (MADSCI_ prefix)
    3. Configuration file (~/.madsci/config.toml or local .madsci/config.toml)
    4. Default values

    Create a new model by parsing and validating input data from keyword arguments.

    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.

    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * pydantic_settings.main.BaseSettings
    * pydantic.main.BaseModel

    ### Class variables

    `color_enabled: bool`
    :

    `data_manager_url: pydantic.networks.AnyUrl`
    :

    `default_output_format: str`
    :

    `event_manager_url: pydantic.networks.AnyUrl`
    :

    `experiment_manager_url: pydantic.networks.AnyUrl`
    :

    `lab_url: pydantic.networks.AnyUrl`
    :

    `location_manager_url: pydantic.networks.AnyUrl`
    :

    `model_config: ClassVar[pydantic_settings.main.SettingsConfigDict]`
    :

    `registry_path: pathlib.Path`
    :

    `resource_manager_url: pydantic.networks.AnyUrl`
    :

    `template_dir: pathlib.Path | None`
    :

    `workcell_manager_url: pydantic.networks.AnyUrl`
    :

    ### Static methods

    `get_config_paths() ‑> list[pathlib.Path]`
    :   Get list of possible config file paths in order of precedence.

        Returns:
            List of Path objects to check for config files.

    `load(config_path: str | None = None) ‑> madsci.client.cli.utils.config.MadsciCLIConfig`
    :   Load configuration from file or defaults.

        Args:
            config_path: Optional explicit path to config file.

        Returns:
            MadsciCLIConfig instance with loaded values.

    ### Methods

    `save(self, path: pathlib.Path | None = None) ‑> None`
    :   Save configuration to a TOML file.

        Args:
            path: Path to save to. Defaults to ~/.madsci/config.toml.
