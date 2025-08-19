"""REST API and Server for the Transfer Manager."""

from pathlib import Path
from typing import Dict, List, Optional, Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from madsci.client.event_client import EventClient
from madsci.common.ownership import global_ownership_info
from madsci.common.types.step_types import Step
from madsci.common.types.event_types import Event, EventType
from madsci.transfer_manager.transfer_manager import TransferManager, TransferManagerConfig
from madsci.common.types.transfer_manager_types import (
    TransferManagerDefinition,
    TransferManagerSettings
)


def create_transfer_manager_server(
    transfer_manager_definition: Optional[TransferManagerDefinition] = None,
    transfer_manager_settings: Optional[TransferManagerSettings] = None,
) -> FastAPI:
    """Creates a Transfer Manager's REST server."""
    
    logger = EventClient()
    transfer_manager_settings = transfer_manager_settings or TransferManagerSettings()
    transfer_manager_path = Path(transfer_manager_settings.transfer_manager_definition)
    
    if not transfer_manager_definition:
        if transfer_manager_path.exists():
            transfer_manager_definition = TransferManagerDefinition.from_yaml(transfer_manager_path)
        else:
            name = str(transfer_manager_path.name).split(".")[0]
            transfer_manager_definition = TransferManagerDefinition(transfer_manager_name=name)
        logger.log_info(f"Writing to transfer manager definition file: {transfer_manager_path}")
        transfer_manager_definition.to_yaml(transfer_manager_path)
    
    global_ownership_info.manager_id = transfer_manager_definition.transfer_manager_id
    logger = EventClient(name=f"transfer_manager.{transfer_manager_definition.transfer_manager_name}")
    logger.log_info(transfer_manager_definition)
    
    # Initialize Transfer Manager with paths from definition
    config = TransferManagerConfig(
        robot_definitions_path=Path(transfer_manager_definition.robot_definitions_path),
        location_constraints_path=Path(transfer_manager_definition.location_constraints_path)
    )
    
    try:
        transfer_manager = TransferManager(config)
        logger.log_info("Transfer Manager initialized successfully")
    except Exception as e:
        logger.log_error(f"Failed to initialize Transfer Manager: {e}")
        raise

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Start the REST server and initialize the transfer manager"""
        global_ownership_info.manager_id = transfer_manager_definition.transfer_manager_id
        
        # LOG TRANSFER MANAGER START EVENT
        logger.log(
            Event(
                event_type=EventType.TRANSFER_MANAGER_START,  # You may need to add this to EventType
                event_data=transfer_manager_definition.model_dump(mode="json"),
            )
        )
        
        try:
            yield
        finally:
            # LOG TRANSFER MANAGER STOP EVENT
            logger.log(
                Event(
                    event_type=EventType.TRANSFER_MANAGER_STOP,  # You may need to add this to EventType
                    event_data=transfer_manager_definition.model_dump(mode="json"),
                )
            )
    
    app = FastAPI(
        lifespan=lifespan,
        title=transfer_manager_definition.transfer_manager_name,
        description=transfer_manager_definition.description or "MADSci Transfer Manager",
        version="1.0.0"
    )

    @app.get("/")
    @app.get("/info")
    @app.get("/definition")
    async def get_definition() -> TransferManagerDefinition:
        """Get the Transfer Manager definition."""
        return transfer_manager_definition

    @app.get("/status")
    async def get_status() -> Dict[str, Any]:
        """Get Transfer Manager status."""
        return {
            "status": "running",
            "service": "transfer_manager",
            "version": "1.0.0",
            "transfer_manager_name": transfer_manager_definition.transfer_manager_name,
            "available_robots": transfer_manager.get_available_robots(),
            "available_locations": transfer_manager.get_available_locations(),
            "total_locations": len(transfer_manager.transfer_graph.locations)
        }

    @app.post("/handle_transfer_step")
    async def handle_transfer_step(step: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Handle a transfer step by expanding it into concrete workflow steps.
        This is the main endpoint called by workcell managers.
        """
        try:
            # Convert dict to Step object
            transfer_step = Step(**step)
            logger.log_info(f"Handling transfer step: {transfer_step.name} ({transfer_step.locations})")
            
            # Call TransferManager core logic
            concrete_steps = transfer_manager.expand_transfer_step(transfer_step)
            
            # Convert Step objects back to dicts for JSON response
            result = []
            for concrete_step in concrete_steps:
                step_dict = concrete_step.model_dump()
                result.append(step_dict)
            
            logger.log_info(f"Generated {len(result)} concrete steps")
            return result
            
        except Exception as e:
            logger.log_error(f"Error handling transfer step: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logger.log_info("Transfer Manager server created successfully")
    return app


if __name__ == "__main__":
    transfer_manager_settings = TransferManagerSettings()
    app = create_transfer_manager_server(transfer_manager_settings=transfer_manager_settings)
    uvicorn.run(
        app,
        host=transfer_manager_settings.transfer_manager_server_url.host,
        port=transfer_manager_settings.transfer_manager_server_url.port,
    )