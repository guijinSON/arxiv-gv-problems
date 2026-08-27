#!/usr/bin/env bash
# Robust arXiv fetch (source preferred, PDF fallback). Usage: scripts/fetch_paper.sh <id> [dir]
set -uo pipefail
ID="${1:?usage: scripts/fetch_paper.sh <arxiv_id> [outdir]}"; OUT="${2:-.}"
UA="arxiv-gv-problems/1.0 (research; contact via repo issues)"
mkdir -p "$OUT/src"
curl -sL -A "$UA" --max-time 120 -o "$OUT/$ID.tar" "https://arxiv.org/e-print/$ID" || true
if tar tzf "$OUT/$ID.tar" >/dev/null 2>&1; then tar xzf "$OUT/$ID.tar" -C "$OUT/src"
elif tar tf "$OUT/$ID.tar" >/dev/null 2>&1; then tar xf "$OUT/$ID.tar" -C "$OUT/src"
else echo "(source not a tarball; keeping raw)"; fi
curl -sL -A "$UA" --max-time 120 -o "$OUT/$ID.pdf" "https://arxiv.org/pdf/$ID" || true
sleep 3   # be polite to arXiv
echo "fetched $ID -> $OUT (src/ $(ls "$OUT/src" 2>/dev/null | wc -l | tr -d ' ') files)"
