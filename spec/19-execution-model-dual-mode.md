# 19. Execution Model: the Abstract Machine and Dual-Mode Interop
> **Status:** mixed · **Maturity:** Contract Stable; in-process embedding a goal  
> **Rule-ID prefix:** `exec`  
> **Primary sources (explorations/):** claude-notes.md (dual-mode interop; interpreter embedding); ir-backend-guidelines.md; runtime-abstraction-plan.md; plan-function-values-phase-3.md  
> Full chapter scope & status caveats: `explorations/plan-language-spec.md` §5.

> _Stub — not yet authored._ Author with the per-construct rubric in [`conventions.md`](conventions.md) (Grammar → Constraints → Static semantics → Dynamic semantics → Exceptions → Notes/Examples). Every normative statement carries a stable rule-ID under the prefix above — the citation target for spec conformance tests.

## Scope notes

- The abstract machine (shared heap + refcount metadata + a function-pointer call primitive both modes satisfy identically); function pointers as the unification mechanism (compiled=native/direct; interpreted=thunk; mode-oblivious caller; one-indirection cost only at the boundary); cross-mode prerequisites (identical layout per §7.13; no marshalling; .bni signature discovery + symbol resolution); the runtime function manifest (specified concretely in §20.2); multi-return value representation; enumerated cross-mode divergence points.
- D2: the thunk-unification mechanism + identical-layout prerequisite are the Stable design-of-record; the two engines pass conformance individually; SEAMLESS SAME-PROCESS IN-PROCESS EMBEDDING is a GOAL, not yet realized (bni is a partial step). The embedding API is a SEPARATE spec, out of scope.

## Rules

_TODO._
