#!/usr/bin/env bash
# Submit a finished paper.  Usage: scripts/submit.sh <arxiv_id>
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
ID="${1:?usage: scripts/submit.sh <arxiv_id> [--reject]}"
REJECT=""; [ "${2:-}" = "--reject" ] && REJECT=1
D="results/$ID"
[ -d "$D" ] || { echo "ERROR: $D missing."; exit 1; }

if [ -n "$REJECT" ]; then
  [ -f "$D/REJECTED.md" ] || { echo "ERROR: write $D/REJECTED.md explaining WHY first."; exit 6; }
  python3 -c "
import json,datetime,os
p='claims/$ID.json'
d=json.load(open(p)) if os.path.exists(p) else {'paper':'$ID'}
d['status']='rejected'
d['done_at']=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
json.dump(d,open(p,'w'))"
  rm -f "$D/.orkey" "$D/.task.md" "$D/.runner.sh"; rm -rf "$D/__pycache__"
  bash scripts/status.sh --write >/dev/null
  git add "$D" "claims/$ID.json" STATUS.md
  git commit -q -m "reject $ID"
  git pull -q --rebase origin main && bash scripts/status.sh --write >/dev/null && git add STATUS.md \
    && git commit -q --amend --no-edit && git push -q origin main && echo "REJECTED $ID (documented)" || {
    echo "push failed — run: git pull --rebase origin main && git push origin main"; exit 4; }
  exit 0
fi

MOD="$(ls "$D"/gen_*.py 2>/dev/null | head -1)"
[ -n "$MOD" ] || { echo "ERROR: no gen_*.py in $D — nothing to submit."; exit 2; }

# The builder writes these; a result nobody can read or re-check is not a result.
for f in README.md selftest_report.json llm_loop_transcript.jsonl; do
  [ -s "$D/$f" ] || { echo "ERROR: $D/$f missing or empty — see prompts/codex_task.md STEP 5."; exit 7; }
done
if [ "$(wc -l < "$D/README.md")" -lt 25 ]; then
  echo "ERROR: $D/README.md is too short to explain the task — see STEP 5."; exit 7
fi

# Gate results are the builder's to produce, but "the file exists" is not evidence
# it ran them.  G8 gets named explicitly: it is the one gate nothing downstream can
# reconstruct, because a canonical_key built on the seed or on hash(render(inst))
# passes the diversity count below while making it meaningless.
python3 - "$D/selftest_report.json" <<'PYGATE' || exit 7
import json, sys
try:
    rep = json.load(open(sys.argv[1]))
except Exception as e:
    print(f"ERROR: selftest_report.json is not readable JSON: {e}"); sys.exit(1)
if not isinstance(rep, dict):
    print("ERROR: selftest_report.json must be a JSON object"); sys.exit(1)
gates = {k: v for k, v in rep.items() if k.startswith("G") and k[1:2].isdigit()}
if not gates:
    print("ERROR: selftest_report.json records no G* gates — see STEP 3."); sys.exit(1)
failed = [k for k, v in sorted(gates.items())
          if not (isinstance(v, dict) and v.get("pass"))]
if failed:
    print("ERROR: gates not passing in selftest_report.json: " + ", ".join(failed)); sys.exit(1)
if rep.get("all_passed") is False:
    print("ERROR: selftest_report.json says all_passed=false"); sys.exit(1)
