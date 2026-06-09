# 18. Memory Model: Reference Counting and Object Lifetime
> **Status:** mixed · **Maturity:** Stable axioms; sentinel Draft  
> **Rule-ID prefix:** `mem`  
> **Primary sources (explorations/):** design-refcount-axioms.md; refcount-lifecycle.md; ownership-model-managed-params.md; claude-notes.md; plan-static-managed-sentinel.md; plan-len0-no-backing.md  
> Full chapter scope & status caveats: `explorations/plan-language-spec.md` §5.

> _Stub — not yet authored._ Author with the per-construct rubric in [`conventions.md`](conventions.md) (Grammar → Constraints → Static semantics → Dynamic semantics → Exceptions → Notes/Examples). Every normative statement carries a stable rule-ID under the prefix above — the citation target for spec conformance tests.

## Scope notes

- Reference counting (no GC, no ownership/borrowing; cycles leak = programmer error); the refcount axioms; managed-allocation header + destructor-vs-free-function separation; recursive deterministic drop; ownership transfer; statement-level temporary lifetime (temp-borrow UAF is USER error — compiler shall not suppress RefDec); managed-slice lifetime + length-0 tie-in; static-managed sentinel; threading/atomicity stance (single-threaded default, non-atomic v1).
- Draft: static-managed sentinel (in-flight; value unfinalized). Proposed (out of normative core): move-as-guarantee (recommendation: optimization only), the move builtin, debug lifecycle hooks. Mechanism detail -> Annex B.
- Use prose + formal operational-rule dual presentation for the hardest rules.

## Rules

_TODO._
