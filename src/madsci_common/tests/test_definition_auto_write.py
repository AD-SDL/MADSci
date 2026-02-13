"""Tests for Phase G.2 & G.3: Removal of auto-writing behavior.

Verifies that managers no longer auto-write definition files and that
the deprecated methods emit proper warnings.
"""

import warnings

from madsci.common.deprecation import MadsciDeprecationWarning
from madsci.common.manager_base import AbstractManagerBase
from madsci.common.types.manager_types import ManagerDefinition, ManagerSettings


class TestLoadDefinitionNoAutoWrite:
    """Tests that load_definition does not write files."""

    def test_load_definition_no_file_written(self, tmp_path) -> None:
        """load_definition() does not create a file when none exists."""

        # Create a minimal concrete manager
        class TestSettings(ManagerSettings, env_prefix="TEST_NOWRITE_"):
            pass

        class TestDefinition(ManagerDefinition):
            manager_type: str = "lab_manager"

        class TestManager(AbstractManagerBase[TestSettings, TestDefinition]):
            SETTINGS_CLASS = TestSettings
            DEFINITION_CLASS = TestDefinition

        # Point to a non-existent definition file
        settings = TestSettings(manager_definition=str(tmp_path / "nonexistent.yaml"))

        TestManager(settings=settings)

        # The definition file should NOT have been created
        assert not (tmp_path / "nonexistent.yaml").exists()

    def test_load_definition_reads_existing_file(self, tmp_path) -> None:
        """load_definition() reads an existing file with deprecation warning."""

        class TestSettings(ManagerSettings, env_prefix="TEST_READ_"):
            pass

        class TestDefinition(ManagerDefinition):
            manager_type: str = "lab_manager"

        class TestManager(AbstractManagerBase[TestSettings, TestDefinition]):
            SETTINGS_CLASS = TestSettings
            DEFINITION_CLASS = TestDefinition

        # Create a valid definition file
        def_path = tmp_path / "test.manager.yaml"
        test_def = TestDefinition(name="File Manager")
        test_def.to_yaml(def_path)

        settings = TestSettings(manager_definition=str(def_path))

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            manager = TestManager(settings=settings)

            # Should have loaded the name from file
            assert manager.definition.name == "File Manager"

            # Should have emitted a deprecation warning
            dep_warnings = [
                x for x in w if issubclass(x.category, MadsciDeprecationWarning)
            ]
            assert len(dep_warnings) > 0

    def test_load_or_create_definition_emits_warning(self, tmp_path) -> None:
        """The deprecated load_or_create_definition() emits a warning."""

        class TestSettings(ManagerSettings, env_prefix="TEST_DEPRECATED_"):
            pass

        class TestDefinition(ManagerDefinition):
            manager_type: str = "lab_manager"

        class TestManager(AbstractManagerBase[TestSettings, TestDefinition]):
            SETTINGS_CLASS = TestSettings
            DEFINITION_CLASS = TestDefinition

        settings = TestSettings(manager_definition=str(tmp_path / "test.yaml"))

        # Manually call the deprecated method
        manager = TestManager.__new__(TestManager)
        manager._settings = settings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            manager.load_or_create_definition()

            dep_warnings = [
                x
                for x in w
                if issubclass(x.category, MadsciDeprecationWarning)
                and "load_or_create_definition" in str(x.message)
            ]
            assert len(dep_warnings) > 0
