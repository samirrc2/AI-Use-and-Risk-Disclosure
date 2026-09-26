"""
a17_verify_manuscript.py — everything that can be checked about the manuscript without
running the analysis: citations, cross-references, float ordering, abbreviations, the
statistics recomputed from first principles, arithmetic identities, and encoding.

This exists because the same audit kept being done by hand. a14 checks that every number
traces to a generated artifact; this checks that the paper is internally coherent and that
the published statistics are actually correct, not merely present in some file. The two are
complementary: a14 catches a number nothing generated, a17 catches a number generated
correctly and then mis-transcribed, and a cross-reference that drifted after a section moved.

Exit status is non-zero if any check fails, so it can sit in reproduce.sh.

Usage:  cd "Paper 10" && python analysis/a17_verify_manuscript.py
"""
import os
import re
import sys
from math import sqrt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, "frontiers", "manuscript.tex")
BIB = os.path.join(ROOT, "frontiers", "references.bib")
Z = 1.959963984540054          # two-sided 95% normal quantile
FAIL = []
SKIP = []
PASSED = []


def head(t):
    print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def ok(cond, msg):
    print(f"  {'OK ' if cond else 'FAIL'}  {msg}")
    (PASSED if cond else FAIL).append(msg)


def skip(why):
    """A skipped block is not a pass.

    Section 9 spent several verification passes printing "skipped: pypdf not installed" and
    letting the run finish on a clean PASS line, so four float-placement assertions were
    reported as verified while never executing. A skip now reaches the verdict and changes
    the exit status.
    """
    print(f"  SKIPPED: {why}")
    SKIP.append(why)


def wilson(k, n, z=Z):
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return 100 * (c - h) / d, 100 * (c + h) / d


def sections(s):
    """Map printed section number -> title, the way LaTeX will number them."""
    num = {}
    sec = sub = 0
    for m in re.finditer(r"\\(sub)?section\*?\{([^}]*)\}", s):
        t = m.group(2)
        if t in ("", "Keywords:", "Word count:"):
            continue
        if m.group(1):
            sub += 1
            num[f"{sec}.{sub}"] = t
        else:
            sec += 1
            sub = 0
            num[str(sec)] = t
    return num


def check_citations(s, bib):
    head("1. CITATIONS")
    defined = re.findall(r"@\w+\s*\{\s*([^,\s]+)", bib)
    used = set()
    for m in re.finditer(r"\\cite[a-zA-Z]*\s*(?:\[[^\]]*\])*\s*\{([^}]*)\}", s):
        used |= {k.strip() for k in m.group(1).split(",") if k.strip()}
    D = set(defined)
    print(f"  {len(D)} bib entries, {len(used)} keys cited")
    ok(not used - D, f"no undefined keys (offenders: {sorted(used - D)})")
    ok(not D - used, f"no uncited entries (offenders: {sorted(D - used)})")
    ok(len(defined) == len(D), "no duplicate bib keys")
    miss = []
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+),(.*?)\n\}", bib, re.S):
        typ, key, body = m.group(1).lower(), m.group(2), m.group(3)
        for f in ["author", "title", "year"] + (["journal"] if typ == "article" else []):
            if not re.search(r"\b%s\s*=" % f, body, re.I):
                miss.append(f"{key}:{f}")
    ok(not miss, f"no missing required bib fields (offenders: {miss})")
    yrs = [int(y) for y in re.findall(r"year\s*=\s*[{\"]?(\d{4})", bib)]
    ok(not [y for y in yrs if y > 2026], "no impossible publication years")
    bad = []
    ent = {}
    for m in re.finditer(r"@\w+\s*\{\s*([^,\s]+),(.*?)\n\}", bib, re.S):
        y = re.search(r"year\s*=\s*[{\"]?(\d{4})", m.group(2))
        ent[m.group(1)] = y.group(1) if y else "?"
    for m in re.finditer(r"\\citet\{([^}]*)\}\s*\((\d{4})\)", s):
        if ent.get(m.group(1).split(",")[0]) != m.group(2):
            bad.append(m.group(1))
    ok(not bad, f"hand-written years match the bib (offenders: {bad})")


