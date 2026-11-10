"""An example to demonstrate how to use the SilaClient to connect to a SiLA node module and list the features."""

from example_lab.example_modules.liquidhandler import (
    LiquidHandlerConfig,
    LiquidHandlerNode,
)
from sila2.client import SilaClient

liquid_handler_node = LiquidHandlerNode()
liquid_handler_node.config = LiquidHandlerConfig(
    node_name="liquidhandler_1",
    node_type="device",
    node_url="http://localhost:4037",
    node_description="A liquid handler node for testing",
)
liquid_handler_node.server.start_insecure("localhost", 4037)
client = SilaClient(address="localhost", port=4037, insecure=True)
feature_id = client.SiLAService.ImplementedFeatures.get()[1]
parts = str(feature_id).split("/")
# The identifier is the second-to-last part (before the version)
feature_id = parts[-2]
feature = getattr(client, feature_id)
print(feature.MADSCIGetState.get())  # noqa: T201
liquid_handler_node.server.stop()
