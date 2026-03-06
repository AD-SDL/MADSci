Module madsci.client.cli.commands.validate
==========================================
MADSci CLI validate command.

Validates MADSci configuration files (settings, manager, node, workflow definitions).

Classes
-------

`ValidationResult(path: str, valid: bool, file_type: str, errors: list[str] = <factory>, warnings: list[str] = <factory>)`
:   Result of validating a single file.

    ### Instance variables

    `errors: list[str]`
    :

    `file_type: str`
    :

    `path: str`
    :

    `valid: bool`
    :

    `warnings: list[str]`
    :

    ### Methods

    `to_dict(self) ‑> dict[str, typing.Any]`
    :   Convert to dictionary for JSON output.