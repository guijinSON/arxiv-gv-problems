#!/usr/bin/env bash
# Build a generator/verifier for one paper with Codex.  Usage: scripts/run_codex.sh <arxiv_id>
# Requires: codex CLI logged in, OPENAI_API_KEY exported (for the hardening loop).
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
ID="${1:?usage: scripts/run_codex.sh <arxiv_id>}"
OUT="results/$ID"; mkdir -p "$OUT"

# claim state: claimed -> in_progress
if [ -f "claims/$ID.json" ]; then
  python3 -c "
import json,datetime,sys
p='claims/$ID.json'; d=json.load(open(p))
d['status']='in_progress'
d['started_at']=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
json.dump(d,open(p,'w'))"
fi

python3 - "$ID" > "$OUT/TASK.md" <<'PY'
import json, sys
pid = sys.argv[1]
rec = next(json.loads(l) for l in open("papers/papers.jsonl")
           if json.loads(l)["arxiv_id"] == pid)
print(open("prompts/codex_task.md").read())
print(f"""## PAPER

arXiv id: {rec['arxiv_id']}
url: {rec['url']}
title: {rec['title']}
categories: {rec['all_cats']}

Prior triage (a hypothesis, not ground truth - verify it against the paper):
  family: {rec['family']}
  method: {rec['method']}
  candidate generator: {rec['candidate_generator']}
  candidate verifier: {rec['candidate_verifier']}
""")
PY

: "${OPENAI_API_KEY:?export OPENAI_API_KEY first (needed for the gpt-5.6-terra loop)}"
command -v codex >/dev/null || { echo "ERROR: codex CLI not on PATH"; exit 2; }

# --- sandbox: see CODEX.md. Prefer the real sandbox; fall back only if bwrap is broken.
MODE="${CODEX_SANDBOX_MODE:-workspace-write}"
if [ "$MODE" = "bypass" ]; then
  SANDBOX_ARGS=(--dangerously-bypass-approvals-and-sandbox)
  echo "WARNING: running WITHOUT sandbox. Only do this in a disposable VM/container."
else
  SANDBOX_ARGS=(--sandbox "$MODE")
fi

cd "$OUT"
setsid nohup codex exec --skip-git-repo-check "${SANDBOX_ARGS[@]}" \
  -m "${CODEX_MODEL:-gpt-5.5}" -c model_reasoning_effort="${CODEX_EFFORT:-high}" \
  "$(cat TASK.md)" > codex_run.log 2>&1 < /dev/null &
sleep 10
echo "started $ID (pid $(pgrep -x codex | head -1)) -> $OUT/codex_run.log"
echo "watch:  tail -f $OUT/codex_run.log"
