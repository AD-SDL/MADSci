"""Experiment Application framework for MADSci.

This module provides various experiment modalities for running MADSci experiments:

- **ExperimentScript**: Simple run-once experiments (scripts)
- **ExperimentNotebook**: Jupyter notebook-friendly experiments
- **ExperimentTUI**: Interactive terminal UI experiments
- **ExperimentNode**: REST server mode experiments
- **ExperimentBase**: Base class for custom modalities

The legacy ExperimentApplication is deprecated and will be removed in v0.8.0.
Use one of the specific modalities instead.

Example:
    ```python
    from madsci.experiment_application import ExperimentScript
    from madsci.common.types.experiment_types import ExperimentDesign

    class MyExperiment(ExperimentScript):
        experiment_design = ExperimentDesign(
            experiment_name="My Experiment"
        )

        def run_experiment(self):
            result = self.workcell_client.run_workflow("synthesis")
            return result

    if __name__ == "__main__":
        MyExperiment().run()
    ```
"""

from .experiment_application import ExperimentApplication, ExperimentApplicationConfig
from .experiment_base import ExperimentBase, ExperimentBaseConfig
from .experiment_node import ExperimentNode, ExperimentNodeConfig
from .experiment_notebook import ExperimentNotebook, ExperimentNotebookConfig
from .experiment_script import ExperimentScript, ExperimentScriptConfig
from .experiment_tui import ExperimentTUI, ExperimentTUIConfig

__all__ = [
    "ExperimentApplication",
    "ExperimentApplicationConfig",
    "ExperimentBase",
    "ExperimentBaseConfig",
    "ExperimentNode",
    "ExperimentNodeConfig",
    "ExperimentNotebook",
    "ExperimentNotebookConfig",
    "ExperimentScript",
    "ExperimentScriptConfig",
    "ExperimentTUI",
    "ExperimentTUIConfig",
]
