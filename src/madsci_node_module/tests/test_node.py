"""A Node implementation to use in automated tests."""

import tempfile
from pathlib import Path
from typing import Annotated, Optional, Union

from madsci.client.event_client import EventClient
from madsci.common.types.action_types import ActionFiles
from madsci.common.types.node_types import RestNodeConfig
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode
from pydantic import BaseModel, Field


class TestNodeConfig(RestNodeConfig):
    """Configuration for the test node module."""

    __test__ = False

    test_required_param: int
    """A required parameter."""
    test_optional_param: Optional[int] = None
    """An optional parameter."""
    test_default_param: int = 42
    """A parameter with a default value."""
    update_node_files: bool = False


class TestResults(BaseModel):
    """Test custom pydantic model for results"""

    test_id: str = Field(description="Test identifier")
    value: float = Field(description="Test measurement value")
    status: str = Field(description="Test status")
    metadata: dict[str, Union[str, bool, int]] = Field(
        default_factory=dict, description="Additional metadata"
    )


class TestNodeInterface:
    """A fake test interface for testing."""

    __test__ = False

    status_code: int = 0

    def __init__(self, logger: Optional[EventClient] = None) -> "TestNodeInterface":
        """Initialize the test interface."""
        self.logger = logger if logger else EventClient()

    def run_command(self, command: str, fail: bool = False) -> bool:
        """Run a command on the test interface."""
        self.logger.log(f"Running command {command}.")
        if fail:
            self.logger.log(f"Failed to run command {command}.")
            return False
        return True


