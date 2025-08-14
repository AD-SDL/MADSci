"""The Modular Autonomous Discovery for Science (MADSci) Python Client and CLI."""

import sys
import types
from madsci.client.data_client import DataClient
from madsci.client.event_client import EventClient
from madsci.client.experiment_application import ExperimentApplication
from madsci.client.experiment_client import ExperimentClient
from madsci.client.node import NODE_CLIENT_MAP, AbstractNodeClient, RestNodeClient
from madsci.client.resource_client import ResourceClient
from madsci.client.workcell_client import WorkcellClient
from madsci.client.workcell_client import WorkcellClient as WorkflowClient
from madsci.client import workcell_client


workflow_client = types.ModuleType('madsci.client.workflow_client')
workflow_client.__dict__.update(workcell_client.__dict__)
sys.modules['madsci.client.workflow_client'] = workflow_client

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
    "WorkflowClient"
]
