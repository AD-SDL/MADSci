"""
Test the Data Manager's REST server.

Uses in-memory document storage handler for fast, Docker-free tests.
"""
# ruff: noqa: T201, S603, S607, S106, PLC0415, RET504

import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi.testclient import TestClient
from madsci.common.db_handlers.document_storage_handler import (
    InMemoryDocumentStorageHandler,
)
from madsci.common.types.datapoint_types import (
    DataManagerSettings,
    FileDataPoint,
    ObjectStorageSettings,
    ValueDataPoint,
)
from madsci.data_manager.data_server import DataManager


@pytest.fixture()
def document_handler():
    """Create an InMemoryDocumentStorageHandler for testing."""
    handler = InMemoryDocumentStorageHandler(database_name="test_data")
    yield handler
    handler.close()


@pytest.fixture
def test_manager(document_handler) -> DataManager:
    """Data Manager Fixture"""
    settings = DataManagerSettings(
        manager_name="test_data_manager", enable_registry_resolution=False
    )
    return DataManager(settings=settings, document_handler=document_handler)


@pytest.fixture
def test_client(test_manager: DataManager) -> TestClient:
    """Data Server Test Client Fixture"""
    app = test_manager.create_server()
    client = TestClient(app)
    yield client
    client.close()


def test_health_root(test_client: TestClient) -> None:
    """
    Test the health endpoint for the Data Manager's server.
    """
    result = test_client.get("/health")
    assert result.status_code == 200


def test_roundtrip_datapoint(test_client: TestClient) -> None:
    """
    Test that we can send and then retrieve a datapoint by ID.
    """
    test_datapoint = ValueDataPoint(
        label="test",
        value=5,
    )
    result = test_client.post(
        "/datapoint", data={"datapoint": test_datapoint.model_dump_json()}
    ).json()
    assert ValueDataPoint.model_validate(result) == test_datapoint
    result = test_client.get(f"/datapoint/{test_datapoint.datapoint_id}").json()
    assert ValueDataPoint.model_validate(result) == test_datapoint
    value = test_client.get(f"/datapoint/{test_datapoint.datapoint_id}/value")
    assert value.json() == test_datapoint.value


def test_roundtrip_file_datapoint(test_client: TestClient, tmp_path: Path) -> None:
    """
    Test that we can send and then retrieve a datapoint by ID.
    """
    test_file = Path(tmp_path) / "test.txt"
    test_file.expanduser().parent.mkdir(parents=True, exist_ok=True)
    with test_file.open("w") as f:
        f.write("test")
    test_datapoint = FileDataPoint(
        label="test",
        path=test_file,
    )
    result = test_client.post(
        "/datapoint",
        data={"datapoint": test_datapoint.model_dump_json()},
        files={
            (
                "files",
                (
                    str(Path(test_datapoint.path).name),
                    Path.open(Path(test_datapoint.path), "rb"),
                ),
            )
        },
    ).json()
    assert FileDataPoint.model_validate(result).label == test_datapoint.label
    result = test_client.get(f"/datapoint/{test_datapoint.datapoint_id}").json()
    assert FileDataPoint.model_validate(result).label == test_datapoint.label
    value = test_client.get(f"/datapoint/{test_datapoint.datapoint_id}/value")
    assert value.content == b"test"


def test_get_datapoints(test_client: TestClient) -> None:
    """
    Test that we can retrieve all datapoints and they are returned as a dictionary in reverse-chronological order, with the correct number of datapoints.
    """
    for i in range(10):
        test_datapoint = ValueDataPoint(
            label="test_" + str(i),
            value=i,
        )
        test_client.post(
            "/datapoint", data={"datapoint": test_datapoint.model_dump_json()}
        )
    query_number = 5
    result = test_client.get("/datapoints", params={"number": query_number}).json()
    # * Check that the number of events returned is correct
    assert len(result) == query_number
    previous_timestamp = float("inf")
    for _, value in result.items():
        datapoint = ValueDataPoint.model_validate(value)
        # * Check that the events are in reverse-chronological order
        assert datapoint.value in range(5, 10)
        assert previous_timestamp >= datapoint.data_timestamp.timestamp()
        previous_timestamp = datapoint.data_timestamp.timestamp()


