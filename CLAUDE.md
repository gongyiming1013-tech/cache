# AI Coding Collaboration Protocol

## 1. Coding Standards & Design Principles

### Clean Code

- **Keep functions small** and focused on a single responsibility.
- **Prefer clarity over cleverness.** Code is read far more often than it is written.
- **Type safety:** Use the language's type system (type hints, generics, static types) in all method signatures wherever possible.
- **Encapsulation:** Expose the minimum public API necessary. All internal state and helpers must be private.

### Implementation Approach

Choose the simplest approach that fits the problem:

| Approach | When to use |
|----------|------------|
| **Functions** | Algorithm problems, single-responsibility logic, user explicitly requests no OOD, V0/MVP rapid prototyping |
| **OOD (Classes)** | Maintaining internal state, multiple related operations sharing data, polymorphism/strategy switching, system design problems |

In the planning phase, compare OOD (object-oriented design) and non-OOD approaches for the task at hand:
- If both are suitable, use functions as the V0 for rapid POC, and note OOD as the V1 path for scale-up.
- If the user explicitly specifies OOD or non-OOD, follow that instruction directly — do not re-evaluate.

### Test-Driven Development (TDD)

Tests are not an afterthought — they are a core design tool. Always follow this order:

1. **Define the contract first:** Establish function signatures or class interfaces that describe the expected behavior.
2. **Write tests against the contract:** Develop test cases based on the expected behavior before any implementation exists.
3. **Implement to pass the tests:** Write the minimum concrete code needed to satisfy the test suite.

This ensures that every component is testable by design, contracts are explicit and well-understood, and regressions are caught immediately.

### Code Structure

#### Function-based

Organize function-based modules in a consistent order:

1. Module-level documentation (docstring / doc comment)
2. Constants
3. Helper functions (private, prefixed with `_`)
4. Public functions
5. Entry point / main logic

#### Class-based

Organize every class in a consistent order:

1. Class-level documentation (docstring / doc comment)
2. Constructor / initializer
3. Public methods
4. Private helpers

### OOD Best Practices

Apply only when OOD is the chosen approach.

- **Favor Composition over Inheritance.** Compose behavior from small, focused objects rather than deep inheritance hierarchies.
- **Use appropriate Design Patterns** based on the domain. Prefer simple, well-known patterns:
  - **Strategy** — swappable algorithms
  - **Observer** — event notification
  - **Factory Method** — conditional object creation
  - **Singleton** — global unique instance
  - **Iterator** — custom traversal
  - **Command / State** — when the domain calls for them
- **Avoid complex patterns** (Builder, Abstract Factory, nested Decorators) unless the problem explicitly requires them.

### SOLID Principles

Apply only when OOD is the chosen approach. Do NOT over-engineer.

- **S — Single Responsibility:** One class, one job. Keep each class and method concise and focused.
- **O — Open/Closed:** Add new behavior via new classes or modules, not by modifying existing ones.
- **L — Liskov Substitution:** Subclasses must be drop-in replacements for their parent type.
- **I — Interface Segregation:** Keep interfaces small and focused. Clients should not depend on methods they do not use.
- **D — Dependency Inversion:** Depend on abstractions (interfaces/protocols), inject concrete implementations.

### Domain-Driven Naming

Use descriptive, ubiquitous language for all entities, variables, and methods.

| Element               | Convention         | Example                          |
|-----------------------|--------------------|----------------------------------|
| Classes / Interfaces  | PascalCase         | `LRUCache`, `FileParser`         |
| Methods / Functions   | snake_case or camelCase (per language convention) | `get_value` / `getValue` |
| Variables             | snake_case or camelCase (per language convention) | `max_size` / `maxSize`   |
| Constants             | UPPER_SNAKE_CASE   | `MAX_CAPACITY`, `DEFAULT_TIMEOUT`|
| Private members       | Language-appropriate access modifier or naming convention | `_cache` (Python), `private` (Java/C++) |

### Comments & Documentation

- Every public function, class, and method must have a doc comment.
- Inline comments explain **why**, not **what**.
- Do not over-comment obvious code.

### Error Handling

- Define a base custom exception per domain, with specific subclasses.
- Use **guard clauses** — put boundary checks at the top of methods.
- Only catch exceptions where recovery is possible. Do not swallow errors silently.

