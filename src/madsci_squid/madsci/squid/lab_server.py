"""REST API and Server for the lab Manager."""

from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from madsci.client.event_client import EventClient
from madsci.common.context import get_current_madsci_context
from madsci.common.ownership import global_ownership_info
from madsci.common.types.context_types import MadsciContext
from madsci.common.types.lab_types import LabDefinition, LabManagerSettings


def create_lab_server(
    lab_settings: Optional[LabManagerSettings] = None,
    lab_definition: Optional[LabDefinition] = None,
) -> FastAPI:
    """Creates an lab Manager's REST server."""
    logger = EventClient()

    lab_settings = lab_settings or LabManagerSettings()
    logger.info(lab_settings)
    if not lab_definition:
        lab_def_path = Path(lab_settings.lab_definition).expanduser()
        if lab_def_path.exists():
            lab_definition = LabDefinition.from_yaml(
                lab_def_path,
            )
        else:
            lab_definition = LabDefinition()
        logger.info(f"Writing to lab definition file: {lab_def_path}")
        lab_definition.to_yaml(lab_def_path)
    global_ownership_info.manager_id = lab_definition.lab_id
    global_ownership_info.lab_id = lab_definition.lab_id
    logger = EventClient(
        name=f"lab_manager.{lab_definition.name}",
    )
    logger.info(lab_definition)
    context = get_current_madsci_context()
    logger.info(context)

    app = FastAPI()

    @app.get("/context")
    async def get_context() -> MadsciContext:
        """Get the context of the lab server."""
        return context

    if lab_settings.dashboard_files_path:
        app.mount(
            "/",
            StaticFiles(
                directory=Path(lab_settings.dashboard_files_path).expanduser(),
                html=True,
            ),
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


if __name__ == "__main__":
    lab_settings = LabManagerSettings()
    app = create_lab_server(lab_settings=lab_settings)
    uvicorn.run(
        app,
        host=lab_settings.lab_server_url.host,
        port=lab_settings.lab_server_url.port,
    )
