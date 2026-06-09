# D. Rationale and Design Notes
> **Status:** informative · **Maturity:** n/a  
> **Rule-ID prefix:** `rationale`  
> **Primary sources (explorations/):** claude-notes.md (philosophy; C-free end state); detailed-notes §30/§31; differences-with-go.md (incomplete); historical-notes.md  
> Full chapter scope & status caveats: `explorations/plan-language-spec.md` §5.

> _Stub — not yet authored._ Author with the per-construct rubric in [`conventions.md`](conventions.md) (Grammar → Constraints → Static semantics → Dynamic semantics → Exceptions → Notes/Examples). Every normative statement carries a stable rule-ID under the prefix above — the citation target for spec conformance tests.

## Scope notes

- Wholly informative — never binding. Why refcounting over GC and over ownership/borrowing; why two pointer kinds and two slice kinds; why a named-distinct type shares the underlying's FIELDS but not its METHODS/impls (fresh method/impl set per named type — the D5 basis, and why opaque forward-decls hide fields entirely); the no-implicit-cost philosophy; the minimal-core-spec / less-monolithic rationale; the v1-without-foreclosing-v2 deferrals; the extended Go comparison and prior art; the C-free-target posture and FFI-as-future-escape-hatch.
- The home for every PROPOSED/deferred item.

## Rules

_TODO._
