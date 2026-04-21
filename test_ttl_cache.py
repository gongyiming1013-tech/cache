"""Test suite for TTLLRUCache and ThreadSafeTTLLRUCache (V2)."""

import threading
import time
from unittest.mock import patch

import pytest

from lru_cache import (
    CacheMissError,
    CacheStats,
    InvalidCapacityError,
    ThreadSafeTTLLRUCache,
    TTLLRUCache,
    TTLNode,
)


# --- TTLNode ---

class TestTTLNode:
    """Tests for TTLNode expiration logic."""

    def test_no_ttl_never_expires(self) -> None:
        node = TTLNode(1, 10)
        assert not node.is_expired()

    def test_expired_node(self) -> None:
        node = TTLNode(1, 10, expires_at=time.monotonic() - 1.0)
        assert node.is_expired()

    def test_not_yet_expired(self) -> None:
        node = TTLNode(1, 10, expires_at=time.monotonic() + 1000.0)
        assert not node.is_expired()


# --- CacheStats ---

class TestCacheStats:
    """Tests for the CacheStats dataclass."""

    def test_defaults_are_zero(self) -> None:
        stats = CacheStats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.expirations == 0

    def test_reset(self) -> None:
        stats = CacheStats(hits=5, misses=3, evictions=2, expirations=1)
        stats.reset()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.expirations == 0


# --- TTLLRUCache Error Handling ---

class TestTTLCacheInvalidCapacity:
    """Capacity validation."""

    def test_zero_capacity_raises(self) -> None:
        with pytest.raises(InvalidCapacityError):
            TTLLRUCache(0)

    def test_negative_capacity_raises(self) -> None:
        with pytest.raises(InvalidCapacityError):
            TTLLRUCache(-1)


# --- TTLLRUCache Core Functionality ---

class TestTTLCacheBasic:
    """Basic get/put without TTL — behaves like LRUCache."""

    def test_put_and_get(self) -> None:
        cache = TTLLRUCache(2)
        cache.put(1, 10)
        assert cache.get(1) == 10

    def test_get_missing_raises(self) -> None:
        cache = TTLLRUCache(2)
        with pytest.raises(CacheMissError):
            cache.get(99)

    def test_update_existing(self) -> None:
        cache = TTLLRUCache(2)
        cache.put(1, 10)
        cache.put(1, 20)
        assert cache.get(1) == 20

    def test_eviction_without_ttl(self) -> None:
        cache = TTLLRUCache(2)
        cache.put(1, 10)
        cache.put(2, 20)
        cache.put(3, 30)  # evicts 1
        with pytest.raises(CacheMissError):
            cache.get(1)
        assert cache.stats.evictions == 1

    def test_get_promotes_to_mru(self) -> None:
        cache = TTLLRUCache(2)
        cache.put(1, 10)
        cache.put(2, 20)
        cache.get(1)       # promote 1
        cache.put(3, 30)   # evicts 2
        with pytest.raises(CacheMissError):
            cache.get(2)
        assert cache.get(1) == 10


# --- TTL Expiration ---

class TestTTLExpiration:
    """Tests for per-entry TTL expiration."""

    def test_entry_expires_after_ttl(self) -> None:
        cache = TTLLRUCache(5)
        # Set a TTL that has already elapsed
        cache.put(1, 10, ttl=0.0)
        # monotonic time will have advanced by the time get is called
        time.sleep(0.01)
        with pytest.raises(CacheMissError):
            cache.get(1)
        assert cache.stats.expirations == 1
        assert cache.stats.misses == 1

    def test_entry_not_expired_yet(self) -> None:
        cache = TTLLRUCache(5)
        cache.put(1, 10, ttl=100.0)
        assert cache.get(1) == 10
        assert cache.stats.hits == 1

    def test_expired_entry_does_not_block_new_insert(self) -> None:
        cache = TTLLRUCache(2)
        cache.put(1, 10, ttl=0.0)
        time.sleep(0.01)
        cache.put(2, 20)
        cache.put(3, 30)  # should evict expired key 1 first, not key 2
        assert cache.get(2) == 20
        assert cache.get(3) == 30
        assert cache.stats.expirations == 1
        assert cache.stats.evictions == 0

    def test_update_resets_ttl(self) -> None:
        cache = TTLLRUCache(5)
        cache.put(1, 10, ttl=0.0)
        # Update with no TTL — should clear expiration
        cache.put(1, 20)
        assert cache.get(1) == 20

    def test_mixed_ttl_and_no_ttl(self) -> None:
        cache = TTLLRUCache(3)
        cache.put(1, 10)              # no TTL
        cache.put(2, 20, ttl=0.0)     # expires immediately
        cache.put(3, 30)              # no TTL
        time.sleep(0.01)
        with pytest.raises(CacheMissError):
            cache.get(2)
        assert cache.get(1) == 10
        assert cache.get(3) == 30


# --- Capacity + TTL Interaction ---

