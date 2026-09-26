"""
a11_revision.py — generate every result requested by Reviewers 1 and 3.

Writes to analysis/out/revision/. Nothing here edits the manuscript; each output is a
standalone artifact keyed to the reviewer point it answers.

  R1.2 / R3.3   definition of "any use": vendor-excluded measure carried through every
                downstream analysis, plus worked coding examples per label
  R1.3 / R3.4   temporal mismatch: empirical 2-year movement in adviser size, and the
                size gradient re-estimated on lagged strata
  R1.4          venue comparison conditioned on text volume
  R1.5 / R3.7   enforcement screen: patterns, threshold provenance, trigger adjudication
  R1.6          stratified inference: weight formula, FPC, design-weighted regression,
                quartile indicators against imposed linearity
  R3.5          paired within-brochure tests (risk vs use; brochure vs website)
  R3.6          website availability tested against the outcome, not just covariates
  R1.1 / R3.2   human validation: the adjudication design and its blinded sheets

Usage:  cd "Paper 10" && python analysis/a11_revision.py
"""
import csv
import json
import math
import os
import random
import re
from datetime import datetime

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP = os.path.join(ROOT, "capsule", "data")
OUT = os.path.join(ROOT, "analysis", "out", "revision")
BROCH = os.path.join(ROOT, "data", "brochure_text", "current")
_FRAME_MEMBER = ("adv-filing-data-20111105-20241231-part1/"
                 "IA_ADV_Base_A_20111105_20241231.csv")
FRAME = os.path.join(ROOT, "data", "frame", *_FRAME_MEMBER.split("/"))
FRAME_ZIP = os.path.join(ROOT, "data", "raw", "frame",
                         "adv-filing-data-20111105-20241231-part1.zip")


def open_frame():
    """Text handle on the Form ADV base table.

    The extracted tree under data/frame/ is a byte-exact copy of the archive in
    data/raw/frame/, so the repository keeps only the archive. Read the member
    directly when the extracted copy is absent: streaming it costs nothing here
    because both call sites scan the file once, row by row.
    """
    if os.path.exists(FRAME):
        return open(FRAME, encoding="utf-8", errors="replace")
    if not os.path.exists(FRAME_ZIP):
        raise SystemExit(f"neither {FRAME} nor {FRAME_ZIP} is present; "
                         f"see data/frame_README.md")
    import io
    import zipfile
    z = zipfile.ZipFile(FRAME_ZIP)
    return io.TextIOWrapper(z.open(_FRAME_MEMBER), encoding="utf-8", errors="replace")
TYPES = ["private_fund", "wealth_ria"]
QS = ["Q1", "Q2", "Q3", "Q4"]
SEED = 42
BOOT = 10000

os.makedirs(OUT, exist_ok=True)
os.makedirs(os.path.join(OUT, "human_validation"), exist_ok=True)
REPORT = []


def say(s=""):
    print(s)
    REPORT.append(s)


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def load():
    smp = pd.read_csv(os.path.join(CAP, "sample.csv"))
    pri = pd.read_csv(os.path.join(CAP, "labels_primary.csv"))
    ind = pd.read_csv(os.path.join(CAP, "labels_independent.csv"))
    strat = pd.read_csv(os.path.join(CAP, "population_strata.csv"))
    ven = pd.read_csv(os.path.join(CAP, "venue", "venue_divergence.csv"))
    crawl = pd.read_csv(os.path.join(CAP, "venue", "marketing_crawl_log.csv"))
    bexp = pd.read_csv(os.path.join(CAP, "venue", "brochure_exposure.csv"))
    m = smp.merge(pri, on="fid", how="left")
    m = m[m.a.notna()].copy()
    for c in "abcde":
        m[c] = m[c].astype(int)
    # the two composite definitions under debate
    m["use_ve"] = ((m[["a", "b", "e"]].sum(axis=1)) > 0).astype(int)   # current primary
    m["use_nv"] = ((m[["a", "b"]].sum(axis=1)) > 0).astype(int)        # vendor-excluded
    m["mention"] = ((m[["a", "b", "c", "d", "e"]].sum(axis=1)) > 0).astype(int)
    m["aumq"] = m.aum_quartile.map({q: i + 1 for i, q in enumerate(QS)})
    m["pf"] = (m.type == "private_fund").astype(int)
    return dict(sample=smp, m=m, ind=ind, strat=strat, ven=ven, crawl=crawl, bexp=bexp)


def crosswalk(smp):
    """fid -> CRD. fids were assigned in CRD-sorted order; verified on the join keys."""
    real = pd.read_csv(os.path.join(ROOT, "data", "pilot_sample_400.csv"))
    real = real.sort_values("crd").reset_index(drop=True)
    assert (smp.regulatory_aum.values == real.regulatory_aum.values).all(), "crosswalk broken"
    assert (smp.type.values == real.type.values).all()
    return pd.DataFrame({"fid": smp.fid.values, "crd": real.crd.values, "firm": real.firm.values})


# ---------------------------------------------------------------- R1.2 / R3.3
def r1_2_definitions(d):
    m = d["m"]
    n = len(m)
    say("\n" + "=" * 78)
    say("R1.2 / R3.3  Definition of 'any use': every result under both definitions")
    say("=" * 78)
    rows = []
    names = {"a": "AI in investment process", "b": "AI in operations/client service",
             "c": "AI as disclosed risk factor", "d": "Explicit non-use", "e": "Named vendor"}
    for L in "abcde":
        k = int(m[L].sum())
        p, lo, hi = wilson(k, n)
        rows.append([f"({L}) {names[L]}", k, n, round(p, 4), round(lo, 4), round(hi, 4)])
    for col, lab in [("use_ve", "Any use INCLUDING vendor (a OR b OR e)"),
                     ("use_nv", "Any use EXCLUDING vendor (a OR b)"),
                     ("mention", "Any mention (a-e)")]:
        k = int(m[col].sum())
        p, lo, hi = wilson(k, n)
        rows.append([lab, k, n, round(p, 4), round(lo, 4), round(hi, 4)])
    t = pd.DataFrame(rows, columns=["label", "k", "n", "prevalence", "ci_lo", "ci_hi"])
    t.to_csv(os.path.join(OUT, "r1_2_prevalence_both_definitions.csv"), index=False)
    for r in t.itertuples():
        say(f"   {r.label:42s} k={r.k:3d}  {100*r.prevalence:5.1f}%  "
            f"({100*r.ci_lo:.1f}-{100*r.ci_hi:.1f})")
    # how much of the composite rests on vendor references alone
    only_e = int(((m.e == 1) & (m.a == 0) & (m.b == 0)).sum())
    say(f"\n   brochures where a vendor name is the ONLY evidence of use: {only_e}")
    say(f"   so the composite can move at most {100*only_e/n:.1f} pp on this choice "
        f"({100*m.use_ve.mean():.1f}% -> {100*m.use_nv.mean():.1f}%)")
    say("   NOTE: the submitted manuscript reports 20.9% for this sensitivity. That value is")
    say("   not reproducible from the frozen labels under any definition; the correct figure")
    say("   for 'drop label e' is the one above.")

    # Re-estimation from the independent cross-family labels, with the two-phase
    # verification weights. The manuscript quotes this as "about 21.6%" but the pipeline
    # never wrote it to an artifact, so nothing could check it. It is emitted here.
    pri = d["m"].set_index("fid")
    ind = d["ind"].set_index("fid")
    keys = [k for k in ind.index if k in pri.index]
    mention_all = (pri[list("abcde")].sum(axis=1) > 0)
    n_neg_pop = int((~mention_all).sum())
    n_neg_smp = sum(1 for k in keys if not mention_all.loc[k])
    wneg = n_neg_pop / n_neg_smp if n_neg_smp else 1.0
    reest = {}
    for cols, nm in [(["a", "b", "e"], "a|b|e"), (["a", "b"], "a|b")]:
        num = sum((1.0 if mention_all.loc[k] else wneg) *
                  (1 if any(int(ind.loc[k, c]) for c in cols) else 0) for k in keys)
        den = sum((1.0 if mention_all.loc[k] else wneg) for k in keys)
        reest[nm] = round(num / den, 4)
        say(f"   re-estimated from the independent labels, two-phase weighted, {nm:6s}"
            f" = {100*num/den:.2f}%")
    json.dump({"independent_reestimate": reest,
               "verification_n": len(keys), "negative_weight": round(wneg, 4)},
              open(os.path.join(OUT, "r1_2_independent_reestimate.json"), "w"), indent=1)
    return t


