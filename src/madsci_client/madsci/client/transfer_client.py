"""Client for the MADSci Transfer Manager."""

from typing import Optional, Union, List

import requests
from madsci.common.types.context_types import MadsciContext
from madsci.common.types.step_types import Step
from pydantic import AnyUrl


class TransferManagerClient:
    """Client for the MADSci Transfer Manager."""

    transfer_server_url: AnyUrl

    def __init__(
        self,
        transfer_server_url: Optional[Union[str, AnyUrl]] = None,
    ) -> "TransferManagerClient":
        """Create a new Transfer Manager Client."""
        self.context = (
            MadsciContext(transfer_server_url=transfer_server_url)
            if transfer_server_url
            else MadsciContext()
        )
        
        # Use provided URL or default
        if transfer_server_url:
            self.transfer_server_url = transfer_server_url
        else:
            # Default to localhost if not in context
            self.transfer_server_url = "http://localhost:8006"
        
        if not self.transfer_server_url:
            raise ValueError(
                "No transfer server URL provided, please specify a URL or set the context."
            )

    def handle_transfer_step(self, step: Step) -> List[Step]:
        """
        Handle a transfer step by expanding it into concrete workflow steps.
        This is the main method workcell managers will use.
        """
        response = requests.post(
            f"{self.transfer_server_url}/handle_transfer_step",
            json=step.model_dump(mode="json"),
            timeout=30  # Transfer planning can take time
        )
        if not response.ok:
            response.raise_for_status()
        
        # Convert response back to Step objects
        concrete_steps = []
        for step_data in response.json():
            concrete_steps.append(Step.model_validate(step_data))
        
        return concrete_steps