g5 = next((v for k, v in gates.items() if k.startswith("G5")), None)
if isinstance(g5, dict):
    import re as _re
    def _num(k):
        v = g5.get(k)
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    DENS = _re.compile(r"fraction|density|valid|solution|count|hits", _re.I)
    COST = _re.compile(r"second|node|iter|restart|wall|time|step|budget", _re.I)
    # A candidate-space cardinality is NOT a density: 2503.01929 reported a 1536-bit
    # space and fell to Algorithm X in 5s.  Require how MANY answers are valid, and
    # what the strongest attack actually cost.
    has_dens = any(DENS.search(k) and _num(k) for k in g5)
    has_cost = any(COST.search(k) and _num(k) for k in g5)
    if not (has_dens and has_cost):
        missing = ("density" if not has_dens else "") + \
                  (" and " if not has_dens and not has_cost else "") + \
                  ("baseline cost" if not has_cost else "")
        print(f"ERROR: G5 is missing {missing}.  Reporting the size of the candidate\n"
              "       space is not difficulty -- 2503.01929 reported a 1536-bit space,\n"
              "       passed G5, and fell to Algorithm X in five seconds.  Report how\n"
              "       many answers are valid at the SHIPPING preset (exact or sampled)\n"
              "       AND the measured cost of your strongest attack there.\n"
              "       See prompts/codex_task.md, G5.")
        sys.exit(1)
    nums = [v for k, v in g5.items()
            if k != "pass" and isinstance(v, (int, float)) and not isinstance(v, bool)]
    if not nums:
        print("ERROR: G5 reports no measured number.  enumerate_all returned None in\n"
              "       40/40 of the first shipped generators, so the sparsity gate never\n"
              "       fired -- 2503.01929 passed it with a 1536-bit space and fell to\n"
              "       Algorithm X in 5s.  Report an exact count, or a sampled density\n"
              "       estimate, AND the measured cost of your strongest attack.\n"
              "       See prompts/codex_task.md, G5.")
        sys.exit(1)
if not any(k.startswith("G8") for k in gates):
    print("ERROR: no G8 gate in selftest_report.json — canonical_key invariance was\n"
          "       never tested.  submit.sh counts distinct keys but cannot tell a real\n"
          "       invariant from a hash of the seed.  See prompts/codex_task.md, G8.")
    sys.exit(1)
# G6 must include the domain-standard attack, not only the three generic probes.
# 2408.04743 passed all eight gates AND the four-vendor oracle pool, then fell to a
# spectral attack on 20/20 instances -- the generic outlier/greedy/restart panel is
# blind to what is actually known about the problem class.
g6 = next((v for k, v in gates.items() if k.startswith("G6")), None)
atk = (g6 or {}).get("attacks")
n_atk = len(atk) if isinstance(atk, (dict, list)) else 0
if g6 is not None and not isinstance(atk, (dict, list)):
    print("ERROR: G6 does not report an 'attacks' object.  Report the panel as\n"
          "       {'pass': ..., 'attacks': {name: {'successes': n, 'attempts': m}, ...}}\n"
          "       so the panel can be checked mechanically -- see prompts/codex_task.md, G6.")
    sys.exit(1)
if n_atk and n_atk < 4:
    names = ", ".join(atk) if isinstance(atk, dict) else str(atk)
    print(f"ERROR: G6 reports only {n_atk} attacks ({names}).\n"
          "       The three generic probes are not sufficient on their own: run the\n"
          "       standard algorithm for the problem class too (SAT/ILP/spectral/LLL/\n"
          "       DLX -- see prompts/codex_task.md, G6). If you truly cannot run it,\n"
          "       record it as an attack entry saying so and name it in the README.")
    sys.exit(1)
print(f"== gates ==\n  {len(gates)} gates pass, G8 canonical_key present, "
      f"G6 panel = {n_atk or 'unknown'} attacks")
PYGATE

echo "== hardening transcript =="
python3 - "$D" <<'PY'
import json, os, sys
D = sys.argv[1]
try:
    meta = json.load(open(os.path.join(D, ".meta.json")))
except (OSError, ValueError):
    meta = {}
ver = meta.get("schema_version", 1)
rows = [json.loads(l) for l in open(os.path.join(D, "llm_loop_transcript.jsonl")) if l.strip()]

if ver < 2:
    # Built before scripts/harden.py existed: single fixed oracle, builder-authored
    # transcript.  Grandfathered rather than re-run, and tagged so that nobody has
    # to guess later which rules it was checked against.
    print(f"  schema_version={ver} (legacy, pre-harden.py) — {len(rows)} calls, not re-validated")
    sys.exit(0)

