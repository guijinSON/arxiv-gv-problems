#!/usr/bin/env bash
# Emit dataset instances from a finished module.
# Usage: scripts/emit.sh <arxiv_id> [count] [difficulty]
set -uo pipefail
# Resolve the script's own directory BEFORE cd'ing, so the python below can import
# scripts/corpus_report.py no matter where emit.sh was invoked from.
HERE="$(cd "$(dirname "$0")" && pwd)" || exit 1
cd "$HERE/.." || exit 1
ID="${1:?usage: scripts/emit.sh <arxiv_id> [count] [difficulty]}"
N="${2:-20}"; DIFF="${3:-}"
MOD="$(ls results/$ID/gen_*.py 2>/dev/null | head -1)"
[ -n "$MOD" ] || { echo "ERROR: no module at results/$ID/gen_*.py"; exit 1; }
mkdir -p artifacts
python3 - "$MOD" "$ID" "$N" "$DIFF" "$HERE" <<'PY'
import importlib.util, json, os, sys, random
mod_path, pid, n, diff, scripts_dir = (sys.argv[1], sys.argv[2], int(sys.argv[3]),
                                       sys.argv[4], sys.argv[5])
s = importlib.util.spec_from_file_location("m", mod_path)
m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
D = getattr(m, "DIFFICULTY", {})
name = diff or getattr(m, "SHIPPING_DIFFICULTY", next(iter(D), "medium"))
if name not in D:
    sys.exit(f"ERROR: {mod_path} has no difficulty {name!r}; it has {list(D)}")
params = D[name]

# Every record carries the family's profile, so the release can be SLICED after the
# fact instead of being split in advance.  Without this, answering "how much of the
# dataset is really graph search?" means re-importing 40 generator modules and
# re-deriving the labels -- which is how the corpus stayed 68% discrete without
# anyone noticing.  The classifier is scripts/corpus_report.py, imported rather than
# duplicated: two copies of this logic would drift, and then the report and the
# dataset would disagree about what was shipped.
sys.path.insert(0, scripts_dir)
try:
    import corpus_report
except Exception as e:
    print(f"ERROR: cannot import {scripts_dir}/corpus_report.py ({e}).\n"
          "       emit.sh stamps every record with native_domain / computational_core /\n"
          "       certificate_form / object_regime / domain_essentiality /\n"
          "       reduction_kind / track / core_provenance, and an unlabelled artifact\n"
          "       cannot be sliced later.  Fix the import rather than emitting blind.")
    sys.exit(1)

# The profile is a property of the FAMILY, not of an instance, so it is computed once
# from a shipping-preset instance and stamped identically onto every record.  A
# failure here is reported, never swallowed: `core_provenance` would silently read
# "derived" and the release would look measured when it is not.
try:
    profile = corpus_report.profile_for_module(
        m, m.make_instance(seed=1, **params), family=corpus_report.family_for(pid))
except Exception as e:
    print(f"ERROR: could not profile {pid}: {type(e).__name__}: {e}")
    sys.exit(1)
PROFILE_FIELDS = ("native_domain", "computational_core", "certificate_form",
                  "object_regime", "domain_essentiality", "reduction_kind",
                  "track", "core_provenance")

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
    # Existing fields keep their order; the profile is appended after them.
    for f in PROFILE_FIELDS:
        rec[f] = profile[f]
    out.append(rec)

path = f"artifacts/{pid}.jsonl"
with open(path, "w") as f:
    for r in out: f.write(json.dumps(r) + "\n")
print(f"wrote {path}: {len(out)} instances (difficulty={name})"
      + (f"  [{bad} SKIPPED - planted failed!]" if bad else "")
      + (f"  [{dupes} duplicates resampled]" if dupes else ""))
print(f"  profile: domain={profile['native_domain']} core={profile['computational_core']} "
      f"cert={profile['certificate_form']} regime={profile['object_regime']} "
      f"[{profile['core_provenance']}]")

if os.path.isdir(f"results/{pid}"):
    meta.update(emit_master_seed=master, emit_tries=tries,
                emit_duplicate_rate=round(dupes / tries, 4) if tries else 0.0,
                emit_profile={k: profile[k] for k in PROFILE_FIELDS})
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
