"""Tests for EventType coverage and logging pattern consistency.

This module verifies that:
1. All EventType values are documented
2. EventType naming conventions are consistent
3. EventType categories are complete for each domain
"""

import re
from pathlib import Path
from typing import Set

import pytest
from madsci.common.types.event_types import EVENT_TYPE_DESCRIPTIONS, EventType


class TestEventTypeCoverage:
    """Test that EventTypes are used correctly throughout the codebase."""

    def test_all_event_types_documented(self) -> None:
        """Test that all EventType values have descriptions."""
        missing = [et for et in EventType if et not in EVENT_TYPE_DESCRIPTIONS]
        assert not missing, f"Missing EventType descriptions: {missing}"

    def test_event_type_descriptions_not_empty(self) -> None:
        """Test that no EventType description is empty."""
        empty = [et for et, desc in EVENT_TYPE_DESCRIPTIONS.items() if not desc.strip()]
        assert not empty, f"Empty EventType descriptions: {empty}"

    def test_event_type_values_are_lowercase_snake_case(self) -> None:
        """Test that all EventType values follow lowercase_snake_case convention."""
        pattern = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")
        invalid = [(et, et.value) for et in EventType if not pattern.match(et.value)]
        assert not invalid, f"EventType values not in snake_case: {invalid}"

    def test_event_type_names_match_values(self) -> None:
        """Test that EventType enum names match their values (UPPER_CASE == lower_case)."""
        mismatched = [
            (et.name, et.value)
            for et in EventType
            if et.name.lower() != et.value.replace("_", "_")
        ]
        assert not mismatched, f"EventType names don't match values: {mismatched}"


class TestEventTypeDomainCoverage:
    """Test that all domain categories have complete EventType coverage."""

    def test_resource_domain_has_complete_lifecycle(self) -> None:
        """Test that resource domain has CREATE, UPDATE, DELETE events."""
        resource_types = {et for et in EventType if et.name.startswith("RESOURCE_")}
        required = {"RESOURCE_CREATE", "RESOURCE_UPDATE", "RESOURCE_DELETE"}
        missing = required - {et.name for et in resource_types}
        assert not missing, f"Missing resource lifecycle EventTypes: {missing}"

    def test_location_domain_has_complete_lifecycle(self) -> None:
        """Test that location domain has CREATE, UPDATE, DELETE events."""
        location_types = {et for et in EventType if et.name.startswith("LOCATION_")}
        required = {"LOCATION_CREATE", "LOCATION_UPDATE", "LOCATION_DELETE"}
        missing = required - {et.name for et in location_types}
        assert not missing, f"Missing location lifecycle EventTypes: {missing}"

    def test_workflow_domain_has_complete_lifecycle(self) -> None:
        """Test that workflow domain has CREATE, START, COMPLETE, ABORT events."""
        workflow_types = {
            et
            for et in EventType
            if et.name.startswith("WORKFLOW_")
            and not et.name.startswith("WORKFLOW_STEP_")
        }
        required = {
            "WORKFLOW_CREATE",
            "WORKFLOW_START",
            "WORKFLOW_COMPLETE",
            "WORKFLOW_ABORT",
        }
        missing = required - {et.name for et in workflow_types}
        assert not missing, f"Missing workflow lifecycle EventTypes: {missing}"

    def test_workflow_step_domain_has_complete_lifecycle(self) -> None:
        """Test that workflow step domain has START, COMPLETE, FAILED events."""
        step_types = {et for et in EventType if et.name.startswith("WORKFLOW_STEP_")}
        required = {
            "WORKFLOW_STEP_START",
            "WORKFLOW_STEP_COMPLETE",
            "WORKFLOW_STEP_FAILED",
        }
        missing = required - {et.name for et in step_types}
        assert not missing, f"Missing workflow step EventTypes: {missing}"

    def test_experiment_domain_has_complete_lifecycle(self) -> None:
        """Test that experiment domain has full lifecycle events."""
        experiment_types = {et for et in EventType if et.name.startswith("EXPERIMENT_")}
        required = {
            "EXPERIMENT_CREATE",
            "EXPERIMENT_START",
            "EXPERIMENT_COMPLETE",
            "EXPERIMENT_FAILED",
            "EXPERIMENT_CANCELLED",
        }
        missing = required - {et.name for et in experiment_types}
        assert not missing, f"Missing experiment lifecycle EventTypes: {missing}"

    def test_manager_domain_has_complete_lifecycle(self) -> None:
        """Test that manager domain has START, STOP, ERROR events."""
        manager_types = {et for et in EventType if et.name.startswith("MANAGER_")}
        required = {"MANAGER_START", "MANAGER_STOP", "MANAGER_ERROR"}
        missing = required - {et.name for et in manager_types}
        assert not missing, f"Missing manager lifecycle EventTypes: {missing}"

    def test_action_domain_has_complete_lifecycle(self) -> None:
        """Test that action domain has START, COMPLETE, FAILED events."""
        action_types = {
            et
            for et in EventType
            if et.name.startswith("ACTION_") and et.name != "ACTION_STATUS_CHANGE"
        }
        required = {"ACTION_START", "ACTION_COMPLETE", "ACTION_FAILED"}
        missing = required - {et.name for et in action_types}
        assert not missing, f"Missing action lifecycle EventTypes: {missing}"

    def test_node_domain_has_complete_lifecycle(self) -> None:
        """Test that node domain has CREATE, START, STOP, ERROR events."""
        node_types = {et for et in EventType if et.name.startswith("NODE_")}
        required = {"NODE_CREATE", "NODE_START", "NODE_STOP", "NODE_ERROR"}
        missing = required - {et.name for et in node_types}
        assert not missing, f"Missing node lifecycle EventTypes: {missing}"

    def test_data_domain_has_core_operations(self) -> None:
        """Test that data domain has STORE, QUERY operations."""
        data_types = {et for et in EventType if et.name.startswith("DATA_")}
        required = {"DATA_STORE", "DATA_QUERY"}
        missing = required - {et.name for et in data_types}
        assert not missing, f"Missing data operation EventTypes: {missing}"

    def test_backup_domain_has_core_operations(self) -> None:
        """Test that backup domain has CREATE, RESTORE operations."""
        backup_types = {et for et in EventType if et.name.startswith("BACKUP_")}
        required = {"BACKUP_CREATE", "BACKUP_RESTORE"}
        missing = required - {et.name for et in backup_types}
        assert not missing, f"Missing backup operation EventTypes: {missing}"


