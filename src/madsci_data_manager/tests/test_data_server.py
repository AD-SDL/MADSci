"""
Test the Data Manager's REST server.

Uses pytest-mock-resources to create a MongoDB fixture. Note that this _requires_
a working docker installation.
"""
# flake8: noqa

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
from madsci.common.types.datapoint_types import (
    DataManagerDefinition,
    FileDataPoint,
    ObjectStorageSettings,
    ValueDataPoint,
)
from madsci.data_manager.data_server import create_data_server
from pymongo.synchronous.database import Database
from pytest_mock_resources import MongoConfig, create_mongo_fixture

data_manager_def = DataManagerDefinition(
    name="test_data_manager",
)


@pytest.fixture(scope="session")
def pmr_mongo_config() -> MongoConfig:
    """Configure the MongoDB fixture."""
    return MongoConfig(image="mongo:8.0")


db_connection = create_mongo_fixture()


@pytest.fixture
def test_client(db_connection: Database) -> TestClient:
    """Data Server Test Client Fixture"""
    app = create_data_server(
        data_manager_definition=data_manager_def, db_client=db_connection
    )
    return TestClient(app)


def test_root(test_client: TestClient) -> None:
    """
    Test the root endpoint for the Data Manager's server.
    Should return a DataManagerDefinition.
    """
    result = test_client.get("/").json()
    DataManagerDefinition.model_validate(result)


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


def test_query_datapoints(test_client: TestClient) -> None:
    """
    Test querying events based on a selector.
    """
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


def find_free_port():  # noqa
    """Find a free port to use for MinIO."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port  # noqa


def is_docker_available():  # noqa
    """Check if Docker is available and running."""
    try:
        result = subprocess.run(  # noqa
            ["docker", "version"],  # noqa
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def cleanup_test_containers():
    """Clean up any leftover MinIO test containers."""
    try:
        # List all containers with our test prefix
        result = subprocess.run(
            [
                "docker",
                "ps",
                "-a",
                "--filter",
                "name=minio_test_",
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
            containers_cleaned = 0

            for name in container_names:
                if name.startswith("minio_test_"):
                    print(f"  Stopping container: {name}")
                    stop_result = subprocess.run(
                        ["docker", "stop", name],
                        capture_output=True,
                        timeout=30,
                        check=False,
                    )

                    print(f"  Removing container: {name}")
                    rm_result = subprocess.run(
                        ["docker", "rm", name],
                        capture_output=True,
                        timeout=30,
                        check=False,
                    )

                    if stop_result.returncode == 0 and rm_result.returncode == 0:
                        containers_cleaned += 1
                    else:
                        print(f"  Warning: Could not fully clean up {name}")

            if containers_cleaned > 0:
                print(f"Cleaned up {containers_cleaned} test container(s)")
            else:
                print("No containers needed cleanup")
        else:
            print("No MinIO test containers found")

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
    Fixture that starts a temporary MinIO server using Docker CLI directly.
    This is more reliable than testcontainers for some environments.
    """
    if not is_docker_available():
        pytest.skip("Docker not available")

    # Find free ports
    minio_port = find_free_port()
    console_port = find_free_port()

    # Create temporary directory for MinIO data
    temp_dir = tempfile.mkdtemp(prefix="minio_test_")

    # Container name with timestamp to avoid conflicts
    timestamp = int(time.time())
    container_name = f"minio_test_{timestamp}_{minio_port}"

    # Start MinIO container using docker CLI
    docker_cmd = [
        "docker",
        "run",
        "-d",
        "--name",
        container_name,
        "-p",
        f"{minio_port}:9000",
        "-p",
        f"{console_port}:9001",
        "-e",
        "MINIO_ROOT_USER=minioadmin",
        "-e",
        "MINIO_ROOT_PASSWORD=minioadmin",
        "-v",
        f"{temp_dir}:/data",
        "minio/minio:latest",
        "server",
        "/data",
        "--console-address",
        ":9001",
    ]

    container_id = None
    try:
        # Start the container
        print(f"Starting MinIO container on port {minio_port}...")
        result = subprocess.run(docker_cmd, capture_output=True, text=True, check=True)
        container_id = result.stdout.strip()
        print(f"MinIO container started: {container_id[:12]}")

        # Wait for MinIO to be ready
        minio_url = f"http://localhost:{minio_port}"
        _wait_for_minio(minio_url)
        print(f"MinIO is ready at {minio_url}")

        # Create test bucket
        _create_test_bucket("localhost", minio_port)

        yield {
            "host": "localhost",
            "port": minio_port,
            "console_port": console_port,
            "endpoint": f"localhost:{minio_port}",
            "url": minio_url,
            "access_key": "minioadmin",
            "secret_key": "minioadmin",
            "container_id": container_id,
            "container_name": container_name,
        }

    except subprocess.CalledProcessError as e:
        pytest.skip(f"Failed to start MinIO container: {e.stderr}")

    finally:
        # Individual container cleanup
        if container_id:
            print(f"Cleaning up MinIO container {container_name}...")
            try:
                # Stop container
                stop_result = subprocess.run(
                    ["docker", "stop", container_name],
                    capture_output=True,
                    timeout=30,
                    check=False,
                )
                # Remove container
                rm_result = subprocess.run(
                    ["docker", "rm", container_name],
                    capture_output=True,
                    timeout=30,
                    check=False,
                )

                if stop_result.returncode == 0 and rm_result.returncode == 0:
                    print(f"Container {container_name} cleaned up")
                else:
                    print(
                        f"Warning: Could not fully clean up container {container_name}"
                    )

            except Exception as e:
                print(f"Warning: Could not clean up container {container_name}: {e}")

        # Remove temp directory
        try:
            shutil.rmtree(temp_dir)
            print(f"Temporary directory {temp_dir} cleaned up")
        except Exception as e:
            print(f"Warning: Could not remove temp directory {temp_dir}: {e}")


