"""LRU Cache implementation using a doubly linked list and hash map."""

from __future__ import annotations

import threading


# --- Exceptions ---

class LRUCacheError(Exception):
    """Base exception for all LRU cache errors."""


class CacheMissError(LRUCacheError, KeyError):
    """Raised when a key is not found in the cache."""


class InvalidCapacityError(LRUCacheError, ValueError):
    """Raised when an invalid capacity (≤ 0) is provided."""


# --- Node ---

class Node:
    """Doubly linked list node storing a key-value pair."""

    def __init__(self, key: int, value: int) -> None:
        self.key = key
        self.value = value
        self.prev: Node | None = None
        self.next: Node | None = None


# --- LRU Cache ---

class LRUCache:
    """Least Recently Used cache with O(1) get and put operations.

    Uses a doubly linked list for recency tracking and a hash map
    for O(1) key lookup. Sentinel head and tail nodes eliminate
    boundary edge cases.
    """

    def __init__(self, capacity: int) -> None:
        """Initialize the LRU cache.

        Args:
            capacity: Maximum number of key-value pairs to store.

        Raises:
            InvalidCapacityError: If capacity is less than or equal to 0.
        """
        if capacity <= 0:
            raise InvalidCapacityError(f"Capacity must be positive, got {capacity}")
        self._capacity = capacity
        self._cache: dict[int, Node] = {}
        self._head = Node(0, 0)  # dummy head (MRU side)
        self._tail = Node(0, 0)  # dummy tail (LRU side)
        self._head.next = self._tail
        self._tail.prev = self._head

    def get(self, key: int) -> int:
        """Retrieve the value for the given key and mark it as most recently used.

        Args:
            key: The key to look up.

        Returns:
            The value associated with the key.

        Raises:
            CacheMissError: If the key is not in the cache.
        """
        if key not in self._cache:
            raise CacheMissError(f"Key {key} not found in cache")
        node = self._cache[key]
        self._remove(node)
        self._add_to_front(node)
        return node.value

    def put(self, key: int, value: int) -> None:
        """Insert or update a key-value pair. Evicts the LRU item if at capacity.

        Args:
            key: The key to insert or update.
            value: The value to associate with the key.
        """
        if key in self._cache:
            node = self._cache[key]
            node.value = value
            self._remove(node)
            self._add_to_front(node)
            return
        node = Node(key, value)
        self._cache[key] = node
        self._add_to_front(node)
        if len(self._cache) > self._capacity:
            lru_node = self._tail.prev
            self._remove(lru_node)
            del self._cache[lru_node.key]

    def _remove(self, node: Node) -> None:
        """Unlink a node from the doubly linked list.

        Args:
            node: The node to remove.
        """
        prev_node = node.prev
        next_node = node.next
        prev_node.next = next_node
        next_node.prev = prev_node

    def _add_to_front(self, node: Node) -> None:
        """Insert a node right after the dummy head (most recently used position).

        Args:
            node: The node to insert.
        """
        first = self._head.next
        self._head.next = node
        node.prev = self._head
        node.next = first
        first.prev = node


# --- Thread-Safe LRU Cache (V1) ---

class ThreadSafeLRUCache:
    """Thread-safe LRU cache wrapper using coarse-grained locking.

    Wraps an ``LRUCache`` instance via composition and serializes all
    ``get`` and ``put`` calls with a ``threading.Lock``.
    """

    def __init__(self, capacity: int) -> None:
        """Initialize the thread-safe LRU cache.

        Args:
            capacity: Maximum number of key-value pairs to store.

        Raises:
            InvalidCapacityError: If capacity is less than or equal to 0.
        """
        self._cache = LRUCache(capacity)
        self._lock = threading.Lock()

    def get(self, key: int) -> int:
        """Retrieve the value for the given key (thread-safe).

        Args:
            key: The key to look up.

        Returns:
            The value associated with the key.

        Raises:
            CacheMissError: If the key is not in the cache.
        """
        with self._lock:
            return self._cache.get(key)

    def put(self, key: int, value: int) -> None:
        """Insert or update a key-value pair (thread-safe).

        Evicts the LRU item if at capacity.

        Args:
            key: The key to insert or update.
            value: The value to associate with the key.
        """
        with self._lock:
            self._cache.put(key, value)