class TestCapacityTTLInteraction:
    """Expired entries should be preferred for eviction over live entries."""

    def test_expired_evicted_before_live(self) -> None:
        cache = TTLLRUCache(2)
        cache.put(1, 10, ttl=0.0)  # will expire
        cache.put(2, 20)           # live
        time.sleep(0.01)
        cache.put(3, 30)           # triggers eviction — should prefer expired key 1
        assert cache.get(2) == 20
        assert cache.get(3) == 30
        assert cache.stats.expirations == 1
        assert cache.stats.evictions == 0

    def test_lru_evicted_when_no_expired(self) -> None:
        cache = TTLLRUCache(2)
        cache.put(1, 10)
        cache.put(2, 20)
        cache.put(3, 30)  # evicts LRU key 1
        with pytest.raises(CacheMissError):
            cache.get(1)
        assert cache.stats.evictions == 1
        assert cache.stats.expirations == 0

    def test_capacity_maintained_with_mixed_entries(self) -> None:
        cache = TTLLRUCache(3)
        cache.put(1, 10, ttl=0.0)
        cache.put(2, 20, ttl=0.0)
        cache.put(3, 30)
        time.sleep(0.01)
        cache.put(4, 40)  # evicts an expired entry
        cache.put(5, 50)  # evicts another expired entry
        # All 3 live entries should be accessible
        assert cache.get(3) == 30
        assert cache.get(4) == 40
        assert cache.get(5) == 50


# --- Observability ---

class TestObservability:
    """Hit/miss/eviction/expiration counters."""

    def test_hit_counter(self) -> None:
        cache = TTLLRUCache(5)
        cache.put(1, 10)
        cache.get(1)
        cache.get(1)
        assert cache.stats.hits == 2

    def test_miss_counter(self) -> None:
        cache = TTLLRUCache(5)
        for _ in range(3):
            with pytest.raises(CacheMissError):
                cache.get(99)
        assert cache.stats.misses == 3

    def test_eviction_counter(self) -> None:
        cache = TTLLRUCache(1)
        cache.put(1, 10)
        cache.put(2, 20)  # evicts 1
        cache.put(3, 30)  # evicts 2
        assert cache.stats.evictions == 2

    def test_expiration_counter(self) -> None:
        cache = TTLLRUCache(5)
        cache.put(1, 10, ttl=0.0)
        cache.put(2, 20, ttl=0.0)
        time.sleep(0.01)
        with pytest.raises(CacheMissError):
            cache.get(1)
        with pytest.raises(CacheMissError):
            cache.get(2)
        assert cache.stats.expirations == 2

    def test_stats_reset(self) -> None:
        cache = TTLLRUCache(5)
        cache.put(1, 10)
        cache.get(1)
        with pytest.raises(CacheMissError):
            cache.get(99)
        cache.stats.reset()
        assert cache.stats.hits == 0
        assert cache.stats.misses == 0


# --- ThreadSafeTTLLRUCache ---

class TestThreadSafeTTLBasic:
    """Single-threaded sanity for the thread-safe wrapper."""

    def test_put_and_get(self) -> None:
        cache = ThreadSafeTTLLRUCache(5)
        cache.put(1, 10, ttl=100.0)
        assert cache.get(1) == 10

    def test_stats_accessible(self) -> None:
        cache = ThreadSafeTTLLRUCache(5)
        cache.put(1, 10)
        cache.get(1)
        assert cache.stats.hits == 1

    def test_zero_capacity_raises(self) -> None:
        with pytest.raises(InvalidCapacityError):
            ThreadSafeTTLLRUCache(0)


class TestThreadSafeTTLConcurrency:
    """Concurrent access with TTL entries."""

    def test_concurrent_ttl_no_crash(self) -> None:
        cache = ThreadSafeTTLLRUCache(20)
        errors: list[Exception] = []

        def writer(wid: int) -> None:
            try:
                for i in range(200):
                    ttl = 0.001 if i % 3 == 0 else None
                    cache.put(wid * 1000 + i, i, ttl=ttl)
            except Exception as exc:
                errors.append(exc)

        def reader() -> None:
            try:
                for i in range(500):
                    try:
                        cache.get(i % 50)
                    except CacheMissError:
                        pass
            except Exception as exc:
                errors.append(exc)

        threads = (
            [threading.Thread(target=writer, args=(w,)) for w in range(5)]
            + [threading.Thread(target=reader) for _ in range(5)]
        )
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors

    def test_stress_no_deadlock(self) -> None:
        cache = ThreadSafeTTLLRUCache(10)
        errors: list[Exception] = []

        def worker(wid: int) -> None:
            try:
                for i in range(300):
                    key = (wid * 300 + i) % 30
                    cache.put(key, i, ttl=0.01 if i % 5 == 0 else None)
                    try:
                        cache.get(key)
                    except CacheMissError:
                        pass
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(w,)) for w in range(15)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
