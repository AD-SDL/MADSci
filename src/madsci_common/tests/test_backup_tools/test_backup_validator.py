"""Test shared backup validation logic."""

import hashlib
import tempfile
from pathlib import Path

import pytest
from madsci.common.backup_tools.backup_validator import BackupValidator


class TestBackupValidator:
    """Test shared backup validation logic."""

    @pytest.fixture
    def validator(self):
        """Create BackupValidator instance for testing."""
        return BackupValidator()

    @pytest.fixture
    def temp_backup_file(self):
        """Create temporary backup file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write(
                "-- Test backup content\nCREATE TABLE test (id INTEGER);\nINSERT INTO test VALUES (1);\n"
            )
            backup_path = Path(f.name)

        yield backup_path

        # Cleanup
        if backup_path.exists():
            backup_path.unlink()

    def test_checksum_generation_consistency(self, validator, temp_backup_file):
        """Test checksum generation produces consistent results."""
        # Generate checksum multiple times for same file
        checksum1 = validator.generate_checksum(temp_backup_file)
        checksum2 = validator.generate_checksum(temp_backup_file)
        checksum3 = validator.generate_checksum(temp_backup_file)

        # All checksums should be identical
        assert checksum1 == checksum2 == checksum3

        # Checksum should be SHA256 hex string (64 characters)
        assert len(checksum1) == 64
        assert all(c in "0123456789abcdef" for c in checksum1)

    def test_checksum_different_content(self, validator):
        """Test different file contents produce different checksums."""
        # Create two different temporary files
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f1:
            f1.write("Content 1")
            file1_path = Path(f1.name)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f2:
            f2.write("Content 2")
            file2_path = Path(f2.name)

        try:
            checksum1 = validator.generate_checksum(file1_path)
            checksum2 = validator.generate_checksum(file2_path)

            # Different content should produce different checksums
            assert checksum1 != checksum2

        finally:
            # Cleanup
            file1_path.unlink()
            file2_path.unlink()

    def test_checksum_empty_file(self, validator):
        """Test checksum generation for empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            # Create empty file
            empty_file_path = Path(f.name)

        try:
            checksum = validator.generate_checksum(empty_file_path)

            # Should generate valid checksum even for empty file
            assert len(checksum) == 64
            assert all(c in "0123456789abcdef" for c in checksum)

            # Empty file should have known SHA256 hash
            expected_empty_hash = hashlib.sha256(b"").hexdigest()
            assert checksum == expected_empty_hash

        finally:
            empty_file_path.unlink()

    def test_checksum_nonexistent_file(self, validator):
        """Test checksum generation for nonexistent file raises error."""
        nonexistent_path = Path("/nonexistent/file.sql")

        with pytest.raises(FileNotFoundError):
            validator.generate_checksum(nonexistent_path)

    def test_checksum_corruption_detection(self, validator, temp_backup_file):
        """Test corrupted backups are detected."""
        # Generate original checksum
        original_checksum = validator.generate_checksum(temp_backup_file)

        # Save checksum to file
        checksum_file = temp_backup_file.with_suffix(".checksum")
        validator.save_checksum(temp_backup_file, original_checksum)

        # Verify original file validates correctly
        assert validator.validate_checksum(temp_backup_file) is True

        # Corrupt the backup file
        with temp_backup_file.open("a") as f:
            f.write("\n-- CORRUPTED DATA --\n")

        # Validation should now fail
        assert validator.validate_checksum(temp_backup_file) is False

        # Cleanup
        if checksum_file.exists():
            checksum_file.unlink()

    def test_save_and_load_checksum(self, validator, temp_backup_file):
        """Test saving and loading checksum files."""
        # Generate and save checksum
        original_checksum = validator.generate_checksum(temp_backup_file)
        checksum_file = validator.save_checksum(temp_backup_file, original_checksum)

        # Verify checksum file was created
        assert checksum_file.exists()
        assert checksum_file.suffix == ".checksum"

        # Load checksum from file
        loaded_checksum = validator.load_checksum(temp_backup_file)

        # Loaded checksum should match original
        assert loaded_checksum == original_checksum

        # Cleanup
        checksum_file.unlink()

    def test_load_checksum_missing_file(self, validator, temp_backup_file):
        """Test loading checksum when file doesn't exist."""
        # Should return None when checksum file doesn't exist
        assert validator.load_checksum(temp_backup_file) is None

    def test_validate_checksum_missing_file(self, validator, temp_backup_file):
        """Test checksum validation when checksum file is missing."""
        # Should return False when checksum file doesn't exist
        assert validator.validate_checksum(temp_backup_file) is False

    def test_metadata_creation_and_validation(self, validator, temp_backup_file):
        """Test backup metadata is created and validated correctly."""
        # Test metadata structure
        metadata = validator.create_backup_metadata(
            backup_path=temp_backup_file,
            database_version="1.0.0",
            backup_type="postgresql",
            additional_info={"test_key": "test_value"},
        )

        # Verify metadata structure
        assert "timestamp" in metadata
        assert "backup_path" in metadata
        assert "backup_size" in metadata
        assert "checksum" in metadata
        assert "database_version" in metadata
        assert "backup_type" in metadata
        assert "is_valid" in metadata
        assert metadata["additional_info"]["test_key"] == "test_value"

        # Verify metadata content
        assert metadata["backup_path"] == str(temp_backup_file)
        assert metadata["backup_size"] == temp_backup_file.stat().st_size
        assert metadata["database_version"] == "1.0.0"
        assert metadata["backup_type"] == "postgresql"
        assert metadata["is_valid"] is True

    def test_save_and_load_metadata(self, validator, temp_backup_file):
        """Test saving and loading metadata files."""
        # Create metadata
        metadata = validator.create_backup_metadata(
            backup_path=temp_backup_file,
            database_version="1.0.0",
            backup_type="postgresql",
        )

        # Save metadata
        metadata_file = validator.save_metadata(temp_backup_file, metadata)

        # Verify metadata file was created
        assert metadata_file.exists()
        assert metadata_file.suffix == ".json"

        # Load metadata from file
        loaded_metadata = validator.load_metadata(temp_backup_file)

        # Loaded metadata should match original (excluding timestamp precision)
        assert loaded_metadata["backup_path"] == metadata["backup_path"]
        assert loaded_metadata["backup_size"] == metadata["backup_size"]
        assert loaded_metadata["database_version"] == metadata["database_version"]
        assert loaded_metadata["backup_type"] == metadata["backup_type"]

        # Cleanup
        metadata_file.unlink()

    def test_comprehensive_backup_validation(self, validator, temp_backup_file):
        """Test comprehensive backup validation workflow."""
        # First create the required metadata and checksum files
        checksum = validator.generate_checksum(temp_backup_file)
        validator.save_checksum(temp_backup_file, checksum)

        metadata = validator.create_backup_metadata(
            backup_path=temp_backup_file,
            database_version="1.0.0",
            backup_type="postgresql",
        )
        validator.save_metadata(temp_backup_file, metadata)

        # Now perform comprehensive validation
        is_valid, validation_result = validator.validate_backup_comprehensive(
            backup_path=temp_backup_file,
            expected_database_version="1.0.0",
            expected_backup_type="postgresql",
        )

        # Should be valid now that we have all required files
        assert is_valid is True
        assert "checksum_valid" in validation_result
        assert "metadata_valid" in validation_result
        assert "file_structure_valid" in validation_result

        # Verify specific validation results
        assert validation_result["file_structure_valid"] is True
        assert validation_result["checksum_valid"] is True
        assert validation_result["metadata_valid"] is True

        # Clean up created files
        checksum_file = temp_backup_file.with_suffix(".checksum")
        metadata_file = temp_backup_file.with_suffix(".metadata.json")
        if checksum_file.exists():
            checksum_file.unlink()
        if metadata_file.exists():
            metadata_file.unlink()

    def test_backup_file_structure_validation(self, validator):
        """Test backup file structure validation."""
        # Test SQL backup validation
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write("-- Valid SQL backup\nCREATE TABLE test (id INTEGER);\n")
            sql_backup_path = Path(f.name)

        try:
            assert validator.validate_sql_backup_structure(sql_backup_path) is True
        finally:
            sql_backup_path.unlink()

        # Test invalid SQL backup
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
            f.write("invalid content without SQL")
            invalid_sql_path = Path(f.name)

        try:
            assert validator.validate_sql_backup_structure(invalid_sql_path) is False
        finally:
            invalid_sql_path.unlink()

    def test_backup_size_validation(self, validator, temp_backup_file):
        """Test backup size validation."""
        actual_size = temp_backup_file.stat().st_size

        # Exact size should validate
        assert validator.validate_backup_size(temp_backup_file, actual_size) is True

        # Different size should not validate
        assert (
            validator.validate_backup_size(temp_backup_file, actual_size + 100) is False
        )

        # Zero size should not validate for non-empty file
        assert validator.validate_backup_size(temp_backup_file, 0) is False