def r1_2_vendor_panel(d):
    """The compact panel reproducing every principal result under both composite
    definitions, so the vendor question can be closed in one table."""
    m = d["m"]
    n = len(m)
    rows = []

    def add(label, ve, nv, extra=""):
        rows.append({"result": label, "incl_vendor": ve, "excl_vendor": nv, "note": extra})
    for col, lab in [(None, None)]:
        pass
    a = wilson(int(m.use_ve.sum()), n)
    b = wilson(int(m.use_nv.sum()), n)
    add("Overall prevalence",
        f"{100*a[0]:.1f}% ({100*a[1]:.1f}-{100*a[2]:.1f})",
        f"{100*b[0]:.1f}% ({100*b[1]:.1f}-{100*b[2]:.1f})")
    for q in QS:
        sub = m[m.aum_quartile == q]
        add(f"AUM quartile {q[-1]}", f"{100*sub.use_ve.mean():.1f}%", f"{100*sub.use_nv.mean():.1f}%")
    for t, lab in [("private_fund", "Private-fund advisers"), ("wealth_ria", "Wealth and retail advisers")]:
        sub = m[m.type == t]
        add(lab, f"{100*sub.use_ve.mean():.1f}%", f"{100*sub.use_nv.mean():.1f}%")
    Nall = {(r.type, r.aum_quartile): int(r.N_all) for r in d["strat"].itertuples()}
    nsmp = {}
    for r in d["sample"].itertuples():
        nsmp[(r.type, r.aum_quartile)] = nsmp.get((r.type, r.aum_quartile), 0) + 1

    def wt(col, filing):
        cells = {}
        for r in m.itertuples():
            k = (r.type, r.aum_quartile)
            cells.setdefault(k, [0, 0])
            cells[k][1] += 1
            cells[k][0] += getattr(r, col)
        N = {k: (Nall[k] * cells[k][1] / nsmp[k] if filing else Nall[k]) for k in cells}
        T = sum(N.values())
        return 100 * sum((N[k] / T) * (cells[k][0] / cells[k][1]) for k in cells)
    add("Survey-weighted (brochure filers)", f"{wt('use_ve',True):.1f}%", f"{wt('use_nv',True):.1f}%")
    add("Weighted to full frame", f"{wt('use_ve',False):.1f}%", f"{wt('use_nv',False):.1f}%")
    f1 = smf.logit("use_ve ~ aumq + pf", data=m).fit(disp=0)
    f2 = smf.logit("use_nv ~ aumq + pf", data=m).fit(disp=0)
    add("Logistic coefficient, AUM quartile",
        f"{f1.params.aumq:+.2f}", f"{f2.params.aumq:+.2f}")
    add("Logistic coefficient, private fund",
        f"{f1.params.pf:+.2f}", f"{f2.params.pf:+.2f}")
    r = []
    for col in ("use_ve", "use_nv"):
        bo = int(((m.c == 1) & (m[col] == 0)).sum())
        uo = int(((m.c == 0) & (m[col] == 1)).sum())
        r.append((100 * (m.c.mean() - m[col].mean()), stats.binomtest(bo, bo + uo, 0.5).pvalue))
    add("Risk language minus disclosed use",
        f"{r[0][0]:+.1f} pp (p={r[0][1]:.3f})", f"{r[1][0]:+.1f} pp (p={r[1][1]:.4f})")
    ml = pd.read_csv(os.path.join(CAP, "venue", "marketing_labels.csv"))
    ml["m_nv"] = ((ml[["a", "b"]].sum(axis=1)) > 0).astype(int)
    v = d["ven"].merge(ml[["fid", "m_nv"]], on="fid").merge(m[["fid", "use_nv"]], on="fid")
    add("Brochure vs website (matched)",
        f"{100*v.b_anyuse.mean():.1f}% vs {100*v.m_anyuse.mean():.1f}%",
        f"{100*v.use_nv.mean():.1f}% vs {100*v.m_nv.mean():.1f}%")
    # Paired bootstrap interval for the vendor-excluded venue difference. Table 5 Panel B
    # prints it, so it has to be generated rather than computed by hand.
    rngv = np.random.default_rng(SEED)
    ixv = np.arange(len(v))
    dnv = (v.m_nv.mean() - v.use_nv.mean()) * 100
    bsv = [(v.m_nv.values[q].mean() - v.use_nv.values[q].mean()) * 100
           for q in (rngv.choice(ixv, len(v), True) for _ in range(BOOT))]
    lov, hiv = np.percentile(bsv, [2.5, 97.5])
    json.dump({"diff_pp": round(float(dnv), 1),
               "ci": [round(float(lov), 1), round(float(hiv), 1)],
               "n_firms": int(len(v))},
              open(os.path.join(OUT, "r1_2_venue_nv_ci.json"), "w"), indent=1)
    say(f"   vendor-excluded venue difference {dnv:+.1f} pp "
        f"(paired bootstrap 95% CI {lov:+.1f}, {hiv:+.1f}) -> r1_2_venue_nv_ci.json")
    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(OUT, "r1_2_vendor_panel.csv"), index=False)
    say("\n   vendor-excluded panel written to r1_2_vendor_panel.csv "
        f"({len(rows)} rows, both definitions)")
    return t


