"""A module for testing advanced features of MADSci."""

from pathlib import Path

from madsci.common.types.action_types import (
    ActionFiles,
)
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.node_types import RestNodeConfig
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode
from pydantic import BaseModel, Field


class ExampleFileData(ActionFiles):
    """Example of returned files with labeled values"""

    log_file_1: Path
    log_file_2: Path


class AnalysisResult(BaseModel):
    """Example custom pydantic model for analysis results"""

    sample_id: str = Field(description="Unique identifier for the sample")
    concentration: float = Field(description="Measured concentration in mg/mL")
    ph_level: float = Field(description="pH level of the sample")
    temperature: float = Field(description="Temperature in Celsius during measurement")
    quality_score: int = Field(description="Quality score from 0-100", ge=0, le=100)
    notes: str = Field(default="", description="Additional notes about the analysis")


class ExperimentMetadata(BaseModel):
    """Example complex pydantic model with nested data"""

    experiment_id: str = Field(description="Unique experiment identifier")
    start_time: str = Field(description="ISO timestamp when experiment started")
    conditions: dict[str, float] = Field(description="Experimental conditions")
    parameters: list[str] = Field(description="List of measured parameters")
    status: str = Field(description="Current experiment status")
    results_summary: dict[str, int] = Field(description="Summary of results count")


class AdvancedExampleConfig(RestNodeConfig):
    """Configuration for the advanced example node module."""

    device_number: int = 0
    """The device number of the advanced example node."""


class AdvancedExampleNode(RestNode):
    """A fake advanced example node module for testing."""

    config: AdvancedExampleConfig = AdvancedExampleConfig()
    config_model = AdvancedExampleConfig

    @action
    def return_none(self) -> None:
        """Run a protocol on the liquid handler"""
        self.logger.log("returning none")

    @action
    def return_json(self) -> int:
        """Return a JSON object"""
        self.logger.log("returning int")
        return 5

    @action
    def return_dict(self) -> dict:
        """Return a JSON object"""
        self.logger.log("returning dict")
        return {"a": "dict"}

    @action
    def return_file(
        self,
    ) -> Path:
        """Return a file"""

        with (Path.home() / "test.txt").open("w") as f:
            self.logger.log_info(f.write("test"))

        return Path.home() / "test.txt"

    @action
    def return_file_and_json(
        self,
    ) -> tuple[int, Path]:
        """Return data and a file"""

        with (Path.home() / "test.txt").open("w") as f:
            self.logger.log_info(f.write("test"))
        path = Path.home() / "test.txt"

        # Must return json first then file
        return 5, path

    @action
    def return_labeled_json_values(self) -> dict:
        """Return labeled JSON values"""
        self.logger.log("returning labeled json")
        return {"example_value_1": "test", "example_value_2": 5}

    @action
    def return_labeled_file_values(self) -> ExampleFileData:
        """Return labeled file values"""

        with (Path.home() / "test1.txt").open("w") as f:
            self.logger.log_info(f.write("test1"))
        path1 = Path.home() / "test1.txt"
        with (Path.home() / "test2.txt").open("w") as f:
            self.logger.log_info(f.write("test2"))
        path2 = Path.home() / "test2.txt"

        return ExampleFileData(log_file_1=path1, log_file_2=path2)

    @action
    def return_labeled_file_and_json_values(
        self,
    ) -> tuple[dict, ExampleFileData]:
        """Return labeled file and json values"""

        with (Path.home() / "test1.txt").open("w") as f:
            self.logger.log_info(f.write("test1"))
        path1 = Path.home() / "test1.txt"
        with (Path.home() / "test2.txt").open("w") as f:
            self.logger.log_info(f.write("test2"))
        path2 = Path.home() / "test2.txt"

        return {"example_value_1": "test", "example_value_2": 5}, ExampleFileData(
            log_file_1=path1, log_file_2=path2
        )

    @action
    def return_analysis_result(self, sample_id: str = "SAMPLE_001") -> AnalysisResult:
        """Return a custom pydantic model with analysis results"""
        self.logger.log(f"returning analysis result for {sample_id}")
        return AnalysisResult(
            sample_id=sample_id,
            concentration=15.75,
            ph_level=7.2,
            temperature=22.5,
            quality_score=92,
            notes="Analysis completed successfully",
        )

    @action
    def return_experiment_metadata(
        self, experiment_id: str = "EXP_001"
    ) -> ExperimentMetadata:
        """Return complex experiment metadata as a custom pydantic model"""
        self.logger.log(f"returning experiment metadata for {experiment_id}")
        return ExperimentMetadata(
            experiment_id=experiment_id,
            start_time="2024-01-15T10:30:00Z",
            conditions={"temperature": 25.0, "humidity": 65.5, "pressure": 1013.25},
            parameters=["concentration", "ph", "conductivity", "turbidity"],
            status="completed",
            results_summary={"total_samples": 24, "passed": 22, "failed": 2},
        )

    @action
    def return_mixed_custom_and_files(
        self, sample_id: str = "SAMPLE_002"
    ) -> tuple[AnalysisResult, Path]:
        """Return a custom pydantic model and a file"""
        self.logger.log(f"returning mixed results for {sample_id}")

        # Create a sample file
        with (Path.home() / "analysis_report.txt").open("w") as f:
            f.write(f"Analysis report for {sample_id}\nTemperature: 23.1°C\nPH: 7.4")
        file_path = Path.home() / "analysis_report.txt"

        # Create the analysis result
        result = AnalysisResult(
            sample_id=sample_id,
            concentration=18.25,
            ph_level=7.4,
            temperature=23.1,
            quality_score=88,
            notes="Mixed return example with file and custom model",
        )

        return result, file_path

    def get_location(self) -> AdminCommandResponse:
        """Get location for the advanced example node"""
        return AdminCommandResponse(data=[0, 0, 0, 0])


if __name__ == "__main__":
    advanced_example_node = AdvancedExampleNode()
    advanced_example_node.start_node()
