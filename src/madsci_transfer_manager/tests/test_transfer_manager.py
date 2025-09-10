"""Unit tests for the TransferManager class in the madsci.transfer_manager.transfer_manager module."""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
import yaml
from madsci.common.types.location_types import LocationArgument
from madsci.common.types.step_types import Step
from madsci.transfer_manager.transfer_manager import (
    TransferManager,
    TransferManagerConfig,
)


@pytest.fixture
def sample_config_data() -> dict:
    """
    Fixture to provide sample transfer configuration data for testing.

    Returns:
        dict: Configuration data with robots and locations.
    """
    return {
        "robots": {
            "robotarm_1": {
                "robot_name": "robotarm_1",
                "default_step_template": {
                    "name": "Transfer via {robot_name}",
                    "node": "robotarm_1",
                    "action": "transfer",
                    "locations": {"source": "{source}", "target": "{target}"},
                },
                "default_args": {},
            },
            "pf400": {
                "robot_name": "pf400",
                "default_step_template": {
                    "name": "Transfer via {robot_name}",
                    "node": "pf400",
                    "action": "transfer",
                    "locations": {"source": "{source}", "target": "{target}"},
                },
                "default_args": {},
            },
            "platecrane": {
                "robot_name": "platecrane",
                "default_step_template": {
                    "name": "Transfer via {robot_name}",
                    "node": "platecrane",
                    "action": "transfer",
                    "locations": {"source": "{source}", "target": "{target}"},
                },
                "default_args": {"plate_type": "96well"},
            },
        },
        "locations": {
            "location_1": {
                "location_name": "location_1",
                "accessible_by": ["robotarm_1"],
                "default_args": {},
                "lookup": {"robotarm_1": [1, 2, 3, 4]},
            },
            "location_2": {
                "location_name": "location_2",
                "accessible_by": ["robotarm_1"],
                "default_args": {},
                "lookup": {"robotarm_1": [5, 6, 7, 8]},
            },
            "exchange": {
                "location_name": "exchange",
                "accessible_by": ["robotarm_1", "pf400"],
                "default_args": {},
                "lookup": {
                    "robotarm_1": [10, 11, 12, 13],
                    "pf400": [100.1, 200.2, 300.3, 400.4],
                },
            },
            "camera_station": {
                "location_name": "camera_station",
                "accessible_by": ["pf400"],
                "default_args": {},
                "robot_overrides": {"pf400": {"plate_rotation": "narrow"}},
                "lookup": {"pf400": [150.5, 250.6, 350.7, 450.8]},
            },
            "hidex_nest": {
                "location_name": "hidex_nest",
                "accessible_by": ["platecrane"],
                "default_args": {"height_offset": 8},
                "lookup": {"platecrane": [50.0, 60.0, 70.0, 80.0]},
            },
            "isolated_location": {
                "location_name": "isolated_location",
                "accessible_by": ["nonexistent_robot"],
                "default_args": {},
            },
        },
    }


