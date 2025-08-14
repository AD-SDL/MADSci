"""The Modular Autonomous Discovery for Science (MADSci) Python Client and CLI."""

from typing import TYPE_CHECKING

from madsci.client.data_client import DataClient
from madsci.client.event_client import EventClient
from madsci.client.experiment_client import ExperimentClient
from madsci.client.node import NODE_CLIENT_MAP, AbstractNodeClient, RestNodeClient
from madsci.client.resource_client import ResourceClient
from madsci.client.workcell_client import WorkcellClient

if TYPE_CHECKING:
    from madsci.client.experiment_application import ExperimentApplication


def __getattr__(name: str) -> object:
    """Lazy import for ExperimentApplication to avoid circular imports."""
    if name == "ExperimentApplication":
        from madsci.client.experiment_application import ExperimentApplication  # noqa

        return ExperimentApplication
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "NODE_CLIENT_MAP",
    "AbstractNodeClient",
    "DataClient",
    "EventClient",
    "ExperimentApplication",
    "ExperimentClient",
    "ResourceClient",
    "RestNodeClient",
    "WorkcellClient",
]
