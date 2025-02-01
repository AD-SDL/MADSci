"""MADSci Resource Manager Server."""

from fastapi import FastAPI
from madsci.resource_manager.types import (
    ResourceManagerConfig,
    ResourceManagerDefinition,
)

app = FastAPI()

resource_manager_definition = ResourceManagerDefinition(
    name="Resource Manager 1",
    description="The First MADSci Resource Manager.",
    config=ResourceManagerConfig(),
)
resource_manager_definition.url = f"https://{resource_manager_definition.config.host}:{resource_manager_definition.config.port}"


@app.get("/info")
def info() -> ResourceManagerDefinition:
    """Get information about the resource manager."""
    return resource_manager_definition


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=resource_manager_definition.config.host,
        port=resource_manager_definition.config.port,
    )
