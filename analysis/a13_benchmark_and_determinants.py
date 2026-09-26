"""
a13_benchmark_and_determinants.py — two results the revision needs that the original
design did not produce.

1. EXTERNAL BENCHMARK RECONCILIATION.
   Two other 2026 measurements of AI in Form ADV Part 2A now exist and disagree with this
   paper by close to an order of magnitude:
       Moond (SSRN, Sept 2026)          586 advisers, 2019 & 2024   0.85% -> 4.10% "mention"
       Astraeus RIA Market Monitor      6,384 independent wealth RIAs, Mar 2026   6% "use"
       this paper                       388 classified, 2026        23.7% use / 31.7% mention
   The gap is not a contradiction; it is a construct-and-design gap. This module walks the
   estimate down a ladder from the broadest construct to the narrowest and from this paper's
   design to their universe, so the reconciliation is arithmetic rather than assertion.

2. DETERMINANTS OF DISCLOSURE.
   The paper has no outcome variable. A true consequence analysis needs post-2026 assets,
   which the 2024 frame cannot supply. What the frame DOES support is the reverse question:
   which advisers disclose. Reported as determinants, never as consequences.

Usage:  cd "Paper 10" && python analysis/a13_benchmark_and_determinants.py
"""
import csv
import json
import math
import os
import re

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP = os.path.join(ROOT, "capsule", "data")
OUT = os.path.join(ROOT, "analysis", "out", "revision")
BROCH = os.path.join(ROOT, "data", "brochure_text", "current")
WEB = os.path.join(ROOT, "marketing", "data", "marketing_text")
TYPES = ["private_fund", "wealth_ria"]
QS = ["Q1", "Q2", "Q3", "Q4"]
REPORT = []

# The construct ladder. LITERAL is Moond's apparent construct; SCOPE is this study's
# rubric scope, which explicitly includes ML, predictive analytics and algorithmic
# decisioning; the LLM labels sit above both.
LITERAL = re.compile(r"artificial intelligence", re.I)
SCOPE = re.compile(r"artificial intelligence|machine learning|deep learning|neural network|"
                   r"generative ai|large language model|\bLLM\b|natural language processing|"
                   r"predictive analytic|predictive model|algorithmic|quantitative model|"
                   r"data science", re.I)


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


def crosswalk(smp):
    real = pd.read_csv(os.path.join(ROOT, "data", "pilot_sample_400.csv"))
    real = real.sort_values("crd").reset_index(drop=True)
    assert (smp.regulatory_aum.values == real.regulatory_aum.values).all()
    return pd.DataFrame({"fid": smp.fid.values, "crd": real.crd.values})


def load():
    smp = pd.read_csv(os.path.join(CAP, "sample.csv"))
    pri = pd.read_csv(os.path.join(CAP, "labels_primary.csv"))
    strat = pd.read_csv(os.path.join(CAP, "population_strata.csv"))
    m = smp.merge(pri, on="fid", how="left")
    m = m[m.a.notna()].copy()
    for c in "abcde":
        m[c] = m[c].astype(int)
    m["use_ve"] = ((m[["a", "b", "e"]].sum(axis=1)) > 0).astype(int)
    m["use_nv"] = ((m[["a", "b"]].sum(axis=1)) > 0).astype(int)
    m["mention"] = ((m[["a", "b", "c", "d", "e"]].sum(axis=1)) > 0).astype(int)
    m["aumq"] = m.aum_quartile.map({q: i + 1 for i, q in enumerate(QS)})
    m["pf"] = (m.type == "private_fund").astype(int)
    xw = crosswalk(smp)
    m = m.merge(xw, on="fid", how="left")
    # keyword constructs, read straight off the brochure text
    lit, sco, ch = [], [], []
    for crd in m.crd:
        p = os.path.join(BROCH, f"{int(crd)}.txt")
        t = open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else ""
        lit.append(int(bool(LITERAL.search(t))))
        sco.append(int(bool(SCOPE.search(t))))
        ch.append(len(t))
    m["kw_literal"] = lit
    m["kw_scope"] = sco
    m["chars"] = ch
    return m, smp, strat


def popweight(m, strat, col, subset=None):
    Nall = {(r.type, r.aum_quartile): int(r.N_all) for r in strat.itertuples()}
    sub = m if subset is None else m[m.type == subset]
    cells = {}
    for r in sub.itertuples():
        k = (r.type, r.aum_quartile)
        cells.setdefault(k, [0, 0])
        cells[k][1] += 1
        cells[k][0] += getattr(r, col)
    Nt = sum(Nall[k] for k in cells)
    return sum((Nall[k] / Nt) * (c[0] / c[1]) for k, c in cells.items())


