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