def check_refs(s):
    head("2. TABLE / FIGURE / SECTION REFERENCES AND ORDERING")
    labels = set(re.findall(r"\\label\{([^}]*)\}", s))
    refs = [(m.group(1), m.start()) for m in re.finditer(r"\\ref\{([^}]*)\}", s)]
    ok(not [k for k, _ in refs if k not in labels],
       f"no dangling \\ref (offenders: {[k for k, _ in refs if k not in labels]})")
    unref = [k for k in labels if not any(k == r for r, _ in refs) and not k.startswith("eq:")]
    ok(not unref, f"every table/figure label is referenced (offenders: {unref})")
    ok(not re.findall(r"(?:Table|Figure)~?\s*\d+", s), "no hard-coded 'Table N' / 'Figure N'")
    for kind, pat in (("table", r"\\begin\{table\*?\}"), ("figure", r"\\begin\{figure\*?\}")):
        env = []
        for m in re.finditer(pat, s):
            blk = s[m.start():s.find("\\end{%s" % kind, m.start())]
            L = re.search(r"\\label\{([^}]*)\}", blk)
            if L:
                env.append(L.group(1))
        first = {}
        for k, pos in refs:
            if k in env and k not in first:
                first[k] = pos
        order = sorted(env, key=lambda k: first.get(k, 10 ** 9))
        ok(env == order, f"{kind} numbering matches first-citation order ({len(env)} {kind}s)")
        ok(all(k in first for k in env), f"every {kind} is cited in the text")
    num = sections(s)
    bad = []
    for m in re.finditer(r"Sections?~([0-9]+(?:\.[0-9]+)?)(?:--([0-9]+(?:\.[0-9]+)?))?", s):
        for k in [x for x in m.groups() if x]:
            if k not in num:
                bad.append(k)
    ok(not bad, f"every hard-coded Section~N.M exists (offenders: {bad})")
    # Existing is not enough: when a section is inserted or merged, every number below it
    # shifts and still resolves to a real section, just the wrong one. So each reference is
    # pinned to a word its target's title must contain.
    EXPECT = {"3.4": "primary", "3.5": "validation", "3.8": "statistical",
              "3.9": "reproducibility", "4.3": "validation", "4.5": "marketing",
              "4.6": "robustness"}
    drift = []
    for m in re.finditer(r"Sections?~([0-9]+(?:\.[0-9]+)?)(?:--([0-9]+(?:\.[0-9]+)?))?", s):
        for k in [x for x in m.groups() if x]:
            want = EXPECT.get(k)
            if want is None:
                drift.append(f"{k} -> '{num.get(k)}' (not a registered reference target; "
                             f"if this reference is intentional, add it to EXPECT)")
            elif want not in num.get(k, "").lower():
                drift.append(f"{k} -> '{num.get(k)}' (expected a title containing '{want}')")
    ok(not drift, f"each reference points at the intended section (drift: {drift})")
    print("  hard-coded section references resolve to:")
    for m in re.finditer(r"Sections?~([0-9]+(?:\.[0-9]+)?)(?:--([0-9]+(?:\.[0-9]+)?))?", s):
        ln = s[:m.start()].count("\n") + 1
        for k in [x for x in m.groups() if x]:
            print(f"    line {ln:4d}  {k:5s} -> {num.get(k, 'MISSING')}")


