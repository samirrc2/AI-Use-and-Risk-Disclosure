"""Human-verification metrics for the capsule.

Recomputes the classifier's performance against the two-coder human reference standard,
entirely from files inside capsule/data/. Nothing here reads the brochure corpus or any
identifiable record: the frame is keyed by the pseudonymous fid and the human labels were
exported by the coders against the same frame.

The estimator is Horvitz--Thompson weighted because the verification frame is a two-phase
sample. Phase one censused the any-mention positives and sampled the negatives at 57/265,
so a negative carries 265/57 = 4.649. Phase two censused the model-disagreement cases and
took half the agreements, so an agreement case carries 2.0. Website cases are drawn under
their own single-phase design and are reported separately, never pooled with the brochures.

Usage:  python validate_human.py [--out DIR]
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import io_paths          # the capsule's own path resolution, so this step writes where
                         # analyze.py writes under every launch mode (local, Code Ocean)

DATA = str(io_paths.data_root())
LABELS = "abcde"
NAMES = {"a": "(a) AI in investment process", "b": "(b) AI in operations/client service",
         "c": "(c) AI as disclosed risk factor", "d": "(d) Explicit prohibition/non-use",
         "e": "(e) Vendor/product named"}


def _rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load():
    hv = os.path.join(DATA, "human_verification")
    frame = {r["row_id"]: r for r in _rows(os.path.join(hv, "frame.csv"))}
    human = {}
    for f in ("brochures.csv", "websites.csv"):
        p = os.path.join(hv, f)
        if os.path.exists(p):
            for r in _rows(p):
                human[r["row_id"]] = {c: int(r[c]) for c in LABELS}
    # Brochure rows are scored against the brochure classifier, website rows against the
    # website classifier. They are different instruments on different corpora and must never
    # be pooled or crossed.
    model = {r["fid"]: {c: int(r[c]) for c in LABELS}
             for r in _rows(os.path.join(DATA, "labels_primary.csv"))}
    site = {r["fid"]: {c: int(r[c]) for c in LABELS}
            for r in _rows(os.path.join(DATA, "venue", "marketing_labels.csv"))}
    design = json.load(open(os.path.join(hv, "design.json"), encoding="utf-8"))
    return frame, human, model, site, design


def weight(row, model, w):
    """Inverse inclusion probability for one verification row."""
    if row["kind"] == "website":
        # single-phase: positives censused, negatives sampled 20 of 265
        m = model.get(row["fid"], {})
        return 1.0 if any(m.get(c) for c in LABELS) else w["website_negative"]
    x = w["agreement_phase2"] if row["stratum"] == "agreement" else 1.0
    m = model.get(row["fid"], {})
    if not any(m.get(c) for c in LABELS):          # phase-one sampled negative
        x *= w["negative_phase1"]
    return x


def confusion(ids, frame, human, model, w, cols):
    tp = fp = fn = tn = 0.0
    for rid in ids:
        x = weight(frame[rid], model, w)
        h = any(human[rid][c] for c in cols)
        m = any(model.get(frame[rid]["fid"], {}).get(c) for c in cols)
        if h and m:
            tp += x
        elif m and not h:
            fp += x
        elif h and not m:
            fn += x
        else:
            tn += x
    return tp, fp, fn, tn


def metrics(tp, fp, fn, tn):
    d = lambda a, b: (a / b) if b else None
    return {"tp": round(tp, 4), "fp": round(fp, 4), "fn": round(fn, 4), "tn": round(tn, 4),
            "sensitivity": d(tp, tp + fn), "specificity": d(tn, tn + fp),
            "precision": d(tp, tp + fp)}


def _wilson(k, n, z=1.959963984540054):
    if n == 0:
        return 0.0, 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return p, (c - h) / d, (c + h) / d


def _disagreements(ids, frame, human, model):
    """Detection vs boundary disagreement on the brochure cases (Section 4.3).

    A detection disagreement is disagreement over whether the retrieved passage qualifies
    under any rubric label at all; a boundary disagreement is when both sides see a
    qualifying disclosure but assign different functional labels. These are descriptive
    tallies over the reviewed cases, not the weighted confusion matrix.
    """
    det = bnd = model_only = human_only = 0
    cat = {"investment_process_only": 0, "operations_only": 0, "both": 0, "other_labels": 0}
    per = {c: {"model_only": 0, "human_only": 0} for c in LABELS}
    for rid in ids:
        fid = frame[rid]["fid"]
        mrow = model.get(fid)
        if mrow is None:
            continue
        m = {c: str(mrow[c]).strip() == "1" for c in LABELS}
        h = {c: str(human[rid][c]).strip() == "1" for c in LABELS}
        if any(m.values()) != any(h.values()):
            det += 1
            if any(m.values()):
                model_only += 1
            else:
                human_only += 1
        elif any(m.values()) and m != h:
            bnd += 1
            da, db = m["a"] != h["a"], m["b"] != h["b"]
            cat["both" if (da and db) else "investment_process_only" if da
                else "operations_only" if db else "other_labels"] += 1
        for c in LABELS:
            if m[c] and not h[c]:
                per[c]["model_only"] += 1
            if h[c] and not m[c]:
                per[c]["human_only"] += 1
    return {"n_reviewed": len(ids), "detection": det, "detection_model_only": model_only,
            "detection_human_only": human_only, "boundary": bnd,
            "boundary_by_label": cat, "per_label": per}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out_root = a.out or str(io_paths.out_dir())
    frame, human, model, site, design = load()
    w = design["weights"]
    coded = [r for r in frame if r in human]
    broch = [r for r in coded if frame[r]["kind"] == "brochure"]
    web = [r for r in coded if frame[r]["kind"] == "website"]
    if len(broch) != design["n_brochure"] or len(web) != design["n_website"]:
        sys.exit(f"frame mismatch: {len(broch)} brochure / {len(web)} website coded, "
                 f"design declares {design['n_brochure']} / {design['n_website']}")

    out = {"n_brochure": len(broch), "n_website": len(web), "weights": w, "brochure": {}, "website": {}}
    for tag, ids, lab in (("brochure", broch, model), ("website", web, site)):
        for c in LABELS:
            out[tag][NAMES[c]] = metrics(*confusion(ids, frame, human, lab, w, [c]))
        out[tag]["any use (a|b)"] = metrics(*confusion(ids, frame, human, lab, w, ["a", "b"]))
        out[tag]["any use (a|b|e)"] = metrics(*confusion(ids, frame, human, lab, w, ["a", "b", "e"]))

    # Section 4.3 reports a Wilson interval on composite precision, and separates detection
    # disagreements from boundary disagreements with their direction and affected labels.
    # None of that was emitted, so those sentences had no artifact behind them.
    out["precision_ci"] = {}
    for tag in ("brochure", "website"):
        for name, m in out[tag].items():
            tp, fp = m["tp"], m["fp"]
            if abs(tp - round(tp)) > 1e-6 or abs(fp - round(fp)) > 1e-6:
                continue          # positives are censused, so these are whole counts
            _p, lo, hi = _wilson(int(round(tp)), int(round(tp + fp)))
            out["precision_ci"][f"{tag}/{name}"] = [round(lo, 4), round(hi, 4)]
    out["disagreements"] = _disagreements(broch, frame, human, model)

    os.makedirs(os.path.join(out_root, "tables"), exist_ok=True)
    p = os.path.join(out_root, "tables", "table6_human_validation.json")
    json.dump(out, open(p, "w", encoding="utf-8"), indent=1, sort_keys=True)

    c = out["brochure"]["any use (a|b|e)"]
    print(f"[human-validation] brochures n={len(broch)}  composite any-use: "
          f"sensitivity {c['sensitivity']:.3f}  specificity {c['specificity']:.3f}  "
          f"precision {c['precision']:.3f}")
    v = out["brochure"]["any use (a|b)"]
    print(f"[human-validation] vendor-excluded: {v['sensitivity']:.3f} / "
          f"{v['specificity']:.3f} / {v['precision']:.3f}")
    ws = out["website"]["any use (a|b|e)"]
    print(f"[human-validation] websites  n={len(web)}   any-use: "
          f"sensitivity {ws['sensitivity']:.3f}  precision {ws['precision']:.3f}")
    print(f"[human-validation] wrote {p}")


if __name__ == "__main__":
    main()
