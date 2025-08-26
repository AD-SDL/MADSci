#!/usr/bin/env python3
"""Simple test script for Transfer Manager with unified config."""

from pathlib import Path
from madsci.common.types.step_types import Step
from madsci.transfer_manager.transfer_manager import TransferManager, TransferManagerConfig


def get_config_path(filename):
    """Get the full path to a config file in the same directory as this script."""
    script_dir = Path(__file__).parent
    return script_dir / filename


def create_test_config():
    """Create a config with path to the unified config file."""
    return TransferManagerConfig(
        config_file_path=get_config_path("transfer_config.yaml")
    )


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
    print("\n" + "="*60)
    print("  Basic Transfer Manager Tests")
    print("="*60)

    config = create_test_config()
    manager = TransferManager(config)
    print("Transfer Manager initialized successfully")

    robots = manager.get_available_robots()
    locations = manager.get_available_locations()

    print(f"Available robots: {robots}")
    print(f"Available locations: {locations}")
    print(f"Total locations in graph: {len(manager.transfer_graph.locations)}")


def test_direct_transfers():
    """Test simple direct transfers."""
    print("\n" + "="*60)
    print("  Direct Transfer Tests")
    print("="*60)

    config = create_test_config()
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
    print(f"Generated {len(result)} steps:")
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
    print(f"Generated {len(result)} steps:")
    for i, s in enumerate(result, 1):
        print_step_details(s, i)


def test_multi_hop_transfer():
    """Test the main multi-hop transfer functionality."""
    print("\n" + "="*60)
    print("  Multi-Hop Transfer Test")
    print("="*60)
    
    config = create_test_config()
    manager = TransferManager(config)
    
    print("Creating Step...")
    step = Step(
        name="Multi-hop Test",
        node="",  # Empty = use graph pathfinding
        action="transfer",
        locations={"source": "tower1", "target": "camera_station"},
        args={}
    )
    print(f"Step created: node='{step.node}', action='{step.action}'")
    
    print("About to call expand_transfer_step...")
    try:
        result = manager.expand_transfer_step(step)
        print(f"SUCCESS: Generated {len(result)} steps")
        for i, s in enumerate(result, 1):
            print_step_details(s, i)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


def main():
    print("=== MADSci Transfer Manager Simple Test ===")
    print(f"Running from: {Path(__file__).parent}")
    print(f"Config file: {get_config_path('transfer_config.yaml')}")
    
    try:
        test_basic_functionality()
        test_direct_transfers()
        test_multi_hop_transfer()
        
        print("\n" + "="*60)
        print("  All Tests Completed Successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()