"""a19_no_stale_names.py — fail if a retired project name or a dead path survives anywhere.

This exists because the old title kept reappearing after each "it's fixed" pass. The reason
was always the same: I searched for one spelling and declared the class clean. The full
title was replaced while the bare name "Disclosed Intelligence" stayed in headings; the
bare name was replaced while the sentence-cased "Disclosed intelligence" stayed in the
BibTeX entry that the manuscript actually prints in its reference list.

So the search is defined once, case-insensitively, across every text file in the tree, with
an explicit allowlist of the places a retired string legitimately survives. Anything else is
a failure.

Usage:  cd "Paper 10" && python analysis/a19_no_stale_names.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Strings that must no longer appear, matched case-insensitively.
RETIRED = [
    "disclosed intelligence",
    "disclosed-intelligence",
    "a large-sample measurement of ai disclosure",
    "samirrc2/disclosed-intelligence",
]

# Paths where a retired string is correct and must stay. Every entry needs a reason.
ALLOWED = {
    "frontiers/submission/manuscript_v1_as_submitted.tex":
        "frozen copy of what the journal received; must not be edited",
    "frontiers/submission/references_v1_as_submitted.bib":
        "frozen bibliography for that submitted version",
    "frontiers/submission/manuscript_tracked.tex":
        "generated latexdiff of v1 against the current text",
    "frontiers/submission/manuscript_tracked.bbl":
        "generated bibliography for the tracked diff",
    "frontiers/submission/manuscript_v1_as_submitted.bbl":
        "frozen bibliography for the submitted version",
    "capsule/code/src/analyze.py":
        "svg.hashsalt constant: changing it changes every committed figure's bytes",
    "analysis/a19_no_stale_names.py":
        "this checker necessarily contains the strings it searches for",
}

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv"}
SKIP_EXT = {".png", ".jpg", ".jpeg", ".pdf", ".docx", ".zip", ".eps", ".svg",
            ".gz", ".tgz", ".ico", ".woff", ".woff2", ".ttf"}


def main():
    scanned = hits = 0
    failures = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            path = os.path.join(base, fn)
            rel = os.path.relpath(path, ROOT)
            if os.path.splitext(fn)[1].lower() in SKIP_EXT:
                continue
            # results/ is regenerated from code; its content is covered by the other checks
            if rel.startswith("capsule/results/") or rel.startswith("analysis/out/"):
                continue
            try:
                text = open(path, encoding="utf-8", errors="strict").read()
            except (UnicodeDecodeError, OSError):
                continue
            scanned += 1
            low = text.lower()
            found = [s for s in RETIRED if s in low]
            if not found:
                continue
            if rel in ALLOWED:
                hits += 1
                continue
            for s in found:
                for m in re.finditer(re.escape(s), low):
                    line = text.count("\n", 0, m.start()) + 1
                    snippet = re.sub(r"\s+", " ", text[m.start():m.start() + 70]).strip()
                    failures.append(f"{rel}:{line}: {snippet}")

    print(f"   scanned {scanned} text files")
    print(f"   {hits} allowlisted file(s) legitimately retain a retired string:")
    for rel, why in sorted(ALLOWED.items()):
        print(f"      {rel} — {why}")
    if failures:
        print(f"\n   {len(failures)} stale occurrence(s):")
        for f in failures:
            print(f"      {f}")
        sys.exit(1)
    if scanned == 0:
        sys.exit("VACUOUS: scanned no files")
    print("\n   PASS — no retired project name outside the allowlist")


if __name__ == "__main__":
    main()
