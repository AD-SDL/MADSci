import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime

from madsci.resource_manager.serialization_utils import serialize_resource, deserialize_resource  
class ResourceClient:
    def __init__(self, base_url: str, database_url: str):
        self.base_url = base_url
        self.database_url = database_url

    def add_resource(self, resource):
        """
        Add a resource to the server.

        Args:
            resource (ResourceBase): The resource to add.

        Returns:
            ResourceBase: The added resource as returned by the server.
        """
        resource_data = serialize_resource(resource)
        response = requests.post(
            f"{self.base_url}/resource/add",
            json={"database_url": self.database_url, "resource": resource_data},
        )
        response.raise_for_status()
        return deserialize_resource(response.json())
        
    def update_resource(self, resource):
        """
        Update or refresh a resource, including its children, on the server.

        Args:
            resource (ResourceBase): The resource to update.

        Returns:
            ResourceBase: The updated resource as returned by the server.
        """
        resource_data = serialize_resource(resource)
        response = requests.post(
            f"{self.base_url}/resource/update",
            json={"database_url": self.database_url, "resource": resource_data},
        )
        response.raise_for_status()
        return deserialize_resource(response.json())

    def get_resource(
        self, resource_name=None, owner_name=None, resource_id=None, resource_type=None
    ):
        """
        Retrieve a resource from the database.

        Args:
            resource_name (str): Name of the resource (optional).
            owner_name (str): Owner of the resource (optional).
            resource_id (str): ID of the resource (optional).
            resource_type (str): Type of the resource (optional).

        Returns:
            ResourceBase: The retrieved resource.
        """
        payload = {
            "database_url": self.database_url,
            "resource_name": resource_name,
            "owner_name": owner_name,
            "resource_id": resource_id,
            "resource_type": resource_type,
        }
        response = requests.post(f"{self.base_url}/resource/get", json=payload)
        response.raise_for_status()
        return deserialize_resource(response.json())
    
    def remove_resource(self, resource_id: str) -> Dict[str, Any]:
        """
        Remove a resource by moving it to the history table with `removed=True`.
        """
        payload = {
            "database_url": self.database_url,
            "resource_id": resource_id
        }
        response = requests.post(f"{self.base_url}/resource/remove", json=payload)
        response.raise_for_status()
        return response.json()

    def get_history(
        self,
        resource_id: str,
        event_type: Optional[str] = None,
        removed: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the history of a resource with flexible filters.
        """
        payload = {
            "database_url": self.database_url,
            "resource_id": resource_id,
            "event_type": event_type,
            "removed": removed,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "limit": limit,
        }
        response = requests.post(f"{self.base_url}/resource/history", json=payload)
        response.raise_for_status()
        
        history_entries = response.json()

        for entry in history_entries:
            if "data" in entry:
                entry["data"] = deserialize_resource(entry["data"])

        return history_entries
    
    def restore_deleted_resource(self, resource_id: str) -> Dict[str, Any]:
        """
        Restore a deleted resource from the history table.
        """
        payload = {
            "database_url": self.database_url,
            "resource_id": resource_id
        }
        response = requests.post(f"{self.base_url}/resource/restore", json=payload)
        response.raise_for_status()
        return deserialize_resource(response.json())
    
    def push_to_stack(self, stack, asset) -> Dict[str, Any]:
        """
        Push an asset onto a stack.

        Args:
            stack (ResourceBase): The stack resource.
            asset (ResourceBase): The asset to push.

        Returns:
            dict: Success message from the server.
        """
        payload = {
            "database_url": self.database_url,
            "stack": serialize_resource(stack),
            "asset": serialize_resource(asset),
        }
        response = requests.post(f"{self.base_url}/stack/push", json=payload)
        response.raise_for_status()
        return deserialize_resource(response.json())

    def pop_from_stack(self, stack) :
        """
        Pop an asset from a stack.

        Args:
            stack (ResourceBase): The stack resource.

        Returns:
            tuple: The popped asset and updated stack.
        """
        payload = {"database_url": self.database_url, "stack": serialize_resource(stack)}
        response = requests.post(f"{self.base_url}/stack/pop", json=payload)
        response.raise_for_status()
        result = response.json()
        popped_asset = deserialize_resource(result["asset"])
        updated_stack = deserialize_resource(result["updated_stack"])
        return popped_asset, updated_stack

    def push_to_queue(self, queue, asset) -> Dict[str, Any]:
        """
        Push an asset onto a queue.

        Args:
            queue (ResourceBase): The queue resource.
            asset (ResourceBase): The asset to push.

        Returns:
            dict: Success message from the server.
        """
        payload = {
            "database_url": self.database_url,
            "queue": serialize_resource(queue),
            "asset": serialize_resource(asset),
        }
        response = requests.post(f"{self.base_url}/queue/push", json=payload)
        response.raise_for_status()
        return deserialize_resource(response.json())

    def pop_from_queue(self, queue) :
        """
        Pop an asset from a queue.

        Args:
            queue (ResourceBase): The queue resource.

        Returns:
            tuple: The popped asset and updated queue.
        """
        payload = {"database_url": self.database_url, "queue": serialize_resource(queue)}
        response = requests.post(f"{self.base_url}/queue/pop", json=payload)
        response.raise_for_status()
        result = response.json()
        popped_asset = deserialize_resource(result["asset"])
        updated_queue = deserialize_resource(result["updated_queue"])
        return popped_asset, updated_queue

    def increase_pool_quantity(self, pool, amount: float) -> Dict[str, Any]:
        """
        Increase the quantity of a pool resource.

        Args:
            pool (ResourceBase): The pool resource.
            amount (float): Amount to increase.

        Returns:
            dict: Success message from the server.
        """
        payload = {
            "database_url": self.database_url,
            "pool": serialize_resource(pool),
            "amount": amount,
        }
        response = requests.post(f"{self.base_url}/pool/increase", json=payload)
        response.raise_for_status()
        return deserialize_resource(response.json())

    def decrease_pool_quantity(self, pool, amount: float) -> Dict[str, Any]:
        """
        Decrease the quantity of a pool resource.

        Args:
            pool (ResourceBase): The pool resource.
            amount (float): Amount to decrease.

        Returns:
            dict: Success message from the server.
        """
        payload = {
            "database_url": self.database_url,
            "pool": serialize_resource(pool),
            "amount": amount,
        }
        response = requests.post(f"{self.base_url}/pool/decrease", json=payload)
        response.raise_for_status()
        return deserialize_resource(response.json())

    def fill_pool(self, pool) -> Dict[str, Any]:
        """
        Fill a pool to its capacity.

        Args:
            pool (ResourceBase): The pool resource.

        Returns:
            dict: Success message from the server.
        """
        payload = {"database_url": self.database_url, "pool": serialize_resource(pool)}
        response = requests.post(f"{self.base_url}/pool/fill", json=payload)
        response.raise_for_status()
        return deserialize_resource(response.json())

    def empty_pool(self, pool) -> Dict[str, Any]:
        """
        Empty a pool.

        Args:
            pool (ResourceBase): The pool resource.

        Returns:
            dict: Success message from the server.
        """
        payload = {"database_url": self.database_url, "pool": serialize_resource(pool)}
        response = requests.post(f"{self.base_url}/pool/empty", json=payload)
        response.raise_for_status()
        return deserialize_resource(response.json())
        
    def increase_plate_well(self, plate, well_id: str, quantity: float) -> Dict[str, Any]:
        """
        Increase the quantity in a specific well of a plate.

        Args:
            plate (ResourceBase): The plate resource.
            well_id (str): The ID of the well to increase.
            quantity (float): The amount to increase.

        Returns:
            dict: Success message from the server.
        """
        payload = {
            "database_url": self.database_url,
            "plate": serialize_resource(plate),
            "well_id": well_id,
            "quantity": quantity,
        }
        response = requests.post(f"{self.base_url}/plate/increase_well", json=payload)
        response.raise_for_status()
        return deserialize_resource(response.json())

    def decrease_plate_well(self, plate, well_id: str, quantity: float) -> Dict[str, Any]:
        """
        Decrease the quantity in a specific well of a plate.

        Args:
            plate (ResourceBase): The plate resource.
            well_id (str): The ID of the well to decrease.
            quantity (float): The amount to decrease.

        Returns:
            dict: Success message from the server.
        """
        payload = {
            "database_url": self.database_url,
            "plate": serialize_resource(plate),
            "well_id": well_id,
            "quantity": quantity,
        }
        response = requests.post(f"{self.base_url}/plate/decrease_well", json=payload)
        response.raise_for_status()
        return deserialize_resource(response.json())

    def update_collection_child(self, collection, key_id: str, child):
        """
        Update a specific chhild in a collection.

        Args:
            collection (ResourceBase): The collection resource.
            key_id (str): The ID of the collection key to update.
            child (ResourceBase): The new child resource to set.

        Returns:
            ResourceBase: The updated collection resource.
        """
        payload = {
            "database_url": self.database_url,
            "collection": serialize_resource(collection),
            "key_id": key_id,
            "child": serialize_resource(child),
        }
        response = requests.post(f"{self.base_url}/collection/update_child", json=payload)
        response.raise_for_status()
        return deserialize_resource(response.json())