def check_stats(s):
    head("3. PUBLISHED STATISTICS RECOMPUTED FROM FIRST PRINCIPLES")
    rows = re.findall(r"([\d,]+)\s*/\s*([\d,]+)\s*&\s*([\d.]+)\\%\s*\(([\d.]+)--([\d.]+)\)", s)
    bad = 0
    for k, n, pp, lo, hi in rows:
        k, n = int(k.replace(",", "")), int(n.replace(",", ""))
        l, h = wilson(k, n)
        if not (abs(100 * k / n - float(pp)) < .051 and abs(l - float(lo)) < .051
                and abs(h - float(hi)) < .051):
            bad += 1
            print(f"    MISMATCH {k}/{n}: paper {pp}% ({lo}-{hi}), computed "
                  f"{100*k/n:.2f}% ({l:.2f}-{h:.2f})")
    ok(bad == 0, f"{len(rows)} 'k/n & pct (CI)' rows reproduce exactly")
    rows = re.findall(r"&\s*([\d.]+)\\%\s*\((\d+)--(\d+)\)\s*\[(\d+)/(\d+)\]", s)
    bad = 0
    for pp, lo, hi, k, n in rows:
        k, n = int(k), int(n)
        l, h = wilson(k, n)
        if not (abs(100 * k / n - float(pp)) < .06 and round(l) == int(lo)
                and round(h) == int(hi)):
            bad += 1
            print(f"    MISMATCH {k}/{n}: paper {pp}% ({lo}-{hi}), computed "
                  f"{100*k/n:.2f}% ({l:.1f}-{h:.1f})")
    ok(bad == 0, f"{len(rows)} 'pct (CI) [k/n]' gradient rows reproduce exactly")

    head("4. ARITHMETIC IDENTITIES BEHIND THE DESIGN")
    for d, c in [("8 strata x 50 = 400 sampled", 8 * 50 == 400),
                 ("private-fund 4x50 + wealth/retail 46+48+48+46 = 388", 200 + 188 == 388),
                 ("283 usable + 105 unusable websites = 388", 283 + 105 == 388),
                 ("140 + 143 matched website firms = 283", 140 + 143 == 283),
                 ("73 + 65 + 71 + 74 by quartile = 283", 73 + 65 + 71 + 74 == 283),
                 ("123 any-mention positive + 265 negative = 388", 123 + 265 == 388),
                 ("123 censused + 57 sampled = 180 verification", 123 + 57 == 180),
                 ("60 disagreement + 60 agreement + 38 website = 158 frame", 60 + 60 + 38 == 158),
                 ("158 frame = 79 + 79 per coder", 79 + 79 == 158),
                 ("phase-1 negative weight 265/57 = 4.649", abs(265 / 57 - 4.6491) < 1e-3),
                 ("phase-2 agreement weight 120/60 = 2.0", 120 / 60 == 2.0),
                 ("website negative weight 265/20 = 13.25", 265 / 20 == 13.25)]:
        ok(c, d)
    for v in ["400", "388", "283", "105", "123", "265", "180", "57", "60", "158", "15,606"]:
        ok(v.replace(",", "") in s.replace("{,}", ""), f"the count {v} appears in the paper")


def check_abbrev(s):
    head("5. ABBREVIATIONS DEFINED AT FIRST USE")
    i = s.index("\\section{Introduction}")
    pairs = [("SEC", "Securities and Exchange Commission"), ("AI", "artificial intelligence"),
             ("LLM", "large.language.model"), ("CI", "confidence interval"),
             ("AUM", "assets under management"), ("SE", "standard error"),
             ("CRD", "Central Registration Depository"),
             ("RIA", "registered investment adviser"),
             ("IAPD", "Investment Adviser Public Disclosure"), ("pp", "percentage point"),
             ("PABAK", "prevalence- and bias-adjusted")]
    # The abstract is read standalone, so it must define what it uses on its own.
    for zone, t in (("abstract", s[:i]), ("main text", s[i:])):
        for a, full in pairs:
            u = re.search(r"(?<![A-Za-z])%s(?![A-Za-z])" % re.escape(a), t)
            if not u:
                continue
            d = re.search(full, t, re.I)
            good = bool(d) and (d.start() <= u.start() + len(a) + 2
                                or abs(d.start() - u.start()) < 60)
            ok(good, f"{a} defined at first use in the {zone}")


