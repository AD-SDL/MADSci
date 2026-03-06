"""Tests for in-memory MongoDB drop-in replacements."""

from __future__ import annotations

from madsci.common.local_backends.inmemory_collection import (
    InMemoryCollection,
    InMemoryDatabase,
    InMemoryMongoClient,
)

# ── InMemoryCollection ───────────────────────────────────────────────────


class TestInsertAndFindOne:
    def test_insert_and_find_one(self):
        col = InMemoryCollection("test")
        col.insert_one({"_id": "1", "name": "Alice", "age": 30})
        doc = col.find_one({"_id": "1"})
        assert doc is not None
        assert doc["name"] == "Alice"

    def test_find_one_no_match(self):
        col = InMemoryCollection("test")
        assert col.find_one({"_id": "nonexistent"}) is None

    def test_find_one_empty_filter(self):
        col = InMemoryCollection("test")
        col.insert_one({"_id": "1", "name": "Alice"})
        doc = col.find_one()
        assert doc is not None

    def test_insert_returns_result(self):
        col = InMemoryCollection("test")
        result = col.insert_one({"_id": "abc", "data": True})
        assert result.inserted_id == "abc"

    def test_deep_copy_isolation(self):
        """Inserted documents should be copies, not references."""
        col = InMemoryCollection("test")
        original = {"_id": "1", "nested": {"a": 1}}
        col.insert_one(original)
        original["nested"]["a"] = 999
        doc = col.find_one({"_id": "1"})
        assert doc["nested"]["a"] == 1


class TestFind:
    def test_find_all(self):
        col = InMemoryCollection("test")
        col.insert_one({"_id": "1", "type": "a"})
        col.insert_one({"_id": "2", "type": "b"})
        col.insert_one({"_id": "3", "type": "a"})
        results = col.find({"type": "a"}).to_list()
        assert len(results) == 2

    def test_find_empty_filter(self):
        col = InMemoryCollection("test")
        col.insert_one({"_id": "1"})
        col.insert_one({"_id": "2"})
        results = col.find().to_list()
        assert len(results) == 2

    def test_find_no_matches(self):
        col = InMemoryCollection("test")
        col.insert_one({"_id": "1", "status": "active"})
        results = col.find({"status": "deleted"}).to_list()
        assert len(results) == 0


class TestCursorChaining:
    def test_sort_ascending(self):
        col = InMemoryCollection("test")
        col.insert_one({"_id": "1", "val": 3})
        col.insert_one({"_id": "2", "val": 1})
        col.insert_one({"_id": "3", "val": 2})
        results = col.find().sort("val", 1).to_list()
        assert [d["val"] for d in results] == [1, 2, 3]

    def test_sort_descending(self):
        col = InMemoryCollection("test")
        col.insert_one({"_id": "1", "val": 3})
        col.insert_one({"_id": "2", "val": 1})
        col.insert_one({"_id": "3", "val": 2})
        results = col.find().sort("val", -1).to_list()
        assert [d["val"] for d in results] == [3, 2, 1]

    def test_sort_with_tuple_list(self):
        """pymongo-style sort with [(field, direction)] list."""
        col = InMemoryCollection("test")
        col.insert_one({"_id": "1", "ts": 3})
        col.insert_one({"_id": "2", "ts": 1})
        results = col.find().sort([("ts", -1)]).to_list()
        assert results[0]["ts"] == 3

    def test_skip(self):
        col = InMemoryCollection("test")
        for i in range(5):
            col.insert_one({"_id": str(i), "val": i})
        results = col.find().sort("val", 1).skip(2).to_list()
        assert [d["val"] for d in results] == [2, 3, 4]

    def test_limit(self):
        col = InMemoryCollection("test")
        for i in range(5):
            col.insert_one({"_id": str(i), "val": i})
        results = col.find().sort("val", 1).limit(3).to_list()
        assert len(results) == 3
        assert [d["val"] for d in results] == [0, 1, 2]

    def test_sort_skip_limit(self):
        col = InMemoryCollection("test")
        for i in range(10):
            col.insert_one({"_id": str(i), "val": i})
        results = col.find().sort("val", -1).skip(2).limit(3).to_list()
        assert [d["val"] for d in results] == [7, 6, 5]

    def test_cursor_iter(self):
        col = InMemoryCollection("test")
        col.insert_one({"_id": "1", "val": 1})
        col.insert_one({"_id": "2", "val": 2})
        vals = [d["val"] for d in col.find()]
        assert sorted(vals) == [1, 2]


