#!/usr/bin/env bash
# ============================================================================
# Rebuild EVERY file derived from manuscript.tex, in dependency order.
# ============================================================================
# This exists because the submission package kept going stale: the manuscript
# would be edited and the tracked-changes PDF, the DOCX and the figure copies
# would silently keep describing an older version. Run this after any edit to
# manuscript.tex, or run it with --check to be told what is out of date without
# building anything.
#
#   bash frontiers/build_package.sh            # rebuild everything
#   bash frontiers/build_package.sh --check    # report staleness, exit 1 if stale
#
# Deliberately NOT rebuilt: manuscript_v1_as_submitted.*, which is the frozen
# version sent to the journal and must keep matching git HEAD.
# ============================================================================
set -euo pipefail
# Resolve before the cd: the final self-check re-invokes this script, and a relative $0 no
# longer resolves once we are inside frontiers/. That silently skipped the staleness check
# at the end of every full build -- the one thing this script exists to guarantee.
SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
cd "$(dirname "$0")"
export PATH="$HOME/Library/TinyTeX/bin/universal-darwin:$PATH"

SRC=manuscript.tex
DERIVED=(manuscript.pdf manuscript.docx submission/manuscript_tracked.pdf
         submission/Figure1.png submission/Figure2.png
         submission/response_reviewer_1.pdf submission/response_reviewer_3.pdf)

if [ "${1:-}" = "--check" ]; then
    stale=0
    for f in "${DERIVED[@]}"; do
        # The response PDFs are typeset from the .txt letters, so they go stale against those
        # rather than against manuscript.tex. Their page and line references do depend on the
        # manuscript, and a timestamp cannot see that; verify_response_refs.py below checks
        # them against the compiled PDF. That script did not exist when this comment first
        # claimed it did, and four stale references shipped past the check that replaced it.
        case "$f" in
          submission/response_reviewer_1.pdf) dep=submission/response_reviewer_1.txt ;;
          submission/response_reviewer_3.pdf) dep=submission/response_reviewer_3.txt ;;
          *) dep="$SRC" ;;
        esac
        if [ ! -f "$dep" ]; then
            continue          # source not published in this copy; nothing to rebuild from
        fi
        if [ ! -f "$f" ] || [ "$f" -ot "$dep" ]; then
            echo "STALE: $f"; stale=1
        fi
    done
    # Staleness is only half of it: a reference can point at the wrong section of a perfectly
    # fresh PDF. Never let this degrade to a skip -- a missing dependency must fail the gate.
    echo
    # Exit 2 from these means "the inputs are not published in this copy", which is not a
    # stale package. Only a real failure (exit 1) should block.
    rc=0; python3 submission/verify_response_refs.py || rc=$?
    [ "$rc" = 0 ] || [ "$rc" = 2 ] || stale=1
    echo
    # Numbers can all be right while the reviewers' own prose sits unattributed in a letter
    # signed by the authors. verify_response_refs.py cannot see that; this can.
    rc=0; python3 submission/verify_letter_structure.py || rc=$?
    [ "$rc" = 0 ] || [ "$rc" = 2 ] || stale=1
    echo
    # Bind every prose claim to the artifact cell it comes from. a14 only asks whether a
    # printed figure occurs somewhere in some artifact, which let seven of eight altered
    # values through untouched.
    if python3 ../analysis/a18_claims_bound.py >/dev/null; then
        echo "claims bound to artifacts: ok"
    else
        python3 ../analysis/a18_claims_bound.py | grep -E "FAIL|UNBOUND|bound to artifacts" || true
        stale=1
    fi
    echo
    [ "$stale" = 0 ] && echo "package is current" || echo "run: bash frontiers/build_package.sh"
    exit "$stale"
fi

echo "== 1/5 manuscript PDF =="
for i in 1 2 3; do
    pdflatex -interaction=nonstopmode "$SRC" >/dev/null 2>&1 || true
    [ "$i" = 1 ] && (bibtex "${SRC%.tex}" >/dev/null 2>&1 || true)
done
grep -o "Output written.*" manuscript.log || true

echo "== 2/5 figure copies for submission =="
# The submission copies must match the numbering in the compiled PDF, not the
# names of the source files: fig2 is Figure 1 and fig4 is Figure 2.
rm -f submission/Figure*.png
cp figures/fig2.png submission/Figure1.png
cp figures/fig4.png submission/Figure2.png
echo "   Figure1.png <- fig2.png (size gradient); Figure2.png <- fig4.png (venue)"

echo "== 3/5 tracked changes =="
bash submission/build_tracked.sh 2>&1 | tail -2


echo "== 4/5 reviewer response PDFs =="
# Typeset from the plain-text letters, which stay the source of truth because the portal needs
# text. No bold, no italics: structure comes from spacing and bullets only.
(cd submission && python3 build_responses.py)

echo "== 5/5 DOCX =="
# pandoc's LaTeX reader silently drops any tabular containing \multicolumn, so the
# command is expanded to plain cells first. Without this, four tables come out as
# raw LaTeX text in the Word file.
python3 - <<'PY'
import os, re, shutil, subprocess
os.makedirs("/tmp/_docx", exist_ok=True)
s = open("manuscript.tex", encoding="utf-8").read()

def grab(t, i):
    d = 0; st = i + 1
    while i < len(t):
        if t[i] == "{": d += 1
        elif t[i] == "}":
            d -= 1
            if d == 0: return t[st:i], i + 1
        i += 1
    raise ValueError

out = []; i = 0; n = 0
while True:
    j = s.find("\\multicolumn", i)
    if j < 0:
        out.append(s[i:]); break
    out.append(s[i:j])
    span, k = grab(s, s.index("{", j)); _, k = grab(s, k); body, k = grab(s, k)
    out.append(body + " & " * (int(span) - 1)); n += 1; i = k
open("/tmp/_docx/manuscript.tex", "w", encoding="utf-8").write("".join(out))
shutil.copy("references.bib", "/tmp/_docx/")
shutil.copytree("figures", "/tmp/_docx/figures", dirs_exist_ok=True)
r = subprocess.run(["pandoc", "manuscript.tex", "--bibliography=references.bib",
                    "--citeproc", "--resource-path=.:figures", "-o", "manuscript.docx"],
                   cwd="/tmp/_docx", capture_output=True, text=True)
if r.returncode:
    raise SystemExit("pandoc failed: " + r.stderr[:400])
shutil.copy("/tmp/_docx/manuscript.docx", "manuscript.docx")
print(f"   expanded {n} multicolumn cells; DOCX written")
PY

echo
echo "== package current =="
bash "$SELF" --check
