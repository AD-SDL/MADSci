import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

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

    def add_resource(self, resource):
        """Add a resource."""
        response = requests.post(
            f"{self.base_url}/resource/add",
            params={"database_url": self.database_url},
            json=resource.dict()
        )
        # Parse the returned resource and reconstruct the object
        resource_data = response.json()
        resource_type = resource_data.get("resource_type")
        if not resource_type or resource_type not in RESOURCE_TYPE_MAP:
            raise ValueError(f"Unknown or missing resource_type in response: {resource_type}")

        # Dynamically reconstruct the saved resource object
        resource_class = RESOURCE_TYPE_MAP[resource_type]
        return resource_class(**resource_data)
    
    def get_resource(self, resource_name=None, owner_name=None, resource_id=None, resource_type=None):
        """
        Retrieve a resource from the database.
        """
        # Prepare the data payload
        data = {
            "resource_name": resource_name,
            "owner_name": owner_name,
            "resource_id": resource_id,
            "resource_type": resource_type
        }

        # Make the request
        response = requests.post(
            f"{self.base_url}/resource/get",
            params={"database_url": self.database_url},
            json=data
        )
        response.raise_for_status()

        # Parse and reconstruct the resource object
        resource_data = response.json()
        resource_type = resource_data.get("resource_type")
        if not resource_type or resource_type not in RESOURCE_TYPE_MAP:
            raise ValueError(f"Unknown or missing resource_type in response: {resource_type}")

        # Dynamically reconstruct the resource object
        resource_class = RESOURCE_TYPE_MAP[resource_type]
        return resource_class(**resource_data)

    def push_to_stack(self, stack, asset):
        """Push an asset to a stack."""
        response = requests.post(
            f"{self.base_url}/stack/push",
            params={"database_url": self.database_url},
            json={"stack": stack.dict(), "asset": asset.dict()}
        )
        response.raise_for_status()
        return response.json()

    def pop_from_stack(self, stack):
        """Pop an asset from a stack."""
        response = requests.post(
            f"{self.base_url}/stack/pop",
            params={"database_url": self.database_url},
            json={"stack": stack.dict()}
        )
        response.raise_for_status()
        return response.json()

    def push_to_queue(self, queue, asset):
        """Push an asset to a queue."""
        response = requests.post(
            f"{self.base_url}/queue/push",
            params={"database_url": self.database_url},
            json={"queue": queue.dict(), "asset": asset.dict()}
        )
        response.raise_for_status()
        return response.json()

    def pop_from_queue(self, queue):
        """Pop an asset from a queue."""
        response = requests.post(
            f"{self.base_url}/queue/pop",
            params={"database_url": self.database_url},
            json={"queue": queue.dict()}
        )
        response.raise_for_status()
        return response.json()

    def increase_pool_quantity(self, pool, amount: float):
        """Increase the quantity of a pool resource."""
        response = requests.post(
            f"{self.base_url}/pool/increase",
            params={"database_url": self.database_url},
            json={"pool": pool.dict(), "amount": amount}
        )
        response.raise_for_status()
        return response.json()

    def decrease_pool_quantity(self, pool, amount: float):
        """Decrease the quantity of a pool resource."""
        response = requests.post(
            f"{self.base_url}/pool/decrease",
            params={"database_url": self.database_url},
            json={"pool": pool.dict(), "amount": amount}
        )
        response.raise_for_status()
        return response.json()

    def fill_pool(self, pool):
        """Fill a pool to its capacity."""
        response = requests.post(
            f"{self.base_url}/pool/fill",
            params={"database_url": self.database_url},
            json={"pool": pool.dict()}
        )
        response.raise_for_status()
        return response.json()

    def empty_pool(self, pool):
        """Empty a pool."""
        response = requests.post(
            f"{self.base_url}/pool/empty",
            params={"database_url": self.database_url},
            json={"pool": pool.dict()}
        )
        response.raise_for_status()
        return response.json()

    def increase_plate_well(self, plate, well_id: str, quantity: float):
        """Increase the quantity in a specific well of a plate."""
        response = requests.post(
            f"{self.base_url}/plate/increase_well",
            params={"database_url": self.database_url},
            json={"plate": plate.dict(), "well_id": well_id, "quantity": quantity}
        )
        response.raise_for_status()
        return response.json()

    def decrease_plate_well(self, plate, well_id: str, quantity: float):
        """Decrease the quantity in a specific well of a plate."""
        response = requests.post(
            f"{self.base_url}/plate/decrease_well",
            params={"database_url": self.database_url},
            json={"plate": plate.dict(), "well_id": well_id, "quantity": quantity}
        )
        response.raise_for_status()
        return response.json()

    def update_plate_well(self, plate, well_id: str, child):
        """Update a specific well in a plate."""
        response = requests.post(
            f"{self.base_url}/plate/update_well",
            params={"database_url": self.database_url},
            json={"plate": plate.dict(), "well_id": well_id, "child": child.dict()}
        )
        response.raise_for_status()
        return response.json()