def _wait_for_minio(minio_url, timeout=60):  # noqa
    """Wait for MinIO server to be ready."""
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{minio_url}/minio/health/live", timeout=5)
            if response.status_code == 200:
                return
        except requests.exceptions.RequestException:
            pass

        try:
            response = requests.get(minio_url, timeout=5)
            if response.status_code in [200, 403, 404]:
                return
        except requests.exceptions.RequestException:
            pass

        time.sleep(2)

    raise TimeoutError(
        f"MinIO server at {minio_url} did not become ready within {timeout} seconds"
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


def test_file_datapoint_with_minio(db_connection, tmp_path: Path) -> None:  # noqa
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
        data_manager_def = DataManagerDefinition(
            name="test_data_manager_with_minio",
        )

        app = create_data_server(
            data_manager_definition=data_manager_def,
            db_client=db_connection,
            object_storage_settings=ObjectStorageSettings(
                endpoint="localhost:9000",
                access_key="minioadmin",
                secret_key="minioadmin",  # noqa
                secure=False,
                default_bucket="madsci-test",
            ),
        )
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

        # Verify MinIO client methods were called
        assert mock_minio_client.bucket_exists.call_count == 2
        mock_minio_client.bucket_exists.assert_called_with("madsci-test")
        mock_minio_client.fput_object.assert_called_once()

        # Verify the fput_object call arguments
        call_args = mock_minio_client.fput_object.call_args
        assert call_args[1]["bucket_name"] == "madsci-test"
        assert call_args[1]["object_name"].endswith("test_minio.txt")
        assert call_args[1]["content_type"] == "text/plain"

        # Verify the returned datapoint has object storage fields and correct data_type
        assert result["data_type"] == "object_storage"
        assert "bucket_name" in result
        assert "object_name" in result
        assert "storage_endpoint" in result
        assert "url" in result
        assert "etag" in result

        assert result["bucket_name"] == "madsci-test"
        assert result["storage_endpoint"] == "localhost:9000"
        assert result["etag"] == "test-etag-123"
        assert "localhost:9001" in result["url"]  # Should use port 9001 for public URL
        assert (
            result["custom_metadata"]["original_datapoint_id"]
            == test_datapoint.datapoint_id
        )

        # Verify we can retrieve the datapoint with object storage info
        retrieved_result = test_client.get(
            f"/datapoint/{test_datapoint.datapoint_id}"
        ).json()
        assert retrieved_result["data_type"] == "object_storage"
        assert retrieved_result["bucket_name"] == "madsci-test"
        assert retrieved_result["object_name"] == result["object_name"]


@pytest.mark.skipif(not is_docker_available(), reason="Docker not available")
def test_real_minio_upload(db_connection, minio_server, tmp_path: Path) -> None:  # noqa
    """Test actual MinIO upload using the subprocess MinIO server."""
    # No mocks - use real MinIO from the fixture
    data_manager_def = DataManagerDefinition(
        name="test_data_manager_with_minio",
    )

    app = create_data_server(
        data_manager_definition=data_manager_def,
        db_client=db_connection,
        object_storage_settings=ObjectStorageSettings(
            endpoint=minio_server["endpoint"],
            access_key=minio_server["access_key"],
            secret_key=minio_server["secret_key"],
            secure=False,
            default_bucket="test-bucket",
        ),
    )
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
    assert result["object_name"].endswith("real_test.txt")
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
