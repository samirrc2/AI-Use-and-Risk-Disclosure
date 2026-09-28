# Environment (Code Ocean–compatible)

## Code Ocean

Capsule DOI: https://doi.org/10.24433/CO.3404788.v2

`Dockerfile` uses Code Ocean `py-r` (Python 3.12.8) and pins
`numpy==2.2.6`, `pandas==2.2.3`, `scipy==1.14.1`, `statsmodels==0.14.4`,
`matplotlib==3.9.2`, `pytest==8.3.3`. Reproduction needs **no API keys and
no network**.

Capsule mounts:

| Mount | Contents |
|-------|----------|
| `/code` | `src/`, `scripts/`, `tests/`, `requirements.txt`, `run` |
| `/data` | frozen pseudonymized inputs (see `data/README.md`) |
| `/results` | analysis outputs: `tables/`, `figures/`, `figures/publication/` (Figures 1 and 2 as typeset), `revision/`, `metrics_summary.md` |

Default Reproducible Run: `/code/run` → `bash code/scripts/reproduce.sh`
(analyze the frozen data, then a SHA-256 byte-identical replication check).
Expect `/results/metrics_summary.md` and **PASS** in
`/results/replication_check.md`. On Code Ocean the run writes straight to
`/results`; the `latest/` level exists only in a local checkout.

## Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r code/requirements.txt
bash reproduce.sh            # analyze + determinism check → results/latest/
bash reproduce.sh --test     # unit tests only
```

`reproduce.sh` sets `PYTHONPATH=code/src` and resolves `data/` and `results/`
automatically for both a local checkout and the Code Ocean mounts.
