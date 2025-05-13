"""REST API and Server for the lab Manager."""

from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from madsci.common.types.lab_types import LabSettings


def create_lab_server(
    lab_settings: Optional[LabSettings] = None,
) -> FastAPI:
    """Creates an lab Manager's REST server."""

    lab_settings = lab_settings or LabSettings.load_model()

    app = FastAPI()

    if lab_settings.static_files_path:
        app.mount(
            "/",
            StaticFiles(
                directory=Path(lab_settings.static_files_path).expanduser(),
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
    lab_settings = LabSettings.load_model()
    app = create_lab_server()
    uvicorn.run(
        app,
        host=lab_settings.lab_url.host,
        port=lab_settings.lab_url.port,
    )
