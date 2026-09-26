#!/usr/bin/env bash
# AI Use and Risk Disclosure by Investment Advisers — end-to-end LIVE pipeline (needs API keys + network).
#
# To REPRODUCE the published numbers you do NOT need this script: run
#   cd capsule && bash reproduce.sh          # offline, deterministic, no keys
#
# This script re-collects from source. Order:
#   build/     s01 frame -> s02 sample(400) -> s03/s04 brochures -> s05 classify -> s06 endpoints
#   analysis/  a07 weighting -> a08 inference -> a09 missingness -> a10 coding sheet
#   marketing/ b01 resolve sites -> b02 crawl -> b03 classify -> b04 divergence
# Keys are read from the sibling "API Keys/keys.env.txt" (see build/common.py).
set -euo pipefail
cd "$(dirname "$0")"
PY="${PY:-python3}"

echo "== build: frame, sample, brochures, classify =="
$PY build/s01_frame.py
$PY build/s02_sample.py
$PY build/s03_current_brochures.py
$PY build/s05_classify.py
$PY build/s06_endpoints.py

echo "== analysis: weighting, inference, missingness, coding sheet =="
(cd analysis && $PY a07_weighting.py && $PY a08_inference.py && $PY a09_missingness.py && $PY a10_build_coding_sheet.py)

echo "== marketing: venue divergence =="
(cd marketing && $PY b01_resolve_sites.py && $PY b02_crawl_marketing.py && $PY b03_classify_marketing.py && $PY b04_divergence.py)

echo "== done. For the frozen, offline reproduction of published numbers: cd capsule && bash reproduce.sh =="