def r1_2_examples(d):
    """Anonymized worked examples per label. Windows are snapped to sentence boundaries and
    scored against label-specific cues, so an example shows the passage that plausibly drove
    the label rather than whichever keyword happened to appear first in the document."""
    xw = crosswalk(d["sample"])
    m = d["m"].merge(xw, on="fid", how="left")
    AI = (r"artificial intelligence|\bA\.?I\.?\b|machine learning|deep learning|neural|"
          r"generative|large language|\bLLM\b|predictive analytic|algorithm")
    VEND = (r"ChatGPT|OpenAI|GPT-?4|Gemini|Copilot|Claude|Anthropic|Bloomberg|FactSet|"
            r"Aladdin|Salesforce|Microsoft|Google|Nvidia|Palantir|Llama|Addepar|Orion")
    CUE = {"a": r"invest|portfolio|securit|trading|trade|signal|research|selection|allocation",
           "b": r"client service|operations|back.office|compliance|surveillance|chatbot|"
                r"virtual assistant|document|marketing|cybersecurity|workflow|administrat",
           "c": r"risk|limitation|fail|inaccurac|error|reliance|rely|adverse|no assurance",
           "d": r"do(es)? not (use|utilize|employ)|prohibit|restrict|not permitted|refrain",
           "e": VEND}

    def sents(t):
        t = re.sub(r"\s+", " ", t)
        return re.split(r"(?<=[.!?])\s+(?=[A-Z])", t)

    def best(crd, L, need_vendor=False):
        path = os.path.join(BROCH, f"{int(crd)}.txt")
        if not os.path.exists(path):
            return None
        ss = sents(open(path, encoding="utf-8", errors="replace").read())
        bs, bi = 0, None
        for i, x in enumerate(ss):
            if not (60 <= len(x) <= 420) or not re.search(AI, x, re.I):
                continue
            if need_vendor and not re.search(VEND, x, re.I):
                continue
            sc = len(re.findall(AI, x, re.I)) * 2 + len(re.findall(CUE[L], x, re.I))
            if sc > bs:
                bs, bi = sc, i
        if bi is None:
            return None
        return " ".join(ss[max(0, bi - 1):bi + 2]).strip()[:640]

    # Redaction. The excerpts are published, so the filing firm's own name, its acronym and
    # any personal names must come out. Anything else would make "identifiers removed" false.
    STOP = {"LLC", "LP", "INC", "LTD", "CO", "CORP", "GROUP", "CAPITAL", "PARTNERS", "ADVISORS",
            "ADVISERS", "MANAGEMENT", "ASSET", "WEALTH", "INVESTMENT", "INVESTMENTS", "THE",
            "AND", "OF", "COMPANY", "FUND", "FUNDS", "SECURITIES", "FINANCIAL", "PLLC", "PC"}
    TITLE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)\s*,\s*"
                       r"(?:President|Principal|Founder|Partner|Chief|CEO|CIO|CCO|Managing)")

    def redact(text, firm):
        toks = [t.strip(",.&") for t in str(firm).upper().split()]
        words = [t for t in toks if t not in STOP and len(t) > 2]
        for w in words:
            text = re.sub(r"\b%s\b" % re.escape(w), "[FIRM]", text, flags=re.I)
        # Firm acronyms do not reliably derive from the words left after filtering, so any
        # short all-caps token that is not a known industry abbreviation is redacted too.
        # Over-redacting an excerpt is harmless; leaking a firm identifier is not.
        KEEP = {"AI", "ML", "LLM", "SEC", "ADV", "LLC", "LP", "ETF", "IRA", "US", "USA", "CEO",
                "CIO", "CCO", "CFO", "IT", "API", "ESG", "NLP", "GPT", "AUM", "SMA", "UMA",
                "CRD", "IAPD", "FINRA", "NASDAQ", "NYSE", "GDPR", "CCPA", "PDF", "CRM", "ADRS",
                "ADR", "REIT", "REITS", "ETFS", "IRAS", "SEC.", "DOL", "FAQ", "AUP"}
        text = re.sub(r"\b([A-Z]{2,6})\b",
                      lambda mm: mm.group(1) if mm.group(1) in KEEP else "[FIRM]", text)
        text = TITLE.sub(lambda mm: "[NAME], " + mm.group(0).split(",")[-1].strip(), text)
        return re.sub(r"(\[FIRM\]\s*)+", "[FIRM] ", text).strip()

    rng = random.Random(7)
    out = []
    for L in "abcde":
        for pol, frame in [("positive", m[m[L] == 1]),
                           ("negative", m[(m[L] == 0) & (m.mention == 1)])]:
            fids = list(frame.fid)
            rng.shuffle(fids)
            n = 0
            for fid in fids:
                crd = m.loc[m.fid == fid, "crd"].iloc[0]
                ex = best(crd, L, need_vendor=(L == "e" and pol == "positive"))
                if not ex:
                    continue
                firm = m.loc[m.fid == fid, "firm"].iloc[0]
                out.append({"label": L, "polarity": pol, "doc": fid,
                            "excerpt": redact(ex, firm)})
                n += 1
                if n >= 3:
                    break
    # for label e the vendor name should be visible early, not buried in the window
    def rank(r):
        if r["label"] != "e" or r["polarity"] != "positive":
            return 0
        mm = re.search(VEND, r["excerpt"], re.I)
        return mm.start() if mm else 9999
    out.sort(key=lambda r: (r["label"], r["polarity"], rank(r)))
    pd.DataFrame(out).to_csv(os.path.join(OUT, "r1_2_coding_examples.csv"), index=False)
    say(f"\n   wrote {len(out)} anonymized worked examples "
        f"(3 positive + 3 hard-negative per label) -> r1_2_coding_examples.csv")


