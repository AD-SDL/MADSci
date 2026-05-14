"""Tests for prefixed alias YAML loading and serialization.

Validates the dual-layer configuration approach where:
- settings.yaml uses prefixed keys (e.g., event_server_url)
- Code uses unprefixed field names (e.g., server_url)
- .env uses prefixed env vars (e.g., EVENT_SERVER_URL)
"""

import textwrap
from pathlib import Path

import pytest
import yaml
from madsci.common.types.backup_types import DocumentDBBackupSettings
from madsci.common.types.base_types import (
    REDACTED_PLACEHOLDER,
    prefixed_alias_generator,
)
from madsci.common.types.datapoint_types import DataManagerSettings
from madsci.common.types.event_types import EventManagerSettings
from madsci.common.types.experiment_types import ExperimentManagerSettings
from madsci.common.types.lab_types import LabManagerSettings
from madsci.common.types.location_types import LocationManagerSettings
from madsci.common.types.resource_types.definitions import ResourceManagerSettings
from madsci.common.types.workcell_types import WorkcellManagerSettings
from pydantic import AliasGenerator


class TestPrefixedAliasGenerator:
    """Tests for the prefixed_alias_generator helper function."""

    def test_returns_alias_generator(self) -> None:
        gen = prefixed_alias_generator("event")
        assert isinstance(gen, AliasGenerator)

    def test_no_validation_alias(self) -> None:
        """prefixed_alias_generator must NOT set validation_alias.

        Setting validation_alias overrides pydantic-settings' env_prefix,
        which causes .env files to lose per-manager prefixes.
        """
        gen = prefixed_alias_generator("event")
        assert gen.validation_alias is None

    def test_serialization_alias_produces_prefixed_name(self) -> None:
        gen = prefixed_alias_generator("event")
        result = gen.serialization_alias("server_url")
        assert result == "event_server_url"

    def test_trailing_underscore_stripped(self) -> None:
        gen = prefixed_alias_generator("EVENT_")
        result = gen.serialization_alias("server_url")
        assert result == "event_server_url"

    def test_case_normalized(self) -> None:
        gen = prefixed_alias_generator("EVENT")
        result = gen.serialization_alias("server_url")
        assert result == "event_server_url"


class TestPrefixedModelValidator:
    """Tests for the prefixed_model_validator helper."""

    def test_strips_prefixed_keys(self) -> None:
        """Prefixed keys in kwargs should be mapped to unprefixed field names."""
        settings = EventManagerSettings(event_server_url="http://test:9999")
        assert str(settings.server_url) == "http://test:9999/"

    def test_unprefixed_keys_still_work(self) -> None:
        settings = EventManagerSettings(server_url="http://test:9999")
        assert str(settings.server_url) == "http://test:9999/"

    def test_unprefixed_takes_precedence(self) -> None:
        """When both prefixed and unprefixed are present, unprefixed wins."""
        settings = EventManagerSettings(
            server_url="http://unprefixed:8001",
            event_server_url="http://prefixed:8001",
        )
        assert str(settings.server_url) == "http://unprefixed:8001/"

    def test_ignores_non_field_prefixed_keys(self) -> None:
        """Prefixed keys that don't correspond to fields are left alone."""
        # event_nonexistent_field should be ignored (no error, no mapping)
        settings = EventManagerSettings(event_nonexistent_field="ignored")
        assert settings.server_url  # just verify no crash


