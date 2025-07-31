"""Fast API Client for Resources"""

import inspect
import time
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, ClassVar, Optional, Union

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
from madsci.common.utils import new_ulid_str
from madsci.common.warnings import MadsciLocalOnlyWarning
from pydantic import AnyUrl


class ResourceWrapper:
    """
    A wrapper around Resource data models that adds client method convenience.

    This class acts as a transparent proxy to the underlying resource while
    adding client methods.

    - Resource classes stay pure data models (no client dependencies)
    - This wrapper adds client functionality without modifying data classes
    - Wrapper is transparent - behaves like the wrapped resource for data access
    """

    def __init__(
        self, resource: "ResourceDataModels", client: "ResourceClient"
    ) -> None:
        """
        Create a wrapper around a resource.

        Args:
            resource: The pure data model (Stack, Queue, Resource, etc.)
            client: The ResourceClient instance for operations
        """
        object.__setattr__(self, "_resource", resource)
        object.__setattr__(self, "_client", client)

    def __getattr__(self, name: str) -> Any:
        """
        Handle attribute access - either delegate to resource or create method wrapper.
        """
        # Skip private attributes - always go to resource
        if name.startswith("_"):
            return getattr(self._resource, name)

        # Check if it's a client method (using the actual method name)
        if hasattr(self._client, name) and callable(getattr(self._client, name)):
            # Return a bound method that will call the client method appropriately
            return lambda *args, **kwargs: self._call_client_method(
                name, *args, **kwargs
            )

        # Not a client method - delegate to wrapped resource
        return getattr(self._resource, name)

    def _call_client_method(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        """
        Call a client method with the wrapped resource and handle the result.
        """
        client_method = getattr(self._client, method_name)

        # * Inspect the method signature to determine how to call it
        sig = inspect.signature(client_method)
        parameters = sig.parameters
        has_resource_arg = any(
            param.name == "resource"
            and param.kind
            in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
            for param in parameters.values()
        )
        if has_resource_arg and "resource" not in kwargs:
            result = client_method(self._resource, *args, **kwargs)
        else:
            # If the method does not require a resource argument, we can try calling it directly
            # with the provided args and kwargs.
            result = client_method(*args, **kwargs)
        return self._handle_method_result(result, method_name)

    def _handle_method_result(self, result: Any, method_name: str) -> Any:
        """
        Handle the result from a client method call intelligently.

        This determines whether to:
        - Update the wrapped resource and return self
        - Return the result directly
        - Handle special cases like tuples
        """
        # Methods that should return their result directly (not update self)
        direct_return_methods = {
            "acquire_lock",
            "release_lock",
            "is_locked",
            "query_history",
            "get_template_info",
            "delete_template",
            "list_templates",
            "get_templates_by_category",
        }

        if method_name in direct_return_methods:
            return result

        # Handle tuple results (like from pop) by recursively handling each item
        if isinstance(result, tuple):
            return tuple(
                self._handle_method_result(item, method_name) for item in result
            )

        # Handle single resource results
        if result and hasattr(result, "resource_id"):
            # It's a resource that should update our wrapped resource
            actual_resource = (
                result.unwrap if isinstance(result, ResourceWrapper) else result
            )

            # Only update if it's the same resource (same ID)
            if actual_resource.resource_id == self._resource.resource_id:
                self._resource = actual_resource
                return self  # Return self for method chaining
            # Different resource - wrap and return it
            return self._client._wrap_resource(actual_resource)

        return (
            result if result is not None else self
        )  # * Enable method chaining for void methods

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Magic method called when setting an attribute.

        Design:
        - Private attributes (starting with _) go to the wrapper
        - Public attributes go to the wrapped resource

        This ensures: wrapper.resource_name = "new" updates the underlying resource
        """
        if name.startswith("_"):
            # Private attributes (_resource, _client) go to the wrapper object
            object.__setattr__(self, name, value)
        else:
            # Public attributes go to the wrapped resource
            setattr(self._resource, name, value)

    def __eq__(self, other: Any) -> bool:
        """
        Equality comparison.

        Two wrappers are equal if their wrapped resources are equal.
        """
        if isinstance(other, ResourceWrapper):
            return self._resource == other._resource
        # Allow comparison with unwrapped resources
        return self._resource == other

    def __hash__(self) -> int:
        """
        Hash method for the wrapper.

        Uses the hash of the underlying resource's ID.
        """
        return hash(self._resource.resource_id)

    @property
    def unwrap(self) -> "ResourceDataModels":
        """
        Get the underlying pure data model.

        Useful when you need to pass the raw resource to functions
        that expect pure data models.
        """
        return self._resource

    @property
    def client(self) -> "ResourceClient":
        """Get the bound client instance."""
        return self._client


class ResourceClient:
    """REST client for interacting with a MADSci Resource Manager."""

    local_resources: dict[str, ResourceDataModels]
    local_templates: ClassVar[dict[str, dict]] = {}
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
        self._client_id = new_ulid_str()

    def _wrap_resource(
        self, resource: Optional["ResourceDataModels"]
    ) -> Optional[ResourceWrapper]:
        """Helper method to wrap a single resource."""
        if resource is None:
            return None
        return ResourceWrapper(resource, self)

    def _unwrap(self, resource: Any) -> Any:
        """Helper method to unwrap a resource if it's wrapped."""
        if isinstance(resource, ResourceWrapper):
            return resource.unwrap
        return resource

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
        return self._wrap_resource(resource)

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
        return self._wrap_resource(resource)

    def add_or_update_resource(self, resource: Resource) -> Resource:
        """
        Add a resource to the server.

        Args:
            resource (Resource): The resource to add.

        Returns:
            Resource: The added resource as returned by the server.
        """
        resource = self._unwrap(resource)

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
        return self._wrap_resource(resource)

    def update_resource(self, resource: ResourceDataModels) -> ResourceDataModels:
        """
        Update or refresh a resource, including its children, on the server.

        Args:
            resource (ResourceDataModels): The resource to update.

        Returns:
            ResourceDataModels: The updated resource as returned by the server.
        """
        resource = self._unwrap(resource)

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
        return self._wrap_resource(resource)

    update = update_resource

    def get_resource(
        self,
        resource: Optional[
            Union[str, ResourceDataModels]
        ] = None,  # Accept Resource object or ID
    ) -> ResourceDataModels:
        """
        Retrieve a resource from the server.

        Args:
            resource (Optional[Union[str, ResourceDataModels]]): The resource object or ID to retrieve.

        Returns:
            ResourceDataModels: The retrieved resource.
        """
        resource_id = resource if isinstance(resource, str) else resource.resource_id
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
        return self._wrap_resource(resource)

    def query_resource(
        self,
        resource: Optional[Union[str, ResourceDataModels]] = None,
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
            resource (str, Resource): The (ID of) the resource to retrieve.
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
            resource_id = (
                resource
                if (isinstance(resource, str) or resource is None)
                else resource.resource_id
            )
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
                for r in resources:
                    r.resource_url = self.url
                return [self._wrap_resource(r) for r in resources]
            resource = Resource.discriminate(response.json())
            resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        else:
            self.logger.log_error(
                "Local-only mode does not currently support querying."
            )
            raise NotImplementedError(
                "Local-only mode does not currently support querying."
            )
        return self._wrap_resource(resource)

    def remove_resource(
        self, resource: Union[str, ResourceDataModels]
    ) -> ResourceDataModels:
        """
        Remove a resource by moving it to the history table with `removed=True`.
        """
        if isinstance(resource, Resource):
            resource = resource.resource_id
        if self.url:
            response = requests.delete(f"{self.url}/resource/{resource}", timeout=10)
            response.raise_for_status()
            resource = Resource.discriminate(response.json())
            resource.resource_url = f"{self.url}/resource/{resource.resource_id}"
        else:
            resource = self.local_resources.pop(resource)
            resource.removed = True
        return self._wrap_resource(resource)

    remove = remove_resource

    def query_history(
        self,
        resource: Optional[Union[str, ResourceDataModels]] = None,
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
            resource_id = (
                resource if isinstance(resource, str) else resource.resource_id
            )
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

    def restore_deleted_resource(
        self, resource: Union[str, ResourceDataModels]
    ) -> ResourceDataModels:
        """
        Restore a deleted resource from the history table.
        """
        resource_id = resource if isinstance(resource, str) else resource.resource_id
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
        return self._wrap_resource(resource)

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
        resource = self._unwrap(resource)
        child = self._unwrap(child)

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
        return self._wrap_resource(resource)

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
            resource = self._unwrap(resource)
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
        return self._wrap_resource(popped_asset), self._wrap_resource(update_parent)

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
            resource = self._unwrap(resource)
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
        return self._wrap_resource(resource)

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
            resource = self._unwrap(resource)
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
        return self._wrap_resource(resource)

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
            resource = self._unwrap(resource)
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
        return self._wrap_resource(resource)

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
            resource = self._unwrap(resource)
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
        return self._wrap_resource(resource)

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
            resource = self._unwrap(resource)
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
        return self._wrap_resource(resource)

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
            resource = self._unwrap(resource)
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
        return self._wrap_resource(resource)

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
            resource = self._unwrap(resource)
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
        return self._wrap_resource(resource)

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
            resource = self._unwrap(resource)
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
        return self._wrap_resource(resource)

    def empty(self, resource: Union[str, ResourceDataModels]) -> ResourceDataModels:
        """
        Empty the contents of a container or consumable resource.

        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.

        Returns:
            ResourceDataModels: The updated resource.
        """
        if self.url:
            resource = self._unwrap(resource)
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
        return self._wrap_resource(resource)

    def fill(self, resource: Union[str, ResourceDataModels]) -> ResourceDataModels:
        """
        Fill a consumable resource to capacity.

        Args:
            resource (Union[str, ResourceDataModels]): The resource or its ID.

        Returns:
            ResourceDataModels: The updated resource.
        """
        if self.url:
            resource = self._unwrap(resource)
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
        return self._wrap_resource(resource)

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
        resource = self._unwrap(resource)
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
        return self._wrap_resource(template)

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
            return self._wrap_resource(template)
        template_data = self.local_templates.get(template_name)
        if template_data:
            return self._wrap_resource(template_data["resource"])
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
        return [self._wrap_resource(t) for t in templates]

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
            return self._wrap_resource(template)
        template_data = self.local_templates.get(template_name)
        if template_data:
            # Update local template data
            for key, value in updates.items():
                if key in template_data:
                    template_data[key] = value
            return self._wrap_resource(template_data["resource"])
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
        return self._wrap_resource(new_resource)

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

    def acquire_lock(
        self,
        resource: Union[str, ResourceDataModels],
        lock_duration: float = 300.0,
        client_id: Optional[str] = None,
    ) -> bool:
        """
        Acquire a lock on a resource.

        Args:
            resource: Resource object or resource ID
            lock_duration: Lock duration in seconds (default 5 minutes)
            client_id: Client identifier (auto-generated if not provided)

        Returns:
            bool: True if lock was acquired, False otherwise
        """
        if client_id:
            self._client_id = client_id
        resource = self._unwrap(resource)
        resource_id = (
            resource.resource_id if isinstance(resource, Resource) else resource
        )

        if self.url:
            response = requests.post(
                f"{self.url}/resource/{resource_id}/lock",
                params={
                    "lock_duration": lock_duration,
                    "client_id": self._client_id,
                },
                timeout=10,
            )
            response.raise_for_status()
            if response.status_code == 200 and response.json():
                locked_resource_data = response.json()
                locked_resource = Resource.discriminate(locked_resource_data)
                locked_resource.resource_url = (
                    f"{self.url}/resource/{locked_resource.resource_id}"
                )

                self.logger.log_info(
                    f"Acquired lock on resource {resource_id} for client {locked_resource.locked_by}"
                )
                return self._wrap_resource(locked_resource)
            self.logger.log_warning(
                f"Failed to acquire lock on resource {resource_id} for client {self._client_id}"
            )
            return None
        # Local-only mode implementation
        if resource_id not in self.local_resources:
            self.logger.log_warning(
                f"Resource {resource_id} not found in local resources"
            )
            return None

        # Simple local locking - just mark as locked
        local_resource = self.local_resources[resource_id]
        try:
            if local_resource.locked_by and local_resource.locked_by != self._client_id:
                self.logger.log_warning(
                    f"Resource {resource_id} already locked by {local_resource.locked_by}"
                )
                return None
        except AttributeError:
            # locked_by doesn't exist, so resource is not locked
            pass

        # Set lock info
        local_resource.locked_by = self._client_id
        local_resource.locked_until = datetime.now() + timedelta(seconds=lock_duration)

        self.logger.log_info(f"Acquired local lock on resource {resource_id}")
        return self._wrap_resource(local_resource)

    def release_lock(
        self,
        resource: Union[str, ResourceDataModels],
        client_id: Optional[str] = None,
    ) -> bool:
        """
        Release a lock on a resource.

        Args:
            resource: Resource object or resource ID
            client_id: Client identifier

        Returns:
            bool: True if lock was released, False otherwise
        """
        if client_id:
            self._client_id = client_id
        resource = self._unwrap(resource)
        resource_id = (
            resource.resource_id if isinstance(resource, Resource) else resource
        )

        if self.url:
            try:
                response = requests.delete(
                    f"{self.url}/resource/{resource_id}/unlock",
                    params={"client_id": self._client_id} if self._client_id else {},
                    timeout=10,
                )
                response.raise_for_status()
                if response.status_code == 200 and response.json():
                    unlocked_resource_data = response.json()
                    unlocked_resource = Resource.discriminate(unlocked_resource_data)
                    unlocked_resource.resource_url = (
                        f"{self.url}/resource/{unlocked_resource.resource_id}"
                    )

                    self.logger.log_info(
                        f"Released lock on resource {resource_id} for client {self._client_id}"
                    )
                    return self._wrap_resource(unlocked_resource)

            except requests.HTTPError as e:
                if e.response.status_code == 403:
                    self.logger.log_warning(
                        f"Access denied: {e.response.json().get('detail', str(e))}"
                    )
                    return None
                self.logger.log_error(f"Error releasing lock: {e}")
                raise e
        else:
            # Local-only mode implementation
            if resource_id not in self.local_resources:
                self.logger.log_warning(
                    f"Resource {resource_id} not found in local resources"
                )
                return None

            local_resource = self.local_resources[resource_id]

            # Check if locked by this client
            try:
                if (
                    local_resource.locked_by
                    and self._client_id
                    and local_resource.locked_by != self._client_id
                ):
                    self.logger.log_warning(
                        f"Cannot release lock on {resource_id}: not owned by {self._client_id}"
                    )
                    return None
            except AttributeError:
                # locked_by doesn't exist, so nothing to release
                pass

            # Release lock
            local_resource.locked_by = None
            local_resource.locked_until = None

            self.logger.log_info(f"Released local lock on resource {resource_id}")
            return self._wrap_resource(local_resource)

    def is_locked(
        self,
        resource: Union[str, ResourceDataModels],
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a resource is currently locked.

        Args:
            resource: Resource object or resource ID

        Returns:
            tuple[bool, Optional[str]]: (is_locked, locked_by)
        """
        resource = self._unwrap(resource)
        resource_id = (
            resource.resource_id if isinstance(resource, Resource) else resource
        )

        if self.url:
            response = requests.get(
                f"{self.url}/resource/{resource_id}/check_lock",
                timeout=10,
            )
            response.raise_for_status()
            result = response.json()
            return result["is_locked"], result["locked_by"]
        # Local-only mode implementation
        if resource_id not in self.local_resources:
            return False, None

        local_resource = self.local_resources[resource_id]

        # Check if locked and not expired
        if hasattr(local_resource, "locked_by") and local_resource.locked_by:
            if hasattr(local_resource, "locked_until") and local_resource.locked_until:
                if datetime.now() < local_resource.locked_until:
                    return True, local_resource.locked_by
                # Lock expired, clean it up
                local_resource.locked_by = None
                local_resource.locked_until = None
                return False, None
            # Locked but no expiration time
            return True, local_resource.locked_by

        return False, None

    def lock(
        self,
        *resources: Union[str, ResourceDataModels],
        lock_duration: float = 300.0,
        auto_refresh: bool = True,
        client_id: Optional[str] = None,
    ) -> Generator[
        Union[ResourceDataModels, tuple[ResourceDataModels, ...]], None, None
    ]:
        """
        Create a context manager for locking multiple resources.

        Args:
            *resources: Resources to lock (can be Resource objects or IDs)
            lock_duration: Lock duration in seconds
            auto_refresh: Whether to refresh resources on entry/exit
            client_id: Client identifier (auto-generated if not provided)

        Returns:
            Context manager that yields locked resources

        Usage:
            with client.lock(stack1, child1) as (stack, child):
                stack.push(child)
        """

        @contextmanager
        def lock_manager() -> Generator[
            Union[ResourceDataModels, tuple[ResourceDataModels, ...]], None, None
        ]:
            """Inner context manager that handles the actual locking logic."""

            # Generate client ID if not provided
            if client_id:
                self._client_id = client_id
            locked_resources = []
            try:
                # Phase 1: Acquire all locks
                locked_resources = self._acquire_all_locks(
                    resources, lock_duration, auto_refresh, self._client_id
                )

                # Phase 2: Yield the locked resources
                if len(locked_resources) == 1:
                    yield locked_resources[0]
                else:
                    yield tuple(locked_resources)

            finally:
                # Phase 3: Release all locks
                self._release_all_locks(locked_resources, auto_refresh, self._client_id)

        return lock_manager()

    def _acquire_all_locks(
        self,
        resources: tuple[Union[str, ResourceDataModels], ...],
        lock_duration: float,
        auto_refresh: bool,
        client_id: str,
    ) -> list[ResourceDataModels]:
        """
        Acquire locks on all resources.

        Returns:
            list[ResourceDataModels]: List of successfully locked resources

        Raises:
            ValueError: If any lock acquisition fails
        """
        locked_resources = []

        for resource in resources:
            try:
                current_resource = self._prepare_resource_for_locking(
                    resource, auto_refresh
                )
                locked_resource = self._acquire_single_lock(
                    current_resource, lock_duration, client_id
                )
                locked_resources.append(locked_resource)

            except Exception as e:
                # Clean up any locks we did acquire
                self._cleanup_failed_locks(locked_resources, client_id)
                resource_id = getattr(resource, "resource_id", resource)
                raise ValueError(
                    f"Failed to acquire lock on resource {resource_id}"
                ) from e

        return locked_resources

    def _prepare_resource_for_locking(
        self, resource: Union[str, ResourceDataModels], auto_refresh: bool
    ) -> ResourceDataModels:
        """Prepare a resource for locking by refreshing if needed."""
        if not auto_refresh:
            return resource

        if isinstance(resource, str):
            return self.get_resource(resource)
        return self.update_resource(resource)

    def _acquire_single_lock(
        self,
        resource: ResourceDataModels,
        lock_duration: float,
        client_id: str,
    ) -> ResourceDataModels:
        """
        Acquire a lock on a single resource.

        Returns:
            ResourceDataModels: The locked resource

        Raises:
            ValueError: If lock acquisition fails
        """
        locked_resource = self.acquire_lock(
            resource, lock_duration=lock_duration, client_id=client_id
        )

        if locked_resource is None:
            resource_id = getattr(resource, "resource_id", resource)
            raise ValueError(f"Failed to acquire lock on resource {resource_id}")

        return locked_resource

    def _cleanup_failed_locks(
        self, locked_resources: list[ResourceDataModels], client_id: str
    ) -> None:
        """Clean up locks that were acquired before a failure occurred."""
        for locked_res in locked_resources:
            try:
                self.release_lock(locked_res, client_id=client_id)
            except Exception as cleanup_error:
                self.logger.error(f"Error cleaning up lock: {cleanup_error}")

    def _release_all_locks(
        self,
        locked_resources: list[ResourceDataModels],
        auto_refresh: bool,
        client_id: str,
    ) -> None:
        """Release all acquired locks and optionally refresh resources."""
        for locked_resource in locked_resources:
            try:
                if auto_refresh:
                    self._refresh_before_release(locked_resource)

                self.release_lock(locked_resource, client_id=client_id)

            except Exception as e:
                self.logger.error(f"Error releasing lock on resource: {e}")

    def _refresh_before_release(self, locked_resource: ResourceDataModels) -> None:
        """Refresh a resource before releasing its lock."""
        try:
            if hasattr(locked_resource, "_resource"):  # It's wrapped
                refreshed = self.update_resource(locked_resource._resource)
                # Update the wrapped resource with fresh data
                locked_resource._update_wrapped_resource(refreshed._resource)
            else:
                # It's not wrapped, refresh it
                self.update_resource(locked_resource)
        except Exception as refresh_error:
            self.logger.error(
                f"Error refreshing resource before release: {refresh_error}"
            )
