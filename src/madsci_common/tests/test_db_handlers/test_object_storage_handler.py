"""Tests for ObjectStorageHandler implementations."""

from __future__ import annotations

import pytest
from madsci.common.db_handlers.object_storage_handler import ObjectStorageHandler

# ---------------------------------------------------------------------------
# Parametrized fixture
# ---------------------------------------------------------------------------


@pytest.fixture(
    params=["inmemory"],
)
def object_storage_handler(request, inmemory_object_storage_handler):
    """Provide an ObjectStorageHandler implementation for testing."""
    if request.param == "inmemory":
        return inmemory_object_storage_handler
    raise ValueError(f"Unknown handler type: {request.param}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestObjectStorageHandlerInterface:
    """Tests that verify any ObjectStorageHandler implementation behaves correctly."""

    def test_is_object_storage_handler(self, object_storage_handler):
        """Handler must implement ObjectStorageHandler ABC."""
        assert isinstance(object_storage_handler, ObjectStorageHandler)

    def test_ping(self, object_storage_handler):
        """Handler should respond to ping."""
        assert object_storage_handler.ping() is True

    def test_make_and_check_bucket(self, object_storage_handler):
        """make_bucket and bucket_exists should work."""
        assert object_storage_handler.bucket_exists("test-bucket") is False
        object_storage_handler.make_bucket("test-bucket")
        assert object_storage_handler.bucket_exists("test-bucket") is True

    def test_list_buckets(self, object_storage_handler):
        """list_buckets should return created buckets."""
        object_storage_handler.make_bucket("bucket-a")
        object_storage_handler.make_bucket("bucket-b")

        buckets = object_storage_handler.list_buckets()
        assert "bucket-a" in buckets
        assert "bucket-b" in buckets

    def test_ensure_bucket(self, object_storage_handler):
        """ensure_bucket should create if not exists."""
        object_storage_handler.ensure_bucket("auto-bucket")
        assert object_storage_handler.bucket_exists("auto-bucket") is True

        # Should be safe to call again
        object_storage_handler.ensure_bucket("auto-bucket")
        assert object_storage_handler.bucket_exists("auto-bucket") is True

    def test_upload_and_download(self, object_storage_handler, tmp_path):
        """Upload a file and download it back."""
        object_storage_handler.make_bucket("upload-test")

        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, Object Storage!")

        # Upload
        result = object_storage_handler.upload_file(
            "upload-test", "test.txt", test_file
        )
        assert result["bucket_name"] == "upload-test"
        assert result["object_name"] == "test.txt"
        assert result["size_bytes"] == len("Hello, Object Storage!")
        assert "etag" in result
        assert "content_type" in result

        # Download
        output_path = tmp_path / "downloaded.txt"
        object_storage_handler.download_file("upload-test", "test.txt", output_path)
        assert output_path.read_text() == "Hello, Object Storage!"

    def test_get_object_data(self, object_storage_handler, tmp_path):
        """get_object_data should return raw bytes."""
        object_storage_handler.make_bucket("data-test")

        test_file = tmp_path / "binary.bin"
        test_data = b"\x00\x01\x02\x03\x04"
        test_file.write_bytes(test_data)

        object_storage_handler.upload_file("data-test", "binary.bin", test_file)

        data = object_storage_handler.get_object_data("data-test", "binary.bin")
        assert data == test_data

    def test_upload_with_metadata(self, object_storage_handler, tmp_path):
        """Upload should accept custom metadata."""
        object_storage_handler.make_bucket("meta-test")

        test_file = tmp_path / "meta.txt"
        test_file.write_text("metadata test")

        result = object_storage_handler.upload_file(
            "meta-test",
            "meta.txt",
            test_file,
            content_type="text/plain",
            metadata={"source": "test"},
        )
        assert result["content_type"] == "text/plain"

    def test_upload_content_type_detection(self, object_storage_handler, tmp_path):
        """Upload should auto-detect content type from extension."""
        object_storage_handler.make_bucket("ct-test")

        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b,c")

        result = object_storage_handler.upload_file("ct-test", "data.csv", csv_file)
        assert (
            "csv" in result["content_type"].lower()
            or "text" in result["content_type"].lower()
        )

    def test_download_nonexistent_object(self, object_storage_handler, tmp_path):
        """Downloading a nonexistent object should raise an error."""
        object_storage_handler.make_bucket("missing-test")
        output = tmp_path / "output.txt"

        with pytest.raises((KeyError, FileNotFoundError, Exception)):
            object_storage_handler.download_file(
                "missing-test", "nonexistent.txt", output
            )

    def test_get_nonexistent_object(self, object_storage_handler):
        """Getting data for a nonexistent object should raise an error."""
        object_storage_handler.make_bucket("missing-data")

        with pytest.raises((KeyError, FileNotFoundError, Exception)):
            object_storage_handler.get_object_data("missing-data", "nonexistent.bin")

    def test_upload_creates_parent_dirs_on_download(
        self, object_storage_handler, tmp_path
    ):
        """download_file should create parent directories."""
        object_storage_handler.make_bucket("dirs-test")

        test_file = tmp_path / "source.txt"
        test_file.write_text("directory test")
        object_storage_handler.upload_file("dirs-test", "source.txt", test_file)

        nested_output = tmp_path / "deep" / "nested" / "output.txt"
        object_storage_handler.download_file("dirs-test", "source.txt", nested_output)
        assert nested_output.read_text() == "directory test"


# ---------------------------------------------------------------------------
# Integration tests (require Docker)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestObjectStorageHandlerIntegration:
    """Tests that run against a real S3-compatible container."""

    @pytest.fixture(autouse=True)
    def _setup(self, real_object_storage_handler):
        self.handler = real_object_storage_handler

    def test_ping(self):
        """Real object storage should respond to ping."""
        assert self.handler.ping() is True

    def test_upload_and_download(self, tmp_path):
        """Full upload/download cycle against real object storage."""
        self.handler.make_bucket("int-test")

        test_file = tmp_path / "integration.txt"
        test_file.write_text("Integration test data")

        result = self.handler.upload_file("int-test", "integration.txt", test_file)
        assert result["bucket_name"] == "int-test"

        output = tmp_path / "downloaded.txt"
        self.handler.download_file("int-test", "integration.txt", output)
        assert output.read_text() == "Integration test data"
