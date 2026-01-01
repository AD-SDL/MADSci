"""Docker Helper Types (used for the automatic example.env and Configuration.md generation)"""

from madsci.common.types.base_types import MadsciBaseSettings
from pydantic import Field


class DockerComposeSettings(MadsciBaseSettings):
    """These environment variables are used to configure the default Docker Compose in the MADSci example lab."""

    USER_ID: int = Field(
        default=1000,
        description="The user ID to use for the MADSci services inside Docker containers. This should match your host user ID to avoid file permission issues. If not set, the default value used by the container is 9999.",
    )
    GROUP_ID: int = Field(
        default=1000,
        description="The group ID to use for the MADSci services inside Docker containers. This should match your host group ID to avoid file permission issues. If not set, the default value used by the container is 9999.",
    )
    REPO_PATH: str = Field(
        default="./",
        description="The path to the MADSci repository on the host machine. This is mounted into the Docker containers to provide access to the codebase.",
    )
    REDIS_PORT: int = Field(
        default=6379,
        description="The port on the host machine to bind the Redis service to. This allows other services to connect to Redis running inside the Docker container.",
    )
    MONGODB_PORT: int = Field(
        default=27017,
        description="The port on the host machine to bind the MongoDB service to. This allows other services to connect to MongoDB running inside the Docker container.",
    )
    POSTGRES_PORT: int = Field(
        default=5432,
        description="The port on the host machine to bind the PostgreSQL service to. This allows other services to connect to PostgreSQL running inside the Docker container.",
    )
    MINIO_PORT: int = Field(
        default=9000,
        description="The port on the host machine to bind the MinIO service to. This allows other services to connect to MinIO running inside the Docker container.",
    )
    MINIO_CONSOLE_PORT: int = Field(
        default=9001,
        description="The port on the host machine to bind the MinIO console to. This allows other services to connect to the MinIO console running inside the Docker container.",
    )
