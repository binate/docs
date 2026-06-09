# 16. Packages and Program Structure
> **Status:** mixed · **Maturity:** Stable core  
> **Rule-ID prefix:** `pkg`  
> **Primary sources (explorations/):** claude-notes.md (packages; visibility; naming); plan-package-search-paths.md; pkg-layout-spec.md  
> Full chapter scope & status caveats: `explorations/plan-language-spec.md` §5.

> _Stub — not yet authored._ Author with the per-construct rubric in [`conventions.md`](conventions.md) (Grammar → Constraints → Static semantics → Dynamic semantics → Exceptions → Notes/Examples). Every normative statement carries a stable rule-ID under the prefix above — the citation target for spec conformance tests.

## Scope notes

- package "path"; .bn + at-most-one .bni; sibling-directory layout; imports; structural visibility (exported iff in .bni); .bni contents (incl. opaque types, generic bodies); main; the two -I/-L search paths + --root; symbol mangling (informative ABI -> Annex B); *_test.bn reservation (testing package surface is §20.4).
- Tier layout largely aspirational -> informative. GAP: import cycles — spec must add a rule.

## Rules

_TODO._
