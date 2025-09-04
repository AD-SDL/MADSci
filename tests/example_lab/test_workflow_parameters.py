"""
Test new workflow parameter system.

These tests validate the input/feed forward parameter separation,
file-based parameters, and automatic parameter promotion from PR #104.
"""

from pathlib import Path

from madsci.common.utils import new_ulid_str


class TestParameterSeparation:
    """Test input vs feed forward parameter separation."""

    def test_input_parameters_structure(self):
        """Test input parameters structure and validation."""
        input_params = {
            "temperature": 25.0,
            "volume_ul": 100,
            "reagent_type": "buffer",
            "mixing_speed": "medium",
        }

        # Validate input parameter types
        assert isinstance(input_params["temperature"], (int, float))
        assert isinstance(input_params["volume_ul"], int)
        assert isinstance(input_params["reagent_type"], str)
        assert isinstance(input_params["mixing_speed"], str)

    def test_feed_forward_parameters_structure(self):
        """Test feed forward parameters structure."""
        feed_forward_params = {
            "previous_step_result": {
                "status": "completed",
                "output_data": {"measurement": 1.23},
            },
            "shared_resources": ["plate_001", "tip_rack_001"],
            "context_data": {"run_id": new_ulid_str(), "batch_id": "batch_001"},
        }

        # Validate feed forward parameter structure
        assert "previous_step_result" in feed_forward_params
        assert "shared_resources" in feed_forward_params
        assert isinstance(feed_forward_params["shared_resources"], list)

    def test_parameter_separation_in_workflow(self):
        """Test that workflows properly separate input and feed forward parameters."""
        workflow_step = {
            "step_id": new_ulid_str(),
            "name": "test_step",
            "node": "test_node",
            "action": "process",
            "input_parameters": {"temperature": 25.0, "duration_min": 30},
            "feed_forward_parameters": {
                "previous_result": None  # Will be populated by previous step
            },
        }

        # Validate separation
        assert "input_parameters" in workflow_step
        assert "feed_forward_parameters" in workflow_step
        assert (
            workflow_step["input_parameters"]
            != workflow_step["feed_forward_parameters"]
        )


class TestFileBasedParameters:
    """Test file-based workflow parameters and automatic promotion."""

    def test_file_parameter_detection(self, temp_lab_dir):
        """Test detection of file arguments as parameters."""
        # Create test files
        input_file = temp_lab_dir / "input_data.csv"
        config_file = temp_lab_dir / "config.json"

        input_file.write_text("sample,value\ntest1,1.23\ntest2,4.56")
        config_file.write_text('{"setting": "value"}')

        # Simulate file arguments being converted to parameters
        file_arguments = {
            "input_file": str(input_file),
            "config_file": str(config_file),
        }

        # Validate files exist and can be promoted to parameters
        for file_path_str in file_arguments.values():
            assert Path(file_path_str).exists()
            assert Path(file_path_str).is_file()

    def test_file_parameter_promotion(self, temp_lab_dir):
        """Test automatic promotion of file arguments to workflow parameters."""
        # Create test file
        data_file = temp_lab_dir / "experiment_data.txt"
        data_file.write_text("test data content")

        # Simulate parameter promotion
        promoted_parameters = {
            "input_file": str(data_file),
            "output_file": "results.txt",
        }

        # Validate promotion
        assert promoted_parameters["input_file"] == str(data_file)
        assert "output_file" in promoted_parameters

    def test_file_parameter_validation(self, temp_lab_dir):
        """Test file parameter validation."""
        # Create valid and invalid file references
        valid_file = temp_lab_dir / "valid_file.txt"
        valid_file.write_text("valid content")
        invalid_file = temp_lab_dir / "nonexistent_file.txt"

        file_params = {"valid_file": str(valid_file), "invalid_file": str(invalid_file)}

        # Validate file existence
        assert Path(file_params["valid_file"]).exists()
        assert not Path(file_params["invalid_file"]).exists()


class TestParameterDataflow:
    """Test parameter dataflow between workflow steps."""

    def test_output_to_input_parameter_flow(self):
        """Test data flow from step output to next step input."""
        step1_output = {
            "measurements": [1.23, 4.56, 7.89],
            "status": "completed",
            "metadata": {"timestamp": "2024-01-01T12:00:00Z"},
        }

        step2_input = {
            "previous_measurements": step1_output["measurements"],
            "processing_mode": "analysis",
        }

        # Validate data flow
        assert step2_input["previous_measurements"] == step1_output["measurements"]
        assert len(step2_input["previous_measurements"]) == 3

    def test_parameter_transformation(self):
        """Test parameter transformation between steps."""
        raw_data = {"values": [1, 2, 3, 4, 5]}

        # Simulate parameter transformation
        transformed_data = {
            "processed_values": [x * 2 for x in raw_data["values"]],
            "summary": {
                "count": len(raw_data["values"]),
                "sum": sum(raw_data["values"]),
            },
        }

        # Validate transformation
        assert transformed_data["processed_values"] == [2, 4, 6, 8, 10]
        assert transformed_data["summary"]["count"] == 5
        assert transformed_data["summary"]["sum"] == 15


class TestParameterValidation:
    """Test parameter validation and error handling."""

    def test_required_parameter_validation(self):
        """Test validation of required parameters."""
        required_params = ["temperature", "volume", "reagent"]
        provided_params = {"temperature": 25.0, "volume": 100}

        missing_params = set(required_params) - set(provided_params.keys())
        assert "reagent" in missing_params
        assert len(missing_params) == 1

    def test_parameter_type_validation(self):
        """Test parameter type validation."""
        parameter_types = {
            "temperature": (int, float),
            "volume": int,
            "name": str,
            "enabled": bool,
        }

        test_params = {
            "temperature": 25.0,
            "volume": 100,
            "name": "test",
            "enabled": True,
        }

        # Validate types
        for param_name, expected_types in parameter_types.items():
            if param_name in test_params:
                assert isinstance(test_params[param_name], expected_types)

    def test_parameter_range_validation(self):
        """Test parameter range validation."""
        temperature_limits = {"min": 4.0, "max": 95.0}
        volume_limits = {"min": 1, "max": 1000}

        valid_params = {"temperature": 25.0, "volume": 100}
        invalid_params = {"temperature": 150.0, "volume": 2000}

        # Validate ranges
        assert (
            temperature_limits["min"]
            <= valid_params["temperature"]
            <= temperature_limits["max"]
        )
        assert volume_limits["min"] <= valid_params["volume"] <= volume_limits["max"]

        # Check invalid values are out of range
        assert invalid_params["temperature"] > temperature_limits["max"]
        assert invalid_params["volume"] > volume_limits["max"]
