#!/usr/bin/env bash
# Claim the next paper.  Usage: scripts/claim.sh [arxiv_id]
# With no argument, selection is DEFICIT-BASED and STRATIFIED -- see
# scripts/pick_paper.py.  The old rule took the first free line of
# papers/papers.jsonl, which is grouped by family, so it handed out 73
# consecutive "additive combinatorial structures" papers; that rule reproduced
# the corpus's combinatorial skew by construction.
# Set CLAIM_EXPLAIN=1 to see the deficit table before the pick.
# Race-safe: a claim is a new file claims/<id>.json pushed to the shared repo.
# If two people grab the same paper, the second push is rejected; we re-sync,
# EXCLUDE the contested id and draw again. Run from a CLEAN working tree.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
WHO="$(git config user.name 2>/dev/null || echo anon)"
WANT="${1:-}"
now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

if [ -n "$(git status --porcelain)" ]; then
  echo "ERROR: working tree not clean — submit or stash first."; exit 5
fi

CONTESTED=""          # ids we lost a race on; never re-drawn this run
EXPLAIN_FLAG=""
[ -n "${CLAIM_EXPLAIN:-}" ] && EXPLAIN_FLAG="--explain"

for attempt in $(seq 1 200); do
  git fetch -q origin main || { echo "ERROR: git fetch failed."; exit 2; }
  git reset --hard -q origin/main
  if [ -n "$WANT" ]; then
    pick="$WANT"
    [ -f "claims/$pick.json" ] && { echo "ERROR: $pick already claimed."; exit 4; }
  else
    pick="$(python3 scripts/pick_paper.py --exclude "$CONTESTED" $EXPLAIN_FLAG)"
    rc=$?
    EXPLAIN_FLAG=""
    if [ $rc -eq 3 ]; then echo "NO_FREE_PAPERS_LEFT"; exit 3; fi
    if [ $rc -ne 0 ] || [ -z "$pick" ]; then
      echo "ERROR: scripts/pick_paper.py failed (rc=$rc). Not claiming."; exit 4
    fi
  fi
  # An id containing "/" needs a directory nothing creates; the redirect then fails
  # and we used to print CLAIMED regardless.  Verify the file exists before claiming.
  case "$pick" in */*) echo "ERROR: $pick is a legacy slashed id and cannot be a claim path."; exit 4;; esac
  printf '{"paper":"%s","who":"%s","status":"in_progress","claimed_at":"%s"}\n' \
    "$pick" "$WHO" "$(now)" > "claims/$pick.json"
  [ -s "claims/$pick.json" ] || { echo "ERROR: could not write claims/$pick.json"; exit 4; }
  git add "claims/$pick.json" && git commit -q -m "claim $pick by $WHO"
  if git push -q origin main 2>/dev/null; then
    echo "CLAIMED $pick"
    echo "  next:  bash scripts/run_codex.sh $pick"
    exit 0
  fi
  if [ -n "$WANT" ]; then
    echo "ERROR: $WANT was claimed by someone else while we were pushing."; exit 4
  fi
  CONTESTED="${CONTESTED:+$CONTESTED,}$pick"
  git reset --hard -q origin/main
  sleep "0.$(( (RANDOM % 7) + 2 ))"
  echo "  (race lost on $pick, redrawing...)"
done
echo "ERROR: could not claim after 200 attempts."; exit 6
