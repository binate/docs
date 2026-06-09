# 15. Built-in Operations
> **Status:** normative · **Maturity:** mostly Stable  
> **Rule-ID prefix:** `builtin`  
> **Primary sources (explorations/):** claude-notes.md (make/make_slice/box; cast/bit_cast/sizeof/alignof); plan-divide-by-zero.md; plan-same-builtin.md  
> Full chapter scope & status caveats: `explorations/plan-language-spec.md` §5.

> _Stub — not yet authored._ Author with the per-construct rubric in [`conventions.md`](conventions.md) (Grammar → Constraints → Static semantics → Dynamic semantics → Exceptions → Notes/Examples). Every normative statement carries a stable rule-ID under the prefix above — the citation target for spec conformance tests.

## Scope notes

- Allocation (make, make_slice, box); conversions (cast, bit_cast -> Ch.8); size/layout (sizeof, alignof, len); unchecked (unsafe_index, unsafe_div, unsafe_rem); identity/presence (same, present); volatile-access builtins; managed-representation introspection.
- present() extended to func values (vtable field 0), pointers (non-null), slices (len>0); value types rejected — DONE (binate 29c9dc47, conformance 667). move/ispod are PROPOSED -> Annex D.

## Rules

_TODO._
