# 7. Types
> **Status:** mixed · **Maturity:** mostly Stable (caveats)  
> **Rule-ID prefix:** `type`  
> **Primary sources (explorations/):** claude-notes.md (value/reference; slices; readonly); plan-type-decls.md; plan-len0-no-backing.md; ir-backend-guidelines.md (layout)  
> Full chapter scope & status caveats: `explorations/plan-language-spec.md` §5.

> _Stub — not yet authored._ Author with the per-construct rubric in [`conventions.md`](conventions.md) (Grammar → Constraints → Static semantics → Dynamic semantics → Exceptions → Notes/Examples). Every normative statement carries a stable rule-ID under the prefix above — the citation target for spec conformance tests.

## Scope notes

- Catalogue, then §7.13 Type Layout & Representation — the single normative home for the cross-mode ABI contract, parameterized by TargetInfo.
- Managed-slice @[]T is 4 words {data,len,backing,backingLen}; raw slice *[]T is 2 words.
- Opaque (forward-declared) types: Stable/shipped (conformance/512). Field access gated on a VISIBLE/CONCRETE underlying; opaque (nil underlying) -> field access permanently rejected.
- Named-distinct field access: §7.3 v1 REJECTS (D5); target = Go's rule (fields incl. auto-deref through a pointer underlying; methods never auto-inherited).
- Provisional/Draft: interface-value byte layout; length-0-no-backing ENFORCEMENT (rule Stable, some backends still violate). Impl-conformance: nested arrays mis-compiled (claude-todo MAJOR).

## Rules

_TODO._