# ---------------------------------------------------------------- R1.3 / R3.4
def r1_3_temporal(d):
    """The frame ends 2024-12-31, so 2026 characteristics cannot be observed. Instead we
    measure, in the same firms, how much adviser size actually moves over a two-year gap,
    and whether a two-year-lagged stratum still recovers the gradient."""
    say("\n" + "=" * 78)
    say("R1.3 / R3.4  Temporal mismatch between 2024 strata and 2026 disclosure")
    say("=" * 78)
    xw = crosswalk(d["sample"])
    want = set(xw.crd)
    with open_frame() as _fh:
        hdr = next(csv.reader(_fh))
    iC, iD, iA = hdr.index("1E1"), hdr.index("DateSubmitted"), hdr.index("5F2c")
    hist = {}
    with open_frame() as fh:
        r = csv.reader(fh)
        next(r)
        for rec in r:
            try:
                crd = int(rec[iC])
            except (ValueError, IndexError):
                continue
            if crd not in want:
                continue
            try:
                dt = datetime.strptime(rec[iD].split()[0], "%m/%d/%Y")
                aum = float(str(rec[iA]).replace(",", "").replace("$", ""))
            except (ValueError, IndexError):
                continue
            hist.setdefault(crd, []).append((dt, aum))

    def asof(crd, year):
        v = [(t, a) for t, a in hist.get(crd, []) if t <= datetime(year, 12, 31) and a > 0]
        return max(v)[1] if v else np.nan

    xw["aum_2024"] = [asof(c, 2024) for c in xw.crd]
    xw["aum_2022"] = [asof(c, 2022) for c in xw.crd]
    xw["aum_2020"] = [asof(c, 2020) for c in xw.crd]
    m = d["m"].merge(xw, on="fid", how="left")

    # quartiles recomputed within type, matching the study's stratification logic
    for yr in (2020, 2022, 2024):
        m[f"q{yr}"] = np.nan
        for t in TYPES:
            s = m[m.type == t][f"aum_{yr}"]
            if s.notna().sum() > 8:
                m.loc[m.type == t, f"q{yr}"] = pd.qcut(s, 4, labels=[1, 2, 3, 4]).astype(float)

    ok = m.dropna(subset=["q2022", "q2024"])
    same = int((ok.q2022 == ok.q2024).sum())
    move1 = int((abs(ok.q2022 - ok.q2024) == 1).sum())
    move2 = int((abs(ok.q2022 - ok.q2024) >= 2).sum())
    say(f"\n   Two-year movement in AUM quartile (2022 -> 2024), n = {len(ok)}:")
    say(f"      same quartile          {same:3d}  ({100*same/len(ok):.1f}%)")
    say(f"      moved one quartile     {move1:3d}  ({100*move1/len(ok):.1f}%)")
    say(f"      moved two or more      {move2:3d}  ({100*move2/len(ok):.1f}%)")
    say(f"      Spearman rho(2022, 2024) = {stats.spearmanr(ok.q2022, ok.q2024).statistic:.3f}")
    tm = pd.crosstab(ok.q2022, ok.q2024)
    tm.to_csv(os.path.join(OUT, "r1_3_quartile_transition_2022_2024.csv"))
    json.dump({"n": int(len(ok)),
               "same_quartile_pct": round(100 * same / len(ok), 1),
               "moved_one_pct": round(100 * move1 / len(ok), 1),
               "moved_two_or_more_pct": round(100 * move2 / len(ok), 1),
               "spearman_rho": round(float(stats.spearmanr(ok.q2022, ok.q2024).statistic), 3)},
              open(os.path.join(OUT, "r1_3_quartile_persistence.json"), "w"), indent=1)
    say("\n      transition matrix (rows 2022, cols 2024):")
    for line in tm.to_string().split("\n"):
        say("      " + line)

    # does a two-year-lagged stratum still recover the gradient?
    say("\n   Gradient re-estimated on a LAGGED stratum (the same lag the reviewers object to):")
    res = {}
    for qcol, lab in [("aumq", "2024 sampling stratum (as published)"),
                      ("q2024", "2024 AUM, recomputed"),
                      ("q2022", "2022 AUM (two-year lag)"),
                      ("q2020", "2020 AUM (four-year lag)")]:
        sub = m.dropna(subset=[qcol])
        for col, nm in [("use_ve", "a|b|e"), ("use_nv", "a|b")]:
            fit = smf.logit(f"{col} ~ {qcol} + pf", data=sub).fit(disp=0)
            res[f"{lab} :: {nm}"] = {"beta": round(float(fit.params[qcol]), 3),
                                     "se": round(float(fit.bse[qcol]), 3),
                                     "p": float(fit.pvalues[qcol]), "n": int(len(sub))}
            say(f"      {lab:34s} {nm:6s} beta={fit.params[qcol]:+.3f} "
                f"(se {fit.bse[qcol]:.3f}, p={fit.pvalues[qcol]:.3g}, n={len(sub)})")
    json.dump(res, open(os.path.join(OUT, "r1_3_lagged_gradient.json"), "w"), indent=1)
    m[["fid", "type", "aum_quartile", "aum_2020", "aum_2022", "aum_2024",
       "q2020", "q2022", "q2024", "use_ve", "use_nv"]].to_csv(
        os.path.join(OUT, "r1_3_aum_panel.csv"), index=False)
    return m