class TestQueryOperators:
    def test_gte(self):
        col = InMemoryCollection("test")
        col.insert_one({"_id": "1", "val": 5})
        col.insert_one({"_id": "2", "val": 10})
        col.insert_one({"_id": "3", "val": 15})
        results = col.find({"val": {"$gte": 10}}).to_list()
        assert len(results) == 2

    def test_gt(self):
        col = InMemoryCollection("test")
        col.insert_one({"_id": "1", "val": 5})
        col.insert_one({"_id": "2", "val": 10})
        results = col.find({"val": {"$gt": 5}}).to_list()
        assert len(results) == 1

    def test_lt(self):
        col = InMemoryCollection("test")
        col.insert_one({"_id": "1", "val": 5})
        col.insert_one({"_id": "2", "val": 10})
        results = col.find({"val": {"$lt": 10}}).to_list()
        assert len(results) == 1

    def test_lte(self):
        col = InMemoryCollection("test")
        col.insert_one({"_id": "1", "val": 5})
        col.insert_one({"_id": "2", "val": 10})
        results = col.find({"val": {"$lte": 10}}).to_list()
        assert len(results) == 2

    def test_ne(self):
        col = InMemoryCollection("test")
        col.insert_one({"_id": "1", "status": "active"})
        col.insert_one({"_id": "2", "status": "deleted"})
        results = col.find({"status": {"$ne": "deleted"}}).to_list()
        assert len(results) == 1

    def test_in(self):
        col = InMemoryCollection("test")
        col.insert_one({"_id": "1", "status": "active"})
        col.insert_one({"_id": "2", "status": "deleted"})
        col.insert_one({"_id": "3", "status": "pending"})
        results = col.find({"status": {"$in": ["active", "pending"]}}).to_list()
        assert len(results) == 2

    def test_combined_operators(self):
        col = InMemoryCollection("test")
        col.insert_one({"_id": "1", "val": 5})
        col.insert_one({"_id": "2", "val": 10})
        col.insert_one({"_id": "3", "val": 15})
        results = col.find({"val": {"$gte": 5, "$lt": 15}}).to_list()
        assert len(results) == 2

    def test_nested_field_query(self):
        col = InMemoryCollection("test")
        col.insert_one({"_id": "1", "data": {"level": 1}})
        col.insert_one({"_id": "2", "data": {"level": 2}})
        results = col.find({"data.level": 1}).to_list()
        assert len(results) == 1


class TestUpdateOperations:
    def test_update_one_set(self):
        col = InMemoryCollection("test")
        col.insert_one({"_id": "1", "name": "Alice", "age": 30})
        result = col.update_one({"_id": "1"}, {"$set": {"age": 31}})
        assert result.matched_count == 1
        assert result.modified_count == 1
        doc = col.find_one({"_id": "1"})
        assert doc["age"] == 31
        assert doc["name"] == "Alice"

    def test_update_one_no_match(self):
        col = InMemoryCollection("test")
        result = col.update_one({"_id": "missing"}, {"$set": {"age": 99}})
        assert result.matched_count == 0

    def test_update_many(self):
        col = InMemoryCollection("test")
        col.insert_one({"_id": "1", "archived": False})
        col.insert_one({"_id": "2", "archived": False})
        col.insert_one({"_id": "3", "archived": True})
        result = col.update_many(
            {"archived": False},
            {"$set": {"archived": True}},
        )
        assert result.matched_count == 2
        assert col.count_documents({"archived": True}) == 3

    def test_update_nested_field(self):
        col = InMemoryCollection("test")
        col.insert_one({"_id": "1", "meta": {"version": 1}})
        col.update_one({"_id": "1"}, {"$set": {"meta.version": 2}})
        doc = col.find_one({"_id": "1"})
        assert doc["meta"]["version"] == 2

    def test_update_with_in_operator(self):
        """Matches the pattern used by EventManager.archive_events."""
        col = InMemoryCollection("test")
        col.insert_one({"_id": "a", "archived": False})
        col.insert_one({"_id": "b", "archived": False})
        col.insert_one({"_id": "c", "archived": False})
        result = col.update_many(
            {"_id": {"$in": ["a", "b"]}},
            {"$set": {"archived": True}},
        )
        assert result.matched_count == 2
        assert col.find_one({"_id": "c"})["archived"] is False


