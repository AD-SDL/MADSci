Module madsci.common.db_handlers.mongo_handler
==============================================
MongoDB handler abstraction.

Provides an ABC for MongoDB database access and two implementations:
- PyMongoHandler: wraps a real pymongo Database
- InMemoryMongoHandler: wraps InMemoryMongoClient for testing

Classes
-------

`InMemoryMongoHandler(database: Optional[Any] = None, database_name: str = 'test')`
:   MongoDB handler backed by in-memory collections for testing.
    
    Usage::
    
        handler = InMemoryMongoHandler()
        collection = handler.get_collection("events")
        collection.insert_one({"key": "value"})
    
    Initialize with an optional InMemoryDatabase.
    
    Args:
        database: An existing ``InMemoryDatabase`` instance.
            If not provided, a new ``InMemoryMongoClient`` is created.
        database_name: Name for the database (used when creating a new client).

    ### Ancestors (in MRO)

    * madsci.common.db_handlers.mongo_handler.MongoHandler
    * abc.ABC

    ### Methods

    `close(self) ‑> None`
    :   No-op for in-memory databases.

    `command(self, cmd: str, **kwargs: Any) ‑> dict[str, typing.Any]`
    :   Execute a database command (only ``ping`` is supported).

    `get_collection(self, name: str) ‑> Any`
    :   Return an InMemoryCollection.

    `list_collection_names(self) ‑> list[str]`
    :   Return collection names from the in-memory database.

    `ping(self) ‑> bool`
    :   Always returns True for in-memory databases.

`MongoHandler()`
:   Abstract interface for MongoDB database access.
    
    Managers use this interface instead of directly depending on
    ``pymongo.Database``, enabling in-memory substitution for tests.

    ### Ancestors (in MRO)

    * abc.ABC

    ### Descendants

    * madsci.common.db_handlers.mongo_handler.InMemoryMongoHandler
    * madsci.common.db_handlers.mongo_handler.PyMongoHandler

    ### Methods

    `close(self) ‑> None`
    :   Release database connections and resources.

    `command(self, cmd: str, **kwargs: Any) ‑> dict[str, typing.Any]`
    :   Execute a database command (e.g. ``ping``).

    `get_collection(self, name: str) ‑> Union[Collection, Any]`
    :   Return a collection-like object for the given name.
        
        The returned object supports the pymongo Collection interface:
        insert_one, find_one, find, update_one, update_many, delete_one,
        delete_many, count_documents, create_index, drop_index, index_information.

    `list_collection_names(self) ‑> list[str]`
    :   Return the names of all collections in the database.

    `ping(self) ‑> bool`
    :   Check connectivity to the database.
        
        Returns:
            True if the database is reachable, False otherwise.

`PyMongoHandler(database: Any)`
:   MongoDB handler backed by a real pymongo connection.
    
    Usage::
    
        handler = PyMongoHandler.from_url("mongodb://localhost:27017", "my_db")
        collection = handler.get_collection("events")
        collection.insert_one({"key": "value"})
    
    Initialize with an existing pymongo Database object.
    
    Args:
        database: A ``pymongo.database.Database`` instance.

    ### Ancestors (in MRO)

    * madsci.common.db_handlers.mongo_handler.MongoHandler
    * abc.ABC

    ### Static methods

    `from_url(url: str, database_name: str) ‑> madsci.common.db_handlers.mongo_handler.PyMongoHandler`
    :   Create a handler by connecting to a MongoDB server.
        
        Args:
            url: MongoDB connection URL.
            database_name: Name of the database to use.
        
        Returns:
            A new PyMongoHandler instance.

    ### Methods

    `close(self) ‑> None`
    :   Close the underlying MongoClient.

    `command(self, cmd: str, **kwargs: Any) ‑> dict[str, typing.Any]`
    :   Execute a database command.

    `get_collection(self, name: str) ‑> Any`
    :   Return a pymongo Collection.

    `list_collection_names(self) ‑> list[str]`
    :   Return collection names from the database.

    `ping(self) ‑> bool`
    :   Ping the MongoDB server.