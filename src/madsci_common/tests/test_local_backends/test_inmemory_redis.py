"""Tests for in-memory Redis drop-in replacements."""

from __future__ import annotations

import threading

import pytest
from madsci.common.local_backends.inmemory_redis import (
    InMemoryRedisClient,
    InMemoryRedisDict,
    InMemoryRedisList,
    InMemoryRedlock,
)

# ── InMemoryRedisClient ──────────────────────────────────────────────────


class TestInMemoryRedisClient:
    def test_ping(self):
        client = InMemoryRedisClient()
        assert client.ping() is True

    def test_incr_new_key(self):
        client = InMemoryRedisClient()
        assert client.incr("counter") == 1
        assert client.incr("counter") == 2

    def test_incr_custom_amount(self):
        client = InMemoryRedisClient()
        assert client.incr("counter", 5) == 5
        assert client.incr("counter", 3) == 8

    def test_get_nonexistent(self):
        client = InMemoryRedisClient()
        assert client.get("missing") is None

    def test_get_after_incr(self):
        client = InMemoryRedisClient()
        client.incr("key")
        assert client.get("key") == "1"

    def test_set_and_get(self):
        client = InMemoryRedisClient()
        client.set("foo", "bar")
        assert client.get("foo") == "bar"

    def test_thread_safety(self):
        """Verify incr is thread-safe."""
        client = InMemoryRedisClient()
        n_threads = 10
        n_increments = 100
        threads = []
        for _ in range(n_threads):
            t = threading.Thread(
                target=lambda: [client.incr("x") for _ in range(n_increments)]
            )
            threads.append(t)
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert int(client.get("x")) == n_threads * n_increments


# ── InMemoryRedisDict ────────────────────────────────────────────────────


class TestInMemoryRedisDict:
    def test_setitem_getitem(self):
        client = InMemoryRedisClient()
        d = InMemoryRedisDict(key="test:dict", redis=client)
        d["a"] = {"value": 1}
        assert d["a"] == {"value": 1}

    def test_delitem(self):
        client = InMemoryRedisClient()
        d = InMemoryRedisDict(key="test:dict:del", redis=client)
        d["a"] = 1
        del d["a"]
        assert "a" not in d

    def test_delitem_missing_raises(self):
        client = InMemoryRedisClient()
        d = InMemoryRedisDict(key="test:dict:delmissing", redis=client)
        with pytest.raises(KeyError):
            del d["nonexistent"]

    def test_contains(self):
        client = InMemoryRedisClient()
        d = InMemoryRedisDict(key="test:dict:contains", redis=client)
        d["x"] = 1
        assert "x" in d
        assert "y" not in d

    def test_iter(self):
        client = InMemoryRedisClient()
        d = InMemoryRedisDict(key="test:dict:iter", redis=client)
        d["a"] = 1
        d["b"] = 2
        keys = list(d)
        assert sorted(keys) == ["a", "b"]

    def test_len(self):
        client = InMemoryRedisClient()
        d = InMemoryRedisDict(key="test:dict:len", redis=client)
        assert len(d) == 0
        d["a"] = 1
        assert len(d) == 1

    def test_get_default(self):
        client = InMemoryRedisClient()
        d = InMemoryRedisDict(key="test:dict:get", redis=client)
        assert d.get("missing") is None
        assert d.get("missing", 42) == 42

    def test_items(self):
        client = InMemoryRedisClient()
        d = InMemoryRedisDict(key="test:dict:items", redis=client)
        d["a"] = 1
        d["b"] = 2
        assert sorted(d.items()) == [("a", 1), ("b", 2)]

    def test_update(self):
        client = InMemoryRedisClient()
        d = InMemoryRedisDict(key="test:dict:update", redis=client)
        d.update(a=1, b=2)
        assert d["a"] == 1
        assert d["b"] == 2

    def test_update_kwargs(self):
        client = InMemoryRedisClient()
        d = InMemoryRedisDict(key="test:dict:update_kw", redis=client)
        d.update(key1="val1", key2="val2")
        assert d["key1"] == "val1"

    def test_clear(self):
        client = InMemoryRedisClient()
        d = InMemoryRedisDict(key="test:dict:clear", redis=client)
        d["a"] = 1
        d.clear()
        assert len(d) == 0

    def test_to_dict(self):
        client = InMemoryRedisClient()
        d = InMemoryRedisDict(key="test:dict:todict", redis=client)
        d["a"] = 1
        d["b"] = 2
        result = d.to_dict()
        assert result == {"a": 1, "b": 2}
        assert isinstance(result, dict)

    def test_shared_storage_same_key(self):
        """Two InMemoryRedisDict with same key and client should share data."""
        client = InMemoryRedisClient()
        d1 = InMemoryRedisDict(key="shared:key", redis=client)
        d2 = InMemoryRedisDict(key="shared:key", redis=client)
        d1["x"] = 42
        assert d2["x"] == 42

    def test_separate_storage_different_key(self):
        """Different keys should NOT share data."""
        client = InMemoryRedisClient()
        d1 = InMemoryRedisDict(key="key1", redis=client)
        d2 = InMemoryRedisDict(key="key2", redis=client)
        d1["x"] = 1
        assert "x" not in d2


