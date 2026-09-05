#!/usr/bin/env bash
# Park a paper: a terminal state that is neither shipped nor rejected.
#
#   scripts/park.sh <arxiv_id> "<reason>"
#
# WHY THIS EXISTS.  A cap_bound family has no other resting place.  It cannot be
# submitted -- the oracle solves it at the shipping preset, so G9 fails -- and it must
# not be rejected, because the binding constraint is OUR 256-atom answer format, not
# the paper.  Before this, such a paper sat in_progress forever, holding a build slot
# that nothing could ever free.  1402.1813 is the worked example: its builder did
# everything right, returned "cap_bound" from escalate(), kept its module, and wrote no
# rejection -- and the pipeline had nowhere to put it.
#
# `parked` is deliberately NOT counted as shipped: corpus_report.py walks
# ("done", "in_progress"), so a parked paper stays out of the corpus and out of every
# quota computed over it.  pick_paper.py treats any claim file as taken, so a parked
# paper is never handed out again by accident.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
ID="${1:?usage: scripts/park.sh <arxiv_id> \"<reason>\"}"
REASON="${2:?give a reason -- a park with no reason is indistinguishable from a leak}"
[ -f "claims/$ID.json" ] || { echo "ERROR: claims/$ID.json missing."; exit 1; }

python3 - "$ID" "$REASON" <<'PY'
import json, sys, datetime, os
pid, reason = sys.argv[1], sys.argv[2]
p = f"claims/{pid}.json"
d = json.load(open(p))
d["status"] = "parked"
d["parked_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
d["parked_reason"] = reason
d.pop("done_at", None)
json.dump(d, open(p, "w"))
v = None
mp = f"results/{pid}/.meta.json"
if os.path.exists(mp):
    try:
        v = (json.load(open(mp)) or {}).get("harden_verdict") or {}
    except Exception:
        v = None
if v:
    d_ = {k: v.get(k) for k in ("verdict", "escalations_used", "answer_atoms",
                                "answer_chars", "axes_moved", "signal") if v.get(k) is not None}
    print(f"  harden verdict: {json.dumps(d_)}")
print(f"PARKED {pid}: {reason}")
PY
bash scripts/status.sh --write >/dev/null 2>&1
# Stage paths one at a time.  A single `git add a b c` ABORTS on the first missing
# pathspec and stages nothing, and results/<id> is routinely absent locally because
# the harvest is git-cleaned each cycle -- so the whole park silently did nothing.
git add "claims/$ID.json"
git add STATUS.md 2>/dev/null || true
[ -d "results/$ID" ] && git add "results/$ID" 2>/dev/null || true
git commit -q -m "park $ID: $REASON"
git pull -q --rebase origin main && bash scripts/status.sh --write >/dev/null 2>&1 \
  && git add STATUS.md && git commit -q --amend --no-edit && git push -q origin main \
  && echo "pushed" || { echo "push failed — run: git pull --rebase origin main && git push origin main"; exit 4; }
