"""
a12_two_coder_setup.py — score the human validation exercise.

The frame is the complete model-disagreement census plus a stratified sample of
agreement brochures and a set of website cases. It is split between two coders, so
every row is coded exactly once; the merged coding is the human reference standard
against which the classifier is scored.

  build   the coding package is built by a16_build_coding_app.py; this command only
          forwards to it, so the pipeline has one entry point per stage
  score   merge human_validation/human_validation_{1,2}.csv into the reference
          standard and report classifier performance against it

Metrics are Horvitz--Thompson weighted \\citep{horvitz1952,breslow1988} through both
phases of the design: phase one is the 180-brochure verification subsample drawn from
the 388 classified brochures (any-mention positives censused, negatives sampled), and
phase two is this coding frame drawn from that subsample (disagreements censused,
agreements sampled). Website rows carry their own weights and are reported separately,
because the classifier was never separately validated on website language.

Usage:  cd "Paper 10" && python analysis/a12_two_coder_setup.py score
"""
import json
import os
import subprocess
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HV = os.path.join(ROOT, "analysis", "out", "revision", "human_validation")
APP = os.path.join(ROOT, "human_validation")
LABELS = list("abcde")
NAMES = {"a": "AI in investment process", "b": "AI in operations/client service",
         "c": "AI as disclosed risk factor", "d": "Explicit prohibition/non-use",
         "e": "Vendor/product named"}
COMPOSITES = [("any_use_ve", ["a", "b"], "any use (a|b)"),
              ("any_use_nv", ["a", "b", "e"], "any use (a|b|e)")]


def build():
    print("  the coding package is built by a16_build_coding_app.py; forwarding")
    sys.exit(subprocess.call([sys.executable,
                              os.path.join(ROOT, "analysis", "a16_build_coding_app.py")]))


def load_key():
    """Model labels and stratum for every row in the frame, brochure and website."""
    key = pd.read_csv(os.path.join(HV, "adjudication_KEY_do_not_give_to_coders.csv"))
    wk = os.path.join(HV, "website_KEY_do_not_give_to_coders.csv")
    if os.path.exists(wk):
        key = pd.concat([key, pd.read_csv(wk)], ignore_index=True)
    return key.set_index("row_id")


def load_coding():
    """The two exported CSVs, merged into one reference standard.

    Each row belongs to exactly one coder, so the merge is a concatenation. The
    assignment record is the authority on who owed which rows: a row missing from its
    owner's export is a hole in the frame and must stop the scoring, because the
    estimator assumes every drawn row was coded.
    """
    ap = os.path.join(APP, "assignment.json")
    if not os.path.exists(ap):
        sys.exit(f"missing {ap} — run analysis/a16_build_coding_app.py first")
    split = json.load(open(ap))["split"]
    frames, missing = [], []
    for coder, owed in split.items():
        p = os.path.join(APP, f"human_validation_{coder}.csv")
        if not os.path.exists(p):
            sys.exit(f"missing {os.path.basename(p)} — coder {coder} has not exported yet")
        s = pd.read_csv(p, dtype={"row_id": str})
        if "row_id" not in s.columns:
            sys.exit(f"{os.path.basename(p)} has no row_id column")
        s = s.drop_duplicates("row_id", keep="last")
        have = set(s.row_id)
        missing += [(coder, r) for r in owed if r not in have]
        extra = have - set(owed)
        if extra:
            print(f"  coder {coder}: ignoring {len(extra)} rows not assigned to them")
            s = s[s.row_id.isin(owed)]
        blank = s[s[LABELS].isna().any(axis=1)]
        if len(blank):
            sys.exit(f"coder {coder}: {len(blank)} of {len(owed)} rows not coded "
                     f"({', '.join(blank.row_id.head(5))}…) — finish before scoring")
        s["coder"] = coder
        frames.append(s)
    if missing:
        byc = {}
        for c, r in missing:
            byc.setdefault(c, []).append(r)
        for c, rs in byc.items():
            print(f"  coder {c}: {len(rs)} assigned rows absent from the export "
                  f"({', '.join(rs[:5])}…)")
        sys.exit("the frame is incomplete; every assigned row must be coded")
    h = pd.concat(frames, ignore_index=True).set_index("row_id")
    for L in LABELS:
        h[L] = h[L].astype(int)
    return h


