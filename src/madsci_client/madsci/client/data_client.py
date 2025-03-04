"""Client for the MADSci Experiment Manager."""

import warnings
from pathlib import Path
from typing import Any, Optional, Union

import requests
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.datapoint_types import (
    DataPoint,
)
from pydantic import AnyUrl
from ulid import ULID


class DataClient:
    """Client for the MADSci Experiment Manager."""

    url: AnyUrl

    def __init__(
        self,
        url: Optional[Union[str, AnyUrl]],
        ownership_info: Optional[OwnershipInfo] = None,
    ) -> "DataClient":
        """Create a new Datapoint Client."""
        self.url = AnyUrl(url) if url is not None else None
        if self.url is None:
            warnings.warn(
                "No URL provided for the data client. Cannot persist datapoints.",
                UserWarning,
                stacklevel=2,
            )
        self._local_datapoints = {}
        self.ownership_info = ownership_info if ownership_info else OwnershipInfo()

    def get_datapoint(self, datapoint_id: Union[str, ULID]) -> dict:
        """Get an datapoint by ID."""
        if self.url is None:
            return self._local_datapoints[datapoint_id]
        response = requests.get(f"{self.url}/datapoint/{datapoint_id}", timeout=10)
        if not response.ok:
            response.raise_for_status()
        return DataPoint.discriminate(response.json())

    def get_datapoint_value(self, datapoint_id: Union[str, ULID]) -> Any:
        """Get an datapoint value by ID."""
        if self.url is None:
            return self._local_datapoints[datapoint_id].value
        response = requests.get(
            f"{self.url}/datapoint/{datapoint_id}/value", timeout=10
        )
        if not response.ok:
            response.raise_for_status()
        return response.content

    def save_datapoint_value(
        self, datapoint_id: Union[str, ULID], output_filepath: str
    ) -> None:
        """Get an datapoint value by ID."""
        if self.url is None:
            if self._local_datapoints[datapoint_id].data_type == "file":
                import shutil

                shutil.copyfile(
                    self._local_datapoints[datapoint_id].path, output_filepath
                )
            else:
                with Path.open(output_filepath, "w") as f:
                    f.write(str(self._local_datapoints[datapoint_id].value))
            return
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

    def get_datapoints(self, number: int = 10) -> list[DataPoint]:
        """Get a list of the latest datapoints."""
        if self.url is None:
            return list(self._local_datapoints.values()).sort(
                key=lambda x: x.datapoint_id, reverse=True
            )[:number]
        response = requests.get(
            f"{self.url}/datapoints", params={number: number}, timeout=10
        )
        if not response.ok:
            response.raise_for_status()
        return [DataPoint.discriminate(datapoint) for datapoint in response.json()]

    def submit_datapoint(self, datapoint: DataPoint) -> DataPoint:
        """Submit a Datapoint object"""
        if self.url is None:
            self._local_datapoints[datapoint.datapoint_id] = datapoint
            return datapoint
        if datapoint.data_type == "file":
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
        return DataPoint.discriminate(response.json())