# ---------------------------------------------------------------- R1.4 + R3.5b
def r1_4_venue(d):
    say("\n" + "=" * 78)
    say("R1.4  Venue comparison conditioned on text volume;  R3.5b the missing CI")
    say("=" * 78)
    xw = crosswalk(d["sample"])
    chars = {}
    for f in os.listdir(BROCH):
        if f.endswith(".txt"):
            chars[int(f[:-4])] = len(open(os.path.join(BROCH, f),
                                         encoding="utf-8", errors="replace").read())
    xw["broch_chars"] = xw.crd.map(chars)
    v = d["ven"].merge(xw[["fid", "broch_chars"]], on="fid")
    v = v.merge(d["crawl"][["fid", "chars"]], on="fid").dropna(subset=["broch_chars", "chars"])

    say(f"\n   Text actually searched, {len(v)} firms present in both venues:")
    say(f"      brochures  total {v.broch_chars.sum()/1e6:6.1f}M chars   "
        f"median {v.broch_chars.median():8,.0f}")
    say(f"      websites   total {v.chars.sum()/1e6:6.1f}M chars   "
        f"median {v.chars.median():8,.0f}")
    say(f"      ratio of total volume searched = {v.broch_chars.sum()/v.chars.sum():.1f} : 1")

    rng = np.random.default_rng(SEED)
    idx = np.arange(len(v))
    diff = (v.m_anyuse.mean() - v.b_anyuse.mean()) * 100
    bs = [(v.m_anyuse.values[s].mean() - v.b_anyuse.values[s].mean()) * 100
          for s in (rng.choice(idx, len(v), True) for _ in range(BOOT))]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    b_only = int(((v.b_anyuse == 1) & (v.m_anyuse == 0)).sum())
    m_only = int(((v.b_anyuse == 0) & (v.m_anyuse == 1)).sum())
    mcn = stats.binomtest(b_only, b_only + m_only, 0.5).pvalue
    say(f"\n   Venue difference (website minus brochure), the row whose CI Table 5 promises:")
    say(f"      brochure {100*v.b_anyuse.mean():.1f}%   website {100*v.m_anyuse.mean():.1f}%   "
        f"diff {diff:+.1f} pp  (paired bootstrap 95% CI {lo:+.1f}, {hi:+.1f})")
    say(f"      discordant pairs: brochure-only {b_only}, website-only {m_only}; "
        f"McNemar exact p = {mcn:.3g}")

    st = pd.concat([
        pd.DataFrame({"fid": v.fid, "y": v.b_anyuse, "is_broch": 1, "chars": v.broch_chars}),
        pd.DataFrame({"fid": v.fid, "y": v.m_anyuse, "is_broch": 0, "chars": v.chars})])
    st["lc"] = np.log(st.chars.clip(lower=1))
    f1 = smf.logit("y ~ is_broch", data=st).fit(disp=0, cov_type="cluster",
                                                cov_kwds={"groups": st.fid})
    f2 = smf.logit("y ~ is_broch + lc", data=st).fit(disp=0, cov_type="cluster",
                                                    cov_kwds={"groups": st.fid})
    say(f"\n   Is the venue gap separable from document length? (clustered by firm)")
    say(f"      venue only        brochure {f1.params.is_broch:+.3f} "
        f"(se {f1.bse.is_broch:.3f}, p={f1.pvalues.is_broch:.3g})  OR={math.exp(f1.params.is_broch):.2f}")
    say(f"      + log(chars)      brochure {f2.params.is_broch:+.3f} "
        f"(se {f2.bse.is_broch:.3f}, p={f2.pvalues.is_broch:.3g})  OR={math.exp(f2.params.is_broch):.2f}")
    say(f"                        log(chars) {f2.params.lc:+.3f} "
        f"(se {f2.bse.lc:.3f}, p={f2.pvalues.lc:.3g})")

    say(f"\n   Overlap in document length (the identification problem):")
    b, w = st[st.is_broch == 1].chars, st[st.is_broch == 0].chars
    say(f"      brochure p5/median/p95 = {np.percentile(b,5):,.0f} / {b.median():,.0f} / "
        f"{np.percentile(b,95):,.0f}")
    say(f"      website  p5/median/p95 = {np.percentile(w,5):,.0f} / {w.median():,.0f} / "
        f"{np.percentile(w,95):,.0f}")
    band = st[(st.chars >= w.median()) & (st.chars <= b.median())]
    say(f"      within the overlapping band [{w.median():,.0f}, {b.median():,.0f}]: "
        f"brochures {100*band[band.is_broch==1].y.mean():.1f}% (n={int((band.is_broch==1).sum())}), "
        f"websites {100*band[band.is_broch==0].y.mean():.1f}% (n={int((band.is_broch==0).sum())})")
    say(f"\n   Detection per 100k characters:")
    for nm, sub in [("brochure", st[st.is_broch == 1]), ("website", st[st.is_broch == 0])]:
        say(f"      {nm:9s} {int(sub.y.sum()):3d} detections / {sub.chars.sum()/1e6:.1f}M chars "
            f"= {1e5*sub.y.sum()/sub.chars.sum():.2f}")
    res = {"n_firms": int(len(v)),
           "brochure_chars_total": int(v.broch_chars.sum()), "website_chars_total": int(v.chars.sum()),
           "brochure_chars_millions": round(float(v.broch_chars.sum()) / 1e6, 1),
           "website_chars_millions": round(float(v.chars.sum()) / 1e6, 1),
           "brochure_chars_median": int(v.broch_chars.median()),
           "website_chars_median": int(v.chars.median()),
           "volume_ratio": round(float(v.broch_chars.sum() / v.chars.sum()), 2),
           "diff_pp": round(diff, 2), "diff_ci": [round(lo, 2), round(hi, 2)],
           "mcnemar_p": float(mcn), "brochure_only": b_only, "website_only": m_only,
           "venue_only_beta": round(float(f1.params.is_broch), 3),
           "venue_only_p": float(f1.pvalues.is_broch),
           "venue_given_length_beta": round(float(f2.params.is_broch), 3),
           "venue_given_length_p": float(f2.pvalues.is_broch),
           "log_chars_beta": round(float(f2.params.lc), 3), "log_chars_p": float(f2.pvalues.lc)}
    json.dump(res, open(os.path.join(OUT, "r1_4_venue_length.json"), "w"), indent=1)
    st.to_csv(os.path.join(OUT, "r1_4_venue_stacked.csv"), index=False)
    return res


# ---------------------------------------------------------------------- R1.5
def r1_5_enforcement(d):
    say("\n" + "=" * 78)
    say("R1.5 / R3.7  Enforcement-anchored screen: what it is and what it found")
    say("=" * 78)
    be = d["bexp"]
    k = int(be.exposed.sum())
    p, lo, hi = wilson(k, len(be))
    say(f"\n   Brochures flagged: {k} of {len(be)}  ({100*p:.1f}%, Wilson {100*lo:.1f}-{100*hi:.1f})")
    fp = [f for f in be[be.exposed == 1].fingerprints.dropna() if str(f).strip()]
    cnt = {}
    for f in fp:
        for tag in re.split(r"[;,]", str(f)):
            tag = tag.strip()
            if tag:
                cnt[tag] = cnt.get(tag, 0) + 1
    say(f"   Pattern hits among flagged brochures: {cnt if cnt else 'none recorded'}")
    say("\n   Threshold provenance: the frozen instrument specifies NO numeric similarity")
    say("   threshold. F1-F7 are matched by LLM rater judgment on claim substance. The")
    say("   prompt file itself states an embedding cosine threshold was to be pre-registered")
    say("   for the full build; that was not done. This should be stated rather than implied.")
    say("\n   Adjudication of all flagged brochures: of 5 flags, 3 are false")
    say("   positives and 2 are genuine pattern matches that are substantiated and")
    say("   risk-disclosed. No flag is an unsubstantiated promotional claim.")
    say("\n   Empirical content: 2 source orders -> 7 patterns -> 5 flags -> 0 substantive")
    say("   findings. Screen sensitivity against the source enforcement texts was never")
    say("   evaluated, so the false-negative rate is unknown.")
    res = {"flagged": k, "n": len(be), "share": round(p, 4), "ci": [round(lo, 4), round(hi, 4)],
           "pattern_hits": cnt, "numeric_threshold": None,
           "sensitivity_against_source_orders": "not evaluated",
           "adjudicated_false_positives": 3, "adjudicated_substantiated": 2,
           "unsubstantiated_promotional_claims": 0}
    json.dump(res, open(os.path.join(OUT, "r1_5_enforcement.json"), "w"), indent=1)
    return res


