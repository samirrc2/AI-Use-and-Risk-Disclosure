#!/usr/bin/env bash
# One command that runs every check on this paper. Exit 0 means all of them passed.
#
# There is no separate "final check" any more. Whatever this script reports is the state of
# the paper. If a check is not in here it is not being run, and the coverage line printed by
# a18 says exactly how much of the manuscript is bound to the capsule.
#
#   CAPSULE_PYTHON=/path/to/pinned/python bash verify.sh
#
# Two interpreters, because they need different things and mixing them makes the results
# meaningless:
#   CAPSULE_PYTHON  must match capsule/code/requirements.txt exactly, or byte-identical
#                   reproduction says nothing. Checked below; the script stops if it differs.
#   TOOLS_PYTHON    must have pypdf, used to read the compiled PDF. Without it a17 reports
#                   INCOMPLETE rather than passing. Defaults to python3.
set -uo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/Library/TinyTeX/bin/universal-darwin:$PATH"
CPY="${CAPSULE_PYTHON:-python3}"
TPY="${TOOLS_PYTHON:-python3}"
fail=0

echo "== preflight =="
if ! "$CPY" - <<'PY'
import re, sys
want = dict(re.findall(r"^([A-Za-z0-9_.-]+)==([0-9.]+)", open("capsule/code/requirements.txt").read(), re.M))
bad = []
for pkg, ver in want.items():
    if pkg == "pytest":
        continue
    try:
        got = __import__(pkg).__version__
    except Exception as e:
        bad.append(f"{pkg}: not importable ({e})"); continue
    if got != ver:
        bad.append(f"{pkg}: have {got}, capsule pins {ver}")
print("  capsule interpreter:", sys.version.split()[0], "-", "pins match" if not bad else "PIN MISMATCH")
for b in bad:
    print("   ", b)
sys.exit(1 if bad else 0)
PY
then
    echo "  Set CAPSULE_PYTHON to an interpreter matching capsule/code/requirements.txt."
    echo "  Reproduction claims are meaningless otherwise; refusing to continue."
    exit 1
fi
if ! "$TPY" -c "import pypdf" 2>/dev/null; then
    echo "  tools interpreter lacks pypdf (pip install pypdf); PDF checks would be skipped."
    exit 1
fi
echo "  tools interpreter:   $("$TPY" --version 2>&1 | awk '{print $2}') - pypdf present"

skipped=0
# Exit-code contract for every check below:
#   0  passed
#   1  something is wrong
#   2  could not check everything here, because inputs are deliberately not published
#      (the identified brochure corpus, the reviewer letters, the working-copy artifact
#      trees). A clone of the public repository hits this legitimately; it is reported as
#      a skip and named, never folded into a pass.
run () { local name="$1"; shift
    out=$("$@" 2>&1); local rc=$?
    if [ "$rc" = 0 ]; then
        printf '  PASS  %-34s %s\n' "$name" "$(echo "$out" | tail -1 | cut -c1-68)"
    elif [ "$rc" = 2 ]; then
        printf '  SKIP  %-34s %s\n' "$name" \
            "$(echo "$out" | grep -E "SKIP|INCOMPLETE|NOTE|SKIPPED" | head -1 | cut -c1-68)"
        echo "$out" | grep -E "SKIPPED:|not present here" | head -4 | sed 's/^/          /'
        skipped=$((skipped + 1))
    else
        printf '  FAIL  %-34s exit %d\n' "$name" "$rc"
        echo "$out" | grep -E "FAIL|UNBOUND|ERROR|unaccounted|VACUOUS" | head -8 | sed 's/^/          /'
        fail=1
    fi
}

echo
echo "== capsule reproduces from scratch =="
if out=$(cd capsule && PYTHON="$CPY" bash code/run 2>&1); then
    echo "$out" | grep -E "^PASS|Python:" | sed 's/^/  /'
else
    echo "  FAIL  capsule pipeline"; echo "$out" | tail -6 | sed 's/^/        /'; fail=1
fi
run "capsule self-tests"          bash -c "cd capsule && PYTHON='$CPY' bash code/run --test"

echo
echo "== manuscript, letters, package =="
run "a17 internal consistency"    "$TPY" analysis/a17_verify_manuscript.py
run "a14 number provenance"       "$TPY" analysis/a14_number_audit.py
run "a18 claims bound + coverage" "$TPY" analysis/a18_claims_bound.py
run "a19 no retired names"        "$TPY" analysis/a19_no_stale_names.py
run "capsule audit"               "$CPY" capsule/scripts/audit_manuscript.py
run "response-letter references"  bash -c "cd frontiers && '$TPY' submission/verify_response_refs.py"
run "response-letter structure"   bash -c "cd frontiers && '$TPY' submission/verify_letter_structure.py"
run "submission package current"  bash frontiers/build_package.sh --check

echo
"$TPY" analysis/a18_claims_bound.py 2>/dev/null | grep -E "coverage of body prose" | sed 's/^/  /'
if [ "$fail" != 0 ]; then
    echo "SOMETHING FAILED -- see above"
elif [ "$skipped" != 0 ]; then
    echo "ALL RUNNABLE CHECKS PASSED ($skipped skipped: inputs not published in this copy)"
else
    echo "ALL CHECKS PASSED"
fi
exit "$fail"
