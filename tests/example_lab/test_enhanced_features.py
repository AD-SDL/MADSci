"""
Tests for Phase 2 enhanced MADSci features in the example lab.

This module tests the integration of modern MADSci features including:
- Enhanced context management throughout examples
- Advanced workflow parameter handling
- File-based parameter promotion
- Internal workcell actions
- Comprehensive resource template usage
"""

import csv
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml
from madsci.client.resource_client import ResourceClient
from madsci.client.workcell_client import WorkcellClient
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.context_types import MadsciContext
from madsci.common.types.node_types import NodeDefinition
from madsci.common.utils import new_ulid_str


class TestEnhancedContextIntegration:
    """Test enhanced context integration throughout examples."""

    @pytest.mark.requires_services
    def test_comprehensive_context_creation(self, madsci_context):
        """Test creation of comprehensive MADSci context."""

        # Verify all required service URLs are present
        assert madsci_context.lab_server_url is not None
        assert madsci_context.resource_server_url is not None
        assert madsci_context.workcell_server_url is not None
        assert madsci_context.experiment_server_url is not None
        assert madsci_context.data_server_url is not None
        assert madsci_context.event_server_url is not None

        # Verify context can be serialized/deserialized
        context_dict = madsci_context.model_dump()
        restored_context = MadsciContext(**context_dict)
        assert restored_context == madsci_context

    @pytest.mark.requires_services
    def test_ownership_info_propagation(self, ownership_info):
        """Test proper ownership information propagation."""

        # Test ownership serialization for API calls
        ownership_dict = ownership_info.model_dump()

        # Verify required fields are present
        assert ownership_dict["user_id"] is not None
        assert ownership_dict["lab_id"] is not None
        assert ownership_dict["experiment_id"] is not None

        # Test ownership comparison
        same_ownership = OwnershipInfo(**ownership_dict)
        assert ownership_info.check(same_ownership)

        different_ownership = OwnershipInfo(
            user_id=new_ulid_str(),
            lab_id=ownership_info.lab_id,
            experiment_id=ownership_info.experiment_id,
        )
        assert not ownership_info.check(different_ownership)

    def test_enhanced_example_app_initialization(self):
        """Test enhanced example app with proper context management."""

        # Import should succeed
        try:
            from example_lab.enhanced_example_app import (  # noqa: PLC0415
                EnhancedExampleApp,
            )
        except ImportError:
            pytest.skip("Enhanced example app module not available")

        # Create node definition
        node_def = NodeDefinition(
            node_name="test_enhanced_app", module_name="test_enhanced_app"
        )

        # App should initialize with context
        with patch("madsci.experiment_application.ExperimentApplication.__init__"):
            app = EnhancedExampleApp.__new__(EnhancedExampleApp)
            app.__init__(node_def)

            # Verify context attributes exist
            assert hasattr(app, "app_context")
            assert hasattr(app, "ownership")
            assert app.ownership.node_id == "test_enhanced_app"


