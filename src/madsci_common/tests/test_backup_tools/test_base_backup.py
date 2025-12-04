"""Test abstract backup tool interface and base classes."""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from madsci.common.backup_tools.base_backup import (
    AbstractBackupTool,
    BackupInfo,
)
from madsci.common.types.backup_types import BaseBackupSettings


class TestBackupInfo:
    """Test BackupInfo model structure and validation."""

    def test_backup_info_creation(self):
        """Test BackupInfo model can be created with valid data."""
        backup_path = Path("/test/backup.dump")
        created_at = datetime.now()

        info = BackupInfo(
            backup_path=backup_path,
            created_at=created_at,
            database_version="1.0.0",
            backup_size=12345,
            checksum="abc123def456",
            backup_type="postgresql",
            is_valid=True,
        )

        assert info.backup_path == backup_path
        assert info.created_at == created_at
        assert info.database_version == "1.0.0"
        assert info.backup_size == 12345
        assert info.checksum == "abc123def456"
        assert info.backup_type == "postgresql"
        assert info.is_valid is True

    def test_backup_info_optional_fields(self):
        """Test BackupInfo with optional fields."""
        backup_path = Path("/test/backup.dump")
        created_at = datetime.now()

        info = BackupInfo(
            backup_path=backup_path,
            created_at=created_at,
            database_version=None,
            backup_size=0,
            checksum="",
            backup_type="mongodb",
            is_valid=False,
        )

        assert info.database_version is None
        assert info.backup_size == 0
        assert info.checksum == ""
        assert info.is_valid is False


