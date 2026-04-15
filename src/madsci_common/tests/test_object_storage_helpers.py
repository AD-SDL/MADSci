"""Tests for object storage helper functions."""

import pytest
from madsci.common.object_storage_helpers import (
    ObjectNamingStrategy,
    generate_object_name,
)


class TestGenerateObjectName:
    """Tests for generate_object_name with all naming strategies."""

    def test_filename_only(self):
        result = generate_object_name("data.csv", ObjectNamingStrategy.FILENAME_ONLY)
        assert result == "data.csv"

    def test_filename_only_with_prefix(self):
        result = generate_object_name(
            "data.csv", ObjectNamingStrategy.FILENAME_ONLY, prefix="uploads"
        )
        assert result == "uploads/data.csv"

    def test_timestamped_path(self):
        result = generate_object_name("data.csv", ObjectNamingStrategy.TIMESTAMPED_PATH)
        # Should contain year/month/day/filename structure
        parts = result.split("/")
        assert len(parts) == 4
        assert parts[-1] == "data.csv"

    def test_ulid_prefixed(self):
        ulid = "01HXYZ1234567890ABCDEFGH"
        result = generate_object_name(
            "data.csv", ObjectNamingStrategy.ULID_PREFIXED, ulid=ulid
        )
        assert result == f"{ulid}_data.csv"

    def test_ulid_prefixed_with_prefix(self):
        ulid = "01HXYZ1234567890ABCDEFGH"
        result = generate_object_name(
            "data.csv",
            ObjectNamingStrategy.ULID_PREFIXED,
            prefix="uploads",
            ulid=ulid,
        )
        assert result == f"uploads/{ulid}_data.csv"

    def test_ulid_prefixed_without_ulid_raises(self):
        with pytest.raises(ValueError, match="ULID_PREFIXED strategy requires a ulid"):
            generate_object_name("data.csv", ObjectNamingStrategy.ULID_PREFIXED)

    def test_ulid_prefixed_with_empty_ulid_raises(self):
        with pytest.raises(ValueError, match="ULID_PREFIXED strategy requires a ulid"):
            generate_object_name(
                "data.csv", ObjectNamingStrategy.ULID_PREFIXED, ulid=""
            )
