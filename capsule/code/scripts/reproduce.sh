#!/usr/bin/env bash
# Reproduce every numerical result, table, and figure from the FROZEN dataset.
# No network, no API keys, no cost. Deterministic.
#
#   bash reproduce.sh                 # analyze + determinism (replication) check  [default]
#   bash reproduce.sh --analyze-only  # analyze once, skip the replication check
#   bash reproduce.sh --test          # run unit tests only
#   bash reproduce.sh --help
set -euo pipefail

usage() {
  cat <<'EOF'
Usage (from repository root or via /code/run on Code Ocean):

  bash reproduce.sh                 # analyze the frozen data + byte-identical replication check
  bash reproduce.sh --analyze-only  # analyze once
  bash reproduce.sh --test          # unit tests only (no data needed)
  bash reproduce.sh --help

Outputs: results/latest/{metrics_summary.md, tables/*.csv, figures/*.{png,svg}}
On Code Ocean these are written to /results.
EOF
}

MODE="full"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --analyze-only|--analyze) MODE="analyze"; shift ;;
    --replication|--full) MODE="full"; shift ;;
    --test) MODE="test"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

# Resolve roots for Code Ocean (/code,/data,/results) or a local checkout.
if [[ -d /code/src && -d /data ]]; then
  CODE_ROOT="/code"; export P10_DATA="/data"; export P10_RESULTS="/results"
  OUT="/results"
else
  CODE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  REPO_ROOT="$(cd "$CODE_ROOT/.." && pwd)"
  export P10_DATA="$REPO_ROOT/data"; export P10_RESULTS="$REPO_ROOT/results"
  OUT="$REPO_ROOT/results/latest"
fi
export PYTHONPATH="$CODE_ROOT/src:${PYTHONPATH:-}"

# PYTHON lets a caller pin the interpreter (a virtualenv, or a specific version) so the
# capsule and the revision analyses are reproduced under one environment. Code Ocean sets
# nothing and falls through to python3, exactly as before.
pybin="${PYTHON:-$(command -v python3 || command -v python)}"
if [[ -z "$pybin" ]] || ! command -v "$pybin" >/dev/null 2>&1; then
  echo "ERROR: python not found (PYTHON=${PYTHON:-unset})." >&2; exit 1
fi
echo "Python: $($pybin --version 2>&1)"

if [[ "$MODE" == "test" ]]; then
  exec bash "$CODE_ROOT/scripts/test.sh"
fi

mkdir -p "$OUT/tables" "$OUT/figures"
export P10_OUT_DIR="$OUT"

echo "== analyze =="
( cd "$CODE_ROOT/src" && "$pybin" analyze.py )
# The human-verification metrics are a separate estimator on a separate frame (two-phase
# weights, brochures and websites scored against their own classifiers), so they run as
# their own step rather than inside analyze.py.
( cd "$CODE_ROOT/src" && "$pybin" validate_human.py )
# Table 4 pairs a quoted passage with the label codes each model family and the human
# coder assigned. The codes are derived here from the frozen label files rather than
# carried as text, so the table is reproduced and not merely restated.
( cd "$CODE_ROOT/src" && "$pybin" case_table.py )
# The two figures as typeset in the article: serif, hatched for greyscale, 300 dpi.
# analyze.py draws the same data in a plain screen style; both are kept so the capsule
# regenerates the published figures and not only equivalents of them.
( cd "$CODE_ROOT/src" && "$pybin" publication_figures.py >/dev/null )
# The revision analyses: construct-sensitivity ladder, determinants, temporal
# falsification, vendor-excluded panel, venue-length conditioning. They write to
# results/revision/ and complete the artifact set behind every published number.
# Order matters: benchmark_determinants.py reads r1_3_aum_panel.csv, which
# revision_analyses.py writes. Running them the other way round left the determinants
# outputs missing on any run that started from an empty results directory -- which is
# every Code Ocean run -- and said so only on a stdout that is discarded here.
( cd "$CODE_ROOT/src" && "$pybin" revision_analyses.py >/dev/null )
( cd "$CODE_ROOT/src" && "$pybin" benchmark_determinants.py >/dev/null )
echo "[revision] wrote results/revision/ (ladder, determinants, temporal, venue-length)"

if [[ "$MODE" == "full" ]]; then
  echo "== replication (determinism) check =="
  ( cd "$CODE_ROOT/src" && "$pybin" replication_check.py )
fi

echo "Done. Open $OUT/metrics_summary.md (verdict first), tables/, figures/."
