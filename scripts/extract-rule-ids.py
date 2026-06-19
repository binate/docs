#!/usr/bin/env python3
"""Extract the spec's declared rule-IDs into a machine-readable export.

`rule-ids.txt` is a GENERATED artifact: it lists every normative rule-ID the
specification declares, each tagged with a coverage **bucket**, so that the
spec-conformance tooling in the `binate` repo (`scripts/spec-coverage`) can map
rule-IDs ↔ tests **without** reading `docs/spec/*.md` directly. That decoupling
is the point — the two repos couple only on stable rule-IDs, never on prose or
file paths (plan-spec-tests.md §2, §5.1).

A rule-ID is *declared* (as opposed to merely *referenced* mid-prose) by a
**column-0** line of the form

    `<prefix>.<area>.<name>` — ...

i.e. a backticked rule-ID at the start of a line, followed by an em-dash lede
(optionally with an ` _(Constraint)_` marker in between). Verified repo-wide:
every declaration matches this shape and none hide in lists/tables/blockquotes,
so the col-0 detector is complete. Backtick mentions elsewhere in prose are
references and are ignored.

Buckets (each rule lands in exactly one; see plan-spec-tests.md §4):
  framework            — excluded from the coverage denominator (metalanguage /
                         definitions / back-reference index): prefixes `term`,
                         `notation`, `behavior`.
  untestable           — non-observable by construction (move elision, release
                         order, …); an explicit, deliberately-minimal allowlist.
  constraint           — carries an explicit `_(Constraint)_` marker: a
                         diagnosable static rule that must be REJECTED (`.error`).
  constraint-candidate — body matches a reject-signal phrase ("is rejected", "is
                         an error", "compile-time error", …) but has no explicit
                         marker: probably needs a negative test; flagged for a
                         human to confirm and (ideally) for the spec to mark.
  positive             — default: defined behavior, assert the observable result.

The allowlist is intentionally small: under-allowlisting makes a truly-untestable
rule surface as a coverage *gap* (a human then moves it here), which is the safe
direction — over-allowlisting would silently hide real gaps.

Usage:
    python3 docs/scripts/extract-rule-ids.py            # write rule-ids.txt
    python3 docs/scripts/extract-rule-ids.py --check     # exit non-zero if stale

Run it after editing the spec's rule-IDs. (Intentionally NOT wired into CI here —
wiring is a separate decision.)
"""

import re
import sys
from pathlib import Path

SPEC_DIR = Path(__file__).resolve().parent.parent / "spec"
OUT_PATH = SPEC_DIR / "rule-ids.txt"

# The chapter rule-ID prefixes (conventions.md / §4.5). A real rule-ID always
# carries one of these — used to reject backticked code identifiers (e.g. the
# member-access example `x.name`) that share the dotted shape.
KNOWN_PREFIXES = {
    "conf", "term", "notation", "lex", "const", "type", "conv", "decl", "func",
    "iface", "gen", "expr", "stmt", "builtin", "pkg", "pkg0", "prog", "mem",
    "exec", "behavior", "grammar", "impl",
}

# A declaration is a **column-0** line whose lead is one or more backticked
# rule-IDs (`A` or `A` / `B` for a shared declaration), optionally followed by
# `_(...)_` qualifier markers (`_(Constraint)_`, `_(operational)_`,
# `_(normative)_`, `_(Provisional)_`, `_(Draft — …)_`, …), then a lede that is
# either an em-dash / en-dash / hyphen (possibly at end-of-line, when the prose
# wraps) or a `(**bold gloss**)` (the lone Ch.3 `term.alias` shape).
# A rule-ID is `<prefix>.<seg>(.<seg>)*`.
RULEID = r"`[a-z][a-z0-9]*(?:\.[a-z0-9-]+)+`"
LEAD_RE = re.compile(
    r"^(?P<ids>" + RULEID + r"(?:\s*/\s*" + RULEID + r")*)"
    r"(?P<markers>(?:\s*_\([^)]*\)_)*)"
    r"(?:\s*[—–-](?:\s|$)|\s+\(\*\*[^*]+\*\*\)\s)"
)
ID_RE = re.compile(r"`([a-z][a-z0-9]*(?:\.[a-z0-9-]+)+)`")
# A line that *looks* like a declaration (col-0 backticked known-prefix rule-ID
# followed by space / marker / multi-ID slash / EOL — not immediate punctuation,
# which marks a wrapped reference) but that LEAD_RE failed to parse. Surfaced as
# a warning so a new non-conforming declaration shape can never be dropped
# silently. (Empty on the current tree.)
SUSPECT_RE = re.compile(r"^(`[a-z][a-z0-9]*(?:\.[a-z0-9-]+)+`)(?=\s|_|/|$)")
HEADING_RE = re.compile(r"^#")


def known(rule_id):
    return rule_id.split(".", 1)[0] in KNOWN_PREFIXES

# Prefixes whose chapters are framework/informative (Ch.3 Terms, Ch.4 Notation,
# Ch.21 Behavior back-reference index) — excluded from the denominator (§4).
FRAMEWORK_PREFIXES = {"term", "notation", "behavior"}

# Non-observable rules (no test possible/meaningful). Deliberately minimal; grows
# as each chapter is triaged during Phase B. See the module docstring.
UNTESTABLE_ALLOWLIST = {
    "mem.move.optimization",  # move elision is an unobservable optimization
    "mem.scope-exit",         # intra-scope release *order* is unobservable
}

