#!/usr/bin/env python3
"""
Protocol Template - Liquid Handling Operations

This template demonstrates MADSci protocol structure with
placeholder parameters that will be customized based on
the sample manifest and configuration files.

Template Variables:
- {{PLATE_COUNT}} - Number of plates to process
- {{TRANSFER_VOLUME}} - Volume per transfer in µL
- {{MIX_CYCLES}} - Number of mixing cycles
- {{SAMPLE_COUNT}} - Total number of samples
- {{EXPERIMENT_ID}} - Experiment tracking ID
"""

from typing import Any, Dict, Optional


def setup(
    plate_id: Optional[str] = None,
    experiment_id: str = "{{EXPERIMENT_ID}}",
    **_kwargs: Any,
) -> Dict[str, str]:
    """Initialize protocol with context information."""

    print("🔧 Protocol Setup")
    print(f"   Experiment: {experiment_id}")
    print(f"   Target Plate: {plate_id}")

    # Template configuration (will be customized)
    return {
        "plate_count": "{{PLATE_COUNT}}",
        "transfer_volume": "{{TRANSFER_VOLUME}}",
        "mix_cycles": "{{MIX_CYCLES}}",
        "sample_count": "{{SAMPLE_COUNT}}",
        "experiment_id": experiment_id,
    }


def main(
    config: Optional[Dict[str, str]] = None,
    _context: Optional[Any] = None,
    **kwargs: Any,
) -> Dict[str, str]:
    """Main protocol execution with template parameters."""

    print("🧪 Executing Liquid Handling Protocol")

    if not config:
        config = setup(**kwargs)

    # Display template parameters (will be replaced during customization)
    print("📋 Protocol Parameters:")
    for key, value in config.items():
        print(f"   {key}: {value}")

    # Simulate protocol steps with template logic
    steps = [
        f"Load {config['plate_count']} plates",
        f"Prepare {config['sample_count']} samples",
        f"Transfer {config['transfer_volume']}µL per well",
        f"Execute {config['mix_cycles']} mixing cycles",
        "Generate completion report",
    ]

    print("\\n🔄 Protocol Execution Steps:")
    for i, step in enumerate(steps, 1):
        print(f"   Step {i}: {step}")

    # Return execution results
    transfer_vol = float(config["transfer_volume"])
    sample_count = float(config["sample_count"])
    total_vol = f"{transfer_vol * sample_count}µL"

    return {
        "status": "completed",
        "steps_executed": len(steps),
        "samples_processed": config["sample_count"],
        "total_volume": total_vol,
        "experiment_id": config["experiment_id"],
    }


def cleanup(config: Optional[Dict[str, str]] = None, **_kwargs: Any) -> None:
    """Protocol cleanup with context awareness."""

    print("🧹 Protocol Cleanup")

    if config and config.get("experiment_id"):
        print(f"   Cleaning up experiment: {config['experiment_id']}")

    cleanup_steps = [
        "Eject tips and plates",
        "Wash liquid handler components",
        "Save protocol execution log",
        "Update resource tracking",
    ]

    for step in cleanup_steps:
        print(f"   • {step}")

    print("✅ Cleanup completed")


if __name__ == "__main__":
    # Template execution for testing
    config = setup(plate_id="TEST_PLATE_001")
    results = main(config=config)
    cleanup(config=config)
    print(f"\\n✅ Template protocol test completed: {results}")