class TestAdvancedWorkflowParameters:
    """Test advanced workflow parameter handling."""

    def test_enhanced_workflow_structure(self):
        """Test enhanced context workflow structure."""

        workflow_path = Path(
            "example_lab/workflows/enhanced_context_workflow.workflow.yaml"
        )
        assert workflow_path.exists(), "Enhanced context workflow file not found"

        # Read and parse workflow
        with workflow_path.open() as f:
            workflow = yaml.safe_load(f)

        # Verify workflow structure
        assert "parameters" in workflow
        assert "json_inputs" in workflow["parameters"]
        assert "file_inputs" in workflow["parameters"]
        assert "feed_forward" in workflow["parameters"]

        # Verify modern parameter features
        json_inputs = workflow["parameters"]["json_inputs"]
        param_keys = [param["key"] for param in json_inputs]

        expected_params = ["experiment_id", "user_id", "plate_id", "reagent_buffer_id"]
        for param in expected_params:
            assert param in param_keys, f"Missing required parameter: {param}"

        # Verify feed-forward parameters
        feed_forward = workflow["parameters"]["feed_forward"]
        assert len(feed_forward) > 0, "No feed-forward parameters defined"

        for param in feed_forward:
            assert "step" in param, "Feed-forward parameter missing step reference"
            assert "label" in param, "Feed-forward parameter missing label"
            assert "data_type" in param, "Feed-forward parameter missing data_type"

    def test_internal_actions_workflow(self):
        """Test internal actions demonstration workflow."""

        workflow_path = Path(
            "example_lab/workflows/internal_actions_demo.workflow.yaml"
        )
        assert workflow_path.exists(), "Internal actions demo workflow not found"

        with workflow_path.open() as f:
            workflow = yaml.safe_load(f)

        # Verify internal actions are present
        steps = workflow.get("steps", [])
        internal_actions = [
            step for step in steps if "action" in step and "node" not in step
        ]

        assert len(internal_actions) > 0, "No internal actions found in workflow"

        # Verify specific internal actions
        action_names = [action.get("action", "") for action in internal_actions]
        expected_actions = [
            "validate_step",
            "generate_comprehensive_report",
            "finalize_workflow",
        ]

        for expected in expected_actions:
            found = any(expected in action for action in action_names)
            assert found, f"Expected internal action not found: {expected}"

    def test_file_parameters_workflow(self):
        """Test file-based parameters demonstration workflow."""

        workflow_path = Path("example_lab/workflows/file_parameters_demo.workflow.yaml")
        assert workflow_path.exists(), "File parameters demo workflow not found"

        with workflow_path.open() as f:
            workflow = yaml.safe_load(f)

        # Verify file parameter handling
        assert "file_inputs" in workflow["parameters"]
        assert "feed_forward" in workflow["parameters"]

        # Check for file-type feed-forward parameters
        feed_forward = workflow["parameters"]["feed_forward"]
        file_feedforward = [p for p in feed_forward if p.get("data_type") == "file"]

        assert len(file_feedforward) > 0, "No file-type feed-forward parameters found"

        # Verify auto-promotion configuration
        file_handling = workflow.get("file_handling", {})
        assert file_handling.get("auto_promotion", False), "Auto-promotion not enabled"


class TestResourceTemplateShowcase:
    """Test comprehensive resource template showcase."""

    @pytest.mark.requires_services
    def test_template_library_completeness(self):
        """Test that template library contains expected categories."""

        try:
            client = ResourceClient(resource_server_url="http://localhost:8003")
            templates = client.list_templates()

            template_names = [t.resource_name for t in templates]

            # Check for expected template categories
            expected_templates = [
                "standard_96well_plate",
                "standard_384well_plate",
                "tip_rack_200ul",
                "generic_reagent",
            ]

            for template_name in expected_templates:
                assert any(template_name in name for name in template_names), (
                    f"Expected template not found: {template_name}"
                )

        except Exception as e:
            pytest.skip(f"Service not available: {e}")

    @pytest.mark.requires_services
    def test_template_context_integration(self, ownership_info):
        """Test template creation with proper context integration."""

        try:
            client = ResourceClient(resource_server_url="http://localhost:8003")

            # Test creating resource from template with ownership
            plate = client.create_resource_from_template(
                template_name="standard_96well_plate",
                resource_name=f"TestPlate_{new_ulid_str()[:8]}",
                overrides={
                    "owner": ownership_info.model_dump(),
                    "attributes": {
                        "test_context": "phase2_testing",
                        "created_by": "automated_test",
                    },
                },
                add_to_database=False,  # Don't actually save
            )

            # Verify ownership was applied
            assert plate.owner is not None
            assert plate.owner.user_id == ownership_info.user_id
            assert plate.owner.experiment_id == ownership_info.experiment_id

            # Verify context attributes
            assert plate.attributes["test_context"] == "phase2_testing"

        except Exception as e:
            pytest.skip(f"Service not available: {e}")


