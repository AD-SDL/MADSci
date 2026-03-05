"""Export OpenAPI JSON specs from all MADSci manager services.

Usage:
    python scripts/export_openapi.py          # Export specs to docs/api-specs/
    python scripts/export_openapi.py --check  # Check committed specs are up-to-date
"""

import argparse
import importlib
import json
import sys
from pathlib import Path

# Manager registry: (display_name, module_path, class_name, output_filename)
MANAGERS = [
    ("Lab Manager", "madsci.squid.lab_server", "LabManager", "lab-manager.json"),
    (
        "Event Manager",
        "madsci.event_manager.event_server",
        "EventManager",
        "event-manager.json",
    ),
    (
        "Experiment Manager",
        "madsci.experiment_manager.experiment_server",
        "ExperimentManager",
        "experiment-manager.json",
    ),
    (
        "Resource Manager",
        "madsci.resource_manager.resource_server",
        "ResourceManager",
        "resource-manager.json",
    ),
    (
        "Data Manager",
        "madsci.data_manager.data_server",
        "DataManager",
        "data-manager.json",
    ),
    (
        "Workcell Manager",
        "madsci.workcell_manager.workcell_server",
        "WorkcellManager",
        "workcell-manager.json",
    ),
    (
        "Location Manager",
        "madsci.location_manager.location_server",
        "LocationManager",
        "location-manager.json",
    ),
]

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "api-specs"


def export_spec(display_name: str, module_path: str, class_name: str) -> dict | None:
    """Import a manager, create its FastAPI app, and return the OpenAPI schema."""
    try:
        module = importlib.import_module(module_path)
        manager_cls = getattr(module, class_name)
        manager = manager_cls()
        app = manager.create_server()
        return app.openapi()
    except Exception as exc:
        print(f"  WARNING: Failed to export {display_name}: {exc}", file=sys.stderr)
        return None


def export_all() -> dict[str, dict]:
    """Export OpenAPI specs for all managers. Returns {filename: spec_dict}."""
    results = {}
    for display_name, module_path, class_name, output_filename in MANAGERS:
        print(f"  Exporting {display_name}...")
        spec = export_spec(display_name, module_path, class_name)
        if spec is not None:
            results[output_filename] = spec
    return results


def write_specs(specs: dict[str, dict]) -> None:
    """Write OpenAPI spec dicts to JSON files in the output directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, spec in specs.items():
        output_path = OUTPUT_DIR / filename
        output_path.write_text(json.dumps(spec, indent=2) + "\n")
        print(f"  Wrote {output_path}")


def check_specs(specs: dict[str, dict]) -> bool:
    """Compare generated specs against committed specs. Returns True if up-to-date."""
    all_match = True
    for filename, spec in specs.items():
        committed_path = OUTPUT_DIR / filename
        generated_json = json.dumps(spec, indent=2) + "\n"
        if not committed_path.exists():
            print(f"  MISSING: {committed_path}")
            all_match = False
        else:
            committed_json = committed_path.read_text()
            if committed_json != generated_json:
                print(f"  DRIFT: {committed_path} differs from generated spec")
                all_match = False
            else:
                print(f"  OK: {committed_path}")
    return all_match


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export OpenAPI specs from MADSci managers"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check committed specs match generated specs (exit non-zero on drift)",
    )
    args = parser.parse_args()

    print("Exporting OpenAPI specs from MADSci managers...")
    specs = export_all()

    if not specs:
        print("ERROR: No specs were exported successfully.", file=sys.stderr)
        sys.exit(1)

    if args.check:
        print("\nChecking committed specs...")
        if check_specs(specs):
            print("\nAll specs are up-to-date.")
        else:
            print(
                "\nSpecs are out of date! Run 'python scripts/export_openapi.py' to update.",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        print("\nWriting specs...")
        write_specs(specs)
        print(f"\nExported {len(specs)}/{len(MANAGERS)} specs to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
