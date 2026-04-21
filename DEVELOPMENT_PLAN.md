# DEVELOPMENT_PLAN.md

---

## Overview

Design and implement a Least Recently Used (LRU) cache that stores a limited number of key-value pairs. When the cache reaches its maximum capacity, the least recently used item is automatically evicted.

The core data structure combines a **doubly linked list** (for O(1) recency tracking and eviction) with a **hash map** (for O(1) key lookup). Sentinel (dummy) head and tail nodes eliminate boundary edge cases.

**Goals:**
- O(1) time complexity for `get` and `put` operations.
- Correct eviction of the least recently used item when capacity is exceeded.
- Extensible design that supports concurrency, logging, and scaling in later versions.

---

## Design

### V0 — MVP (Single-Threaded LRU Cache)

**Goal:** A correct, single-threaded LRU cache with O(1) `get` and `put`.

**Architecture:**

```
┌──────────────────────────────────────────────────┐
│                   LRUCache                       │
│                                                  │
│  HashMap: { key → Node }                         │
│                                                  │
│  Doubly Linked List (most recent → least recent):│
│  [dummy_head] <-> [node] <-> ... <-> [dummy_tail]│
│   (MRU side)                        (LRU side)   │
└──────────────────────────────────────────────────┘

- get(key): lookup node in map → move to head → return value; raise CacheMissError if not found
- put(key, val): if exists, update & move to head;
                 else create node, add to head, insert in map;
                 if over capacity, remove node at tail, delete from map
```

**Design Patterns:**

| Pattern | Where | Why |
|---------|-------|-----|
| Sentinel Object | Dummy head/tail nodes | Eliminates None-check edge cases in list operations |

**Class / Function & Data Structure Reference:**

| Type | Name | Signature / Fields | Notes |
|------|------|--------------------|-------|
| Class | `LRUCacheError` | inherits `Exception` | Base exception for all LRU cache errors |
| Class | `CacheMissError` | inherits `LRUCacheError, KeyError` | Raised when `get` is called with a key not in the cache |
| Class | `InvalidCapacityError` | inherits `LRUCacheError, ValueError` | Raised when capacity ≤ 0 is provided to `__init__` |
| Class | `Node` | `key: int, value: int, prev: Node, next: Node` | Doubly linked list node |
| Class | `LRUCache` | `capacity: int, cache: dict[int, Node], head: Node, tail: Node` | Main cache class |
| Method | `LRUCache.__init__` | `(self, capacity: int) -> None` | Init map, sentinel nodes, link head <-> tail; raises `InvalidCapacityError` if capacity ≤ 0 |
| Method | `LRUCache.get` | `(self, key: int) -> int` | Returns value or raises `CacheMissError` |
| Method | `LRUCache.put` | `(self, key: int, value: int) -> None` | Insert or update; evict LRU if over capacity |
| Method | `LRUCache._remove` | `(self, node: Node) -> None` | Unlink a node from the list |
| Method | `LRUCache._add_to_front` | `(self, node: Node) -> None` | Insert a node right after dummy head |

**Test Plan:**

| Dimension | Covers | Key Scenarios |
|-----------|--------|---------------|
| Core functionality | get/put correctness | get existing key, get missing key raises `CacheMissError`, put new key, put update existing key |
| Eviction | LRU eviction policy | Evict when at capacity, evict correct (least recent) item, evict after access pattern changes order |
| Error handling | Invalid input | Capacity of 0 raises `InvalidCapacityError`, negative capacity raises `InvalidCapacityError` |
| Edge cases | Boundary conditions | Capacity of 1, get on empty cache raises `CacheMissError`, put same key repeatedly, large number of operations |
| Ordering | Recency tracking | get promotes item to MRU, put promotes item to MRU, verify eviction order after mixed get/put |

### V1 — Thread-Safe LRU Cache (Planned)

**Goal:** Make the LRU cache safe for concurrent access from multiple threads.

**Strategy Comparison:**
- Placeholder for candidate approaches: coarse-grained lock vs. read-write lock vs. fine-grained locking.

**Design Discussion:**
- What granularity of locking provides the best trade-off between simplicity and throughput?
- Should we use `threading.Lock` or `threading.RLock`?
- Is a read-write lock worthwhile given Python's GIL?

**Class / Function & Data Structure Changes:**
- Placeholder for lock integration into `LRUCache`.

**Test Plan:**

| Dimension | Covers | Key Scenarios |
|-----------|--------|---------------|
| Concurrency | Thread safety | Concurrent get/put, no data corruption under contention, eviction correctness under concurrent writes |

---

## Roadmap & Implementation

### V0 — MVP

**Scope:** Implement a single-threaded LRU cache with O(1) `get` and `put` using a hand-built doubly linked list and a hash map. Sentinel head/tail nodes simplify boundary handling. All public methods include docstrings. Achieve ≥95% branch coverage.

- [x] Implement exception hierarchy: `LRUCacheError` → `CacheMissError`, `InvalidCapacityError`
- [x] Implement `Node` class with `key`, `value`, `prev`, `next` fields
- [x] Implement `LRUCache.__init__` — initialize capacity, hash map, sentinel head/tail; raises `InvalidCapacityError` if capacity ≤ 0
- [x] Implement `LRUCache._remove` — unlink a node from the doubly linked list
- [x] Implement `LRUCache._add_to_front` — insert node right after dummy head
- [x] Implement `LRUCache.get` — lookup, move to front, return value; raises `CacheMissError` if not found
- [x] Implement `LRUCache.put` — insert/update, evict LRU if over capacity
- [x] Write test suite covering core functionality, eviction, edge cases, ordering (16 tests)
- [x] Verify ≥95% branch coverage (achieved 100%)

### V1 — Thread-Safe (Planned)

**Scope:** Add thread-safety to the LRU cache so it can be used in multi-threaded environments without data corruption.

- [ ] Evaluate locking strategies (coarse lock vs. read-write lock)
- [ ] Add lock to `get` and `put` operations
- [ ] Write concurrent test cases (multi-threaded get/put)
- [ ] Verify correctness under contention
