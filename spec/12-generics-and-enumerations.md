# 12. Generics and Enumerations
> **Status:** normative · **Maturity:** Stable (v1 scope)  
> **Rule-ID prefix:** `gen`  
> **Primary sources (explorations/):** plan-generics.md; claude-notes.md (generics; enums); detailed-notes §19.8/§5  
> Full chapter scope & status caveats: `explorations/plan-language-spec.md` §5.

> _Stub — not yet authored._ Author with the per-construct rubric in [`conventions.md`](conventions.md) (Grammar → Constraints → Static semantics → Dynamic semantics → Exceptions → Notes/Examples). Every normative statement carries a stable rule-ID under the prefix above — the citation target for spec conformance tests.

## Scope notes

- Type parameters on functions/structs/interfaces (each constraint a single named interface; no '+'; [T any]); no generic methods; no conditional impls (v1); monomorphization (no type inference; explicit args; constraint calls -> direct calls); cross-package generic bodies in .bni (source-text).
- No first-class enums (named-int + const(...)+iota idiom); tagged unions are a separate future feature.
- Generic-instantiation '==' comparability gap OPEN (xref Ch.13).

## Rules

_TODO._
