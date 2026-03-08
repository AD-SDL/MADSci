"""Tests for MinioHandler implementations."""

from __future__ import annotations

import pytest
from madsci.common.db_handlers.minio_handler import MinioHandler

# ---------------------------------------------------------------------------
# Parametrized fixture
# ---------------------------------------------------------------------------


@pytest.fixture(
    params=["inmemory"],
)
def minio_handler(request, inmemory_minio_handler):
    """Provide a MinioHandler implementation for testing."""
    if request.param == "inmemory":
        return inmemory_minio_handler
    raise ValueError(f"Unknown handler type: {request.param}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMinioHandlerInterface:
    """Tests that verify any MinioHandler implementation behaves correctly."""

    def test_is_minio_handler(self, minio_handler):
        """Handler must implement MinioHandler ABC."""
        assert isinstance(minio_handler, MinioHandler)

    def test_ping(self, minio_handler):
        """Handler should respond to ping."""
        assert minio_handler.ping() is True

    def test_make_and_check_bucket(self, minio_handler):
        """make_bucket and bucket_exists should work."""
        assert minio_handler.bucket_exists("test-bucket") is False
        minio_handler.make_bucket("test-bucket")
        assert minio_handler.bucket_exists("test-bucket") is True

    def test_list_buckets(self, minio_handler):
        """list_buckets should return created buckets."""
        minio_handler.make_bucket("bucket-a")
        minio_handler.make_bucket("bucket-b")

        buckets = minio_handler.list_buckets()
        assert "bucket-a" in buckets
        assert "bucket-b" in buckets

    def test_ensure_bucket(self, minio_handler):
        """ensure_bucket should create if not exists."""
        minio_handler.ensure_bucket("auto-bucket")
        assert minio_handler.bucket_exists("auto-bucket") is True

        # Should be safe to call again
        minio_handler.ensure_bucket("auto-bucket")
        assert minio_handler.bucket_exists("auto-bucket") is True

    def test_upload_and_download(self, minio_handler, tmp_path):
        """Upload a file and download it back."""
        minio_handler.make_bucket("upload-test")

        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, MinIO!")

        # Upload
        result = minio_handler.upload_file("upload-test", "test.txt", test_file)
        assert result["bucket_name"] == "upload-test"
        assert result["object_name"] == "test.txt"
        assert result["size_bytes"] == len("Hello, MinIO!")
        assert "etag" in result
        assert "content_type" in result

        # Download
        output_path = tmp_path / "downloaded.txt"
        minio_handler.download_file("upload-test", "test.txt", output_path)
        assert output_path.read_text() == "Hello, MinIO!"

    def test_get_object_data(self, minio_handler, tmp_path):
        """get_object_data should return raw bytes."""
        minio_handler.make_bucket("data-test")

        test_file = tmp_path / "binary.bin"
        test_data = b"\x00\x01\x02\x03\x04"
        test_file.write_bytes(test_data)

        minio_handler.upload_file("data-test", "binary.bin", test_file)

        data = minio_handler.get_object_data("data-test", "binary.bin")
        assert data == test_data

    def test_upload_with_metadata(self, minio_handler, tmp_path):
        """Upload should accept custom metadata."""
        minio_handler.make_bucket("meta-test")

        test_file = tmp_path / "meta.txt"
        test_file.write_text("metadata test")

        result = minio_handler.upload_file(
            "meta-test",
            "meta.txt",
            test_file,
            content_type="text/plain",
            metadata={"source": "test"},
        )
        assert result["content_type"] == "text/plain"

    def test_upload_content_type_detection(self, minio_handler, tmp_path):
        """Upload should auto-detect content type from extension."""
        minio_handler.make_bucket("ct-test")

        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b,c")

        result = minio_handler.upload_file("ct-test", "data.csv", csv_file)
        assert (
            "csv" in result["content_type"].lower()
            or "text" in result["content_type"].lower()
        )

    def test_download_nonexistent_object(self, minio_handler, tmp_path):
        """Downloading a nonexistent object should raise an error."""
        minio_handler.make_bucket("missing-test")
        output = tmp_path / "output.txt"

        with pytest.raises((KeyError, FileNotFoundError, Exception)):
            minio_handler.download_file("missing-test", "nonexistent.txt", output)

    def test_get_nonexistent_object(self, minio_handler):
        """Getting data for a nonexistent object should raise an error."""
        minio_handler.make_bucket("missing-data")

        with pytest.raises((KeyError, FileNotFoundError, Exception)):
            minio_handler.get_object_data("missing-data", "nonexistent.bin")

    def test_upload_creates_parent_dirs_on_download(self, minio_handler, tmp_path):
        """download_file should create parent directories."""
        minio_handler.make_bucket("dirs-test")

        test_file = tmp_path / "source.txt"
        test_file.write_text("directory test")
        minio_handler.upload_file("dirs-test", "source.txt", test_file)

        nested_output = tmp_path / "deep" / "nested" / "output.txt"
        minio_handler.download_file("dirs-test", "source.txt", nested_output)
        assert nested_output.read_text() == "directory test"


# ---------------------------------------------------------------------------
# Integration tests (require Docker)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestMinioHandlerIntegration:
    """Tests that run against a real MinIO container."""

    @pytest.fixture(autouse=True)
    def _setup(self, real_minio_handler):
        self.handler = real_minio_handler

    def test_ping(self):
        """Real MinIO should respond to ping."""
        assert self.handler.ping() is True

    def test_upload_and_download(self, tmp_path):
        """Full upload/download cycle against real MinIO."""
        self.handler.make_bucket("int-test")

        test_file = tmp_path / "integration.txt"
        test_file.write_text("Integration test data")

        result = self.handler.upload_file("int-test", "integration.txt", test_file)
        assert result["bucket_name"] == "int-test"

        output = tmp_path / "downloaded.txt"
        self.handler.download_file("int-test", "integration.txt", output)
        assert output.read_text() == "Integration test data"
