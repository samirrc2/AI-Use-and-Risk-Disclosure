#!/usr/bin/env python3
"""Verify every cross-reference in the reviewer response letters against manuscript.pdf.

This exists because the check it replaces was near-vacuous. The old version scraped every
1-3 digit number on a PDF page, took min/max as that page's "line band", and asked whether a
cited line number fell inside it. Pages carry percentages, counts and table cells, so the band
was effectively 1-999 and every reference passed, including ones that named the wrong section
entirely. Four stale references survived it.

What is actually checked here, per reference:
  * the cited line range lies wholly inside the span of the section it names
  * the cited page (p. N / pp. N-M) equals the pages those lines really fall on
  * table and figure page claims match where that float is actually typeset

Exits 1 on any mismatch, and also exits 1 if it made no assertions, so a parsing change that
silently stops finding references can never read as a pass.
"""
import json, re, sys
from pathlib import Path
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
PDF = HERE.parent / "manuscript.pdf"
LETTERS = sorted(HERE.glob("response_reviewer_*.txt"))


def line_map(pdf):
    """{line number: (page, text)} read from the lineno margin numbers."""
    out = {}
    for pi, page in enumerate(PdfReader(pdf).pages, 1):
        items = []
        page.extract_text(visitor_text=lambda t, cm, tm, fs, fd:
                          items.append((round(tm[5], 1), round(tm[4], 1), t)) if t.strip() else None)
        if not items:
            continue
        xmin = min(x for _, x, _ in items)
        marks = {int(t.strip()): y for y, x, t in items if t.strip().isdigit() and x < xmin + 14}
        rows = {}
        for y, x, t in items:
            rows.setdefault(y, []).append((x, t))
        for n, y in marks.items():
            band = [(x, t) for yy, xs in rows.items() if abs(yy - y) < 3.0 for x, t in xs]
            txt = "".join(t for x, t in sorted(band) if not t.strip().isdigit())
            out[n] = (pi, re.sub(r"\s+", " ", txt).strip())
    return out


def float_pages(pdf):
    """{'Table 4': page, 'Figure 2': page} from the typeset caption, not from the source order."""
    out = {}
    for pi, page in enumerate(PdfReader(pdf).pages, 1):
        t = re.sub(r"\s+", " ", page.extract_text() or "")
        for m in re.finditer(r"\b(Table|Figure)\s+(\d+)\.", t):
            out.setdefault(f"{m.group(1)} {m.group(2)}", pi)
    return out


def main():
    if not PDF.exists():
        sys.exit(f"missing {PDF}")
    L = line_map(PDF)
    if len(L) < 100:
        sys.exit(f"line-number extraction failed: only {len(L)} margin numbers found")
    page_of = {n: p for n, (p, _) in L.items()}
    floats = float_pages(PDF)

    heads = []
    for n in sorted(L):
        m = re.match(r"^(\d(?:\.\d)?)\s+([A-Z][A-Za-z].{3,70})$", L[n][1].strip())
        if m:
            heads.append((n, m.group(1)))
    if not heads:
        sys.exit("no numbered section headings recovered from the PDF")
    span = {num: (n, (heads[i + 1][0] - 1 if i + 1 < len(heads) else max(L)))
            for i, (n, num) in enumerate(heads)}

    def pagestr(a, b):
        ps = sorted({page_of[i] for i in range(a, b + 1) if i in page_of})
        return (f"p. {ps[0]}" if len(ps) == 1 else f"pp. {ps[0]}-{ps[-1]}") if ps else "?"

    checks = bad = 0
    for letter in LETTERS:
        flat = re.sub(r"\s+", " ", letter.read_text(encoding="utf-8"))
        print(f"-- {letter.name}")

        for m in re.finditer(r"Section\s+(\d(?:\.\d)?),\s*(pp?\.\s*[\d-]+),\s*lines\s+(\d+)-(\d+)", flat):
            sec, claimed, a, b = m.group(1), re.sub(r"\s+", " ", m.group(2)), int(m.group(3)), int(m.group(4))
            checks += 1
            if sec not in span:
                bad += 1; print(f"   FAIL §{sec}: no such section in the PDF"); continue
            s0, s1 = span[sec]
            actual = pagestr(a, b)
            problems = []
            if not (s0 <= a and b <= s1):
                problems.append(f"lines {a}-{b} outside §{sec} (spans {s0}-{s1})")
            if claimed != actual:
                problems.append(f"page claim '{claimed}' but lines fall on '{actual}'")
            if problems:
                bad += 1; print(f"   FAIL §{sec} lines {a}-{b}: " + "; ".join(problems))
            else:
                print(f"   ok   §{sec:<4} {claimed:<9} lines {a}-{b}")

        # bare line ranges tied to a named part rather than a numbered section
        for m in re.finditer(r"(abstract|contributions paragraph),\s*(pp?\.\s*[\d-]+),\s*lines\s+(\d+)-(\d+)", flat, re.I):
            what, claimed, a, b = m.group(1), re.sub(r"\s+", " ", m.group(2)), int(m.group(3)), int(m.group(4))
            checks += 1
            actual = pagestr(a, b)
            if claimed != actual:
                bad += 1; print(f"   FAIL {what} lines {a}-{b}: page claim '{claimed}' but '{actual}'")
            else:
                print(f"   ok   {what:<24} {claimed:<9} lines {a}-{b}")

        for m in re.finditer(r"\b(Table|Figure)\s+(\d+)(?:,\s*Panel\s+[A-C])?,\s*p\.\s*(\d+)", flat):
            key, claimed = f"{m.group(1)} {m.group(2)}", int(m.group(3))
            checks += 1
            if key not in floats:
                bad += 1; print(f"   FAIL {key}: not found in the typeset PDF")
            elif floats[key] != claimed:
                bad += 1; print(f"   FAIL {key}: cited p. {claimed}, typeset on p. {floats[key]}")
            else:
                print(f"   ok   {key:<24} p. {claimed}")

    print(f"\n{checks} references checked, {bad} wrong")
    if checks == 0:
        sys.exit("VACUOUS: no references were parsed, refusing to report a pass")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