def check_hygiene(s):
    head("6. SOURCE HYGIENE")
    ok(not [c for c in s if ord(c) < 32 and c not in "\n\t"], "no control characters")
    ok("\r" not in s, "no CRLF line endings")
    # Reported, not asserted: placeholders are expected while human coding is outstanding and
    # expected to be gone afterwards, so neither state is a failure on its own. The
    # data-availability check below is what turns their absence into an obligation.
    print(f"  INFO  {s.count('PLACEHOLDER')} placeholder(s) open")
    # Table 4's human column said "pending" in eight cells for a whole revision cycle, because
    # a stub does not have to contain the word PLACEHOLDER to be a stub. Any of these inside a
    # table or figure environment is one.
    stubs = []
    for m in re.finditer(r"\\begin\{(table|figure)\*?\}(.*?)\\end\{\1\*?\}", s, re.S):
        for w in ("pending", "TBD", "tbd", "XX", "forthcoming", "to be added"):
            if re.search(r"&\s*%s\s*(&|\\\\)" % w, m.group(2)) or f"& {w} &" in m.group(2):
                stubs.append(f"{w} in a {m.group(1)}")
    ok(not stubs, f"no stub cells left in tables or figures (found: {sorted(set(stubs))})")
    for w in ("TODO", "FIXME", "XXX", "???"):
        ok(w not in s, f"no {w} markers")
    t = s[s.index("\\section{Introduction}"):s.index("\\section*{Conflict of Interest")]
    t = re.sub(r"\\begin\{(table|figure)\*?\}.*?\\end\{\1\*?\}", "", t, flags=re.S)
    t = re.sub(r"\\begin\{(equation|align|displaymath)\*?\}.*?\\end\{\1\*?\}", "", t, flags=re.S)
    t = re.sub(r"\\cite[a-zA-Z]*\s*(\[[^\]]*\])*\{[^}]*\}", "X", t)
    t = re.sub(r"\\[a-zA-Z]+\*?", "", t)
    w = len(re.sub(r"[{}$~\\&%]", " ", t).split())
    dec = re.search(r"\$\\approx\$([\d{},]+) \(main text", s)
    d = int(dec.group(1).replace("{,}", "").replace(",", "")) if dec else 0
    ok(abs(w - d) <= 50, f"declared word count {d:,} matches the measured {w:,}")
    a = s[s.index("\\begin{abstract}"):s.index("\\tiny")]
    a = re.sub(r"\\cite[a-zA-Z]*\s*(\[[^\]]*\])*\{[^}]*\}", "X", a)
    a = re.sub(r"\[PLACEHOLDER[^\]]*\]", "", a)
    a = re.sub(r"\\[a-zA-Z]+\*?", "", a)
    aw = len(re.sub(r"[{}$~\\&%]", " ", a).split())
    ok(aw <= 350, f"abstract {aw} words, within the 350-word limit")
    # The header advertises counts to the editor, so they must match what is actually there.
    nt = s.count("\\begin{table}") + s.count("\\begin{table*}")
    nf = s.count("\\begin{figure}") + s.count("\\begin{figure*}")
    m = re.search(r"Figures:\s*(\d+);\s*Tables:\s*(\d+)", s)
    ok(bool(m) and int(m.group(1)) == nf, f"header declares {m.group(1) if m else '?'} figures, "
                                          f"the paper has {nf}")
    ok(bool(m) and int(m.group(2)) == nt, f"header declares {m.group(2) if m else '?'} tables, "
                                         f"the paper has {nt}")


def check_tables_against_artifacts(s):
    """Tables 3 and 5 cell-by-cell against the files that produced them.

    a14 only proves a value exists in some artifact; it cannot tell whether the right value
    landed in the right cell. These two tables carry the most cells and the most opportunity
    for a transcription slip, so they are matched position by position.
    """
    import csv
    head("7. TABLES MATCHED CELL-BY-CELL TO THEIR ARTIFACTS")
    vp = os.path.join(ROOT, "capsule", "results", "latest", "tables", "table4_validation.csv")
    if not os.path.exists(vp):
        skip("section 7: capsule results absent, run the capsule first")
        return
    art = list(csv.DictReader(open(vp)))
    blk = s[s.index("\\label{tab:validation}"):]
    blk = blk[:blk.index("\\end{table}")]
    rows = re.findall(r"^(\(.\)[^&]*|Any use[^&]*)&\s*([\d.]+)\s*&\s*([\d.]+)\s*&"
                      r"\s*([\d.]+)\s*&\s*([\d.]+)\\%\s*&\s*([\d.]+)\s*&\s*([\d.]+)",
                      blk, re.M)
    ok(len(rows) == len(art), f"validation table has {len(art)} rows in the paper and artifact")
    bad = 0
    for i, (lab, pr, rc, f1, ag, kp, pb) in enumerate(rows):
        a = art[i]
        for got, want, nm in [(pr, a["precision"], "precision"), (rc, a["recall"], "recall"),
                              (f1, a["f1"], "f1"),
                              (str(float(ag) / 100), a["pct_agree"], "pct_agree"),
                              (kp, a["kappa"], "kappa"), (pb, a["pabak"], "pabak")]:
            if abs(float(got) - float(want)) > 6e-4:
                bad += 1
                print(f"    MISMATCH row {i+1} {nm}: paper {got}, artifact {want}")
    ok(bad == 0, f"all {len(rows) * 6} validation cells match the artifact")
    # The paper asserts precision is invariant to the verification weighting, because every
    # model-positive was censused into phase two. That is checkable: the weighted precision
    # it publishes must equal the unweighted tp/(tp+fp) from the raw cell counts.
    bad = 0
    for a in art:
        tp, fp = int(a["tp"]), int(a["fp"])
        if abs(tp / (tp + fp) - float(a["precision"])) > 6e-4:
            bad += 1
    ok(bad == 0, "the paper's precision-invariance claim holds for every label")

    vp = os.path.join(ROOT, "analysis", "out", "revision", "r1_2_vendor_panel.csv")
    if not os.path.exists(vp):
        return
    art = {r["result"]: r for r in csv.DictReader(open(vp))}
    blk = s[s.index("\\label{tab:vendorpanel}"):]
    blk = blk[:blk.index("\\end{table}")]
    checked = bad = 0
    for label, row in art.items():
        for col in ("incl_vendor", "excl_vendor"):
            v = row[col].replace("%", "").split(" ")[0]
            try:
                float(v)
            except ValueError:
                continue
            checked += 1
            if v not in blk.replace("\\%", "").replace("$+$", "+").replace("$", ""):
                bad += 1
                print(f"    MISSING from Table 5: {label} / {col} = {row[col]}")
    ok(bad == 0, f"all {checked} vendor-panel values appear in Table 5")


