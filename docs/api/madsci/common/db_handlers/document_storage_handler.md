Module madsci.common.db_handlers.document_storage_handler
=========================================================
MongoDB-compatible document storage handler abstraction.

Provides an ABC for document database access and two implementations:
- PyDocumentStorageHandler: wraps a real pymongo Database (works with MongoDB, FerretDB, etc.)
- InMemoryDocumentStorageHandler: wraps InMemoryMongoClient for testing

Classes
-------

`DocumentStorageHandler()`
:   Abstract interface for MongoDB-compatible document database access.
    
    Managers use this interface instead of directly depending on
    ``pymongo.Database``, enabling in-memory substitution for tests.

    ### Ancestors (in MRO)

    * abc.ABC

    ### Descendants

    * madsci.common.db_handlers.document_storage_handler.InMemoryDocumentStorageHandler
    * madsci.common.db_handlers.document_storage_handler.PyDocumentStorageHandler

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

`InMemoryDocumentStorageHandler(database: Optional[Any] = None, database_name: str = 'test')`
:   Document storage handler backed by in-memory collections for testing.
    
    Usage::
    
        handler = InMemoryDocumentStorageHandler()
        collection = handler.get_collection("events")
        collection.insert_one({"key": "value"})
    
    Initialize with an optional InMemoryDatabase.
    
    Args:
        database: An existing ``InMemoryDatabase`` instance.
            If not provided, a new ``InMemoryMongoClient`` is created.
        database_name: Name for the database (used when creating a new client).

    ### Ancestors (in MRO)

    * madsci.common.db_handlers.document_storage_handler.DocumentStorageHandler
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

`PyDocumentStorageHandler(database: Any)`
:   Document storage handler backed by a real pymongo connection (MongoDB, FerretDB, etc.).
    
    Usage::
    
        handler = PyDocumentStorageHandler.from_url("mongodb://localhost:27017", "my_db")
        collection = handler.get_collection("events")
        collection.insert_one({"key": "value"})
    
    Initialize with an existing pymongo Database object.
    
    Args:
        database: A ``pymongo.database.Database`` instance.

    ### Ancestors (in MRO)

    * madsci.common.db_handlers.document_storage_handler.DocumentStorageHandler
    * abc.ABC

    ### Static methods

    `from_url(url: str, database_name: str) ‑> madsci.common.db_handlers.document_storage_handler.PyDocumentStorageHandler`
    :   Create a handler by connecting to a MongoDB-compatible server.
        
        Args:
            url: MongoDB-compatible connection URL.
            database_name: Name of the database to use.
        
        Returns:
            A new PyDocumentStorageHandler instance.

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
    :   Ping the document database server.