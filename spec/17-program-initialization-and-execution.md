# 17. Program Initialization and Execution
> **Status:** normative · **Maturity:** Stable  
> **Rule-ID prefix:** `prog`  
> **Primary sources (explorations/):** claude-notes.md (retained/immediate; init order; errors as values); grammar.ebnf §6 (annotations); plan-divide-by-zero.md  
> Full chapter scope & status caveats: `explorations/plan-language-spec.md` §5.

> _Stub — not yet authored._ Author with the per-construct rubric in [`conventions.md`](conventions.md) (Grammar → Constraints → Static semantics → Dynamic semantics → Exceptions → Notes/Examples). Every normative statement carries a stable rule-ID under the prefix above — the citation target for spec conformance tests.

## Scope notes

- Retained vs immediate evaluation (a non-REPL run is fully validated before execution via an external entry call); no forward declarations required; package init order (no init()); main entry + termination (host-dependent argv); the annotation system (#[...]); errors-as-values (no exceptions/panic-recover/defer); the closed set of defined non-recoverable runtime panics (bounds, divide-by-zero, MIN/-1).
- The standard annotation name/arg schemas are not enumerated in sources — must be supplied. Proposed annotation features -> Annex D.

## Rules

_TODO._