def check_data_availability(s):
    """Every data path the Data Availability Statement names must exist in the capsule.

    The statement claims the capsule regenerates every reported number. Naming a file that
    is not there makes that claim stronger than the contents support, which is a referee's
    easy hit. While human coding is outstanding the three verification files cannot exist
    yet, so they are reported as pending; once the placeholders are gone they must be real.
    """
    head("8. DATA AVAILABILITY PROMISES vs CAPSULE CONTENTS")
    i = s.index("\\section*{Data Availability Statement}")
    das = s[i:]
    paths = sorted(set(re.findall(r"\\texttt\{(data/[^}]*)\}", das)))
    paths = [q.replace("\\_", "_") for q in paths]
    cap = os.path.join(ROOT, "capsule")
    missing = [q for q in paths
               if not (os.path.exists(os.path.join(cap, q))
                       or os.path.exists(os.path.join(cap, q.rstrip("/"))))]
    print(f"  {len(paths)} data paths named in the statement")
    for q in paths:
        there = q not in missing
        print(f"    {'present' if there else 'MISSING':8s}  {q}")
    outstanding = "PLACEHOLDER" in s
    if missing and outstanding:
        print(f"\n  {len(missing)} path(s) not yet in the capsule. Human coding is still")
        print("  outstanding, so this is expected: a12 score writes them when coding is done.")
        print("  This check becomes a hard failure once the placeholders are filled.")
        ok(True, f"{len(missing)} promised path(s) pending human coding (not yet a failure)")
    else:
        ok(not missing, f"every promised data path exists in the capsule (missing: {missing})")


def check_gradient_weights(s):
    """Table 2's Filing pop. and Weight columns, which no other check covered.

    These two columns are derived in the manuscript rather than emitted by the capsule, so
    a14 (which matches printed figures to generated artifacts) could not see them and a17
    did not look. The Wealth/retail Q4 weight printed 0.090, which is only reachable by
    rounding N_h.c_h/n_h to an integer before dividing; from the exact value it is 0.08949,
    i.e. 0.089. The tell was the column summing to 1.001 against a printed total of 1.000.
    """
    import csv
    head("10. TABLE 2 FILING POPULATION AND STRATUM WEIGHTS")
    src = os.path.join(ROOT, "capsule", "results", "latest", "tables", "table3_weighting.csv")
    if not os.path.exists(src):
        skip("section 10: capsule table3_weighting.csv absent, stratum weights unverified")
        return
    cap = list(csv.DictReader(open(src)))
    blk = s[s.index("\\label{tab:gradient}"):]
    blk = blk[:blk.index("\\end{table}")]
    rows, total_n, total_w = [], None, None
    for line in blk.split("\\\\"):
        # \midrule and friends sit glued to the start of the row that follows them, which
        # silently dropped the first stratum from this parse.
        line = re.sub(r"\\(?:top|mid|bottom)rule", " ", line)
        c = [x.strip() for x in line.split("&")]
        if len(c) != 5:
            continue
        if c[0].startswith("Total"):
            total_n = int(c[1].replace("{,}", "").replace(",", ""))
            total_w = float(c[4])
            continue
        if not re.match(r"(Private fund|Wealth/retail)", c[0]):
            continue
        rows.append((c[0], int(c[1].replace("{,}", "").replace(",", "")), int(c[2]),
                     c[3], float(c[4])))
    ok(len(rows) == len(cap), f"Table 2 prints all {len(cap)} sampling strata ({len(rows)} found)")
    if len(rows) != len(cap):
        return
    # N_h * c_h / n_h, with n_h = 50 advisers drawn per stratum by design
    unrounded = [float(r["N_all"]) * float(r["n_classified"]) / 50 for r in cap]
    grand = sum(unrounded)
    ok(total_n == round(grand),
       f"Table 2 total filing population {total_n:,} equals the exact sum {grand:.2f}")
    for i, (name, N, n, kn, w) in enumerate(rows):
        ok(N == round(unrounded[i]),
           f"{name}: filing population {N:,} matches capsule {unrounded[i]:.2f}")
        ok(int(cap[i]["n_classified"]) == n,
           f"{name}: classified n {n} matches capsule")
        exact = unrounded[i] / grand
        ok(round(exact, 3) == w,
           f"{name}: weight {w:.3f} equals the exact {exact:.5f} rounded, not a pre-rounded N")
    ok(abs(sum(r[4] for r in rows) - total_w) < 5e-4,
       f"printed weights sum to the printed total {total_w:.3f} "
       f"(got {sum(r[4] for r in rows):.3f})")
    est = sum(rows[i][4] * float(cap[i]["any_use"]) for i in range(len(rows)))
    ok(abs(est - 0.227) < 5e-4,
       f"printed weights reproduce the 22.7% survey-weighted estimate (got {100*est:.2f}%)")