def benchmark(m, strat):
    say("\n" + "=" * 80)
    say("EXTERNAL BENCHMARK RECONCILIATION")
    say("=" * 80)
    say("\n  Independent 2026 measurements of AI in Form ADV Part 2A:")
    say("     Moond (SSRN, Sep 2026)        586 advisers, 2019 & 2024   4.10% mention (2024)")
    say("     Astraeus RIA Market Monitor   6,384 indep. wealth RIAs    6%    disclosed use")
    say("     this paper                    388 classified, 2026        23.7% use, 31.7% mention")
    say("\n  The ladder from their number to ours. Each step changes exactly one thing.")
    rows = []
    steps = [
        ("kw_literal", "wealth_ria", True,
         "literal 'artificial intelligence', wealth RIAs, pop-weighted   <- Moond-like"),
        ("kw_literal", "wealth_ria", False, "literal 'artificial intelligence', wealth RIAs, design"),
        ("kw_literal", None, False, "literal 'artificial intelligence', all advisers, design"),
        ("use_ve", "wealth_ria", True,
         "LLM any-use, wealth RIAs, pop-weighted                         <- Astraeus-like"),
        ("use_ve", "wealth_ria", False, "LLM any-use, wealth RIAs, design"),
        ("use_nv", None, True, "LLM any-use vendor-excluded, all advisers, pop-weighted"),
        ("use_ve", None, True, "LLM any-use, all advisers, pop-weighted"),
        ("use_ve", None, False,
         "LLM any-use, all advisers, design                              <- this paper"),
        ("kw_scope", None, False, "rubric-scope keyword anywhere, all advisers, design"),
        ("mention", None, False, "LLM any-mention, all advisers, design"),
    ]
    for col, subset, pw, label in steps:
        sub = m if subset is None else m[m.type == subset]
        k, n = int(sub[col].sum()), len(sub)
        est = popweight(m, strat, col, subset) if pw else k / n
        p, lo, hi = wilson(k, n)
        rows.append(dict(step=label, measure=col, universe=subset or "all",
                         weighting="population" if pw else "design",
                         k=k, n=n, estimate=round(est, 4),
                         ci_lo=round(lo, 4), ci_hi=round(hi, 4)))
        say(f"     {100*est:5.1f}%   {label}")
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "a13_benchmark_ladder.csv"), index=False)
    lit_w0 = popweight(m, strat, "kw_literal", "wealth_ria")
    use_w0 = popweight(m, strat, "use_ve", "wealth_ria")
    json.dump({"construct_cost_pp": round(100 * (use_w0 - lit_w0), 1),
               "universe_cost_pp": round(100 * (m.use_ve.mean()
                                                - m[m.type == "wealth_ria"].use_ve.mean()), 1),
               "weighting_cost_pp": round(100 * (m[m.type == "wealth_ria"].use_ve.mean() - use_w0), 1)},
              open(os.path.join(OUT, "a13_ladder_deltas.json"), "w"), indent=1)

    say("\n  What the ladder shows:")
    lit_w = popweight(m, strat, "kw_literal", "wealth_ria")
    use_w = popweight(m, strat, "use_ve", "wealth_ria")
    say(f"     narrowing the CONSTRUCT to the literal phrase costs "
        f"{100*(use_w-lit_w):.1f} pp among wealth RIAs")
    say(f"     restricting the UNIVERSE to wealth RIAs costs "
        f"{100*(m.use_ve.mean()-m[m.type=='wealth_ria'].use_ve.mean()):.1f} pp")
    say(f"     population WEIGHTING costs a further "
        f"{100*(m[m.type=='wealth_ria'].use_ve.mean()-use_w):.1f} pp")
    say("     The three published estimates are therefore measuring three different things.")
    say("     None is wrong; the spread is the measurement problem this paper is about.")

    say("\n  Keyword against classifier on identical text (why a keyword census overstates or")
    say("  understates depending on which keyword):")
    for col, nm in [("kw_literal", "literal 'artificial intelligence'"),
                    ("kw_scope", "rubric-scope keyword")]:
        tp = int(((m[col] == 1) & (m.use_ve == 1)).sum())
        fp = int(((m[col] == 1) & (m.use_ve == 0)).sum())
        fn = int(((m[col] == 0) & (m.use_ve == 1)).sum())
        prec = tp / (tp + fp) if tp + fp else float("nan")
        rec = tp / (tp + fn) if tp + fn else float("nan")
        say(f"     {nm:34s} flags {int(m[col].sum()):3d}/388   "
            f"precision vs LLM any-use {prec:.2f}  recall {rec:.2f}")
    return rows