def weights(key, ids):
    """Chained two-phase Horvitz--Thompson weights, one per coded row.

    Phase one, into the 180-brochure verification subsample: primary any-mention
    positives were censused and primary negatives sampled, so a coded negative stands
    for several. Phase two, into this coding frame: disagreement brochures were
    censused and agreement brochures sampled. Website rows enter through their own
    single-phase design (positives censused, negatives sampled) and are scored on their
    own, so they take only that weight.
    """
    d = json.load(open(os.path.join(HV, "design.json")))
    n_ag_pop = d["subsample"] - d["brochures_with_disagreement"]
    n_ag_smp = sum(1 for i in ids if key.loc[i, "stratum"] == "agreement")
    w_ag = n_ag_pop / n_ag_smp if n_ag_smp else 1.0

    wp = os.path.join(HV, "website_design.json")
    if os.path.exists(wp):
        wd = json.load(open(wp))
        w_wneg = (wd["negatives_population"] / wd["negatives_sampled"]
                  if wd.get("negatives_sampled") else 1.0)
    else:
        w_wneg = 1.0

    # phase one is read off the primary labels the key already carries: a brochure was
    # censused into the subsample iff the primary model called it any-mention positive.
    ver = json.load(open(os.path.join(ROOT, "analysis", "out", "revision",
                                      "r1_2_independent_reestimate.json")))
    w_neg1 = ver["negative_weight"]

    W, parts = {}, {}
    for i in ids:
        st = key.loc[i, "stratum"]
        if st == "website":
            pos = any(int(key.loc[i, f"primary_{L}"]) for L in LABELS)
            W[i] = 1.0 if pos else w_wneg
        else:
            anym = any(int(key.loc[i, f"primary_{L}"]) for L in LABELS)
            w1 = 1.0 if anym else w_neg1
            w2 = 1.0 if st == "disagreement" else w_ag
            W[i] = w1 * w2
    parts = {"agreement_phase2": round(w_ag, 3), "negative_phase1": round(w_neg1, 3),
             "website_negative": round(w_wneg, 3)}
    return W, parts


def metrics(model, human, W, ids):
    tp = sum(W[i] for i in ids if model[i] and human[i])
    fp = sum(W[i] for i in ids if model[i] and not human[i])
    fn = sum(W[i] for i in ids if not model[i] and human[i])
    tn = sum(W[i] for i in ids if not model[i] and not human[i])
    n = tp + fp + fn + tn
    sens = tp / (tp + fn) if tp + fn else float("nan")
    spec = tn / (tn + fp) if tn + fp else float("nan")
    prec = tp / (tp + fp) if tp + fp else float("nan")
    f1 = 2 * prec * sens / (prec + sens) if prec + sens else float("nan")
    return {"tp": round(tp, 1), "fp": round(fp, 1), "fn": round(fn, 1), "tn": round(tn, 1),
            "sensitivity": round(sens, 3), "specificity": round(spec, 3),
            "precision": round(prec, 3), "f1": round(f1, 3),
            "accuracy": round((tp + tn) / n, 3) if n else float("nan"),
            "n_rows": len(ids)}


