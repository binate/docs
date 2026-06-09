# 11. Interfaces, impl, and Self
> **Status:** mixed · **Maturity:** Stable design; known dispatch defects  
> **Rule-ID prefix:** `iface`  
> **Primary sources (explorations/):** plan-interface-syntax-revision.md; claude-notes.md (interfaces; Self; any; extension); plan-{interface-embedding,pointers-to-iface-values,cross-package-interfaces,primitives-impl-interfaces}.md  
> Full chapter scope & status caveats: `explorations/plan-language-spec.md` §5.

> _Stub — not yet authored._ Author with the per-construct rubric in [`conventions.md`](conventions.md) (Grammar → Constraints → Static semantics → Dynamic semantics → Exceptions → Notes/Examples). Every normative statement carries a stable rule-ID under the prefix above — the citation target for spec conformance tests.

## Scope notes

- Interface declarations (bare name is not a type); *Iface/@Iface values + pointers to them; impl (relational, separate, nominal explicit satisfaction); construction-site conversions + boxing; any/*any/@any; extension/embedding + transitive impl; Self + object-safety; interface aliases; cross-package interfaces (no orphan rule).
- Canonical interfaces Compare/String/Hash are DEFINED in §20.1 (pkg/builtins/lang).
- Impl-conformance (per-subsection overrides): interface-method MULTI-RETURN dispatch CRITICAL-broken; transitive re-export -> SIGSEGV (CRITICAL); sub-word multi-return mis-unpacked (claude-todo 2026-06-08). Interface-value byte layout Provisional.

## Rules

_TODO._
