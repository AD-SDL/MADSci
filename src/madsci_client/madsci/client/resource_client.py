"""Fast API Client for Resources"""

from datetime import datetime
from typing import Any, Optional, Union

import requests
from madsci.common.types.resource_types import (
    GridIndex2D,
    GridIndex3D,
    ResourceDataModels,
)
from madsci.common.types.resource_types.server_types import (
    PushResourceBody,
    RemoveChildBody,
    ResourceGetQuery,
    ResourceHistoryGetQuery,
    SetChildBody,
)
from madsci.resource_manager.resource_tables import Resource


class ResourceClient:
    """Fast API Client for Resources"""

    def __init__(self, url: str) -> None:
        """Initial params"""
        self.url = url
        if self.url.endswith("/"):
            self.url = {self.url[:-1]}

    def add_resource(self, resource: ResourceDataModels) -> ResourceDataModels:
        """
        Add a resource to the server.

        Args:
            resource (ResourceDataModels): The resource to add.

        Returns:
            Resource: The added resource as returned by the server.
        """
        response = requests.post(
            f"{self.url}/resource/add",
            json=resource.model_dump(mode="json"),
            timeout=10,
        )
        response.raise_for_status()
        resource = Resource.discriminate(response.json())
        resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        return resource

    def update_resource(self, resource: ResourceDataModels) -> ResourceDataModels:
        """
        Update or refresh a resource, including its children, on the server.

        Args:
            resource (ResourceDataModels): The resource to update.

        Returns:
            ResourceDataModels: The updated resource as returned by the server.
        """
        response = requests.post(
            f"{self.url}/resource/update",
            json=resource.model_dump(mode="json"),
            timeout=10,
        )
        response.raise_for_status()
        resource = Resource.discriminate(response.json())
        resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        return resource

    def get_resource(
        self,
        resource_id: str,
    ) -> ResourceDataModels:
        """
        Retrieve a resource from the server.

        Args:
            resource_id (str): The ID of the resource to retrieve.

        Returns:
            ResourceDataModels: The retrieved resource.
        """
        response = requests.get(
            f"{self.url}/resource/{resource_id}",
            timeout=10,
        )
        response.raise_for_status()
        resource = Resource.discriminate(response.json())
        resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        return resource

    def query_resource(
        self,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        parent_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_base_type: Optional[str] = None,
        unique: Optional[bool] = False,
        multiple: Optional[bool] = False,
    ) -> Union[ResourceDataModels, list[ResourceDataModels]]:
        """
        Query for one or more resources matching specific properties.

        Args:
            resource_id (str): The ID of the resource to retrieve.
            resource_name (str): The name of the resource to retrieve.
            parent_id (str): The ID of the parent resource.
            resource_type (str): The custom type of the resource.
            resource_base_type (str): The base type of the resource.
            unique (bool): Whether to require a unique resource or not.
            multiple (bool): Whether to return multiple resources or just the first.

        Returns:
            Resource: The retrieved resource.
        """
        payload = ResourceGetQuery(
            resource_id=resource_id,
            resource_name=resource_name,
            parent_id=parent_id,
            resource_type=resource_type,
            resource_base_type=resource_base_type,
            unique=unique,
            multiple=multiple,
        ).model_dump(mode="json")
        response = requests.post(f"{self.url}/resource/query", json=payload, timeout=10)
        response.raise_for_status()
        response_json = response.json()
        if isinstance(response_json, list):
            resources = [Resource.discriminate(resource) for resource in response_json]
            for resource in resources:
                resource.resource_url = self.url
            return resources
        resource = Resource.discriminate(response.json())
        resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        return resource

    def remove_resource(self, resource_id: str) -> dict[str, Any]:
        """
        Remove a resource by moving it to the history table with `removed=True`.
        """
        response = requests.delete(f"{self.url}/resource/{resource_id}", timeout=10)
        response.raise_for_status()
        resource = Resource.discriminate(response.json())
        resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        return resource

    def query_history(
        self,
        resource_id: Optional[str] = None,
        version: Optional[int] = None,
        change_type: Optional[str] = None,
        removed: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = 100,
    ) -> list[dict[str, Any]]:
        """
        Retrieve the history of a resource with flexible filters.
        """
        query = ResourceHistoryGetQuery(
            resource_id=resource_id,
            version=version,
            change_type=change_type,
            removed=removed,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        ).model_dump(mode="json")
        response = requests.post(f"{self.url}/history/query", json=query, timeout=10)
        response.raise_for_status()

        return response.json()

    def restore_deleted_resource(self, resource_id: str) -> dict[str, Any]:
        """
        Restore a deleted resource from the history table.
        """
        response = requests.post(
            f"{self.url}/history/{resource_id}/restore", timeout=10
        )
        response.raise_for_status()
        resource = Resource.discriminate(response.json())
        resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        return resource

    def push(
        self,
        resource: Union[ResourceDataModels, str],
        child: Union[ResourceDataModels, str],
    ) -> ResourceDataModels:
        """
        Push a child resource onto a parent stack or queue.

        Args:
            resource (Union[ResourceDataModels, str]): The parent resource or its ID.
            child (Union[ResourceDataModels, str]): The child resource or its ID.

        Returns:
            ResourceDataModels: The updated parent resource.
        """
        resource_id = (
            resource.resource_id if isinstance(resource, Resource) else resource
        )
        payload = PushResourceBody(
            child=child if isinstance(child, Resource) else None,
            child_id=child.resource_id if isinstance(child, Resource) else child,
        ).model_dump(mode="json")
        response = requests.post(
            f"{self.url}/resource/{resource_id}/push", json=payload, timeout=10
        )
        response.raise_for_status()
        resource = Resource.discriminate(response.json())
        resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        return resource

    def pop(
        self, resource: Union[str, ResourceDataModels]
    ) -> tuple[ResourceDataModels, ResourceDataModels]:
        """
        Pop an asset from a stack or queue resource.

        Args:
            resource (Union[str, ResourceDataModels]): The parent resource or its ID.

        Returns:
            tuple[ResourceDataModels, ResourceDataModels]: The popped asset and updated parent.
        """

        resource_id = (
            resource.resource_id if isinstance(resource, Resource) else resource
        )
        response = requests.post(f"{self.url}/resource/{resource_id}/pop", timeout=10)
        response.raise_for_status()
        result = response.json()
        popped_asset = Resource.discriminate(result[0])
        update_parent = Resource.discriminate(result[1])
        popped_asset.resource_url = f"{self.url}/resource/{popped_asset.resource_id}"
        update_parent.resource_url = f"{self.url}/resource/{update_parent.resource_id}"
        return popped_asset, update_parent

    def set_child(
        self,
        resource: Union[str, ResourceDataModels],
        key: Union[str, GridIndex2D, GridIndex3D],
        child: Union[str, ResourceDataModels],
    ) -> ResourceDataModels:
        """
        Set a child resource in a parent container resource.

        Args:
            resource (Union[str, ResourceDataModels]): The parent container resource or its ID.
            key (Union[str, GridIndex2D, GridIndex3D]): The key to identify the child resource's location in the parent container.
            child (Union[str, ResourceDataModels]): The child resource or its ID.

        Returns:
            ResourceDataModels: The updated parent container resource.
        """
        resource_id = (
            resource.resource_id if isinstance(resource, Resource) else resource
        )
        payload = SetChildBody(
            key=key,
            child=child,
        ).model_dump(mode="json")
        response = requests.post(
            f"{self.url}/resource/{resource_id}/child/set",
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        resource = Resource.discriminate(response.json())
        resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        return resource

    def remove_child(
        self,
        resource: Union[str, ResourceDataModels],
        key: Union[str, GridIndex2D, GridIndex3D],
    ) -> ResourceDataModels:
        """
        Remove a child resource from a parent container resource.

        Args:
            resource (Union[str, ResourceDataModels]): The parent container resource or its ID.
            key (Union[str, GridIndex2D, GridIndex3D]): The key to identify the child resource's location in the parent container.

        Returns:
            ResourceDataModels: The updated parent container resource.
        """
        resource_id = (
            resource.resource_id if isinstance(resource, Resource) else resource
        )
        payload = RemoveChildBody(
            key=key,
        ).model_dump(mode="json")
        response = requests.post(
            f"{self.url}/resource/{resource_id}/child/remove",
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        resource = Resource.discriminate(response.json())
        resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        return resource

    def set_quantity(
        self, resource: Union[str, ResourceDataModels], quantity: Union[float, int]
    ) -> ResourceDataModels:
        """
        Set the quantity of a resource.

        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.
            quantity (Union[float, int]): The quantity to set.

        Returns:
            ResourceDataModels: The updated resource.
        """
        resource_id = (
            resource.resource_id if isinstance(resource, Resource) else resource
        )
        response = requests.post(
            f"{self.url}/resource/{resource_id}/quantity",
            params={"quantity": quantity},
            timeout=10,
        )
        response.raise_for_status()
        resource = Resource.discriminate(response.json())
        resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        return resource

    def change_quantity_by(
        self, resource: Union[str, ResourceDataModels], amount: Union[float, int]
    ) -> ResourceDataModels:
        """
        Change the quantity of a resource by a given amount.

        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.
            amount (Union[float, int]): The quantity to change by.

        Returns:
            ResourceDataModels: The updated resource.
        """
        resource_id = (
            resource.resource_id if isinstance(resource, Resource) else resource
        )
        response = requests.post(
            f"{self.url}/resource/{resource_id}/quantity/change_by",
            params={"amount": amount},
            timeout=10,
        )
        response.raise_for_status()
        resource = Resource.discriminate(response.json())
        resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        return resource

    def increase_quantity(
        self, resource: Union[str, ResourceDataModels], amount: Union[float, int]
    ) -> ResourceDataModels:
        """
        Increase the quantity of a resource by a given amount.

        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.
            amount (Union[float, int]): The quantity to increase by. Note that this is a magnitude, so negative and positive values will have the same effect.

        Returns:
            ResourceDataModels: The updated resource.
        """
        resource_id = (
            resource.resource_id if isinstance(resource, Resource) else resource
        )
        response = requests.post(
            f"{self.url}/resource/{resource_id}/quantity/increase",
            params={"amount": amount},
            timeout=10,
        )
        response.raise_for_status()
        resource = Resource.discriminate(response.json())
        resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        return resource

    def decrease_quantity(
        self, resource: Union[str, ResourceDataModels], amount: Union[float, int]
    ) -> ResourceDataModels:
        """
        Decrease the quantity of a resource by a given amount.

        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.
            amount (Union[float, int]): The quantity to decrease by. Note that this is a magnitude, so negative and positive values will have the same effect.

        Returns:
            ResourceDataModels: The updated resource.
        """
        resource_id = (
            resource.resource_id if isinstance(resource, Resource) else resource
        )
        response = requests.post(
            f"{self.url}/resource/{resource_id}/quantity/decrease",
            params={"amount": amount},
            timeout=10,
        )
        response.raise_for_status()
        resource = Resource.discriminate(response.json())
        resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        return resource

    def set_capacity(
        self, resource: Union[str, ResourceDataModels], capacity: Union[float, int]
    ) -> ResourceDataModels:
        """
        Set the capacity of a resource.

        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.
            capacity (Union[float, int]): The capacity to set.

        Returns:
            ResourceDataModels: The updated resource.
        """
        resource_id = (
            resource.resource_id if isinstance(resource, Resource) else resource
        )
        response = requests.post(
            f"{self.url}/resource/{resource_id}/capacity",
            params={"capacity": capacity},
            timeout=10,
        )
        response.raise_for_status()
        resource = Resource.discriminate(response.json())
        resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        return resource

    def remove_capacity_limit(
        self, resource: Union[str, ResourceDataModels]
    ) -> ResourceDataModels:
        """
        Remove the capacity limit of a resource.

        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.

        Returns:
            ResourceDataModels: The updated resource.
        """
        resource_id = (
            resource.resource_id if isinstance(resource, Resource) else resource
        )
        response = requests.delete(
            f"{self.url}/resource/{resource_id}/capacity", timeout=10
        )
        response.raise_for_status()
        resource = Resource.discriminate(response.json())
        resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        return resource

    def empty(self, resource: Union[str, ResourceDataModels]) -> ResourceDataModels:
        """
        Empty the contents of a container or consumable resource.

        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.

        Returns:
            ResourceDataModels: The updated resource.
        """
        resource_id = (
            resource.resource_id if isinstance(resource, Resource) else resource
        )
        response = requests.post(
            f"{self.url}/resource/{resource_id}/empty",
            timeout=10,
        )
        response.raise_for_status()
        resource = Resource.discriminate(response.json())
        resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        return resource

    def fill(self, resource: Union[str, ResourceDataModels]) -> ResourceDataModels:
        """
        Fill a consumable resource to capacity.

        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.

        Returns:
            ResourceDataModels: The updated resource.
        """
        resource_id = (
            resource.resource_id if isinstance(resource, Resource) else resource
        )
        response = requests.post(
            f"{self.url}/resource/{resource_id}/fill",
            timeout=10,
        )
        response.raise_for_status()
        resource = Resource.discriminate(response.json())
        resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        return resource