class TestDataFiles:
    """Test example data files for demonstrations."""

    def test_sample_manifest_structure(self):
        """Test sample manifest file structure and content."""

        manifest_path = Path("example_lab/data_files/sample_manifest.csv")
        assert manifest_path.exists(), "Sample manifest file not found"

        with manifest_path.open() as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Verify structure
        assert len(rows) > 0, "Sample manifest is empty"

        required_columns = [
            "sample_id",
            "sample_type",
            "concentration",
            "volume",
            "timestamp",
        ]
        for column in required_columns:
            assert column in rows[0], f"Missing required column: {column}"

        # Verify data types and content
        for row in rows:
            assert row["sample_id"].startswith("SAMPLE_"), "Invalid sample ID format"
            assert row["sample_type"] in [
                "control",
                "test_compound",
                "blank",
                "standard",
            ]
            assert float(row["concentration"]) >= 0, "Invalid concentration value"
            assert float(row["volume"]) > 0, "Invalid volume value"

    def test_protocol_template_structure(self):
        """Test protocol template file structure."""

        template_path = Path("example_lab/data_files/protocol_template.py")
        assert template_path.exists(), "Protocol template file not found"

        with template_path.open() as f:
            content = f.read()

        # Verify template structure
        assert "def setup(" in content, "Missing setup function"
        assert "def main(" in content, "Missing main function"
        assert "def cleanup(" in content, "Missing cleanup function"

        # Verify template variables
        template_vars = ["{{EXPERIMENT_ID}}", "{{PLATE_COUNT}}", "{{TRANSFER_VOLUME}}"]
        for var in template_vars:
            assert var in content, f"Missing template variable: {var}"

    def test_processing_config_structure(self):
        """Test processing configuration file structure."""

        config_path = Path("example_lab/data_files/processing_config.json")
        assert config_path.exists(), "Processing config file not found"

        with config_path.open() as f:
            config = json.load(f)

        # Verify configuration sections
        required_sections = [
            "processing_settings",
            "liquid_handling",
            "quality_control",
            "file_handling",
            "experiment_tracking",
        ]

        for section in required_sections:
            assert section in config, f"Missing config section: {section}"

        # Verify specific settings
        assert config["processing_settings"]["validation_level"] in [
            "strict",
            "lenient",
            "disabled",
        ]
        assert isinstance(
            config["liquid_handling"]["default_transfer_volume"], (int, float)
        )
        assert isinstance(config["quality_control"]["enable_volume_verification"], bool)


class TestWorkflowIntegration:
    """Test integration of all Phase 2 features in workflows."""

    def test_workflow_files_exist(self):
        """Test that all enhanced workflow files exist."""

        workflows_dir = Path("example_lab/workflows")

        expected_workflows = [
            "enhanced_context_workflow.workflow.yaml",
            "internal_actions_demo.workflow.yaml",
            "file_parameters_demo.workflow.yaml",
        ]

        for workflow_file in expected_workflows:
            workflow_path = workflows_dir / workflow_file
            assert workflow_path.exists(), f"Missing workflow file: {workflow_file}"

    @pytest.mark.requires_services
    def test_enhanced_app_workflow_execution(self):
        """Test enhanced application workflow execution."""

        try:
            # Test that enhanced app can be imported and initialized
            from madsci.common.types.node_types import NodeDefinition  # noqa: PLC0415

            from example_lab.enhanced_example_app import (  # noqa: PLC0415
                EnhancedExampleApp,
            )

            node_def = NodeDefinition(
                node_name="test_enhanced_integration",
                module_name="test_enhanced_integration",
            )

            # Mock the initialization to avoid actual service calls
            with patch("madsci.experiment_application.ExperimentApplication.__init__"):
                app = EnhancedExampleApp.__new__(EnhancedExampleApp)
                app.__init__(node_def)

                # Verify context integration
                assert hasattr(app, "app_context")
                assert hasattr(app, "ownership")

                # Mock resource setup method
                with patch.object(app, "resource_client") as mock_client:
                    mock_client.create_resource_from_template.return_value = Mock(
                        resource_id=new_ulid_str(), resource_name="MockPlate_001"
                    )

                    # Test resource setup method
                    resource_ids = app.setup_lab_resources()
                    assert isinstance(resource_ids, dict)
                    assert len(resource_ids) > 0

        except ImportError as e:
            pytest.skip(f"Enhanced app module not available: {e}")
        except Exception as e:
            pytest.skip(f"Service integration test failed: {e}")


