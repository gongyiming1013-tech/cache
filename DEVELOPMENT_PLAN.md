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

### V1 — Thread-Safe LRU Cache

**Goal:** Make the LRU cache safe for concurrent access from multiple threads.

**Architecture:**

```
┌──────────────────────────────────────────────────────┐
│              ThreadSafeLRUCache                       │
│                                                      │
│  Composition: wraps an LRUCache instance              │
│  Lock: threading.Lock (coarse-grained)               │
│                                                      │
│  get(key)  → acquire lock → delegate to LRUCache.get │
│  put(k, v) → acquire lock → delegate to LRUCache.put │
└──────────────────────────────────────────────────────┘
```

**Design Patterns:**

| Pattern | Where | Why |
|---------|-------|-----|
| Composition | `ThreadSafeLRUCache` wraps `LRUCache` | Keeps thread-safety concern separate from core logic; V0 `LRUCache` remains unchanged and independently testable |
| Context Manager | `with self._lock:` | Ensures lock is always released, even on exceptions |

**Strategy Comparison:**

| Strategy | Pros | Cons | Verdict |
|----------|------|------|---------|
| Coarse-grained `threading.Lock` | Simple, correct, easy to test | Read/write contention | **Selected** — `get` mutates the list so it's effectively a write; RWLock provides no benefit |
| Read-Write Lock | Higher read concurrency in theory | `get` is a write operation (moves node); Python GIL limits benefit | Not applicable |
| Fine-grained Locking | Higher throughput under contention | Complex, deadlock risk, hard to test | Over-engineering for this use case |
| `threading.RLock` | Allows reentrant locking | Not needed — no public method calls another public method | Unnecessary overhead |

**Class / Function & Data Structure Reference:**

| Type | Name | Signature / Fields | Notes |
|------|------|--------------------|-------|
| Class | `ThreadSafeLRUCache` | `_cache: LRUCache, _lock: threading.Lock` | Thread-safe wrapper via composition |
| Method | `ThreadSafeLRUCache.__init__` | `(self, capacity: int) -> None` | Creates internal `LRUCache` and `Lock`; raises `InvalidCapacityError` if capacity ≤ 0 |
| Method | `ThreadSafeLRUCache.get` | `(self, key: int) -> int` | Acquires lock, delegates to `LRUCache.get` |
| Method | `ThreadSafeLRUCache.put` | `(self, key: int, value: int) -> None` | Acquires lock, delegates to `LRUCache.put` |

**Test Plan:**

| Dimension | Covers | Key Scenarios |
|-----------|--------|---------------|
| Basic delegation | Correctness through lock | get/put behave identically to `LRUCache` (single-threaded sanity check) |
| Concurrent writes | No data corruption | Multiple threads calling `put` simultaneously; final cache state is consistent |
| Concurrent reads + writes | No data corruption | Threads calling `get` and `put` concurrently; no exceptions besides expected `CacheMissError` |
| Eviction under contention | Correctness | Cache size never exceeds capacity under concurrent `put` from many threads |
| Stress test | Stability | High volume of operations from many threads; no deadlocks or crashes |

### V2 — TTL & Observability

**Goal:** Add time-to-live (TTL) expiration per entry and lightweight observability (hit/miss counters, eviction counts) to support production monitoring.

**Architecture:**

```
┌──────────────────────────────────────────────────────────────┐
│                     TTLLRUCache                               │
│                                                              │
│  HashMap: { key → TTLNode }                                   │
│  Doubly Linked List: [dummy_head] <-> [TTLNode] <-> [dummy_tail] │
│  Stats: CacheStats (hits, misses, evictions, expirations)    │
│                                                              │
│  get(key)        → check expired → move to front → stats++   │
│  put(key, val, ttl) → insert/update with expires_at          │
│  _evict()        → prefer expired entries, fallback to LRU   │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│           ThreadSafeTTLLRUCache                   │
│  Composition: wraps TTLLRUCache + threading.Lock  │
│  get / put → acquire lock → delegate              │
│  stats property → exposes inner cache stats       │
└──────────────────────────────────────────────────┘
```

**Design Patterns:**

| Pattern | Where | Why |
|---------|-------|-----|
| Lazy Expiration | `get()` checks `is_expired()` before returning | Avoids background thread complexity; expired entries cleaned on access |
| Prefer-Expired Eviction | `_evict()` scans for expired before LRU | Expired entries removed first to preserve live data |
| Composition | `ThreadSafeTTLLRUCache` wraps `TTLLRUCache` | Consistent with V1 pattern; keeps concerns separated |
| Dataclass | `CacheStats` | Clean, lightweight counter container with `reset()` |

**Strategy Comparison:**

