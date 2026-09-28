# Data availability statement

*(For the Frontiers in Artificial Intelligence submission — deposit supporting
materials in a repository, then cite and link them from the article.)*

All code and frozen data required to reproduce every number, table, and figure in
this article are openly available as an executable, deterministic Code Ocean capsule and in the
source repository:

- **Source repository:** https://github.com/samirrc2/AI-Use-and-Risk-Disclosure
- **Executable capsule (Code Ocean):** https://doi.org/10.24433/CO.3404788.v2

The Code Ocean capsule (DOI above) is the archived, executable version of record; the
source repository is made public upon acceptance.

## The deposit contains

- **Frozen stratified sample** (`data/sample.csv`, 400 firms; 388 classified) and the
  **classifier label sets** — primary gpt-4o labels (`data/labels_primary.csv`),
  same-family gpt-4o-mini subsample (`data/labels_secondary_sub.csv`), and the
  independent cross-family re-coding (`data/labels_independent.csv`), each pseudonymized.
- **Population stratum counts** (`data/population_strata.csv`) and the frozen
  **venue/exposure tables** (`data/venue/`): marketing labels, brochure and marketing
  exposure screens, the matched venue-divergence table, and the marketing crawl log.
- **The measurement instruments** (`data/prompts/`): the frozen five-label typology
  rubric and the F1–F7 AI-washing exposure fingerprint distilled from SEC orders
  IA-6573/IA-6574.
- **Analysis code** (`code/src/`): typology prevalence, the size/type gradient, design-based
  inference (Wilson intervals, trend tests, logistic regression), survey weighting, the
  design-weighted two-phase validation, the exposure summary, and the venue/missingness
  analysis — plus a byte-identical replication check.
- **Provenance**: data provenance and design docs (`docs/`), the decision log
  (`DECISIONS.md`), and a SHA-256 freeze receipt.

## Reproduction is offline, deterministic, and free

`bash reproduce.sh` regenerates the full analysis from the frozen, pseudonymized inputs
and re-derives every reported statistic, then verifies that two independent runs produce
byte-identical tables. It makes **no vendor API calls and requires no network or keys**.

The classifier labels were produced by a large-language-model pass over brochure text
(network, cost, and model-version sensitive) plus an independent cross-family re-coding.
As with a frozen model-output dataset, that classification is **not re-executed**; the
label tables are frozen, and the pipeline reproduces every published number from them.

## Upstream source (referenced, not redistributed here)

SEC Form ADV Part 1 bulk data (filings through 31 December 2024) and Part 2A brochures
retrieved from the Investment Adviser Public Disclosure (IAPD) system, both public. To
honor firm-level confidentiality, firm identifiers in the release are pseudonymized and
the crosswalk to CRD identifiers is withheld; it is required only to re-fetch raw source
documents, never to reproduce a published result.

No proprietary, personal, or confidential data are used or distributed. Only aggregate
rates and counts are reported; the study measures disclosure behavior, not compliance,
and makes no claim that any named adviser breached a disclosure obligation.
