# Run sequence

## Reproduce the article (offline — this capsule)

No keys, no network, no cost. From the repository root (or `/code/run` on Code Ocean):

```bash
bash code/run                  # analyze frozen data + byte-identical replication check
bash code/run --analyze-only
bash code/run --test           # unit tests only
```

The run executes, in order: `analyze.py` (prevalences, gradient, weighting, validation,
figures), `validate_human.py` (two-coder human verification under the two-phase weights),
`case_table.py` (Table 4's label codes, derived from the frozen labels),
`publication_figures.py` (Figures 1 and 2 at their typeset resolution),
`revision_analyses.py` and `benchmark_determinants.py` (robustness, temporal
falsification, construct ladder, venue-length conditioning), then `replication_check.py`.
Order matters: `benchmark_determinants.py` reads a file `revision_analyses.py` writes.

Outputs:

- Local: `results/latest/` — `metrics_summary.md`, `tables/`, `figures/`,
  `replication_check.md`
- Code Ocean: `/results/metrics_summary.md`, `/results/tables/`, `/results/figures/`,
  `/results/figures/publication/`, `/results/revision/`, and
  `/results/replication_check.md` (SHA-256 determinism check; expect **PASS**).
  On Code Ocean the run writes straight to `/results`; the `latest/` level exists
  only in a local checkout.

## Upstream collection (documented, NOT run here)

The frozen `data/` files were produced once by the collection pipeline. These steps
require network access and API keys and are recorded for transparency only
(details in `DATA_PROVENANCE.md`):

```
s01_frame.py          # parse SEC Form ADV Part 1 bulk data -> sampling frame
s02_sample.py         # stratified random sample of 400 firms (frozen)
s03_current_brochures.py   # retrieve current Part 2A brochure per firm from IAPD
s05_classify.py       # classify each brochure with gpt-4o (rubric v1); gpt-4o-mini on a 60-subsample
                      # independent cross-family re-coding of the 180 validation brochures
b01_resolve_sites.py … b04_divergence.py   # marketing crawl, classify, venue divergence
```

## Determinism

`analyze.py` reads only the frozen files in `data/` and uses no randomness. Running
it twice yields byte-identical tables; `replication_check.py` asserts this and writes
`results/latest/replication_check.md`.