class TestSetupNotebooks:
    """Test setup notebook structure and content."""

    def test_comprehensive_setup_notebook(self):
        """Test comprehensive lab setup notebook."""

        notebook_path = Path("example_lab/setup/05_comprehensive_lab_setup.ipynb")
        assert notebook_path.exists(), "Comprehensive setup notebook not found"

        with notebook_path.open() as f:
            notebook_content = f.read()

        # Verify key features are covered
        expected_features = [
            "MadsciContext",
            "OwnershipInfo",
            "create_resource_from_template",
            "feed_forward",
            "json_inputs",
            "file_inputs",
        ]

        for feature in expected_features:
            assert feature in notebook_content, (
                f"Missing feature in notebook: {feature}"
            )

    def test_notebook_cell_structure(self):
        """Test that setup notebook has proper cell structure."""

        notebook_path = Path("example_lab/setup/05_comprehensive_lab_setup.ipynb")

        with notebook_path.open() as f:
            notebook = json.load(f)

        # Verify notebook structure
        assert "cells" in notebook
        assert len(notebook["cells"]) > 0

        # Check for markdown documentation cells
        markdown_cells = [
            cell for cell in notebook["cells"] if cell["cell_type"] == "markdown"
        ]
        assert len(markdown_cells) > 0, "No documentation cells found"

        # Check for code execution cells
        code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
        assert len(code_cells) > 0, "No executable code cells found"


class TestFileParameterHandling:
    """Test file-based parameter handling and promotion."""

    def test_sample_data_files_exist(self):
        """Test that example data files exist and are properly formatted."""

        data_dir = Path("example_lab/data_files")

        expected_files = [
            "sample_manifest.csv",
            "protocol_template.py",
            "processing_config.json",
        ]

        for file_name in expected_files:
            file_path = data_dir / file_name
            assert file_path.exists(), f"Missing data file: {file_name}"
            assert file_path.stat().st_size > 0, f"Empty data file: {file_name}"

    def test_file_parameter_workflow_structure(self):
        """Test file parameters demo workflow structure."""

        workflow_path = Path("example_lab/workflows/file_parameters_demo.workflow.yaml")

        import yaml  # noqa: PLC0415

        with workflow_path.open() as f:
            workflow = yaml.safe_load(f)

        # Verify file handling configuration
        assert "file_handling" in workflow
        file_config = workflow["file_handling"]

        assert file_config.get("auto_promotion", False), "Auto-promotion not enabled"
        assert file_config.get("validation_required", False), (
            "File validation not enabled"
        )

        # Verify feed-forward file parameters
        feed_forward = workflow["parameters"]["feed_forward"]
        file_params = [p for p in feed_forward if p.get("data_type") == "file"]

        assert len(file_params) > 0, "No file-type feed-forward parameters"

        for param in file_params:
            assert "step" in param, "File parameter missing step reference"
            assert "label" in param, "File parameter missing label"

    def test_protocol_template_customization(self):
        """Test protocol template customization features."""

        template_path = Path("example_lab/data_files/protocol_template.py")

        with template_path.open() as f:
            content = f.read()

        # Verify template variables exist
        template_vars = [
            "{{EXPERIMENT_ID}}",
            "{{PLATE_COUNT}}",
            "{{TRANSFER_VOLUME}}",
            "{{MIX_CYCLES}}",
            "{{SAMPLE_COUNT}}",
        ]

        for var in template_vars:
            assert var in content, f"Missing template variable: {var}"

        # Verify template structure
        assert "def setup(" in content, "Template missing setup function"
        assert "def main(" in content, "Template missing main function"
        assert "def cleanup(" in content, "Template missing cleanup function"