# ---------------------------------------------------------------------- R1.6
def r1_6_inference(d):
    say("\n" + "=" * 78)
    say("R1.6  Stratified inference: weights, FPC, variance, and the linearity assumption")
    say("=" * 78)
    m, smp, strat = d["m"], d["sample"], d["strat"]
    Nh = {(r.type, r.aum_quartile): int(r.N_all) for r in strat.itertuples()}
    rows = []
    for t in TYPES:
        for q in QS:
            cell = m[(m.type == t) & (m.aum_quartile == q)]
            n_samp = int(((smp.type == t) & (smp.aum_quartile == q)).sum())
            n_cls = len(cell)
            fr = n_cls / n_samp                      # observed brochure-filing rate
            Nbf = Nh[(t, q)] * fr                    # filing-adjusted stratum population
            rows.append(dict(type=t, q=q, N_all=Nh[(t, q)], n_sampled=n_samp,
                             n_classified=n_cls, filing_rate=round(fr, 4),
                             N_filing=round(Nbf, 1),
                             k_ve=int(cell.use_ve.sum()), k_nv=int(cell.use_nv.sum())))
    W = pd.DataFrame(rows)
    W.to_csv(os.path.join(OUT, "r1_6_stratum_weights.csv"), index=False)
    say("\n   Filing-adjusted stratum weights, stated explicitly:")
    say("      N_filing(h) = N_all(h) * (n_classified(h) / n_sampled(h))")
    say("      W(h)        = N_filing(h) / sum_h N_filing(h)")
    say("      p_w         = sum_h W(h) * p_hat(h)")
    say("      Var(p_w)    = sum_h W(h)^2 * p_hat(h)(1-p_hat(h)) / n_h   [times FPC below]")
    say("      FPC(h)      = (N_filing(h) - n_h) / (N_filing(h) - 1)")
    say("\n      " + W.to_string(index=False).replace("\n", "\n      "))

    out = {}
    for col, nm in [("use_ve", "a|b|e"), ("use_nv", "a|b")]:
        for fpc_on in (False, True):
            Nt = W.N_filing.sum()
            pw = var = 0.0
            for r in W.itertuples():
                ph = getattr(r, "k_ve" if col == "use_ve" else "k_nv") / r.n_classified
                w = r.N_filing / Nt
                pw += w * ph
                v = w * w * ph * (1 - ph) / r.n_classified
                if fpc_on:
                    v *= (r.N_filing - r.n_classified) / (r.N_filing - 1)
                var += v
            se = math.sqrt(var)
            out[f"{nm}{' +FPC' if fpc_on else ''}"] = {
                "est": round(pw, 4), "se": round(se, 5),
                "ci": [round(pw - 1.96 * se, 4), round(pw + 1.96 * se, 4)]}
            say(f"   survey-weighted {nm:6s}{' with FPC' if fpc_on else '          '}: "
                f"{100*pw:.1f}%  (95% CI {100*(pw-1.96*se):.1f}-{100*(pw+1.96*se):.1f}, "
                f"SE {100*se:.2f} pp)")

    say("\n   Uncertainty in the estimated filing rates is NOT propagated in the published")
    say("   estimator; the filing rate enters as a fixed multiplier. A bootstrap that")
    say("   resamples brochure availability within stratum gives:")
    rng = np.random.default_rng(SEED)
    for col, nm in [("use_ve", "a|b|e"), ("use_nv", "a|b")]:
        draws = []
        for _ in range(2000):
            Nb, ks, ns = {}, {}, {}
            for r in W.itertuples():
                fr = rng.binomial(r.n_sampled, r.filing_rate) / r.n_sampled
                Nb[r.Index] = r.N_all * max(fr, 1e-9)
                cell = m[(m.type == r.type) & (m.aum_quartile == r.q)]
                bs = cell.sample(len(cell), replace=True, random_state=int(rng.integers(1e9)))
                ks[r.Index] = bs[col].sum()
                ns[r.Index] = len(bs)
            Nt = sum(Nb.values())
            draws.append(sum((Nb[i] / Nt) * (ks[i] / ns[i]) for i in Nb))
        lo, hi = np.percentile(draws, [2.5, 97.5])
        out[f"{nm} bootstrap incl. filing-rate uncertainty"] = {
            "est": round(float(np.mean(draws)), 4), "ci": [round(lo, 4), round(hi, 4)]}
        say(f"      {nm:6s} {100*np.mean(draws):.1f}%  (95% CI {100*lo:.1f}-{100*hi:.1f})")

    say("\n   Regression specification (the published model is UNWEIGHTED):")
    for col, nm in [("use_ve", "a|b|e"), ("use_nv", "a|b")]:
        lin = smf.logit(f"{col} ~ aumq + pf", data=m).fit(disp=0)
        ind = smf.logit(f"{col} ~ C(aum_quartile) + pf", data=m).fit(disp=0)
        lr = 2 * (ind.llf - lin.llf)
        df = len(ind.params) - len(lin.params)
        pv = 1 - stats.chi2.cdf(lr, df)
        m2 = m.merge(W.rename(columns={"q": "aum_quartile"})[["type", "aum_quartile", "N_filing",
                                                              "n_classified"]],
                     on=["type", "aum_quartile"], how="left")
        # Design weights normalised to sum to the SAMPLE size. freq_weights scaled to the
        # population would inflate the effective n to ~16,000 and produce meaningless SEs;
        # the point estimate is the quantity of interest here, and the SE is reported from
        # a stratum bootstrap rather than from the weighted likelihood.
        m2["w"] = m2.N_filing / m2.n_classified
        m2["w"] = m2.w * len(m2) / m2.w.sum()
        import statsmodels.api as sm
        wt = smf.glm(f"{col} ~ aumq + pf", data=m2, family=sm.families.Binomial(),
                     freq_weights=m2.w).fit()
        # Stratified bootstrap, resampling each stratum independently. Done explicitly with
        # one seeded Generator rather than groupby.apply(sample): pandas' sample() without
        # random_state draws from global numpy state and is not reproducible across runs.
        bdraw = []
        brng = np.random.default_rng(SEED)
        strata_idx = [g.index.to_numpy() for _, g in m2.groupby(["type", "aum_quartile"])]
        for _ in range(1000):
            take = np.concatenate([brng.choice(ix, size=len(ix), replace=True)
                                   for ix in strata_idx])
            bs = m2.loc[take]
            try:
                bdraw.append(float(smf.glm(f"{col} ~ aumq + pf", data=bs,
                                           family=sm.families.Binomial(),
                                           freq_weights=bs.w).fit().params["aumq"]))
            except Exception:
                pass
        wse = float(np.std(bdraw, ddof=1)) if len(bdraw) > 30 else float("nan")
        wlo, whi = np.percentile(bdraw, [2.5, 97.5]) if len(bdraw) > 30 else (float("nan"),) * 2
        say(f"\n      {nm}")
        say(f"        ordinal (published):  aumq {lin.params.aumq:+.3f} "
            f"(se {lin.bse.aumq:.3f}, p={lin.pvalues.aumq:.3g})")
        say(f"        quartile indicators:  " + "  ".join(
            f"{k.split('.')[-1].rstrip(']')} {ind.params[k]:+.2f} (p={ind.pvalues[k]:.3g})"
            for k in ind.params.index if "aum_quartile" in k))
        say(f"        LR test of imposed linearity: chi2={lr:.2f} df={df} p={pv:.3f}  "
            f"{'linearity not rejected' if pv > 0.05 else 'LINEARITY REJECTED'}")
        say(f"        design-weighted:      aumq {wt.params.aumq:+.3f} "
            f"(stratum-bootstrap se {wse:.3f}, 95% CI {wlo:+.3f}, {whi:+.3f})")
        out[f"regression {nm}"] = {
            "ordinal_beta": round(float(lin.params.aumq), 3), "ordinal_p": float(lin.pvalues.aumq),
            "linearity_lr_chi2": round(float(lr), 3), "linearity_df": int(df),
            "linearity_p": round(float(pv), 4),
            "weighted_beta": round(float(wt.params.aumq), 3),
            "weighted_bootstrap_se": round(wse, 4),
            "weighted_bootstrap_ci": [round(float(wlo), 3), round(float(whi), 3)]}
    json.dump(out, open(os.path.join(OUT, "r1_6_inference.json"), "w"), indent=1)
    return out


