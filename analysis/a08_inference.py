"""
a08_inference.py — design-based inference for the disclosure results.

Per-label and per-stratum Wilson 95% CIs, a linear-by-linear trend test of any-use across AUM
quartiles (within type and overall), a firm-level logistic regression of any-use on AUM quartile
(ordinal) and adviser type, and the type contrast. Prints a table; writes out/a08_inference.json.

Usage:  cd "Paper 10/analysis" && pip install statsmodels scipy && python a08_inference.py
"""
import json, math
import pandas as pd, numpy as np
from scipy import stats
import statsmodels.formula.api as smf
from pathlib import Path

OUT = Path("out"); OUT.mkdir(exist_ok=True)

def wilson(k, n, z=1.96):
    if n == 0: return (float("nan"),) * 3
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, c - h, c + h

def main():
    smp = pd.read_csv("../data/pilot_sample_400.csv"); smp["crd"] = smp.crd.astype(int)
    lab = pd.read_csv("../pilot/labels_primary.csv"); lab["crd"] = lab.crd.astype(int)
    d = smp.merge(lab, on="crd", how="left")
    d["cl"] = d["a"].notna()
    d = d[d.cl].copy()
    d["any_use"] = ((d[["a", "b", "e"]].sum(axis=1)) > 0).astype(int)
    d["aumq"] = d.aum_quartile.map({"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4})
    d["pf"] = (d.type == "private_fund").astype(int)
    res = {"labels": {}, "cells": {}, "trend": {}, "logit": {}}

    n = len(d)
    for L in ["a", "b", "c", "d", "e"]:
        p, lo, hi = wilson(int(d[L].sum()), n); res["labels"][L] = [round(x, 4) for x in (p, lo, hi)]
    p, lo, hi = wilson(int(d.any_use.sum()), n); res["any_use_overall"] = [round(x, 4) for x in (p, lo, hi)]

    for t in ["private_fund", "wealth_ria"]:
        for q in ["Q1", "Q2", "Q3", "Q4"]:
            c = d[(d.type == t) & (d.aum_quartile == q)]
            p, lo, hi = wilson(int(c.any_use.sum()), len(c))
            res["cells"][f"{t}|{q}"] = {"k": int(c.any_use.sum()), "n": len(c), "p": round(p, 4),
                                        "ci": [round(lo, 4), round(hi, 4)]}
    def trend(sub):
        x = sub.aumq.values.astype(float); y = sub.any_use.values.astype(float)
        xb, yb = x.mean(), y.mean()
        sxy = ((x - xb) * (y - yb)).sum(); sxx = ((x - xb) ** 2).sum(); syy = ((y - yb) ** 2).sum()
        r = sxy / math.sqrt(sxx * syy); z = r * math.sqrt(len(y) - 1)
        return round(z, 3), float(2 * (1 - stats.norm.cdf(abs(z))))
    for t in ["private_fund", "wealth_ria", "ALL"]:
        sub = d if t == "ALL" else d[d.type == t]
        z, pv = trend(sub); res["trend"][t] = {"z": z, "p": pv}

    m = smf.logit("any_use ~ aumq + pf", data=d).fit(disp=0)
    for term in ["Intercept", "aumq", "pf"]:
        res["logit"][term] = {"coef": round(float(m.params[term]), 3),
                              "se": round(float(m.bse[term]), 3), "p": float(m.pvalues[term])}
    res["type_contrast_chi2_p"] = float(stats.chi2_contingency(pd.crosstab(d.pf, d.any_use))[1])

    json.dump(res, open(OUT / "a08_inference.json", "w"), indent=1)
    print(json.dumps(res, indent=1))
    print("\n[a08] wrote out/a08_inference.json")

if __name__ == "__main__":
    main()