class TestDeleteOperations:
    def test_delete_one(self):
        col = InMemoryCollection("test")
        col.insert_one({"_id": "1", "name": "Alice"})
        result = col.delete_one({"_id": "1"})
        assert result.deleted_count == 1
        assert col.find_one({"_id": "1"}) is None

    def test_delete_one_no_match(self):
        col = InMemoryCollection("test")
        result = col.delete_one({"_id": "missing"})
        assert result.deleted_count == 0

    def test_delete_many(self):
        col = InMemoryCollection("test")
        col.insert_one({"_id": "1", "status": "old"})
        col.insert_one({"_id": "2", "status": "old"})
        col.insert_one({"_id": "3", "status": "new"})
        result = col.delete_many({"status": "old"})
        assert result.deleted_count == 2
        assert col.count_documents({}) == 1

    def test_delete_many_with_operators(self):
        """Matches the EventManager.purge_events pattern."""
        col = InMemoryCollection("test")
        col.insert_one({"_id": "1", "archived": True, "archived_at": 100})
        col.insert_one({"_id": "2", "archived": True, "archived_at": 200})
        col.insert_one({"_id": "3", "archived": False})
        result = col.delete_many({"archived": True, "archived_at": {"$lt": 150}})
        assert result.deleted_count == 1
        assert col.count_documents({}) == 2


class TestCountDocuments:
    def test_count_all(self):
        col = InMemoryCollection("test")
        col.insert_one({"_id": "1"})
        col.insert_one({"_id": "2"})
        assert col.count_documents({}) == 2

    def test_count_filtered(self):
        col = InMemoryCollection("test")
        col.insert_one({"_id": "1", "type": "a"})
        col.insert_one({"_id": "2", "type": "b"})
        col.insert_one({"_id": "3", "type": "a"})
        assert col.count_documents({"type": "a"}) == 2

    def test_count_empty(self):
        col = InMemoryCollection("test")
        assert col.count_documents({}) == 0


class TestIndexOperations:
    def test_create_index(self):
        col = InMemoryCollection("test")
        name = col.create_index("event_timestamp")
        assert name == "event_timestamp_1"
        assert name in col.index_information()

    def test_create_compound_index(self):
        col = InMemoryCollection("test")
        name = col.create_index([("archived", 1), ("archived_at", 1)])
        assert name == "archived_1_archived_at_1"

    def test_drop_index(self):
        col = InMemoryCollection("test")
        name = col.create_index("ts")
        col.drop_index(name)
        assert name not in col.index_information()

    def test_create_index_with_kwargs(self):
        col = InMemoryCollection("test")
        name = col.create_index("archived_at", expireAfterSeconds=3600, name="ttl_idx")
        assert name == "ttl_idx"
        info = col.index_information()
        assert info["ttl_idx"]["expireAfterSeconds"] == 3600


# ── InMemoryDatabase ─────────────────────────────────────────────────────


class TestInMemoryDatabase:
    def test_getitem_returns_collection(self):
        db = InMemoryDatabase("testdb")
        col = db["events"]
        assert isinstance(col, InMemoryCollection)
        assert col.name == "events"

    def test_same_name_returns_same_collection(self):
        db = InMemoryDatabase("testdb")
        assert db["events"] is db["events"]

    def test_command_ping(self):
        db = InMemoryDatabase("testdb")
        result = db.command("ping")
        assert result == {"ok": 1}


# ── InMemoryMongoClient ─────────────────────────────────────────────────


class TestInMemoryMongoClient:
    def test_getitem_returns_database(self):
        client = InMemoryMongoClient()
        db = client["mydb"]
        assert isinstance(db, InMemoryDatabase)

    def test_same_name_returns_same_db(self):
        client = InMemoryMongoClient()
        assert client["mydb"] is client["mydb"]

    def test_admin_ping(self):
        client = InMemoryMongoClient()
        result = client.admin.command("ping")
        assert result == {"ok": 1}

    def test_context_manager(self):
        with InMemoryMongoClient() as client:
            db = client["test"]
            col = db["items"]
            col.insert_one({"_id": "1"})
            assert col.find_one({"_id": "1"}) is not None

    def test_full_workflow(self):
        """End-to-end test matching how managers use pymongo."""
        client = InMemoryMongoClient()
        db = client["experiments"]
        experiments = db["experiments"]

        # Insert
        experiments.insert_one(
            {"_id": "exp-1", "status": "running", "started_at": 1000}
        )
        experiments.insert_one(
            {"_id": "exp-2", "status": "completed", "started_at": 900}
        )
        experiments.insert_one(
            {"_id": "exp-3", "status": "running", "started_at": 1100}
        )

        # Count
        assert experiments.count_documents({}) == 3

        # Find with sort and limit
        latest = experiments.find().sort("started_at", -1).limit(2).to_list()
        assert len(latest) == 2
        assert latest[0]["_id"] == "exp-3"

        # Update
        experiments.update_one({"_id": "exp-1"}, {"$set": {"status": "completed"}})
        doc = experiments.find_one({"_id": "exp-1"})
        assert doc["status"] == "completed"

        # Delete
        experiments.delete_one({"_id": "exp-2"})
        assert experiments.count_documents({}) == 2
