"""
a10_build_coding_sheet.py — build a blinded HUMAN gold-standard coding sheet.

Produces a 180-brochure validation set (all model-positive brochures + a random negative sample)
with the AI-relevant excerpt and blank a-e columns, for two independent human coders. A hidden key
maps rows back to firms and model labels for scoring (precision / recall / F1 / confusion matrix /
PABAK per label) after coding and adjudication. Coders see only a doc_id and the excerpt.

Outputs (analysis/out/):
    coder_sheet_A.csv, coder_sheet_B.csv   (blinded; blank a,b,c,d,e,notes)
    a10_key.csv                            (row_id -> crd, firm, model labels; NOT for coders)
    a10_instructions.txt                   (the rubric, for coders)

Usage:  cd "Paper 10/analysis" && python a10_build_coding_sheet.py
"""
import re, csv, random, shutil
from pathlib import Path
import pandas as pd

OUT = Path("out"); OUT.mkdir(exist_ok=True)
BROCHURE = Path("../data/brochure_text/current")
RUBRIC = Path("../pilot/prompts/typology_v1.md")
N_NEG = 57            # random negatives to add to all positives
SEED = 42

KW = re.compile(r"artificial intelligence|\bAI\b|machine learning|deep learning|neural|generative|"
                r"large language|LLM|natural language|algorithm|quantitative model|model-driven|"
                r"predictive|automated|robo|data science", re.I)

def excerpt(text, radius=320, cap=12, maxlen=2600):
    hits = [m.start() for m in KW.finditer(text)]
    if not hits:
        return text[:1200].strip()
    spans = sorted((max(0, h - radius), min(len(text), h + radius)) for h in hits)
    merged = [spans[0]]
    for s, e in spans[1:]:
        if s <= merged[-1][1]: merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else: merged.append((s, e))
    return (" … ".join(text[s:e] for s, e in merged[:cap]))[:maxlen].strip()

def main():
    smp = pd.read_csv("../data/pilot_sample_400.csv"); smp["crd"] = smp.crd.astype(int)
    lab = pd.read_csv("../pilot/labels_primary.csv"); lab["crd"] = lab.crd.astype(int)
    d = smp.merge(lab, on="crd", how="inner")
    d["mention"] = (d[["a", "b", "c", "d", "e"]].sum(axis=1) > 0)
    pos = d[d.mention]; neg = d[~d.mention]
    rng = random.Random(SEED)
    neg_idx = rng.sample(list(neg.index), min(N_NEG, len(neg)))
    chosen = pd.concat([pos, neg.loc[neg_idx]])
    rows = []
    for _, r in chosen.iterrows():
        p = BROCHURE / f"{int(r.crd)}.txt"
        if not p.exists(): continue
        rows.append({"crd": int(r.crd), "firm": r.firm,
                     "excerpt": excerpt(p.read_text(encoding="utf-8", errors="replace")),
                     "m_a": int(r.a), "m_b": int(r.b), "m_c": int(r.c), "m_d": int(r.d), "m_e": int(r.e)})
    rng.shuffle(rows)
    for i, row in enumerate(rows): row["row_id"] = f"D{i+1:03d}"

    # blinded coder sheet
    with open(OUT / "coder_sheet_A.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["row_id", "excerpt", "a", "b", "c", "d", "e", "notes"])
        for r in rows: w.writerow([r["row_id"], r["excerpt"], "", "", "", "", "", ""])
    shutil.copy(OUT / "coder_sheet_A.csv", OUT / "coder_sheet_B.csv")
    # hidden key
    with open(OUT / "a10_key.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["row_id", "crd", "firm", "m_a", "m_b", "m_c", "m_d", "m_e"])
        for r in rows: w.writerow([r["row_id"], r["crd"], r["firm"], r["m_a"], r["m_b"], r["m_c"], r["m_d"], r["m_e"]])

    (OUT / "a10_instructions.txt").write_text(
        "HUMAN CODING INSTRUCTIONS — Paper 10 typology validation\n\n"
        "Code each row from the EXCERPT only, using the rubric below. Enter 1 or 0 in columns "
        "a,b,c,d,e. A label is 1 only if a verbatim phrase in the excerpt supports it. If the "
        "excerpt shows no AI/technology content, all five are 0. Do not consult the firm name or "
        "outside sources. Two coders complete sheets A and B independently; disagreements are then "
        "adjudicated by discussion. After coding, score against the model with the hidden key.\n\n"
        + RUBRIC.read_text())

    print(f"[a10] wrote coder_sheet_A/B.csv ({len(rows)} rows: {int(chosen.mention.sum())} model-positive, "
          f"{len(rows)-int(chosen.mention.sum())} negative), a10_key.csv, a10_instructions.txt")
    print("[a10] Give coders the sheet + instructions ONLY. Keep a10_key.csv hidden until scoring.")

if __name__ == "__main__":
    main()
