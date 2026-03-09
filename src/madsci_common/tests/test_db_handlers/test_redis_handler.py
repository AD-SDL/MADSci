"""Tests for RedisHandler implementations."""

from __future__ import annotations

import pytest
from madsci.common.db_handlers.redis_handler import RedisHandler

# ---------------------------------------------------------------------------
# Parametrized fixture
# ---------------------------------------------------------------------------


@pytest.fixture(
    params=["inmemory"],
)
def redis_handler(request, inmemory_redis_handler):
    """Provide a RedisHandler implementation for testing."""
    if request.param == "inmemory":
        return inmemory_redis_handler
    raise ValueError(f"Unknown handler type: {request.param}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRedisHandlerInterface:
    """Tests that verify any RedisHandler implementation behaves correctly."""

    def test_is_redis_handler(self, redis_handler):
        """Handler must implement RedisHandler ABC."""
        assert isinstance(redis_handler, RedisHandler)

    def test_ping(self, redis_handler):
        """Handler should respond to ping."""
        assert redis_handler.ping() is True

    def test_incr(self, redis_handler):
        """incr should increment and return the new value."""
        val1 = redis_handler.incr("test:counter")
        assert val1 == 1

        val2 = redis_handler.incr("test:counter")
        assert val2 == 2

        val3 = redis_handler.incr("test:counter", 5)
        assert val3 == 7

    def test_get_set(self, redis_handler):
        """get/set should store and retrieve values."""
        redis_handler.set("test:key", "hello")
        assert redis_handler.get("test:key") == "hello"

    def test_get_nonexistent(self, redis_handler):
        """get should return None for nonexistent keys."""
        assert redis_handler.get("test:nonexistent") is None

    def test_create_dict(self, redis_handler):
        """create_dict should return a dict-like object."""
        d = redis_handler.create_dict("test:dict")

        d["key1"] = "value1"
        d["key2"] = "value2"

        assert d["key1"] == "value1"
        assert d["key2"] == "value2"
        assert len(d) == 2
        assert "key1" in d

    def test_create_dict_update_and_clear(self, redis_handler):
        """Dict should support update and clear operations."""
        d = redis_handler.create_dict("test:dict_ops")

        d.update({"a": 1, "b": 2})
        assert len(d) == 2

        d.clear()
        assert len(d) == 0

    def test_create_dict_items(self, redis_handler):
        """Dict should support items() iteration."""
        d = redis_handler.create_dict("test:dict_items")
        d["x"] = "10"
        d["y"] = "20"

        items = dict(d.items())
        assert items["x"] == "10"
        assert items["y"] == "20"

    def test_create_dict_delete(self, redis_handler):
        """Dict should support item deletion."""
        d = redis_handler.create_dict("test:dict_del")
        d["to_delete"] = "value"
        assert "to_delete" in d

        del d["to_delete"]
        assert "to_delete" not in d

    def test_create_list(self, redis_handler):
        """create_list should return a list-like object."""
        lst = redis_handler.create_list("test:list")

        lst.append("item1")
        lst.append("item2")

        assert len(lst) == 2
        assert "item1" in lst
        items = list(lst)
        assert items == ["item1", "item2"]

    def test_create_list_remove(self, redis_handler):
        """List should support remove operation."""
        lst = redis_handler.create_list("test:list_remove")
        lst.append("a")
        lst.append("b")
        lst.append("c")

        lst.remove("b")
        assert len(lst) == 2
        assert "b" not in lst

    def test_create_lock(self, redis_handler):
        """create_lock should return a lock that can be acquired and released."""
        lock = redis_handler.create_lock("test:lock", auto_release_time=10)

        # Context manager usage
        with lock:
            pass  # Lock acquired and released

    def test_create_lock_acquire_release(self, redis_handler):
        """Lock should support explicit acquire/release."""
        lock = redis_handler.create_lock("test:lock_explicit", auto_release_time=10)

        assert lock.acquire() is True
        lock.release()

    def test_dict_shared_state(self, redis_handler):
        """Two dicts with the same key should share state."""
        d1 = redis_handler.create_dict("test:shared")
        d2 = redis_handler.create_dict("test:shared")

        d1["shared_key"] = "shared_value"
        assert d2["shared_key"] == "shared_value"


# ---------------------------------------------------------------------------
# Integration tests (require Docker)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestRedisHandlerIntegration:
    """Tests that run against a real Redis container."""

    @pytest.fixture(autouse=True)
    def _setup(self, real_redis_handler):
        self.handler = real_redis_handler

    def test_ping(self):
        """Real Redis should respond to ping."""
        assert self.handler.ping() is True

    def test_incr_and_get(self):
        """Basic incr/get should work against real Redis."""
        val = self.handler.incr("int_test:counter")
        assert val >= 1

    def test_set_get(self):
        """set/get should work against real Redis."""
        self.handler.set("int_test:key", "value")
        assert self.handler.get("int_test:key") == "value"
