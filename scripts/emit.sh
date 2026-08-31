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
import importlib.util, json, os, sys, random
mod_path, pid, n, diff = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
s = importlib.util.spec_from_file_location("m", mod_path)
m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
D = getattr(m, "DIFFICULTY", {})
name = diff or getattr(m, "SHIPPING_DIFFICULTY", next(iter(D), "medium"))
params = D.get(name, {})

# Seeds are drawn, not counted off from a constant.  A fixed ladder like
# 10_000+i means every run of a paper emits the same instances forever, so an
# easy instance that slips in stays in; drawing them means the dataset is a
# fresh sample each time.  Reproducibility comes from recording, not from
# fixing: the master seed lands in .meta.json and each instance carries its own
# seed in `params`.
META = f"results/{pid}/.meta.json"
try:
    meta = json.load(open(META))
except (OSError, ValueError):
    meta = {}
# Fresh every run.  Set EMIT_MASTER_SEED to deliberately reproduce an earlier
# dataset from the value recorded in .meta.json; never default to the stored one,
# or "random seeds" quietly becomes "the first run's seeds, forever".
master = int(os.environ.get("EMIT_MASTER_SEED") or int.from_bytes(os.urandom(8), "big"))
rng = random.Random(master)

# Instances that are the same problem up to relabelling are worth one instance,
# not two.  canonical_key is the family's own definition of that; resample past
# collisions rather than shipping near-duplicates.
seen, out, bad, dupes, tries = set(), [], 0, 0, 0
while len(out) < n and tries < 3 * n:
    tries += 1
    seed = rng.randrange(1, 2**31 - 1)
    inst = m.make_instance(seed=seed, **params)
    ok, why = m.verify(inst, inst["answer"])
    if not ok:
        bad += 1; continue
    key = m.canonical_key(inst)
    if key in seen:
        dupes += 1; continue
    seen.add(key)
    rec = {"paper": pid, "difficulty": name, "params": {**params, "seed": seed},
           "question": m.render(inst), "answer": inst["answer"]}
    sp = m.search_space(inst)
    if sp is not None: rec["search_space"] = sp
    out.append(rec)

path = f"artifacts/{pid}.jsonl"
with open(path, "w") as f:
    for r in out: f.write(json.dumps(r) + "\n")
print(f"wrote {path}: {len(out)} instances (difficulty={name})"
      + (f"  [{bad} SKIPPED - planted failed!]" if bad else "")
      + (f"  [{dupes} duplicates resampled]" if dupes else ""))

if os.path.isdir(f"results/{pid}"):
    meta.update(emit_master_seed=master, emit_tries=tries,
                emit_duplicate_rate=round(dupes / tries, 4) if tries else 0.0)
    json.dump(meta, open(META, "w"), indent=1)

if bad: sys.exit(1)
if len(out) < n:
    # A family that cannot produce n distinct problems in 3n draws has a seed
    # space that is exhausted, and that is a defect in the family rather than
    # something to paper over with a short dataset.
    print(f"ERROR: only {len(out)}/{n} distinct instances in {tries} draws "
          f"({dupes} duplicates) — the instance space is too small to sample.")
    sys.exit(1)
PY
