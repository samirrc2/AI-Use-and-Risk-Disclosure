#!/usr/bin/env bash
# ============================================================================
# AI Use and Risk Disclosure by Investment Advisers — REPRODUCE (offline, $0, no network, no API keys)
# ============================================================================
# Stage 1 (always) regenerates every reported number, table and figure from the
# FROZEN, pseudonymized dataset and checks two runs are byte-identical, by
# delegating to the audited Code Ocean capsule under capsule/.
#
# Stage 2 (only in the full working repository) builds the coding apps and
# AUDITS THE MANUSCRIPT. Revision numbers already came from stage 1
# (capsule/code/src/). Do not re-run analysis/a11 or a13: those are wrappers
# around the same capsule scripts. Stage 2 still needs brochure text for the
# coding-app rebuild, so it is skipped when that tree is absent.
#
#   bash reproduce.sh              # both stages
#   bash reproduce.sh --capsule    # stage 1 only, exactly as Code Ocean runs it
#
# The original data-gathering path (network + API keys, time-sensitive) is the
# live pipeline in build/, analysis/, marketing/ and is NOT part of this
# reproduction; see run_all.sh.
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
export PYTHON="$PY"

if [ "${1:-}" = "--capsule" ]; then
    exec bash capsule/reproduce.sh
fi

echo "== stage 1: capsule reproduction =="
bash capsule/reproduce.sh "$@"

if [ ! -d data/brochure_text/current ]; then
    echo
    echo "== stage 2: skipped =="
    echo "   data/brochure_text/current is absent, so this is the capsule-only"
    echo "   distribution. Stage 1 above is complete and self-contained."
    exit 0
fi

echo
echo "== stage 2: coding apps and supplement =="
"$PY" analysis/a16_build_coding_app.py           # split the frame into the two coding apps
"$PY" analysis/a15_build_supplement.py

echo
echo "== stage 3: manuscript number audit =="
# A non-zero exit here means a figure in the paper is produced by no artifact.
# That is a failure, not a warning: it is how 20.9% survived to submission.
"$PY" analysis/a14_number_audit.py

echo
echo "== stage 4: manuscript self-consistency =="
# a14 proves every number came from somewhere; a17 proves the paper is coherent and the
# published statistics are actually correct: Wilson intervals recomputed from k/n, float
# numbering against citation order, section cross-references against current headings,
# abbreviations defined at first use. A number can be generated correctly and still be
# mis-transcribed, and a cross-reference silently drifts whenever a section moves.
"$PY" analysis/a17_verify_manuscript.py
