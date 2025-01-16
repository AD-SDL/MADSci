"""Exceptions common across the MADSci Framework"""


class ActionMissingArgumentError(ValueError):
    """An action was requested with a missing argument"""


class ActionMissingFileError(ValueError):
    """An action was requested with a missing file argument"""


class ActionNotImplementedError(ValueError):
    """An action was requested, but isn't implemented by the node"""
