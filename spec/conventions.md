# Conventions

An **informative** cheat-sheet of the conventions used throughout the Binate
language specification, for quick reference while reading or authoring. The
**normative** sources are **Ch.4 Notation** (metalanguage, rubric, status
legend, rule-IDs) and **Ch.3 Terms and Definitions** (terminology); where this
digest and those chapters could differ, the chapters govern.

## Requirement vocabulary

Body prose is **normative by default**. Binding terms: **shall** / **shall
not** (requirement), **should** (recommendation), **may** (permission).
Informative content is confined to clearly-marked **Note**, **Example**, and
**Rationale** blocks, and to annexes labeled _(informative)_. All design
rationale lives only in Annex D and Note blocks — never in normative prose.

## Per-construct rubric

Each feature section is presented in this fixed order:

1. **Grammar** — the relevant EBNF productions (inlined; normative). Until the
   Phase-0 grammar reconciliation produces the canonical `binate.ebnf`, the
   inlined productions are authoritative and `binate.ebnf` is a placeholder
   (§4.1 `notation.grammar.source`).
2. **Constraints** — diagnosable static rules (what a conforming
   implementation must reject). Maps onto Binate's "compiler checks upfront /
   interpreter defers" split, and onto the conformance harness's negative
   (`.error`) tests.
3. **Static semantics** — typing, name resolution.
4. **Dynamic semantics** — runtime behavior, including refcount/ownership
   effects and any compiled-vs-interpreted divergence.
5. **Exceptions** — the enumerated error conditions and any undefined behavior.
6. **Notes / Examples** — informative, typographically distinct, never binding.

For the hardest cross-cutting dynamic semantics (the refcount memory model,
Ch.18; dual-mode dispatch, Ch.19), supplement prose with a formal operational
rule and state which form is authoritative.

## Status legend (two orthogonal axes)

Status is **orthogonal** to normative/informative. There are two axes:

### Language-design stability (per section/rule)

- **Stable** — semantics fixed; changes are breaking and rare.
- **Provisional** — specified and implemented but may still change.
- **Draft** — specified but partially/not implemented; still normative-in-intent.
- **Reserved** — syntax/feature reserved, semantics not yet defined.

### Implementation-conformance (does the current toolchain conform?)

Separate from language stability. A known miscompile does **not** make a
language rule unstable — it makes the _implementation_ non-conformant. This
axis is sourced from `claude-todo.md` (CRITICAL + MAJOR) and, going forward,
from **spec conformance test** results (pass / xfail per mode). It lives in
**Annex C** (the status table); the implementation model and
implementation-defined-behavior index are **Annex B**.

The retired grammar annotations `[BOOTSTRAP]` / `[DEFERRED]` are **not** a
stability axis (they tracked a retired Go-interpreter subset) and are stripped
from the normative grammar.

## Rule-ID scheme

Every normative section/statement carries a **stable rule-ID**:
`<prefix>.<area>.<name>` (e.g. `mem.ownership.transfer`, `type.layout.slice-managed`,
`exec.dualmode.thunk`, `iface.dispatch.multireturn`). Per-chapter prefixes
(normative home: §4.5 `notation.ruleid`):

| Ch | Prefix | Ch | Prefix | Ch | Prefix |
|----|--------|----|--------|----|--------|
| 2 Conformance | `conf` | 9 Declarations | `decl` | 16 Packages | `pkg` |
| 3 Terms | `term` | 10 Functions | `func` | 17 Program | `prog` |
| 4 Notation | `notation` | 11 Interfaces | `iface` | 18 Memory model | `mem` |
| 5 Lexical | `lex` | 12 Generics | `gen` | 19 Execution | `exec` |
| 6 Constants | `const` | 13 Expressions | `expr` | 20 Tier-0 pkgs | `pkg0` |
| 7 Types | `type` | 14 Statements | `stmt` | 21 Behavior | `behavior` |
| 8 Conversions | `conv` | 15 Builtins | `builtin` | Annex A/B | `grammar`/`impl` |

Rule-IDs — not section numbers — are the cross-reference target **and** the
**spec-conformance-test citation target**, so references and tests survive
renumbering and the file split. IDs are adopted from day one and are stable
across edits.

## Terminology pins

- **`readonly`** is the type modifier everywhere; **`const`** is _only_ the
  compile-time-constant declaration. Legacy `const T` / `[N]const char`
  (older docs) are superseded.
- **managed-slice** (hyphenated) = `@[]T`, **4 words** `{data, len, backing,
  backingLen}`. **raw slice** = `*[]T`, 2 words. **managed struct** (two words).
- Canonical interface methods are **`Compare`** / **`String`** / **`Hash`**
  (`toString`/`less`/`hash` superseded).
- Behavior-latitude terms (implementation-defined / unspecified / undefined)
  plus target-invariant / target-parameterized are defined in Ch.3 and used
  consistently.

## Grammar notation

Keep the ISO/IEC-14977-flavored EBNF already in use: `=` definition, `|`
alternation, `{}` repetition, `[]` optional, `()` grouping, `…` inclusive
character range, `;` terminator, `(* *)` comments, double-quoted literal
terminals, juxtaposition = concatenation. The canonical grammar will be
`binate.ebnf`; Annex A and the inlined per-section productions are to be
generated from it once the Phase-0 reconciliation completes. Until then
`binate.ebnf` is a placeholder and the inlined productions are authoritative.

## Spec conformance tests

The implementation-conformance axis is made real by **spec conformance
tests** — conformance-style `.bn` programs tagged with the rule-ID(s) they
exercise. See `explorations/plan-language-spec.md` §10 for the mechanism.