def determinants(m):
    say("\n" + "=" * 80)
    say("DETERMINANTS OF DISCLOSURE  (NOT consequences — see the caveat below)")
    say("=" * 80)
    panel = os.path.join(OUT, "r1_3_aum_panel.csv")
    if not os.path.exists(panel):
        say("  r1_3_aum_panel.csv missing; run a11_revision.py first.")
        return {}
    P = pd.read_csv(panel)
    d = m.merge(P[["fid", "aum_2020", "aum_2022", "aum_2024"]], on="fid", how="left")
    d = d[(d.aum_2022 > 0) & (d.aum_2024 > 0)].copy()
    d["g24"] = np.log(d.aum_2024) - np.log(d.aum_2022)
    d["lsize"] = np.log(d.aum_2024)
    d["lchars"] = np.log(d.chars.clip(lower=1))
    say(f"\n  n = {len(d)} advisers with usable 2022 and 2024 assets")
    say(f"  two-year log asset growth: median {d.g24.median():+.3f}  "
        f"IQR [{d.g24.quantile(.25):+.3f}, {d.g24.quantile(.75):+.3f}]")

    say("\n  Prior growth against later disclosure (does growth precede disclosure?):")
    res = {}
    for col, nm in [("use_ve", "any use (a|b|e)"), ("use_nv", "any use (a|b)"),
                    ("c", "risk language (c)")]:
        f = smf.logit(f"{col} ~ g24 + lsize + pf", data=d).fit(disp=0)
        say(f"     {nm:20s} growth {f.params.g24:+.3f} (se {f.bse.g24:.3f}, p={f.pvalues.g24:.3g})   "
            f"log size {f.params.lsize:+.3f} (p={f.pvalues.lsize:.3g})")
        res[nm] = {"growth_beta": round(float(f.params.g24), 4), "growth_p": float(f.pvalues.g24),
                   "logsize_beta": round(float(f.params.lsize), 4),
                   "logsize_p": float(f.pvalues.lsize), "n": int(len(d))}
    say("\n  Growth by disclosure status (descriptive, the Astraeus-style comparison):")
    for col, nm in [("use_ve", "any use (a|b|e)"), ("use_nv", "any use (a|b)")]:
        a, b = d[d[col] == 1].g24, d[d[col] == 0].g24
        u = stats.mannwhitneyu(a, b)
        say(f"     {nm:20s} disclosers median {a.median():+.3f} (n={len(a)})   "
            f"non-disclosers {b.median():+.3f} (n={len(b)})   Mann-Whitney p={u.pvalue:.3f}")
        res[nm + " growth split"] = {"discloser_median": round(float(a.median()), 4),
                                     "non_median": round(float(b.median()), 4),
                                     "p": float(u.pvalue)}

    say("\n  Does brochure length confound disclosure the way it confounds the venue test?")
    for col, nm in [("use_ve", "any use (a|b|e)")]:
        f1 = smf.logit(f"{col} ~ lsize + pf", data=d).fit(disp=0)
        f2 = smf.logit(f"{col} ~ lsize + pf + lchars", data=d).fit(disp=0)
        say(f"     {nm}: log size {f1.params.lsize:+.3f} (p={f1.pvalues.lsize:.3g}) -> "
            f"{f2.params.lsize:+.3f} (p={f2.pvalues.lsize:.3g}) once brochure length is added; "
            f"length itself {f2.params.lchars:+.3f} (p={f2.pvalues.lchars:.3g})")
        res["size net of brochure length"] = {
            "lsize_before": round(float(f1.params.lsize), 4),
            "lsize_after": round(float(f2.params.lsize), 4),
            "lsize_p_after": float(f2.pvalues.lsize),
            "lchars_beta": round(float(f2.params.lchars), 4),
            "lchars_p": float(f2.pvalues.lchars)}

    say("\n  CAVEAT, to be carried verbatim into any text that uses this:")
    say("     Disclosure is observed in 2026; assets end 2024-12-31. Every association above")
    say("     runs earlier assets -> later disclosure. These are determinants of who discloses.")
    say("     They are NOT consequences of disclosing, and cannot be reported as such without")
    say("     post-2026 assets from a fresh Form ADV pull.")
    json.dump(res, open(os.path.join(OUT, "a13_determinants.json"), "w"), indent=1)
    d[["fid", "type", "aum_quartile", "aum_2022", "aum_2024", "g24", "chars",
       "use_ve", "use_nv", "c", "kw_literal", "kw_scope"]].to_csv(
        os.path.join(OUT, "a13_determinants_panel.csv"), index=False)
    return res


