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

python3 - "$ID" > "$OUT/.task.md" <<'PY'
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

# The hardening oracle is a four-vendor pool reached through OpenRouter, so an
# OpenAI key can only serve one member of it.  See scripts/harden.py.
if [ -z "${OPENROUTER_API_KEY:-}" ]; then
  echo "ERROR: export OPENROUTER_API_KEY — the hardening oracle pool spans four vendors."
  exit 3
fi

CODEX_BIN="${CODEX_BIN:-$(command -v codex)}"
[ -n "$CODEX_BIN" ] || { echo "ERROR: codex CLI not found (set CODEX_BIN)"; exit 2; }
CV="$("$CODEX_BIN" --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
CVMIN="0.150.0"
if [ "$(printf '%s\n%s\n' "$CVMIN" "$CV" | sort -V | head -1)" != "$CVMIN" ]; then
  echo "ERROR: codex $CV is too old for gpt-5.6-sol (need >= $CVMIN)."
  echo "  npm install -g @openai/codex@latest    # then use that binary, e.g."
  echo "  CODEX_BIN=\$HOME/.npm-global/bin/codex bash scripts/run_codex.sh $ID"
  exit 4
fi

# --- sandbox: see CODEX.md. Prefer the real sandbox; fall back only if bwrap is broken.
MODE="${CODEX_SANDBOX_MODE:-workspace-write}"
if [ "$MODE" = "bypass" ]; then
  SANDBOX_ARGS=(--dangerously-bypass-approvals-and-sandbox)
  echo "WARNING: running WITHOUT sandbox. Only do this in a disposable VM/container."
else
  # workspace-write blocks network by default; STEP 4's harden.py must reach
  # openrouter.ai, and STEP 0 must reach arxiv.org.  Without this the run gets
  # "curl: (6) Could not resolve host" and dies at the hardening loop.
  SANDBOX_ARGS=(--sandbox "$MODE" -c sandbox_workspace_write.network_access=true)
fi

python3 -c "
import json,datetime
json.dump({'paper':'$ID',
           'schema_version':2,
           'model':'${CODEX_MODEL:-gpt-5.6-sol}',
           'effort':'${CODEX_EFFORT:-xhigh}',
           'codex_version':'$CV',
           'started_at':datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')},
          open('$OUT/.meta.json','w'), indent=1)"

cd "$OUT"
setsid nohup "$CODEX_BIN" exec --skip-git-repo-check "${SANDBOX_ARGS[@]}" \
  -m "${CODEX_MODEL:-gpt-5.6-sol}" -c model_reasoning_effort="${CODEX_EFFORT:-xhigh}" \
  "$(cat .task.md)" > codex_run.log 2>&1 < /dev/null &
sleep 10
echo "started $ID  codex=$CV model=${CODEX_MODEL:-gpt-5.6-sol} effort=${CODEX_EFFORT:-xhigh}"
echo "  log: $OUT/codex_run.log"
echo "watch:  tail -f $OUT/codex_run.log"
