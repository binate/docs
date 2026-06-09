# 20. Intrinsic (Tier-0) Packages
> **Status:** mixed · **Maturity:** lang Stable; rt/reflect/testing Draft/Provisional  
> **Rule-ID prefix:** `pkg0`  
> **Primary sources (explorations/):** claude-notes.md ('primary spec is minimal'); plan-primitives-impl-interfaces.md; plan-std-errors.md; notes-package-introspection.md  
> Full chapter scope & status caveats: `explorations/plan-language-spec.md` §5.

> _Stub — not yet authored._ Author with the per-construct rubric in [`conventions.md`](conventions.md) (Grammar → Constraints → Static semantics → Dynamic semantics → Exceptions → Notes/Examples). Every normative statement carries a stable rule-ID under the prefix above — the citation target for spec conformance tests.

## Scope notes

- §20.1 pkg/builtins/lang — canonical interfaces (Compare/String/Hash) + primitive impls. Fairly mature -> mostly Stable. (Normative home for the canonical-interface signatures, referenced by §11.10.)
- §20.2 pkg/builtins/rt — the runtime contract (minimal primitives; hosted vs freestanding). Draft — GATED on the pkg/rt review; the manifest is actively shrinking.
- §20.3 pkg/builtins/reflect — reflection/introspection surface. Draft/incomplete.
- §20.4 pkg/builtins/testing — testing-support surface (the *_test.bn name reservation is §16.9). Provisional.

## Rules

_TODO._
