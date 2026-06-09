# 5. Lexical Elements
> **Status:** normative · **Maturity:** mostly Stable  
> **Rule-ID prefix:** `lex`  
> **Primary sources (explorations/):** grammar.ebnf §1; claude-notes.md (literals; readonly keyword; adjacent concat; no-null)  
> Full chapter scope & status caveats: `explorations/plan-language-spec.md` §5.

> _Stub — not yet authored._ Author with the per-construct rubric in [`conventions.md`](conventions.md) (Grammar → Constraints → Static semantics → Dynamic semantics → Exceptions → Notes/Examples). Every normative statement carries a stable rule-ID under the prefix above — the citation target for spec conformance tests.

## Scope notes

- Identifiers; reserved keywords (incl. readonly) and builtin-operation keywords (make, make_slice, box, cast, bit_cast, len, unsafe_index, sizeof, alignof, same, present, unsafe_div, unsafe_rem); predeclared shadowable names.
- Literals + escapes (no implicit null terminator); adjacent string-literal concatenation; comments; automatic semicolon insertion.
- RECENT: 'readonly' keyword; grammar not yet fully updated (Phase-0).

## Rules

_TODO._
