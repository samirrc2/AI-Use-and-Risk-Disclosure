# Reproducibility audit

Last full verification of this capsule (offline, no network, no API keys).

| Check | Result |
|---|---|
| Environment | Pinned deps from `code/requirements.txt` (numpy 2.2.6, pandas 2.2.3, scipy 1.14.1, statsmodels 0.14.4, matplotlib 3.9.2) on Python 3.12.8, the version the Code Ocean base image ships |
| `bash code/run` | Completed, exit 0, from an empty results directory |
| Reproduction from scratch | Results deleted and regenerated: **55 of 55 output files byte-identical** |
| Determinism | Runs under differing `PYTHONHASHSEED`, `TZ` and `LC_ALL` produced byte-identical artifacts — PASS |
| Simulated Code Ocean mounts | Running each step with `/code`, `/data`, `/results` semantics reproduced every artifact byte-identically |
| Unit tests | `6 passed` |
| Fault injection | 14 corruptions of the frozen inputs (label flips, dropped rows, altered stratum counts, a repointed case, a nonexistent `fid`) — **14 of 14 changed the outputs or failed the run**, so the pipeline is not ignoring its inputs |
| Manuscript audit | **AUDIT PASS** — every headline number recomputes exactly from the frozen data |
| Claims bound to artifacts | 191 printed values in the manuscript bound to the specific artifact cell each comes from; **0 wrong**. Coverage of the body prose: 142 bound, 22 declared external with a reason, **0 unaccounted** |
| Table 4 | Its label codes are derived at run time from the frozen labels (`tables/table4_cases.csv`), not carried as text |
| Figures | Figures 1 and 2 regenerate at their typeset resolution under `figures/publication/`, and are byte-identical to the files the manuscript compiles |
| Pseudonymisation | 16 CSVs, 4,177 rows, no identifying column, all 400 identifiers of the form `F####` |

Reproduce it yourself, from this `capsule/` directory:

```
bash code/run          # analyze + byte-identical determinism check
bash code/run --test   # unit tests only
```

To run every check on the paper as well as the capsule, use `../verify.sh` from the
repository root. It refuses to run against an interpreter that does not match the pins
above, because a byte-identity claim made in the wrong environment means nothing.