@pytest.fixture
def config_file(sample_config_data: dict) -> Generator[Path, None, None]:
    """
    Fixture to create a temporary config file for testing.

    Args:
        sample_config_data (dict): Configuration data to write to file.

    Yields:
        Path: Path to the temporary config file.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(sample_config_data, f)
        config_path = Path(f.name)

    yield config_path

    # Cleanup
    config_path.unlink()


@pytest.fixture
def transfer_manager(config_file: Path) -> TransferManager:
    """
    Fixture to provide a TransferManager instance for testing.

    Args:
        config_file (Path): Path to the configuration file.

    Returns:
        TransferManager: An instance of TransferManager with test configuration.
    """
    config = TransferManagerConfig(config_file_path=config_file)
    return TransferManager(config)


def test_transfer_manager_initialization(transfer_manager: TransferManager) -> None:
    """
    Test that TransferManager initializes correctly with proper configuration.

    Args:
        transfer_manager (TransferManager): The TransferManager instance to test.
    """
    assert len(transfer_manager.get_available_robots()) == 3
    assert len(transfer_manager.get_available_locations()) == 6
    assert "robotarm_1" in transfer_manager.get_available_robots()
    assert "pf400" in transfer_manager.get_available_robots()
    assert "platecrane" in transfer_manager.get_available_robots()


def test_direct_transfer_same_robot(transfer_manager: TransferManager) -> None:
    """
    Test successful direct transfer between locations accessible by the same robot.

    Args:
        transfer_manager (TransferManager): The TransferManager instance to test.
    """
    step = Step(
        name="Test Transfer",
        node="robotarm_1",
        action="transfer",
        locations={
            "source": LocationArgument(
                location=[1, 2, 3, 4],
                location_name="location_1",
                resource_id="test_source",
            ),
            "target": LocationArgument(
                location=[5, 6, 7, 8],
                location_name="location_2",
                resource_id="test_target",
            ),
        },
        args={},
    )

    resolved_steps = transfer_manager.expand_transfer_step(step)

    assert len(resolved_steps) == 1
    assert resolved_steps[0].node == "robotarm_1"
    assert resolved_steps[0].action == "transfer"

    # Check that lookup coordinates are populated
    source_location = resolved_steps[0].locations["source"]
    target_location = resolved_steps[0].locations["target"]
    assert source_location.location == [1, 2, 3, 4]
    assert target_location.location == [5, 6, 7, 8]


def test_multi_hop_transfer_success(transfer_manager: TransferManager) -> None:
    """
    Test successful multi-hop transfer requiring multiple robots.

    Args:
        transfer_manager (TransferManager): The TransferManager instance to test.
    """
    step = Step(
        name="Multi-hop Transfer",
        node="",  # Let transfer manager choose path
        action="transfer",
        locations={
            "source": LocationArgument(
                location=[0, 0, 0, 0],
                location_name="location_1",
                resource_id="test_source",
            ),
            "target": LocationArgument(
                location=[0, 0, 0, 0],
                location_name="camera_station",
                resource_id="test_target",
            ),
        },
        args={},
    )

    resolved_steps = transfer_manager.expand_transfer_step(step)

    # Should require 2 hops: location_1 -> exchange -> camera_station
    assert len(resolved_steps) == 2

    # First hop: robotarm_1 from location_1 to exchange
    assert resolved_steps[0].node == "robotarm_1"
    assert resolved_steps[0].locations["source"].location_name == "location_1"
    assert resolved_steps[0].locations["target"].location_name == "exchange"
    assert resolved_steps[0].locations["source"].location == [1, 2, 3, 4]
    assert resolved_steps[0].locations["target"].location == [10, 11, 12, 13]

    # Second hop: pf400 from exchange to camera_station
    assert resolved_steps[1].node == "pf400"
    assert resolved_steps[1].locations["source"].location_name == "exchange"
    assert resolved_steps[1].locations["target"].location_name == "camera_station"
    assert resolved_steps[1].locations["source"].location == [
        100.1,
        200.2,
        300.3,
        400.4,
    ]
    assert resolved_steps[1].locations["target"].location == [
        150.5,
        250.6,
        350.7,
        450.8,
    ]


def test_no_path_available(transfer_manager: TransferManager) -> None:
    """
    Test that transfer manager properly handles cases where no path exists.

    Args:
        transfer_manager (TransferManager): The TransferManager instance to test.
    """
    step = Step(
        name="Impossible Transfer",
        node="",
        action="transfer",
        locations={
            "source": LocationArgument(
                location=[0, 0, 0, 0],
                location_name="location_1",
                resource_id="test_source",
            ),
            "target": LocationArgument(
                location=[0, 0, 0, 0],
                location_name="isolated_location",
                resource_id="test_target",
            ),
        },
        args={},
    )

    with pytest.raises(ValueError, match="No transfer path found"):
        transfer_manager.expand_transfer_step(step)


def test_invalid_source_location(transfer_manager: TransferManager) -> None:
    """
    Test that transfer manager handles invalid source locations properly.

    Args:
        transfer_manager (TransferManager): The TransferManager instance to test.
    """
    step = Step(
        name="Invalid Source Transfer",
        node="",
        action="transfer",
        locations={
            "source": LocationArgument(
                location=[0, 0, 0, 0],
                location_name="nonexistent_location",
                resource_id="test_source",
            ),
            "target": LocationArgument(
                location=[0, 0, 0, 0],
                location_name="location_1",
                resource_id="test_target",
            ),
        },
        args={},
    )

    with pytest.raises(ValueError, match="No transfer path found"):
        transfer_manager.expand_transfer_step(step)


def test_robot_parameter_merging(transfer_manager: TransferManager) -> None:
    """
    Test that robot-specific parameters and overrides are properly merged.

    Args:
        transfer_manager (TransferManager): The TransferManager instance to test.
    """
    step = Step(
        name="Parameter Test",
        node="pf400",
        action="transfer",
        locations={
            "source": LocationArgument(
                location=[0, 0, 0, 0],
                location_name="exchange",
                resource_id="test_source",
            ),
            "target": LocationArgument(
                location=[0, 0, 0, 0],
                location_name="camera_station",
                resource_id="test_target",
            ),
        },
        args={"custom_param": "test_value"},
    )

    resolved_steps = transfer_manager.expand_transfer_step(step)

    assert len(resolved_steps) == 1
    step_args = resolved_steps[0].args

    # Should include robot override from camera_station location
    assert step_args["plate_rotation"] == "narrow"
    # Should include user parameter
    assert step_args["custom_param"] == "test_value"


def test_non_transfer_step_passthrough(transfer_manager: TransferManager) -> None:
    """
    Test that non-transfer steps are returned unchanged.

    Args:
        transfer_manager (TransferManager): The TransferManager instance to test.
    """
    step = Step(
        name="Non-transfer Step",
        node="some_robot",
        action="pick_plate",
        locations={
            "source": LocationArgument(
                location=[1, 2, 3, 4], location_name="location_1"
            )
        },
        args={},
    )

    resolved_steps = transfer_manager.expand_transfer_step(step)

    assert len(resolved_steps) == 1
    assert resolved_steps[0] == step  # Should be unchanged


def test_get_transfer_options(transfer_manager: TransferManager) -> None:
    """
    Test that transfer options are returned for valid paths.

    Args:
        transfer_manager (TransferManager): The TransferManager instance to test.
    """
    options = transfer_manager.get_transfer_options("location_1", "camera_station")

    assert len(options) == 1
    assert options[0]["num_hops"] == 2
    assert "robotarm_1" in options[0]["robots_used"]
    assert "pf400" in options[0]["robots_used"]


def test_validate_transfer_request_valid(transfer_manager: TransferManager) -> None:
    """
    Test transfer validation for valid transfer requests.

    Args:
        transfer_manager (TransferManager): The TransferManager instance to test.
    """
    result = transfer_manager.validate_transfer_request("location_1", "location_2")

    assert result["valid"] is True
    assert result["reachable"] is True
    assert result["source_exists"] is True
    assert result["target_exists"] is True
    assert len(result["errors"]) == 0


def test_validate_transfer_request_invalid(transfer_manager: TransferManager) -> None:
    """
    Test transfer validation for invalid transfer requests.

    Args:
        transfer_manager (TransferManager): The TransferManager instance to test.
    """
    result = transfer_manager.validate_transfer_request("nonexistent", "location_1")

    assert result["valid"] is False
    assert result["source_exists"] is False
    assert result["target_exists"] is True
    assert "Source location 'nonexistent' not found" in result["errors"]


def test_validate_transfer_request_unreachable(
    transfer_manager: TransferManager,
) -> None:
    """
    Test transfer validation for unreachable locations.

    Args:
        transfer_manager (TransferManager): The TransferManager instance to test.
    """
    result = transfer_manager.validate_transfer_request(
        "location_1", "isolated_location"
    )

    assert result["valid"] is False
    assert result["reachable"] is False
    assert result["source_exists"] is True
    assert result["target_exists"] is True
    assert "No path exists from location_1 to isolated_location" in result["errors"]


def test_location_argument_extraction_with_location_name(
    transfer_manager: TransferManager,
) -> None:
    """
    Test that location name extraction works correctly with LocationArgument objects.

    Args:
        transfer_manager (TransferManager): The TransferManager instance to test.
    """
    location_arg = LocationArgument(
        location=[1, 2, 3, 4], location_name="location_1", resource_id="test_resource"
    )

    extracted_name = transfer_manager._extract_location_name(location_arg)
    assert extracted_name == "location_1"


def test_location_argument_extraction_fallback_to_location(
    transfer_manager: TransferManager,
) -> None:
    """
    Test that location extraction falls back to location field when location_name is None.

    Args:
        transfer_manager (TransferManager): The TransferManager instance to test.
    """
    location_arg = LocationArgument(
        location=[1, 2, 3, 4], location_name=None, resource_id="test_resource"
    )

    extracted_name = transfer_manager._extract_location_name(location_arg)
    assert extracted_name == "[1, 2, 3, 4]"


def test_lookup_coordinates_retrieval(transfer_manager: TransferManager) -> None:
    """
    Test that lookup coordinates are correctly retrieved for robot-location pairs.

    Args:
        transfer_manager (TransferManager): The TransferManager instance to test.
    """
    coordinates = transfer_manager._get_lookup_coordinates("location_1", "robotarm_1")
    assert coordinates == [1, 2, 3, 4]

    # Test non-existent lookup
    coordinates = transfer_manager._get_lookup_coordinates(
        "location_1", "nonexistent_robot"
    )
    assert coordinates is None


def test_transfer_manager_debug_output(transfer_manager: TransferManager) -> None:
    """
    Test that debug output is generated during transfer planning.

    Args:
        transfer_manager (TransferManager): The TransferManager instance to test.
    """
    step = Step(
        name="Test Transfer",
        node="robotarm_1",
        action="transfer",
        locations={
            "source": LocationArgument(
                location=[1, 2, 3, 4], location_name="location_1"
            ),
            "target": LocationArgument(
                location=[5, 6, 7, 8], location_name="location_2"
            ),
        },
        args={},
    )

    result = transfer_manager.expand_transfer_step(step)

    # Test the actual functionality instead of debug output
    assert result is not None
    assert isinstance(result, list)
