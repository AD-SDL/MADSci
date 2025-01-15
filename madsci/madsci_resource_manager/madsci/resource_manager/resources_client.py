import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from resources_interface import ResourcesInterface
from db_tables import Stack, Queue, Pool, Plate, Asset, Consumable

# --- Resource Client ---

class ResourceClient:
    def __init__(self, base_url: str, database_url: str):
        self.base_url = base_url
        self.database_url = database_url

    def add_resource(self, resource):
        """Add a resource."""
        response = requests.post(f"{self.base_url}/resources", json={
            "database_url": self.database_url,
            "resource": resource.dict()
        })
        response.raise_for_status()
        return response.json()

    def push_to_stack(self, stack, asset):
        """Push an asset to a stack."""
        response = requests.post(f"{self.base_url}/stack/{stack.resource_id}/push", json={
            "database_url": self.database_url,
            "asset": asset.dict()
        })
        response.raise_for_status()
        return response.json()

    def pop_from_stack(self, stack):
        """Pop an asset from a stack."""
        response = requests.post(f"{self.base_url}/stack/{stack.resource_id}/pop", json={
            "database_url": self.database_url
        })
        response.raise_for_status()
        return response.json()

    def push_to_queue(self, queue, asset):
        """Push an asset to a queue."""
        response = requests.post(f"{self.base_url}/queue/{queue.resource_id}/push", json={
            "database_url": self.database_url,
            "asset": asset.dict()
        })
        response.raise_for_status()
        return response.json()

    def pop_from_queue(self, queue):
        """Pop an asset from a queue."""
        response = requests.post(f"{self.base_url}/queue/{queue.resource_id}/pop", json={
            "database_url": self.database_url
        })
        response.raise_for_status()
        return response.json()

    def increase_pool_quantity(self, pool, amount: float):
        """Increase the quantity of a pool resource."""
        response = requests.post(f"{self.base_url}/pool/{pool.resource_id}/increase", json={
            "database_url": self.database_url,
            "amount": amount
        })
        response.raise_for_status()
        return response.json()

    def decrease_pool_quantity(self, pool, amount: float):
        """Decrease the quantity of a pool resource."""
        response = requests.post(f"{self.base_url}/pool/{pool.resource_id}/decrease", json={
            "database_url": self.database_url,
            "amount": amount
        })
        response.raise_for_status()
        return response.json()

    def fill_pool(self, pool):
        """Fill a pool to its capacity."""
        response = requests.post(f"{self.base_url}/pool/{pool.resource_id}/fill", json={
            "database_url": self.database_url
        })
        response.raise_for_status()
        return response.json()

    def empty_pool(self, pool):
        """Empty a pool."""
        response = requests.post(f"{self.base_url}/pool/{pool.resource_id}/empty", json={
            "database_url": self.database_url
        })
        response.raise_for_status()
        return response.json()

    def increase_plate_well(self, plate, well_id: str, quantity: float):
        """Increase the quantity in a specific well of a plate."""
        response = requests.post(f"{self.base_url}/plate/{plate.resource_id}/well/{well_id}/increase", json={
            "database_url": self.database_url,
            "quantity": quantity
        })
        response.raise_for_status()
        return response.json()

    def decrease_plate_well(self, plate, well_id: str, quantity: float):
        """Decrease the quantity in a specific well of a plate."""
        response = requests.post(f"{self.base_url}/plate/{plate.resource_id}/well/{well_id}/decrease", json={
            "database_url": self.database_url,
            "quantity": quantity
        })
        response.raise_for_status()
        return response.json()

    def update_plate_well(self, plate, well_id: str, child):
        """Update a specific well in a plate."""
        response = requests.post(f"{self.base_url}/plate/{plate.resource_id}/well/{well_id}/update", json={
            "database_url": self.database_url,
            "child": child.dict()
        })
        response.raise_for_status()
        return response.json()

# --- Resource Manager ---

app = FastAPI()

class DatabaseRequest(BaseModel):
    database_url: str

class ResourceRequest(DatabaseRequest):
    resource: dict

class PushToStackRequest(DatabaseRequest):
    asset: dict

@app.post("/resources")
def add_resource(request: ResourceRequest):
    try:
        resources_interface = ResourcesInterface(database_url=request.database_url)
        resource_class_map = {
            "stack": Stack,
            "queue": Queue,
            "pool": Pool,
            "plate": Plate,
            "asset": Asset,
            "consumable": Consumable
        }

        resource_type = request.resource.get("resource_type")
        if resource_type not in resource_class_map:
            raise HTTPException(status_code=400, detail="Invalid resource type")

        resource_class = resource_class_map[resource_type]
        resource = resource_class(**request.resource)
        saved_resource = resources_interface.add_resource(resource)

        return {"message": "Resource added successfully", "resource_id": saved_resource.resource_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stack/{stack_id}/push")
def push_to_stack(stack_id: str, request: PushToStackRequest):
    try:
        resources_interface = ResourcesInterface(database_url=request.database_url)
        stack = resources_interface.get_resource(resource_id=stack_id, resource_type="stack")
        if not stack:
            raise HTTPException(status_code=404, detail="Stack not found")

        asset = Asset(**request.asset)
        resources_interface.push_to_stack(stack, asset)
        return {"message": "Asset pushed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stack/{stack_id}/pop")
def pop_from_stack(stack_id: str, request: DatabaseRequest):
    try:
        resources_interface = ResourcesInterface(database_url=request.database_url)
        stack = resources_interface.get_resource(resource_id=stack_id, resource_type="stack")
        if not stack:
            raise HTTPException(status_code=404, detail="Stack not found")

        asset = resources_interface.pop_from_stack(stack)
        return {"message": "Asset popped successfully", "asset": asset.to_json()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add endpoints for queue, pool, plate, etc.

# --- Example Application Usage ---

def example_usage():
    client = ResourceClient(base_url="http://localhost:8000", database_url="postgresql://rpl:rpl@127.0.0.1:5432/resources")

    stack_data = {
        "resource_name": "stack",
        "resource_type": "stack",
        "capacity": 10
    }
    stack = client.add_resource(stack_data)

    for i in range(5):
        asset_data = {"resource_name": f"Test plate {i}"}
        asset = client.add_resource(asset_data)
        client.push_to_stack(stack["resource_id"], asset)

    for _ in range(2):
        client.pop_from_stack(stack["resource_id"])
