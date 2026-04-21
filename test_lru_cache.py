"""Test suite for LRU Cache."""

import pytest

from lru_cache import CacheMissError, InvalidCapacityError, LRUCache


# --- Error Handling ---

class TestInvalidCapacity:
    """Tests for invalid capacity validation."""

    def test_zero_capacity_raises(self) -> None:
        with pytest.raises(InvalidCapacityError):
            LRUCache(0)

    def test_negative_capacity_raises(self) -> None:
        with pytest.raises(InvalidCapacityError):
            LRUCache(-1)


# --- Core Functionality ---

class TestGetAndPut:
    """Tests for basic get and put operations."""

    def test_put_and_get_single_item(self) -> None:
        cache = LRUCache(2)
        cache.put(1, 10)
        assert cache.get(1) == 10

    def test_get_missing_key_raises(self) -> None:
        cache = LRUCache(2)
        with pytest.raises(CacheMissError):
            cache.get(99)

    def test_put_updates_existing_key(self) -> None:
        cache = LRUCache(2)
        cache.put(1, 10)
        cache.put(1, 20)
        assert cache.get(1) == 20

    def test_put_multiple_keys(self) -> None:
        cache = LRUCache(3)
        cache.put(1, 10)
        cache.put(2, 20)
        cache.put(3, 30)
        assert cache.get(1) == 10
        assert cache.get(2) == 20
        assert cache.get(3) == 30


# --- Eviction ---

class TestEviction:
    """Tests for LRU eviction policy."""

    def test_evict_least_recent_on_capacity(self) -> None:
        cache = LRUCache(2)
        cache.put(1, 10)
        cache.put(2, 20)
        cache.put(3, 30)  # evicts key 1
        with pytest.raises(CacheMissError):
            cache.get(1)
        assert cache.get(2) == 20
        assert cache.get(3) == 30

    def test_evict_correct_item_after_get_promotes(self) -> None:
        cache = LRUCache(2)
        cache.put(1, 10)
        cache.put(2, 20)
        cache.get(1)      # promotes key 1 to MRU
        cache.put(3, 30)  # evicts key 2 (now LRU)
        with pytest.raises(CacheMissError):
            cache.get(2)
        assert cache.get(1) == 10
        assert cache.get(3) == 30

    def test_evict_correct_item_after_put_update_promotes(self) -> None:
        cache = LRUCache(2)
        cache.put(1, 10)
        cache.put(2, 20)
        cache.put(1, 15)  # updates key 1, promotes to MRU
        cache.put(3, 30)  # evicts key 2 (now LRU)
        with pytest.raises(CacheMissError):
            cache.get(2)
        assert cache.get(1) == 15
        assert cache.get(3) == 30


# --- Edge Cases ---

class TestEdgeCases:
    """Tests for boundary conditions."""

    def test_capacity_of_one(self) -> None:
        cache = LRUCache(1)
        cache.put(1, 10)
        assert cache.get(1) == 10
        cache.put(2, 20)  # evicts key 1
        with pytest.raises(CacheMissError):
            cache.get(1)
        assert cache.get(2) == 20

    def test_get_on_empty_cache_raises(self) -> None:
        cache = LRUCache(5)
        with pytest.raises(CacheMissError):
            cache.get(1)

    def test_put_same_key_repeatedly(self) -> None:
        cache = LRUCache(2)
        for i in range(100):
            cache.put(1, i)
        assert cache.get(1) == 99

    def test_large_number_of_operations(self) -> None:
        cache = LRUCache(100)
        for i in range(1000):
            cache.put(i, i * 10)
        # only the last 100 keys should remain
        for i in range(900):
            with pytest.raises(CacheMissError):
                cache.get(i)
        for i in range(900, 1000):
            assert cache.get(i) == i * 10


# --- Ordering ---

class TestOrdering:
    """Tests for recency tracking correctness."""

    def test_get_moves_item_to_mru(self) -> None:
        cache = LRUCache(3)
        cache.put(1, 10)
        cache.put(2, 20)
        cache.put(3, 30)
        cache.get(1)      # promotes key 1 to MRU; LRU order: 2, 3, 1
        cache.put(4, 40)  # evicts key 2
        with pytest.raises(CacheMissError):
            cache.get(2)
        assert cache.get(1) == 10
        assert cache.get(3) == 30
        assert cache.get(4) == 40

    def test_sequential_evictions_follow_lru_order(self) -> None:
        cache = LRUCache(3)
        cache.put(1, 10)
        cache.put(2, 20)
        cache.put(3, 30)
        # LRU order: 1, 2, 3
        cache.put(4, 40)  # evicts 1
        cache.put(5, 50)  # evicts 2
        cache.put(6, 60)  # evicts 3
        with pytest.raises(CacheMissError):
            cache.get(1)
        with pytest.raises(CacheMissError):
            cache.get(2)
        with pytest.raises(CacheMissError):
            cache.get(3)
        assert cache.get(4) == 40
        assert cache.get(5) == 50
        assert cache.get(6) == 60

    def test_mixed_get_put_ordering(self) -> None:
        cache = LRUCache(2)
        cache.put(1, 10)
        cache.put(2, 20)  # LRU order: 1, 2
        cache.get(1)       # LRU order: 2, 1
        cache.put(3, 30)   # evicts 2; LRU order: 1, 3
        cache.get(3)       # LRU order: 1, 3
        cache.put(4, 40)   # evicts 1; LRU order: 3, 4
        with pytest.raises(CacheMissError):
            cache.get(1)
        assert cache.get(3) == 30
        assert cache.get(4) == 40
