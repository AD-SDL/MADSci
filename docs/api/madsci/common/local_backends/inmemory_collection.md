Module madsci.common.local_backends.inmemory_collection
=======================================================
In-memory drop-in replacements for pymongo Collection, Database, and MongoClient.

These classes mirror the pymongo interfaces used by Event, Experiment, Data, and
Workcell managers, enabling the MADSci stack to run without a MongoDB server.

Usage::

    client = InMemoryMongoClient()
    db = client["my_database"]
    collection = db["events"]
    collection.insert_one({"_id": "1", "name": "test"})
    doc = collection.find_one({"_id": "1"})

Classes
-------

`InMemoryCollection(name: str)`
:   Drop-in replacement for ``pymongo.collection.Collection``.
    
    Supports: ``insert_one``, ``find_one``, ``find``, ``update_one``,
    ``update_many``, ``delete_one``, ``delete_many``, ``count_documents``,
    ``create_index``, ``drop_index``, ``index_information``.
    
    Initialize a named in-memory collection.

    ### Methods

    `count_documents(self, filter_query: Optional[dict[str, Any]] = None) ‑> int`
    :   Count documents matching the filter.

    `create_index(self, keys: Any, **kwargs: Any) ‑> str`
    :   Create an index (no-op for in-memory; records metadata only).

    `delete_many(self, filter_query: dict[str, Any]) ‑> madsci.common.local_backends.inmemory_collection.InMemoryDeleteResult`
    :   Delete all documents matching the filter.

    `delete_one(self, filter_query: dict[str, Any]) ‑> madsci.common.local_backends.inmemory_collection.InMemoryDeleteResult`
    :   Delete the first document matching the filter.

    `drop_index(self, name: str) ‑> None`
    :   Remove an index by name.

    `find(self, filter_query: Optional[dict[str, Any]] = None) ‑> madsci.common.local_backends.inmemory_collection.InMemoryCursor`
    :   Return a cursor over documents matching the filter.

    `find_one(self, filter_query: Optional[dict[str, Any]] = None) ‑> dict[str, typing.Any] | None`
    :   Return the first document matching the filter, or ``None``.

    `index_information(self) ‑> dict[str, typing.Any]`
    :   Return metadata for all indexes.

    `insert_one(self, document: dict[str, Any]) ‑> madsci.common.local_backends.inmemory_collection.InMemoryInsertResult`
    :   Insert a single document and return the result.

    `update_many(self, filter_query: dict[str, Any], update: dict[str, Any]) ‑> madsci.common.local_backends.inmemory_collection.InMemoryUpdateResult`
    :   Update all documents matching the filter.

    `update_one(self, filter_query: dict[str, Any], update: dict[str, Any]) ‑> madsci.common.local_backends.inmemory_collection.InMemoryUpdateResult`
    :   Update the first document matching the filter.

`InMemoryCursor(documents: list[dict[str, Any]])`
:   Mimics ``pymongo.cursor.Cursor`` with sort/skip/limit/to_list chaining.
    
    Initialize with a list of documents to iterate over.

    ### Methods

    `limit(self, count: int) ‑> madsci.common.local_backends.inmemory_collection.InMemoryCursor`
    :   Limit the number of results returned.

    `skip(self, count: int) ‑> madsci.common.local_backends.inmemory_collection.InMemoryCursor`
    :   Skip the first *count* results.

    `sort(self, key: Any, direction: int = 1) ‑> madsci.common.local_backends.inmemory_collection.InMemoryCursor`
    :   Sort results.  Accepts a string key or list of (key, direction) tuples.

    `to_list(self, length: Optional[int] = None) ‑> list[dict[str, typing.Any]]`
    :   Materialise the cursor to a list.

`InMemoryDatabase(name: str = 'test')`
:   Drop-in replacement for ``pymongo.database.Database``.
    
    Access collections via ``db["collection_name"]``.
    
    Initialize a named in-memory database.

    ### Methods

    `command(self, cmd: str, **_kwargs: Any) ‑> dict[str, typing.Any]`
    :   Execute a database command (only ``ping`` is supported).

`InMemoryDeleteResult(deleted_count: int = 0)`
:   Mimics ``pymongo.results.DeleteResult``.
    
    Initialize with the deletion count.

`InMemoryInsertResult(inserted_id: Any)`
:   Mimics ``pymongo.results.InsertOneResult``.
    
    Initialize with the inserted document's ID.

`InMemoryMongoClient(*_args: Any, **_kwargs: Any)`
:   Drop-in replacement for ``pymongo.MongoClient``.
    
    Access databases via ``client["database_name"]``.
    Provides ``client.admin.command("ping")`` for health checks.
    
    Initialize the in-memory Mongo client.

    ### Methods

    `close(self) ‑> None`
    :   Close the client (no-op for in-memory).

`InMemoryUpdateResult(matched_count: int = 0, modified_count: int = 0)`
:   Mimics ``pymongo.results.UpdateResult``.
    
    Initialize with match and modification counts.