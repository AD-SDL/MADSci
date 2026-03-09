"""Tests for MongoHandler implementations."""

from __future__ import annotations

import pytest
from madsci.common.db_handlers.mongo_handler import MongoHandler

# ---------------------------------------------------------------------------
# Parametrized fixture: runs each test against all available implementations
# ---------------------------------------------------------------------------


@pytest.fixture(
    params=["inmemory"],
)
def mongo_handler(request, inmemory_mongo_handler):
    """Provide a MongoHandler implementation for testing."""
    if request.param == "inmemory":
        return inmemory_mongo_handler
    raise ValueError(f"Unknown handler type: {request.param}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMongoHandlerInterface:
    """Tests that verify any MongoHandler implementation behaves correctly."""

    def test_is_mongo_handler(self, mongo_handler):
        """Handler must implement MongoHandler ABC."""
        assert isinstance(mongo_handler, MongoHandler)

    def test_ping(self, mongo_handler):
        """Handler should respond to ping."""
        assert mongo_handler.ping() is True

    def test_get_collection(self, mongo_handler):
        """get_collection should return a collection-like object."""
        coll = mongo_handler.get_collection("test_collection")
        assert coll is not None
        assert coll.name == "test_collection"

    def test_insert_and_find_one(self, mongo_handler):
        """Insert a document and retrieve it."""
        coll = mongo_handler.get_collection("test_insert")
        coll.insert_one({"_id": "doc1", "name": "test", "value": 42})

        doc = coll.find_one({"_id": "doc1"})
        assert doc is not None
        assert doc["name"] == "test"
        assert doc["value"] == 42

    def test_find_one_not_found(self, mongo_handler):
        """find_one should return None for non-existent documents."""
        coll = mongo_handler.get_collection("test_find_none")
        assert coll.find_one({"_id": "nonexistent"}) is None

    def test_find_multiple(self, mongo_handler):
        """find should return all matching documents."""
        coll = mongo_handler.get_collection("test_find_multi")
        coll.insert_one({"_id": "a", "type": "alpha", "val": 1})
        coll.insert_one({"_id": "b", "type": "beta", "val": 2})
        coll.insert_one({"_id": "c", "type": "alpha", "val": 3})

        results = coll.find({"type": "alpha"}).to_list()
        assert len(results) == 2
        ids = {r["_id"] for r in results}
        assert ids == {"a", "c"}

    def test_find_with_sort(self, mongo_handler):
        """find should support sorting."""
        coll = mongo_handler.get_collection("test_sort")
        coll.insert_one({"_id": "1", "order": 3})
        coll.insert_one({"_id": "2", "order": 1})
        coll.insert_one({"_id": "3", "order": 2})

        results = coll.find({}).sort("order", 1).to_list()
        assert [r["order"] for r in results] == [1, 2, 3]

    def test_find_with_skip_and_limit(self, mongo_handler):
        """find should support skip and limit."""
        coll = mongo_handler.get_collection("test_skip_limit")
        for i in range(5):
            coll.insert_one({"_id": str(i), "order": i})

        results = coll.find({}).sort("order", 1).skip(1).limit(2).to_list()
        assert len(results) == 2
        assert results[0]["order"] == 1
        assert results[1]["order"] == 2

    def test_find_with_projection(self, mongo_handler):
        """find should support field projection."""
        coll = mongo_handler.get_collection("test_projection")
        coll.insert_one({"_id": "doc1", "name": "test", "secret": "hidden"})

        # Inclusion projection
        results = coll.find({"_id": "doc1"}, {"_id": 1}).to_list()
        assert len(results) == 1
        assert results[0]["_id"] == "doc1"
        assert "name" not in results[0]

    def test_find_one_with_projection(self, mongo_handler):
        """find_one should support field projection."""
        coll = mongo_handler.get_collection("test_find_one_proj")
        coll.insert_one({"_id": "doc1", "name": "test", "value": 42})

        doc = coll.find_one({"_id": "doc1"}, {"name": 1})
        assert doc is not None
        assert doc["name"] == "test"
        assert "value" not in doc

    def test_update_one(self, mongo_handler):
        """update_one should modify the first matching document."""
        coll = mongo_handler.get_collection("test_update")
        coll.insert_one({"_id": "u1", "status": "new"})

        result = coll.update_one({"_id": "u1"}, {"$set": {"status": "done"}})
        assert result.matched_count == 1
        assert result.modified_count == 1

        doc = coll.find_one({"_id": "u1"})
        assert doc["status"] == "done"

    def test_update_many(self, mongo_handler):
        """update_many should modify all matching documents."""
        coll = mongo_handler.get_collection("test_update_many")
        coll.insert_one({"_id": "m1", "type": "x", "done": False})
        coll.insert_one({"_id": "m2", "type": "x", "done": False})
        coll.insert_one({"_id": "m3", "type": "y", "done": False})

        result = coll.update_many({"type": "x"}, {"$set": {"done": True}})
        assert result.matched_count == 2

        assert coll.find_one({"_id": "m1"})["done"] is True
        assert coll.find_one({"_id": "m3"})["done"] is False

    def test_replace_one(self, mongo_handler):
        """replace_one should replace the entire document (keeping _id)."""
        coll = mongo_handler.get_collection("test_replace")
        coll.insert_one({"_id": "r1", "old_field": "old_value"})

        result = coll.replace_one({"_id": "r1"}, {"new_field": "new_value"})
        assert result.matched_count == 1

        doc = coll.find_one({"_id": "r1"})
        assert doc is not None
        assert doc["_id"] == "r1"
        assert "old_field" not in doc
        assert doc["new_field"] == "new_value"

    def test_delete_one(self, mongo_handler):
        """delete_one should remove a single matching document."""
        coll = mongo_handler.get_collection("test_delete")
        coll.insert_one({"_id": "d1", "val": 1})

        result = coll.delete_one({"_id": "d1"})
        assert result.deleted_count == 1
        assert coll.find_one({"_id": "d1"}) is None

    def test_delete_many(self, mongo_handler):
        """delete_many should remove all matching documents."""
        coll = mongo_handler.get_collection("test_delete_many")
        coll.insert_one({"_id": "dm1", "type": "a"})
        coll.insert_one({"_id": "dm2", "type": "a"})
        coll.insert_one({"_id": "dm3", "type": "b"})

        result = coll.delete_many({"type": "a"})
        assert result.deleted_count == 2
        assert coll.count_documents({}) == 1

    def test_count_documents(self, mongo_handler):
        """count_documents should return correct counts."""
        coll = mongo_handler.get_collection("test_count")
        assert coll.count_documents({}) == 0

        coll.insert_one({"_id": "c1"})
        coll.insert_one({"_id": "c2"})
        assert coll.count_documents({}) == 2

    def test_indexes(self, mongo_handler):
        """Index operations should work without errors."""
        coll = mongo_handler.get_collection("test_indexes")
        name = coll.create_index("field_name")
        assert name is not None

        info = coll.index_information()
        assert len(info) > 0

        coll.drop_index(name)

    def test_list_collection_names(self, mongo_handler):
        """list_collection_names should return created collections."""
        mongo_handler.get_collection("coll_a")
        mongo_handler.get_collection("coll_b")

        names = mongo_handler.list_collection_names()
        assert "coll_a" in names
        assert "coll_b" in names

    def test_command_ping(self, mongo_handler):
        """command("ping") should succeed."""
        result = mongo_handler.command("ping")
        assert result.get("ok") == 1

    def test_query_operators(self, mongo_handler):
        """MongoDB query operators should work."""
        coll = mongo_handler.get_collection("test_operators")
        coll.insert_one({"_id": "op1", "val": 10})
        coll.insert_one({"_id": "op2", "val": 20})
        coll.insert_one({"_id": "op3", "val": 30})

        # $gte
        results = coll.find({"val": {"$gte": 20}}).to_list()
        assert len(results) == 2

        # $in
        results = coll.find({"val": {"$in": [10, 30]}}).to_list()
        assert len(results) == 2

    def test_nested_field_query(self, mongo_handler):
        """Dot-notation queries on nested fields should work."""
        coll = mongo_handler.get_collection("test_nested")
        coll.insert_one({"_id": "n1", "data": {"level": "high"}})
        coll.insert_one({"_id": "n2", "data": {"level": "low"}})

        doc = coll.find_one({"data.level": "high"})
        assert doc is not None
        assert doc["_id"] == "n1"


# ---------------------------------------------------------------------------
# Integration tests (require Docker)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestMongoHandlerIntegration:
    """Tests that run against a real MongoDB container."""

    @pytest.fixture(autouse=True)
    def _setup(self, real_mongo_handler):
        self.handler = real_mongo_handler

    def test_ping(self):
        """Real MongoDB should respond to ping."""
        assert self.handler.ping() is True

    def test_insert_and_find(self):
        """Basic CRUD should work against real MongoDB."""
        coll = self.handler.get_collection("integration_test")
        coll.insert_one({"_id": "int1", "name": "integration"})

        doc = coll.find_one({"_id": "int1"})
        assert doc is not None
        assert doc["name"] == "integration"

        # Cleanup
        coll.delete_many({})

    def test_list_collection_names(self):
        """Real MongoDB should list collections."""
        self.handler.get_collection("int_coll_test")
        names = self.handler.list_collection_names()
        assert isinstance(names, list)
