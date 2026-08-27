#!/usr/bin/env bash
# Progress board.  Usage: scripts/status.sh [--write] [--sync]
#   --sync   fetch origin first
#   --write  regenerate STATUS.md (source of truth stays claims/*.json)
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
[ "${1:-}" = "--sync" ] || [ "${2:-}" = "--sync" ] && { git fetch -q origin main 2>/dev/null; git reset --hard -q origin/main 2>/dev/null; }
WRITE=""; [ "${1:-}" = "--write" ] || [ "${2:-}" = "--write" ] && WRITE=1
python3 - ${WRITE:+--write} <<'PY'
import json, os, sys, glob, datetime, collections
write = "--write" in sys.argv
papers = [json.loads(l) for l in open("papers/papers.jsonl")]
total = len(papers)
fam_of = {p["arxiv_id"]: p["family"] for p in papers}
claims = {}
for f in glob.glob("claims/*.json"):
    try: c = json.load(open(f))
    except Exception: continue
    claims[c.get("paper", os.path.basename(f)[:-5])] = c
by = collections.Counter(c.get("status", "claimed") for c in claims.values())
done      = by.get("done", 0)
rejected  = by.get("rejected", 0)
progress  = by.get("in_progress", 0) + by.get("claimed", 0)
free      = total - len(claims)
bar_n = 40
filled = int(bar_n * (done + rejected) / total) if total else 0
bar = "█" * filled + "░" * (bar_n - filled)

lines = []
lines.append(f"# Status\n")
lines.append(f"`{bar}`  **{done+rejected:,} / {total:,}** resolved "
             f"({100*(done+rejected)/total:.2f}%)\n")
lines.append("| state | count |")
lines.append("|---|---:|")
lines.append(f"| ✅ done | {done:,} |")
lines.append(f"| 🚫 rejected (documented) | {rejected:,} |")
lines.append(f"| 🔄 in progress | {progress:,} |")
lines.append(f"| ⚪ free | {free:,} |")
lines.append(f"| **total** | **{total:,}** |\n")

if progress:
    lines.append("## In progress\n")
    lines.append("| paper | who | claimed |")
    lines.append("|---|---|---|")
    rows = [c for c in claims.values() if c.get("status") in (None, "claimed", "in_progress")]
    for c in sorted(rows, key=lambda c: c.get("claimed_at", ""))[:40]:
        lines.append(f"| `{c.get('paper')}` | {c.get('who','?')} | {c.get('claimed_at','')[:16]} |")
    if len(rows) > 40: lines.append(f"| … {len(rows)-40} more | | |")
    lines.append("")

resolved_fam = collections.Counter(fam_of.get(p, "?") for p, c in claims.items()
                                   if c.get("status") in ("done", "rejected"))
tot_fam = collections.Counter(p["family"] for p in papers)
lines.append("## By family\n")
lines.append("| family | resolved | total |")
lines.append("|---|---:|---:|")
for fam, t in tot_fam.most_common(12):
    lines.append(f"| {fam} | {resolved_fam.get(fam,0):,} | {t:,} |")
lines.append(f"\n_regenerated {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M')}Z by `scripts/status.sh --write`_")

out = "\n".join(lines)
print(f"papers: {total:,} | done: {done:,} | rejected: {rejected:,} | in progress: {progress:,} | free: {free:,}")
if write:
    open("STATUS.md", "w").write(out + "\n")
    print("wrote STATUS.md")
PY
