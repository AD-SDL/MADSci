"""
Test runner for MADSci example lab tests.

This script provides a convenient way to run example lab tests
with proper service dependencies and configuration.

Usage: python run_tests.py [options]
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_tests(test_category=None, coverage=False, verbose=False):
    """Run example lab tests with specified options."""
    cmd = ["pytest"]

    # Set test path
    test_dir = Path(__file__).parent
    if test_category:
        test_file = test_dir / f"test_{test_category}.py"
        if test_file.exists():
            cmd.append(str(test_file))
        else:
            sys.stderr.write(f"Test category '{test_category}' not found\n")
            return 1
    else:
        cmd.append(str(test_dir))

    # Add options
    if coverage:
        cmd.extend(["--cov", "--cov-report=term-missing"])

    if verbose:
        cmd.append("-v")

    # Add markers for service requirements
    cmd.extend(["-m", "not requires_services or requires_services"])

    sys.stdout.write(f"Running: {' '.join(cmd)}\n")
    return subprocess.call(cmd, shell=False)  # noqa: S603


def main():
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(description="Run MADSci example lab tests")
    parser.add_argument(
        "--category",
        choices=[
            "lab_setup",
            "resource_templates",
            "workflows",
            "workflow_parameters",
            "error_handling",
            "context_management",
        ],
        help="Test category to run",
    )
    parser.add_argument("--coverage", action="store_true", help="Run with coverage")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    return run_tests(
        test_category=args.category, coverage=args.coverage, verbose=args.verbose
    )


if __name__ == "__main__":
    sys.exit(main())
