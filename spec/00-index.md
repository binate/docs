# Binate Language Specification — index

The **core language specification** for Binate (a systems language with
reference-counted managed/raw pointers, explicit interfaces + `impl`,
monomorphized generics, errors-as-values, and a dual compiled+interpreted
execution model). This spec covers the core language **and the tier-0
intrinsic packages** (Ch.20); the standard library (tier 1) is a separate,
dependent sibling spec.

- **Structure, conventions, and authoring plan:** `explorations/plan-language-spec.md`.
- **Shared apparatus:** [`conventions.md`](conventions.md) (requirement
  vocabulary, status legend, per-construct rubric, rule-ID scheme,
  terminology, grammar notation, spec-tests).
- **Canonical grammar:** [`binate.ebnf`](binate.ebnf) (Annex A is generated
  from it).

> **Authoring status.** Chapters 3–21 (and the shared apparatus —
> [`conventions.md`](conventions.md) and this index) are **authored**, and
> **Annex A** is generated from the canonical [`binate.ebnf`](binate.ebnf).
> Chapters 1–2 and annexes B–D remain Phase-0 stubs carrying their status badge,
> rule-ID prefix, and source map. Per-chapter maturity is in the table below;
> each chapter's own header badge governs where it could differ.

## Status legend

Two orthogonal axes (see [`conventions.md`](conventions.md)):
**language-design stability** (Stable / Provisional / Draft / Reserved) and
**implementation-conformance** (does the current toolchain conform? — sourced
from `claude-todo.md` and, going forward, spec-test results). Status is
orthogonal to normative/informative.

## Reading order (the dependency DAG)

Bottom-up: each chapter leans only on earlier ones. The two load-bearing
cross-cutting chapters (Memory model, Execution/dual-mode) come late, after
every term they need is defined.

| # | Chapter | Kind | Maturity | Rule-ID |
|---|---------|------|----------|---------|
| 1 | [Scope and Introduction](01-scope-introduction.md) | informative | n/a (framing) |  |
| 2 | [Conformance](02-conformance.md) | normative | Draft (skeleton) | `conf` |
| 3 | [Terms and Definitions](03-terms-and-definitions.md) | normative | mostly Stable (grows with the spec) | `term` |
| 4 | [Notation](04-notation.md) | normative | Stable (apparatus) | `notation` |
| 5 | [Lexical Elements](05-lexical-elements.md) | normative | mostly Stable | `lex` |
| 6 | [Constants](06-constants.md) | normative | Stable | `const` |
| 7 | [Types](07-types.md) | mixed | mostly Stable (caveats) | `type` |
| 7.13 | [Type Layout & Representation](07b-type-layout.md) | normative | Stable (ABI contract) | `type.layout` |
| 8 | [Conversions](08-conversions.md) | normative | Stable | `conv` |
| 9 | [Declarations and Scope](09-declarations-and-scope.md) | normative | Stable | `decl` |
| 10 | [Functions, Methods, and Function Values](10-functions-methods-function-values.md) | mixed | Stable (functions/methods) | `func` |
| 10.8 | [Function Values, Closures, Method Values](10b-function-values.md) | mixed | Provisional | `func` |
| 11 | [Interfaces, impl, and Self](11-interfaces-impl-self.md) | mixed | language rules Stable; conformance mixed (CRITICAL dispatch defects resolved; alias-receiver §11.3, arm32 §11.11) | `iface` |
| 12 | [Generics and Enumerations](12-generics-and-enumerations.md) | mixed | language rules Stable (v1 scope); two v1-restrictions unenforced | `gen` |
| 13 | [Expressions](13-expressions.md) | normative | Stable (composite-literal defects flagged) | `expr` |
| 14 | [Statements](14-statements.md) | mixed | language rules Stable; 1 MAJOR impl defect flagged (inc/dec on non-ident lvalue) | `stmt` |
| 14.8 | [Control-flow statements](14b-control-flow.md) | mixed | language rules Stable; a few open semantic items | `stmt` |
| 15 | [Built-in Operations](15-builtin-operations.md) | mixed | mostly Stable (opaque-gate + VM-panic gaps flagged; print/println provisional) | `builtin` |
| 16 | [Packages and Program Structure](16-packages-and-program-structure.md) | mixed | Stable core | `pkg` |
| 16.7 | [Annotations, Build Constraints, FFI](16b-build-constraints.md) | mixed | arch/os MVP; most predicates deferred | `pkg` |
| 17 | [Program Initialization and Execution](17-program-initialization-and-execution.md) | mixed | Stable rules; entry/termination host-dependent; panic gaps flagged | `prog` |
| 18 | [Memory Model: Reference Counting and Object Lifetime](18-memory-model-reference-counting.md) | mixed | Stable axioms (ownership-transfer DECIDED); move is an optimization | `mem` |
| 19 | [Execution Model: the Abstract Machine and Dual-Mode Interop](19-execution-model-dual-mode.md) | mixed | Contract Stable; in-process embedding a goal | `exec` |
| 20 | [Intrinsic (Tier-0) Packages](20-intrinsic-tier0-packages.md) | mixed | lang Stable (float-NaN Provisional); rt Draft (gated); reflect Draft; testing Provisional | `pkg0` |
| 21 | [Implementation-defined, Unspecified, and Undefined Behavior](21-implementation-defined-and-undefined-behavior.md) | normative | contracts Stable; byte-order GAP open (§21.4) | `behavior` |
| A | [Grammar Summary](annex-a-grammar-summary.md) | normative | Stable (generated from `binate.ebnf`) | `grammar` |
| B | [Implementation Model and Implementation-defined Index](annex-b-implementation-model-and-idb-index.md) | mixed | Split Stable | `impl` |
| C | [Stability Status Table](annex-c-stability-status-table.md) | informative | Derived — finalize last | `status` |
| D | [Rationale and Design Notes](annex-d-rationale-and-design-notes.md) | informative | n/a | `rationale` |

## Prerequisites (before dependent chapters/annex finalize)

1. ~~**Grammar reconciliation + move into the spec** (Phase 0) — produces the
   canonical `binate.ebnf`; gates Annex A.~~ **Done** — `binate.ebnf` is
   canonical and Annex A is generated from it (`scripts/gen-annex-a.py`).
2. **`pkg/rt` review** — classify each member stay / move-to-stdlib /
   make-internal; gates §20.2.
