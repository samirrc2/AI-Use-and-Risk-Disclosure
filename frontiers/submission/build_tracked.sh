#!/usr/bin/env bash
# Build the tracked-changes PDF: the as-submitted manuscript against the current revision.
#
#   bash frontiers/submission/build_tracked.sh
#
# manuscript_v1_as_submitted.tex is the version at the commit that was sent to the journal
# (recovered with `git show`). latexdiff marks every change; fix_tracked.py repairs the two
# artefacts latexdiff leaves behind in this document class (see that file for details).
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/Library/TinyTeX/bin/universal-darwin:$PATH"

OLD=manuscript_v1_as_submitted.tex
NEW=../manuscript.tex
OUT=manuscript_tracked.tex

latexdiff --encoding=utf8 --append-safecmd="citep,citet,ref,label,url" \
          "$OLD" "$NEW" > "$OUT" 2>/dev/null || true
python3 fix_tracked.py "$OUT" "$NEW"

cp ../references.bib ../FrontiersinHarvard.cls ../Frontiers-Harvard.bst . 2>/dev/null || true
mkdir -p figures && cp ../figures/*.png figures/ 2>/dev/null || true
cp ../logo1.eps . 2>/dev/null || true   # the only logo the Frontiers class renders

for i in 1 2 3; do
    pdflatex -interaction=nonstopmode "$OUT" >/dev/null 2>&1 || true
    [ "$i" = 1 ] && (bibtex "${OUT%.tex}" >/dev/null 2>&1 || true)
done
echo "built $(pwd)/manuscript_tracked.pdf"
grep -o "Output written.*" "${OUT%.tex}.log" || true