---

## 2. Thinking & Planning Workflow (Mandatory)

Before writing any implementation code, follow this high-level thinking process:

### Phase A: High-Level Conceptualization & Design

Analyze the requirements and produce the **Overview** and **Design** sections of `DEVELOPMENT_PLAN.md`.

1. **High-Level Conceptualization** (maps to the **Overview** section in `DEVELOPMENT_PLAN.md`)
   - Summarize what this project / feature is and the problem it solves.
   - State the high-level goals and expected outcomes.
   - Distill the requirements into a concise description of the task and its general direction.

2. **Design** (maps to the **Design** section in `DEVELOPMENT_PLAN.md`, organized by version)
   - Each completed version must include:
     - **Goal** — one sentence summarizing the version's objective.
     - **Architecture** — diagram showing component relationships and data flow.
     - **Design Patterns** — table of patterns used, where, and why.
     - **Strategy Comparisons** (if applicable) — table of alternatives considered with pros, cons, and verdict.
     - **Class / Function & Data Structure Reference** — every function, class, interface, record, and enum with signatures, fields, and thread-safety annotations.
     - **Test Plan** — table listing test dimensions, what each dimension covers, and key scenarios. Example dimensions: core functionality, edge cases, error handling, concurrency, performance.
   - Each planned version must include:
     - **Goal** — one sentence summarizing the version's objective.
     - **Strategy Comparison** — placeholder for candidate approaches and trade-offs.
     - **Design Discussion** — open questions to resolve before implementation.
     - **Class / Function & Data Structure Changes** — placeholder for new and modified types.
     - **Test Plan** — placeholder table for test dimensions and scenarios to cover.

### Phase B: Roadmap & Implementation Plan

Produce the **Roadmap & Implementation** section of `DEVELOPMENT_PLAN.md`. This is a single unified section organized by version:

- **V0 (MVP):** The minimum viable functional version.
- **V1+ (Enrichment):** Incremental enhancements (e.g., concurrency, advanced constraints, persistence).

Each version subsection must contain:
- **Scope** — a short paragraph describing the version's objective and approach in slightly more detail than the Goal in Design.
- **Checklist** — specific, actionable items covering feature scope and implementation steps. Use `[x]` for completed items, `[ ]` for pending items. Each version should end with a coverage verification item.

After completing Phase A and Phase B, the `DEVELOPMENT_PLAN.md` is ready for review. **STOP and ask the user to review and confirm the plan** before proceeding to Phase C.

### Phase C: Contract & TDD Setup

1. **Define Stubs:** Create function stubs or abstract classes/interfaces based on the chosen approach.
2. **Write Test Cases:** Develop comprehensive unit tests based on the API contract.
3. **User Review:** STOP and ask the user to review the test suite before proceeding to implementation.

---

## 3. Implementation & Iteration Rules

- **Step-by-Step Execution:** Follow the `DEVELOPMENT_PLAN.md` sequentially. Do not skip steps.
- **Continuous Verification:** Run the test suite and check branch coverage after every meaningful feature implementation.
- **Iterative Refinement:** Based on test results or user feedback, iterate on the code until it meets the quality bar.
- **Keep `DEVELOPMENT_PLAN.md` in sync:** After each change is merged to production, update the corresponding version's:
  1. **Design** section — reflect the actual architecture, classes, and patterns as implemented (not as originally planned).
  2. **Roadmap & Implementation** checklist — mark completed items `[x]` and update scope if it changed during implementation.

---

## 4. Quality & Commit Strategy

### Test Coverage

- Maintain a minimum of **95% branch coverage**.
- Every public function, class, and method must have corresponding test cases.
- Use the language's standard test framework (e.g., `pytest`, `JUnit`, `Jest`, `go test`).

### Edge Cases

- Explicitly handle null/nil inputs, boundary conditions, and concurrency race conditions.

### Final Review

- Once tests pass, propose a **Commit Strategy** using [Conventional Commits](https://www.conventionalcommits.org/) and wait for user approval before checking in the code.

---

## General Rules

- Prefer clarity over cleverness.
- Keep each class and method concise and focused.
- When proposing a solution, briefly explain the design rationale.