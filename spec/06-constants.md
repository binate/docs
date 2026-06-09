# 6. Constants
> **Status:** normative · **Maturity:** Stable  
> **Rule-ID prefix:** `const`  
> **Primary sources (explorations/):** claude-notes.md (type conversions & literals; integer range DECIDED); plan-floats.md  
> Full chapter scope & status caveats: `explorations/plan-language-spec.md` §5.

> _Stub — not yet authored._ Author with the per-construct rubric in [`conventions.md`](conventions.md) (Grammar → Constraints → Static semantics → Dynamic semantics → Exceptions → Notes/Examples). Every normative statement carries a stable rule-ID under the prefix above — the citation target for spec conformance tests.

## Scope notes

- Untyped literals + default types (literal-only coercion). Integer constant value range + union-range constant arithmetic (intermediate overflow rejected).
- String-literal natural type [N]readonly char, default type @[]readonly char (D1, verified against pkg/binate/types).
- Untyped-float class; strict no-implicit-int<->float; literal overflow is a compile error.

## Rules

_TODO._
