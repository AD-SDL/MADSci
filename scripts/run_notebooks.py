"""
Automated Jupyter Notebook Execution Script for MADSci

This script provides different methods for executing MADSci setup notebooks
automatically, with proper error handling and reporting.
"""

import argparse
import json
import subprocess
from pathlib import Path
from typing import Dict, Optional

from rich import print


def run_notebook_with_papermill(
    notebook_path: Path,
    output_path: Optional[Path] = None,
    parameters: Optional[Dict] = None,
) -> bool:
    """
    Execute notebook using papermill with optional parameterization.

    Args:
        notebook_path: Path to input notebook
        output_path: Path for output notebook (optional)
        parameters: Dictionary of parameters to inject

    Returns:
        True if successful, False otherwise
    """
    if output_path is None:
        output_path = notebook_path.parent / f"executed_{notebook_path.name}"

    cmd = ["papermill", str(notebook_path), str(output_path)]

    # Add parameters if provided
    if parameters:
        for key, value in parameters.items():
            cmd.extend(["-p", key, str(value)])

    print(f"📄 Executing {notebook_path.name} with papermill...")

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)  # noqa: S603 (expected)
        print(f"✅ Success: {notebook_path.name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {notebook_path.name}")
        print(f"   Error: {e.stderr}")
        return False


def run_setup_sequence() -> None:
    """
    Run the MADSci setup notebooks in sequence using papermill.
    """
    setup_dir = Path("example_lab/setup")

    if not setup_dir.exists():
        print(f"❌ Setup directory not found: {setup_dir}")
        return

    # Define execution order
    notebooks = [
        "01_service_orchestration.ipynb",
        "02_resource_templates.ipynb",
        "03_initial_resources.ipynb",
        "04_validation.ipynb",
        "05_comprehensive_lab_setup.ipynb",
    ]

    print("🚀 Running MADSci setup sequence with papermill")
    print("=" * 50)

    successful = []
    failed = []

    for notebook_name in notebooks:
        notebook_path = setup_dir / notebook_name

        if not notebook_path.exists():
            print(f"⚠️  Notebook not found: {notebook_name}")
            continue

        success = run_notebook_with_papermill(notebook_path)

        if success:
            successful.append(notebook_name)
        else:
            failed.append(notebook_name)

        print()  # Empty line between notebooks

    # Summary
    print("📊 Execution Summary")
    print("=" * 20)
    print(f"✅ Successful: {len(successful)}")
    for notebook in successful:
        print(f"   • {notebook}")

    if failed:
        print(f"❌ Failed: {len(failed)}")
        for notebook in failed:
            print(f"   • {notebook}")


def main() -> None:
    """Main execution function with CLI interface."""
    parser = argparse.ArgumentParser(
        description="Execute MADSci Jupyter notebooks automatically"
    )
    parser.add_argument(
        "--notebook", type=Path, help="Execute single notebook instead of full sequence"
    )
    parser.add_argument(
        "--parameters",
        help='JSON string of parameters for papermill (e.g., \'{"param1": "value1"}\')',
    )

    args = parser.parse_args()

    if args.notebook:
        # Execute single notebook
        parameters = {}
        if args.parameters:
            parameters = json.loads(args.parameters)
        run_notebook_with_papermill(args.notebook, parameters=parameters)
    else:
        # Execute full sequence
        run_setup_sequence()


if __name__ == "__main__":
    main()