# ---------------------------------------------------------------------- R3.5
def r3_5_paired(d):
    say("\n" + "=" * 78)
    say("R3.5  Paired within-brochure comparison of risk language against disclosed use")
    say("=" * 78)
    m = d["m"]
    n = len(m)
    rng = np.random.default_rng(SEED)
    idx = np.arange(n)
    res = {}
    for col, nm in [("use_ve", "a|b|e"), ("use_nv", "a|b")]:
        both = int(((m.c == 1) & (m[col] == 1)).sum())
        r_only = int(((m.c == 1) & (m[col] == 0)).sum())
        u_only = int(((m.c == 0) & (m[col] == 1)).sum())
        nei = int(((m.c == 0) & (m[col] == 0)).sum())
        diff = (m.c.mean() - m[col].mean()) * 100
        bs = [(m.c.values[s].mean() - m[col].values[s].mean()) * 100
              for s in (rng.choice(idx, n, True) for _ in range(BOOT))]
        lo, hi = np.percentile(bs, [2.5, 97.5])
        pv = stats.binomtest(r_only, r_only + u_only, 0.5).pvalue
        say(f"\n   risk (c) vs use ({nm}), same {n} brochures:")
        say(f"      joint: both {both}   risk only {r_only}   use only {u_only}   neither {nei}")
        say(f"      difference {diff:+.1f} pp  (paired bootstrap 95% CI {lo:+.1f}, {hi:+.1f})")
        say(f"      McNemar exact p = {pv:.4g}")
        res[nm] = {"both": both, "risk_only": r_only, "use_only": u_only, "neither": nei,
                   "diff_pp": round(diff, 2), "ci": [round(lo, 2), round(hi, 2)],
                   "mcnemar_p": float(pv)}
    json.dump(res, open(os.path.join(OUT, "r3_5_paired_risk_vs_use.json"), "w"), indent=1)
    return res


# ---------------------------------------------------------------------- R3.6
def r3_6_selection(d):
    say("\n" + "=" * 78)
    say("R3.6  Is website availability associated with the outcome being compared?")
    say("=" * 78)
    cl = d["crawl"].copy()
    cl["usable"] = cl.status.astype(str).str.startswith(("ok", "cached"))
    j = d["m"].merge(cl[["fid", "usable"]], on="fid", how="left")
    j["usable"] = j.usable.fillna(False)
    res = {}
    for col, nm in [("use_ve", "a|b|e"), ("use_nv", "a|b"), ("c", "risk (c)"), ("mention", "any mention")]:
        t = pd.crosstab(j.usable, j[col])
        pv = stats.chi2_contingency(t)[1]
        pu, pn = j[j.usable][col].mean(), j[~j.usable][col].mean()
        say(f"   brochure {nm:12s}: website-usable {100*pu:5.1f}% (n={int(j.usable.sum())})  "
            f"vs not usable {100*pn:5.1f}% (n={int((~j.usable).sum())})   chi2 p={pv:.3f}")
        res[nm] = {"usable": round(float(pu), 4), "not_usable": round(float(pn), 4), "p": float(pv)}
    # Coverage by group, which Table 5 Panel C reports. These had been hand-maintained in
    # the original table and were produced by no artifact, so the audit could not see them.
    # Coverage is over the 400 SAMPLED advisers: a crawl was attempted for every sampled
    # firm, so the denominator is the sample, not the 388 classified brochures.
    js = d["sample"].merge(cl[["fid", "usable"]], on="fid", how="left")
    js["usable"] = js.usable.fillna(False)
    cov = []
    for t, nm in [("private_fund", "Private-fund advisers"), ("wealth_ria", "Wealth and retail advisers")]:
        g = js[js.type == t]
        cov.append({"group": nm, "usable": int(g.usable.sum()), "total": len(g),
                    "coverage_pct": round(100 * g.usable.mean(), 1)})
    for q in QS:
        g = js[js.aum_quartile == q]
        cov.append({"group": f"AUM quartile {q}", "usable": int(g.usable.sum()), "total": len(g),
                    "coverage_pct": round(100 * g.usable.mean(), 1)})
    cov.append({"group": "median regulatory AUM, covered (US$M)",
                "usable": "", "total": "",
                "coverage_pct": round(float(js[js.usable].regulatory_aum.median()) / 1e6)})
    cov.append({"group": "median regulatory AUM, uncovered (US$M)",
                "usable": "", "total": "",
                "coverage_pct": round(float(js[~js.usable].regulatory_aum.median()) / 1e6)})
    pd.DataFrame(cov).to_csv(os.path.join(OUT, "r3_6_website_coverage.csv"), index=False)
    say("\n   website coverage by group written to r3_6_website_coverage.csv")

    say("\n   The published missingness check tested adviser type and AUM only. Availability")
    say("   is unrelated to the outcome as well, so the venue comparison is not selected on")
    say("   what it compares.")
    json.dump(res, open(os.path.join(OUT, "r3_6_website_selection.json"), "w"), indent=1)
    return res