NEED = {"schema_version","model","effort","preset","params","seed","escalation_round",
        "solved","parsed","verify_ok","verify_reason","reply","error","elapsed_sec",
        "http_status","finish_reason"}
fail = []
for n, r in enumerate(rows, 1):
    missing = NEED - set(r)
    if missing:
        fail.append(f"line {n}: missing keys {sorted(missing)}")
if not rows:
    fail.append("transcript is empty")

models = {r.get("model") for r in rows}
if len(models) < 3:
    fail.append(f"only {len(models)} distinct oracle model(s) used: {sorted(models)} — "
                "the pool must be redrawn per call")
seeds = [r.get("seed") for r in rows]
if len(set(seeds)) != len(seeds):
    fail.append("repeated seeds — every attempt must use a distinct instance")
rounds = [r.get("escalation_round", 0) for r in rows]
cap = meta.get("max_escalations", 3)
if rounds and max(rounds) > cap:
    fail.append(f"escalation_round reached {max(rounds)}, above the cap of {cap}")
# The hardness claim rests on the level that held, not on the run as a whole:
# a transcript can show four vendors overall while the shipping level was decided
# by two of them.
verdict = meta.get("harden_verdict", {})
if verdict.get("verdict") == "hardened" and rows:
    top = max(rounds)
    deciders = {r.get("model") for r in rows
                if r.get("escalation_round") == top and r.get("solved") != "error"}
    want = min(3, len(meta.get("oracle_pool") or []) or 3)
    if len(deciders) < want:
        fail.append(f"the shipping level was decided by only {len(deciders)} distinct "
                    f"vendor(s) {sorted(deciders)}; the all-fail claim needs {want}")
if verdict.get("verdict") == "too_easy":
    fail.append("harden.py returned verdict too_easy — this family is given up on; "
                "write REJECTED.md and use: scripts/submit.sh <id> --reject")

if fail:
    print("TRANSCRIPT INVALID:")
    for f in fail: print("  -", f)
    sys.exit(1)
print(f"  {len(rows)} calls | {len(models)} distinct models | "
      f"{max(rounds)+1} difficulty level(s) | verdict "
      f"{meta.get('harden_verdict',{}).get('verdict')}")
PY
[ $? -eq 0 ] || { echo "SUBMIT BLOCKED — see prompts/codex_task.md STEP 4."; exit 8; }

