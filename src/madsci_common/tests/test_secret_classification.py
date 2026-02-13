"""Tests for Phase G.1: Secret field classification system.

Tests model_dump_safe(), _is_secret_field(), to_yaml() with secret redaction,
and secret annotations on settings classes.
"""

from typing import Optional

from madsci.common.types.base_types import (
    REDACTED_PLACEHOLDER,
    MadsciBaseModel,
    MadsciBaseSettings,
    _is_secret_field,
)
from madsci.common.types.datapoint_types import (
    DataManagerSettings,
    ObjectStorageSettings,
)
from madsci.common.types.event_types import EmailAlertsConfig, EventManagerSettings
from madsci.common.types.experiment_types import ExperimentManagerSettings
from madsci.common.types.location_types import LocationManagerSettings
from madsci.common.types.resource_types.definitions import ResourceManagerSettings
from madsci.common.types.workcell_types import WorkcellManagerSettings
from pydantic import Field

# --- Test Models ---


class ModelWithSecrets(MadsciBaseModel):
    """Test model with secret fields."""

    name: str = Field(default="test")
    password: str = Field(default="secret123", json_schema_extra={"secret": True})
    api_key: str = Field(default="key123", json_schema_extra={"secret": True})
    normal_field: str = Field(default="visible")


class NestedModel(MadsciBaseModel):
    """Nested model with secrets."""

    smtp_password: Optional[str] = Field(
        default="smtp_pass", json_schema_extra={"secret": True}
    )
    smtp_server: str = Field(default="mail.example.com")


class ParentModel(MadsciBaseModel):
    """Parent model with nested model containing secrets."""

    name: str = Field(default="parent")
    email_config: Optional[NestedModel] = Field(default_factory=NestedModel)


class SettingsWithSecrets(
    MadsciBaseSettings,
    env_prefix="TEST_SECRET_",
):
    """Test settings with secret fields."""

    host: str = Field(default="localhost")
    db_url: str = Field(
        default="postgres://user:pass@localhost/db",
        json_schema_extra={"secret": True},
    )
    redis_password: Optional[str] = Field(
        default="redis_pass",
        json_schema_extra={"secret": True},
    )


class ModelNoSecrets(MadsciBaseModel):
    """Model with no secret fields."""

    name: str = Field(default="test")
    count: int = Field(default=42)


# --- Tests for _is_secret_field ---


class TestIsSecretField:
    """Tests for the _is_secret_field helper."""

    def test_secret_via_json_schema_extra(self) -> None:
        """Fields with json_schema_extra={"secret": True} are detected."""
        field_info = ModelWithSecrets.model_fields["password"]
        assert _is_secret_field(field_info) is True

    def test_non_secret_field(self) -> None:
        """Normal fields are not detected as secret."""
        field_info = ModelWithSecrets.model_fields["name"]
        assert _is_secret_field(field_info) is False

    def test_normal_field_not_secret(self) -> None:
        """Fields without secret metadata are not detected."""
        field_info = ModelWithSecrets.model_fields["normal_field"]
        assert _is_secret_field(field_info) is False


# --- Tests for model_dump_safe ---


class TestModelDumpSafe:
    """Tests for MadsciBaseModel.model_dump_safe()."""

    def test_secrets_redacted_by_default(self) -> None:
        """Secret fields are redacted when include_secrets=False (default)."""
        m = ModelWithSecrets()
        safe = m.model_dump_safe()
        assert safe["name"] == "test"
        assert safe["password"] == REDACTED_PLACEHOLDER
        assert safe["api_key"] == REDACTED_PLACEHOLDER
        assert safe["normal_field"] == "visible"

    def test_secrets_revealed_when_requested(self) -> None:
        """Secret fields are shown when include_secrets=True."""
        m = ModelWithSecrets()
        revealed = m.model_dump_safe(include_secrets=True)
        assert revealed["password"] == "secret123"  # noqa: S105
        assert revealed["api_key"] == "key123"

    def test_model_without_secrets(self) -> None:
        """Models without secret fields work normally."""
        m = ModelNoSecrets()
        safe = m.model_dump_safe()
        assert safe["name"] == "test"
        assert safe["count"] == 42

    def test_nested_model_redaction(self) -> None:
        """Nested models with secrets are also redacted."""
        m = ParentModel()
        safe = m.model_dump_safe()
        assert safe["name"] == "parent"
        assert safe["email_config"]["smtp_password"] == REDACTED_PLACEHOLDER
        assert safe["email_config"]["smtp_server"] == "mail.example.com"

    def test_nested_model_revealed(self) -> None:
        """Nested models reveal secrets when requested."""
        m = ParentModel()
        revealed = m.model_dump_safe(include_secrets=True)
        assert revealed["email_config"]["smtp_password"] == "smtp_pass"  # noqa: S105


# --- Tests for MadsciBaseSettings.model_dump_safe ---


