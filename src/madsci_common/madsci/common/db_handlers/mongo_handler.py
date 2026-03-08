"""MongoDB handler abstraction.

Provides an ABC for MongoDB database access and two implementations:
- PyMongoHandler: wraps a real pymongo Database
- InMemoryMongoHandler: wraps InMemoryMongoClient for testing
"""

from __future__ import annotations

import contextlib
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional, Union

if TYPE_CHECKING:
    from pymongo.collection import Collection


class MongoHandler(ABC):
    """Abstract interface for MongoDB database access.

    Managers use this interface instead of directly depending on
    ``pymongo.Database``, enabling in-memory substitution for tests.
    """

    @abstractmethod
    def get_collection(self, name: str) -> Union[Collection, Any]:
        """Return a collection-like object for the given name.

        The returned object supports the pymongo Collection interface:
        insert_one, find_one, find, update_one, update_many, delete_one,
        delete_many, count_documents, create_index, drop_index, index_information.
        """

    @abstractmethod
    def ping(self) -> bool:
        """Check connectivity to the database.

        Returns:
            True if the database is reachable, False otherwise.
        """

    @abstractmethod
    def close(self) -> None:
        """Release database connections and resources."""

    @abstractmethod
    def list_collection_names(self) -> list[str]:
        """Return the names of all collections in the database."""

    @abstractmethod
    def command(self, cmd: str, **kwargs: Any) -> dict[str, Any]:
        """Execute a database command (e.g. ``ping``)."""


class PyMongoHandler(MongoHandler):
    """MongoDB handler backed by a real pymongo connection.

    Usage::

        handler = PyMongoHandler.from_url("mongodb://localhost:27017", "my_db")
        collection = handler.get_collection("events")
        collection.insert_one({"key": "value"})
    """

    def __init__(self, database: Any) -> None:
        """Initialize with an existing pymongo Database object.

        Args:
            database: A ``pymongo.database.Database`` instance.
        """
        self._database = database

    @classmethod
    def from_url(cls, url: str, database_name: str) -> PyMongoHandler:
        """Create a handler by connecting to a MongoDB server.

        Args:
            url: MongoDB connection URL.
            database_name: Name of the database to use.

        Returns:
            A new PyMongoHandler instance.
        """
        from pymongo import MongoClient  # noqa: PLC0415

        client = MongoClient(str(url))
        return cls(client[database_name])

    def get_collection(self, name: str) -> Any:
        """Return a pymongo Collection."""
        return self._database[name]

    def ping(self) -> bool:
        """Ping the MongoDB server."""
        try:
            self._database.client.admin.command("ping")
            return True
        except Exception:
            return False

    def close(self) -> None:
        """Close the underlying MongoClient."""
        with contextlib.suppress(Exception):
            self._database.client.close()

    def list_collection_names(self) -> list[str]:
        """Return collection names from the database."""
        return self._database.list_collection_names()

    def command(self, cmd: str, **kwargs: Any) -> dict[str, Any]:
        """Execute a database command."""
        return self._database.command(cmd, **kwargs)


class InMemoryMongoHandler(MongoHandler):
    """MongoDB handler backed by in-memory collections for testing.

    Usage::

        handler = InMemoryMongoHandler()
        collection = handler.get_collection("events")
        collection.insert_one({"key": "value"})
    """

    def __init__(
        self,
        database: Optional[Any] = None,
        database_name: str = "test",
    ) -> None:
        """Initialize with an optional InMemoryDatabase.

        Args:
            database: An existing ``InMemoryDatabase`` instance.
                If not provided, a new ``InMemoryMongoClient`` is created.
            database_name: Name for the database (used when creating a new client).
        """
        if database is not None:
            self._client = None
            self._database = database
        else:
            from madsci.common.local_backends.inmemory_collection import (  # noqa: PLC0415
                InMemoryMongoClient,
            )

            self._client = InMemoryMongoClient()
            self._database = self._client[database_name]

    def get_collection(self, name: str) -> Any:
        """Return an InMemoryCollection."""
        return self._database[name]

    def ping(self) -> bool:
        """Always returns True for in-memory databases."""
        return True

    def close(self) -> None:
        """No-op for in-memory databases."""

    def list_collection_names(self) -> list[str]:
        """Return collection names from the in-memory database."""
        return self._database.list_collection_names()

    def command(self, cmd: str, **kwargs: Any) -> dict[str, Any]:
        """Execute a database command (only ``ping`` is supported)."""
        return self._database.command(cmd, **kwargs)
