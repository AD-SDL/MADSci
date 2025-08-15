#!/usr/bin/env python3
"""Test script for Transfer Manager."""

from pathlib import Path

from madsci.common.types.step_types import Step

# Add the path where your transfer manager code is located
# sys.path.append('/path/to/your/madsci/transfer_manager')
from transfer_manager import TransferManager, TransferManagerConfig


def print_separator(title):
    """Print a nice separator for test sections."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_step_details(step, index=None):
    """Print detailed information about a step."""
    prefix = f"Step {index}: " if index is not None else ""
    print(f"  {prefix}{step.name}")
    print(f"    Node: {step.node}")
    print(f"    Action: {step.action}")
    print(f"    Args: {step.args}")
    print(f"    Locations: {step.locations}")


def test_basic_functionality():
    """Test basic transfer manager functionality."""
    print_separator("Basic Transfer Manager Tests")

    # Initialize transfer manager
    config = TransferManagerConfig(
        robot_definitions_path=Path(
            "/Users/dozgulbas/workspace/MADSci/src/madsci_transfer_manager/madsci/transfer_manager/test_robot_definitions.yaml"
        ),
        location_constraints_path=Path(
            "/Users/dozgulbas/workspace/MADSci/src/madsci_transfer_manager/madsci/transfer_manager/test_location_constraints.yaml"
        ),
    )

    manager = TransferManager(config)
    print("✓ Transfer Manager initialized successfully")

    # Test basic info methods
    robots = manager.get_available_robots()
    locations = manager.get_available_locations()

    print(f"✓ Available robots: {robots}")
    print(f"✓ Available locations: {locations}")
    print(f"✓ Total locations in graph: {len(manager.transfer_graph.locations)}")


def test_direct_transfers():
    """Test simple direct transfers."""
    print_separator("Direct Transfer Tests")

    config = TransferManagerConfig(
        robot_definitions_path=Path(
            "/Users/dozgulbas/workspace/MADSci/src/madsci_transfer_manager/madsci/transfer_manager/test_robot_definitions.yaml"
        ),
        location_constraints_path=Path(
            "/Users/dozgulbas/workspace/MADSci/src/madsci_transfer_manager/madsci/transfer_manager/test_location_constraints.yaml"
        ),
    )
    manager = TransferManager(config)

    # Test 1: Simple robotarm transfer
    print("\nTest 1: Direct transfer between robotarm locations")
    step = Step(
        name="Test Transfer",
        node="robotarm_1",
        action="transfer",
        locations={"source": "location_1", "target": "location_2"},
        args={},
    )

    result = manager.expand_transfer_step(step)
    print(f"✓ Generated {len(result)} steps:")
    for i, s in enumerate(result, 1):
        print_step_details(s, i)

    # Test 2: Platecrane transfer with location constraints
    print("\nTest 2: Platecrane transfer with special parameters")
    step = Step(
        name="Hidex Transfer",
        node="platecrane",
        action="transfer",
        locations={"source": "sealer_nest", "target": "hidex_nest"},
        args={},
    )

    result = manager.expand_transfer_step(step)
    print(f"✓ Generated {len(result)} steps:")
    for i, s in enumerate(result, 1):
        print_step_details(s, i)


def test_multi_hop_transfers():
    """Test complex multi-hop transfers."""
    print_separator("Multi-Hop Transfer Tests")

    config = TransferManagerConfig(
        robot_definitions_path=Path(
            "/Users/dozgulbas/workspace/MADSci/src/madsci_transfer_manager/madsci/transfer_manager/test_robot_definitions.yaml"
        ),
        location_constraints_path=Path(
            "/Users/dozgulbas/workspace/MADSci/src/madsci_transfer_manager/madsci/transfer_manager/test_location_constraints.yaml"
        ),
    )
    manager = TransferManager(config)

    # Test 1: Tower to camera (requires sciclops + pf400)
    print("\nTest 1: Tower to camera station (2 hops)")
    step = Step(
        name="Complex Transfer",
        node="",  # Empty node - let graph determine robots
        action="transfer",
        locations={"source": "tower1", "target": "camera_station"},
        args={},
    )

    result = manager.expand_transfer_step(step)
    print(f"✓ Generated {len(result)} steps:")
    for i, s in enumerate(result, 1):
        print_step_details(s, i)

    # Test 2: Cross-zone transfer using central hub
    print("\nTest 2: Cross-zone transfer via central hub")
    step = Step(
        name="Cross Zone Transfer",
        node="",  # Empty node - let graph determine robots
        action="transfer",
        locations={"source": "location_1", "target": "hidex_nest"},
        args={"custom_param": "test_value"},
    )

    result = manager.expand_transfer_step(step)
    print(f"✓ Generated {len(result)} steps:")
    for i, s in enumerate(result, 1):
        print_step_details(s, i)

    # Test 3: Forced robot selection (should still work if robot can do it)
    print("\nTest 3: Forced robot selection for direct transfer")
    step = Step(
        name="Forced Robot Transfer",
        node="robotarm_1",  # Specify exact robot
        action="transfer",
        locations={"source": "location_1", "target": "location_2"},
        args={"force_test": True},
    )

    result = manager.expand_transfer_step(step)
    print(f"✓ Generated {len(result)} steps:")
    for i, s in enumerate(result, 1):
        print_step_details(s, i)


def test_transfer_options():
    """Test getting multiple transfer options."""
    print_separator("Transfer Options Tests")

    config = TransferManagerConfig(
        robot_definitions_path=Path(
            "/Users/dozgulbas/workspace/MADSci/src/madsci_transfer_manager/madsci/transfer_manager/test_robot_definitions.yaml"
        ),
        location_constraints_path=Path(
            "/Users/dozgulbas/workspace/MADSci/src/madsci_transfer_manager/madsci/transfer_manager/test_location_constraints.yaml"
        ),
    )
    manager = TransferManager(config)

    # Get multiple options for a transfer
    print("\nTransfer options from tower1 to camera_station:")
    options = manager.get_transfer_options("tower1", "camera_station")

    for option in options:
        print(f"  Option {option['option']}: {option['description']}")
        print(f"    Cost: {option['total_cost']:.2f}, Hops: {option['num_hops']}")
        print(f"    Robots: {option['robots_used']}")
        print(
            f"    Path: {' → '.join([hop['source'] for hop in option['path']] + [option['path'][-1]['target']])}"
        )


def test_validation():
    """Test transfer validation and error handling."""
    print_separator("Validation Tests")

    config = TransferManagerConfig(
        robot_definitions_path=Path(
            "/Users/dozgulbas/workspace/MADSci/src/madsci_transfer_manager/madsci/transfer_manager/test_robot_definitions.yaml"
        ),
        location_constraints_path=Path(
            "/Users/dozgulbas/workspace/MADSci/src/madsci_transfer_manager/madsci/transfer_manager/test_location_constraints.yaml"
        ),
    )
    manager = TransferManager(config)

    # Test valid transfer
    print("\nTest 1: Valid transfer validation")
    result = manager.validate_transfer_request("tower1", "camera_station")
    print(f"Valid: {result['valid']}, Reachable: {result['reachable']}")
    if result["errors"]:
        print(f"Errors: {result['errors']}")

    # Test invalid location
    print("\nTest 2: Invalid location validation")
    result = manager.validate_transfer_request("nonexistent", "camera_station")
    print(f"Valid: {result['valid']}, Errors: {result['errors']}")

    # Test unreachable transfer (if any exist)
    print("\nTest 3: Check if all locations are reachable from tower1")
    locations = manager.get_available_locations()
    unreachable = []
    for loc in locations:
        if loc != "tower1" and not manager.transfer_graph.is_reachable("tower1", loc):
            unreachable.append(loc)

    if unreachable:
        print(f"Unreachable locations from tower1: {unreachable}")
    else:
        print("✓ All locations are reachable from tower1")


def test_error_handling():
    """Test error handling for impossible transfers."""
    print_separator("Error Handling Tests")

    config = TransferManagerConfig(
        robot_definitions_path=Path(
            "/Users/dozgulbas/workspace/MADSci/src/madsci_transfer_manager/madsci/transfer_manager/test_robot_definitions.yaml"
        ),
        location_constraints_path=Path(
            "/Users/dozgulbas/workspace/MADSci/src/madsci_transfer_manager/madsci/transfer_manager/test_location_constraints.yaml"
        ),
    )
    manager = TransferManager(config)

    # Test impossible transfer
    print("\nTest: Attempting transfer to nonexistent location")
    try:
        step = Step(
            name="Impossible Transfer",
            node="",  # Let graph handle it
            action="transfer",
            locations={"source": "tower1", "target": "nonexistent_location"},
            args={},
        )

        result = manager.expand_transfer_step(step)
        print("ERROR: Should have failed!")
    except ValueError as e:
        print(f"✓ Correctly caught error: {e}")


def main():
    """Run all tests."""
    print("Transfer Manager Test Suite")
    print(
        "Make sure /Users/dozgulbas/workspace/MADSci/src/madsci_transfer_manager/madsci/transfer_manager/test_robot_definitions.yaml and /Users/dozgulbas/workspace/MADSci/src/madsci_transfer_manager/madsci/transfer_manager/test_location_constraints.yaml are in the current directory"
    )

    try:
        test_basic_functionality()
        test_direct_transfers()
        test_multi_hop_transfers()
        test_transfer_options()
        test_validation()
        test_error_handling()

        print_separator("All Tests Completed Successfully!")

    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