class TestEnvPrefixPreserved:
    """Verify that env_prefix is NOT overridden by the alias system.

    This is the critical regression test for the bug where validation_alias
    in the AliasGenerator caused pydantic-settings to lose env_prefix.
    """

    @pytest.mark.parametrize(
        "settings_cls,prefix,field",
        [
            (EventManagerSettings, "EVENT_", "server_url"),
            (WorkcellManagerSettings, "WORKCELL_", "server_url"),
            (ResourceManagerSettings, "RESOURCE_", "server_url"),
            (DataManagerSettings, "DATA_", "server_url"),
            (ExperimentManagerSettings, "EXPERIMENT_", "server_url"),
            (LocationManagerSettings, "LOCATION_", "server_url"),
            (LabManagerSettings, "LAB_", "server_url"),
        ],
    )
    def test_env_prefix_applied(
        self,
        settings_cls: type,
        prefix: str,
        field: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Env vars with the manager prefix should be picked up correctly."""
        env_var = f"{prefix}{field.upper()}"
        monkeypatch.setenv(env_var, "http://envtest:9999")
        settings = settings_cls()
        assert "envtest:9999" in str(getattr(settings, field))

    def test_unprefixed_env_var_does_not_leak(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An unprefixed SERVER_URL env var should NOT affect EventManagerSettings."""
        monkeypatch.setenv("SERVER_URL", "http://leaked:9999")
        settings = EventManagerSettings()
        # Should use default, not the leaked env var
        assert "leaked" not in str(settings.server_url)


class TestEventManagerAliases:
    """Tests for EventManagerSettings alias behavior."""

    def test_by_alias_false_uses_field_names(self) -> None:
        settings = EventManagerSettings()
        data = settings.model_dump(mode="json")
        assert "server_url" in data
        assert "event_server_url" not in data

    def test_by_alias_true_uses_prefixed_names(self) -> None:
        settings = EventManagerSettings()
        data = settings.model_dump(mode="json", by_alias=True)
        assert "event_server_url" in data
        assert "event_manager_id" in data
        assert "event_database_name" in data
        # field name should not appear
        assert "server_url" not in data

    def test_explicit_validation_alias_preserved(self) -> None:
        """Fields with explicit validation_alias should not be broken by alias_generator."""
        # document_db_url has validation_alias=AliasChoices("document_db_url", "mongo_db_url", "EVENT_DB_URL", "db_url")
        settings = EventManagerSettings(EVENT_DB_URL="mongodb://custom:27017")
        assert "custom:27017" in str(settings.document_db_url)

    def test_env_var_still_works(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EVENT_SERVER_URL", "http://envtest:8001")
        settings = EventManagerSettings()
        assert str(settings.server_url) == "http://envtest:8001/"

    def test_model_dump_safe_by_alias_redacts_secrets(self) -> None:
        settings = EventManagerSettings()
        data = settings.model_dump_safe(by_alias=True)
        assert data["event_document_db_url"] == REDACTED_PLACEHOLDER
        # Non-secret fields should not be redacted
        assert data["event_server_url"] != REDACTED_PLACEHOLDER

    def test_model_dump_safe_without_alias_redacts_secrets(self) -> None:
        settings = EventManagerSettings()
        data = settings.model_dump_safe()
        assert data["document_db_url"] == REDACTED_PLACEHOLDER


class TestWorkcellManagerAliases:
    """Tests for WorkcellManagerSettings alias behavior."""

    def test_by_alias_true_uses_prefixed_names(self) -> None:
        settings = WorkcellManagerSettings()
        data = settings.model_dump(mode="json", by_alias=True)
        assert "workcell_server_url" in data
        assert "workcell_cache_host" in data

    def test_explicit_alias_field_preserved(self) -> None:
        """workcells_directory has alias='workcells_directory' which should take precedence."""
        settings = WorkcellManagerSettings()
        data = settings.model_dump(mode="json", by_alias=True)
        # Explicit alias should win over generator
        assert "workcells_directory" in data
        assert "workcell_workcells_directory" not in data

    def test_explicit_validation_alias_preserved(self) -> None:
        """manager_name has an explicit value that can be set via settings."""
        settings = WorkcellManagerSettings(manager_name="custom_workcell")
        assert settings.manager_name == "custom_workcell"

    def test_model_dump_safe_by_alias_redacts_secrets(self) -> None:
        settings = WorkcellManagerSettings()
        data = settings.model_dump_safe(by_alias=True)
        assert data["workcell_document_db_url"] == REDACTED_PLACEHOLDER
        assert data["workcell_cache_password"] == REDACTED_PLACEHOLDER


class TestResourceManagerAliases:
    """Tests for ResourceManagerSettings alias behavior."""

    def test_by_alias_true_uses_prefixed_names(self) -> None:
        settings = ResourceManagerSettings()
        data = settings.model_dump(mode="json", by_alias=True)
        assert "resource_server_url" in data
        assert "resource_db_url" in data

    def test_model_dump_safe_by_alias_redacts_db_url(self) -> None:
        settings = ResourceManagerSettings()
        data = settings.model_dump_safe(by_alias=True)
        assert data["resource_db_url"] == REDACTED_PLACEHOLDER


class TestDataManagerAliases:
    """Tests for DataManagerSettings alias behavior."""

    def test_by_alias_true_uses_prefixed_names(self) -> None:
        settings = DataManagerSettings()
        data = settings.model_dump(mode="json", by_alias=True)
        assert "data_server_url" in data
        assert "data_database_name" in data

    def test_explicit_validation_alias_preserved(self) -> None:
        settings = DataManagerSettings(DATA_DB_URL="mongodb://custom:27017")
        assert "custom:27017" in str(settings.document_db_url)


class TestExperimentManagerAliases:
    """Tests for ExperimentManagerSettings alias behavior."""

    def test_by_alias_true_uses_prefixed_names(self) -> None:
        settings = ExperimentManagerSettings()
        data = settings.model_dump(mode="json", by_alias=True)
        assert "experiment_server_url" in data

    def test_explicit_validation_alias_preserved(self) -> None:
        settings = ExperimentManagerSettings(EXPERIMENT_DB_URL="mongodb://custom:27017")
        assert "custom:27017" in str(settings.document_db_url)


class TestLocationManagerAliases:
    """Tests for LocationManagerSettings alias behavior."""

    def test_by_alias_true_uses_prefixed_names(self) -> None:
        settings = LocationManagerSettings()
        data = settings.model_dump(mode="json", by_alias=True)
        assert "location_server_url" in data
        assert "location_cache_host" in data

    def test_model_dump_safe_by_alias_redacts_secrets(self) -> None:
        settings = LocationManagerSettings(cache_password="secret123")  # noqa: S106
        data = settings.model_dump_safe(by_alias=True)
        assert data["location_cache_password"] == REDACTED_PLACEHOLDER


class TestLabManagerAliases:
    """Tests for LabManagerSettings alias behavior."""

    def test_by_alias_true_uses_prefixed_names(self) -> None:
        settings = LabManagerSettings()
        data = settings.model_dump(mode="json", by_alias=True)
        assert "lab_server_url" in data
        assert "lab_manager_id" in data


class TestSharedYAMLLoading:
    """Tests for loading settings from a shared YAML file with prefixed keys."""

    def test_load_from_prefixed_yaml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A shared YAML file with prefixed keys should load correctly."""
        yaml_content = textwrap.dedent("""\
            event_server_url: http://custom:8001/
            event_database_name: custom_events
        """)
        yaml_file = tmp_path / "settings.yaml"
        yaml_file.write_text(yaml_content)
        monkeypatch.chdir(tmp_path)

        settings = EventManagerSettings()
        assert str(settings.server_url) == "http://custom:8001/"
        assert settings.database_name == "custom_events"

    def test_load_from_unprefixed_yaml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Per-manager YAML with unprefixed keys should still work."""
        yaml_content = textwrap.dedent("""\
            server_url: http://custom:8001/
            database_name: custom_events
        """)
        yaml_file = tmp_path / "events.settings.yaml"
        yaml_file.write_text(yaml_content)
        monkeypatch.chdir(tmp_path)

        settings = EventManagerSettings()
        assert str(settings.server_url) == "http://custom:8001/"
        assert settings.database_name == "custom_events"

    def test_round_trip_yaml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Settings dumped with by_alias=True (including secrets) should be loadable from YAML."""
        original = EventManagerSettings()
        # Use include_secrets=True for a valid round-trip (redacted placeholders aren't valid URLs)
        data = original.model_dump_safe(include_secrets=True, by_alias=True)

        yaml_file = tmp_path / "settings.yaml"
        yaml_file.write_text(yaml.dump(data, sort_keys=False))
        monkeypatch.chdir(tmp_path)

        # Should load back with prefixed keys
        loaded = EventManagerSettings()
        assert str(loaded.server_url) == str(original.server_url)
        assert loaded.database_name == original.database_name

    def test_env_vars_override_yaml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Env vars should override YAML values (higher precedence)."""
        yaml_content = textwrap.dedent("""\
            event_server_url: http://yaml:8001/
        """)
        yaml_file = tmp_path / "settings.yaml"
        yaml_file.write_text(yaml_content)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("EVENT_SERVER_URL", "http://envvar:8001")

        settings = EventManagerSettings()
        # Env var should win
        assert str(settings.server_url) == "http://envvar:8001/"


class TestAllManagersPrefixedDump:
    """Verify that all manager settings produce prefixed keys with by_alias=True."""

    @pytest.mark.parametrize(
        "settings_cls,prefix",
        [
            (EventManagerSettings, "event_"),
            (WorkcellManagerSettings, "workcell_"),
            (ResourceManagerSettings, "resource_"),
            (DataManagerSettings, "data_"),
            (ExperimentManagerSettings, "experiment_"),
            (LocationManagerSettings, "location_"),
            (LabManagerSettings, "lab_"),
        ],
    )
    def test_all_keys_prefixed(self, settings_cls: type, prefix: str) -> None:
        """All keys in by_alias dump should start with the manager prefix."""
        settings = settings_cls()
        data = settings.model_dump(mode="json", by_alias=True)

        # Check that the server_url key is prefixed
        assert f"{prefix}server_url" in data

        # Most keys should be prefixed; fields with explicit alias may differ
        # Just check that the primary field name pattern works
        for key in data:
            if key.startswith(prefix) or key == "workcells_directory":
                continue
            # Unexpected unprefixed key
            pytest.fail(
                f"Unexpected unprefixed key '{key}' in {settings_cls.__name__} dump"
            )


class TestBackwardCompatMongoDbUrl:
    """Tests that the old 'mongo_db_url' parameter name still works for all settings
    classes that were renamed to 'document_db_url' during the FOSS migration."""

    @pytest.mark.parametrize(
        "settings_cls",
        [
            EventManagerSettings,
            ExperimentManagerSettings,
            WorkcellManagerSettings,
        ],
    )
    def test_old_mongo_db_url_kwarg_accepted(self, settings_cls: type) -> None:
        """The old 'mongo_db_url' keyword argument should populate document_db_url."""
        settings = settings_cls(mongo_db_url="mongodb://oldhost:27017")
        assert "oldhost:27017" in str(settings.document_db_url)

    def test_data_manager_old_mongo_db_url_kwarg_accepted(self) -> None:
        """DataManagerSettings also accepts mongo_db_url via its AliasChoices."""
        settings = DataManagerSettings(mongo_db_url="mongodb://oldhost:27017")
        assert "oldhost:27017" in str(settings.document_db_url)

    def test_document_db_backup_old_mongo_db_url_kwarg_accepted(self) -> None:
        """DocumentDBBackupSettings accepts the old mongo_db_url kwarg."""
        settings = DocumentDBBackupSettings(mongo_db_url="mongodb://oldhost:27017")
        assert "oldhost:27017" in str(settings.document_db_url)

    @pytest.mark.parametrize(
        "settings_cls,env_var",
        [
            (EventManagerSettings, "EVENT_DB_URL"),
            (ExperimentManagerSettings, "EXPERIMENT_DB_URL"),
            (WorkcellManagerSettings, "WORKCELL_MONGO_URL"),
        ],
    )
    def test_old_env_var_alias_accepted(
        self,
        settings_cls: type,
        env_var: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Old env var aliases in validation_alias AliasChoices should still work."""
        monkeypatch.setenv(env_var, "mongodb://envold:27017")
        settings = settings_cls()
        assert "envold:27017" in str(settings.document_db_url)
