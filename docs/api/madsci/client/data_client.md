Module madsci.client.data_client
================================
Client for the MADSci Experiment Manager.

Classes
-------

`DataClient(data_server_url: str | pydantic.networks.AnyUrl | None = None, object_storage_settings: madsci.common.types.datapoint_types.ObjectStorageSettings | None = None, config: madsci.common.types.client_types.DataClientConfig | None = None)`
:   Client for the MADSci Experiment Manager.

    Create a new Datapoint Client.

    Args:
        data_server_url: The base URL of the Data Manager. If not provided, it will be taken from the current MadsciContext.
        object_storage_settings: Configuration for object storage (e.g., MinIO). If not provided, defaults will be used.
        config: Client configuration for retry and timeout settings. If not provided, uses default DataClientConfig.

    ### Class variables

    `data_server_url: pydantic.networks.AnyUrl | None`
    :

    ### Methods

    `extract_datapoint_ids_from_action_result(self, action_result: Any) ‑> list[str]`
    :   Extract all datapoint IDs from an ActionResult.

        Args:
            action_result: ActionResult object to extract IDs from

        Returns:
            List of unique datapoint ULID strings

    `get_datapoint(self, datapoint_id: str | ulid.ULID, timeout: float | None = None) ‑> madsci.common.types.datapoint_types.DataPoint`
    :   Get a datapoint's metadata by ID, either from local storage or server.

        Args:
            datapoint_id: The ID of the datapoint to get.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_datapoint_metadata(self, datapoint_id: str) ‑> dict[str, typing.Any]`
    :   Get basic metadata for a datapoint without fetching the full data.

        Useful for UI display where you need labels, types, timestamps, etc.
        without loading large file contents or values.

        Args:
            datapoint_id: ULID string of the datapoint

        Returns:
            Dictionary with metadata fields like label, data_type, data_timestamp

    `get_datapoint_value(self, datapoint_id: str | ulid.ULID, timeout: float | None = None) ‑> Any`
    :   Get a datapoint value by ID. If the datapoint is JSON, returns the JSON data.
        Otherwise, returns the raw data as bytes.

        Args:
            datapoint_id: The ID of the datapoint to get.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_data_operations.

    `get_datapoints(self, number: int = 10, timeout: float | None = None) ‑> list[madsci.common.types.datapoint_types.DataPoint]`
    :   Get a list of the latest datapoints.

        Args:
            number: Number of datapoints to retrieve.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `get_datapoints_by_ids(self, datapoint_ids: list[str]) ‑> dict[str, madsci.common.types.datapoint_types.DataPoint]`
    :   Fetch multiple datapoints by their IDs in a batch operation.

        This method enables just-in-time fetching of datapoints when only IDs are stored
        in workflows, following the principle of efficient datapoint management.

        Args:
            datapoint_ids: List of datapoint ULID strings to fetch

        Returns:
            Dictionary mapping datapoint IDs to DataPoint objects

        Raises:
            Exception: If any datapoint cannot be fetched

    `get_datapoints_metadata(self, datapoint_ids: list[str]) ‑> dict[str, dict[str, typing.Any]]`
    :   Get metadata for multiple datapoints efficiently.

        Args:
            datapoint_ids: List of datapoint ULID strings

        Returns:
            Dictionary mapping datapoint IDs to metadata dictionaries

    `query_datapoints(self, selector: Any, timeout: float | None = None) ‑> dict[str, madsci.common.types.datapoint_types.DataPoint]`
    :   Query datapoints based on a selector.

        Args:
            selector: Query selector for filtering datapoints.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.

    `save_datapoint_value(self, datapoint_id: str | ulid.ULID, output_filepath: str, timeout: float | None = None) ‑> None`
    :   Get an datapoint value by ID.

        Args:
            datapoint_id: The ID of the datapoint to save.
            output_filepath: Path where the datapoint value should be saved.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_data_operations.

    `submit_datapoint(self, datapoint: madsci.common.types.datapoint_types.DataPoint, timeout: float | None = None) ‑> madsci.common.types.datapoint_types.DataPoint`
    :   Submit a Datapoint object.

        If object storage is configured and the datapoint is a file type,
        the file will be automatically uploaded to object storage instead
        of being sent to the Data Manager server.

        Args:
            datapoint: The datapoint to submit.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_data_operations.

        Returns:
            The submitted datapoint with server-assigned IDs if applicable