def check_case_table_labels(s):
    """Table 4's Prim./Indep./Hum. cells, matched to the frozen labels via the source brochure.

    These are label codes, not numbers, so a14 never saw them and four verification passes
    reported Table 4 as checked while only its numeric cells were in scope. Two rows were
    wrong: the named-vendor row printed "ce / --" where both model families had assigned bce,
    and the hard-negative row printed "-- / -- / n/a" for a passage that exists in only two
    brochures, both of which carry model labels and sit inside the human frame.

    Each passage is located in the identified corpus, which is deliberately absent from the
    public capsule, so this runs locally only and skips loudly elsewhere. Two details matter:
    the source PDFs carry ffi/fi/fl ligatures, so comparison is on NFKD-normalised
    alphanumerics only, and a redaction such as [firm] breaks the run of source text, so only
    the passage up to the first redaction is used as the probe.
    """
    import csv, glob, unicodedata
    head("11. TABLE 4 LABEL CODES AGAINST THE FROZEN LABELS")
    broch = os.path.join(ROOT, "data", "brochure_text")
    smp_p = os.path.join(ROOT, "capsule", "data", "sample.csv")
    real_p = os.path.join(ROOT, "data", "pilot_sample_400.csv")
    if not (os.path.isdir(broch) and os.path.exists(real_p)):
        skip("section 11: identified brochure corpus absent, Table 4 label codes unverified")
        return

    def norm(x):
        return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", str(x)).lower())

    def rd(path):
        return list(csv.DictReader(open(path, encoding="utf-8", errors="replace")))

    def lab(r):
        return "".join(k for k in "abcde" if r and str(r.get(k, "0")).strip() == "1") or "--"

    smp = rd(smp_p)
    real = sorted(rd(real_p), key=lambda r: int(r["crd"]))
    ok(len(smp) == len(real), f"sample and identified frame agree in size ({len(smp)}/{len(real)})")
    if len(smp) != len(real):
        return
    # fids were assigned in CRD-sorted order; the join keys confirm the alignment
    aligned = all(smp[i]["type"] == real[i]["type"] for i in range(len(smp)))
    ok(aligned, "fid -> CRD crosswalk verified on the adviser-type join key")
    if not aligned:
        return
    xw = {int(real[i]["crd"]): smp[i]["fid"] for i in range(len(smp))}

    cap = os.path.join(ROOT, "capsule", "data")
    prim = {r["fid"]: r for r in rd(os.path.join(cap, "labels_primary.csv"))}
    ind = {r["fid"]: r for r in rd(os.path.join(cap, "labels_independent.csv"))}
    hv = os.path.join(cap, "human_verification")
    hum = {r["row_id"]: r for r in rd(os.path.join(hv, "brochures.csv"))}
    fid2row = {r["fid"]: r["row_id"] for r in rd(os.path.join(hv, "frame.csv"))}
    corpus = {}
    for f in glob.glob(os.path.join(broch, "**", "*.txt"), recursive=True):
        corpus[os.path.basename(f)[:-4]] = norm(open(f, encoding="utf-8", errors="replace").read())
    ok(len(corpus) > 300, f"brochure corpus loaded ({len(corpus)} documents)")

    blk = s[s.index("\\label{tab:cases}"):]
    blk = blk[:blk.index("\\end{table}")]
    rows = []
    for line in blk.split("\\\\"):
        line = re.sub(r"\\(?:top|mid|bottom)rule", " ", line)
        c = [x.strip() for x in line.split("&")]
        if len(c) == 6 and c[0] and "tabular" not in c[0] and not c[0].startswith("Case"):
            rows.append(c)
    ok(len(rows) == 8, f"Table 4 parses to 8 case rows ({len(rows)} found)")
    for c in rows:
        name, passage, P, I, H = c[0], c[1], c[2], c[3], c[4]
        seg = re.split(r"\[[A-Za-z]+\]", passage)[0]
        frag = norm(re.sub(r"\\ldots|``|''|\\%", "", seg))
        hits = [crd for crd, txt in corpus.items() if frag and frag in txt]
        triples = set()
        for crd in hits:
            fid = xw.get(int(crd))
            row = fid2row.get(fid)
            triples.add((lab(prim.get(fid)),
                         lab(ind.get(fid)) if fid in ind else "--",
                         lab(hum.get(row)) if row in hum else "n/a"))
        ok(len(hits) > 0, f"{name}: passage located in the corpus")
        ok((P, I, H) in triples,
           f"{name}: printed {P}/{I}/{H} is what the frozen labels say"
           + ("" if (P, I, H) in triples else f" (data: {sorted(triples)})"))


