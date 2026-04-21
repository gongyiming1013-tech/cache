"""Test suite for ThreadSafeLRUCache (V1)."""

import threading

import pytest

from lru_cache import CacheMissError, InvalidCapacityError, ThreadSafeLRUCache


# --- Error Handling ---

class TestThreadSafeInvalidCapacity:
    """ThreadSafeLRUCache delegates capacity validation to LRUCache."""

    def test_zero_capacity_raises(self) -> None:
        with pytest.raises(InvalidCapacityError):
            ThreadSafeLRUCache(0)

    def test_negative_capacity_raises(self) -> None:
        with pytest.raises(InvalidCapacityError):
            ThreadSafeLRUCache(-1)


# --- Basic Delegation (single-threaded sanity) ---

class TestBasicDelegation:
    """Verify get/put behave identically to LRUCache through the lock."""

    def test_put_and_get(self) -> None:
        cache = ThreadSafeLRUCache(2)
        cache.put(1, 10)
        assert cache.get(1) == 10

    def test_get_missing_raises(self) -> None:
        cache = ThreadSafeLRUCache(2)
        with pytest.raises(CacheMissError):
            cache.get(99)

    def test_update_existing_key(self) -> None:
        cache = ThreadSafeLRUCache(2)
        cache.put(1, 10)
        cache.put(1, 20)
        assert cache.get(1) == 20

    def test_eviction(self) -> None:
        cache = ThreadSafeLRUCache(2)
        cache.put(1, 10)
        cache.put(2, 20)
        cache.put(3, 30)  # evicts 1
        with pytest.raises(CacheMissError):
            cache.get(1)
        assert cache.get(2) == 20
        assert cache.get(3) == 30

    def test_get_promotes_to_mru(self) -> None:
        cache = ThreadSafeLRUCache(2)
        cache.put(1, 10)
        cache.put(2, 20)
        cache.get(1)       # promotes 1
        cache.put(3, 30)   # evicts 2
        with pytest.raises(CacheMissError):
            cache.get(2)
        assert cache.get(1) == 10


# --- Concurrent Writes ---

class TestConcurrentWrites:
    """Multiple threads calling put simultaneously."""

    def test_concurrent_puts_no_corruption(self) -> None:
        cache = ThreadSafeLRUCache(100)
        errors: list[Exception] = []

        def writer(start: int) -> None:
            try:
                for i in range(start, start + 100):
                    cache.put(i, i * 10)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(i * 100,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        # Cache should have exactly 100 items (capacity)
        count = 0
        for i in range(1000):
            try:
                cache.get(i)
                count += 1
            except CacheMissError:
                pass
        assert count == 100


# --- Concurrent Reads + Writes ---

class TestConcurrentReadsWrites:
    """Threads calling get and put concurrently."""

    def test_mixed_get_put_no_crash(self) -> None:
        cache = ThreadSafeLRUCache(50)
        # Pre-populate
        for i in range(50):
            cache.put(i, i)

        errors: list[Exception] = []

        def reader() -> None:
            try:
                for i in range(200):
                    try:
                        cache.get(i % 100)
                    except CacheMissError:
                        pass  # expected for keys that were evicted
            except Exception as exc:
                errors.append(exc)

        def writer() -> None:
            try:
                for i in range(50, 150):
                    cache.put(i, i * 10)
            except Exception as exc:
                errors.append(exc)

        threads = (
            [threading.Thread(target=reader) for _ in range(5)]
            + [threading.Thread(target=writer) for _ in range(3)]
        )
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors


# --- Eviction Under Contention ---

class TestEvictionUnderContention:
    """Cache size never exceeds capacity under concurrent puts."""

    def test_capacity_not_exceeded(self) -> None:
        capacity = 10
        cache = ThreadSafeLRUCache(capacity)
        barrier = threading.Barrier(5)

        def writer(thread_id: int) -> None:
            barrier.wait()
            for i in range(100):
                cache.put(thread_id * 1000 + i, i)

        threads = [threading.Thread(target=writer, args=(tid,)) for tid in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Count remaining items — must not exceed capacity
        count = 0
        for tid in range(5):
            for i in range(100):
                try:
                    cache.get(tid * 1000 + i)
                    count += 1
                except CacheMissError:
                    pass
        assert count <= capacity


# --- Stress Test ---

class TestStress:
    """High volume of operations from many threads."""

    def test_stress_no_deadlock(self) -> None:
        cache = ThreadSafeLRUCache(20)
        errors: list[Exception] = []

        def worker(worker_id: int) -> None:
            try:
                for i in range(500):
                    key = (worker_id * 500 + i) % 50
                    cache.put(key, i)
                    try:
                        cache.get(key)
                    except CacheMissError:
                        pass  # another thread may have evicted it
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(w,)) for w in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
