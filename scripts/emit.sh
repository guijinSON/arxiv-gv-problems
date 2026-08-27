#!/usr/bin/env bash
# Emit dataset instances from a finished module.
# Usage: scripts/emit.sh <arxiv_id> [count] [difficulty]
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
ID="${1:?usage: scripts/emit.sh <arxiv_id> [count] [difficulty]}"
N="${2:-20}"; DIFF="${3:-}"
MOD="$(ls results/$ID/gen_*.py 2>/dev/null | head -1)"
[ -n "$MOD" ] || { echo "ERROR: no module at results/$ID/gen_*.py"; exit 1; }
mkdir -p artifacts
python3 - "$MOD" "$ID" "$N" "$DIFF" <<'PY'
import importlib.util, json, sys, random
mod_path, pid, n, diff = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
s = importlib.util.spec_from_file_location("m", mod_path)
m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
D = getattr(m, "DIFFICULTY", {})
name = diff or getattr(m, "SHIPPING_DIFFICULTY", next(iter(D), "medium"))
params = D.get(name, {})
out, bad = [], 0
for i in range(n):
    inst = m.make_instance(seed=10_000 + i, **params)
    ok, why = m.verify(inst, inst["answer"])
    if not ok:
        bad += 1; continue
    rec = {"paper": pid, "difficulty": name, "params": {**params, "seed": 10_000 + i},
           "question": m.render(inst), "answer": inst["answer"]}
    sp = m.search_space(inst)
    if sp is not None: rec["search_space"] = sp
    out.append(rec)
path = f"artifacts/{pid}.jsonl"
with open(path, "w") as f:
    for r in out: f.write(json.dumps(r) + "\n")
print(f"wrote {path}: {len(out)} instances (difficulty={name})" + (f"  [{bad} SKIPPED - planted failed!]" if bad else ""))
if bad: sys.exit(1)
PY