def check_case_table_against_capsule(s):
    """Table 4 as printed, against the capsule artifact that regenerates it.

    Section 11 proves the labels by locating each passage in the identified corpus, which is
    withheld from the public capsule. This check needs only capsule outputs, so the printed
    table stays verifiable wherever the capsule runs.
    """
    import csv
    head("13. TABLE 4 AGAINST THE CAPSULE ARTIFACT")
    art = os.path.join(ROOT, "capsule", "results", "latest", "tables", "table4_cases.csv")
    if not os.path.exists(art):
        skip("section 13: capsule table4_cases.csv absent, run the capsule first")
        return
    with open(art, newline="", encoding="utf-8") as fh:
        cap = sorted(csv.DictReader(fh), key=lambda r: int(r["order"]))
    blk = s[s.index("\\label{tab:cases}"):]
    blk = blk[:blk.index("\\end{table}")]
    rows = []
    for line in blk.split("\\\\"):
        line = re.sub(r"\\(?:top|mid|bottom)rule", " ", line)
        c = [x.strip() for x in line.split("&")]
        if len(c) == 6 and c[0] and "tabular" not in c[0] and not c[0].startswith("Case"):
            rows.append(c)
    ok(len(rows) == len(cap), f"printed rows match the artifact's row count ({len(rows)}/{len(cap)})")
    if len(rows) != len(cap):
        return
    norm = lambda x: re.sub(r"\s+", " ", x).strip()
    for printed, a in zip(rows, cap):
        ok(printed[0] == a["case"], f"row {a['order']}: case name '{printed[0]}' matches the artifact")
        ok((printed[2], printed[3], printed[4]) == (a["primary"], a["independent"], a["human"]),
           f"{a['case']}: printed {printed[2]}/{printed[3]}/{printed[4]} matches regenerated "
           f"{a['primary']}/{a['independent']}/{a['human']}")
        ok(norm(printed[1]) == norm(a["passage"]),
           f"{a['case']}: printed passage matches the capsule's case_examples entry")


def check_published_figures(_s):
    """The figures typeset in the article must be the capsule's own renderings.

    Until publication_figures.py existed, no committed code produced the published figures:
    the capsule drew the same data in a different style, so the two could drift silently and
    the Data Availability Statement's claim was not literally true.
    """
    import filecmp
    head("12. PUBLISHED FIGURES COME FROM THE CAPSULE")
    pub = os.path.join(ROOT, "capsule", "results", "latest", "figures", "publication")
    if not os.path.isdir(pub):
        skip("section 12: capsule publication figures absent, run the capsule first")
        return
    for src, dest, label in (("figure1.png", "fig2.png", "Figure 1"),
                             ("figure2.png", "fig4.png", "Figure 2")):
        a = os.path.join(pub, src)
        b = os.path.join(ROOT, "frontiers", "figures", dest)
        ok(os.path.exists(a) and os.path.exists(b) and filecmp.cmp(a, b, shallow=False),
           f"{label}: frontiers/figures/{dest} is byte-identical to the capsule's {src}")


