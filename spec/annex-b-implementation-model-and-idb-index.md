# B. Implementation Model and Implementation-defined Index
> **Status:** mixed · **Maturity:** Split Stable  
> **Rule-ID prefix:** `impl`  
> **Primary sources (explorations/):** ir-backend-guidelines.md (the authoritative split); plan-multi-backend-layout.md; plan-backend-objformat-decoupling.md; C Annex J (index model)  
> Full chapter scope & status caveats: `explorations/plan-language-spec.md` §5.

> _Stub — not yet authored._ Author with the per-construct rubric in [`conventions.md`](conventions.md) (Grammar → Constraints → Static semantics → Dynamic semantics → Exceptions → Notes/Examples). Every normative statement carries a stable rule-ID under the prefix above — the citation target for spec conformance tests.

## Scope notes

- (Informative) runtime/ABI contracts observable in consequence but not mechanism: vtable layout, value-receiver thunks, weak_odr dedup, destructor/handle-dispatch, name mangling + object-format symbol decoration, the IR/backend split, and the observable-ABI-vs-backend-private boundary.
- (Normative index) the Annex-J-style reverse index from each impl-defined/unspecified/undefined point to its defining section + a target-word-size-dependent-points table.
- FLAG the OPEN mangler class (struct types not carrying fully-qualified names; genMethodValue cross-package value receiver); the specific reflect.Package collision was FIXED 2026-06-08.

## Rules

_TODO._