class TestNode(RestNode):
    """A test node module for automated testing."""

    __test__ = False

    test_interface: TestNodeInterface = None
    config: TestNodeConfig
    config_model = TestNodeConfig

    def startup_handler(self) -> None:
        """Called to (re)initialize the node. Should be used to open connections to devices or initialize any other resources."""
        self.logger.log("Node initializing...")
        self.test_interface = TestNodeInterface(logger=self.logger)
        self.startup_has_run = True
        self.logger.log("Test node initialized!")

    def shutdown_handler(self) -> None:
        """Called to shutdown the node. Should be used to close connections to devices or release any other resources."""
        self.logger.log("Shutting down")
        self.shutdown_has_run = True
        del self.test_interface
        self.test_interface = None
        self.logger.log("Shutdown complete.")

    def state_handler(self) -> None:
        """Periodically called to update the current state of the node."""
        if self.test_interface is not None:
            self.node_state = {
                "test_status_code": self.test_interface.status_code,
            }

    @action
    def test_action(self, test_param: int) -> None:
        """A test action."""
        result = self.test_interface.run_command(
            f"Test action with param {test_param}."
        )
        if result:
            return
        raise ValueError(f"`run_command` returned '{result}'. Expected 'True'.")

    @action(name="test_fail", description="A test action that fails.")
    def test_action_fail(self, test_param: int) -> None:
        """A doc string, but not the actual description of the action."""
        result = self.test_interface.run_command(
            f"Test action with param {test_param}.", fail=True
        )
        if result:
            return
        raise ValueError(f"`run_command` returned '{result}'. Expected 'True'.")

    def pause(self) -> None:
        """Pause the node."""
        self.logger.log("Pausing node...")
        self.node_status.paused = True
        self.logger.log("Node paused.")
        return True

    def resume(self) -> None:
        """Resume the node."""
        self.logger.log("Resuming node...")
        self.node_status.paused = False
        self.logger.log("Node resumed.")
        return True

    def shutdown(self) -> None:
        """Shutdown the node."""
        self.shutdown_handler()
        return True

    def reset(self) -> None:
        """Reset the node."""
        self.logger.log("Resetting node...")
        result = super().reset()
        self.logger.log("Node reset.")
        return result

    def safety_stop(self) -> None:
        """Stop the node."""
        self.logger.log("Stopping node...")
        self.node_status.stopped = True
        self.logger.log("Node stopped.")
        return True

    def cancel(self) -> None:
        """Cancel the node."""
        self.logger.log("Canceling node...")
        self.node_status.cancelled = True
        self.logger.log("Node cancelled.")
        return True

    @action
    def test_optional_param_action(
        self, test_param: int, optional_param: Optional[str] = ""
    ) -> None:
        """A test action with an optional parameter."""
        result = self.test_interface.run_command(
            f"Test action with param {test_param}."
        )
        if not result:
            raise ValueError(
                errors=f"`run_command` returned '{result}'. Expected 'True'."
            )
        if optional_param:
            result = self.test_interface.run_command(
                f"Test action with optional param {optional_param}."
            )
        if result:
            return
        raise ValueError(errors=f"`run_command` returned '{result}'. Expected 'True'.")

    @action
    def test_annotation_action(
        self,
        test_param: Annotated[int, "Description"] = 1,
        test_param_2: Optional[Annotated[int, "Description 2"]] = 2,
        test_param_3: Annotated[Optional[int], "Description 3"] = 3,
    ) -> None:
        """A no-op action to test argument parsing"""
        self.logger.log(
            f"Test annotation action with params {test_param}, {test_param_2}, {test_param_3}"
        )

    @action
    def file_action(
        self, config_file: Path, optional_file: Optional[Path] = None
    ) -> str:
        """Test action that requires a file parameter.

        Args:
            config_file: A required configuration file
            optional_file: An optional file parameter
        """
        self.logger.log(f"Processing file action with config_file: {config_file}")
        if optional_file:
            self.logger.log(f"Also processing optional_file: {optional_file}")

        # Simple file processing - just return the file name
        return config_file.name if config_file else "no_file"

    @action
    def file_result_action(self, data: str = "test") -> Path:
        """Test action that returns a single file.

        Args:
            data: Data to write to the result file

        Returns:
            Path: A temporary file containing the data
        """
        self.logger.log(f"Creating file result with data: {data}")

        # Create a temporary file with the data
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as temp_file:
            temp_file.write(f"Result data: {data}")
            return Path(temp_file.name)

    class FileResults(ActionFiles):
        """Multiple file results for testing."""

        output_file: Path
        log_file: Path

    @action
    def multiple_file_result_action(self, data: str = "test") -> FileResults:
        """Test action that returns multiple files.

        Args:
            data: Data to write to the result files

        Returns:
            FileResults: Multiple files containing the processed data
        """
        self.logger.log(f"Creating multiple file results with data: {data}")

        # Create output file
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".out"
        ) as output_file:
            output_file.write(f"Output: {data}")
            output_path = Path(output_file.name)

        # Create log file
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".log"
        ) as log_file:
            log_file.write(f"Log: Processing {data}")
            log_path = Path(log_file.name)

        return self.FileResults(output_file=output_path, log_file=log_path)

    @action
    def custom_pydantic_result_action(self, test_id: str = "test_001") -> TestResults:
        """Test action that returns a custom pydantic model.

        Args:
            test_id: Identifier for the test

        Returns:
            TestResults: Custom pydantic model with test results
        """
        self.logger.log(f"Creating custom pydantic result for test: {test_id}")

        return TestResults(
            test_id=test_id,
            value=42.5,
            status="completed",
            metadata={"instrument": "test_instrument", "operator": "test_user"},
        )

    @action
    def mixed_pydantic_and_file_action(
        self, test_id: str = "mixed_001"
    ) -> tuple[TestResults, Path]:
        """Test action that returns both a custom pydantic model and a file.

        Args:
            test_id: Identifier for the test

        Returns:
            tuple[TestResults, Path]: Custom model and a file
        """
        self.logger.log(f"Creating mixed result for test: {test_id}")

        # Create the file
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".json"
        ) as temp_file:
            temp_file.write(f'{{"test_id": "{test_id}", "raw_data": [1.0, 2.0, 3.0]}}')
            file_path = Path(temp_file.name)

        # Create the pydantic model
        result = TestResults(
            test_id=test_id,
            value=123.45,
            status="completed",
            metadata={"type": "mixed_return", "file_created": True},
        )

        return result, file_path


if __name__ == "__main__":
    test_node = TestNode()
    test_node.start_node()
