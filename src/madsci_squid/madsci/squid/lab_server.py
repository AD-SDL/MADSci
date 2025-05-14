"""REST API and Server for the lab Manager."""

from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from madsci.common.types.context_types import MadsciContext
from madsci.common.types.lab_types import LabSettings


def create_lab_server(
    lab_settings: Optional[LabSettings] = None,
    context: Optional[MadsciContext] = None,
) -> FastAPI:
    """Creates an lab Manager's REST server."""

    lab_settings = lab_settings or LabSettings.load_model()
    context = context or MadsciContext.load_model()

    app = FastAPI()

    @app.get("/context")
    async def get_context() -> MadsciContext:
        """Get the context of the lab server."""
        return context

    @app.post("/context")
    async def set_context(new_context: MadsciContext) -> None:
        """Set the context of the lab server."""
        nonlocal context
        context = new_context

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
    lab_settings = LabSettings()
    context = MadsciContext()
    app = create_lab_server(lab_settings=lab_settings, context=context)
    uvicorn.run(
        app,
        host=lab_settings.lab_url.host,
        port=lab_settings.lab_url.port,
    )
