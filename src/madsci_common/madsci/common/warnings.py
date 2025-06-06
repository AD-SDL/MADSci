"""Standard Warnings for the MADSci framework."""


class MadsciLocalOnlyWarning(Warning):
    """A warning that a component is being used in local-only mode, for a system where local only mode carries reduced functionality."""

    def __init__(self, message: str) -> "MadsciLocalOnlyWarning":
        """Initializes the warning."""
        super().__init__(message)
        self.message = message
