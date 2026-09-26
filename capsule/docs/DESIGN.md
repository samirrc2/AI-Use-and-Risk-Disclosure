# Study design (frozen instrument)

The design is measurement-first: build and validate a reproducible instrument for
AI claims in adviser filings, describe the level and distribution of disclosed AI
use, and compare disclosed use against surveyed adoption and against firms' own
marketing. Estimands and the classification rubric were fixed before analysis.

## Population and sample

- **Population:** active SEC-registered investment advisers reporting regulatory
  AUM in the SEC Form ADV Part 1 bulk data (N = 16,223 after de-duplicating to the
  latest 2024+ filing per adviser and requiring non-negative AUM).
- **Strata:** adviser type (private-fund vs. wealth/retail, from the Form ADV
  private-fund flag `7B`) × AUM quartile (quartiles by rank of regulatory AUM).
- **Sample:** stratified random sample of 400 firms (frozen as `data/sample.csv`).
  Brochures were retrieved and classified for 388; the 12 unclassified are all in
  wealth/retail strata (brochure-exempt or no usable text).

## Typology (frozen rubric: `data/prompts/typology_v1.md`)

Multi-label; a brochure may carry zero or several labels, each assigned only when a
verbatim phrase about the **filing firm's own** practices supports it:

- **a** — AI in the investment process
- **b** — AI in operations / client service
- **c** — AI as a disclosed risk factor
- **d** — explicit prohibition / non-use
- **e** — named AI vendor / product

Derived indicators: **any_use = a ∨ b ∨ e** (the headline estimand and the basis of
the survey-vs-disclosure wedge); **mention = a ∨ b ∨ c ∨ d ∨ e**.

## Estimands and inference

- **Prevalence:** per-label and any-use shares among classified brochures, with
  Wilson 95% intervals.
- **Gradient:** any-use by (type × quartile); a linear-by-linear trend test within
  type and overall; a firm-level logistic regression of any-use on AUM quartile
  (ordinal) and adviser type; the private-fund vs. wealth/retail contrast.
- **Survey weighting:** stratum prevalences reweighted to (i) the full AUM-reporting
  universe and (ii) the brochure-filing universe (`N_all × classified/sampled`), with
  design-based variance.
- **Reliability:** same-family inter-model reproducibility (gpt-4o vs. gpt-4o-mini,
  60 brochures) and independent cross-family validation (180 brochures re-coded by a
  different model family), reported as precision/recall/F1, Cohen's κ, and PABAK.
- **Human verification:** a targeted two-coder exercise on 158 cases (120 brochures —
  the 60 model-disagreement cases censused plus a stratified 60 of the agreement cases —
  and 38 website cases under their own single-phase design). Both coders were blind to the
  model labels and used the same frozen rubric; each case received one code. Metrics are
  Horvitz–Thompson weighted for the two-phase frame (agreement 2.0, phase-1 negative
  4.649, website negative 13.25) and reported separately for the two genres.
- **Exposure:** an F1–F7 fingerprint distilled from SEC AI-washing orders IA-6573 and
  IA-6574 (`data/prompts/exposure_fingerprints_v1.md`); positives are human-adjudicated
  (Supplement S1).
- **Venue:** for firms with both a brochure and usable marketing text, brochure vs.
  marketing any-use and exposure, with a selection analysis on the marketing corpus.

## Reproducibility contract

`code/src/analyze.py` is a pure function of the frozen files in `data/`. It uses no
randomness and no network; two runs produce byte-identical tables
(`replication_check.py`).