echo "== interface check =="
python3 - "$MOD" <<'PY'
import importlib.util, json, sys
p=sys.argv[1]
s=importlib.util.spec_from_file_location("m",p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
need=["make_instance","render","parse_answer","verify","random_candidate","search_space",
      "enumerate_all","canonical_key","escalate"]
miss=[f for f in need if not callable(getattr(m,f,None))]
if miss: print("MISSING:", miss); sys.exit(1)
# The ladder is the same four rungs in every family.  harden.py walks DIFFICULTY
# in insertion order, so the order is the ladder; and the emitted "difficulty"
# field only means something across papers if the names mean the same thing.
# `demo` is the hand-scale rung: harden.py skips it and it must never ship.
D=getattr(m,"DIFFICULTY",None)
if not isinstance(D,dict) or list(D)!=["demo","easy","medium","hard"]:
    print("DIFFICULTY FAIL: expected exactly demo, easy, medium, hard in that order; got",
          list(D) if isinstance(D,dict) else repr(D)); sys.exit(1)
if getattr(m,"SHIPPING_DIFFICULTY",None) not in ("easy","medium","hard"):
    print("SHIPPING_DIFFICULTY FAIL: must be easy, medium or hard (never demo):",
          repr(getattr(m,"SHIPPING_DIFFICULTY",None))); sys.exit(1)
i=m.make_instance(**D[m.SHIPPING_DIFFICULTY], seed=0)
ok,why=m.verify(i, i["answer"])
if not ok: print("G1 FAIL: planted answer does not verify:", why); sys.exit(1)
# Can parse_answer consume real solver output?  The wire format is the module's
# own choice and often differs from the internal answer representation (binary
# strings vs ints, nested JSON vs a flat list), so guessing a rendering of
# inst["answer"] produces false failures.  Test the contract the renderer itself
# advertises: pull the example out of render() and require parse_answer to accept
# it.  That is format-agnostic and still independent of the builder's own gate.
def _parse_contract(mod, inst, ans):
    import re
    ex = re.findall(r"<answer>(.*?)</answer>", mod.render(inst), re.S)
    for body in reversed(ex):
        try:
            if mod.parse_answer(f"<answer>{body}</answer>") is not None:
                return True, "renderer example parses"
        except Exception:
            pass
    for body in [json.dumps(ans)] + ([", ".join(map(str, ans))]
                 if isinstance(ans, list) and all(isinstance(x,(int,float,str)) for x in ans) else []):
        try:
            if mod.parse_answer(f"<answer>{body}</answer>") == ans:
                return True, "planted answer round-trips"
        except Exception:
            pass
    return False, "parse_answer accepted neither the renderer example nor the planted answer"
rt, rt_why = _parse_contract(m, i, i["answer"])

# --- surrogate gate -------------------------------------------------------
# A geometry/analysis paper compiled down to an adjacency matrix passes every
# other check in this file: the module is correct, the gates pass, the oracle
# fails.  What is lost is the paper's mathematics, before the solver sees
# anything.  Observed live: an equiangular-lines paper (Gram matrices, Seidel
# matrices, interlacing) shipped as a 720-vertex graph whose verify() is
# documented "check any size-k clique" -- no vectors in the instance at all.
CL = getattr(m, "CERTIFICATE_LANGUAGE", None)
if not isinstance(CL, dict) or not CL.get("description") or "bounds" not in CL:
    print("ERROR: module has no CERTIFICATE_LANGUAGE {description, bounds}.\n"
          "       Requiring an integer search_space without a declared language\n"
          "       silently forces every answer to be a tuple of small ints: across\n"
          "       the first 40 shipped generators search_space was an int 40/40 and\n"
          "       None 0/40, with zero rational, polynomial or symbolic answers.\n"
          "       Bound the language instead -- see prompts/codex_task.md, STEP 1.")
    sys.exit(1)

NAT = getattr(m, "NATIVE", None)
if not isinstance(NAT, dict):
    print("ERROR: module has no NATIVE dict.  Declare what this family really is\n"
          "       (domain / core / objects / intuition / reduction) -- see\n"
          "       prompts/codex_task.md, STEP 1.")
    sys.exit(1)
missing = [k for k in ("domain", "core", "objects", "intuition", "reduction")
           if k not in NAT]
if missing:
    print(f"ERROR: NATIVE is missing {missing} -- see prompts/codex_task.md, STEP 1.")
    sys.exit(1)

CONTINUOUS = {"geometry", "analysis", "dynamics", "optimization"}
DISCRETE_CORE = {"graph", "csp_sat", "exact_cover", "subset_sum", "permutation"}
keys = " ".join(k for k in i if k != "answer").lower()
graphy = any(w in keys for w in ("adjac", "edges", "neighb", "vertex", "vertic", "conflict"))

if graphy and NAT["core"] not in DISCRETE_CORE:
    print(f"ERROR: the solver is handed {sorted(k for k in i if k != 'answer')},\n"
          f"       which is a graph, but NATIVE['core'] says {NAT['core']!r}.\n"
          "       Label the core by what the solver actually searches.")
    sys.exit(1)

if NAT["domain"] in CONTINUOUS and NAT["core"] in DISCRETE_CORE and not NAT["reduction"]:
    print(f"ERROR: NATIVE says domain={NAT['domain']!r} but core={NAT['core']!r} with\n"
          "       reduction=None.  A continuous-domain paper rendered as a discrete\n"
          "       search is a discretised analogue: either build the family in the\n"
          "       paper's own objects, or set NATIVE['reduction'] to the section that\n"
          "       licenses the surrogate.  See prompts/codex_task.md, STEP 0.")
    sys.exit(1)

_track = "discretised analogue" if NAT["reduction"] else "native"
print(f"== native check ==\n  domain={NAT['domain']} core={NAT['core']} "
      f"intuition={NAT['intuition']} [{_track}]")
# --------------------------------------------------------------------------
# canonical_key must be a function of the instance, not of the call.  A key that
# is not deterministic cannot detect a duplicate; we cannot check the harder
# property (invariance under relabelling) without family-specific machinery, so
# the README caveats have to carry that one.
params = m.DIFFICULTY[m.SHIPPING_DIFFICULTY]
k1 = m.canonical_key(m.make_instance(**params, seed=4242))
k2 = m.canonical_key(m.make_instance(**params, seed=4242))
if not isinstance(k1,str) or k1 != k2:
    print("canonical_key FAIL: not deterministic or not a str:", repr(k1), repr(k2)); sys.exit(1)
if m.canonical_key(m.make_instance(**params, seed=4243)) == k1:
    print("canonical_key FAIL: two different seeds collide — the key ignores the instance"); sys.exit(1)
print(f"  interface OK | planted verifies | parse_answer: {rt} ({rt_why}) | canonical_key deterministic")
PY
[ $? -eq 0 ] || { echo "SUBMIT BLOCKED — fix the module first."; exit 3; }

rm -f "$D/.orkey" "$D/.task.md" "$D/.runner.sh"; rm -rf "$D/__pycache__"
echo "== emitting sample instances =="
bash scripts/emit.sh "$ID" "${EMIT_N:-20}" || { echo "SUBMIT BLOCKED — emit failed."; exit 5; }

# emit.sh already resamples past duplicates; this re-checks the file it produced,
# so the thing that generates the instances is not the only thing that vouches
# for them.
echo "== diversity =="
python3 - "$MOD" "artifacts/$ID.jsonl" <<'PY'
import importlib.util, json, sys
mod_path, art = sys.argv[1], sys.argv[2]
s = importlib.util.spec_from_file_location("m", mod_path)
m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
recs = [json.loads(l) for l in open(art) if l.strip()]
keys = [m.canonical_key(m.make_instance(**r["params"])) for r in recs]
dupes = len(keys) - len(set(keys))
if dupes:
    print(f"  {dupes} duplicate instance(s) out of {len(keys)} — isomorphic problems in "
          f"the dataset"); sys.exit(1)
print(f"  {len(set(keys))}/{len(keys)} distinct canonical keys")
PY
[ $? -eq 0 ] || { echo "SUBMIT BLOCKED — duplicate instances."; exit 9; }


python3 -c "
import json,os,datetime
p='claims/$ID.json'
d=json.load(open(p)) if os.path.exists(p) else {'paper':'$ID'}
d['status']='done'
d['done_at']=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
json.dump(d, open(p,'w'))"
bash scripts/status.sh --write >/dev/null
git add "$D" "artifacts/$ID.jsonl" "claims/$ID.json" STATUS.md
git commit -q -m "result $ID"
# STATUS.md is generated: on conflict, regenerate rather than merge
git pull -q --rebase origin main 2>/dev/null || { git checkout --ours STATUS.md 2>/dev/null; git add STATUS.md 2>/dev/null; git rebase --continue >/dev/null 2>&1 || true; }
bash scripts/status.sh --write >/dev/null; git add STATUS.md
git diff --cached --quiet 2>/dev/null || git commit -q --amend --no-edit 2>/dev/null
git push -q origin main && echo "SUBMITTED $ID" || {
  echo "push failed — run: git pull --rebase origin main && git push origin main"; exit 4; }
