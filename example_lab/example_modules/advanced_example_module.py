"""A fake liquid handler module for testing."""

import time
from pathlib import Path
from typing import Any, Optional

from madsci.client.event_client import EventClient
from madsci.common.types.action_types import ActionResult, ActionSucceeded, ActionFiles, ActionJSON
from madsci.common.types.admin_command_types import AdminCommandResponse
from madsci.common.types.node_types import RestNodeConfig
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode


class ExampleJSONData(ActionJSON):
        example_value_1: str
        example_value_2: int

class ExampleFileData(ActionFiles):
        log_file_1: Path
        log_file_2: Path

class AdvancedExampleConfig(RestNodeConfig):
    """Configuration for the liquid handler node module."""

    device_number: int = 0
    """The device number of the liquid handler."""




class AdvancedExampleNode(RestNode):
    """A fake liquid handler node module for testing."""

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
        return {'a': "dict"}
    
    
    @action
    def return_file(
        self,
    ) -> Path:
        """Return a file"""

        with (Path.home() / "test.txt").open("w") as f:
            self.logger.log_info(f.write("test"))
        path = Path.home() / "test.txt"

        return path
    
    @action
    def return_file_and_json(
        self,
    ) -> tuple[int, Path]:
        """Return a file"""

        with (Path.home() / "test.txt").open("w") as f:
            self.logger.log_info(f.write("test"))
        path = Path.home() / "test.txt"

        #Must return json first then file
        return 5, path
    
    @action
    def return_labeled_json_values(self) -> ExampleJSONData:
        """Return labeled JSON values"""
        self.logger.log("returning labeled json")
        return ExampleJSONData(example_value_1="test", example_value_2=5)
    
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
    def return_labeled_file_and_json_values(self) -> tuple[ExampleJSONData, ExampleFileData]:
        """Return labeled file and json values"""

        with (Path.home() / "test1.txt").open("w") as f:
            self.logger.log_info(f.write("test1"))
        path1 = Path.home() / "test1.txt"
        with (Path.home() / "test2.txt").open("w") as f:
            self.logger.log_info(f.write("test2"))
        path2 = Path.home() / "test2.txt"

        return ExampleJSONData(example_value_1="test", example_value_2=5), ExampleFileData(log_file_1=path1, log_file_2=path2)
    
    
    

    
   

    def get_location(self) -> AdminCommandResponse:
        """Get location for the liquid handler"""
        return AdminCommandResponse(data=[0, 0, 0, 0])


if __name__ == "__main__":
    liquid_handler_node = AdvancedExampleNode()
    liquid_handler_node.start_node()
