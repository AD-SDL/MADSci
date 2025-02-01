"""Squid Lab Server."""

import uvicorn
from fastapi import FastAPI
from madsci.common.definition_loaders import lab_definition_loader
from madsci.common.types.lab_types import LabDefinition
from starlette.responses import JSONResponse

app = FastAPI()


@app.get("/")
async def root() -> JSONResponse:
    """Root endpoint."""
    return {"message": "Hello World"}


if __name__ == "__main__":
    lab_definition = LabDefinition.model_validate(lab_definition_loader())
    uvicorn.run(
        app,
        host=lab_definition.host,
        port=lab_definition.port,
    )
