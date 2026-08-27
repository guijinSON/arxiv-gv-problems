#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
git fetch -q origin main 2>/dev/null && git reset --hard -q origin/main 2>/dev/null
T=$(wc -l < papers/papers.jsonl | tr -d ' ')
C=$(ls claims/*.json 2>/dev/null | wc -l | tr -d ' ')
D=$(grep -l '"status": *"done"' claims/*.json 2>/dev/null | wc -l | tr -d ' ')
echo "papers: $T | claimed: $C | done: $D | free: $((T-C))"
