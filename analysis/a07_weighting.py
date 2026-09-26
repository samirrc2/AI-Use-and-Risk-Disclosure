"""
a07_weighting.py — population-weighted disclosure prevalence with design-based CI (reviewer #2).

Reproduces the s02 stratification on the FULL Form ADV Part 1 frame to obtain the population
count in each of the 8 strata (adviser type x AUM quartile), then combines those counts with the
sample stratum prevalences to produce a survey-weighted any-use estimate and a design-based
(stratified) 95% CI. Also prints per-stratum population counts, sampling weights, and denominators.

Runs on the Mac (reads the local 533 MB frame). Reuses the exact s02 column mapping.

Usage:  cd "Paper 10/analysis" && python a07_weighting.py
"""
import glob, math
import os
import pandas as pd, numpy as np

_MEMBER = ("adv-filing-data-20111105-20241231-part1/"
           "IA_ADV_Base_A_20111105_20241231.csv")
_ZIP = "../data/raw/frame/adv-filing-data-20111105-20241231-part1.zip"
_hits = glob.glob("../data/frame/**/IA_ADV_Base_A*.csv", recursive=True)


def _frame_source():
    """Extracted copy when present, otherwise the member inside the archive.

    data/frame/ is a byte-exact duplicate of that archive and the repository keeps
    only the archive; see data/frame_README.md.
    """
    if _hits:
        return _hits[0]
    import zipfile
    if not os.path.exists(_ZIP):
        raise SystemExit(f"no Form ADV frame found: neither ../data/frame/ nor {_ZIP}")
    return zipfile.ZipFile(_ZIP).open(_MEMBER)


FRAME = _frame_source()
CRD, AUM, PF, DATE = "1E1", "5F2c", "7B", "DateSubmitted"
MIN_YEAR = 2024

def load_frame():
    df = pd.read_csv(FRAME, encoding="latin-1", low_memory=False, dtype=str)
    df.columns = [c.strip().strip('"') for c in df.columns]
    df["_crd"] = pd.to_numeric(df[CRD], errors="coerce")
    df["_aum"] = pd.to_numeric(df[AUM].astype(str).str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce")
    df["_dt"] = pd.to_datetime(df.get(DATE), errors="coerce")
    df = df.dropna(subset=["_crd"]).sort_values("_dt").drop_duplicates("_crd", keep="last")
    if df["_dt"].notna().any():
        df = df[df["_dt"].dt.year >= MIN_YEAR]
    df = df.dropna(subset=["_aum"]); df = df[df["_aum"] >= 0]
    pf = df[PF].astype(str).str.strip().str.upper()
    df["type"] = np.where(pf == "Y", "private_fund", "wealth_ria")
    pos = df[df["_aum"] > 0].copy()
    pos["q"] = pd.qcut(pos["_aum"].rank(method="first"), 4, labels=["Q1", "Q2", "Q3", "Q4"])
    df = df.merge(pos[["_crd", "q"]], on="_crd", how="left")
    df["q"] = df["q"].astype("object").fillna("Q1")
    return df

def sample_prev():
    smp = pd.read_csv("../data/pilot_sample_400.csv"); smp["crd"] = smp.crd.astype(int)
    lab = pd.read_csv("../pilot/labels_primary.csv"); lab["crd"] = lab.crd.astype(int)
    d = smp.merge(lab, on="crd", how="left")
    d["cl"] = d["a"].notna()
    d["au"] = ((d[["a", "b", "e"]].sum(axis=1)) > 0).astype(float)
    out = {}
    for t in ["private_fund", "wealth_ria"]:
        for q in ["Q1", "Q2", "Q3", "Q4"]:
            c = d[(d.type == t) & (d.aum_quartile == q)]
            n = int(c.cl.sum()); k = int(c[c.cl].au.sum()); n_samp = len(c)
            out[(t, q)] = (k, n, n_samp)
    return out

def main():
    print("[a07] loading frame (large; ~1-2 min) ...", flush=True)
    fr = load_frame()
    Npop = len(fr)
    Nh = fr.groupby(["type", "q"]).size().to_dict()
    prev = sample_prev()
    print(f"[a07] population (active SEC RIAs reporting AUM): {Npop}")
    # brochure-filing population per stratum = N x (classified/sampled)  (aligns weighting universe
    # with the estimand: disclosure among brochure-filing advisers)
    Nbf = {k: Nh.get(k, 0) * (prev[k][1] / prev[k][2]) for k in prev}
    print("\nstratum            N_all   N_filing   n_cl   any-use")
    for t in ["private_fund", "wealth_ria"]:
        for q in ["Q1", "Q2", "Q3", "Q4"]:
            k, n, ns = prev[(t, q)]
            print(f"  {t:12s} {q}   {Nh.get((t,q),0):6d}   {Nbf[(t,q)]:7.0f}   {n:4d}   {k/n:6.3f}")

    def weighted(Nmap):
        Ntot = sum(Nmap.values()); pw = 0.0; var = 0.0
        for key in prev:
            k, n, ns = prev[key]; ph = k / n; W = Nmap[key] / Ntot
            pw += W * ph
            if n > 1:
                var += W * W * ph * (1 - ph) / n
        se = math.sqrt(var); return pw, pw - 1.96 * se, pw + 1.96 * se, Ntot

    pw_a, lo_a, hi_a, Nt_a = weighted(Nh)
    pw_b, lo_b, hi_b, Nt_b = weighted(Nbf)
    print(f"\n[a07] all AUM-reporting universe (N={Nt_a:.0f}): weighted any-use = {pw_a:.3f} "
          f"[{lo_a:.3f}, {hi_a:.3f}]")
    print(f"[a07] brochure-filing universe (N={Nt_b:.0f}, aligned to estimand): "
          f"weighted any-use = {pw_b:.3f} [{lo_b:.3f}, {hi_b:.3f}]  <-- report this")
    print(f"[a07] design (unweighted, among filers) = 0.237 [0.197, 0.282]; "
          f"wedge vs 0.63 = {0.63 - pw_b:.3f} weighted, {0.63 - 0.237:.3f} unweighted.")

if __name__ == "__main__":
    main()