class TestAbstractBackupTool:
    """Test abstract backup tool interface."""

    def test_backup_tool_is_abstract(self):
        """Test that AbstractBackupTool is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            AbstractBackupTool()

    def test_backup_tool_interface_requirements(self):
        """Test that backup tools implement required methods."""
        # Verify AbstractBackupTool has expected abstract methods
        expected_methods = {
            "create_backup",
            "restore_from_backup",
            "validate_backup_integrity",
            "list_available_backups",
            "delete_backup",
        }

        abstract_methods = set(AbstractBackupTool.__abstractmethods__)
        assert expected_methods.issubset(abstract_methods)

    def test_concrete_implementation_requirements(self):
        """Test that concrete implementations must implement all abstract methods."""

        class IncompleteBackupTool(AbstractBackupTool):
            """Incomplete implementation missing required methods."""

        with pytest.raises(TypeError):
            IncompleteBackupTool()

    def test_concrete_implementation_success(self):
        """Test that complete implementations can be instantiated."""

        class ConcreteBackupTool(AbstractBackupTool):
            """Complete implementation of backup tool."""

            def create_backup(self, name_suffix=None):  # noqa: ARG002
                return Path("/fake/backup")

            def restore_from_backup(self, backup_path, target_db=None):
                pass

            def validate_backup_integrity(self, backup_path):  # noqa: ARG002
                return True

            def list_available_backups(self):
                return []

            def delete_backup(self, backup_path):
                pass

        # Should not raise TypeError
        tool = ConcreteBackupTool()
        assert isinstance(tool, AbstractBackupTool)

    def test_backup_path_validation(self):
        """Test backup path creation and validation."""

        class TestBackupTool(AbstractBackupTool):
            def create_backup(self, name_suffix=None):
                # Should return Path object
                if name_suffix:
                    return Path(f"/backups/backup_{name_suffix}.dump")
                return Path("/backups/backup.dump")

            def restore_from_backup(self, backup_path, target_db=None):  # noqa: ARG002
                # Should accept Path object
                assert isinstance(backup_path, Path)

            def validate_backup_integrity(self, backup_path):
                assert isinstance(backup_path, Path)
                return True

            def list_available_backups(self):
                return [
                    BackupInfo(
                        backup_path=Path("/test/backup.dump"),
                        created_at=datetime.now(),
                        database_version="1.0.0",
                        backup_size=100,
                        checksum="test",
                        backup_type="test",
                        is_valid=True,
                    )
                ]

            def delete_backup(self, backup_path):
                assert isinstance(backup_path, Path)

        tool = TestBackupTool()

        # Test create_backup returns Path
        backup_path = tool.create_backup()
        assert isinstance(backup_path, Path)

        # Test create_backup with suffix
        backup_path_with_suffix = tool.create_backup("test_suffix")
        assert isinstance(backup_path_with_suffix, Path)
        assert "test_suffix" in str(backup_path_with_suffix)

        # Test other methods accept Path
        tool.restore_from_backup(backup_path)
        assert tool.validate_backup_integrity(backup_path) is True
        tool.delete_backup(backup_path)

    def test_backup_metadata_structure(self):
        """Test backup metadata format and content."""

        class TestBackupTool(AbstractBackupTool):
            def create_backup(self, name_suffix=None):  # noqa: ARG002
                return Path("/test/backup.dump")

            def restore_from_backup(self, backup_path, target_db=None):
                pass

            def validate_backup_integrity(self, backup_path):  # noqa: ARG002
                return True

            def list_available_backups(self):
                return [
                    BackupInfo(
                        backup_path=Path("/test/backup1.dump"),
                        created_at=datetime(2024, 1, 1, 12, 0, 0),
                        database_version="1.0.0",
                        backup_size=1000,
                        checksum="checksum1",
                        backup_type="postgresql",
                        is_valid=True,
                    ),
                    BackupInfo(
                        backup_path=Path("/test/backup2.dump"),
                        created_at=datetime(2024, 1, 2, 12, 0, 0),
                        database_version="1.1.0",
                        backup_size=2000,
                        checksum="checksum2",
                        backup_type="mongodb",
                        is_valid=False,
                    ),
                ]

            def delete_backup(self, backup_path):
                pass

        tool = TestBackupTool()
        backups = tool.list_available_backups()

        assert len(backups) == 2

        # Check first backup
        backup1 = backups[0]
        assert backup1.backup_path == Path("/test/backup1.dump")
        assert backup1.created_at == datetime(2024, 1, 1, 12, 0, 0)
        assert backup1.database_version == "1.0.0"
        assert backup1.backup_size == 1000
        assert backup1.checksum == "checksum1"
        assert backup1.backup_type == "postgresql"
        assert backup1.is_valid is True

        # Check second backup
        backup2 = backups[1]
        assert backup2.backup_path == Path("/test/backup2.dump")
        assert backup2.database_version == "1.1.0"
        assert backup2.backup_type == "mongodb"
        assert backup2.is_valid is False


class TestBaseBackupSettings:
    """Test base backup settings configuration."""

    def test_default_settings(self):
        """Test default backup settings values."""
        settings = BaseBackupSettings()

        assert settings.backup_dir == Path(".madsci/backups")
        assert settings.max_backups == 10
        assert settings.validate_integrity is True
        assert settings.compression is True

    def test_custom_settings(self):
        """Test custom backup settings values."""
        custom_dir = Path("/custom/backup/dir")

        settings = BaseBackupSettings(
            backup_dir=custom_dir,
            max_backups=5,
            validate_integrity=False,
            compression=False,
        )

        assert settings.backup_dir == custom_dir
        assert settings.max_backups == 5
        assert settings.validate_integrity is False
        assert settings.compression is False

    @pytest.mark.parametrize(
        "backup_dir_input,expected_type",
        [
            ("/absolute/path", Path),
            ("relative/path", Path),
            (Path("/already/path"), Path),
        ],
    )
    def test_backup_dir_path_conversion(self, backup_dir_input, expected_type):
        """Test backup directory path conversion."""
        settings = BaseBackupSettings(backup_dir=backup_dir_input)
        assert isinstance(settings.backup_dir, expected_type)

    def test_settings_validation(self):
        """Test settings field validation."""
        # Test negative max_backups
        with pytest.raises(ValueError):
            BaseBackupSettings(max_backups=-1)

    def test_settings_environment_integration(self):
        """Test settings can load from environment variables."""
        with patch.dict(
            "os.environ",
            {
                "MADSCI_BACKUP_DIR": "/env/backup/dir",
                "MADSCI_MAX_BACKUPS": "15",
                "MADSCI_VALIDATE_INTEGRITY": "false",
                "MADSCI_COMPRESSION": "false",
            },
        ):
            # Note: Actual environment loading depends on MadsciBaseSettings implementation
            # This test structure is prepared for when that's implemented
            pass
