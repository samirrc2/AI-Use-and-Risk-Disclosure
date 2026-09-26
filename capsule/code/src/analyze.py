"""
analyze.py — deterministic reproduction of every numerical result in the article
"AI Use and Risk Disclosure by Investment Advisers" from the frozen, pseudonymized dataset.

No network, no API keys, no randomness. Reads data/ (see data/README.md), writes
results/<run>/: tables/*.csv, figures/*.{png,svg}, and metrics_summary.md
(verdict-first). Every figure/table it emits corresponds to a numbered claim in
the manuscript; the mapping is printed and written to metrics_summary.md.

Usage:  python analyze.py           (paths resolved by io_paths for local or Code Ocean)
"""
import json
import math
import warnings
from pathlib import Path

import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf

import io_paths
from stats_util import wilson, confusion, prf, kappa_pabak, linear_trend_z

warnings.filterwarnings("ignore")
TYPES = ["private_fund", "wealth_ria"]
QS = ["Q1", "Q2", "Q3", "Q4"]


def load():
    D = io_paths.data_root()
    d = {
        "sample": pd.read_csv(D / "sample.csv"),
        "primary": pd.read_csv(D / "labels_primary.csv"),
        "secondary": pd.read_csv(D / "labels_secondary_sub.csv"),
        "independent": pd.read_csv(D / "labels_independent.csv"),
        "strata": pd.read_csv(D / "population_strata.csv"),
        "venue": pd.read_csv(D / "venue" / "venue_divergence.csv"),
        "broch_exp": pd.read_csv(D / "venue" / "brochure_exposure.csv"),
        "mkt_exp": pd.read_csv(D / "venue" / "marketing_exposure.csv"),
        "crawl": pd.read_csv(D / "venue" / "marketing_crawl_log.csv"),
    }
    return d


