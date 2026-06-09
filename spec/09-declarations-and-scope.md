# 9. Declarations and Scope
> **Status:** normative · **Maturity:** Stable  
> **Rule-ID prefix:** `decl`  
> **Primary sources (explorations/):** claude-notes.md (const/var/readonly split); plan-const-readonly.md; detailed-notes (scopes)  
> Full chapter scope & status caveats: `explorations/plan-language-spec.md` §5.

> _Stub — not yet authored._ Author with the per-construct rubric in [`conventions.md`](conventions.md) (Grammar → Constraints → Static semantics → Dynamic semantics → Exceptions → Notes/Examples). Every normative statement carries a stable rule-ID under the prefix above — the citation target for spec conformance tests.

## Scope notes

- const (compile-time, scalar-only, no storage) vs var (storage; .bni extern form) vs the readonly modifier; iota in grouped const blocks; ':=' + D1 disambiguation.
- Block scope + shadowing (suppressible warning); permitted package-scope decls (function-local 'type' is a parse error); init order (no init()).
- Grammar still spells the modifier 'const' (Phase-0 reconcile).

## Rules

_TODO._
