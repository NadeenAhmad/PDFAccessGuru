#!/bin/bash
# The whole automatic evaluation of one frozen version, one step after the other, kind to the computer:
# veraPDF (Java) on at most 2 cores, at most WORKERS files at a time, low priority (on a Mac kept awake).
#
#   VERSION=1.1.0 WORKERS=3 bash evaluation/run_all.sh
#   (daytime, while the computer is in use: NICE=15 JAVA_CORES=1)
#
# 1. installs the version from PyPI into evaluation/work/venv-VERSION with pinned library versions
#    (evaluation/constraints.txt), so the same tool gives the same results;
# 2. runs every set with every setting (rules, Gemma 4 26B, GPT-6 Luna on Kumar);
# 3. the do-no-harm check of every output.
# Online settings check the EUR 10 budget before every file (budget.py) and stop at the stop line.
set -u
cd "$(dirname "$0")/.."
VERSION=${VERSION:?set VERSION, e.g. 1.1.0}
WORKERS=${WORKERS:-3}
NICE=${NICE:-10}
WORK=${PDFACCESSGURU_EVAL_WORK:-$PWD/evaluation/work}
AWAKE=$(command -v caffeinate >/dev/null && echo 'caffeinate -i' || echo '')
export PDFACCESSGURU_EVAL_VERSION=$VERSION JAVA_TOOL_OPTIONS=-XX:ActiveProcessorCount=${JAVA_CORES:-2} PDFACCESSGURU_DESCRIPTIONS=standard
if [ ! -x "$WORK/venv-$VERSION/bin/python" ]; then
  uv venv -q -p 3.13 "$WORK/venv-$VERSION" || exit 1
  VIRTUAL_ENV="$WORK/venv-$VERSION" uv pip install -q --refresh --no-build -c evaluation/constraints.txt "pdfaccessguru==$VERSION" || exit 1
fi
"$WORK/venv-$VERSION/bin/python" -c "import pdfaccessguru, sys; print('PDFAccessGuru', pdfaccessguru.__version__); sys.exit(pdfaccessguru.__version__ != '$VERSION')" || exit 1
# offline steps first: they may pause (lid closed) without harm; the online steps come later
for step in "reference rules" "kumar rules" "safedocs rules" "reference gemma" "kumar gemma" "safedocs gemma" "kumar luna"; do
  set -- $step
  echo "== $(date +%H:%M) run $1 $2"
  $AWAKE nice -n "$NICE" python3 evaluation/run.py "$1" "$2" --workers "$WORKERS" || echo "!! run $1 $2 ended with an error"
  echo "== $(date +%H:%M) no-harm $1 $2"
  $AWAKE nice -n "$NICE" python3 evaluation/no_harm.py "$1" "$2" || echo "!! no-harm $1 $2 ended with an error"
done
# the 4 documents of the PAVE-style check, with Gemma 4 26B
for doc in pave-1 pave-2 pave-3 pave-4; do
  out="$WORK/pave/outputs/pdfaccessguru-$VERSION/$doc.pdf"
  [ -f "$out" ] && continue
  mkdir -p "$WORK/pave/outputs/pdfaccessguru-$VERSION" "$WORK/pave/work"
  echo "== $(date +%H:%M) pave $doc"
  $AWAKE nice -n "$NICE" "$WORK/venv-$VERSION/bin/python" -I evaluation/fix_one.py "$WORK/pave/input/$doc.pdf" "$WORK/pave/work/v$VERSION-$doc" gemma \
    && cp "$WORK/pave/work/v$VERSION-$doc/fixed.pdf" "$out" || echo "!! pave $doc ended with an error"
  python3 -c "import json, sys; sys.path.insert(0, 'evaluation'); import budget; p = '$WORK/pave/work/v$VERSION-$doc/paid.jsonl'; import os
rows = [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []
print('cost USD', round(budget.record('pave docs: PDFAccessGuru $VERSION $doc (Gemma 4 26B)', [r for r in rows if r.get('id')]), 5))"
done
echo "== $(date +%H:%M) all done"
python3 -c "import sys; sys.path.insert(0, 'evaluation'); import budget; print(budget.status())"