def merged_labels(d):
    m = d["sample"].merge(d["primary"], on="fid", how="left")
    m["classified"] = m["a"].notna()
    m = m[m.classified].copy()
    for c in "abcde":
        m[c] = m[c].astype(int)
    m["any_use"] = ((m[["a", "b", "e"]].sum(axis=1)) > 0).astype(int)
    m["mention"] = ((m[["a", "b", "c", "d", "e"]].sum(axis=1)) > 0).astype(int)
    m["aumq"] = m.aum_quartile.map({"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4})
    m["pf"] = (m.type == "private_fund").astype(int)
    return m


def t1_typology(m, out):
    n = len(m)
    rows = []
    names = {"a": "AI in investment process", "b": "AI in operations/client service",
             "c": "AI as disclosed risk factor", "d": "Explicit non-use", "e": "Named vendor"}
    for L in "abcde":
        p, lo, hi = wilson(int(m[L].sum()), n)
        rows.append([f"({L}) {names[L]}", int(m[L].sum()), n, round(p, 4), round(lo, 4), round(hi, 4)])
    for key, lab in [("mention", "Any mention (a-e)"), ("any_use", "Any use (a OR b OR e)")]:
        p, lo, hi = wilson(int(m[key].sum()), n)
        rows.append([lab, int(m[key].sum()), n, round(p, 4), round(lo, 4), round(hi, 4)])
    df = pd.DataFrame(rows, columns=["label", "k", "n", "prevalence", "ci_lo", "ci_hi"])
    df.to_csv(out / "tables" / "table1_typology.csv", index=False)
    return df


def t2_gradient(m, out):
    cells = []
    for t in TYPES:
        for q in QS:
            c = m[(m.type == t) & (m.aum_quartile == q)]
            p, lo, hi = wilson(int(c.any_use.sum()), len(c))
            cells.append([t, q, int(c.any_use.sum()), len(c), round(p, 4), round(lo, 4), round(hi, 4)])
    cdf = pd.DataFrame(cells, columns=["type", "aum_quartile", "k", "n", "any_use", "ci_lo", "ci_hi"])
    cdf.to_csv(out / "tables" / "table2_gradient.csv", index=False)

    trend = {}
    for t in TYPES + ["ALL"]:
        sub = m if t == "ALL" else m[m.type == t]
        z = linear_trend_z(sub.aumq.tolist(), sub.any_use.tolist())
        trend[t] = {"z": round(z, 3), "p": float(2 * (1 - stats.norm.cdf(abs(z))))}
    fit = smf.logit("any_use ~ aumq + pf", data=m).fit(disp=0)
    logit = {k: {"coef": round(float(fit.params[k]), 3), "se": round(float(fit.bse[k]), 3),
                 "p": float(fit.pvalues[k])} for k in ["Intercept", "aumq", "pf"]}
    contrast = {
        "private_fund": round(float(m[m.pf == 1].any_use.mean()), 4),
        "wealth_ria": round(float(m[m.pf == 0].any_use.mean()), 4),
        "chi2_p": float(stats.chi2_contingency(pd.crosstab(m.pf, m.any_use))[1]),
    }
    res = {"trend": trend, "logit": logit, "type_contrast": contrast}
    json.dump(res, open(out / "tables" / "table2_inference.json", "w"), indent=1)
    return cdf, res


def t3_weighting(m, d, out):
    Nh = {(r.type, r.aum_quartile): int(r.N_all) for r in d["strata"].itertuples()}
    smp = d["sample"]
    prev = {}
    for t in TYPES:
        for q in QS:
            c = m[(m.type == t) & (m.aum_quartile == q)]
            sampled = int(((smp.type == t) & (smp.aum_quartile == q)).sum())
            prev[(t, q)] = (int(c.any_use.sum()), len(c), sampled)
    Nbf = {k: Nh[k] * (prev[k][1] / prev[k][2]) for k in prev}

    def weighted(Nmap):
        Nt = sum(Nmap.values())
        pw = var = 0.0
        for k in prev:
            kk, nn, _ = prev[k]
            ph = kk / nn
            W = Nmap[k] / Nt
            pw += W * ph
            if nn > 1:
                var += W * W * ph * (1 - ph) / nn
        se = math.sqrt(var)
        return pw, pw - 1.96 * se, pw + 1.96 * se, Nt

    rows = []
    for t in TYPES:
        for q in QS:
            kk, nn, _ = prev[(t, q)]
            rows.append([t, q, Nh[(t, q)], round(Nbf[(t, q)]), nn, round(kk / nn, 4)])
    tab = pd.DataFrame(rows, columns=["type", "aum_quartile", "N_all", "N_filing", "n_classified", "any_use"])
    tab.to_csv(out / "tables" / "table3_weighting.csv", index=False)
    a = weighted(Nh)
    b = weighted(Nbf)
    res = {"all_aum_universe": {"est": round(a[0], 4), "ci": [round(a[1], 4), round(a[2], 4)], "N": round(a[3])},
           "brochure_filing_universe": {"est": round(b[0], 4), "ci": [round(b[1], 4), round(b[2], 4)], "N": round(b[3])},
           "design_unweighted": round(float(m.any_use.mean()), 4)}
    json.dump(res, open(out / "tables" / "table3_weighting.json", "w"), indent=1)
    return tab, res


def _code_dicts(primary_df, other_df):
    """Return (model_dict, other_dict) keyed by fid over the intersection."""
    p = primary_df.set_index("fid")
    o = other_df.set_index("fid")
    keys = [k for k in o.index if k in p.index]
    md = {k: {c: int(p.loc[k, c]) for c in "abcde"} for k in keys}
    od = {k: {c: int(o.loc[k, c]) for c in "abcde"} for k in keys}
    return md, od


def _wconf(md, hd, w, keys, L):
    """Design-weighted 2x2 counts for label L over the two-phase validation sample."""
    tp = fp = fn = tn = 0.0
    for k in keys:
        m, h, wt = md[k][L], hd[k][L], w[k]
        if m and h: tp += wt
        elif m and not h: fp += wt
        elif not m and h: fn += wt
        else: tn += wt
    return tp, fp, fn, tn


def t4_validation(d, out):
    md, hd = _code_dicts(d["primary"], d["independent"])
    keys = list(md.keys())
    n = len(keys)
    # Two-phase (verification) sampling weights. Model-positive brochures (any label a-e, i.e.
    # any mention) are a census (inclusion probability 1); model-negatives are sampled, so each
    # carries weight (population model-negatives)/(sampled model-negatives). Weights are derived
    # from the data, not hard-coded, so the metrics apply to the full classified population.
    prim = d["primary"].set_index("fid")
    mention_all = (prim[list("abcde")].sum(axis=1) > 0)
    n_neg_pop = int((~mention_all).sum())
    ment = {k: int(mention_all.loc[k]) for k in keys}
    n_neg_sampled = sum(1 for k in keys if ment[k] == 0)
    wneg = n_neg_pop / n_neg_sampled if n_neg_sampled else 1.0
    w = {k: (1.0 if ment[k] == 1 else wneg) for k in keys}

    names = {"a": "investment process", "b": "operations", "c": "risk factor",
             "d": "explicit non-use", "e": "named vendor"}
    rows = []
    for L in "abcde":
        tp, fp, fn, tn = confusion(md, hd, L)                 # observed (unweighted) counts
        wtp, wfp, wfn, wtn = _wconf(md, hd, w, keys, L)       # design-weighted
        prec, rec, f1 = prf(wtp, wfp, wfn)
        k, pk = kappa_pabak(wtp, wfp, wfn, wtn)
        agr = (wtp + wtn) / (wtp + wfp + wfn + wtn)
        rows.append([f"({L}) {names[L]}", tp + fp, tp + fn, tp, fp, fn, tn,
                     round(prec, 3), round(rec, 3), round(f1, 3), round(agr, 3), round(k, 3), round(pk, 3)])
    # any-use derived
    mu = {k: {"x": 1 if (md[k]["a"] or md[k]["b"] or md[k]["e"]) else 0} for k in keys}
    hu = {k: {"x": 1 if (hd[k]["a"] or hd[k]["b"] or hd[k]["e"]) else 0} for k in keys}
    tp, fp, fn, tn = confusion(mu, hu, "x")
    wtp, wfp, wfn, wtn = _wconf(mu, hu, w, keys, "x")
    prec, rec, f1 = prf(wtp, wfp, wfn)
    k, pk = kappa_pabak(wtp, wfp, wfn, wtn)
    rows.append(["Any use (a OR b OR e)", tp + fp, tp + fn, tp, fp, fn, tn,
                 round(prec, 3), round(rec, 3), round(f1, 3),
                 round((wtp + wtn) / (wtp + wfp + wfn + wtn), 3), round(k, 3), round(pk, 3)])
    cols = ["label", "model_pos", "indep_pos", "tp", "fp", "fn", "tn",
            "precision", "recall", "f1", "pct_agree", "kappa", "pabak"]
    tab = pd.DataFrame(rows, columns=cols)
    tab.to_csv(out / "tables" / "table4_validation.csv", index=False)

    # same-family reproducibility (secondary vs primary on the 60-subsample)
    smd, ssd = _code_dicts(d["primary"], d["secondary"])
    sn = len(smd)
    srows = []
    for L in "abcde":
        tp, fp, fn, tn = confusion(smd, ssd, L)
        k, pk = kappa_pabak(tp, fp, fn, tn)
        srows.append([L, sn, round((tp + tn) / sn, 3), round(k, 3)])
    # The paper also quotes same-family agreement on the composite any-mention measure
    # (Section 4.3). Emit it alongside the per-label rows so every published figure has
    # an artifact behind it.
    mu = {c: {"x": int(any(smd[c][L] for L in "abcde"))} for c in smd}
    hu = {c: {"x": int(any(ssd[c][L] for L in "abcde"))} for c in ssd}
    tp, fp, fn, tn = confusion(mu, hu, "x")
    k, pk = kappa_pabak(tp, fp, fn, tn)
    srows.append(["any-mention (a|b|c|d|e)", sn, round((tp + tn) / sn, 3), round(k, 3)])
    # Section 4.3 also quotes same-family agreement on the composite any-USE measure, which
    # is a different union from any-mention and was not emitted by any artifact.
    mu = {c: {"x": int(any(smd[c][L] for L in "abe"))} for c in smd}
    hu = {c: {"x": int(any(ssd[c][L] for L in "abe"))} for c in ssd}
    tp, fp, fn, tn = confusion(mu, hu, "x")
    k, pk = kappa_pabak(tp, fp, fn, tn)
    srows.append(["any-use (a|b|e)", sn, round((tp + tn) / sn, 3), round(k, 3)])
    sf = pd.DataFrame(srows, columns=["label", "n", "pct_agree", "kappa"])
    sf.to_csv(out / "tables" / "table4b_samefamily.csv", index=False)
    return tab, sf, n, sn


def t5_venue(d, out):
    v = d["venue"]
    n = len(v)
    row = {"n_firms_both_venues": n,
           "brochure_anyuse": round(float(v.b_anyuse.mean()), 4),
           "marketing_anyuse": round(float(v.m_anyuse.mean()), 4),
           "brochure_exposed": round(float(v.b_exposed.mean()), 4),
           "marketing_exposed": round(float(v.m_exposed.mean()), 4)}
    # McNemar-style directional counts for any-use
    b_only = int(((v.b_anyuse == 1) & (v.m_anyuse == 0)).sum())
    m_only = int(((v.b_anyuse == 0) & (v.m_anyuse == 1)).sum())
    row["brochure_only_anyuse"] = b_only
    row["marketing_only_anyuse"] = m_only
    pd.DataFrame([["Any use (a OR b OR e)", row["brochure_anyuse"], row["marketing_anyuse"],
                   round(row["marketing_anyuse"] - row["brochure_anyuse"], 4)],
                  ["Exposure screen (F1-F7)", row["brochure_exposed"], row["marketing_exposed"],
                   round(row["marketing_exposed"] - row["brochure_exposed"], 4)]],
                 columns=["measure", "brochure", "marketing", "marketing_minus_brochure"]
                 ).to_csv(out / "tables" / "table5_venue.csv", index=False)
    json.dump(row, open(out / "tables" / "table5_venue.json", "w"), indent=1)
    return row


def exposure_and_missingness(m, d, out):
    be = d["broch_exp"]
    # Section 4.4 prints a Wilson interval on the screen's hit rate; emit it rather than
    # leaving the reader to recompute it.
    _k, _n = int(be.exposed.sum()), len(be)
    _p, _lo, _hi = wilson(_k, _n)
    exp = {"brochure_exposed_k": _k, "brochure_n": _n,
           "brochure_exposed_share": round(float(be.exposed.mean()), 4),
           "brochure_exposed_ci": [round(_lo, 4), round(_hi, 4)]}
    json.dump(exp, open(out / "tables" / "exposure_summary.json", "w"), indent=1)

    cl = d["crawl"].copy()
    cl["usable"] = cl.status.str.startswith(("ok", "cached"))
    j = d["sample"].merge(cl[["fid", "usable"]], on="fid", how="left")
    j["usable"] = j.usable.fillna(False)
    p_type = float(stats.chi2_contingency(pd.crosstab(j.type, j.usable))[1])
    p_q = float(stats.chi2_contingency(pd.crosstab(j.aum_quartile, j.usable))[1])
    inc = j[j.usable].regulatory_aum
    exc = j[~j.usable].regulatory_aum
    p_aum = float(stats.mannwhitneyu(inc, exc).pvalue)
    miss = {"n_usable": int(j.usable.sum()), "overall_usable_share": round(float(j.usable.mean()), 4),
            "chi2_type_p": round(p_type, 4), "chi2_quartile_p": round(p_q, 4),
            "median_aum_included": float(inc.median()), "median_aum_excluded": float(exc.median()),
            "aum_mannwhitney_p": round(p_aum, 4)}
    json.dump(miss, open(out / "tables" / "missingness.json", "w"), indent=1)
    return exp, miss


def figures(m, t1, t4, t5, out):
    import matplotlib
    matplotlib.use("Agg")
    # SVG clip-path ids are randomised per process unless the hash salt is fixed; without
    # this the vector copies are not byte-reproducible even though the PNGs are.
    matplotlib.rcParams["svg.hashsalt"] = "disclosed-intelligence"
    import matplotlib.pyplot as plt

    # Figure 1 — typology label prevalence with Wilson 95% CIs
    tl = t1[t1.label.str.match(r"^\([a-e]\)")].copy()
    tlabels = tl.label.tolist()
    tprev = [p * 100 for p in tl.prevalence.tolist()]
    tlo = [max(0.0, pv - lo * 100) for pv, lo in zip(tprev, tl.ci_lo.tolist())]
    thi = [max(0.0, hi * 100 - pv) for pv, hi in zip(tprev, tl.ci_hi.tolist())]
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    yp = list(range(len(tlabels)))
    ax.barh(yp, tprev, color="#2b6cb0",
            xerr=[tlo, thi], error_kw=dict(ecolor="#1a365d", capsize=3, lw=1))
    ax.set_yticks(yp)
    ax.set_yticklabels(tlabels, fontsize=8)
    ax.set_xlabel("Prevalence among 388 classified brochures (%)")
    ax.set_title("Typology label prevalence (Wilson 95% CIs)")
    ax.invert_yaxis()
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(out / "figures" / f"fig1_typology.{ext}", dpi=150,
                    metadata={"Date": None} if ext == "svg" else None)
    plt.close(fig)

    # Figure 2 — any-use gradient by stratum
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    width = 0.38
    xs = range(4)
    for i, (t, color, lab) in enumerate([("private_fund", "#2b6cb0", "Private-fund"),
                                          ("wealth_ria", "#dd6b20", "Wealth/retail")]):
        vals = [m[(m.type == t) & (m.aum_quartile == q)].any_use.mean() * 100 for q in QS]
        ax.bar([x + i * width for x in xs], vals, width, label=lab, color=color)
    ax.set_xticks([x + width / 2 for x in xs])
    ax.set_xticklabels(QS)
    ax.set_ylabel("Any-use disclosure (%)")
    ax.set_xlabel("AUM quartile")
    ax.set_title("Disclosed AI use by adviser type and size")
    ax.legend(frameon=False)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(out / "figures" / f"fig2_gradient.{ext}", dpi=150,
                    metadata={"Date": None} if ext == "svg" else None)
    plt.close(fig)

    # Figure 3 — validation kappa per label + any-use
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    labs = t4.label.tolist()
    ks = t4.kappa.tolist()
    ax.barh(range(len(labs)), ks, color="#38a169")
    ax.set_yticks(range(len(labs)))
    ax.set_yticklabels(labs, fontsize=8)
    ax.set_xlabel("Cohen's κ (model vs. independent re-coding)")
    ax.set_xlim(0, 1)
    ax.set_title("Independent cross-family validation")
    ax.invert_yaxis()
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(out / "figures" / f"fig3_validation.{ext}", dpi=150,
                    metadata={"Date": None} if ext == "svg" else None)
    plt.close(fig)

    # Figure 4 — venue comparison
    fig, ax = plt.subplots(figsize=(4.6, 3.6))
    ax.bar(["Brochure", "Marketing"],
           [t5["brochure_anyuse"] * 100, t5["marketing_anyuse"] * 100],
           color=["#2b6cb0", "#a0aec0"])
    ax.set_ylabel("Any-use disclosure (%)")
    ax.set_title("Disclosure by venue (n=%d matched)" % t5["n_firms_both_venues"])
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(out / "figures" / f"fig4_venue.{ext}", dpi=150,
                    metadata={"Date": None} if ext == "svg" else None)
    plt.close(fig)


def write_summary(out, t1, t2res, t3res, t4, t4b, nval, t5, exp, miss):
    L = []
    L.append("# Reproduction summary: AI Use and Risk Disclosure by Investment Advisers\n")
    L.append("Regenerated from the frozen, pseudonymized dataset with no network or API access. "
             "Every value below is computed by `code/src/analyze.py`.\n")
    au = t1[t1.label.str.startswith("Any use")].iloc[0]
    # Recompute CI from the exact counts to avoid double-rounding at half-boundaries
    # (e.g. the any-use lower bound is 19.749…%, which the paper reports as 19.7).
    _p, _lo, _hi = wilson(int(au.k), int(au.n))
    L.append("## Headline results\n")
    L.append(f"- **Disclosed any-use (design):** {_p*100:.1f}% "
             f"(95% CI {_lo*100:.1f}-{_hi*100:.1f}); n={int(au.n)} classified brochures.")
    bf = t3res["brochure_filing_universe"]
    aa = t3res["all_aum_universe"]
    L.append(f"- **Survey-weighted any-use:** brochure-filing universe {bf['est']*100:.1f}% "
             f"(95% CI {bf['ci'][0]*100:.1f}-{bf['ci'][1]*100:.1f}); all-AUM universe {aa['est']*100:.1f}%.")
    riskrow = t1[t1.label.str.startswith("(c)")].iloc[0]
    L.append(f"- **Dominant mode is risk-framing:** {riskrow.prevalence*100:.1f}% disclose AI as a risk factor.")
    tr = t2res["trend"]
    lg = t2res["logit"]
    L.append(f"- **Size/type gradient:** trend z (private-fund) {tr['private_fund']['z']}, "
             f"(wealth) {tr['wealth_ria']['z']}, (overall) {tr['ALL']['z']}; "
             f"logit AUM-quartile coef {lg['aumq']['coef']} (SE {lg['aumq']['se']}), "
             f"private-fund coef {lg['pf']['coef']} (SE {lg['pf']['se']}), both p<0.001.")
    anyrow = t4[t4.label.str.startswith("Any use")].iloc[0]
    L.append(f"- **Independent cross-family validation (n={nval}, design-weighted to the population):** "
             f"any-use κ={anyrow.kappa}, precision {anyrow.precision}, recall {anyrow.recall}; risk-factor κ="
             f"{t4[t4.label.str.startswith('(c)')].iloc[0].kappa}, named-vendor recall "
             f"{t4[t4.label.str.startswith('(e)')].iloc[0].recall}. Metrics use two-phase verification weights "
             f"(model-positives censused; model-negatives up-weighted); precision is invariant to the weighting.")
    L.append(f"- **AI-washing exposure screen:** {exp['brochure_exposed_k']}/{exp['brochure_n']} "
             f"brochures ({exp['brochure_exposed_share']*100:.1f}%) match charged-conduct language.")
    L.append(f"- **Venue comparison (n={t5['n_firms_both_venues']} matched):** brochure any-use "
             f"{t5['brochure_anyuse']*100:.1f}% vs. marketing {t5['marketing_anyuse']*100:.1f}%; "
             f"exposure {t5['brochure_exposed']*100:.2f}% vs. {t5['marketing_exposed']*100:.2f}%.")
    L.append(f"- **Marketing-corpus selection:** usable text for {miss['n_usable']} firms; "
             f"no significant selection on type (p={miss['chi2_type_p']}) or "
             f"quartile (p={miss['chi2_quartile_p']}); AUM Mann-Whitney p={miss['aum_mannwhitney_p']}.\n")
    L.append("## Article map\n")
    L.append("| Output file | Manuscript element |")
    L.append("|---|---|")
    # Output filenames keep the original submission's numbering; the revised article
    # renumbered its tables and dropped two figures, so the mapping is stated explicitly.
    L.append("| tables/table1_typology.csv | Table 1 (typology prevalence, Wilson CIs) |")
    L.append("| tables/table2_gradient.csv | Table 2 (any-use by sampling stratum) and Figure 1 |")
    L.append("| tables/table2_inference.json | Section 4.2 ordered trend tests and logistic regression |")
    L.append("| tables/table3_weighting.csv, table3_weighting.json | Table 2 filing populations and stratum weights; Section 4.1 survey-weighted estimates |")
    L.append("| tables/table4_validation.csv | Table 3 (independent cross-family validation) |")
    L.append("| tables/table4b_samefamily.csv | Section 4.3 same-family reproducibility |")
    L.append("| tables/table5_venue.csv, table5_venue.json | Table 5 Panel B (cross-venue comparison) and Figure 2 |")
    L.append("| tables/table6_human_validation.json | Sections 3.5 and 4.3 targeted human verification |")
    L.append("| tables/table4_cases.csv | Table 4 (illustrative classification and human-verification cases) |")
    L.append("| tables/exposure_summary.json | Section 4.4 enforcement-anchored exposure screen |")
    L.append("| tables/missingness.json | Table 5 Panel C website coverage and selection |")
    L.append("| revision/ | Section 4.6 robustness, Table 5 Panel A, and the reviewer-requested analyses |")
    L.append("| figures/publication/figure1.png | Figure 1 as typeset in the article (300 dpi) |")
    L.append("| figures/publication/figure2.png | Figure 2 as typeset in the article (300 dpi) |")
    L.append("| figures/fig2_gradient.* | Figure 1 (disclosed any-use by adviser type and AUM quartile) |")
    L.append("| figures/fig4_venue.* | Figure 2 (disclosed any-use by venue) |")
    L.append("| figures/fig1_typology.*, figures/fig3_validation.* | Supporting figures; not printed in the revised article |")
    L.append("")
    L.append("Table 4's passages ship in data/case_examples.csv because they are printed "
             "verbatim in the article; its label codes are derived at run time from "
             "data/labels_primary.csv, data/labels_independent.csv and "
             "data/human_verification/, so the table is regenerated rather than restated.")
    (out / "metrics_summary.md").write_text("\n".join(L) + "\n")


def main():
    out = io_paths.out_dir()
    d = load()
    m = merged_labels(d)
    t1 = t1_typology(m, out)
    _, t2res = t2_gradient(m, out)
    _, t3res = t3_weighting(m, d, out)
    t4, t4b, nval, _ = t4_validation(d, out)
    t5 = t5_venue(d, out)
    exp, miss = exposure_and_missingness(m, d, out)
    figures(m, t1, t4, t5, out)
    write_summary(out, t1, t2res, t3res, t4, t4b, nval, t5, exp, miss)
    print(f"[analyze] wrote outputs to: {out}")
    print(f"[analyze] classified n={len(m)}; any-use={m.any_use.mean()*100:.1f}%; "
          f"weighted(brochure-filing)={t3res['brochure_filing_universe']['est']*100:.1f}%; "
          f"validation any-use kappa={t4[t4.label.str.startswith('Any use')].iloc[0].kappa}")
    print("[analyze] see metrics_summary.md for the verdict-first summary.")


if __name__ == "__main__":
    main()
