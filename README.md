# Disclosed Intelligence

Computational artifact and manuscript for the *Frontiers in Artificial Intelligence* article:

**AI Use and Risk Disclosure by Investment Advisers**

### Paper summary

We measure how U.S. registered investment advisers disclose their use of artificial
intelligence in the fiduciary documents clients actually receive — Form ADV Part 2A
brochures. Over a stratified sample of advisers (388 brochures classified against a
frozen five-label typology), we quantify how much AI use is disclosed, in what framing,
how it varies with adviser type and size, and how brochure disclosure compares with the
same firms' public website marketing. Classifier reliability is established with an
independent, cross-model-family re-coding, weighted to the population via a two-phase
verification sample.

**Main findings:**

- **Disclosed any-use is 23.7%** (95% CI 19.7–28.2; n=388). Survey-weighted to the
  brochure-filing universe it is 22.7%.
- **The dominant framing is risk, not capability:** 27.6% of brochures disclose AI as a
  *risk factor*, while explicit claims of use in the investment process are rarer.
- **Disclosure rises strongly with adviser size and differs by type** (private-fund vs.
  wealth/retail): a monotone AUM gradient, significant in both a trend test and a logistic model.
- **The classifier is evaluated, not assumed:** design-weighted cross-family validation gives
  any-use κ=0.738 (precision 0.761, recall 0.837), and a targeted two-coder human verification
  of 158 cases gives composite precision 0.76 (95% CI 0.67–0.84), sensitivity 0.81, specificity 0.94.
- **AI-washing exposure is rare:** 5/388 brochures (1.3%) match charged-conduct language
  distilled from SEC enforcement orders IA-6573/IA-6574; none was adjudicated as an
  unsubstantiated promotional claim.
- **Raw prevalence differs by venue, but the design cannot attribute it to venue:** across 283
  firms observed in both, disclosed any-use is 23.0% in brochures vs. 5.7% on websites, yet the
  venue indicator is indistinguishable from zero once document length is included.
- **Prevalence is itself a measurement result:** the same corpus yields 9.9%, 13.1% and 23.7%
  as the construct, adviser universe and weighting change.

This repository is the frozen dataset, the deterministic analysis pipeline that regenerates
those results, and the Frontiers manuscript package.

---

## 1. Artifact identification

| Field | Value |
|-------|-------|
| **Article title** | AI Use and Risk Disclosure by Investment Advisers |
| **Authors** | Samir Chincholikar, Robin Chawla |
| **Affiliations** | Independent Researcher, New York, NY, United States; Independent Researcher, New York, NY, United States |
| **Code repository** | https://github.com/samirrc2/AI-Use-and-Risk-Disclosure |
| **Persistent DOI** | https://doi.org/10.24433/CO.3404788.v1 (`10.24433/CO.3404788.v1`) |
| **Contact** | Samir Chincholikar: samir.chincholikar@gmail.com; Robin Chawla: robin.chawla.cse14@iitbhu.ac.in |
| **ORCID** | Samir Chincholikar: 0009-0007-2779-3492; Robin Chawla: 0009-0007-2807-3948 |

The artifact enables independent reproduction of the article's computational results
from a frozen, pseudonymized dataset. That path requires **no API keys** and incurs
**no inference cost**. Re-collecting the raw SEC filings and running the LLM classifier
is optional and **not required** to verify any number in the article.

---

## 2. Repository layout

```
frontiers/         The paper: manuscript.tex + figures/ + references.bib, the compiled
                   manuscript.pdf, and submission/ (tracked changes, reviewer response
                   letters, figure copies). Rebuild with: bash frontiers/build_package.sh
capsule/           The Code Ocean reproducibility capsule (self-contained). code/ + frozen
                   data/ + docs/ + environment/ + results/. Run: cd capsule && bash code/run
analysis/          Design-based inference and the verification suite: weighting, trend/logit,
                   missingness, coding-sheet build, a14/a17/a18 checks.
build/             Live collection: Form ADV frame, sampling, brochure retrieval, classification.
marketing/         Venue comparison: resolve firm websites, crawl, classify, divergence.
human_validation/  The two-coder coding app, its briefing, and the coder exports.
data/ pilot/       Working sample, labels, prompts, and the pilot that gated the study.
recon/             Phase-0 data-availability reconnaissance.
docs/ metadata/    Reviewer reports (confidential, gitignored) and submission metadata.
verify.sh          Runs every check on the paper. requirements.txt = dependencies.
run_all.sh         Live end-to-end pipeline (needs keys).
DATA_AVAILABILITY.md · CITATION.cff · .zenodo.json · LICENSE · DECISIONS.md
```

## 3. Reproduce the published results (offline, no keys)

```
cd capsule
bash code/run              # analyze frozen data + byte-identical determinism check
```

Outputs land in `capsule/results/latest/`: `metrics_summary.md` (verdict first),
`tables/*.csv`, `figures/*.{png,svg}`, `figures/publication/` (Figures 1 and 2 exactly as
typeset), and `revision/` (robustness and the reviewer-requested analyses). The run must
end with `PASS — all table artifacts byte-identical across runs.`

The capsule pins its dependencies (`capsule/code/requirements.txt`); running it against
other numpy/pandas versions invalidates the byte-identity check.

## 3a. Verify the whole paper

```
CAPSULE_PYTHON=/path/to/pinned/python bash verify.sh
```

One command, every check: the capsule reproduces from scratch, the manuscript's internal
consistency and float placement, every printed number bound to the specific artifact cell it
comes from (with a coverage line naming anything unaccounted for), Table 4's label codes,
the published figures' provenance, and the reviewer letters' references and structure. It
refuses to run if the interpreter does not match the capsule's pins, because a reproduction
claim made in the wrong environment means nothing. Exit 0 means all of them passed.
See `capsule/AUDIT.md` for the last full verification run.

## 4. Re-collect from source (optional, needs API keys)

```
./run_all.sh               # build -> analysis -> marketing; keys from ../API Keys/keys.env.txt
```

## The manuscript

`frontiers/manuscript.pdf` (source: `frontiers/manuscript.tex`). The submission package —
tracked-changes PDF, the two reviewer response letters, and the figure copies named as the
journal expects — is built by `bash frontiers/build_package.sh` and lands in
`frontiers/submission/`.
