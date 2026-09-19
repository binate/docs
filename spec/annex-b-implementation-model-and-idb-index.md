# B. Implementation Model and Implementation-defined Index
> **Status:** mixed · **Maturity:** Split Stable  
> **Rule-ID prefix:** `impl`  
> **Primary sources (explorations/):** ir-backend-guidelines.md (the authoritative split); done/plan-multi-backend-layout.md; plan-backend-objformat-decoupling.md; C Annex J (index model)  
> Full chapter scope & status caveats: `explorations/plan-language-spec.md` §5.

> _Stub — not yet authored._ Author with the per-construct rubric in [`conventions.md`](conventions.md) (Grammar → Constraints → Static semantics → Dynamic semantics → Exceptions → Notes/Examples). Every normative statement carries a stable rule-ID under the prefix above — the citation target for spec conformance tests.

## Scope notes

- (Informative) runtime/ABI contracts observable in consequence but not mechanism: vtable layout, value-receiver thunks, weak_odr dedup, destructor/handle-dispatch, name mangling + object-format symbol decoration, the IR/backend split, and the observable-ABI-vs-backend-private boundary.
- (Normative index) the Annex-J-style reverse index from each impl-defined/unspecified/undefined point to its defining section + a target-word-size-dependent-points table.
- FLAG the OPEN mangler class: genMethodValue cross-package value receiver. The reflect.Package collision was FIXED 2026-06-08; the destructor/copy element-walk suffix (`__dtor_ms_…`/`__copy_ms_…`) non-injectivity — a nested struct written by bare leaf name, which both collided with same-leaf structs across packages AND let a struct adversarially named to spoof a kind token (`mp_`/`ms_`/…) shadow the wrapped type — was FIXED 2026-09-18 by encoding a nested struct/named type with the identifier-only, full-path length-prefixed `mangle.LpTypeArgNamedRaw` form (aligning the symbol with the §16.6 `pkg.identity` full-import-path identity). The same day the TOP-LEVEL struct dtor/copy leaf and the anonymous-struct suffix were made injective too (length-prefixed leaf token; per-field length-prefixed anon encoding replacing a hash fallback), so every `__dtor_`/`__copy_` symbol is now injective w.r.t. type identity.

## Rules

_TODO._
