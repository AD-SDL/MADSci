"""In-memory drop-in replacements for pymongo Collection, Database, and MongoClient.

These classes mirror the pymongo interfaces used by Event, Experiment, Data, and
Workcell managers, enabling the MADSci stack to run without a MongoDB server.

Usage::

    client = InMemoryMongoClient()
    db = client["my_database"]
    collection = db["events"]
    collection.insert_one({"_id": "1", "name": "test"})
    doc = collection.find_one({"_id": "1"})
"""

from __future__ import annotations

import copy
import re
import threading
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


class InMemoryInsertResult:
    """Mimics ``pymongo.results.InsertOneResult``."""

    def __init__(self, inserted_id: Any) -> None:
        """Initialize with the inserted document's ID."""
        self.inserted_id = inserted_id


class InMemoryUpdateResult:
    """Mimics ``pymongo.results.UpdateResult``."""

    def __init__(self, matched_count: int = 0, modified_count: int = 0) -> None:
        """Initialize with match and modification counts."""
        self.matched_count = matched_count
        self.modified_count = modified_count


class InMemoryDeleteResult:
    """Mimics ``pymongo.results.DeleteResult``."""

    def __init__(self, deleted_count: int = 0) -> None:
        """Initialize with the deletion count."""
        self.deleted_count = deleted_count


# ---------------------------------------------------------------------------
# Cursor
# ---------------------------------------------------------------------------


