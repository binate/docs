# 4. Notation

> **Status:** normative · **Maturity:** Stable (apparatus)  
> **Rule-ID prefix:** `notation`

This chapter defines how the rest of this specification is written and read:
the grammar metalanguage (§4.1), the per-construct presentation rubric
(§4.2), the normative/informative distinction and requirement vocabulary
(§4.3), the stability-status legend (§4.4), the rule-identifier scheme
(§4.5), and the notation used for dynamic semantics (§4.6).

This chapter is the normative source for these conventions; the
[`conventions.md`](conventions.md) cheat-sheet is an informative digest of it.

## 4.1 Grammar metalanguage

`notation.grammar.ebnf` — Syntax is specified with Extended Backus–Naur Form
in the style of ISO/IEC 14977, with the free choices of that standard pinned
as follows:

| Form | Meaning |
|------|---------|
| `=` | defines a production |
| juxtaposition (space) | concatenation |
| `\|` | alternation |
| `{ X }` | zero or more repetitions of `X` |
| `[ X ]` | `X` is optional (zero or one) |
| `( X )` | grouping |
| `"abc"` | the literal terminal `abc` |
| `…` (e.g. `"a" … "z"`) | an inclusive range of characters |
| `;` | terminates a production |
| `(* … *)` | a comment within the grammar |

Nonterminals are written as identifiers (e.g. `IntegerLit`); terminals are
either double-quoted literals or named character classes defined in prose.
A note such as `(* any character except '"' *)` defines a terminal class.

`notation.grammar.source` — The complete grammar is given in **Annex A**, which
is generated from the single canonical source `binate.ebnf`. The productions
relevant to a construct are also inlined at the head of that construct's
section (the **Grammar** part of the rubric, §4.2). Where an inlined
production and Annex A could disagree, Annex A governs; where the grammar and
this document's prose could disagree, **the prose governs** until the grammar
reconciliation pass (see Annex A) completes.

> _Note._ The retired grammar annotations `[BOOTSTRAP]` and `[DEFERRED]`
> tracked a now-removed Go-interpreter subset; they are **not** part of this
> metalanguage and do not appear in the normative grammar.

## 4.2 Per-construct presentation rubric

`notation.rubric` — Each feature is presented in a fixed order. A part is
omitted when it is empty (e.g. a construct with no static constraints has no
**Constraints** part).

1. **Grammar** _(normative)_ — the relevant EBNF productions, inlined from
   `binate.ebnf`.
2. **Constraints** _(normative)_ — the statically diagnosable rules a
   conforming implementation must enforce, i.e. the conditions under which a
   program is rejected. These correspond to compiler diagnostics, to the
   checks an interpreter defers to load or run time, and to **negative
   conformance tests** (a program plus the diagnostics it must produce).
3. **Static semantics** _(normative)_ — typing, name resolution, and other
   compile-time meaning that is not itself a rejection rule.
4. **Dynamic semantics** _(normative)_ — run-time behavior, including any
   reference-count or ownership effects (Ch.18) and any defined difference
   between compiled and interpreted execution.
5. **Exceptions** _(normative)_ — the enumerated run-time error conditions and
   any behavior left undefined (Ch.21).
6. **Notes / Examples** _(informative)_ — clarification, examples, and
   pointers; never binding.

## 4.3 Normative and informative text; requirement vocabulary

`notation.normative.default` — All text in the body chapters and in normative
annexes is **normative** unless explicitly marked informative. Informative
content appears only in blocks labelled **Note**, **Example**, or
**Rationale**, and in annexes labelled _(informative)_. Design rationale is
confined to **Annex D** and to Note blocks; it never appears in normative
prose.

`notation.requirement.terms` — The verbal forms below have precise meaning. A
conforming implementation (Ch.2):

- **shall** / **shall not** — an absolute requirement / prohibition.
- **should** / **should not** — a recommendation: valid reasons may exist to
  deviate, but the full implications must be understood.
- **may** — an optional, permitted behavior; **need not** marks the absence of
  a requirement.

The present indicative ("a string literal *has* default type …") states a
requirement equivalent to **shall**.

## 4.4 Stability-status legend

`notation.status.axes` — Status is tracked on two axes that are **orthogonal**
to the normative/informative distinction (a Draft rule is still
normative-in-intent). Every chapter and section carries a status badge; a rule
may override its section's badge.

**Axis 1 — language-design stability:**

- **Stable** — the semantics are fixed; changes would be breaking and are rare.
- **Provisional** — specified and implemented, but the design may still change.
- **Draft** — specified but only partially or not yet implemented;
  normative-in-intent.
- **Reserved** — syntax or a feature is reserved with semantics not yet
  defined.

**Axis 2 — implementation-conformance:** whether the current toolchain
actually conforms to a rule. A known miscompile does **not** make a rule
unstable on Axis 1; it makes the *implementation* non-conformant. This axis is
derived from **spec conformance test** results (pass / expected-failure per
execution mode; Ch.2) together with the project defect ledger, and is
recorded in **Annex C** with cross-references.

## 4.5 Rule identifiers and cross-referencing

`notation.ruleid` — Every normative statement carries a stable **rule
identifier** of the form `<prefix>.<area>.<name>` (for example
`type.slice.layout`, `mem.ownership.transfer`, `iface.dispatch.multireturn`).
Each chapter owns a prefix (the table is in [`conventions.md`](conventions.md);
e.g. Ch.5 = `lex`, Ch.7 = `type`, Ch.18 = `mem`).

`notation.ruleid.stability` — Rule identifiers are **stable**: they are the
target for cross-references and for **spec-conformance-test citations**, and
they are preserved across edits and renumbering. A reference is written as the
identifier (optionally with a section pointer), e.g. "see `mem.ownership.transfer`
(§18.5)", never as a bare section number. Each rule has exactly one normative
home; other sites cross-reference it rather than restating it.

## 4.6 Notation for dynamic semantics

`notation.operational` — Run-time behavior is specified in prose. For the
behaviors that are most error-prone or where the two execution modes must
provably agree — the reference-counting lifecycle and ownership transfer
(Ch.18) and dual-mode dispatch (Ch.19) — the prose is supplemented by a
lightweight **operational** description over an abstract machine state
(a store mapping locations to values, a heap of managed allocations, and a
reference count `rc(o)` per managed allocation `o`; Ch.19). Where both a prose
statement and an operational rule are given, **the prose is authoritative**
unless that rule explicitly states otherwise.

> _Example (form only)._ An ownership transfer on return is described in prose
> ("the returned reference carries one count to the caller, which becomes
> responsible for releasing it") and, alongside, as an operational effect on
> the abstract machine (`rc` is unchanged across the return; responsibility to
> `RefDec` moves from callee to caller). The prose governs.