def test_query_datapoints(test_client: TestClient, test_manager: DataManager) -> None:
    """
    Test querying events based on a selector.
    """
    # Clear datapoints
    test_manager.datapoints.delete_many({})
    # Create 20 datapoints with values 0-19
    for i in range(10, 20):
        test_datapoint = ValueDataPoint(
            label="test_" + str(i),
            value=i,
        )
        test_client.post(
            "/datapoint", data={"datapoint": test_datapoint.model_dump_json()}
        )
    test_val = 10
    selector = {"value": {"$gte": test_val}}
    result = test_client.post("/datapoints/query", json=selector).json()
    assert len(result) == test_val
    for _, value in result.items():
        datapoint = ValueDataPoint.model_validate(value)
        assert datapoint.value >= test_val


def find_free_port():
    """Find a free port to use for object storage."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def is_docker_available():
    """Check if Docker is available and running."""
    try:
        result = subprocess.run(
            ["docker", "version"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def cleanup_test_containers():
    """Clean up any leftover object storage test containers."""
    try:
        # List all containers with our test prefixes
        for prefix in ("seaweedfs_test_", "minio_test_"):
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "-a",
                    "--filter",
                    f"name={prefix}",
                    "--format",
                    "{{.Names}}",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            if result.returncode == 0 and result.stdout.strip():
                container_names = result.stdout.strip().split("\n")

                for name in container_names:
                    if name.startswith(prefix):
                        subprocess.run(
                            ["docker", "stop", name],
                            capture_output=True,
                            timeout=30,
                            check=False,
                        )
                        subprocess.run(
                            ["docker", "rm", name],
                            capture_output=True,
                            timeout=30,
                            check=False,
                        )

    except Exception as e:
        print(f"Could not clean up test containers: {e}")


@pytest.fixture(scope="session", autouse=True)
def cleanup_before_tests():
    """Automatically clean up any leftover containers before running tests."""
    cleanup_test_containers()
    yield


@pytest.fixture(scope="session", autouse=True)
def cleanup_after_tests():
    """Automatically clean up any leftover containers after running tests."""
    yield  # This runs before cleanup (i.e., after all tests complete)
    print("\nCleaning up test containers after all tests...")
    cleanup_test_containers()


@pytest.fixture(scope="session", autouse=True)
def cleanup_on_interrupt():
    """Clean up containers even if tests are interrupted."""
    try:
        yield
    except KeyboardInterrupt:
        print("\nTests interrupted, cleaning up containers...")
        cleanup_test_containers()
        raise
    except Exception:
        # Don't interfere with other exceptions, but still try to clean up
        cleanup_test_containers()
        raise


@pytest.fixture(scope="session")
def minio_server():
    """
    Fixture that starts a temporary SeaweedFS S3-compatible server using Docker CLI.
    This is more reliable than testcontainers for some environments.
    """
    if not is_docker_available():
        pytest.skip("Docker not available")

    # Find free port for S3 API
    s3_port = find_free_port()

    # Create temporary directory for SeaweedFS data
    temp_dir = tempfile.mkdtemp(prefix="seaweedfs_test_")

    # Container name with timestamp to avoid conflicts
    timestamp = int(time.time())
    container_name = f"seaweedfs_test_{timestamp}_{s3_port}"

    # Start SeaweedFS container using docker CLI
    docker_cmd = [
        "docker",
        "run",
        "-d",
        "--name",
        container_name,
        "-p",
        f"{s3_port}:8333",
        "-e",
        "AWS_ACCESS_KEY_ID=minioadmin",
        "-e",
        "AWS_SECRET_ACCESS_KEY=minioadmin",
        "-v",
        f"{temp_dir}:/data",
        "chrislusf/seaweedfs:4.17",
        "server",
        "-s3",
        "-dir=/data",
        "-s3.port=8333",
    ]

    container_id = None
    try:
        # Start the container
        print(f"Starting SeaweedFS container on port {s3_port}...")
        result = subprocess.run(docker_cmd, capture_output=True, text=True, check=True)
        container_id = result.stdout.strip()
        print(f"SeaweedFS container started: {container_id[:12]}")

        # Wait for SeaweedFS to be ready
        s3_url = f"http://localhost:{s3_port}"
        _wait_for_object_storage(s3_url)
        print(f"SeaweedFS is ready at {s3_url}")

        # Create test bucket
        _create_test_bucket("localhost", s3_port)

        yield {
            "host": "localhost",
            "port": s3_port,
            "endpoint": f"localhost:{s3_port}",
            "url": s3_url,
            "access_key": "minioadmin",
            "secret_key": "minioadmin",
            "container_id": container_id,
            "container_name": container_name,
        }

    except subprocess.CalledProcessError as e:
        pytest.skip(f"Failed to start SeaweedFS container: {e.stderr}")

    finally:
        if container_id:
            try:
                subprocess.run(
                    ["docker", "stop", container_name],
                    capture_output=True,
                    timeout=30,
                    check=False,
                )
                subprocess.run(
                    ["docker", "rm", container_name],
                    capture_output=True,
                    timeout=30,
                    check=False,
                )
            except Exception as e:
                print(f"Warning: Could not clean up container {container_name}: {e}")

        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Warning: Could not remove temp directory {temp_dir}: {e}")


def _wait_for_object_storage(url, timeout=60):
    """Wait for S3-compatible object storage server to be ready."""
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code in [200, 403, 404]:
                return
        except requests.exceptions.RequestException:
            pass

        time.sleep(2)

    raise TimeoutError(
        f"Object storage server at {url} did not become ready within {timeout} seconds"
    )


def _create_test_bucket(host, port):
    """Create the test bucket using MinIO client."""
    try:
        from minio import Minio

        client = Minio(
            f"{host}:{port}",
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False,
        )

        bucket_name = "madsci-test"
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            print(f"Created test bucket: {bucket_name}")
        else:
            print(f"Test bucket {bucket_name} already exists")

    except Exception as e:
        print(f"Warning: Could not create test bucket: {e}")


def test_file_datapoint_with_minio(document_handler, tmp_path: Path) -> None:
    """
    Test that file datapoints are uploaded to MinIO object storage when configured.
    This version uses mocks for fast unit testing.
    """
    # Create mock objects
    mock_minio_client = MagicMock()
    mock_minio_client.bucket_exists.return_value = True
    mock_minio_client.fput_object.return_value = MagicMock(etag="test-etag-123")

    # Mock the Minio class where it's imported in your server code
    with patch(
        "madsci.common.object_storage_helpers.Minio", return_value=mock_minio_client
    ):
        # Create DataManager with MinIO config
        settings = DataManagerSettings(
            manager_name="test_data_manager_with_minio",
            enable_registry_resolution=False,
        )

        manager = DataManager(
            settings=settings,
            document_handler=document_handler,
            object_storage_settings=ObjectStorageSettings(
                endpoint="localhost:8333",
                access_key="minioadmin",
                secret_key="minioadmin",
                secure=False,
                default_bucket="madsci-test",
            ),
        )
        app = manager.create_server()
        test_client = TestClient(app)

        # Create test file
        test_file = tmp_path / "test_minio.txt"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("test content for minio")

        test_datapoint = FileDataPoint(
            label="test_minio_file",
            path=test_file,
        )

        # Upload the datapoint
        result = test_client.post(
            "/datapoint",
            data={"datapoint": test_datapoint.model_dump_json()},
            files={
                (
                    "files",
                    (
                        str(Path(test_datapoint.path).name),
                        Path.open(Path(test_datapoint.path), "rb"),
                    ),
                )
            },
        ).json()

        # Verify object storage client methods were called via the RealObjectStorageHandler
        mock_minio_client.bucket_exists.assert_called_with("madsci-test")
        mock_minio_client.fput_object.assert_called_once()

        # Verify the fput_object call arguments
        call_args = mock_minio_client.fput_object.call_args
        assert call_args[1]["bucket_name"] == "madsci-test"
        assert call_args[1]["object_name"] == "test_minio_file"
        assert call_args[1]["content_type"] == "text/plain"

        # Verify the returned datapoint has object storage fields and correct data_type
        assert result["data_type"] == "object_storage"
        assert "bucket_name" in result
        assert "object_name" in result
        assert "storage_endpoint" in result
        assert "url" in result
        assert "etag" in result

        assert result["bucket_name"] == "madsci-test"
        assert result["object_name"] == "test_minio_file"
        assert result["storage_endpoint"] == "localhost:8333"
        assert result["etag"] == "test-etag-123"
        assert (
            "localhost:8333" in result["url"]
        )  # Uses same endpoint when no public_endpoint set
        assert result["url"] == "http://localhost:8333/madsci-test/test_minio_file"

        # Verify we can retrieve the datapoint with object storage info
        retrieved_result = test_client.get(
            f"/datapoint/{test_datapoint.datapoint_id}"
        ).json()
        assert retrieved_result["data_type"] == "object_storage"
        assert retrieved_result["bucket_name"] == "madsci-test"
        assert retrieved_result["object_name"] == result["object_name"]


@pytest.mark.skipif(not is_docker_available(), reason="Docker not available")
def test_real_minio_upload(document_handler, minio_server, tmp_path: Path) -> None:
    """Test actual MinIO upload using the subprocess MinIO server."""
    # No mocks - use real MinIO from the fixture
    settings = DataManagerSettings(
        manager_name="test_data_manager_with_minio",
        enable_registry_resolution=False,
    )

    manager = DataManager(
        settings=settings,
        document_handler=document_handler,
        object_storage_settings=ObjectStorageSettings(
            endpoint=minio_server["endpoint"],
            access_key=minio_server["access_key"],
            secret_key=minio_server["secret_key"],
            secure=False,
            default_bucket="test-bucket",
        ),
    )
    app = manager.create_server()
    test_client = TestClient(app)

    # Create a test file
    test_file = tmp_path / "real_test.txt"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_content = "This is a real test file for MinIO upload!"
    with test_file.open("w") as f:
        f.write(test_content)

    # Create a file datapoint
    test_datapoint = FileDataPoint(
        label="real_minio_test",
        path=test_file,
    )

    # Upload the datapoint to the server
    result = test_client.post(
        "/datapoint",
        data={"datapoint": test_datapoint.model_dump_json()},
        files={
            (
                "files",
                (
                    str(test_file.name),
                    test_file.open("rb"),
                ),
            )
        },
    ).json()

    # Verify the response indicates object storage
    assert result["data_type"] == "object_storage"
    assert result["bucket_name"] == "test-bucket"
    assert result["object_name"] == "real_minio_test"
    assert result["size_bytes"] == len(test_content)
    assert "url" in result

    # Verify the file actually exists in MinIO using the real client
    from minio import Minio

    # Create a real MinIO client to verify upload
    real_minio_client = Minio(
        endpoint=minio_server["endpoint"],
        access_key=minio_server["access_key"],
        secret_key=minio_server["secret_key"],
        secure=False,
    )

    # Check if the object exists
    bucket_name = result["bucket_name"]
    object_name = result["object_name"]

    # Try to get object info (this will raise an exception if it doesn't exist)
    object_info = real_minio_client.stat_object(bucket_name, object_name)
    assert object_info.size == len(test_content)

    # Download and verify content
    response = real_minio_client.get_object(bucket_name, object_name)
    downloaded_content = response.read().decode("utf-8")
    assert downloaded_content == test_content


def test_health_endpoint(test_client: TestClient) -> None:
    """Test the health endpoint of the Data Manager."""

    test_datapoint = ValueDataPoint(
        label="test",
        value=5,
    )
    test_client.post(
        "/datapoint", data={"datapoint": test_datapoint.model_dump_json()}
    ).json()

    response = test_client.get("/health")
    assert response.status_code == 200

    health_data = response.json()
    print(health_data)
    assert "healthy" in health_data
    assert "description" in health_data
    assert "db_connected" in health_data
    assert "storage_accessible" in health_data
    assert "total_datapoints" in health_data

    # Health should be True when database and storage are working
    assert health_data["healthy"] is True
    assert health_data["db_connected"] is True
    assert health_data["storage_accessible"] is True
    assert isinstance(health_data["total_datapoints"], int)
    assert health_data["total_datapoints"] >= 0
