"""Regenerate Table 4 of the article (illustrative classification cases).

The article's Table 4 pairs a quoted brochure passage with the labels each model family
assigned and the human coding. Only the passage text is carried as an input here, in
data/case_examples.csv, and only because those passages are already printed verbatim in the
published table; the brochure corpus itself stays withheld. Every label code is derived at
run time from the frozen label files, so this script reproduces the table rather than
restating it, and a change in the labels moves the table.

Two rows of the table were wrong before this existed, because label codes are not numbers
and the numeric audits never had them in scope: one row printed "ce / --" where both model
families had assigned bce, and another printed no labels at all for a passage whose document
carries them.

Outputs: results/tables/table4_cases.csv
"""
from __future__ import annotations
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import io_paths

LABELS = "abcde"


def rd(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def codes(row):
    """Label letters for one record, or '--' when the record carries none."""
    if row is None:
        return None
    return "".join(k for k in LABELS if str(row.get(k, "0")).strip() == "1") or "--"


def main():
    data = str(io_paths.data_root())
    out = io_paths.out_dir()

    cases = rd(os.path.join(data, "case_examples.csv"))
    primary = {r["fid"]: r for r in rd(os.path.join(data, "labels_primary.csv"))}
    indep = {r["fid"]: r for r in rd(os.path.join(data, "labels_independent.csv"))}
    hv = os.path.join(data, "human_verification")
    human = {r["row_id"]: r for r in rd(os.path.join(hv, "brochures.csv"))}
    fid2row = {r["fid"]: r["row_id"] for r in rd(os.path.join(hv, "frame.csv"))}

    rows = []
    for c in sorted(cases, key=lambda r: int(r["order"])):
        fid = c["fid"]
        if fid not in primary:
            sys.exit(f"ERROR: case '{c['case']}' names fid {fid}, absent from labels_primary.csv")
        row_id = fid2row.get(fid)
        rows.append({
            "order": c["order"],
            "case": c["case"],
            "fid": fid,
            # A dash means the model family assigned no label; n/a means the document was
            # never in the human-verification frame, which is not the same thing.
            "primary": codes(primary.get(fid)),
            "independent": codes(indep.get(fid)) if fid in indep else "--",
            "human": codes(human.get(row_id)) if row_id in human else "n/a",
            "passage": c["passage"],
            "note": c["note"],
        })

    dest = out / "tables" / "table4_cases.csv"
    with open(dest, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["order", "case", "fid", "primary",
                                           "independent", "human", "passage", "note"])
        w.writeheader()
        w.writerows(rows)
    print(f"[cases] regenerated {len(rows)} Table 4 rows from the frozen labels -> {dest}")
    for r in rows:
        print(f"[cases]   {r['case']:<23} {r['fid']}  "
              f"{r['primary']} / {r['independent']} / {r['human']}")


if __name__ == "__main__":
    main()
