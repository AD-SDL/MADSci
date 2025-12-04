"""Backup validation utilities and classes."""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from madsci.client.event_client import EventClient


class BackupValidator:
    """Handles backup validation operations."""

    def __init__(self, logger: Optional[EventClient] = None) -> None:
        """
        Initialize the backup validator.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or EventClient()

    def generate_checksum(self, backup_path: Path) -> str:
        """
        Generate SHA256 checksum for a backup file.

        Args:
            backup_path: Path to the backup file

        Returns:
            SHA256 checksum as hex string
        """
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        sha256_hash = hashlib.sha256()

        with backup_path.open("rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)

        return sha256_hash.hexdigest()

    def save_checksum(self, backup_path: Path, checksum: str) -> Path:
        """
        Save checksum to a file alongside the backup.

        Args:
            backup_path: Path to the backup file
            checksum: Checksum to save

        Returns:
            Path to the checksum file
        """
        checksum_file = backup_path.with_suffix(".checksum")
        checksum_file.write_text(checksum)
        return checksum_file

    def load_checksum(self, backup_path: Path) -> Optional[str]:
        """
        Load checksum from file.

        Args:
            backup_path: Path to the backup file

        Returns:
            Checksum string if file exists, None otherwise
        """
        checksum_file = backup_path.with_suffix(".checksum")
        if not checksum_file.exists():
            return None

        return checksum_file.read_text().strip()

    def validate_checksum(self, backup_path: Path) -> bool:
        """
        Validate backup file against its stored checksum.

        Args:
            backup_path: Path to the backup file

        Returns:
            True if checksum is valid, False otherwise
        """
        stored_checksum = self.load_checksum(backup_path)
        if stored_checksum is None:
            self.logger.warning(f"No checksum file found for {backup_path}")
            return False

        try:
            current_checksum = self.generate_checksum(backup_path)
            is_valid = current_checksum == stored_checksum

            if is_valid:
                self.logger.info(f"Checksum validation passed for {backup_path}")
            else:
                self.logger.error(
                    f"Checksum validation failed for {backup_path}: "
                    f"expected {stored_checksum}, got {current_checksum}"
                )

            return is_valid

        except Exception as e:
            self.logger.error(f"Error validating checksum for {backup_path}: {e}")
            return False

    def create_backup_metadata(
        self,
        backup_path: Path,
        database_version: Optional[str],
        backup_type: str,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create metadata dictionary for a backup.

        Args:
            backup_path: Path to the backup file
            database_version: Version of the database
            backup_type: Type of backup (postgresql, mongodb, etc.)
            additional_info: Additional metadata to include

        Returns:
            Metadata dictionary
        """
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "backup_path": str(backup_path),
            "backup_size": backup_path.stat().st_size if backup_path.exists() else 0,
            "checksum": self.generate_checksum(backup_path)
            if backup_path.exists()
            else "",
            "database_version": database_version,
            "backup_type": backup_type,
            "is_valid": True,
        }

        if additional_info:
            metadata["additional_info"] = additional_info

        return metadata

    def save_metadata(self, backup_path: Path, metadata: Dict[str, Any]) -> Path:
        """
        Save metadata to a JSON file alongside the backup.

        Args:
            backup_path: Path to the backup file
            metadata: Metadata dictionary to save

        Returns:
            Path to the metadata file
        """
        metadata_file = backup_path.with_suffix(".metadata.json")
        metadata_file.write_text(json.dumps(metadata, indent=2))
        return metadata_file

    def load_metadata(self, backup_path: Path) -> Optional[Dict[str, Any]]:
        """
        Load metadata from JSON file.

        Args:
            backup_path: Path to the backup file

        Returns:
            Metadata dictionary if file exists, None otherwise
        """
        metadata_file = backup_path.with_suffix(".metadata.json")
        if not metadata_file.exists():
            return None

        try:
            return json.loads(metadata_file.read_text())
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid metadata JSON in {metadata_file}: {e}")
            return None

    def validate_backup_comprehensive(
        self,
        backup_path: Path,
        expected_database_version: Optional[str] = None,
        expected_backup_type: Optional[str] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Perform comprehensive backup validation.

        Args:
            backup_path: Path to the backup file
            expected_database_version: Expected database version
            expected_backup_type: Expected backup type

        Returns:
            Tuple of (is_valid, validation_result_dict)
        """
        result = {
            "file_structure_valid": False,
            "checksum_valid": False,
            "metadata_valid": False,
            "version_match": True,
            "type_match": True,
        }

        # Check file structure
        if backup_path.suffix == ".sql":
            result["file_structure_valid"] = self.validate_sql_backup_structure(
                backup_path
            )
        else:
            result["file_structure_valid"] = (
                backup_path.exists() and backup_path.stat().st_size > 0
            )

        # Check checksum
        result["checksum_valid"] = self.validate_checksum(backup_path)

        # Check metadata
        metadata = self.load_metadata(backup_path)
        result["metadata_valid"] = metadata is not None

        if metadata:
            if expected_database_version:
                result["version_match"] = (
                    metadata.get("database_version") == expected_database_version
                )

            if expected_backup_type:
                result["type_match"] = (
                    metadata.get("backup_type") == expected_backup_type
                )

        is_valid = all(
            [
                result["file_structure_valid"],
                result["checksum_valid"],
                result["metadata_valid"],
                result["version_match"],
                result["type_match"],
            ]
        )

        return is_valid, result

    def validate_sql_backup_structure(self, backup_path: Path) -> bool:
        """
        Validate SQL backup file structure.

        Args:
            backup_path: Path to the SQL backup file

        Returns:
            True if structure is valid, False otherwise
        """
        if not backup_path.exists():
            return False

        try:
            content = backup_path.read_text(encoding="utf-8")

            # Basic validation - should contain SQL keywords
            sql_indicators = ["CREATE", "INSERT", "COPY", "--", "TABLE"]
            has_sql_content = any(
                keyword in content.upper() for keyword in sql_indicators
            )

            return has_sql_content and len(content.strip()) > 0

        except Exception as e:
            self.logger.error(
                f"Error validating SQL backup structure for {backup_path}: {e}"
            )
            return False

    def validate_backup_size(self, backup_path: Path, expected_size: int) -> bool:
        """
        Validate backup file size matches expected size.

        Args:
            backup_path: Path to the backup file
            expected_size: Expected file size in bytes

        Returns:
            True if size matches, False otherwise
        """
        if not backup_path.exists():
            return False

        actual_size = backup_path.stat().st_size
        return actual_size == expected_size