| Strategy | Pros | Cons | Verdict |
|----------|------|------|---------|
| Lazy expiration (on `get`) | Simple, no background threads | Expired entries linger until accessed | **Selected** — combined with prefer-expired eviction for cleanup |
| Background reaper thread | Proactive cleanup | Threading complexity, overhead | Not needed — lazy + prefer-expired sufficient |
| Hybrid (lazy + periodic sweep) | Best of both | More complex | Over-engineering for current scope |
| Per-entry TTL | Flexible, each key can have different TTL | Slightly more storage per node | **Selected** — set via `put(key, val, ttl=...)` |
| Global TTL | Simpler API | Inflexible | Rejected — per-entry is more useful |
| Stats built into cache | Direct access, no indirection | Couples concerns | **Selected** — simpler than decorator for this scope |

**Class / Function & Data Structure Reference:**

| Type | Name | Signature / Fields | Notes |
|------|------|--------------------|-------|
| Dataclass | `CacheStats` | `hits: int, misses: int, evictions: int, expirations: int` | Mutable counters; `reset()` zeros all |
| Class | `TTLNode` | `key: int, value: int, expires_at: float \| None, prev: TTLNode, next: TTLNode` | Extends Node concept with expiration |
| Method | `TTLNode.is_expired` | `(self) -> bool` | Compares `expires_at` against `time.monotonic()` |
| Class | `TTLLRUCache` | `_capacity: int, _cache: dict, _head: TTLNode, _tail: TTLNode, stats: CacheStats` | Core TTL cache |
| Method | `TTLLRUCache.__init__` | `(self, capacity: int) -> None` | Raises `InvalidCapacityError` if capacity ≤ 0 |
| Method | `TTLLRUCache.get` | `(self, key: int) -> int` | Lazy expiration; tracks hits/misses/expirations |
| Method | `TTLLRUCache.put` | `(self, key: int, value: int, ttl: float \| None = None) -> None` | Per-entry TTL via `time.monotonic() + ttl` |
| Method | `TTLLRUCache._evict` | `(self) -> None` | Prefers expired entries; falls back to LRU |
| Class | `ThreadSafeTTLLRUCache` | `_cache: TTLLRUCache, _lock: threading.Lock` | Thread-safe wrapper |

**Test Plan:**

| Dimension | Covers | Key Scenarios |
|-----------|--------|---------------|
| TTL expiration | Correctness | Entry expires after TTL, `get` on expired entry raises `CacheMissError`, expired entry does not block new inserts |
| Capacity + TTL interaction | Eviction policy | Expired entries evicted before live entries, capacity correctly maintained with mixed expired/live entries |
| Observability | Metric accuracy | Hit/miss counters correct after sequences of get/put, eviction counter increments on eviction, stats reset |
| Thread safety + TTL | Concurrency | Concurrent access with TTL entries; no races on expiration checks |

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

### V1 — Thread-Safe

**Scope:** Add a `ThreadSafeLRUCache` class that wraps `LRUCache` via composition, using a coarse-grained `threading.Lock` to serialize all `get` and `put` calls. The existing `LRUCache` remains unchanged. Achieve ≥95% branch coverage on the new class.

- [x] Evaluate locking strategies (coarse lock vs. read-write lock) — coarse `Lock` selected
- [x] Implement `ThreadSafeLRUCache` class with `__init__`, `get`, `put`
- [x] Write single-threaded sanity tests for `ThreadSafeLRUCache` (5 tests)
- [x] Write concurrent test cases: multi-threaded put, mixed get/put, eviction under contention (3 tests)
- [x] Write stress test: high volume operations from many threads (1 test)
- [x] Verify ≥95% branch coverage (achieved 99% across all classes)

### V2 — TTL & Observability

**Scope:** Extend the cache with optional per-entry TTL expiration and a lightweight stats interface (hit/miss/eviction counters) for production observability. Includes `TTLLRUCache`, `TTLNode`, `CacheStats`, and `ThreadSafeTTLLRUCache`. Uses lazy expiration on `get` and prefer-expired eviction on `put`.

- [x] Evaluate TTL strategies (lazy vs. eager vs. hybrid expiration) — lazy + prefer-expired eviction selected
- [x] Decide on per-entry vs. global TTL approach — per-entry via `put(key, val, ttl=...)` selected
- [x] Design `CacheStats` dataclass for observability metrics (hits, misses, evictions, expirations, reset)
- [x] Implement `TTLNode` with `is_expired()` using `time.monotonic()`
- [x] Implement `TTLLRUCache` with lazy expiration in `get` and prefer-expired `_evict`
- [x] Implement hit/miss/eviction/expiration counters in `TTLLRUCache`
- [x] Implement `ThreadSafeTTLLRUCache` wrapper with `threading.Lock`
- [x] Write TTL correctness tests: expiration, capacity interaction, mixed TTL/no-TTL (8 tests)
- [x] Write observability tests: counter accuracy, stats reset (5 tests)
- [x] Write concurrent TTL + stats tests: mixed read/write with TTL, stress test (5 tests)
- [x] Verify ≥95% branch coverage (achieved 99% across all classes)
