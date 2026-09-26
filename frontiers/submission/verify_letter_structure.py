#!/usr/bin/env python3
"""Structural check on the reviewer response letters.

Written after three paragraphs of the reviewers' own prose were found sitting unattributed in
letters signed by the authors: each reviewer's opening assessment above Q1, and Reviewer 3's
closing assessment stranded directly under the Q9 response, where it read as the authors
calling their own paper "obscured by excessive qualification". Removing the "Your opening
assessment" labels had left the paragraphs behind. A reference checker cannot see this, because
every number in those paragraphs is fine.

Checks, per letter:
  1. two title lines, then the first paragraph is the Q1 heading  (no orphan opening)
  2. Q headings number 1..n with no gaps or repeats
  3. each Q block contains exactly one "Authors response :" marker
  4. each Q heading is the reviewer's own topic sentence, verbatim from docs/reviewer_N_report.txt
  5. no reviewer-voice phrasing inside an authors' response  (catches stranded reviewer prose)

Exits 1 on any failure, and exits 1 if it made no assertions.
"""
import re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
# First person and second-person-about-the-authors: a reviewer writing, never the authors.
REVIEWER_VOICE = [
    r"\bI recommend\b", r"\bI believe\b", r"\bI particularly\b", r"\bI suggest\b",
    r"\bI would (?:recommend|suggest|encourage)\b", r"\bthe authors should\b",
    r"\bthe authors deserve\b", r"\bthe authors could\b", r"\bthe authors obtain\b",
    r"\bthe authors are encouraged\b", r"\bwould allow the authors\b",
    r"\brequires substantial revision\b", r"\bbefore it is ready for publication\b",
]


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", s.lower())).strip()


def main():
    checks = bad = 0

    def ok(cond, msg):
        nonlocal checks, bad
        checks += 1
        if not cond:
            bad += 1
        print(f"   {'ok  ' if cond else 'FAIL'} {msg}")

    letters = sorted(HERE.glob("response_reviewer_*.txt"))
    if not letters:
        sys.exit("no response letters found")

    for letter in letters:
        num = re.search(r"_(\d+)\.txt$", letter.name).group(1)
        print(f"-- {letter.name}")
        paras = [p for p in letter.read_text(encoding="utf-8").split("\n\n") if p.strip()]

        head = paras[0].splitlines()
        ok(len(head) == 2 and head[0].startswith("RESPONSE TO REVIEWER"),
           "letter opens with a two-line title block")
        ok(len(paras) > 1 and paras[1].lstrip().startswith("Q1."),
           "first paragraph after the title is the Q1 heading, not an unattributed assessment")

        # split into Q blocks
        text = "\n\n".join(paras)
        starts = [(m.start(), int(m.group(1))) for m in re.finditer(r"^Q(\d+)\.", text, re.M)]
        nums = [n for _, n in starts]
        ok(nums == list(range(1, len(nums) + 1)),
           f"Q headings run 1..{len(nums)} with no gaps or repeats (got {nums})")

        report = ROOT / "docs" / f"reviewer_{num}_report.txt"
        src = {}
        if report.exists():
            src = {k: " ".join(v.split()) for k, v in
                   re.findall(r"^\s{0,3}(\d+)\.\s+(.*?)(?=\n\n)", report.read_text(encoding="utf-8"), re.M | re.S)}
        ok(bool(src), f"reviewer topic sentences available from {report.name}")

        for i, (pos, n) in enumerate(starts):
            end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
            block = text[pos:end]
            heading = " ".join(re.match(r"Q\d+\.\s*(.*?)(?=\n\n)", block, re.S).group(1).split())
            ok(norm(heading) == norm(src.get(str(n), "")),
               f"Q{n} heading is the reviewer's own sentence, verbatim")
            markers = re.findall(r"^Authors response :", block, re.M)
            ok(len(markers) == 1, f"Q{n} has exactly one 'Authors response :' marker")
            if len(markers) == 1:
                # Collapse the 98-column wrap first. With literal spaces in the patterns,
                # "would\nallow the authors" did not match "would allow the authors", so the
                # stranded paragraph this check exists to find went undetected.
                response = " ".join(block.split("Authors response :", 1)[1].split())
                hits = [m for pat in REVIEWER_VOICE for m in re.findall(pat, response, re.I)]
                ok(not hits, f"Q{n} response is free of reviewer-voice prose"
                             + (f" (found: {sorted(set(h.lower() for h in hits))})" if hits else ""))

    print(f"\n{checks} structural assertions, {bad} failed")
    if checks == 0:
        sys.exit("VACUOUS: no assertions ran, refusing to report a pass")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
