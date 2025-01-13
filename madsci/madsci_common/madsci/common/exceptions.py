"""Exceptions common across the MADSci Framework"""


class ActionMissingArgumentError(ValueError):
    """An action was requested with a missing argument"""


class ActionMissingFileError(ValueError):
    """An action was requested with a missing file argument"""


class ActionNotImplementedError(ValueError):
    """An action was requested, but isn't implemented by the node"""

class WorkflowFailedException(Exception):
    """Raised when a workflow fails"""

    def __init__(self, message: str):
        """Initializes the exception"""
        super().__init__(message)
        self.message = message

class WorkflowCanceledException(Exception):
    """Raised when a workflow is canceled"""

    def __init__(self, message: str):
        """Initializes the exception"""
        super().__init__(message)
        self.message = message