# Prose signals that a rule names a must-reject / error case (the other half of
# the negative-testable bucket, per §4, beyond the explicit `_(Constraint)_`
# marker). Matched case-insensitively against the rule's body.
REJECT_RE = re.compile(
    r"\b("
    r"is rejected|are rejected|be rejected|shall be rejected|must reject|"
    r"is an error|is a compile(?:-time)? error|compile-time error|"
    r"is illegal|is invalid|is not allowed|are not allowed|not permitted"
    r")\b",
    re.IGNORECASE,
)


def find_declarations(text):
    """Yield (rule_id, is_constraint, body_text) for each col-0 declaration.

    A declaration *line* may declare several rule-IDs (the `A` / `B — …` shared
    form); they all share one body. `body_text` runs from the declaration line up
    to (not including) the next declaration line or markdown heading — the rule's
    prose, used for the reject-signal scan. Boundaries are taken on declaration
    *lines*, not per-ID, so shared declarations don't yield empty bodies.
    """
    lines = text.splitlines()
    n = len(lines)
    decl_lines = []  # (line_index, [rule_id, ...], is_constraint)
    for i, line in enumerate(lines):
        m = LEAD_RE.match(line)
        if m:
            ids = [x for x in ID_RE.findall(m.group("ids")) if known(x)]
            if ids:
                decl_lines.append((i, ids, "_(Constraint)_" in m.group("markers")))
    for k, (start, ids, is_constraint) in enumerate(decl_lines):
        end = decl_lines[k + 1][0] if k + 1 < len(decl_lines) else n
        j = start + 1
        while j < end:
            if HEADING_RE.match(lines[j]):
                end = j
                break
            j += 1
        body = "\n".join(lines[start:end])
        for rule_id in ids:
            yield rule_id, is_constraint, body


def bucket_for(rule_id, is_constraint, body):
    prefix = rule_id.split(".", 1)[0]
    if prefix in FRAMEWORK_PREFIXES:
        return "framework"
    if rule_id in UNTESTABLE_ALLOWLIST:
        return "untestable"
    if is_constraint:
        return "constraint"
    if REJECT_RE.search(body):
        return "constraint-candidate"
    return "positive"


def find_suspects(text, captured):
    """Return col-0 lines that look like declarations but weren't captured."""
    out = []
    for line in text.splitlines():
        m = SUSPECT_RE.match(line)
        if not m:
            continue
        rule_id = m.group(1).strip("`")
        if known(rule_id) and rule_id not in captured and not LEAD_RE.match(line):
            out.append(line)
    return out


def collect():
    """Return (rows, duplicates, suspects). rows = sorted [(id, bucket, source)]."""
    seen = {}
    duplicates = []
    suspects = []
    for path in sorted(SPEC_DIR.glob("*.md")):
        text = path.read_text()
        for rule_id, is_constraint, body in find_declarations(text):
            if rule_id in seen:
                duplicates.append((rule_id, path.name, seen[rule_id][2]))
                continue
            seen[rule_id] = (rule_id, bucket_for(rule_id, is_constraint, body), path.name)
        suspects += [(path.name, ln) for ln in find_suspects(text, set(seen))]
    rows = sorted(seen.values())
    return rows, duplicates, suspects


def render(rows):
    out = [
        "# Declared rule-IDs, with coverage buckets.  GENERATED — do not edit.",
        "# Source: docs/spec/*.md (col-0 `<rule-id>` — declarations).",
        "# Regenerate: python3 docs/scripts/extract-rule-ids.py",
        "# Format (tab-separated): <rule-id>\t<bucket>\t<source-file>",
        "# Buckets: positive | constraint | constraint-candidate | untestable | framework",
        "#   denominator (coverage %) = positive + constraint + constraint-candidate",
        "#   excluded                 = untestable + framework",
    ]
    for rule_id, bucket, source in rows:
        out.append(f"{rule_id}\t{bucket}\t{source}")
    return "\n".join(out) + "\n"


def summary(rows, duplicates):
    counts = {}
    for _, bucket, _ in rows:
        counts[bucket] = counts.get(bucket, 0) + 1
    denom = sum(counts.get(b, 0) for b in ("positive", "constraint", "constraint-candidate"))
    parts = ", ".join(f"{b}={counts.get(b, 0)}" for b in sorted(counts))
    msg = f"{len(rows)} rule-IDs ({parts}); denominator={denom}"
    if duplicates:
        msg += f"; WARNING: {len(duplicates)} duplicate declaration(s)"
    return msg


def main():
    check = "--check" in sys.argv[1:]
    if not SPEC_DIR.is_dir():
        sys.exit(f"error: spec dir not found at {SPEC_DIR}")
    rows, duplicates, suspects = collect()
    if not rows:
        sys.exit(f"error: no rule-ID declarations found under {SPEC_DIR} — "
                 "has the declaration format changed?")
    for rule_id, here, there in duplicates:
        print(f"warning: duplicate declaration of {rule_id} in {here} "
              f"(first seen in {there})", file=sys.stderr)
    for fname, line in suspects:
        print(f"warning: {fname}: line looks like a declaration but did not "
              f"parse (new lede shape?): {line}", file=sys.stderr)
    rendered = render(rows)
    if check:
        current = OUT_PATH.read_text() if OUT_PATH.exists() else ""
        if current != rendered:
            sys.exit(f"error: {OUT_PATH.name} is stale — re-run "
                     "scripts/extract-rule-ids.py")
        print(f"{OUT_PATH.name} is up to date — {summary(rows, duplicates)}")
        return
    OUT_PATH.write_text(rendered)
    print(f"wrote {OUT_PATH.name} — {summary(rows, duplicates)}")


if __name__ == "__main__":
    main()
