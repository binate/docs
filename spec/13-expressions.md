# 13. Expressions
> **Status:** normative · **Maturity:** Stable (comparability gaps)  
> **Rule-ID prefix:** `expr`  
> **Primary sources (explorations/):** grammar.ebnf §8/§9/§10; claude-notes.md (operators); plan-divide-by-zero.md; plan-floats.md; plan-same-builtin.md  
> Full chapter scope & status caveats: `explorations/plan-language-spec.md` §5.

> _Stub — not yet authored._ Author with the per-construct rubric in [`conventions.md`](conventions.md) (Grammar → Constraints → Static semantics → Dynamic semantics → Exceptions → Notes/Examples). Every normative statement carries a stable rule-ID under the prefix above — the citation target for spec conformance tests.

## Scope notes

- Operands, primaries, operators; the grammar's 11-level Go-style precedence is AUTHORITATIVE over the conflicting notes prose; defined arithmetic (no UB); div/mod-by-zero + signed-MIN/-1 as defined panics; comparison (no chaining; IEEE-754 incl. unordered-!=); short-circuit logical; selectors (. only, auto-deref, no ->); index/slice + bounds; composite literals; D1-D11; no operator overloading.
- ==/!= on aggregates (struct/array) AND interface values is DISALLOWED by design (a defined Constraint); rejection LANDED (binate 60719e01/78af9c23). Equality via explicit methods (Compare/Equatable), present()/same, or errors.Is; sentinel identity (err==io.EOF) via io.IsEOF/errors.Is/same, not ==.
- FLAG (MAJOR): cyclic non-struct named types hang the comparability checker (compiler-DoS).

## Rules

_TODO._
