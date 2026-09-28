# Data (`/data` mount)

Companion data package for the Frontiers in Artificial Intelligence manuscript
*AI Use and Risk Disclosure by Investment Advisers*. See the repository root `README.md` for the
full Data Availability statement. Executable Code Ocean capsule:
https://doi.org/10.24433/CO.3404788.v2.

All files are **frozen intermediate artifacts**. The expensive, networked upstream
steps — downloading SEC Form ADV bulk data, retrieving each brochure from IAPD, and
classifying brochures with a large language model — are **not** re-run here. Their
outputs are frozen so the statistical results reproduce deterministically and for free.

## Privacy / pseudonymization

Per the article's Data Availability statement, firm-level classifications are **not**
released against identifiable firms. Every record here is keyed by a pseudonymous
`fid` (`F0001`…`F0400`); firm names and CRD numbers are withheld. The analysis is
invariant to firm identity, so all published statistics reproduce exactly. The CRD
crosswalk is retained privately by the authors and available on request under the
terms described in the article; it is required only to re-fetch raw brochures, not to
reproduce any result.

## Files

| File | Rows | Contents |
|---|---|---|
| `sample.csv` | 400 | Frozen stratified random sample: `fid, type, aum_quartile, regulatory_aum`. |
| `labels_primary.csv` | 388 | Primary classifier (OpenAI gpt-4o) typology labels `a,b,c,d,e` per classified brochure. |
| `labels_secondary_sub.csv` | 60 | Same-family second rater (gpt-4o-mini) on a random 60-brochure subsample (reproducibility check). |
| `labels_independent.csv` | 180 | Independent, blinded re-coding by a different model family (validation reference). |
| `population_strata.csv` | 8 | Population count `N_all` per (type × AUM quartile) stratum, derived once from the SEC Form ADV Part 1 frame (see below). |
| `venue/venue_divergence.csv` | 283 | Firms with both a classified brochure and usable marketing text: per-venue any-use and exposure flags. |
| `venue/brochure_exposure.csv` | 388 | AI-washing exposure screen (F1–F7) applied to brochures. |
| `venue/marketing_exposure.csv` | 283 | Exposure screen applied to marketing text. |
| `venue/marketing_labels.csv` | 283 | Typology labels applied to marketing text. |
| `venue/marketing_crawl_log.csv` | 400 | Marketing-text retrieval status and character counts (for the selection analysis). |
| `venue/divergence_summary.json` | — | Precomputed venue summary (reference; recomputed by the code). |
| `doc_lengths.csv` | 388 | Character count per classified brochure, for the venue length-conditioning analysis (Section 4.5). |
| `aum_history.csv` | 400 | Regulatory AUM at 2020, 2022 and 2024 year-end, for the lagged-stratum falsification test (Section 4.6). |
| `keyword_constructs.csv` | 400 | Literal-phrase and rubric-scope keyword flags plus character count, for the construct-sensitivity ladder (Section 4.1). |
| `case_examples.csv` | 8 | The passages quoted in Table 4, keyed by `fid`. Only the passage text is carried; every label code in that table is derived at run time from the label files below, so the table is regenerated rather than restated. The passages are already printed verbatim in the article. |
| `human_verification/frame.csv` | 158 | The targeted human-verification frame: `row_id, fid, stratum, kind`. 120 brochure cases (60 model-disagreement, 60 stratified agreement) plus 38 website cases. |
| `human_verification/brochures.csv` | 120 | Human codes for the brochure cases, one code per row, both coders blind to the model labels. |
| `human_verification/websites.csv` | 38 | Human codes for the website cases, drawn under their own single-phase design. |
| `human_verification/design.json` | — | The verification design: stratum sizes and the two-phase weights (agreement 2.0, phase-1 negative 4.649, website negative 13.25). The scoring step refuses to run if the coded rows do not match this design. |
| `prompts/typology_v1.md` | — | Frozen five-label classification rubric (the measurement instrument). |
| `prompts/exposure_fingerprints_v1.md` | — | Frozen F1–F7 exposure-language fingerprint, distilled from SEC orders IA-6573/IA-6574. |

## Provenance of `population_strata.csv`

The eight stratum population counts are the only artifact derived from the full
4.4 GB SEC Form ADV bulk dataset, which is public but too large (and firm-identifiable)
to redistribute here. They were computed once from `IA_ADV_Base_A` by replicating the
sampling frame exactly: parse CRD (`1E1`), regulatory AUM (`5F2c`), private-fund flag
(`7B`), and `DateSubmitted`; keep the latest filing per CRD; restrict to 2024+ filings
reporting non-negative AUM (N = 16,223 advisers); assign AUM quartiles by rank; and
count firms per (type × quartile). The bulk source is the SEC's public *Investment
Adviser Report – ADV bulk data* download.

## Reproduce

```bash
bash reproduce.sh              # analyze + byte-identical replication check
bash reproduce.sh --analyze-only
bash reproduce.sh --test
```

Outputs land in `results/latest/` (local) or `/results` (Code Ocean).
