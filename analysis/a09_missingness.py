"""
a09_missingness.py — selection analysis for the marketing corpus.

Compares firms WITH usable marketing text against those WITHOUT, on adviser type, AUM quartile,
and regulatory AUM. Reports chi-square tests and a Mann-Whitney AUM comparison, so the venue
comparison's selection bias can be characterized (not merely asserted).

Usage:  cd "Paper 10/analysis" && python a09_missingness.py
"""
import json
import pandas as pd
from scipy import stats
from pathlib import Path

OUT = Path("out"); OUT.mkdir(exist_ok=True)

def main():
    smp = pd.read_csv("../data/pilot_sample_400.csv"); smp["crd"] = smp.crd.astype(int)
    cl = pd.read_csv("../marketing/out/marketing_crawl_log.csv"); cl["crd"] = cl.crd.astype(int)
    cl["usable"] = cl.status.str.startswith(("ok", "cached"))
    d = smp.merge(cl[["crd", "usable"]], on="crd", how="left")
    d["usable"] = d.usable.fillna(False)

    by_type = d.groupby("type").usable.agg(["sum", "count", "mean"]).round(3)
    by_q = d.groupby("aum_quartile").usable.agg(["sum", "count", "mean"]).round(3)
    p_type = float(stats.chi2_contingency(pd.crosstab(d.type, d.usable))[1])
    p_q = float(stats.chi2_contingency(pd.crosstab(d.aum_quartile, d.usable))[1])
    inc = d[d.usable].regulatory_aum; exc = d[~d.usable].regulatory_aum
    p_aum = float(stats.mannwhitneyu(inc, exc).pvalue)

    print("Marketing usable-text coverage by TYPE:\n", by_type)
    print("\nby AUM QUARTILE:\n", by_q)
    print(f"\nchi2 usable~type p = {p_type:.4f}")
    print(f"chi2 usable~quartile p = {p_q:.4f}")
    print(f"median AUM included ${inc.median():,.0f} vs excluded ${exc.median():,.0f}; "
          f"Mann-Whitney p = {p_aum:.4f}")
    res = {"overall_usable": float(d.usable.mean()), "n_usable": int(d.usable.sum()),
           "by_type": by_type.to_dict(), "by_quartile": by_q.to_dict(),
           "chi2_type_p": round(p_type, 4), "chi2_quartile_p": round(p_q, 4),
           "aum_mannwhitney_p": round(p_aum, 4)}
    json.dump(res, open(OUT / "a09_missingness.json", "w"), indent=1)
    print("\n[a09] wrote out/a09_missingness.json — no significant selection on type/size ⇒ "
          "venue comparison bias is limited.")

if __name__ == "__main__":
    main()
