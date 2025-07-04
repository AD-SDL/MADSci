"""Fast API Client for Resources"""

import time
from datetime import datetime
from typing import Any, Optional, Union

import requests
from madsci.client.event_client import EventClient
from madsci.common.types.context_types import MadsciContext
from madsci.common.types.resource_types import (
    GridIndex2D,
    GridIndex3D,
    Resource,
    ResourceDataModels,
)
from madsci.common.types.resource_types.definitions import ResourceDefinitions
from madsci.common.types.resource_types.server_types import (
    CreateResourceFromTemplateBody,
    PushResourceBody,
    RemoveChildBody,
    ResourceGetQuery,
    ResourceHistoryGetQuery,
    SetChildBody,
    TemplateCreateBody,
    TemplateGetQuery,
    TemplateUpdateBody,
)
from madsci.common.warnings import MadsciLocalOnlyWarning
from pydantic import AnyUrl


class ResourceClient:
    """REST client for interacting with a MADSci Resource Manager."""

    local_resources: dict[str, ResourceDataModels]
    context: Optional[MadsciContext] = None

    def __init__(
        self,
        url: Optional[Union[str, AnyUrl]] = None,
        event_client: Optional[EventClient] = None,
    ) -> None:
        """Initialize the resource client."""
        self.context = (
            MadsciContext(resource_server_url=url) if url else MadsciContext()
        )
        self.url = self.context.resource_server_url
        if self.url is not None and str(self.url).endswith("/"):
            self.url = str(self.url)[:-1]
        if self.url is not None:
            start_time = time.time()
            while time.time() - start_time < 20:
                try:
                    requests.get(self.url + "/definition", timeout=10)
                    break
                except Exception:
                    time.sleep(1)
            else:
                raise ConnectionError(
                    f"Could not connect to the resource manager at {self.url}."
                )
        self.local_resources = {}
        self.logger = event_client if event_client is not None else EventClient()
        if self.url is None:
            self.logger.log_warning(
                "ResourceClient initialized without a URL. Resource operations will be local-only and won't be persisted to a server. Local-only mode has limited functionality and should be used only for basic development purposes only. DO NOT USE LOCAL-ONLY MODE FOR PRODUCTION.",
                warning_category=MadsciLocalOnlyWarning,
            )

    def add_resource(self, resource: Resource) -> Resource:
        """
        Add a resource to the server.

        Args:
            resource (Resource): The resource to add.

        Returns:
            Resource: The added resource as returned by the server.
        """
        if self.url:
            response = requests.post(
                f"{self.url}/resource/add",
                json=resource.model_dump(mode="json"),
                timeout=10,
            )
            response.raise_for_status()
            resource = Resource.discriminate(response.json())
            resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        else:
            self.local_resources[resource.resource_id] = resource
        return resource

    def init_resource(
        self, resource_definition: ResourceDefinitions
    ) -> ResourceDataModels:
        """
        Initializes a resource with the resource manager based on a definition, either creating a new resource if no matching one exists, or returning an existing match.

        Args:
            resource (Resource): The resource to initialize.

        Returns:
            ResourceDataModels: The initialized resource as returned by the server.
        """
        self.logger.warning(
            "THIS METHOD IS DEPRECATED AND WILL BE REMOVED IN A FUTURE VERSION! Use Template methods instead."
        )
        if self.url:
            response = requests.post(
                f"{self.url}/resource/init",
                json=resource_definition.model_dump(mode="json"),
                timeout=10,
            )
            response.raise_for_status()

            resource = Resource.discriminate(response.json())
            resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        else:
            self.logger.log_warning(
                "Local-only mode does not check to see if an existing resource match already exists."
            )
            resource = Resource.discriminate(resource_definition)
            self.local_resources[resource.resource_id] = resource
        return resource

    def add_or_update_resource(self, resource: Resource) -> Resource:
        """
        Add a resource to the server.

        Args:
            resource (Resource): The resource to add.

        Returns:
            Resource: The added resource as returned by the server.
        """
        if self.url:
            response = requests.post(
                f"{self.url}/resource/add_or_update",
                json=resource.model_dump(mode="json"),
                timeout=10,
            )
            response.raise_for_status()
            resource = Resource.discriminate(response.json())
            resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        else:
            self.local_resources[resource.resource_id] = resource
        return resource

    def update_resource(self, resource: ResourceDataModels) -> ResourceDataModels:
        """
        Update or refresh a resource, including its children, on the server.

        Args:
            resource (ResourceDataModels): The resource to update.

        Returns:
            ResourceDataModels: The updated resource as returned by the server.
        """
        if self.url:
            response = requests.post(
                f"{self.url}/resource/update",
                json=resource.model_dump(mode="json"),
                timeout=10,
            )
            response.raise_for_status()
            resource = Resource.discriminate(response.json())
            resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        else:
            self.local_resources[resource.resource_id] = resource
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
        if self.url:
            response = requests.get(
                f"{self.url}/resource/{resource_id}",
                timeout=10,
            )
            response.raise_for_status()
            resource = Resource.discriminate(response.json())
            resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        else:
            self.logger.log_warning(
                "Local-only mode does not currently search through child resources to get children."
            )
            resource = self.local_resources.get(resource_id)
        return resource

    def query_resource(
        self,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        parent_id: Optional[str] = None,
        resource_class: Optional[str] = None,
        base_type: Optional[str] = None,
        unique: Optional[bool] = False,
        multiple: Optional[bool] = False,
    ) -> Union[ResourceDataModels, list[ResourceDataModels]]:
        """
        Query for one or more resources matching specific properties.

        Args:
            resource_id (str): The ID of the resource to retrieve.
            resource_name (str): The name of the resource to retrieve.
            parent_id (str): The ID of the parent resource.
            resource_class (str): The class of the resource.
            base_type (str): The base type of the resource.
            unique (bool): Whether to require a unique resource or not.
            multiple (bool): Whether to return multiple resources or just the first.

        Returns:
            Resource: The retrieved resource.
        """
        if self.url:
            payload = ResourceGetQuery(
                resource_id=resource_id,
                resource_name=resource_name,
                parent_id=parent_id,
                resource_class=resource_class,
                base_type=base_type,
                unique=unique,
                multiple=multiple,
            ).model_dump(mode="json")
            response = requests.post(
                f"{self.url}/resource/query", json=payload, timeout=10
            )
            response.raise_for_status()
            response_json = response.json()
            if isinstance(response_json, list):
                resources = [
                    Resource.discriminate(resource) for resource in response_json
                ]
                for resource in resources:
                    resource.resource_url = self.url
                return resources
            resource = Resource.discriminate(response.json())
            resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        else:
            self.logger.log_error(
                "Local-only mode does not currently support querying."
            )
            raise NotImplementedError(
                "Local-only mode does not currently support querying."
            )
        return resource

    def remove_resource(self, resource_id: str) -> dict[str, Any]:
        """
        Remove a resource by moving it to the history table with `removed=True`.
        """
        if self.url:
            response = requests.delete(f"{self.url}/resource/{resource_id}", timeout=10)
            response.raise_for_status()
            resource = Resource.discriminate(response.json())
            resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        else:
            resource = self.local_resources.pop(resource_id)
            resource.removed = True
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
        if self.url:
            query = ResourceHistoryGetQuery(
                resource_id=resource_id,
                version=version,
                change_type=change_type,
                removed=removed,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            ).model_dump(mode="json")
            response = requests.post(
                f"{self.url}/history/query", json=query, timeout=10
            )
            response.raise_for_status()
        else:
            self.logger.log_error(
                "Local-only mode does not currently support querying history."
            )
            raise NotImplementedError(
                "Local-only mode does not currently support querying history."
            )

        return response.json()

    def restore_deleted_resource(self, resource_id: str) -> dict[str, Any]:
        """
        Restore a deleted resource from the history table.
        """
        if self.url:
            response = requests.post(
                f"{self.url}/history/{resource_id}/restore", timeout=10
            )
            response.raise_for_status()
            resource = Resource.discriminate(response.json())
            resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        else:
            self.logger.log_error(
                "Local-only mode does not currently support restoring resources."
            )
            raise NotImplementedError(
                "Local-only mode does not currently support restoring resources."
            )
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
        if self.url:
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
        else:
            resource = resource.children.append(child)
            self.local_resources[resource.resource_id] = resource
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

        if self.url:
            resource_id = (
                resource.resource_id if isinstance(resource, Resource) else resource
            )
            response = requests.post(
                f"{self.url}/resource/{resource_id}/pop", timeout=10
            )
            response.raise_for_status()
            result = response.json()
            popped_asset = Resource.discriminate(result[0])
            update_parent = Resource.discriminate(result[1])
            popped_asset.resource_url = (
                f"{self.url}/resource/{popped_asset.resource_id}"
            )
            update_parent.resource_url = (
                f"{self.url}/resource/{update_parent.resource_id}"
            )
        else:
            update_parent = resource
            popped_asset = update_parent.children.pop(0)
            self.local_resources[update_parent.resource_id] = update_parent
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
        if self.url:
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
        else:
            resource = resource.children[key] = child
            self.local_resources[resource.resource_id] = resource
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
        if self.url:
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
        else:
            resource = resource.children.pop(key)
            self.local_resources[resource.resource_id] = resource
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
        if self.url:
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
        else:
            self.local_resources[resource.resource_id].quantity = quantity
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
        if self.url:
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
        else:
            self.local_resources[resource.resource_id].quantity += amount
            resource = self.local_resources[resource.resource_id]
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
        if self.url:
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
        else:
            self.local_resources[resource.resource_id].quantity += abs(amount)
            resource = self.local_resources[resource.resource_id]
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
        if self.url:
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
        else:
            self.local_resources[resource.resource_id].quantity -= abs(amount)
            resource = self.local_resources[resource.resource_id]
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
        if self.url:
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
        else:
            self.local_resources[resource.resource_id].capacity = capacity
            resource = self.local_resources[resource.resource_id]
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
        if self.url:
            resource_id = (
                resource.resource_id if isinstance(resource, Resource) else resource
            )
            response = requests.delete(
                f"{self.url}/resource/{resource_id}/capacity", timeout=10
            )
            response.raise_for_status()
            resource = Resource.discriminate(response.json())
            resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        else:
            self.local_resources[resource.resource_id].capacity = None
            resource = self.local_resources[resource.resource_id]
        return resource

    def empty(self, resource: Union[str, ResourceDataModels]) -> ResourceDataModels:
        """
        Empty the contents of a container or consumable resource.

        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.

        Returns:
            ResourceDataModels: The updated resource.
        """
        if self.url:
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
        else:
            resource = self.local_resources[resource.resource_id]
            while resource.children:
                resource.children.pop()
            if resource.quantity:
                resource.quantity = 0
            self.local_resources[resource.resource_id] = resource
        return resource

    def fill(self, resource: Union[str, ResourceDataModels]) -> ResourceDataModels:
        """
        Fill a consumable resource to capacity.

        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.

        Returns:
            ResourceDataModels: The updated resource.
        """
        if self.url:
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
        else:
            resource = self.local_resources[resource.resource_id]
            resource.quantity = resource.capacity
            self.local_resources[resource.resource_id] = resource
        return resource

    def create_template(
        self,
        resource: ResourceDataModels,
        template_name: str,
        description: str = "",
        required_overrides: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        created_by: Optional[str] = None,
        version: str = "1.0.0",
    ) -> ResourceDataModels:
        """
        Create a new resource template from a resource.

        Args:
            resource (ResourceDataModels): The resource to use as a template.
            template_name (str): Unique name for the template.
            description (str): Description of what this template creates.
            required_overrides (Optional[list[str]]): Fields that must be provided when using template.
            tags (Optional[list[str]]): Tags for categorization.
            created_by (Optional[str]): Creator identifier.
            version (str): Template version.

        Returns:
            ResourceDataModels: The created template resource.
        """
        if self.url:
            payload = TemplateCreateBody(
                resource=resource,
                template_name=template_name,
                description=description,
                required_overrides=required_overrides,
                tags=tags,
                created_by=created_by,
                version=version,
            ).model_dump(mode="json")
            response = requests.post(f"{self.url}/templates", json=payload, timeout=10)
            response.raise_for_status()
            template = Resource.discriminate(response.json())
            template.resource_url = f"{self.url}/templates/{template_name}"
        else:
            # Store template in local templates
            template_data = {
                "resource": resource,
                "template_name": template_name,
                "description": description,
                "required_overrides": required_overrides or [],
                "tags": tags or [],
                "created_by": created_by,
                "version": version,
            }
            self.local_templates[template_name] = template_data
            template = resource  # Return the original resource as template
        return template

    def get_template(self, template_name: str) -> Optional[ResourceDataModels]:
        """
        Get a template by name.

        Args:
            template_name (str): Name of the template to retrieve.

        Returns:
            Optional[ResourceDataModels]: The template resource if found, None otherwise.
        """
        if self.url:
            response = requests.get(f"{self.url}/templates/{template_name}", timeout=10)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            template = Resource.discriminate(response.json())
            template.resource_url = f"{self.url}/templates/{template_name}"
            return template
        template_data = self.local_templates.get(template_name)
        if template_data:
            return template_data["resource"]
        return None

    def list_templates(
        self,
        base_type: Optional[str] = None,
        tags: Optional[list[str]] = None,
        created_by: Optional[str] = None,
    ) -> list[ResourceDataModels]:
        """
        List templates with optional filtering.

        Args:
            base_type (Optional[str]): Filter by base resource type.
            tags (Optional[list[str]]): Filter by templates that have any of these tags.
            created_by (Optional[str]): Filter by creator.

        Returns:
            list[ResourceDataModels]: List of template resources.
        """
        if self.url:
            if any([base_type, tags, created_by]):
                # Use query endpoint for filtering
                payload = TemplateGetQuery(
                    base_type=base_type,
                    tags=tags,
                    created_by=created_by,
                ).model_dump(mode="json")
                response = requests.post(
                    f"{self.url}/templates/query", json=payload, timeout=10
                )
            else:
                # Use simple endpoint for no filtering
                response = requests.get(f"{self.url}/templates", timeout=10)

            response.raise_for_status()
            templates = [
                Resource.discriminate(template) for template in response.json()
            ]
            for template in templates:
                template.resource_url = f"{self.url}/templates/{template.resource_name}"
            return templates
        # Filter local templates
        templates = []
        for template_name, template_data in self.local_templates.items():  # noqa
            # Apply filters
            if base_type and template_data["resource"].base_type != base_type:
                continue
            if tags and not any(tag in template_data["tags"] for tag in tags):
                continue
            if created_by and template_data["created_by"] != created_by:
                continue
            templates.append(template_data["resource"])
        return templates

    def get_template_info(self, template_name: str) -> Optional[dict[str, Any]]:
        """
        Get detailed template metadata.

        Args:
            template_name (str): Name of the template.

        Returns:
            Optional[dict[str, Any]]: Template metadata if found, None otherwise.
        """
        if self.url:
            response = requests.get(
                f"{self.url}/templates/{template_name}/info", timeout=10
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        template_data = self.local_templates.get(template_name)
        if template_data:
            # Return metadata without the resource object
            return {
                "template_name": template_data["template_name"],
                "description": template_data["description"],
                "required_overrides": template_data["required_overrides"],
                "tags": template_data["tags"],
                "created_by": template_data["created_by"],
                "version": template_data["version"],
            }
        return None

    def update_template(
        self, template_name: str, updates: dict[str, Any]
    ) -> ResourceDataModels:
        """
        Update an existing template.

        Args:
            template_name (str): Name of the template to update.
            updates (dict[str, Any]): Fields to update.

        Returns:
            ResourceDataModels: The updated template resource.
        """
        if self.url:
            payload = TemplateUpdateBody(updates=updates).model_dump(mode="json")
            response = requests.put(
                f"{self.url}/templates/{template_name}", json=payload, timeout=10
            )
            response.raise_for_status()
            template = Resource.discriminate(response.json())
            template.resource_url = f"{self.url}/templates/{template_name}"
            return template
        template_data = self.local_templates.get(template_name)
        if template_data:
            # Update local template data
            for key, value in updates.items():
                if key in template_data:
                    template_data[key] = value
            return template_data["resource"]
        return None

    def delete_template(self, template_name: str) -> bool:
        """
        Delete a template from the database.

        Args:
            template_name (str): Name of the template to delete.

        Returns:
            bool: True if template was deleted, False if not found.
        """
        if self.url:
            response = requests.delete(
                f"{self.url}/templates/{template_name}", timeout=10
            )
            if response.status_code == 404:
                return False
            response.raise_for_status()
            return True
        if template_name in self.local_templates:
            del self.local_templates[template_name]
            return True
        return False

    def create_resource_from_template(
        self,
        template_name: str,
        resource_name: str,
        overrides: Optional[dict[str, Any]] = None,
        add_to_database: bool = True,
    ) -> ResourceDataModels:
        """
        Create a resource from a template.

        Args:
            template_name (str): Name of the template to use.
            resource_name (str): Name for the new resource.
            overrides (Optional[dict[str, Any]]): Values to override template defaults.
            add_to_database (bool): Whether to add the resource to the database.

        Returns:
            ResourceDataModels: The created resource.
        """
        if self.url:
            payload = CreateResourceFromTemplateBody(
                resource_name=resource_name,
                overrides=overrides,
                add_to_database=add_to_database,
            ).model_dump(mode="json")
            response = requests.post(
                f"{self.url}/templates/{template_name}/create_resource",
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            resource = Resource.discriminate(response.json())
            resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
            return resource
        template_data = self.local_templates.get(template_name)
        if not template_data:
            raise ValueError(f"Template '{template_name}' not found")

        # Check required overrides
        overrides = overrides or {}
        missing_required = [
            field
            for field in template_data["required_overrides"]
            if field not in overrides and field != "resource_name"
        ]
        if missing_required:
            raise ValueError(f"Missing required fields: {missing_required}")

        # Create new resource from template
        base_resource = template_data["resource"]
        resource_data = base_resource.model_dump()
        resource_data["resource_name"] = resource_name
        resource_data.update(overrides)

        # Create new resource
        new_resource = Resource.discriminate(resource_data)
        if add_to_database:
            self.local_resources[new_resource.resource_id] = new_resource
        return new_resource

    def get_templates_by_category(self) -> dict[str, list[str]]:
        """
        Get templates organized by base_type category.

        Returns:
            dict[str, list[str]]: Dictionary mapping base_type to template names.
        """
        if self.url:
            response = requests.get(f"{self.url}/templates/categories", timeout=10)
            response.raise_for_status()
            return response.json()
        categories = {}
        for template_name, template_data in self.local_templates.items():
            base_type = template_data["resource"].base_type.value
            if base_type not in categories:
                categories[base_type] = []
            categories[base_type].append(template_name)
        return categories
