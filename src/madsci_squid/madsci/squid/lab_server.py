"""REST API and Server for the lab Manager."""

from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from madsci.common.types.lab_types import LabDefinition, LabUrls


def create_lab_server(
    lab_manager_definition: Optional[LabDefinition] = None,
) -> FastAPI:
    """Creates an lab Manager's REST server."""

    if not lab_manager_definition:
        lab_manager_definition = LabDefinition.load_model(require_unique=True)

    if not lab_manager_definition:
        raise ValueError(
            "No lab manager definition found, please specify a path with --definition, or add it to your lab definition's 'managers' section"
        )
    app = FastAPI()

    # * Logger
    @app.get("/urls")
    async def urls() -> LabUrls:
        """Get the definition for the Experiment Manager."""
        return lab_manager_definition.managers

    if lab_manager_definition.static_files_path:
        app.mount(
            "/",
            StaticFiles(
                directory=Path(lab_manager_definition.static_files_path).expanduser(),
                html=True,
            ),
        )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


if __name__ == "__main__":
    lab_manager_definition = LabDefinition.load_model(require_unique=True)
    app = create_lab_server(lab_manager_definition=lab_manager_definition)
    uvicorn.run(
        app,
        host=lab_manager_definition.host,
        port=lab_manager_definition.port,
    )
