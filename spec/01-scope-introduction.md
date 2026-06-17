# 1. Scope and Introduction

> **Status:** informative · **Maturity:** n/a (framing)  
> **Rule-IDs:** none (framing / derived)

This chapter is **informative**. It says what Binate is (§1.1), the design goals
(§1.2) and the deliberate absences that shape it (§1.3), how this document fits
into the wider specification suite (§1.4), and how to read it (§1.5). Nothing
here is normative; the binding rules begin in Ch.2.

## 1.1 What Binate is

Binate is a **systems programming language** whose defining feature is
**dual-mode execution**: every program runs either **compiled** to native code or
**interpreted** by a bytecode virtual machine, and the two modes **interoperate**
over one shared heap (Ch.19). Its other pillars are:

- **Reference-counted memory** with **managed** (`@T`) and **raw** (`*T`)
  pointers — no garbage collector, and no ownership/borrowing system; raw
  pointers are the escape hatch for cycles and hot paths (Ch.18).
- **Explicit, nominal interfaces** with separate `impl` declarations and
  vtable-based dispatch — satisfaction is declared, never structural (Ch.11).
- **Monomorphized generics** constrained by interfaces (Ch.12).
- **Errors as values** — Go-style multiple returns; there are no exceptions and
  no `panic`/`recover` (§14.14).
- **Transparent, source-determined allocation** — where a value lives is
  determined by how it is written, never by hidden heap-allocation or escape
  analysis.

Binate targets **32-bit systems primarily**, with 64-bit support, and is designed
to run in a **C-free** system — C is used only to interface with existing
C-based components (for example, to make system calls), never as a substrate the
language requires.

## 1.2 Design goals

- **Dual-mode interop as a first-class property.** Compiled and interpreted code
  share one type system, one heap layout, and one calling seam, so they can be
  mixed; this is the **cross-mode agreement** invariant of Ch.2.
- **Deterministic memory.** Cleanup happens at well-defined points (statement
  end, scope exit, last reference) with no background collector and no
  non-deterministic finalization (Ch.18).
- **Explicit over implicit.** Interfaces are satisfied by declaration, numeric
  conversions are written, allocation is visible in the source, and `readonly`
  is a written type modifier — there is little that happens invisibly.
- **A small core, specifiable on bare metal.** The core language assumes no
  console, filesystem, process model, or threads, so it stays implementable on a
  **freestanding** target (Ch.2); host-dependent facilities are layered above it.
- **Layout as a contract.** A type's byte layout is a language-level contract
  shared by every compiler backend **and** the interpreter, not a per-backend
  decision (§7.13, Ch.2).

## 1.3 Deliberate absences

The following are omitted **by design**, not as gaps; each is a decision recorded
in the body (§14.14 catalogues the statement-level absences) and motivated in
Annex D:

- no **garbage collector**, and no **ownership/borrowing** system (Ch.18);
- no **exceptions** and no **`panic`/`recover`** — errors are values (§14.14);
- no built-in **maps**, no built-in **`string`** type (text is `@[]char` /
  `*[]char`), and no **`append`** or other built-in growable-collection
  operation — these are library concerns;
- no **`goto`**, no package **`init`** functions, no **`defer`**, and no
  **variadic** parameters;
- no **implicit numeric or named conversions** (Ch.8);
- and — in the **core** — no **`printf`**/formatting facility and no standard
  library at all.

## 1.4 The specification suite

Binate is deliberately **less monolithic** than most languages: the language is
usable without a standard library, and the core defines no `printf`-equivalent.
It is therefore specified as **several documents**:

- **This document — the core language specification.** It covers the syntax, type
  system, and semantics, **and the tier-0 intrinsic packages** (Ch.20) — the
  packages bound to the language itself (`pkg/builtins/{lang, rt, reflect,
  testing}`).
- **The standard library specification (tier 1)** — a separate, **dependent,
  younger-sibling** spec that builds on this one. It is **not** written here; the
  core spec only reserves a pointer to it.
- **Out of scope, each its own concern:** the **package manager**, the
  **toolchain**, and the **interpreter embedding API** (Ch.19).
- **Not part of the language:** `pkg/bootstrap` is temporary scaffolding.

**Why the split.** Binate targets environments with no console, filesystem,
process model, or threads. A core specification free of standard-library and I/O
assumptions stays implementable on a bare-metal target, while the standard
library layers host facilities selectively per target. This is why the spec
distinguishes **hosted** from **freestanding** conformance (Ch.2).

## 1.5 How to read this specification

- **Normative by default.** Body prose is binding; **Note**, **Example**, and
  **Rationale** blocks, and annexes marked _(informative)_, are not. The
  requirement vocabulary (**shall** / **should** / **may**) and the per-construct
  rubric are defined in Ch.4 and digested in [`conventions.md`](conventions.md).
- **Rule-IDs.** Each normative statement carries a stable `<prefix>.<area>.<name>`
  rule-ID; these — not section numbers — are the cross-reference and
  conformance-test citation targets (§4.5).
- **Two status axes.** Every feature carries a **language-stability** status and
  an **implementation-conformance** status; they are independent (§2.6).
- **The grammar.** The canonical grammar is [`binate.ebnf`](binate.ebnf); Annex A
  and the per-section inlined productions are generated from it (§4.1).
- **Terms** are defined in Ch.3. **Reading order** is bottom-up — each chapter
  leans only on earlier ones (see the [index](00-index.md)).
