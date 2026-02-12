Module madsci.common.exceptions
===============================
Exceptions common across the MADSci Framework

Classes
-------

`ActionMissingArgumentError(*args, **kwargs)`
:   An action was requested with a missing argument

    ### Ancestors (in MRO)

    * builtins.ValueError
    * builtins.Exception
    * builtins.BaseException

`ActionMissingFileError(*args, **kwargs)`
:   An action was requested with a missing file argument

    ### Ancestors (in MRO)

    * builtins.ValueError
    * builtins.Exception
    * builtins.BaseException

`ActionNotImplementedError(*args, **kwargs)`
:   An action was requested, but isn't implemented by the node

    ### Ancestors (in MRO)

    * builtins.ValueError
    * builtins.Exception
    * builtins.BaseException

`ExperimentCancelledError(message: str)`
:   Raised in an experiment application when an experiment is cancelled

    Initializes the exception

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException

`ExperimentFailedError(message: str)`
:   Raised in an experiment application when an experiment fails.

    Initializes the exception

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException

`LocationNotFoundError(message: str)`
:   Raised when a location cannot be found by name or ID

    Initializes the exception

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException

`WorkflowCanceledError(message: str)`
:   Raised when a workflow is canceled

    Initializes the exception

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException

`WorkflowFailedError(message: str)`
:   Raised when a workflow fails

    Initializes the exception

    ### Ancestors (in MRO)

    * builtins.Exception
    * builtins.BaseException