def check_pdf_float_order(s):
    """Where the floats actually land, which source order does not determine.

    LaTeX keeps a separate deferred queue per float class, so one float with a different
    placement option reorders the output without changing the source. Table 4 carried [p]
    while every other float carried [h!]; that stalled the table queue and pushed Tables 4
    and 5 out behind both figures, with nothing wrong in the source for a source-order check
    to find.
    """
    head("9. FLOAT ORDER IN THE COMPILED PDF")
    pdf = os.path.join(ROOT, "frontiers", "manuscript.pdf")
    try:
        from pypdf import PdfReader
    except ImportError:
        skip("section 9: pypdf not installed, float placement in the PDF unverified")
        return
    if not os.path.exists(pdf):
        skip("section 9: manuscript.pdf not built, float placement unverified")
        return
    caps = {}
    for m in re.finditer(r"\\begin\{(table|figure)\}", s):
        blk = s[m.start():s.find("\\end{%s}" % m.group(1), m.start())]
        c = re.search(r"\\caption\{(.{0,60})", blk, re.S)
        if c:
            t = re.sub(r"\s+", " ", re.sub(r"\\[a-zA-Z]+\*?", "", c.group(1))).strip()
            caps.setdefault(m.group(1), []).append(t[:30])
    found = []
    pages = [re.sub(r"\s+", " ", pg.extract_text() or "") for pg in PdfReader(pdf).pages]
    for kind, titles in caps.items():
        label = kind.capitalize()
        for i, t in enumerate(titles, 1):
            for n, txt in enumerate(pages, 1):
                if re.search(re.escape(f"{label} {i}.") + r"\s+" + re.escape(t[:25]), txt):
                    found.append((n, txt.index(t[:25]), f"{label} {i}"))
                    break
    found.sort()
    seq = [f for _, _, f in found]
    for n, _, f in found:
        print(f"    page {n:2d}   {f}")
    for kind in ("Table", "Figure"):
        got = [x for x in seq if x.startswith(kind)]
        want = sorted(got, key=lambda x: int(x.split()[1]))
        ok(got == want, f"{kind.lower()}s appear in numerical order in the PDF ({len(got)} found)")
    ok(len(seq) == sum(len(v) for v in caps.values()),
       f"every float reached the PDF ({len(seq)} of {sum(len(v) for v in caps.values())})")
    # Per-class order is not enough. With floats grouped at the end, one class must finish
    # before the other starts; interleaving is what a stalled float queue produces, and it
    # leaves each class internally ordered so a per-class check sees nothing wrong.
    kinds = [x.split()[0] for x in seq]
    blocks = [k for i, k in enumerate(kinds) if i == 0 or k != kinds[i - 1]]
    ok(len(blocks) == len(set(blocks)),
       f"tables and figures are not interleaved in the PDF (block order: {' then '.join(blocks)})")


def main():
    s = open(TEX, encoding="utf-8").read()
    bib = open(BIB, encoding="utf-8").read()
    check_citations(s, bib)
    check_refs(s)
    check_stats(s)
    check_abbrev(s)
    check_hygiene(s)
    check_tables_against_artifacts(s)
    check_data_availability(s)
    check_pdf_float_order(s)
    check_gradient_weights(s)
    check_case_table_labels(s)
    check_published_figures(s)
    check_case_table_against_capsule(s)
    head("VERDICT")
    print(f"  {len(PASSED)} checks passed, {len(FAIL)} failed, {len(SKIP)} blocks skipped")
    if FAIL:
        print(f"  {len(FAIL)} CHECKS FAILED:")
        for f in FAIL:
            print(f"    - {f}")
        sys.exit(1)
    if SKIP:
        for w in SKIP:
            print(f"    - {w}")
        print("  INCOMPLETE — nothing failed, but the run did not check everything")
        sys.exit(2)
    if not PASSED:
        print("  VACUOUS — no assertions ran")
        sys.exit(3)
    print("  PASS — manuscript internally consistent and statistics reproduce")


if __name__ == "__main__":
    main()
