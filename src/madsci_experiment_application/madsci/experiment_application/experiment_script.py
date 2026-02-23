"""ExperimentScript modality for simple run-once experiments.

This module provides the ExperimentScript class, the simplest experiment
modality designed for experiments that run once from start to finish
without user interaction.
"""

from typing import Any, ClassVar, Optional, Union

from madsci.common.types.experiment_types import ExperimentDesign
from madsci.experiment_application.experiment_base import (
    ExperimentBase,
    ExperimentBaseConfig,
)
from pydantic import AnyUrl, Field


class ExperimentScriptConfig(ExperimentBaseConfig):
    """Configuration for script-based experiments.

    Extends ExperimentBaseConfig with options for passing arguments
    to the run_experiment method.
    """

    run_args: list[Any] = Field(
        default_factory=list,
        title="Run Arguments",
        description="Positional arguments to pass to run_experiment().",
    )
    run_kwargs: dict[str, Any] = Field(
        default_factory=dict,
        title="Run Keyword Arguments",
        description="Keyword arguments to pass to run_experiment().",
    )


class ExperimentScript(ExperimentBase):
    """Experiment modality for simple run-once scripts.

    This is the simplest experiment modality, designed for experiments
    that run once from start to finish without interaction. It provides
    a clean, minimal API for running experiments.

    The recommended pattern is to:
    1. Subclass ExperimentScript
    2. Set experiment_design as a class attribute
    3. Override run_experiment() with your experiment logic
    4. Call run() or main() to execute

    Example:
        ```python
        from madsci.common.types.experiment_types import ExperimentDesign
        from madsci.experiment_application import ExperimentScript

        class MyExperiment(ExperimentScript):
            experiment_design = ExperimentDesign(
                experiment_name="My Synthesis Experiment",
                experiment_description="Synthesize compound X"
            )

            def run_experiment(self):
                # Your experiment logic here
                result = self.workcell_client.run_workflow("synthesis")
                return {"yield": result.get("product_mass", 0)}

        if __name__ == "__main__":
            MyExperiment().run()
        ```

    Alternative using run_experiment directly:
        ```python
        class MyExperiment(ExperimentScript):
            experiment_design = ExperimentDesign(
                experiment_name="Parameterized Experiment"
            )

            def run_experiment(self, temperature: float, duration: int):
                # Parameterized experiment
                return self.workcell_client.run_workflow(
                    "synthesis",
                    parameters={"temp": temperature, "time": duration}
                )

        if __name__ == "__main__":
            # Pass parameters via run()
            MyExperiment().run(temperature=25.0, duration=60)

            # Or via config
            config = ExperimentScriptConfig(
                run_kwargs={"temperature": 25.0, "duration": 60}
            )
            MyExperiment(config=config).run()
        ```

    Attributes:
        experiment_design: The design template for this experiment
        config: Script-specific configuration
    """

    config: ExperimentScriptConfig  # type: ignore[assignment]
    config_model: ClassVar[type[ExperimentScriptConfig]] = ExperimentScriptConfig

    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the experiment.

        This is the main entry point for script-based experiments.
        It wraps run_experiment() with automatic lifecycle management
        using the manage_experiment() context manager.

        Arguments passed to run() are merged with config.run_args and
        config.run_kwargs, with directly passed arguments taking precedence.

        Args:
            *args: Positional arguments passed to run_experiment().
            **kwargs: Keyword arguments passed to run_experiment().

        Returns:
            Results from run_experiment().

        Example:
            # Simple execution
            result = MyExperiment().run()

            # With parameters
            result = MyExperiment().run(sample_id="ABC123", cycles=5)
        """
        # Merge config args with passed args (passed args take precedence)
        final_args = list(self.config.run_args) + list(args)
        final_kwargs = {**self.config.run_kwargs, **kwargs}

        with self.manage_experiment():
            return self.run_experiment(*final_args, **final_kwargs)

    @classmethod
    def main(
        cls,
        experiment_design: Optional[ExperimentDesign] = None,
        lab_server_url: Optional[Union[str, AnyUrl]] = None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Class method entry point for scripts.

        Convenience method for running experiments from __main__.
        Creates an instance and immediately runs the experiment.

        Args:
            experiment_design: Optional experiment design override.
            lab_server_url: Optional lab server URL override.
            *args: Positional arguments passed to run_experiment().
            **kwargs: Keyword arguments passed to run_experiment().

        Returns:
            Results from run_experiment().

        Example:
            ```python
            if __name__ == "__main__":
                MyExperiment.main()

            # With parameters
            if __name__ == "__main__":
                MyExperiment.main(sample_id="ABC123")
            ```
        """
        instance = cls(
            experiment_design=experiment_design,
            lab_server_url=lab_server_url,
        )
        return instance.run(*args, **kwargs)

    def run_experiment(self, *args: Any, **kwargs: Any) -> Any:
        """Override this method with your experiment logic.

        This method should contain the core experiment implementation.
        It is called within the manage_experiment() context, so:
        - The experiment is automatically started before this runs
        - The experiment is automatically ended after this completes
        - Exceptions are logged and the experiment marked as failed

        Args:
            *args: Positional arguments (from config.run_args or run()).
            **kwargs: Keyword arguments (from config.run_kwargs or run()).

        Returns:
            Experiment results. The format is up to you, but returning
            a dictionary is recommended for easy serialization.

        Example:
            ```python
            def run_experiment(self, sample_id: str, cycles: int = 1):
                results = []
                for i in range(cycles):
                    result = self.workcell_client.run_workflow(
                        "process_sample",
                        parameters={"sample_id": sample_id, "cycle": i}
                    )
                    results.append(result)
                return {"sample_id": sample_id, "results": results}
            ```
        """
        raise NotImplementedError(
            "Subclasses must implement run_experiment() with experiment logic"
        )
