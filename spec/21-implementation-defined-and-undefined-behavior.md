# 21. Implementation-defined, Unspecified, and Undefined Behavior
> **Status:** normative · **Maturity:** Contracts Stable  
> **Rule-ID prefix:** `behavior`  
> **Primary sources (explorations/):** C-standard §3 + Annex J; Rust Reference; ir-backend-guidelines.md; claude-notes.md (target parameterization)  
> Full chapter scope & status caveats: `explorations/plan-language-spec.md` §5.

> _Stub — not yet authored._ Author with the per-construct rubric in [`conventions.md`](conventions.md) (Grammar → Constraints → Static semantics → Dynamic semantics → Exceptions → Notes/Examples). Every normative statement carries a stable rule-ID under the prefix above — the citation target for spec conformance tests.

## Scope notes

- Implementation-defined (must be documented; compiled & interpreted modes must AGREE on a target): word/pointer/int size, alignment, struct padding/offsets, the concrete byte layout of raw slice / managed-slice / interface-value / function-value / managed-pointer header, byte order/endianness (a GAP — spec MUST decide), int64/float availability, sentinel refcount value, panic message/exit-code, symbol decoration. State target-INVARIANT structure (managed-slice = exactly 4 words) and parameterize sizes by TargetInfo.
- Unspecified: evaluation order where unpinned, padding contents, inline-vs-runtime-call, shared-static-literal storage.
- Undefined (raw-pointer/refcount escape hatch, fenced as USER error): UAF via a borrowed raw slice/pointer outliving its backing, dangling *T deref, refcount-invariant violation via raw aliasing, bit_cast/unsafe_* out of contract, mode-dependence beyond the one-indirection cost.

## Rules

_TODO._
