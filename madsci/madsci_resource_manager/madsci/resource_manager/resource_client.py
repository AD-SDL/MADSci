import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# --- Resource Client ---

class ResourceClient:
    def __init__(self, base_url: str, database_url: str):
        self.base_url = base_url
        self.database_url = database_url

    def add_resource(self, resource):
        """Add a resource."""
        payload = {
            "database_url": self.database_url,
            "resource": resource.dict()
        }
        print(f"Payload: {payload}")  # Debugging
        response = requests.post(f"{self.base_url}/resource/add", json=payload)
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

