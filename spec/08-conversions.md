# 8. Conversions
> **Status:** normative · **Maturity:** Stable  
> **Rule-ID prefix:** `conv`  
> **Primary sources (explorations/):** claude-notes.md (conversions & literals; cast); plan-const-type-modifier.md; proposal-restrict-implicit-raw-conversion.md  
> Full chapter scope & status caveats: `explorations/plan-language-spec.md` §5.

> _Stub — not yet authored._ Author with the per-construct rubric in [`conventions.md`](conventions.md) (Grammar → Constraints → Static semantics → Dynamic semantics → Exceptions → Notes/Examples). Every normative statement carries a stable rule-ID under the prefix above — the citation target for spec conformance tests.

## Scope notes

- Closed set of implicit conversions: untyped-literal coercion, readonly-adding widenings, the managed->raw borrow. No implicit numeric/named conversions.
- Explicit cast (value conversion; literal fit-checking; runtime wrap/truncate; drops readonly) and bit_cast (bit reinterpretation).
- PROVISIONAL: the implicit @T->*T / @[]T->*[]T borrow is permissive in all positions today; a proposal would restrict it to borrowing positions.

## Rules

_TODO._