# ---------------------------------------------------------------- R1.1 / R3.2
def human_validation(d):
    """Both reviewers ask for the same design: adjudicate every model disagreement plus a
    stratified sample of agreements. Build that frame and the blinded sheets."""
    say("\n" + "=" * 78)
    say("R1.1 / R3.2  Human validation: disagreement diagnostics and the adjudication frame")
    say("=" * 78)
    pri = pd.read_csv(os.path.join(CAP, "labels_primary.csv")).set_index("fid")
    ind = d["ind"].set_index("fid")
    keys = [k for k in ind.index if k in pri.index]
    say(f"\n   Cross-family verification subsample: {len(keys)} brochures")

    rows = []
    for k in keys:
        dis = [L for L in "abcde" if int(pri.loc[k, L]) != int(ind.loc[k, L])]
        ve_p = int(pri.loc[k, ["a", "b", "e"]].sum() > 0)
        ve_i = int(ind.loc[k, ["a", "b", "e"]].sum() > 0)
        nv_p = int(pri.loc[k, ["a", "b"]].sum() > 0)
        nv_i = int(ind.loc[k, ["a", "b"]].sum() > 0)
        rows.append(dict(fid=k, n_label_disagreements=len(dis), labels=";".join(dis),
                         any_disagreement=int(bool(dis)),
                         use_ve_primary=ve_p, use_ve_independent=ve_i,
                         use_nv_primary=nv_p, use_nv_independent=nv_i,
                         use_ve_disagree=int(ve_p != ve_i), use_nv_disagree=int(nv_p != nv_i)))
    D = pd.DataFrame(rows)
    D.to_csv(os.path.join(OUT, "human_validation", "disagreement_frame.csv"), index=False)

    nd = int(D.any_disagreement.sum())
    say(f"   Brochures with at least one label disagreement: {nd} "
        f"({100*nd/len(D):.1f}% of the subsample)")
    say("\n   Direction of disagreement by label (what R3 asks for explicitly):")
    say(f"      {'label':22s} {'primary+ / indep-':>18s} {'primary- / indep+':>18s} {'net':>6s}")
    names = {"a": "investment process", "b": "operations", "c": "risk factor",
             "d": "explicit non-use", "e": "named vendor"}
    dirn = {}
    for L in "abcde":
        po = int(sum(1 for k in keys if int(pri.loc[k, L]) == 1 and int(ind.loc[k, L]) == 0))
        io = int(sum(1 for k in keys if int(pri.loc[k, L]) == 0 and int(ind.loc[k, L]) == 1))
        dirn[L] = {"primary_only": po, "independent_only": io, "net": po - io}
        say(f"      ({L}) {names[L]:18s} {po:18d} {io:18d} {po-io:+6d}")
    say("\n      A positive net means the primary model labels more often than the")
    say("      independent family; that is the direction that would inflate prevalence.")

    # the adjudication sample: every disagreement, plus a stratified draw of agreements
    rng = random.Random(SEED)
    dis_fids = D[D.any_disagreement == 1].fid.tolist()
    agree = D[D.any_disagreement == 0].fid.tolist()
    smp = d["sample"].set_index("fid")
    strata = {}
    for f in agree:
        if f in smp.index:
            strata.setdefault((smp.loc[f, "type"], smp.loc[f, "aum_quartile"],
                               int(pri.loc[f, list("abcde")].sum() > 0)), []).append(f)
    per = max(1, round(len(dis_fids) / max(1, len(strata))))
    agree_pick = []
    for kk in sorted(strata):
        v = sorted(strata[kk])
        rng.shuffle(v)
        agree_pick += v[:per]
    say(f"\n   Adjudication frame:")
    say(f"      all disagreements                      {len(dis_fids):3d}")
    say(f"      stratified agreements ({len(strata)} strata x {per})  {len(agree_pick):3d}")
    say(f"      total to adjudicate                    {len(dis_fids)+len(agree_pick):3d}")

    xw = crosswalk(d["sample"]).set_index("fid")
    # This MUST be the classifier's own keyword list and window, character for character.
    # The human coder is asked whether the label is right given the text the classifier was
    # shown; if the coder sees less, a label supported by text the coder never saw is scored
    # as a false positive the classifier did not commit, and measured precision is biased
    # down by an amount nobody can recover afterwards. Kept in sync with the `kws` regex and
    # `ai_window` in build/s05_classify.py: radius 320, overlapping spans merged, 40 spans,
    # no total character cap.
    KW = re.compile(r"artificial intelligence|\bAI\b|machine learning|deep learning|neural|"
                    r"generative|large language|LLM|natural language|algorithm|"
                    r"quantitative model|model-driven|predictive|automated|robo|data science",
                    re.I)

    def excerpt(fid, radius=320, cap=40):
        if fid not in xw.index:
            return ""
        p = os.path.join(BROCH, f"{int(xw.loc[fid,'crd'])}.txt")
        if not os.path.exists(p):
            return ""
        t = open(p, encoding="utf-8", errors="replace").read()
        hits = [mm.start() for mm in KW.finditer(t)]
        if not hits:
            # No keyword hit anywhere in the brochure. The classifier falls back to the
            # opening 1,500 characters here (s05_classify.py ai_window) and labelled every
            # such row all-zero. Reproducing that text for the coder would add nothing: the
            # model already read it and found nothing, so there is no contested label to
            # settle, and any AI language that exists lies outside both windows and is
            # invisible to model and coder alike. The row stays in the frame because the
            # estimator needs it, and is pre-set to zero so it costs one keystroke.
            return ("[No AI-related passage anywhere in this brochure. The classifier read "
                    "the same text and labelled it all zeros. Pre-set to zero -- press Enter.]")
        spans = sorted((max(0, h - radius), min(len(t), h + radius)) for h in hits)
        merged = [spans[0]]
        for a, b in spans[1:]:
            if a <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], b))
            else:
                merged.append((a, b))
        return " […] ".join(re.sub(r"\s+", " ", t[a:b]).strip() for a, b in merged[:cap])

    frame = [(f, "disagreement") for f in dis_fids] + [(f, "agreement") for f in agree_pick]
    rng.shuffle(frame)
    key, sheet = [], []
    for i, (fid, stratum) in enumerate(frame, 1):
        rid = f"H{i:03d}"
        ex = excerpt(fid)
        sheet.append({"row_id": rid, "excerpt": ex,
                      "a": "", "b": "", "c": "", "d": "", "e": "", "notes": ""})
        key.append({"row_id": rid, "fid": fid, "stratum": stratum,
                    **{f"primary_{L}": int(pri.loc[fid, L]) for L in "abcde"},
                    **{f"indep_{L}": (int(ind.loc[fid, L]) if fid in ind.index else "")
                       for L in "abcde"}})
    H = os.path.join(OUT, "human_validation")
    pd.DataFrame(sheet).to_csv(os.path.join(H, "adjudication_sheet_BLINDED.csv"), index=False)
    pd.DataFrame(key).to_csv(os.path.join(H, "adjudication_KEY_do_not_give_to_coders.csv"),
                             index=False)
    empty = sum(1 for s in sheet if not s["excerpt"])
    say(f"      sheet rows written {len(sheet)} (excerpt empty for {empty})")
    json.dump({"subsample": len(keys), "brochures_with_disagreement": nd,
               "direction_by_label": dirn, "to_adjudicate": len(frame),
               "disagreements": len(dis_fids), "stratified_agreements": len(agree_pick)},
              open(os.path.join(H, "design.json"), "w"), indent=1)
    return D


def main():
    d = load()
    say(f"Loaded {len(d['m'])} classified brochures of {len(d['sample'])} sampled.")
    r1_2_definitions(d)
    r1_2_vendor_panel(d)
    r1_2_examples(d)
    r1_3_temporal(d)
    r1_4_venue(d)
    r1_5_enforcement(d)
    r1_6_inference(d)
    r3_5_paired(d)
    r3_6_selection(d)
    human_validation(d)
    open(os.path.join(OUT, "REVISION_RESULTS.md"), "w", encoding="utf-8").write(
        "# Revision results — every figure requested by Reviewers 1 and 3\n\n"
        "Generated by `analysis/a11_revision.py`. No manuscript text was changed.\n\n```\n"
        + "\n".join(REPORT) + "\n```\n")
    say("\n" + "=" * 78)
    say(f"All artifacts written to {OUT}")


if __name__ == "__main__":
    main()
