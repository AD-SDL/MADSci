"""Enhanced Example Application with Context Management and Resource Templates"""

import time
from typing import Any

from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.context_types import MadsciContext
from madsci.common.types.experiment_types import ExperimentDesign
from madsci.common.types.node_types import NodeDefinition
from madsci.common.utils import new_ulid_str
from madsci.experiment_application import (
    ExperimentApplication,
    ExperimentApplicationConfig,
)
from pydantic import AnyUrl


class EnhancedExampleApp(ExperimentApplication):
    """Enhanced Example Application demonstrating modern MADSci features"""

    def __init__(self, node_definition: NodeDefinition, **kwargs: Any) -> None:
        """Initialize with proper context management."""

        # Create comprehensive context for this application
        self.app_context = MadsciContext(
            lab_server_url="http://localhost:8000",
            event_server_url="http://localhost:8001",
            experiment_server_url="http://localhost:8002",
            resource_server_url="http://localhost:8003",
            data_server_url="http://localhost:8004",
            workcell_server_url="http://localhost:8005",
        )

        # Create ownership info for tracking
        self.ownership = OwnershipInfo(
            user_id=new_ulid_str(),
            experiment_id=new_ulid_str(),
            project_id=new_ulid_str(),
            lab_id="example_lab_001",
            node_id=node_definition.node_name,
        )

        # Enhanced experiment design with context
        experiment_design = ExperimentDesign(
            experiment_name="Enhanced_Context_Demo",
            experiment_description="MADSci Context Management and Templates Demo",
            owner=self.ownership,
        )

        # Configure with context-aware settings
        config = ExperimentApplicationConfig(
            node_url=AnyUrl("http://localhost:6000"),
            server_mode=False,
        )

        super().__init__(
            node_definition=node_definition,
            experiment_design=experiment_design,
            config=config,
            **kwargs,
        )

    def setup_lab_resources(self) -> dict[str, str]:
        """Set up resources using templates with proper ownership context."""

        self.logger.info("Setting up lab resources with context management")

        resource_ids = {}

        try:
            # Create plates from templates
            for i in range(1, 4):
                plate = self.resource_client.create_resource_from_template(
                    template_name="standard_96well_plate",
                    resource_name=f"ContextDemo_Plate_{i:03d}",
                    overrides={
                        "owner": self.ownership.model_dump(),
                        "attributes": {
                            "plate_purpose": "context_demonstration",
                            "batch_number": f"CD20241201_{i:03d}",
                        },
                    },
                    add_to_database=True,
                )
                resource_ids[f"plate_{i}"] = plate.resource_id

                self.logger.info(
                    f"Created plate {plate.resource_name}",
                    extra={
                        "resource_id": plate.resource_id,
                        "ownership": self.ownership.model_dump(),
                    },
                )

            # Create reagents with context tracking
            reagent_configs = [
                {"name": "PBS_Buffer_Context", "type": "buffer", "volume": 50.0},
                {"name": "DMSO_Context", "type": "solvent", "volume": 25.0},
            ]

            for config in reagent_configs:
                reagent = self.resource_client.create_resource_from_template(
                    template_name="generic_reagent",
                    resource_name=config["name"],
                    overrides={
                        "owner": self.ownership.model_dump(),
                        "attributes": {
                            "reagent_type": config["type"],
                            "volume": config["volume"],
                            "remaining_volume": config["volume"],
                            "lot_number": f"CTX_{new_ulid_str()[:8]}",
                            "opened": False,
                        },
                    },
                    add_to_database=True,
                )
                resource_ids[f"reagent_{config['type']}"] = reagent.resource_id

                self.logger.info(
                    f"Created reagent {reagent.resource_name}",
                    extra={
                        "resource_id": reagent.resource_id,
                        "ownership": self.ownership.model_dump(),
                    },
                )

            return resource_ids

        except Exception as e:
            self.logger.error(f"Failed to setup resources: {e}")
            raise

    def run_context_aware_workflow(self, resource_ids: dict[str, str]) -> str:
        """Run workflow with proper context propagation."""

        self.logger.info("Starting context-aware workflow execution")

        try:
            # Submit workflow with enhanced parameter handling
            workflow_run = self.workcell_client.submit_workflow(
                "./workflows/enhanced_context_workflow.workflow.yaml",
                json_inputs={
                    "experiment_id": self.ownership.experiment_id,
                    "user_id": self.ownership.user_id,
                    "plate_id": resource_ids.get("plate_1", ""),
                    "reagent_buffer_id": resource_ids.get("reagent_buffer", ""),
                    "context_demo": "true",
                },
                file_inputs={"protocol_file": "./protocols/context_demo_protocol.py"},
                context={
                    "ownership": self.ownership.model_dump(),
                    "lab_context": self.app_context.model_dump(),
                },
            )

            self.logger.info(
                "Workflow submitted successfully",
                extra={
                    "workflow_run_id": workflow_run.workflow_run_id,
                    "ownership": self.ownership.model_dump(),
                },
            )

            return workflow_run.workflow_run_id

        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}")
            raise

    def run_experiment(self) -> str:
        """Main experiment function with full context management."""

        try:
            self.logger.info(
                "Starting Enhanced Context Demo Experiment",
                extra={"ownership": self.ownership.model_dump()},
            )

            # Phase 1: Resource setup with templates and context
            self.logger.info("Phase 1: Setting up resources from templates")
            resource_ids = self.setup_lab_resources()

            # Phase 2: Context-aware workflow execution
            self.logger.info("Phase 2: Running context-aware workflow")
            workflow_id = self.run_context_aware_workflow(resource_ids)

            # Phase 3: Monitor with context tracking
            self.logger.info("Phase 3: Monitoring workflow with context tracking")
            self.monitor_workflow_with_context(workflow_id)

            self.logger.info(
                "Enhanced Context Demo completed successfully",
                extra={
                    "workflow_id": workflow_id,
                    "resource_count": len(resource_ids),
                    "ownership": self.ownership.model_dump(),
                },
            )

            return workflow_id

        except Exception as e:
            self.logger.error(f"Experiment failed: {e}")
            raise

    def monitor_workflow_with_context(self, workflow_id: str) -> None:
        """Monitor workflow execution with proper context tracking."""

        self.logger.info("Starting workflow monitoring with context tracking")

        try:
            # Poll workflow status with context-aware logging
            while True:
                status = self.workcell_client.get_workflow_run_status(workflow_id)

                self.logger.info(
                    f"Workflow status: {status.status}",
                    extra={
                        "workflow_run_id": workflow_id,
                        "ownership": self.ownership.model_dump(),
                        "step_count": len(status.steps) if status.steps else 0,
                    },
                )

                if status.status in ["completed", "failed", "cancelled"]:
                    break

                time.sleep(2)

            self.logger.info("Workflow monitoring completed")

        except Exception as e:
            self.logger.error(f"Workflow monitoring failed: {e}")


if __name__ == "__main__":
    app = EnhancedExampleApp(
        node_definition=NodeDefinition(
            node_name="enhanced_example_app", module_name="enhanced_example_app"
        )
    )
    app.start_app()
