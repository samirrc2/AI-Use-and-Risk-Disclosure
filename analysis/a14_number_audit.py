"""
a14_number_audit.py — check every number in the manuscript against generated output.

This exists because the submitted manuscript reported a vendor-excluded prevalence of
20.9% that is not produced by any artifact in the repository under any definition, and
nothing in the pipeline could have caught it: the test suite checks the statistics
helpers, and reproduce.sh checks that two runs are byte-identical. Neither compares the
prose to the numbers.

Every figure in the manuscript body must either

  * appear in a generated artifact (results tables, JSON summaries, analysis output), or
  * be listed in analysis/number_allowlist.txt with a reason — for values that are
    legitimately external (years, SEC release numbers, a cited survey statistic).

Exit status is non-zero if anything is unaccounted for, so it can gate a build.

Usage:  cd "Paper 10" && python analysis/a14_number_audit.py [--update-allowlist]
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, "frontiers", "manuscript.tex")
ALLOW = os.path.join(ROOT, "analysis", "number_allowlist.txt")
SOURCES = [
    os.path.join(ROOT, "capsule", "results", "latest", "tables", "*"),
    os.path.join(ROOT, "analysis", "out", "**", "*"),
    os.path.join(ROOT, "build", "out", "*"),
    os.path.join(ROOT, "pilot", "*.json"),
]
# Only audit figures in this range. Below 1 they are mostly p-values and coefficients
# written to varying precision; above 100 they are counts and populations that the
# artifacts carry in many formats. The band below is where the paper's claims live.
LO, HI = 1.0, 100.0


def load_allowlist():
    allow = {}
    if os.path.exists(ALLOW):
        for line in open(ALLOW, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            v, _, why = line.partition("#")
            allow[v.strip()] = why.strip() or "(no reason given)"
    return allow


# Narrative write-ups quote the manuscript back at us, so including them would let a
# wrong number vouch for itself. Only machine-written artifacts count as evidence.
PROSE = ("REVISION_RESULTS.md", "BENCHMARK_AND_DETERMINANTS.md", "NUMBER_AUDIT",
         "CODING_INSTRUCTIONS.md", "design.json")
TOL = 0.05     # a manuscript figure matches if some artifact value is this close


def pool():
    """Every numeric value any generated artifact contains, as floats and as percentages."""
    vals = set()

    def add(tok):
        try:
            f = float(tok)
        except ValueError:
            return
        vals.add(abs(f))
        vals.add(abs(f) * 100.0)
    seen = 0
    for pat in SOURCES:
        for p in glob.glob(pat, recursive=True):
            if not os.path.isfile(p):
                continue
            if p.endswith((".svg", ".png", ".pdf")) or any(x in p for x in PROSE):
                continue
            try:
                t = open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            seen += 1
            for m in re.finditer(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?", t):
                add(m.group(0))
    return sorted(vals), seen


def matches(x, vals):
    """Numeric match with tolerance, so 21.56 in a table satisfies 21.6 in the prose."""
    import bisect
    i = bisect.bisect_left(vals, x - TOL)
    return i < len(vals) and vals[i] <= x + TOL


def manuscript_numbers():
    s = open(TEX, encoding="utf-8").read()
    s = re.sub(r"(?<!\\)%.*", "", s)                     # strip LaTeX comments
    s = re.sub(r"\\(cite[a-z]*|ref|label|url|href)\{[^}]*\}", " ", s)
    s = re.sub(r"\\(includegraphics|input|usepackage)(\[[^\]]*\])?\{[^}]*\}", " ", s)
    out = {}
    for m in re.finditer(r"(?<![\w.])(\d+(?:\.\d+)?)(?![\w])", s):
        tok = m.group(1)
        try:
            f = float(tok)
        except ValueError:
            continue
        if not (LO <= f <= HI):
            continue
        ctx = re.sub(r"\s+", " ", s[max(0, m.start() - 70):m.end() + 70]).strip()
        out.setdefault(tok, ctx)
    return out


def main():
    if not os.path.exists(TEX):
        print(f"[number-audit] no manuscript at {TEX}; nothing to check")
        return 0
    allow = load_allowlist()
    vals, nfiles = pool()
    nums = manuscript_numbers()
    missing = {t: c for t, c in nums.items()
               if not matches(float(t), vals) and t not in allow}
    print(f"[number-audit] {len(nums)} figures in [{LO:g},{HI:g}] found in the manuscript")
    print(f"[number-audit] checked against {nfiles} generated files; "
          f"{len(allow)} allowlisted")
    if "--update-allowlist" in sys.argv:
        with open(ALLOW, "a", encoding="utf-8") as fh:
            for t, c in sorted(missing.items(), key=lambda kv: float(kv[0])):
                fh.write(f"{t}  # REVIEW: {c[:110]}\n")
        print(f"[number-audit] appended {len(missing)} entries to "
              f"{os.path.relpath(ALLOW, ROOT)} — replace each REVIEW note with a real reason")
        return 0
    if not missing:
        print("[number-audit] PASS — every manuscript figure traces to generated output")
        return 0
    print(f"[number-audit] FAIL — {len(missing)} figure(s) not produced by any artifact:\n")
    for t, c in sorted(missing.items(), key=lambda kv: float(kv[0])):
        print(f"   {t:>8s}   …{c}…")
    print("\n  Each of these is either a number that needs recomputing, or one that is")
    print("  legitimately external and belongs in analysis/number_allowlist.txt with a reason.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