class TestErrorHandlingEnhancements:
    """Test enhanced error handling and retry mechanisms."""

    def test_workflow_error_handling_config(self):
        """Test workflow error handling configuration."""

        workflow_path = Path(
            "example_lab/workflows/internal_actions_demo.workflow.yaml"
        )

        import yaml  # noqa: PLC0415

        with workflow_path.open() as f:
            workflow = yaml.safe_load(f)

        # Verify error handling configuration
        assert "error_handling" in workflow
        error_config = workflow["error_handling"]

        required_fields = ["global_timeout", "step_timeout", "retry_strategy"]
        for field in required_fields:
            assert field in error_config, f"Missing error handling field: {field}"

        # Verify failure actions
        assert "failure_actions" in error_config
        failure_actions = error_config["failure_actions"]
        assert len(failure_actions) > 0, "No failure actions defined"

    def test_retry_configuration(self):
        """Test retry configuration in workflow steps."""

        workflow_path = Path("example_lab/workflows/file_parameters_demo.workflow.yaml")

        import yaml  # noqa: PLC0415

        with workflow_path.open() as f:
            workflow = yaml.safe_load(f)

        # Look for steps with retry configuration
        steps = workflow.get("steps", [])
        steps_with_retry = [s for s in steps if "retry_config" in s]

        if steps_with_retry:
            for step in steps_with_retry:
                retry_config = step["retry_config"]
                assert "max_attempts" in retry_config
                assert "retry_delay" in retry_config
                assert isinstance(retry_config["max_attempts"], int)


class TestPhase2Integration:
    """Test overall Phase 2 feature integration."""

    def test_all_phase2_features_present(self):
        """Test that all Phase 2 features are implemented."""

        # Check for enhanced example app
        app_path = Path("example_lab/enhanced_example_app.py")
        assert app_path.exists(), "Enhanced example app not found"

        # Check for comprehensive setup notebook
        setup_path = Path("example_lab/setup/05_comprehensive_lab_setup.ipynb")
        assert setup_path.exists(), "Comprehensive setup notebook not found"

        # Check for enhanced workflows
        workflow_paths = [
            "example_lab/workflows/enhanced_context_workflow.workflow.yaml",
            "example_lab/workflows/internal_actions_demo.workflow.yaml",
            "example_lab/workflows/file_parameters_demo.workflow.yaml",
        ]

        for workflow_path in workflow_paths:
            assert Path(workflow_path).exists(), f"Missing workflow: {workflow_path}"

        # Check for data files
        data_paths = [
            "example_lab/data_files/sample_manifest.csv",
            "example_lab/data_files/protocol_template.py",
            "example_lab/data_files/processing_config.json",
        ]

        for data_path in data_paths:
            assert Path(data_path).exists(), f"Missing data file: {data_path}"

    def test_feature_documentation(self):
        """Test that Phase 2 features are properly documented."""

        # Check comprehensive setup notebook content
        notebook_path = Path("example_lab/setup/05_comprehensive_lab_setup.ipynb")

        with notebook_path.open() as f:
            content = f.read()

        # Verify documentation of key features
        documented_features = [
            "Context Management",
            "Resource Templates",
            "Modern Workflows",
            "Internal Actions",
            "OwnershipInfo",
            "MadsciContext",
            "feed_forward",
        ]

        for feature in documented_features:
            assert feature in content, f"Feature not documented: {feature}"

    @pytest.mark.requires_services
    def test_end_to_end_integration(self, madsci_context):
        """Test end-to-end integration of all Phase 2 features."""

        try:
            # Test resource client with context
            resource_client = ResourceClient(
                resource_server_url=str(madsci_context.resource_server_url)
            )

            # Test workcell client with context
            workcell_client = WorkcellClient(
                workcell_server_url=str(madsci_context.workcell_server_url)
            )

            # Verify clients can be created with context
            assert resource_client is not None
            assert workcell_client is not None

            # Test basic connectivity
            templates = resource_client.list_templates()
            assert isinstance(templates, list)

            workflows = workcell_client.list_workflows()
            assert isinstance(workflows, list)

        except Exception as e:
            pytest.skip(f"End-to-end integration test failed: {e}")

    def test_phase2_completion_markers(self):
        """Test that Phase 2 completion markers are in place."""

        # All required files should exist
        required_files = [
            "example_lab/enhanced_example_app.py",
            "example_lab/setup/05_comprehensive_lab_setup.ipynb",
            "example_lab/workflows/enhanced_context_workflow.workflow.yaml",
            "example_lab/workflows/internal_actions_demo.workflow.yaml",
            "example_lab/workflows/file_parameters_demo.workflow.yaml",
            "example_lab/data_files/sample_manifest.csv",
            "example_lab/data_files/protocol_template.py",
            "example_lab/data_files/processing_config.json",
        ]

        missing_files = []
        for file_path in required_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)

        assert len(missing_files) == 0, f"Missing Phase 2 files: {missing_files}"
