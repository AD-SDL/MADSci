import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pickle

from db_tables import Stack, Queue, Pool, Plate, Asset, Consumable

# --- Resource Client ---
# Resource type map for dynamic reconstruction
RESOURCE_TYPE_MAP = {
    "stack": Stack,
    "asset": Asset,
    "queue": Queue,
    "pool": Pool,
    "plate": Plate,
    "consumable": Consumable,
}
class ResourceClient:
    def __init__(self, base_url: str, database_url: str):
        self.base_url = base_url
        self.database_url = database_url

    # def add_resource(self, resource):
    #     """Add a resource."""
    #     response = requests.post(
    #         f"{self.base_url}/resource/add",
    #         params={"database_url": self.database_url},
    #         json=resource.dict()
    #     )
    #     # Parse the returned resource and reconstruct the object
    #     resource_data = response.json()
    #     resource_type = resource_data.get("resource_type")
    #     if not resource_type or resource_type not in RESOURCE_TYPE_MAP:
    #         raise ValueError(f"Unknown or missing resource_type in response: {resource_type}")

    #     # Dynamically reconstruct the saved resource object
    #     resource_class = RESOURCE_TYPE_MAP[resource_type]
    #     return resource_class(**resource_data)
    def add_resource(self, resource):
        """Add a resource."""
        payload = {
            "database_url": self.database_url,
            "resource": pickle.dumps(resource),  # Serialize the resource object
        }
        response = requests.post(
            f"{self.base_url}/resource/add",
            files={"data": pickle.dumps(payload)},  # Send payload as a file
        )
        response.raise_for_status()

        # Deserialize the binary response
        return pickle.loads(response.content)
    
    def get_resource(self, resource_name=None, owner_name=None, resource_id=None, resource_type=None):
        """
        Retrieve a resource from the database.
        """
        # Prepare the data payload
        payload = {
            "database_url": self.database_url,
            "resource_name": resource_name,
            "owner_name": owner_name,
            "resource_id": resource_id,
            "resource_type": resource_type,
        }

        # Send the request with the payload
        response = requests.post(
            f"{self.base_url}/resource/get",
            json=payload,  # Send as JSON
        )
        response.raise_for_status()

        # Deserialize the response to reconstruct the resource object
        resource = pickle.loads(response.content)
        return resource

    def push_to_stack(self, stack, asset):
        """Push an asset to a stack."""
        data = {
            "database_url": self.database_url,
            "stack": pickle.dumps(stack),
            "asset": pickle.dumps(asset)
        }
        response = requests.post(
            f"{self.base_url}/stack/push",
            files={"data": pickle.dumps(data)}
        )
        response.raise_for_status()
        return response.json()
    
    def pop_from_stack(self, stack):
        """Pop an asset from a stack."""
        data = {
            "database_url": self.database_url,
            "stack": pickle.dumps(stack)
        }
        response = requests.post(
            f"{self.base_url}/stack/pop",
            files={"data": pickle.dumps(data)}
        )
        response.raise_for_status()
        print(response)
        return pickle.loads(response.content)

    def push_to_queue(self, queue, asset):
        """Push an asset to a queue."""
        data = {
            "database_url": self.database_url,
            "queue": pickle.dumps(queue),
            "asset": pickle.dumps(asset)
        }
        response = requests.post(
            f"{self.base_url}/queue/push",
            files={"data": pickle.dumps(data)}
        )
        response.raise_for_status()
        return response.json()

    def pop_from_queue(self, queue):
        """Pop an asset from a queue."""
        data = {
            "database_url": self.database_url,
            "queue": pickle.dumps(queue)
        }
        response = requests.post(
            f"{self.base_url}/queue/pop",
            files={"data": pickle.dumps(data)}
        )
        response.raise_for_status()
        return pickle.loads(response.content)

    def increase_pool_quantity(self, pool, amount: float):
        """Increase the quantity of a pool resource."""
        data = {
            "database_url": self.database_url,
            "pool": pickle.dumps(pool),
            "amount": amount
        }
        response = requests.post(
            f"{self.base_url}/pool/increase",
            files={"data": pickle.dumps(data)}
        )
        response.raise_for_status()
        return response.json()

    def decrease_pool_quantity(self, pool, amount: float):
        """Decrease the quantity of a pool resource."""
        data = {
            "database_url": self.database_url,
            "pool": pickle.dumps(pool),
            "amount": amount
        }
        response = requests.post(
            f"{self.base_url}/pool/decrease",
            files={"data": pickle.dumps(data)}
        )
        response.raise_for_status()
        return response.json()

    def fill_pool(self, pool):
        """Fill a pool to its capacity."""
        data = {
            "database_url": self.database_url,
            "pool": pickle.dumps(pool)
        }
        response = requests.post(
            f"{self.base_url}/pool/fill",
            files={"data": pickle.dumps(data)}
        )
        response.raise_for_status()
        return response.json()

    def empty_pool(self, pool):
        """Empty a pool."""
        data = {
            "database_url": self.database_url,
            "pool": pickle.dumps(pool)
        }
        response = requests.post(
            f"{self.base_url}/pool/empty",
            files={"data": pickle.dumps(data)}
        )
        response.raise_for_status()
        return response.json()

    def increase_plate_well(self, plate, well_id: str, quantity: float):
        """Increase the quantity in a specific well of a plate."""
        data = {
            "database_url": self.database_url,
            "plate": pickle.dumps(plate),
            "well_id": well_id,
            "quantity": quantity
        }
        response = requests.post(
            f"{self.base_url}/plate/increase_well",
            files={"data": pickle.dumps(data)}
        )
        response.raise_for_status()
        return response.json()

    def decrease_plate_well(self, plate, well_id: str, quantity: float):
        """Decrease the quantity in a specific well of a plate."""
        data = {
            "database_url": self.database_url,
            "plate": pickle.dumps(plate),
            "well_id": well_id,
            "quantity": quantity
        }
        response = requests.post(
            f"{self.base_url}/plate/decrease_well",
            files={"data": pickle.dumps(data)}
        )
        response.raise_for_status()
        return response.json()

    def update_plate_well(self, plate, well_id: str, child):
        """Update a specific well in a plate."""
        data = {
            "database_url": self.database_url,
            "plate": pickle.dumps(plate),
            "well_id": well_id,
            "child": pickle.dumps(child)
        }
        response = requests.post(
            f"{self.base_url}/plate/update_well",
            files={"data": pickle.dumps(data)}
        )
        response.raise_for_status()
        return response.json()