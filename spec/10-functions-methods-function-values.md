# 10. Functions, Methods, and Function Values
> **Status:** mixed · **Maturity:** Stable surface; function VALUES Provisional  
> **Rule-ID prefix:** `func`  
> **Primary sources (explorations/):** claude-notes.md (function/variadic/spread; method resolution; function values); plan-function-values*.md; detailed-notes §19.7  
> Full chapter scope & status caveats: `explorations/plan-language-spec.md` §5.

> _Stub — not yet authored._ Author with the per-construct rubric in [`conventions.md`](conventions.md) (Grammar → Constraints → Static semantics → Dynamic semantics → Exceptions → Notes/Examples). Every normative statement carries a stable rule-ID under the prefix above — the citation target for spec conformance tests.

## Scope notes

- Function declarations; single/multiple returns (position lists, not tuples) + destructuring; variadics + spread; methods, five receiver kinds, receiver smoothing (safe direction only), object- vs handle-readonly dispatch, one-method-per-name, one-level auto-deref.
- Function VALUES (*func/@func, 2-word repr; closures capture by value; escape via lint not type error; method expressions/values) — RECENT, Provisional.
- Impl-conformance: destructuring a multi-return @func() call rejected at type-check (claude-todo MAJOR). Recursive anonymous closures Reserved.

## Rules

_TODO._