def panel(title, key, human, W, ids, out, tag):
    if not ids:
        return
    print(f"\n=== {title} (n={len(ids)}) ===")
    print(f"  {'label':34s} {'sens':>6s} {'spec':>6s} {'prec':>6s} {'F1':>6s} {'acc':>6s}")
    res = {}
    for L in LABELS:
        mv = {i: int(key.loc[i, f"primary_{L}"]) for i in ids}
        hv = {i: int(human.loc[i, L]) for i in ids}
        r = metrics(mv, hv, W, ids)
        res[f"({L}) {NAMES[L]}"] = r
        print(f"  ({L}) {NAMES[L]:30s} {r['sensitivity']:6.3f} {r['specificity']:6.3f} "
              f"{r['precision']:6.3f} {r['f1']:6.3f} {r['accuracy']:6.3f}")
    for _, cols, nm in COMPOSITES:
        mv = {i: int(any(int(key.loc[i, f"primary_{c}"]) for c in cols)) for i in ids}
        hv = {i: int(any(int(human.loc[i, c]) for c in cols)) for i in ids}
        r = metrics(mv, hv, W, ids)
        res[nm] = r
        print(f"  {nm:34s} {r['sensitivity']:6.3f} {r['specificity']:6.3f} "
              f"{r['precision']:6.3f} {r['f1']:6.3f} {r['accuracy']:6.3f}")
    out[tag] = res


def score():
    key = load_key()
    human = load_coding()
    ids = [i for i in human.index if i in key.index]
    lost = [i for i in human.index if i not in key.index]
    if lost:
        sys.exit(f"{len(lost)} coded rows are not in the key ({', '.join(lost[:5])}…)")
    W, parts = weights(key, ids)
    broch = [i for i in ids if key.loc[i, "stratum"] != "website"]
    web = [i for i in ids if key.loc[i, "stratum"] == "website"]
    ncod = human.coder.value_counts().to_dict()

    print(f"\n  reference standard: {len(ids)} rows coded once each "
          f"({', '.join(f'coder {c}: {n}' for c, n in sorted(ncod.items()))})")
    print(f"  {len(broch)} brochure rows, {len(web)} website rows")
    print(f"  Horvitz--Thompson weights: agreement brochures x{parts['agreement_phase2']}, "
          f"primary-negative brochures x{parts['negative_phase1']}, "
          f"sampled website negatives x{parts['website_negative']}")

    out = {"n_rows": len(ids), "n_brochure": len(broch), "n_website": len(web),
           "rows_per_coder": ncod, "weights": parts}
    panel("Classifier against the human reference standard, brochures",
          key, human, W, broch, out, "brochure")
    panel("Classifier against the human reference standard, websites",
          key, human, W, web, out, "website")

    print(f"\n=== Human-referenced prevalence within the coding frame ===")
    for _, cols, nm in COMPOSITES:
        num = sum(W[i] for i in broch if any(int(human.loc[i, c]) for c in cols))
        den = sum(W[i] for i in broch)
        print(f"  {nm:18s} {100 * num / den:.1f}%  [the frame is enriched with "
              f"model-positives; this is not a population prevalence]")
        out.setdefault("human_prevalence_in_frame", {})[nm] = round(num / den, 4)

    p = os.path.join(HV, "validation_results.json")
    json.dump(out, open(p, "w"), indent=1)
    print(f"\n  wrote {p}")

    # The Data Availability Statement names these three files by path, so they must exist in
    # the capsule or the reproducibility claim outruns the contents. Written here, from the
    # merged reference standard, the moment coding is complete.
    cap = os.path.join(ROOT, "capsule", "data", "human_verification")
    os.makedirs(cap, exist_ok=True)
    web_ids = [i for i in ids if key.loc[i, "stratum"] == "website"]
    web = human.index.isin(web_ids)
    cols = LABELS + ["coder"]
    human.loc[~web, cols].to_csv(os.path.join(cap, "brochures.csv"))
    human.loc[web, cols].to_csv(os.path.join(cap, "websites.csv"))
    json.dump({"frame": "model-disagreement census + stratified agreement sample + website cases",
               "n_brochure": len(broch), "n_website": len(web_ids),
               "strata": {st: sum(1 for i in ids if key.loc[i, "stratum"] == st)
                          for st in ("disagreement", "agreement", "website")},
               "weights": parts, "coded_once_per_row": True, "rows_per_coder": ncod},
              open(os.path.join(cap, "design.json"), "w"), indent=1)
    print(f"  wrote capsule/data/human_verification/ (brochures.csv {len(broch)} rows, "
          f"websites.csv {len(web_ids)} rows, design.json)")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "score"
    {"build": build, "score": score}.get(cmd, score)()
