#!/usr/bin/env bash
# Claim the next free paper.  Usage: scripts/claim.sh [arxiv_id]
# Race-safe: a claim is a new file claims/<id>.json pushed to the shared repo.
# If two people grab the same paper, the second push is rejected; we re-sync and
# take the next free one. Run from a CLEAN working tree.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
WHO="$(git config user.name 2>/dev/null || echo anon)"
WANT="${1:-}"
now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

if [ -n "$(git status --porcelain)" ]; then
  echo "ERROR: working tree not clean — submit or stash first."; exit 5
fi

for attempt in $(seq 1 200); do
  git fetch -q origin main || { echo "ERROR: git fetch failed."; exit 2; }
  git reset --hard -q origin/main
  if [ -n "$WANT" ]; then
    pick="$WANT"
    [ -f "claims/$pick.json" ] && { echo "ERROR: $pick already claimed."; exit 4; }
  else
    pick="$(python3 - <<'PY'
import json, os
for line in open("papers/papers.jsonl"):
    pid = json.loads(line)["arxiv_id"]
    if os.path.exists(f"claims/{pid}.json"):    continue
    if os.path.isdir(f"results/{pid}"):         continue
    print(pid); break
PY
)"
  fi
  [ -z "$pick" ] && { echo "NO_FREE_PAPERS_LEFT 🎉"; exit 3; }

  printf '{"paper":"%s","who":"%s","status":"in_progress","claimed_at":"%s"}\n' \
    "$pick" "$WHO" "$(now)" > "claims/$pick.json"
  git add "claims/$pick.json" && git commit -q -m "claim $pick by $WHO"
  if git push -q origin main 2>/dev/null; then
    echo "CLAIMED $pick"
    echo "  next:  bash scripts/run_codex.sh $pick"
    exit 0
  fi
  echo "  (race lost, retrying...)"; WANT=""
done
echo "ERROR: could not claim after 200 attempts."; exit 6