class TestSettingsDumpSafe:
    """Tests for MadsciBaseSettings.model_dump_safe()."""

    def test_settings_secrets_redacted(self) -> None:
        """Settings secrets are redacted by default."""
        s = SettingsWithSecrets()
        safe = s.model_dump_safe()
        assert safe["host"] == "localhost"
        assert safe["db_url"] == REDACTED_PLACEHOLDER
        assert safe["redis_password"] == REDACTED_PLACEHOLDER

    def test_settings_secrets_revealed(self) -> None:
        """Settings secrets are shown when requested."""
        s = SettingsWithSecrets()
        revealed = s.model_dump_safe(include_secrets=True)
        assert revealed["db_url"] == "postgres://user:pass@localhost/db"
        assert revealed["redis_password"] == "redis_pass"  # noqa: S105


# --- Tests for to_yaml with secret redaction ---


class TestToYamlSecrets:
    """Tests for to_yaml() with include_secrets parameter."""

    def test_to_yaml_includes_secrets_by_default(self, tmp_path) -> None:
        """to_yaml() includes secrets by default for backwards compat."""
        m = ModelWithSecrets()
        path = tmp_path / "test.yaml"
        m.to_yaml(path)
        content = path.read_text()
        assert "secret123" in content
        assert REDACTED_PLACEHOLDER not in content

    def test_to_yaml_redacts_when_requested(self, tmp_path) -> None:
        """to_yaml(include_secrets=False) redacts secrets."""
        m = ModelWithSecrets()
        path = tmp_path / "test.yaml"
        m.to_yaml(path, include_secrets=False)
        content = path.read_text()
        assert "secret123" not in content
        assert REDACTED_PLACEHOLDER in content


# --- Tests for model_dump_yaml ---


class TestModelDumpYaml:
    """Tests for model_dump_yaml() with include_secrets parameter."""

    def test_dump_yaml_includes_secrets_by_default(self) -> None:
        """model_dump_yaml() includes secrets by default."""
        m = ModelWithSecrets()
        yaml_str = m.model_dump_yaml()
        assert "secret123" in yaml_str

    def test_dump_yaml_redacts_when_requested(self) -> None:
        """model_dump_yaml(include_secrets=False) redacts secrets."""
        m = ModelWithSecrets()
        yaml_str = m.model_dump_yaml(include_secrets=False)
        assert "secret123" not in yaml_str
        assert REDACTED_PLACEHOLDER in yaml_str


# --- Tests for real settings classes ---


class TestRealSettingsSecretAnnotations:
    """Tests that real manager settings classes have proper secret annotations."""

    def test_resource_manager_db_url_redacted(self) -> None:
        """ResourceManagerSettings.db_url is classified as secret."""
        s = ResourceManagerSettings()
        safe = s.model_dump_safe()
        assert safe["db_url"] == REDACTED_PLACEHOLDER

    def test_event_manager_mongo_url_redacted(self) -> None:
        """EventManagerSettings.mongo_db_url is classified as secret."""
        s = EventManagerSettings()
        safe = s.model_dump_safe()
        assert safe["mongo_db_url"] == REDACTED_PLACEHOLDER

    def test_workcell_manager_redis_password_redacted(self) -> None:
        """WorkcellManagerSettings.redis_password is classified as secret."""
        s = WorkcellManagerSettings()
        safe = s.model_dump_safe()
        assert safe["redis_password"] == REDACTED_PLACEHOLDER

    def test_location_manager_redis_password_redacted(self) -> None:
        """LocationManagerSettings.redis_password is classified as secret."""
        s = LocationManagerSettings()
        safe = s.model_dump_safe()
        assert safe["redis_password"] == REDACTED_PLACEHOLDER

    def test_data_manager_mongo_url_redacted(self) -> None:
        """DataManagerSettings.mongo_db_url is classified as secret."""
        s = DataManagerSettings()
        safe = s.model_dump_safe()
        assert safe["mongo_db_url"] == REDACTED_PLACEHOLDER

    def test_experiment_manager_mongo_url_redacted(self) -> None:
        """ExperimentManagerSettings.mongo_db_url is classified as secret."""
        s = ExperimentManagerSettings()
        safe = s.model_dump_safe()
        assert safe["mongo_db_url"] == REDACTED_PLACEHOLDER

    def test_object_storage_keys_redacted(self) -> None:
        """ObjectStorageSettings access/secret keys are classified as secret."""
        s = ObjectStorageSettings()
        safe = s.model_dump_safe()
        assert safe["access_key"] == REDACTED_PLACEHOLDER
        assert safe["secret_key"] == REDACTED_PLACEHOLDER

    def test_email_alerts_smtp_credentials_redacted(self) -> None:
        """EmailAlertsConfig SMTP credentials are classified as secret."""
        config = EmailAlertsConfig(smtp_username="user", smtp_password="pass")  # noqa: S106
        safe = config.model_dump_safe()
        assert safe["smtp_username"] == REDACTED_PLACEHOLDER
        assert safe["smtp_password"] == REDACTED_PLACEHOLDER
        assert safe["smtp_server"] == "smtp.example.com"  # not a secret