class TestEventTypeUsagePatterns:
    """Test EventType usage patterns in the codebase.

    These tests scan the codebase for EventType usage and verify patterns.
    """

    @staticmethod
    def _get_python_files(directory: Path) -> list[Path]:
        """Get all Python files in a directory recursively."""
        return list(directory.rglob("*.py"))

    @staticmethod
    def _extract_event_types_from_file(file_path: Path) -> Set[str]:
        """Extract EventType references from a Python file."""
        event_types: Set[str] = set()
        try:
            content = file_path.read_text()
            # Match patterns like EventType.WORKFLOW_START or event_type=EventType.X
            pattern = re.compile(r"EventType\.([A-Z_]+)")
            event_types = set(pattern.findall(content))
        except (OSError, UnicodeDecodeError):
            pass
        return event_types

    def test_event_types_used_in_managers(self) -> None:
        """Test that managers use EventTypes (not just generic LOG_*)."""
        manager_dirs = [
            Path("src/madsci_event_manager/madsci/event_manager"),
            Path("src/madsci_workcell_manager/madsci/workcell_manager"),
            Path("src/madsci_resource_manager/madsci/resource_manager"),
            Path("src/madsci_location_manager/madsci/location_manager"),
            Path("src/madsci_data_manager/madsci/data_manager"),
            Path("src/madsci_experiment_manager/madsci/experiment_manager"),
        ]

        all_event_types: Set[str] = set()
        for manager_dir in manager_dirs:
            if manager_dir.exists():
                for py_file in self._get_python_files(manager_dir):
                    all_event_types.update(self._extract_event_types_from_file(py_file))

        # Should have more than just LOG_* types
        non_log_types = {et for et in all_event_types if not et.startswith("LOG")}
        assert len(non_log_types) > 0, (
            "Managers should use domain-specific EventTypes, not just LOG_*"
        )

    def test_event_types_are_valid_enum_members(self) -> None:
        """Test that all EventType references in code are valid enum members."""
        src_dir = Path("src")
        if not src_dir.exists():
            pytest.skip("Source directory not found")

        invalid_references: list[tuple[Path, str]] = []
        valid_names = {et.name for et in EventType}

        for py_file in self._get_python_files(src_dir):
            # Skip test files for this check
            if "/tests/" in str(py_file):
                continue
            event_types = self._extract_event_types_from_file(py_file)
            for et_name in event_types:
                if et_name not in valid_names:
                    invalid_references.append((py_file, et_name))

        assert not invalid_references, (
            f"Invalid EventType references: {invalid_references[:10]}"
        )
