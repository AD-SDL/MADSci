"""Exceptions common across the MADSci Framework"""


class ActionMissingArgumentError(ValueError):
    """An action was requested with a missing argument"""


class ActionMissingFileError(ValueError):
    """An action was requested with a missing file argument"""


class ActionNotImplementedError(ValueError):
    """An action was requested, but isn't implemented by the node"""


class WorkflowFailedError(Exception):
    """Raised when a workflow fails"""

    def __init__(self, message: str) -> "WorkflowFailedError":
        """Initializes the exception"""
        super().__init__(message)
        self.message = message


class WorkflowCanceledError(Exception):
    """Raised when a workflow is canceled"""

    def __init__(self, message: str) -> "WorkflowCanceledError":
        """Initializes the exception"""
        super().__init__(message)
        self.message = message


class ExperimentCancelledError(Exception):
    """Raised in an experiment application when an experiment is cancelled"""

    def __init__(self, message: str) -> "ExperimentCancelledError":
        """Initializes the exception"""
        super().__init__(message)
        self.message = message


class ExperimentFailedError(Exception):
    """Raised in an experiment application when an experiment fails."""

    def __init__(self, message: str) -> "ExperimentCancelledError":
        """Initializes the exception"""
        super().__init__(message)
        self.message = message