def website_rows(m):
    """R3.6 asks for the website classifications to be validated separately. Add website
    cases to the human coding frame so both venues are covered by the same exercise."""
    say("\n" + "=" * 80)
    say("R3.6  Website cases added to the human coding frame")
    say("=" * 80)
    HV = os.path.join(OUT, "human_validation")
    ml = pd.read_csv(os.path.join(CAP, "venue", "marketing_labels.csv"))
    lab = [c for c in "abcde" if c in ml.columns]
    if not lab:
        say(f"  marketing_labels.csv has columns {list(ml.columns)}; no a-e labels to sample.")
        return
    xw = crosswalk(pd.read_csv(os.path.join(CAP, "sample.csv"))).set_index("fid")
    ml["pos"] = (ml[lab].sum(axis=1) > 0).astype(int)
    rng = np.random.default_rng(42)
    pos = ml[ml.pos == 1].fid.tolist()
    neg = ml[ml.pos == 0].fid.tolist()
    take_neg = list(rng.choice(neg, size=min(20, len(neg)), replace=False)) if neg else []
    picks = list(pos) + list(take_neg)
    say(f"  website-positive cases (census): {len(pos)}   sampled negatives: {len(take_neg)}")
    # Kept identical to the `KW` regex and `window()` in marketing/b03_classify_marketing.py:
    # radius 340, overlapping spans merged, 40 spans, no total cap. The coder must be shown
    # exactly the text the website classifier was shown, for the same reason as the brochure
    # excerpt in a11 -- otherwise a correct label looks like a false positive.
    KW = re.compile(r"artificial intelligence|\bAI\b|machine learning|deep learning|neural|"
                    r"generative|large language|LLM|natural language|algorithm|"
                    r"quantitative model|model-driven|predictive|automated|robo|data science",
                    re.I)
    rows, key = [], []
    for i, fid in enumerate(picks, 1):
        rid = f"W{i:03d}"
        crd = int(xw.loc[fid, "crd"]) if fid in xw.index else None
        p = os.path.join(WEB, f"{crd}.txt") if crd else ""
        t = open(p, encoding="utf-8", errors="replace").read() if p and os.path.exists(p) else ""
        hits = [mm.start() for mm in KW.finditer(t)]
        if hits:
            spans = sorted((max(0, h - 340), min(len(t), h + 340)) for h in hits)
            merged = [spans[0]]
            for a, b in spans[1:]:
                if a <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], b))
                else:
                    merged.append((a, b))
            ex = " […] ".join(re.sub(r"\s+", " ", t[a:b]).strip() for a, b in merged[:40])
        else:
            # As in a11: the website classifier fell back to the page opening and labelled
            # these all-zero, so reproducing that marketing copy for the coder settles
            # nothing. Pre-set to zero instead.
            ex = ("[No AI-related passage anywhere on this website. The classifier read the "
                  "same text and labelled it all zeros. Pre-set to zero -- press Enter.]")
        rows.append({"row_id": rid, "excerpt": ex, "a": "", "b": "", "c": "", "d": "",
                     "e": "", "notes": ""})
        key.append({"row_id": rid, "fid": fid, "stratum": "website",
                    **{f"primary_{L}": int(ml[ml.fid == fid][L].iloc[0]) for L in lab}})
    if not rows:
        say("  nothing to add.")
        return
    pd.DataFrame(rows).to_csv(os.path.join(HV, "website_sheet_BLINDED.csv"), index=False)
    pd.DataFrame(key).to_csv(os.path.join(HV, "website_KEY_do_not_give_to_coders.csv"),
                             index=False)
    # The website design, recorded so the scorer can weight the sampled negatives: the
    # positives are a census, the negatives stand for the whole website-negative pool.
    json.dump({"positives_census": len(pos), "negatives_population": len(neg),
               "negatives_sampled": len(take_neg), "seed": 42},
              open(os.path.join(HV, "website_design.json"), "w"), indent=1)
    say(f"  website_design.json  negatives sampled {len(take_neg)} of {len(neg)} "
        f"(weight {len(neg)/len(take_neg):.3f})" if take_neg else "  website_design.json")
    say("  the coding frame is assembled by a16_build_coding_app.py from these sheets.")


def main():
    os.makedirs(OUT, exist_ok=True)
    m, smp, strat = load()
    say(f"Loaded {len(m)} classified brochures.")
    benchmark(m, strat)
    determinants(m)
    website_rows(m)
    open(os.path.join(OUT, "BENCHMARK_AND_DETERMINANTS.md"), "w", encoding="utf-8").write(
        "# External benchmark reconciliation and determinants of disclosure\n\n"
        "Generated by `analysis/a13_benchmark_and_determinants.py`.\n\n```\n"
        + "\n".join(REPORT) + "\n```\n")
    say("\n" + "=" * 80)
    say(f"written to {OUT}")


if __name__ == "__main__":
    main()
