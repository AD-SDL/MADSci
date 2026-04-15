"""Tests for CacheHandler implementations."""

from __future__ import annotations

import pytest
from madsci.common.db_handlers.cache_handler import CacheHandler

# ---------------------------------------------------------------------------
# Parametrized fixture
# ---------------------------------------------------------------------------


@pytest.fixture(
    params=["inmemory"],
)
def cache_handler(request, inmemory_cache_handler):
    """Provide a CacheHandler implementation for testing."""
    if request.param == "inmemory":
        return inmemory_cache_handler
    raise ValueError(f"Unknown handler type: {request.param}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCacheHandlerInterface:
    """Tests that verify any CacheHandler implementation behaves correctly."""

    def test_is_cache_handler(self, cache_handler):
        """Handler must implement CacheHandler ABC."""
        assert isinstance(cache_handler, CacheHandler)

    def test_ping(self, cache_handler):
        """Handler should respond to ping."""
        assert cache_handler.ping() is True

    def test_incr(self, cache_handler):
        """incr should increment and return the new value."""
        val1 = cache_handler.incr("test:counter")
        assert val1 == 1

        val2 = cache_handler.incr("test:counter")
        assert val2 == 2

        val3 = cache_handler.incr("test:counter", 5)
        assert val3 == 7

    def test_get_set(self, cache_handler):
        """get/set should store and retrieve values."""
        cache_handler.set("test:key", "hello")
        assert cache_handler.get("test:key") == "hello"

    def test_get_nonexistent(self, cache_handler):
        """get should return None for nonexistent keys."""
        assert cache_handler.get("test:nonexistent") is None

    def test_create_dict(self, cache_handler):
        """create_dict should return a dict-like object."""
        d = cache_handler.create_dict("test:dict")

        d["key1"] = "value1"
        d["key2"] = "value2"

        assert d["key1"] == "value1"
        assert d["key2"] == "value2"
        assert len(d) == 2
        assert "key1" in d

    def test_create_dict_update_and_clear(self, cache_handler):
        """Dict should support update and clear operations."""
        d = cache_handler.create_dict("test:dict_ops")

        d.update({"a": 1, "b": 2})
        assert len(d) == 2

        d.clear()
        assert len(d) == 0

    def test_create_dict_items(self, cache_handler):
        """Dict should support items() iteration."""
        d = cache_handler.create_dict("test:dict_items")
        d["x"] = "10"
        d["y"] = "20"

        items = dict(d.items())
        assert items["x"] == "10"
        assert items["y"] == "20"

    def test_create_dict_delete(self, cache_handler):
        """Dict should support item deletion."""
        d = cache_handler.create_dict("test:dict_del")
        d["to_delete"] = "value"
        assert "to_delete" in d

        del d["to_delete"]
        assert "to_delete" not in d

    def test_create_list(self, cache_handler):
        """create_list should return a list-like object."""
        lst = cache_handler.create_list("test:list")

        lst.append("item1")
        lst.append("item2")

        assert len(lst) == 2
        assert "item1" in lst
        items = list(lst)
        assert items == ["item1", "item2"]

    def test_create_list_remove(self, cache_handler):
        """List should support remove operation."""
        lst = cache_handler.create_list("test:list_remove")
        lst.append("a")
        lst.append("b")
        lst.append("c")

        lst.remove("b")
        assert len(lst) == 2
        assert "b" not in lst

    def test_create_lock(self, cache_handler):
        """create_lock should return a lock that can be acquired and released."""
        lock = cache_handler.create_lock("test:lock", auto_release_time=10)

        # Context manager usage
        with lock:
            pass  # Lock acquired and released

    def test_create_lock_acquire_release(self, cache_handler):
        """Lock should support explicit acquire/release."""
        lock = cache_handler.create_lock("test:lock_explicit", auto_release_time=10)

        assert lock.acquire() is True
        lock.release()

    def test_dict_shared_state(self, cache_handler):
        """Two dicts with the same key should share state."""
        d1 = cache_handler.create_dict("test:shared")
        d2 = cache_handler.create_dict("test:shared")

        d1["shared_key"] = "shared_value"
        assert d2["shared_key"] == "shared_value"


# ---------------------------------------------------------------------------
# Integration tests (require Docker)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestCacheHandlerIntegration:
    """Tests that run against a real Redis/Valkey container."""

    @pytest.fixture(autouse=True)
    def _setup(self, real_cache_handler):
        self.handler = real_cache_handler

    def test_ping(self):
        """Real cache server should respond to ping."""
        assert self.handler.ping() is True

    def test_incr_and_get(self):
        """Basic incr/get should work against real cache server."""
        val = self.handler.incr("int_test:counter")
        assert val >= 1

    def test_set_get(self):
        """set/get should work against real cache server."""
        self.handler.set("int_test:key", "value")
        assert self.handler.get("int_test:key") == "value"
