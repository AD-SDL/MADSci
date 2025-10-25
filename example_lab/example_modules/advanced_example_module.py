"""A module for testing advanced features of MADSci."""

from pathlib import Path
from typing import Annotated, Optional, Union

from madsci.common.types.action_types import (
    ActionFiles,
)
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.location_types import LocationArgument
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


class SampleProcessingRequest(BaseModel):
    """Example complex input model for testing pydantic argument handling"""

    sample_ids: list[str] = Field(description="List of sample identifiers to process")
    processing_type: str = Field(description="Type of processing to perform")
    parameters: dict[str, Union[str, int, float]] = Field(
        description="Processing parameters"
    )
    priority: int = Field(description="Processing priority (1-10)", ge=1, le=10)
    notify_on_completion: bool = Field(
        default=False, description="Whether to send notifications"
    )


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

    # ===== SIMPLE ARGUMENT TEST CASES =====

    @action
    def test_simple_string(self, message: str) -> str:
        """Test action with a simple string argument"""
        self.logger.log(f"Received string: {message}")
        return f"Processed: {message}"

    @action
    def test_simple_int(self, number: int) -> int:
        """Test action with a simple integer argument"""
        self.logger.log(f"Received int: {number}")
        return number * 2

    @action
    def test_simple_float(self, value: float) -> float:
        """Test action with a simple float argument"""
        self.logger.log(f"Received float: {value}")
        return round(value * 3.14, 2)

    @action
    def test_simple_bool(self, flag: bool) -> bool:
        """Test action with a simple boolean argument"""
        self.logger.log(f"Received bool: {flag}")
        return not flag

    @action
    def test_multiple_simple_args(
        self, name: str, age: int, height: float, active: bool
    ) -> dict:
        """Test action with multiple simple arguments of different types"""
        self.logger.log(
            f"Received: name={name}, age={age}, height={height}, active={active}"
        )
        return {
            "name": name.upper(),
            "age_doubled": age * 2,
            "height_cm": height * 100,
            "status": "active" if active else "inactive",
        }

    # ===== OPTIONAL ARGUMENT TEST CASES =====

    @action
    def test_optional_string(self, message: str, prefix: Optional[str] = None) -> str:
        """Test action with optional string argument"""
        result = f"{prefix}: {message}" if prefix else message
        self.logger.log(f"Result: {result}")
        return result

    @action
    def test_optional_with_defaults(
        self,
        required_param: str,
        optional_int: Optional[int] = None,
        default_string: str = "default_value",
        default_float: float = 1.0,
        default_bool: bool = False,
    ) -> dict:
        """Test action with various optional parameters and defaults"""
        self.logger.log(f"Processing with required_param={required_param}")
        return {
            "required": required_param,
            "optional_int": optional_int
            if optional_int is not None
            else "not_provided",
            "default_string": default_string,
            "default_float": default_float,
            "default_bool": default_bool,
        }

    @action
    def test_annotated_args(
        self,
        annotated_int: Annotated[int, "An annotated integer parameter"] = 42,
        annotated_str: Annotated[str, "An annotated string parameter"] = "default",
        optional_annotated: Optional[
            Annotated[float, "Optional annotated float"]
        ] = None,
    ) -> dict:
        """Test action with annotated type parameters"""
        self.logger.log("Processing annotated arguments")
        return {
            "annotated_int": annotated_int,
            "annotated_str": annotated_str,
            "optional_annotated": optional_annotated,
        }

    # ===== COMPLEX DATA STRUCTURE TEST CASES =====

    @action
    def test_list_args(self, string_list: list[str], number_list: list[int]) -> dict:
        """Test action with list arguments"""
        self.logger.log(
            f"Received lists: {len(string_list)} strings, {len(number_list)} numbers"
        )
        return {
            "string_count": len(string_list),
            "strings_upper": [s.upper() for s in string_list],
            "number_sum": sum(number_list),
            "number_max": max(number_list) if number_list else 0,
        }

    @action
    def test_dict_args(self, config: dict[str, Union[str, int, float]]) -> dict:
        """Test action with dictionary argument"""
        self.logger.log(f"Received config with {len(config)} keys")
        processed_config = {}
        for key, value in config.items():
            if isinstance(value, str):
                processed_config[f"{key}_processed"] = value.upper()
            elif isinstance(value, (int, float)):
                processed_config[f"{key}_doubled"] = value * 2
        return processed_config

    @action
    def test_nested_structures(
        self, nested_data: dict[str, list[dict[str, Union[str, int]]]]
    ) -> dict:
        """Test action with complex nested data structures"""
        self.logger.log("Processing nested data structures")
        result = {"processed_keys": [], "total_items": 0}

        for key, items in nested_data.items():
            result["processed_keys"].append(key)
            result["total_items"] += len(items)

        return result

    # ===== PYDANTIC MODEL ARGUMENT TEST CASES =====

    @action
    def test_pydantic_input(self, request: SampleProcessingRequest) -> dict:
        """Test action with pydantic model as input"""
        self.logger.log(f"Processing request for {len(request.sample_ids)} samples")
        return {
            "processing_type": request.processing_type,
            "sample_count": len(request.sample_ids),
            "priority": request.priority,
            "estimated_time": len(request.sample_ids) * request.priority * 5,
            "notifications_enabled": request.notify_on_completion,
        }

    @action
    def test_optional_pydantic_input(
        self, sample_id: str, request: Optional[SampleProcessingRequest] = None
    ) -> AnalysisResult:
        """Test action with optional pydantic model input"""
        self.logger.log(f"Processing {sample_id} with optional request")

        priority_modifier = request.priority / 10 if request else 0.5

        return AnalysisResult(
            sample_id=sample_id,
            concentration=15.0 * priority_modifier,
            ph_level=7.0,
            temperature=22.0,
            quality_score=int(90 * priority_modifier),
            notes=f"Processed with priority modifier: {priority_modifier}",
        )

    # ===== FILE ARGUMENT TEST CASES =====

    @action
    def test_file_input(self, input_file: Path) -> str:
        """Test action with file path input"""
        self.logger.log(f"Processing file: {input_file}")

        if input_file.exists():
            with input_file.open("r") as f:
                content = f.read()
            return f"File content length: {len(content)} characters"
        return f"File not found: {input_file}"

    @action
    def test_optional_file_input(
        self, data: str, config_file: Optional[Path] = None
    ) -> Path:
        """Test action with optional file input"""
        self.logger.log(
            f"Processing data with optional config: {config_file is not None}"
        )

        output_path = Path.home() / "test_output.txt"
        with output_path.open("w") as f:
            f.write(f"Data: {data}\n")
            if config_file and config_file.exists():
                f.write(f"Config file used: {config_file}\n")
            else:
                f.write("No config file provided\n")

        return output_path

    @action
    def test_multiple_file_inputs(
        self, primary_file: Path, secondary_files: list[Path]
    ) -> ExampleFileData:
        """Test action with multiple file inputs"""
        self.logger.log(f"Processing {len(secondary_files)} secondary files")

        # Create output files
        log1_path = Path.home() / "processing_log.txt"
        log2_path = Path.home() / "summary_log.txt"

        with log1_path.open("w") as f:
            f.write(f"Primary file: {primary_file}\n")
            for i, sec_file in enumerate(secondary_files):
                f.write(f"Secondary file {i + 1}: {sec_file}\n")

        with log2_path.open("w") as f:
            f.write(f"Total files processed: {len(secondary_files) + 1}\n")

        return ExampleFileData(log_file_1=log1_path, log_file_2=log2_path)

    # ===== LOCATION ARGUMENT TEST CASES =====

    @action
    def test_location_input(self, target_location: LocationArgument) -> dict:
        """Test action with location argument"""
        self.logger.log(f"Processing location: {target_location.location}")
        return {
            "location_representation": str(target_location.representation),
            "location_name": target_location.location_name,
            "resource_id": target_location.resource_id,
            "has_reservation": target_location.reservation is not None,
        }

    @action
    def test_multiple_locations(
        self,
        source: LocationArgument,
        destination: LocationArgument,
        waypoints: Optional[list[LocationArgument]] = None,
    ) -> None:
        """Test action with multiple location arguments"""
        self.logger.log(f"Moving from {source.location} to {destination.location}")

        if waypoints:
            self.logger.log(f"Via {len(waypoints)} waypoints")
            for i, waypoint in enumerate(waypoints):
                self.logger.log(f"Waypoint {i + 1}: {waypoint.location}")

    @action
    def test_location_with_resource_interaction(
        self, pick_location: LocationArgument, place_location: LocationArgument
    ) -> dict:
        """Test action that simulates resource movement between locations"""
        self.logger.log(
            f"Simulating resource transfer from {pick_location.location} to {place_location.location}"
        )

        # Simulate picking up resource from source location
        if pick_location.resource_id:
            self.logger.log(f"Picking up resource {pick_location.resource_id}")

        # Simulate placing resource at destination
        return {
            "source_location": str(pick_location.representation),
            "destination_location": str(place_location.representation),
            "resource_moved": pick_location.resource_id,
            "transfer_completed": True,
        }

    # ===== MIXED COMPLEX ARGUMENT TEST CASES =====

    @action
    def test_everything_mixed(
        self,
        sample_request: SampleProcessingRequest,
        target_location: LocationArgument,
        data_files: list[Path],
        config: dict[str, Union[str, int, float]],
        optional_notes: Optional[str] = None,
        priority_override: bool = False,
    ) -> tuple[AnalysisResult, ExampleFileData]:
        """Test action with a mix of all argument types"""
        self.logger.log("Processing complex mixed arguments")

        # Process the sample request
        final_priority = 10 if priority_override else sample_request.priority

        # Create analysis result
        analysis = AnalysisResult(
            sample_id=sample_request.sample_ids[0]
            if sample_request.sample_ids
            else "UNKNOWN",
            concentration=config.get("concentration", 20.0),
            ph_level=config.get("ph", 7.0),
            temperature=config.get("temperature", 25.0),
            quality_score=final_priority * 9,
            notes=optional_notes
            or f"Processed at {target_location.location_name or 'unknown location'}",
        )

        # Create file outputs
        log1_path = Path.home() / "complex_analysis_log.txt"
        log2_path = Path.home() / "complex_summary.txt"

        with log1_path.open("w") as f:
            f.write(f"Sample IDs: {', '.join(sample_request.sample_ids)}\n")
            f.write(f"Processing type: {sample_request.processing_type}\n")
            f.write(f"Location: {target_location.location}\n")
            f.write(f"Data files: {len(data_files)}\n")

        with log2_path.open("w") as f:
            f.write(f"Final priority: {final_priority}\n")
            f.write(f"Config keys: {list(config.keys())}\n")
            f.write(f"Notes: {optional_notes or 'None'}\n")

        files = ExampleFileData(log_file_1=log1_path, log_file_2=log2_path)

        return analysis, files

    @action
    def arg_type_test(self, x: bool, y: int, z: float, w: str) -> None:
        """Used to test that argument types are correctly passed to the node module."""
        if type(x) is bool and type(y) is int and type(z) is float and type(w) is str:
            self.logger.log(f"Value of x is {x} and type is {type(x)}")
            return
        raise ValueError("Argument types are incorrect")

    def get_location(self) -> AdminCommandResponse:
        """Get location for the advanced example node"""
        return AdminCommandResponse(data=[0, 0, 0, 0])


if __name__ == "__main__":
    advanced_example_node = AdvancedExampleNode()
    advanced_example_node.start_node()
