#!/usr/bin/env bash
# One command: build packet -> browser capture -> summary.   Usage: tools/evidence/run.sh A1
set -euo pipefail
TRACK="${1:?usage: tools/evidence/run.sh <TRACK, e.g. A1>}"
LOWER="$(echo "$TRACK" | tr '[:upper:]' '[:lower:]')"
cd "$(dirname "$0")/../.."
START=$(date +%s)
echo "== [1/3] build tracks/$TRACK/evidence/packet.json"
uv run python "tools/evidence/build_${LOWER}.py"
echo "== [2/3] browser capture (Playwright + Chromium)"
node viewer/capture.mjs "$TRACK"
echo "== [3/3] summary"
uv run python - "$TRACK" <<'PY'
import json, sys
t = sys.argv[1]
p = json.load(open(f"tracks/{t}/evidence/packet.json")); c = json.load(open(f"tracks/{t}/evidence/capture.json"))
print(f"track {t}: verdict={p['result']['verdict']}  git={p['run_record']['git_sha'][:12]}  dirty={p['run_record']['working_tree_dirty']}")
for tst in p["run_record"]["tests"]: print(f"  pytest {tst['target']}: {tst['summary']}")
print(f"  browser: {c['browser']['name']} {c['browser']['version']}  viewport {c['viewport']['width']}x{c['viewport']['height']}")
print(f"  assertions: {c['assertions_passed']}/{c['assertions_total']} passed  ok={c['ok']}")
for s in c["screenshots"]: print(f"  tracks/{t}/evidence/{s}")
sys.exit(0 if c["ok"] else 1)
PY
echo "done in $(( $(date +%s) - START ))s"
