#!/usr/bin/env python3
"""Generate Annex A (Grammar Summary) from the canonical grammar.

Annex A is a GENERATED artifact: it presents the complete EBNF from the
canonical source `docs/spec/binate.ebnf` (specification Decision D4), split into
the same sections, plus the D1-D11 disambiguation summary. The canonical grammar
is the single source of truth; this script reproduces it as the spec's
human-facing annex so the two never drift by hand.

Usage:
    python3 docs/scripts/gen-annex-a.py            # write the annex
    python3 docs/scripts/gen-annex-a.py --check     # exit non-zero if stale

Run it after editing binate.ebnf. (It is intentionally NOT wired into CI here.)
"""

import re
import sys
from pathlib import Path

SPEC_DIR = Path(__file__).resolve().parent.parent / "spec"
EBNF_PATH = SPEC_DIR / "binate.ebnf"
ANNEX_PATH = SPEC_DIR / "annex-a-grammar-summary.md"

# A section banner is a comment line of only "=" (e.g. "(* ===== *)"); a section
# title is "(* N. Title *)" sandwiched between two banners.
BANNER_RE = re.compile(r"^\(\*\s*=+\s*\*\)\s*$")
TITLE_RE = re.compile(r"^\(\*\s*(\d+)\.\s*(.+?)\s*\*\)\s*$")


def parse_sections(text):
    """Return [(number, title, [content_lines])] for each "N. Title" section."""
    lines = text.splitlines()
    n = len(lines)

    def is_header(i):
        return (
            i + 2 < n
            and BANNER_RE.match(lines[i])
            and TITLE_RE.match(lines[i + 1])
            and BANNER_RE.match(lines[i + 2])
        )

    sections = []
    i = 0
    while i < n:
        if is_header(i):
            m = TITLE_RE.match(lines[i + 1])
            num, title = m.group(1), m.group(2)
            i += 3
            content = []
            while i < n and not is_header(i):
                content.append(lines[i])
                i += 1
            # Trim leading/trailing blank lines.
            while content and not content[0].strip():
                content.pop(0)
            while content and not content[-1].strip():
                content.pop()
            sections.append((num, title, content))
        else:
            i += 1
    return sections


def render(sections):
    out = []
    out.append("# A. Grammar Summary")
    out.append(
        "> **Status:** normative · **Maturity:** Stable (generated from "
        "`binate.ebnf`)  "
    )
    out.append("> **Rule-ID prefix:** `grammar`")
    out.append("")
    out.append(
        "> _**Generated file — do not edit by hand.**_ This annex is produced "
        "from the canonical grammar [`binate.ebnf`](binate.ebnf) by "
        "[`scripts/gen-annex-a.py`](../scripts/gen-annex-a.py) (specification "
        "Decision D4). `binate.ebnf` is the single source of truth; to change "
        "the grammar, edit it and re-run the generator. The per-feature-chapter "
        "inlined productions present the same grammar in context."
    )
    out.append("")
    out.append(
        "The metalanguage is ISO/IEC-14977-flavored EBNF, defined normatively in "
        "**Ch.4 Notation**: `=` definition, `|` alternation, `{}` repetition "
        "(zero or more), `[]` optional, `()` grouping, `…` inclusive character "
        "range, `;` rule terminator, `(* … *)` comment, `\"x\"` literal terminal, "
        "juxtaposition = concatenation."
    )
    out.append("")
    for num, title, content in sections:
        out.append(f"## A.{num} {title}")
        out.append("")
        out.append("```ebnf")
        out.extend(content)
        out.append("```")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main():
    check = "--check" in sys.argv[1:]
    if not EBNF_PATH.exists():
        sys.exit(f"error: canonical grammar not found at {EBNF_PATH}")
    sections = parse_sections(EBNF_PATH.read_text())
    if not sections:
        sys.exit(
            f"error: no '(* N. Title *)' sections found in {EBNF_PATH} — "
            "has the banner format changed?"
        )
    rendered = render(sections)
    if check:
        current = ANNEX_PATH.read_text() if ANNEX_PATH.exists() else ""
        if current != rendered:
            sys.exit(
                f"error: {ANNEX_PATH.name} is stale — re-run "
                "scripts/gen-annex-a.py"
            )
        print(f"{ANNEX_PATH.name} is up to date ({len(sections)} sections).")
        return
    ANNEX_PATH.write_text(rendered)
    print(f"wrote {ANNEX_PATH.name} ({len(sections)} sections) from {EBNF_PATH.name}")


if __name__ == "__main__":
    main()
