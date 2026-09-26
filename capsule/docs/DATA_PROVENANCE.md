# Data provenance — how each frozen artifact was produced

The upstream collection is **not** part of the Reproducible Run (it needs network,
API keys, and cost, and the raw brochure text is firm-identifiable). This document
records exactly how the frozen files in `data/` were produced, so the pipeline is
auditable end to end.

## 1. Sampling frame → `data/sample.csv`, `data/population_strata.csv`

Source: the SEC's public *Investment Adviser Report — ADV bulk data* download
(Form ADV Part 1), file `IA_ADV_Base_A`. Fields used: CRD (`1E1`), regulatory AUM
(`5F2c`), private-fund flag (`7B`), `DateSubmitted`. Processing: keep the latest
filing per CRD; restrict to 2024+ filings with non-negative AUM (N = 16,223);
assign AUM quartiles by rank; stratify by (type × quartile) and draw 400 firms at
a fixed seed. `population_strata.csv` is the per-stratum population count `N_all`
computed from the same frame. (Collection scripts: `s01_frame.py`, `s02_sample.py`.)

## 2. Brochure retrieval (not shipped; text is firm-identifiable)

Each sampled firm's current Form ADV Part 2A brochure was retrieved from IAPD
(`api.adviserinfo.sec.gov` → brochure viewer on `files.adviserinfo.sec.gov`),
converted to text, and cached. Raw brochures and extracted text are **not**
redistributed. (Collection script: `s03_current_brochures.py`.)

## 3. Primary classification → `data/labels_primary.csv`

Each brochure's AI-relevant passages were extracted by keyword windowing and
submitted with the frozen rubric (`data/prompts/typology_v1.md`) to the primary
classifier (OpenAI **gpt-4o**, temperature 0) returning structured `a–e` labels
with a verbatim quote required for every positive. (Collection script:
`s05_classify.py`.)

## 4. Reliability sets → `labels_secondary_sub.csv`, `labels_independent.csv`

- **Same-family reproducibility:** a random 60-brochure subsample re-classified by
  **gpt-4o-mini** under the identical rubric.
- **Independent cross-family validation:** all 180 brochures in the validation set
  (all model-positive brochures + a random model-negative sample, seed 42)
  re-coded from the brochure text and the rubric alone by an independent rater from
  a **different model family** (Anthropic Claude), blind to the primary labels.

## 5. Exposure screen → `venue/brochure_exposure.csv`, `venue/marketing_exposure.csv`

The F1–F7 fingerprint (`data/prompts/exposure_fingerprints_v1.md`), distilled from
SEC orders IA-6573 (Delphia) and IA-6574 (Global Predictions), was applied to each
brochure and to marketing text; positives were human-adjudicated, and the
adjudication outcome is reported in the manuscript's enforcement-screen section.

## 6. Venue corpus → `venue/marketing_*.csv`, `venue/venue_divergence.csv`

For firms with a resolvable website, main-site marketing text was crawled, its
retrieval status logged (`marketing_crawl_log.csv`), classified under the same
rubric (`marketing_labels.csv`), and paired with the brochure result for the 283
firms present in both venues (`venue_divergence.csv`). (Collection scripts:
`b01_resolve_sites.py` … `b04_divergence.py`.)

## Pseudonymization

Before inclusion here, every file was re-keyed from CRD to a pseudonym `fid`
(`F0001`…`F0400`) and firm names were dropped, per the article's Data Availability
statement. The mapping is withheld; it is needed only to re-fetch raw brochures,
never to reproduce a result.
