"""
a15_build_supplement.py — build Supplementary S3, the auditable classification examples.

Reviewers 1 and 3 both asked to see the language behind the classification decisions, not
only the category definitions. This assembles positives, hard negatives (AI vocabulary
present, label withheld) and model-disagreement cases into one table per label.

Passages are redacted in a11_revision.py before they reach this script: the filing firm's
name, its acronym and any personal names are removed.

Usage:  cd "Paper 10" && python analysis/a15_build_supplement.py
"""
import os
import re

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REV = os.path.join(ROOT, "analysis", "out", "revision")
# The revision removed all supplementary material from the paper, so this table is an
# analysis artifact rather than a shipped supplement. It belongs with its siblings under
# analysis/out/revision/, not in a frontiers/ folder the manuscript no longer references.
OUT = os.path.join(ROOT, "analysis", "out", "revision", "S3_coding_examples.md")
NAMES = {"a": "Investment-process AI", "b": "Operations / client-service AI", "c": "AI risk",
         "d": "Explicit non-use", "e": "Named vendor / product"}


def main():
    ex = pd.read_csv(os.path.join(REV, "r1_2_coding_examples.csv"))
    dpath = os.path.join(REV, "s4_disagreement_cases.csv")
    dis = pd.read_csv(dpath) if os.path.exists(dpath) else pd.DataFrame(columns=["category"])
    L = ["# Supplementary Material S3 — Auditable classification examples", "",
         "This table exists so the classification framework can be audited rather than taken on",
         "trust. For each label it shows passages that received the label, hard negatives where AI",
         "vocabulary is present but the label was withheld, and cases where the two model families",
         "disagreed. Passages are quoted from the current Form ADV Part 2A brochure with the filing",
         "firm's name, its acronym and any personal names redacted; the document key is the",
         "pseudonymous identifier used in the reproducibility package.", "",
         "The governing rule is in the frozen rubric: a label describes the **filing firm's own**",
         "practices. Generic market commentary, third-party managers the adviser merely allocates",
         "to, and plain automation the text does not frame as AI or predictive do not qualify.", "",
         "> **Status of the human-adjudication column.** Two independent coders are adjudicating",
         "> the disagreement set and a stratified sample of agreements. Until that is complete the",
         "> column reads *pending*; no adjudication outcome is asserted here.", ""]
    for c in "abcde":
        L += [f"## {NAMES[c]} (label {c})", "",
              "| Kind | Doc | GPT-4o | Claude | Human | Passage |", "|---|---|---|---|---|---|"]
        for pol, kind, cap in [("positive", "positive", 2), ("negative", "hard negative", 1)]:
            n = 0
            for _, r in ex[(ex.label == c) & (ex.polarity == pol)].iterrows():
                p = re.sub(r"\s+", " ", str(r.excerpt))[:300].replace("|", "/")
                L.append(f"| {kind} | {r.doc} | {c if pol=='positive' else '—'} | — | pending | {p}… |")
                n += 1
                if n >= cap:
                    break
        for _, r in dis[dis.category == c].iterrows() if len(dis) else []:
            p = re.sub(r"\s+", " ", str(r.passage))[:300].replace("|", "/")
            L.append(f"| model disagreement | {r.doc} | {r.gpt} | {r.claude} | pending | {p}… |")
        L.append("")
    L += ["## Why the disagreement cases matter", "",
          "The adjudicated disagreement set is the input to the error analysis in the main text.",
          "[PLACEHOLDER: once adjudication is complete, classify each disagreement by mechanism —",
          "conventional quantitative language read as AI, a vendor mention read as adviser use, the",
          "investment-process against operations boundary, or general technology risk read as",
          "AI-specific risk — and report counts, direction of error and the affected category.]", ""]
    open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
    rows = sum(1 for x in L if x.startswith("| ") and not x.startswith("|---"))
    print(f"[supplement] wrote S3_coding_examples.md — {rows} example rows across 5 labels")


if __name__ == "__main__":
    main()