class InMemoryCursor:
    """Mimics ``pymongo.cursor.Cursor`` with sort/skip/limit/to_list chaining."""

    def __init__(
        self,
        documents: list[dict[str, Any]],
        projection: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize with a list of documents to iterate over."""
        self._documents = documents
        self._projection = projection
        self._sort_key: Optional[str] = None
        self._sort_direction: int = 1
        self._skip_count: int = 0
        self._limit_count: int = 0

    def sort(self, key: Any, direction: int = 1) -> InMemoryCursor:
        """Sort results.  Accepts a string key or list of (key, direction) tuples."""
        if isinstance(key, list):
            # pymongo accepts [(field, direction), ...] — use the first one.
            key, direction = key[0]
        self._sort_key = key
        self._sort_direction = direction
        return self

    def skip(self, count: int) -> InMemoryCursor:
        """Skip the first *count* results."""
        self._skip_count = count
        return self

    def limit(self, count: int) -> InMemoryCursor:
        """Limit the number of results returned."""
        self._limit_count = count
        return self

    def _resolve(self) -> list[dict[str, Any]]:
        docs = list(self._documents)
        if self._sort_key is not None:
            docs.sort(
                key=lambda d: _nested_get(d, self._sort_key, ""),
                reverse=(self._sort_direction == -1),
            )
        if self._skip_count:
            docs = docs[self._skip_count :]
        if self._limit_count:
            docs = docs[: self._limit_count]
        if self._projection:
            docs = [_apply_projection(d, self._projection) for d in docs]
        return docs

    def to_list(self, length: Optional[int] = None) -> list[dict[str, Any]]:
        """Materialise the cursor to a list."""
        resolved = self._resolve()
        if length is not None:
            return resolved[:length]
        return resolved

    def __iter__(self):  # noqa: ANN204
        """Iterate over resolved documents."""
        return iter(self._resolve())

    def __next__(self) -> dict[str, Any]:
        """Not supported directly; use ``iter()`` or ``to_list()``."""
        raise NotImplementedError("Use iter() or to_list()")


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------


class InMemoryCollection:
    """Drop-in replacement for ``pymongo.collection.Collection``.

    Supports: ``insert_one``, ``find_one``, ``find``, ``update_one``,
    ``update_many``, ``replace_one``, ``delete_one``, ``delete_many``,
    ``count_documents``, ``create_index``, ``drop_index``, ``index_information``.
    """

    def __init__(self, name: str) -> None:
        """Initialize a named in-memory collection."""
        self.name = name
        self._documents: list[dict[str, Any]] = []
        self._indexes: dict[str, Any] = {}
        self._lock = threading.Lock()

    # --- Write operations ---

    def insert_one(self, document: dict[str, Any]) -> InMemoryInsertResult:
        """Insert a single document and return the result.

        Raises ``pymongo.errors.DuplicateKeyError`` if the document violates
        a unique index constraint.
        """
        doc = copy.deepcopy(document)
        with self._lock:
            self._check_unique_constraints(doc)
            self._documents.append(doc)
        return InMemoryInsertResult(doc.get("_id"))

    def _check_unique_constraints(self, doc: dict[str, Any]) -> None:
        """Check unique index constraints for a document (must hold self._lock)."""
        for index_name, index_info in self._indexes.items():
            if not index_info.get("unique", False):
                continue
            key = index_info.get("key")
            if key is None:
                continue
            # key can be a string field name or list of (field, direction) tuples
            if isinstance(key, str):
                fields = [key]
            elif isinstance(key, list):
                fields = [f for f, _ in key]
            else:
                continue
            # Get the values for the indexed fields from the new document
            new_values = tuple(doc.get(f) for f in fields)
            # Check against existing documents
            for existing in self._documents:
                existing_values = tuple(existing.get(f) for f in fields)
                if new_values == existing_values and all(
                    v is not None for v in new_values
                ):
                    from pymongo.errors import DuplicateKeyError  # noqa: PLC0415

                    raise DuplicateKeyError(
                        f"E11000 duplicate key error collection: index: {index_name} dup key: {dict(zip(fields, new_values, strict=True))}"
                    )

    def update_one(
        self, filter_query: dict[str, Any], update: dict[str, Any]
    ) -> InMemoryUpdateResult:
        """Update the first document matching the filter."""
        with self._lock:
            for doc in self._documents:
                if _matches(doc, filter_query):
                    _apply_update(doc, update)
                    return InMemoryUpdateResult(matched_count=1, modified_count=1)
        return InMemoryUpdateResult()

    def update_many(
        self, filter_query: dict[str, Any], update: dict[str, Any]
    ) -> InMemoryUpdateResult:
        """Update all documents matching the filter."""
        matched = 0
        with self._lock:
            for doc in self._documents:
                if _matches(doc, filter_query):
                    _apply_update(doc, update)
                    matched += 1
        return InMemoryUpdateResult(matched_count=matched, modified_count=matched)

    def replace_one(
        self, filter_query: dict[str, Any], replacement: dict[str, Any]
    ) -> InMemoryUpdateResult:
        """Replace the first document matching the filter with a new document.

        The ``_id`` field of the original document is preserved.
        """
        replacement = copy.deepcopy(replacement)
        with self._lock:
            for i, doc in enumerate(self._documents):
                if _matches(doc, filter_query):
                    doc_id = doc.get("_id")
                    self._documents[i] = replacement
                    if doc_id is not None and "_id" not in replacement:
                        self._documents[i]["_id"] = doc_id
                    return InMemoryUpdateResult(matched_count=1, modified_count=1)
        return InMemoryUpdateResult()

    def delete_one(self, filter_query: dict[str, Any]) -> InMemoryDeleteResult:
        """Delete the first document matching the filter."""
        with self._lock:
            for i, doc in enumerate(self._documents):
                if _matches(doc, filter_query):
                    self._documents.pop(i)
                    return InMemoryDeleteResult(deleted_count=1)
        return InMemoryDeleteResult()

    def delete_many(self, filter_query: dict[str, Any]) -> InMemoryDeleteResult:
        """Delete all documents matching the filter."""
        with self._lock:
            before = len(self._documents)
            self._documents = [
                d for d in self._documents if not _matches(d, filter_query)
            ]
            return InMemoryDeleteResult(deleted_count=before - len(self._documents))

    # --- Read operations ---

    def find_one(
        self,
        filter_query: Optional[dict[str, Any]] = None,
        projection: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        """Return the first document matching the filter, or ``None``.

        Args:
            filter_query: MongoDB-style query filter.
            projection: Optional field projection (e.g. ``{"_id": 1}``
                for inclusion or ``{"field": 0}`` for exclusion).
        """
        filter_query = filter_query or {}
        with self._lock:
            for doc in self._documents:
                if _matches(doc, filter_query):
                    result = copy.deepcopy(doc)
                    if projection:
                        return _apply_projection(result, projection)
                    return result
        return None

    def find(
        self,
        filter_query: Optional[dict[str, Any]] = None,
        projection: Optional[dict[str, Any]] = None,
    ) -> InMemoryCursor:
        """Return a cursor over documents matching the filter.

        Args:
            filter_query: MongoDB-style query filter.
            projection: Optional field projection passed to the cursor.
        """
        filter_query = filter_query or {}
        with self._lock:
            matched = [
                copy.deepcopy(d) for d in self._documents if _matches(d, filter_query)
            ]
        return InMemoryCursor(matched, projection=projection)

    def count_documents(self, filter_query: Optional[dict[str, Any]] = None) -> int:
        """Count documents matching the filter."""
        filter_query = filter_query or {}
        with self._lock:
            return sum(1 for d in self._documents if _matches(d, filter_query))

    # --- Index operations (no-ops for in-memory) ---

    def create_index(self, keys: Any, **kwargs: Any) -> str:
        """Create an index (no-op for in-memory; records metadata only)."""
        name = kwargs.get("name") or _index_name(keys)
        self._indexes[name] = {"key": keys, **kwargs}
        return name

    def drop_index(self, name: str) -> None:
        """Remove an index by name."""
        self._indexes.pop(name, None)

    def index_information(self) -> dict[str, Any]:
        """Return metadata for all indexes."""
        return dict(self._indexes)

    def list_indexes(self) -> list[dict[str, Any]]:
        """Return a list of index info dicts, matching pymongo's ``Collection.list_indexes()``."""
        result: list[dict[str, Any]] = []
        for name, info in self._indexes.items():
            entry = dict(info)
            entry["name"] = name
            result.append(entry)
        return result


# ---------------------------------------------------------------------------
# Database & Client
# ---------------------------------------------------------------------------


class InMemoryDatabase:
    """Drop-in replacement for ``pymongo.database.Database``.

    Access collections via ``db["collection_name"]``.
    """

    def __init__(
        self,
        name: str = "test",
        client: Optional[InMemoryMongoClient] = None,
    ) -> None:
        """Initialize a named in-memory database."""
        self.name = name
        self._client = client
        self._collections: dict[str, InMemoryCollection] = {}
        self._lock = threading.Lock()

    @property
    def client(self) -> InMemoryMongoClient:
        """Return the parent ``InMemoryMongoClient``.

        Mirrors ``pymongo.database.Database.client``, used by health checks
        like ``db.client.admin.command("ping")``.
        """
        if self._client is None:
            # Create a standalone client if none was provided.
            self._client = InMemoryMongoClient()
        return self._client

    def __getitem__(self, collection_name: str) -> InMemoryCollection:
        """Get or create a collection by name."""
        with self._lock:
            if collection_name not in self._collections:
                self._collections[collection_name] = InMemoryCollection(collection_name)
            return self._collections[collection_name]

    def list_collection_names(self) -> list[str]:
        """Return the names of all collections that have been created."""
        with self._lock:
            return list(self._collections.keys())

    def create_collection(self, name: str) -> InMemoryCollection:
        """Explicitly create a collection.

        If the collection already exists, returns the existing one.
        """
        return self[name]

    def drop_collection(self, name: str) -> None:
        """Drop a collection by name, removing all its data."""
        with self._lock:
            self._collections.pop(name, None)

    def command(self, cmd: str, **_kwargs: Any) -> dict[str, Any]:
        """Execute a database command (only ``ping`` is supported)."""
        if cmd == "ping":
            return {"ok": 1}
        return {"ok": 1}


class InMemoryMongoClient:
    """Drop-in replacement for ``pymongo.MongoClient``.

    Access databases via ``client["database_name"]``.
    Provides ``client.admin.command("ping")`` for health checks.
    """

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        """Initialize the in-memory Mongo client."""
        self._databases: dict[str, InMemoryDatabase] = {}
        self._lock = threading.Lock()
        self.admin = InMemoryDatabase("admin", client=self)

    def __getitem__(self, db_name: str) -> InMemoryDatabase:
        """Get or create a database by name."""
        with self._lock:
            if db_name not in self._databases:
                self._databases[db_name] = InMemoryDatabase(db_name, client=self)
            return self._databases[db_name]

    def __enter__(self) -> InMemoryMongoClient:
        """Enter the context manager."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Exit the context manager (no-op)."""

    def close(self) -> None:
        """Close the client (no-op for in-memory)."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _nested_get(doc: dict[str, Any], key: str, default: Any = None) -> Any:
    """Get a value from a nested dict using dot-separated keys (e.g. ``"event_data.test"``)."""
    parts = key.split(".")
    current: Any = doc
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part, default)
        else:
            return default
    return current


def _nested_set(doc: dict[str, Any], key: str, value: Any) -> None:
    """Set a value in a nested dict using dot-separated keys."""
    parts = key.split(".")
    current = doc
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def _matches(doc: dict[str, Any], query: dict[str, Any]) -> bool:
    """Check if a document matches a MongoDB-style query filter."""
    for key, condition in query.items():
        doc_val = _nested_get(doc, key)
        if isinstance(condition, dict):
            # Operator query: {"field": {"$gte": 10, "$lt": 20}}
            for op, op_val in condition.items():
                if not _apply_operator(doc_val, op, op_val):
                    return False
        elif isinstance(condition, re.Pattern):
            if doc_val is None or not condition.search(str(doc_val)):
                return False
        # Exact match
        elif doc_val != condition:
            return False
    return True


_COMPARISON_OPS: dict[str, Any] = {
    "$eq": lambda d, v: d == v,
    "$ne": lambda d, v: d != v,
    "$gt": lambda d, v: d is not None and d > v,
    "$gte": lambda d, v: d is not None and d >= v,
    "$lt": lambda d, v: d is not None and d < v,
    "$lte": lambda d, v: d is not None and d <= v,
    "$in": lambda d, v: d in v,
    "$nin": lambda d, v: d not in v,
    "$exists": lambda d, v: (d is not None) == v,
}


def _apply_operator(doc_val: Any, op: str, op_val: Any) -> bool:
    """Evaluate a single MongoDB comparison operator."""
    fn = _COMPARISON_OPS.get(op)
    if fn is not None:
        return fn(doc_val, op_val)
    # Unknown or no-op operators (e.g. $set at condition level)
    return True


def _apply_update(doc: dict[str, Any], update: dict[str, Any]) -> None:
    """Apply MongoDB-style update operators to a document."""
    if "$set" in update:
        for key, value in update["$set"].items():
            _nested_set(doc, key, value)
    if "$unset" in update:
        _apply_unset(doc, update["$unset"])
    if "$inc" in update:
        for key, value in update["$inc"].items():
            current = _nested_get(doc, key, 0)
            _nested_set(doc, key, current + value)
    # If no operators, treat as a full replacement (keeping _id).
    if not any(k.startswith("$") for k in update):
        doc_id = doc.get("_id")
        doc.clear()
        doc.update(update)
        if doc_id is not None:
            doc["_id"] = doc_id


def _apply_unset(doc: dict[str, Any], fields: Any) -> None:
    """Remove fields specified by ``$unset``."""
    for key in fields:
        parts = key.split(".")
        current = doc
        for part in parts[:-1]:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                break
        else:
            if isinstance(current, dict):
                current.pop(parts[-1], None)


def _apply_projection(
    doc: dict[str, Any], projection: dict[str, Any]
) -> dict[str, Any]:
    """Apply a MongoDB-style field projection to a document.

    Supports inclusion (``{"field": 1}``) and exclusion (``{"field": 0}``)
    projections.  ``_id`` is included by default in inclusion projections
    unless explicitly excluded.
    """
    if not projection:
        return doc

    # Determine if this is an inclusion or exclusion projection.
    # MongoDB does not allow mixing (except _id exclusion in inclusion mode).
    include_fields = {k for k, v in projection.items() if v and k != "_id"}
    exclude_fields = {k for k, v in projection.items() if not v and k != "_id"}

    # Check if any non-_id field has a truthy value (inclusion mode)
    is_inclusion = bool(include_fields) or (
        "_id" in projection and projection["_id"] and not exclude_fields
    )

    if is_inclusion:
        # Inclusion projection: only keep specified fields (+ _id by default)
        result: dict[str, Any] = {}
        if projection.get("_id", 1) and "_id" in doc:
            result["_id"] = doc["_id"]
        for field in include_fields:
            val = _nested_get(doc, field)
            if val is not None:
                result[field] = val
        return result

    # Exclusion projection: keep everything except specified fields
    result = dict(doc)
    for field in exclude_fields:
        result.pop(field, None)
    if "_id" in projection and not projection["_id"]:
        result.pop("_id", None)
    return result


def _index_name(keys: Any) -> str:
    """Generate an index name from a key specification."""
    if isinstance(keys, str):
        return f"{keys}_1"
    if isinstance(keys, list):
        parts = []
        for item in keys:
            if isinstance(item, tuple):
                parts.append(f"{item[0]}_{item[1]}")
            else:
                parts.append(f"{item}_1")
        return "_".join(parts)
    return str(keys)
