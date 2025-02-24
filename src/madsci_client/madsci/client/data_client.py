"""Client for the MADSci Experiment Manager."""

from pathlib import Path
from typing import Any, Optional, Union

import requests
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.datapoint_types import (
    DataPoint,
    data_types,
)
from pydantic import AnyUrl
from ulid import ULID


class DataClient:
    """Client for the MADSci Experiment Manager."""

    url: AnyUrl

    def __init__(
        self, url: Union[str, AnyUrl], ownership_info: Optional[OwnershipInfo] = None
    ) -> "DataClient":
        """Create a new Datapoint Client."""
        self.url = AnyUrl(url)
        self.ownership_info = ownership_info if ownership_info else OwnershipInfo()

    def get_datapoint(self, datapoint_id: Union[str, ULID]) -> dict:
        """Get an datapoint by ID."""
        response = requests.get(f"{self.url}/datapoint/{datapoint_id}", timeout=10)
        if not response.ok:
            response.raise_for_status()
        response = response.json()
        return data_types[response["type"]].model_validate(response)

    def get_datapoint_value(self, datapoint_id: Union[str, ULID]) -> Any:
        """Get an datapoint value by ID."""
        response = requests.get(
            f"{self.url}/datapoint/{datapoint_id}/value", timeout=10
        )
        if not response.ok:
            response.raise_for_status()
        return response.content

    def save_datapoint_value(
        self, datapoint_id: Union[str, ULID], output_filepath: str
    ) -> Any:
        """Get an datapoint value by ID."""
        response = requests.get(
            f"{self.url}/datapoint/{datapoint_id}/value", timeout=10
        )
        if not response.ok:
            response.raise_for_status()
        try:
            with Path.open(output_filepath, "w") as f:
                f.write(str(response.json()["value"]))

        except Exception:
            Path(output_filepath).parent.mkdir(parents=True, exist_ok=True)
            with Path.open(output_filepath, "wb") as f:
                f.write(response.content)
        return response.content

    def get_datapoints(self, number: int = 10) -> list[DataPoint]:
        """Get a list of the latest datapoints."""
        response = requests.get(
            f"{self.url}/datapoints", params={number: number}, timeout=10
        )
        if not response.ok:
            response.raise_for_status()
        return [
            data_types[datapoint["type"]].model_validate(datapoint)
            for datapoint in response.json()
        ]

    def submit_datapoint(self, datapoint: DataPoint) -> DataPoint:
        """Submit a Datapoint object"""
        if datapoint.type == "local_file":
            files = {
                (
                    "files",
                    (
                        str(Path(datapoint.path).name),
                        Path.open(Path(datapoint.path), "rb"),
                    ),
                )
            }
        else:
            files = {}
        response = requests.post(
            "/datapoint",
            data={"datapoint": datapoint.model_dump_json()},
            files=files,
            timeout=10,
        )
        if not response.ok:
            response.raise_for_status()
        datapoint = response.json()
        return data_types[datapoint["type"]].model_validate(datapoint)