# ── InMemoryRedisList ────────────────────────────────────────────────────


class TestInMemoryRedisList:
    def test_append_and_iter(self):
        client = InMemoryRedisClient()
        lst = InMemoryRedisList(key="test:list", redis=client)
        lst.append("a")
        lst.append("b")
        assert list(lst) == ["a", "b"]

    def test_remove(self):
        client = InMemoryRedisClient()
        lst = InMemoryRedisList(key="test:list:remove", redis=client)
        lst.append("a")
        lst.append("b")
        lst.remove("a")
        assert list(lst) == ["b"]

    def test_remove_missing_raises(self):
        client = InMemoryRedisClient()
        lst = InMemoryRedisList(key="test:list:remove_missing", redis=client)
        with pytest.raises(ValueError):
            lst.remove("nonexistent")

    def test_len(self):
        client = InMemoryRedisClient()
        lst = InMemoryRedisList(key="test:list:len", redis=client)
        assert len(lst) == 0
        lst.append("x")
        assert len(lst) == 1

    def test_contains(self):
        client = InMemoryRedisClient()
        lst = InMemoryRedisList(key="test:list:contains", redis=client)
        lst.append("a")
        assert "a" in lst
        assert "b" not in lst

    def test_shared_storage(self):
        """Same key and client → shared list."""
        client = InMemoryRedisClient()
        l1 = InMemoryRedisList(key="shared:list", redis=client)
        l2 = InMemoryRedisList(key="shared:list", redis=client)
        l1.append("x")
        assert "x" in l2


# ── InMemoryRedlock ──────────────────────────────────────────────────────


class TestInMemoryRedlock:
    def test_context_manager(self):
        lock = InMemoryRedlock(key="test:lock", masters={None})
        with lock:
            pass  # Should not raise

    def test_reentrant(self):
        """RLock allows the same thread to acquire multiple times."""
        lock = InMemoryRedlock(key="test:lock:reentrant", masters={None})
        with lock, lock:
            pass  # Should not deadlock

    def test_acquire_release(self):
        lock = InMemoryRedlock(key="test:lock:acq", masters={None})
        assert lock.acquire() is True
        lock.release()

    def test_different_keys_independent(self):
        lock1 = InMemoryRedlock(key="lock:a", masters={None})
        lock2 = InMemoryRedlock(key="lock:b", masters={None})
        lock1.acquire()
        # lock2 should be independently acquirable
        assert lock2.acquire() is True
        lock1.release()
        lock2.release()

    def test_thread_exclusion(self):
        """Verify that the lock provides mutual exclusion across threads."""
        lock = InMemoryRedlock(key="test:lock:excl", masters={None})
        shared = {"counter": 0}
        n_threads = 10
        n_increments = 100

        def work():
            for _ in range(n_increments):
                with lock:
                    val = shared["counter"]
                    shared["counter"] = val + 1

        threads = [threading.Thread(target=work) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert shared["counter"] == n_threads * n_increments
