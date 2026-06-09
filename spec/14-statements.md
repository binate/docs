# 14. Statements
> **Status:** normative · **Maturity:** Stable  
> **Rule-ID prefix:** `stmt`  
> **Primary sources (explorations/):** grammar.ebnf §7; claude-notes.md (assignment, inc/dec); detailed-notes (control flow)  
> Full chapter scope & status caveats: `explorations/plan-language-spec.md` §5.

> _Stub — not yet authored._ Author with the per-construct rubric in [`conventions.md`](conventions.md) (Grammar → Constraints → Static semantics → Dynamic semantics → Exceptions → Notes/Examples). Every normative statement carries a stable rule-ID under the prefix above — the citation target for spec conformance tests.

## Scope notes

- Block-local decls; simple statements; assignment (multi-target destructuring; compound); inc/dec (postfix-only); if; for (four forms incl. range, for-in value-vs-index differing from Go); switch (no fallthrough); return/break/continue (no labels/goto).
- Deliberate omissions: no if/for/switch init clause, no labeled break/continue, no goto, no fallthrough.

## Rules

_TODO._
