# flake8: noqa
"""
Simplified MinIO test script for MADSci.
"""

import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import MADSci modules
from madsci.client.data_client import DataClient
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.datapoint_types import (  # noqa
    FileDataPoint,
    ObjectStorageSettings,
    ObjectStorageSettings,
)


def test_object_storage(file_path: str) -> None:
    """
    Test uploading and downloading a file using MinIO.

    Args:
        file_path: Path to the file to test with
    """
    file_path = Path(file_path).expanduser()
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return False

    logger.info(f"Testing with file: {file_path}")

    # Create MinIO configuration
    minio_config = ObjectStorageSettings(
        endpoint="localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",  # noqa
        secure=False,  # Use HTTP for local testing
        default_bucket="madsci-test",
    )

    # Initialize DataClient
    client = DataClient(
        url=None,  # Local mode
        object_storage_settings=minio_config,
    )

    try:
        # Create file datapoint
        file_datapoint = FileDataPoint(
            label=file_path.name, path=str(file_path), value="test_value"
        )

        # Upload file (will automatically use object storage)
        logger.info("Uploading file to MinIO...")
        uploaded_datapoint = client.submit_datapoint(file_datapoint)

        # Log details
        logger.info(
            f"Upload successful! Datapoint ID: {uploaded_datapoint.datapoint_id}"
        )
        logger.info(f"Data type: {uploaded_datapoint.data_type}")

        if hasattr(uploaded_datapoint, "bucket_name"):
            logger.info("Storage details:")
            logger.info(f"  - Bucket: {uploaded_datapoint.bucket_name}")
            logger.info(f"  - Object name: {uploaded_datapoint.object_name}")
            logger.info(f"  - URL: {uploaded_datapoint.url}")
            logger.info(f"  - Storage endpoint: {uploaded_datapoint.storage_endpoint}")
            logger.info(f"  - Public endpoint: {uploaded_datapoint.public_endpoint}")

        # Download to a new location
        download_path = Path(f"/Users/dozgulbas/Desktop/downloaded_{file_path.name}")
        logger.info(f"Downloading file to: {download_path}")
        client.save_datapoint_value(uploaded_datapoint.datapoint_id, str(download_path))

        # Verify download was successful
        if download_path.exists():
            original_size = file_path.stat().st_size
            downloaded_size = download_path.stat().st_size

            logger.info("Download successful!")
            logger.info(f"  - Original size: {original_size} bytes")
            logger.info(f"  - Downloaded size: {downloaded_size} bytes")
            logger.info(f"  - Content match: {original_size == downloaded_size}")

            return True
        logger.error("Download failed: File not found")
        return False

    except Exception as e:
        logger.error(f"Test failed with error: {e!s}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Get file path from command line argument or use a default
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = (
            "/Users/dozgulbas/Desktop/Train_1_2022-01-12_14-36-35_6de05ad28b.json"
        )

    success = test_object_storage(file_path)
    sys.exit(0 if success else 1)
