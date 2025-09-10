"""Transfer Manager Node that submits child workflows to execute transfers."""

from pathlib import Path
from threading import Lock
from typing import Annotated, Union

from madsci.client.workcell_client import WorkcellClient
from madsci.common.types.action_types import ActionFailed, ActionResult, ActionSucceeded
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.location_types import LocationArgument
from madsci.common.types.node_types import RestNodeConfig
from madsci.common.types.step_types import Step
from madsci.common.types.transfer_manager_types import (
    TransferManagerDefinition,
    TransferManagerSettings,
)
from madsci.common.types.workflow_types import WorkflowDefinition
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode
from madsci.transfer_manager.transfer_manager import (
    TransferManager,
    TransferManagerConfig,
)


class TransferNodeConfig(RestNodeConfig):
    """Configuration for the Transfer Node."""

    node_url: str = "http://localhost:8006"
    workcell_server_url: str = "http://localhost:8005"


class TransferNode(RestNode):
    """Transfer Node that submits child workflows to execute transfers"""

    config: TransferNodeConfig = TransferNodeConfig()
    config_model = TransferNodeConfig
    transfer_manager: TransferManager = None

    def startup_handler(self) -> None:
        """Initialize the transfer manager and workcell client using existing config resolution."""
        # Use existing transfer manager settings and definition resolution
        transfer_manager_settings = TransferManagerSettings()
        transfer_manager_path = Path(
            transfer_manager_settings.transfer_manager_definition
        )

        # Load or create transfer manager definition
        if transfer_manager_path.exists():
            transfer_manager_definition = TransferManagerDefinition.from_yaml(
                transfer_manager_path
            )
        else:
            # Create a default definition if none exists
            transfer_manager_definition = TransferManagerDefinition(
                transfer_manager_name="transfer_node"
            )

        # Resolve transfer config path properly, If it's not absolute, look in the same directory as the definition file
        transfer_config_path = Path(
            transfer_manager_definition.transfer_manager_config_path
        )
        if not transfer_config_path.is_absolute():
            transfer_config_path = transfer_manager_path.parent / transfer_config_path
        self.logger.info(f"Using transfer config at: {transfer_config_path}")

        # Initialize transfer manager with resolved config
        transfer_config = TransferManagerConfig(config_file_path=transfer_config_path)
        self.transfer_manager = TransferManager(transfer_config)

        # Initialize workcell client
        self.workcell_client = WorkcellClient(
            workcell_server_url=self.config.workcell_server_url
        )
        if self.resource_client:
            self.resource_owner = OwnershipInfo(node_id=self.node_definition.node_id)
        self.reservation_lock = Lock()
        self.logger.info(
            f"Transfer Node initialized with {len(self.transfer_manager.get_available_robots())} robots"
        )
        self.logger.info(
            f"Available locations: {self.transfer_manager.get_available_locations()}"
        )

    @action(
        name="transfer",
        description="Transfer between two locations by submitting child workflow",
    )
    def transfer(
        self,
        source: Annotated[LocationArgument, "Location to transfer from"],
        target: Annotated[LocationArgument, "Location to transfer to"],
    ) -> ActionResult:
        """Execute transfer by submitting child workflow to workcell manager."""

        # Acquire lock to ensure only one transfer executes at a time
        with self.reservation_lock:
            try:
                self.logger.info(
                    f"Starting transfer: {source.location_name} -> {target.location_name}"
                )

                # Create transfer step
                transfer_step = Step(
                    name=f"Transfer {source.location_name} -> {target.location_name}",
                    action="transfer",
                    node="",  # Let transfer manager choose path
                    locations={"source": source, "target": target},
                )

                # Expand transfer step into resolved steps
                resolved_steps = self.transfer_manager.expand_transfer_step(
                    transfer_step
                )

                self.logger.info(
                    f"Transfer expanded to {len(resolved_steps)} resolved steps"
                )

                # Create child workflow definition
                child_workflow_def = WorkflowDefinition(
                    name=f"Transfer: {source.location_name} -> {target.location_name}",
                    description="Child workflow for transfer operation",
                    steps=resolved_steps,
                    parameters=[],
                )

                # Submit child workflow and wait for completion
                child_workflow = self.workcell_client.submit_workflow(
                    workflow=child_workflow_def, parameters={}, await_completion=True
                )
                # Check child workflow result
                if child_workflow.status.completed:
                    self.logger.info(
                        f"Transfer completed successfully: {child_workflow.workflow_id}"
                    )
                    return ActionSucceeded(
                        data={
                            "child_workflow_id": child_workflow.workflow_id,
                            "resolved_steps_count": len(resolved_steps),
                        }
                    )

                if child_workflow.status.failed:
                    self.logger.error(
                        f"Transfer workflow failed: {child_workflow.workflow_id}"
                    )
                    return ActionFailed(
                        errors=[
                            f"Transfer workflow failed: {child_workflow.status.errors}"
                        ]
                    )

                if child_workflow.status.cancelled:
                    self.logger.warning(
                        f"Transfer workflow cancelled: {child_workflow.workflow_id}"
                    )
                    return ActionFailed(errors=["Transfer workflow was cancelled"])

                self.logger.error(
                    f"Transfer workflow ended unexpectedly: {child_workflow.workflow_id}"
                )
                return ActionFailed(
                    errors=["Transfer workflow ended in unexpected state"]
                )

            except Exception as e:
                self.logger.error(f"Transfer action failed: {e}")
                return ActionFailed(errors=[f"Transfer execution error: {e!s}"])

    @action(
        name="transfer_resource",
        description="Transfer a resource by ID to a target location",
    )
    def transfer_resource(
        self,
        source_resource: Annotated[
            Union[LocationArgument, str], "ID of the resource to transfer"
        ],
        target: Annotated[LocationArgument, "Target location to transfer to"],
    ) -> ActionResult:
        """Transfer a resource by ID to a target location."""

        if not self.resource_client:
            return ActionFailed(errors=["Resource client not available"])

        # Acquire lock for this transfer operation
        with self.reservation_lock:
            try:
                resource_id = (
                    source_resource
                    if isinstance(source_resource, str)
                    else source_resource.resource_id
                )
                self.logger.info(
                    f"Starting resource transfer: {resource_id} -> {target.location_name}"
                )

                # Get the resource and validate
                try:
                    resource = self.resource_client.get_resource(resource_id)
                    if not resource.parent_id:
                        raise ValueError(
                            f"Resource {resource_id} has no parent location"
                        )

                    parent_resource = self.resource_client.get_resource(
                        resource.parent_id
                    )
                    source_location_name = parent_resource.resource_name
                except Exception as e:
                    return ActionFailed(errors=[f"Resource validation failed: {e!s}"])

                self.logger.info(
                    f"Resource {resource_id} found at location '{source_location_name}', transferring to '{target.location_name}'"
                )

                # Create source LocationArgument
                source_location = LocationArgument(
                    location=source_resource.location
                    if isinstance(source_resource, LocationArgument)
                    else target.location,  # Use target's location if source is just an ID but this will be updated to actual location value by the manager
                    location_name=source_location_name,
                    resource_id=parent_resource.resource_id,
                )

                # Create transfer step
                transfer_step = Step(
                    name=f"Transfer resource {resource_id}: {source_location_name} -> {target.location_name}",
                    action="transfer",
                    node="",  # Let transfer manager choose path
                    locations={"source": source_location, "target": target},
                )

                # Expand transfer step into resolved steps
                resolved_steps = self.transfer_manager.expand_transfer_step(
                    transfer_step
                )

                self.logger.info(
                    f"Resource transfer expanded to {len(resolved_steps)} resolved steps"
                )

                # Create and submit child workflow
                child_workflow_def = WorkflowDefinition(
                    name=f"Resource Transfer: {resource_id} to {target.location_name}",
                    steps=resolved_steps,
                    parameters=[],
                )

                child_workflow = self.workcell_client.submit_workflow(
                    workflow=child_workflow_def, parameters={}, await_completion=True
                )

                # Handle workflow completion
                if child_workflow.status.completed:
                    self.logger.info(
                        f"Resource transfer completed successfully: {child_workflow.workflow_id}"
                    )
                    return ActionSucceeded(
                        data={
                            "child_workflow_id": child_workflow.workflow_id,
                            "resolved_steps_count": len(resolved_steps),
                        }
                    )
                # Handle all non-success states with generic failure
                status_info = f"Status: {child_workflow.status}"
                if child_workflow.status.failed or child_workflow.status.cancelled:
                    self.logger.error(
                        f"Resource transfer workflow failed: {status_info}"
                    )
                return ActionFailed(
                    errors=[f"Resource transfer workflow failed: {status_info}"]
                )

            except Exception as e:
                self.logger.error(f"Resource transfer action failed: {e}")
                return ActionFailed(
                    errors=[f"Resource transfer execution error: {e!s}"]
                )

    @action(
        name="get_transfer_options",
        description="Get available transfer path options between two locations",
    )
    def get_transfer_options(
        self,
        source: Annotated[str, "Source location name"],
        target: Annotated[str, "Target location name"],
    ) -> ActionResult:
        """Get available transfer path options."""
        try:
            options = self.transfer_manager.get_transfer_options(source, target)
            return ActionSucceeded(data={"transfer_options": options})
        except Exception as e:
            return ActionFailed(errors=[str(e)])

    @action(
        name="validate_transfer",
        description="Validate if a transfer between two locations is possible",
    )
    def validate_transfer(
        self,
        source: Annotated[str, "Source location name"],
        target: Annotated[str, "Target location name"],
    ) -> ActionResult:
        """Validate if a transfer is possible."""
        try:
            validation = self.transfer_manager.validate_transfer_request(source, target)
            return ActionSucceeded(data=validation)
        except Exception as e:
            return ActionFailed(errors=[str(e)])

    def shutdown_handler(self) -> None:
        """Cleanup when shutting down."""
        try:
            if self.transfer_manager is not None:
                del self.transfer_manager
                self.transfer_manager = None
                self.logger.info("Transfer manager shut down successfully.")
        except Exception as e:
            self.logger.error(f"Error during transfer node shutdown: {e}")
            raise e

    def state_handler(self) -> None:
        """Update node state - show available robots and locations."""
        if self.transfer_manager is not None:
            self.node_state = {
                "available_robots": self.transfer_manager.get_available_robots(),
                "available_locations": self.transfer_manager.get_available_locations(),
                "total_graph_edges": len(self.transfer_manager.transfer_graph.edges)
                if hasattr(self.transfer_manager, "transfer_graph")
                else 0,
            }
        else:
            self.node_state = {"status": "initializing"}
            self.logger.warning("Transfer manager is not initialized.")


if __name__ == "__main__":
    transfer_node = TransferNode()
    transfer_node.start_node()
