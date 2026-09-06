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

  # A cap_bound paper must not be rejected.  scripts/harden.py now DETECTS this
  # rather than waiting for escalate() to declare it: if the ladder stopped with the
  # answer near the output cap, or never moved more than one dial, the binding
  # constraint was our answer FORMAT, not the paper.  2601.05272 climbed n=64..84,
  # stopped at 249 atoms against a 256 cap, reported "cannot be made harder", and was
  # rejected.  Instruction alone did not prevent that; this guard does.
  # A G9(b) rejection blames the PAPER for a result produced by the builder's own
  # hint.  Measured over the 17 modules on disk that carry a STRUCTURAL_HINT: 4 of 9
  # rejected papers hand the solver a procedure, against 1 of 8 accepted.  This gate
  # only ever runs on --reject, so that one accepted paper is never touched by it.
  #
  # 1904.00563 is the pattern: "Among target-one vertices, keep edges whose endpoints
  # have equal eligible degree; the result is three even cycles, so take alternating
  # edges on each."  That is the whole algorithm, including the derived count and the
  # final step.  The hinted oracle solving it says nothing about the paper.
  python3 - "$D" <<'PYHINT' || exit 6
import ast, glob, re, sys, os
d = sys.argv[1]
rj = os.path.join(d, "REJECTED.md")
try:
    note = open(rj, encoding="utf-8", errors="ignore").read()
except OSError:
    sys.exit(0)
# only gate rejections that actually turn on G9
if not re.search(r"G9\(b\)|G9\b", note):
    sys.exit(0)
# G9(b) stopped being a gate on 2026-09-05, so a rejection that turns on it is no
# longer a valid rejection at all -- regardless of how the hint was written. Refuse
# it outright when G9(b) is named as the deciding reason.
if re.search(r"fails?\s+\*{0,2}(H|hardness)?\*{0,2}[^.]{0,60}G9\(b\)|G9\(b\)[^.]{0,40}(gate|fail)"
             r"|rejected?[^.]{0,60}G9\(b\)", note, re.I):
    print("ERROR: this rejection turns on G9(b), the polarity-flipped hinted-oracle gate.")
    print("       G9(b) was retired to a DIAGNOSTIC on 2026-09-05: a family that")
    print("       dissolves when you name the trick is one whose difficulty lies in")
    print("       FINDING the insight, which is what this corpus is for. It cost 8")
    print("       rejections and 23 blocked papers, 6 of which had already defeated")
    print("       the four-vendor no-tool pool.")
    print("       If the family passed G, V and STEP 4, SHIP IT. Record the hinted arm")
    print("       in the README as a diagnostic. See prompts/codex_task.md G9(b).")
    sys.exit(1)

hint = None
for f in glob.glob(os.path.join(d, "*gen_*.py")):
    try:
        tree = ast.parse(open(f, encoding="utf-8", errors="ignore").read())
    except Exception:
        continue
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id == "STRUCTURAL_HINT":
                    try:
                        hint = " ".join(str(ast.literal_eval(n.value)).split())
                    except Exception:
                        pass
    if hint:
        break
if not hint:
    sys.exit(0)                      # no module or no hint kept: cannot check
CHAIN = re.compile(r";\s*(the\s+)?\w+|,\s*then\b|\bthen\b|\bso (take|use|apply|read|pick|choose)\b"
                   r"|\bbefore using\b|\bfirst,|\bnext,|\bfinally\b", re.I)
DERIVED = re.compile(r"\bthe result is\b|\bthis (gives|yields|produces)\b|\byou (get|obtain)\b"
                     r"|\bthere are (two|three|four|five|\d+)\b|\bexactly (two|three|four|\d+)\b", re.I)
bad = []
if CHAIN.search(hint):
    bad.append("it chains a SECOND step (\"then\" / \"; ...\" / \"so take\" / \"first,\")")
if DERIVED.search(hint):
    bad.append("it hands over a DERIVED FACT the solver was supposed to find "
               "(\"the result is ...\", \"there are three ...\")")
if not bad:
    sys.exit(0)
print("ERROR: this rejection cites G9, but the STRUCTURAL_HINT is a PROCEDURE, not a")
print("       structural hint, so G9(b) measured your hint and not the paper.")
print(f"       hint: {hint[:200]}")
for b in bad:
    print(f"       - {b}")
print("       A structural hint names the INVARIANT a solver has to notice -- the thing")
print("       to look at. It does not say what to do with it, does not chain steps, and")
print("       does not state a quantity the solver was supposed to derive.")
print("       Rewrite the hint to name only the invariant, re-run the G9(b) arm, and")
print("       reject only if the family still dissolves. See prompts/codex_task.md G9(b).")
sys.exit(1)
PYHINT

  python3 - "$D/.meta.json" <<'PYCAP' || exit 6
import json, sys
try:
    v = (json.load(open(sys.argv[1])) or {}).get("harden_verdict") or {}
except Exception:
    sys.exit(0)                       # no verdict recorded; nothing to contradict
if v.get("verdict") not in ("cap_bound", "budget_bound"):
    sys.exit(0)
if v.get("verdict") == "budget_bound":
    print("ERROR: the oracle harness recorded verdict=budget_bound for this paper.")
    print("       The ladder ran out of ESCALATIONS while escalate() was still willing")
    print(f"       to climb ({v.get('escalate_says')}); the binding constraint was this")
    print("       harness's budget, not the paper.  7 of 13 too_easy verdicts on disk")
    print("       were this, including 1612.03280, which stopped at n=149 with five")
    print("       more levels available.  PARK it -- delete REJECTED.md and re-run with")
    print("       ORACLE_MAX_ESCALATIONS raised, or ship at a higher preset.")
    sys.exit(1)
print("ERROR: the oracle harness recorded verdict=cap_bound for this paper, which")
print("       means the ANSWER CAP stopped the ladder, not the mathematics.")
a, c = v.get("answer_atoms"), v.get("answer_chars")
if a is not None:
    print(f"       answer at the last level: {a} atoms / {c} chars "
          f"(cap {v.get('atom_cap')} atoms / {v.get('char_cap')} chars)")
print(f"       dials the ladder ever moved: {v.get('axes_moved') or 'none'}")
sig = v.get("signal", "")
if "single_axis" in sig and "answer_cap" not in sig:
    print("       signal=single_axis: the answer is still small -- this family was never")
    print("       explored, not exhausted. Turn a SECOND dial before giving it up.")
print("       PARK it -- delete REJECTED.md and leave the claim in_progress.  Harden")
print("       at FIXED ANSWER LENGTH instead: grow the haystack, not the needle.")
print("       Bigger ground set with the same witness size, larger modulus, denser")
print("       decoys, tighter constraints.  See prompts/codex_task.md, escalate().")
sys.exit(1)
PYCAP

  # A rejection that says only "an efficient method exists" is not reviewable, and an
  # independent audit found 7 of 12 such rejections were WRONG -- the papers were
  # buildable on Track B. One was dismissed for having "a short linear formula" while
  # its mechanical alternative was 16,689,170 lattice-vector enumerations. If the note
  # rests on a method existing, it must quantify the gap it is claiming is too small.
  python3 - "$D/REJECTED.md" <<'PYREJ' || exit 6
import re, sys
t = open(sys.argv[1], encoding="utf-8", errors="ignore").read()
low = t.lower()
METHOD_EXISTS = re.compile(
    r"polynomial[- ]time|explicit (construction|formula)|closed[- ]form|"
    r"constructive (solution|procedure|algorithm)|efficient algorithm|"
    r"linear solve|spectral characteri|classification (table|of)|is in p|"
    r"algorithm (exists|is given)|buchberger|gaussian elimination|sdp", re.I)
if not METHOD_EXISTS.search(low):
    sys.exit(0)                       # rejected for some other reason; nothing to check
has_mech = re.search(r"mechanical|brute[- ]force cost|operations|enumerat|seconds|"
                     r"cost|running time", low)
has_compact = re.search(r"compact route|shortcut|by hand|no shorter|"
                        r"same length|nothing to see|track b", low)
if has_mech and has_compact:
    sys.exit(0)
print("ERROR: this rejection rests on 'an efficient method exists', which is NOT by")
print("       itself a reason to reject -- that is what TRACK B is for.  State the")
print("       MECHANICAL COST (operations the standard method needs at shipping size)")
print("       and the COMPACT ROUTE length, and show the gap is too small to test")
print("       anything.  7 of 12 audited rejections of this shape were wrong.")
print("       See prompts/codex_task.md, STEP 0 item 4.")
sys.exit(1)
PYREJ
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
# G9(b) -- the polarity-flipped hinted gate -- was retired to a diagnostic on
# 2026-09-05. It had become the pipeline's largest loss mechanism: 8 rejections and
# 23 blocked papers, six of which had already DEFEATED the four-vendor no-tool pool
# at their shipping preset. Its premise was also wrong: a family that dissolves when
# you name the trick is one whose difficulty lies in FINDING the insight, which is
# what this corpus is for.
#
# G9's `pass` folds (a) the three-arm diagnostic, (b) that retired gate, and (c) the
# size/effort caps into one flag. Only (c) still gates, so recompute it from the
# measured numbers rather than trust a flag that may still encode the retired rule.
g9key = next((k for k in gates if k.startswith("G9")), None)
if g9key:
    g9 = gates[g9key]
    caps = g9.get("caps") if isinstance(g9.get("caps"), dict) else {}
    def _num(d, k):
        v = d.get(k)
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None
    # POLICY caps, applied regardless of what the module records in its own `caps`
    # block. A module must not set the bar it is judged against -- several record
    # caps.operations=300 simply because that was the figure in the prompt when they
    # were written, and honouring a stale self-reported cap would keep enforcing a
    # retired policy after it changed.
    #
    # The route cap went 300 -> 1000 on 2026-09-06. Its purpose is to exclude families
    # whose intended method is a CALCULATOR TEST -- "thousands of arithmetic
    # operations" in G9(c)'s own words -- not to exclude one that needs a few hundred.
    # It was blocking 1905.11021 at 343 ops, where six unknowns is the structural floor
    # for a cubic norm form over a degree-3 extension, and 2205.13442 at 967.
    POLICY_CAPS = {"chars": 2000, "elements": 256, "operations": 1000}
    over = []
    for field, capkey in (("answer_chars", "chars"),
                          ("answer_elements", "elements"),
                          ("intended_route_operations", "operations")):
        got = _num(g9, field)
        cap = POLICY_CAPS[capkey]
        if got is not None and got > cap:
            over.append(f"{field}={got} > {cap}")
    gates[g9key] = {**g9, "pass": not over}
    if over:
        print("ERROR: G9(c) size/effort caps exceeded: " + "; ".join(over))
        print("       (G9(b), the hinted-oracle gate, is a diagnostic and no longer blocks.)")
        sys.exit(1)

failed = [k for k, v in sorted(gates.items())
          if not (isinstance(v, dict) and v.get("pass"))]
if failed:
    print("ERROR: gates not passing in selftest_report.json: " + ", ".join(failed)); sys.exit(1)
# `all_passed` is the BUILDER's summary and still folds in G9(b), so a module that
# only failed the retired gate reports all_passed=false. Trusting it here would
# re-block exactly the papers this change is meant to release; the per-gate check
# above is authoritative.
if rep.get("all_passed") is False and not failed:
    print("  note: builder reported all_passed=false, but every gate that still gates"
          " passes (G9(b) is retired).")
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
# The pass flag is self-reported.  Recompute from the numbers that are already on
# disk: a panel that records a successful attack has broken its own family, whatever
# the flag says.  Observed live: 2410.07666 recorded
# random_restart_walksat_32x200n successes=8/8 -- it honestly set pass=false, but
# nothing here would have caught it if it had not.
_wins = []
if isinstance(atk, dict):
    for _name, _res in atk.items():
        _s = _res.get("successes") if isinstance(_res, dict) else None
        _a = _res.get("attempts") if isinstance(_res, dict) else None
        if isinstance(_s, (int, float)) and _s > 0:
            _wins.append(f"{_name} {_s}/{_a}")
if _wins:
    print("ERROR: G6 records a SUCCESSFUL attack: " + "; ".join(_wins) + "\n"
          "       The family is solved by its own adversary panel.  Escalate the\n"
          "       parameters or reject the paper -- do not ship it.")
    sys.exit(1)
print(f"== gates ==\n  {len(gates)} gates pass, G8 canonical_key present, "
      f"G6 panel = {n_atk or 'unknown'} attacks, 0 attack successes")
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

# The requirement is that the pool was genuinely redrawn, not that some fixed number
# of vendors exists. Hardcoding 3 made a smaller pool unshippable: with the 2-model
# pool adopted 2026-09-05 EVERY transcript would have failed this line while the
# modules themselves were fine -- the same shape as the answer cap and the escalation
# budget, a constant of OURS reported as a defect in the work.
pool = meta.get("oracle_pool") or []
need = min(3, len(pool)) if pool else 2
models = {r.get("model") for r in rows}
if len(models) < need:
    fail.append(f"only {len(models)} distinct oracle model(s) used: {sorted(models)} — "
                f"the recorded pool has {len(pool) or 'an unknown number of'} model(s), so "
                f"at least {need} distinct must appear; the pool must be redrawn per call")
seeds = [r.get("seed") for r in rows]
if len(set(seeds)) != len(seeds):
    fail.append("repeated seeds — every attempt must use a distinct instance")
rounds = [r.get("escalation_round", 0) for r in rows]
# Track harden.py's own default, not a frozen number. When MAX_ESCALATIONS went
# 3 -> 6 this stayed at 3, so a run whose .meta.json lost its fields (the G9 arms
# overwrite it) was blocked for "escalation_round reached 5, above the cap of 3" --
# a cap that never applied to that run.
cap = meta.get("max_escalations") or int(os.environ.get("ORACLE_MAX_ESCALATIONS", "6"))
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
import importlib.util, json, os, re, sys
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
    try:
        _json_body = json.dumps(ans)
    except TypeError as e:
        return False, (f"answer is not JSON-native ({e}). Represent rationals as "
                       "[num, den] and monomials as exponent lists -- see STEP 1")
    for body in [_json_body] + ([", ".join(map(str, ans))]
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

# escalate() decides whether a paper lives: when the oracle solves a level the
# harness climbs the ladder, and a one-dial ladder that only raises n runs into the
# output cap and returns None, which the harness reports as too_easy. 33 of 54
# shipped modules moved exactly one axis. Require a second.
import inspect as _inspect
try:
    _esc = _inspect.getsource(m.escalate)
except Exception:
    _esc = ""
if _esc:
    _axes = set(re.findall(r"[\"']([a-z_][a-z0-9_]*)[\"']\s*\]\s*=", _esc))
    _axes |= set(re.findall(r"\bp(?:arams)?\[[\"']([a-z_][a-z0-9_]*)[\"']\]", _esc))
    _axes.discard("_preset")
    if _axes and _axes <= {"n"} and "cap_bound" not in _esc:
        print("ERROR: escalate() moves only 'n'.  Raising n lengthens the ANSWER and\n"
              "       runs into the output cap, at which point the harness reports\n"
              "       too_easy and the paper is discarded -- 10 papers were lost that\n"
              "       way.  Add an axis that raises difficulty at FIXED answer length\n"
              "       (bigger ground set with the same witness size, larger modulus,\n"
              "       denser decoys, tighter constraints), or return \"cap_bound\".\n"
              "       See prompts/codex_task.md, escalate().")
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
# Read what the SOLVER is actually shown, not the dict key names -- renaming
# "edges" to "pairs" was enough to evade this entirely.  Mirrored in
# scripts/corpus_report.py; the gate and the report must never disagree.
#
# These are WORD-BOUNDED regexes, not substrings.  Plain substring "graph" matched
# "crypto-graph-ic" and blocked 1912.02640, a finite-field polynomial_identity
# module, on the word "cryptographic" in its own problem statement -- and would
# have blocked every crypto paper that ever says so, which is exactly the
# under-represented family this corpus needs.  "degree of" matched "degree of the
# polynomial" for the same reason and is now pinned to a graph noun.
# Split by how much each word actually proves. Reading render() is right -- renaming
# "edges" to "pairs" evaded a keys-only test -- but ONE ambiguous word in prose is not
# evidence of a graph. Of the 11 papers this gate blocked on 2026-09-06, at least 7 were
# ordinary algebraic prose: "incidence vector belongs to the row span", "every adjacent
# pair swapped", "finite projective vertex", "swapping adjacent disjoint cycles".
GRAPH_STRONG = (
    r"\b(?:sub|multi|di|hyper)?graphs?\b", r"\bcliques?\b", r"\bedges?\b",
    r"\badjacency\b", r"\bneighbou?rs?\b",
)
GRAPH_WEAK = (
    r"\badjacent\b", r"\binciden(?:t|ce)\b", r"\bvert(?:ex|ices)\b",
    r"\bconflict", r"\bdegree of (?:a |the )?(?:vertex|vertices|node|nodes)\b",
)


def _is_graphy(text):
    if any(re.search(w, text) for w in GRAPH_STRONG):
        return True
    return sum(1 for w in GRAPH_WEAK if re.search(w, text)) >= 2
try:
    _shown = m.render(i).lower()
except Exception:
    _shown = ""
keys = (" ".join(k for k in i if k != "answer") + " " + _shown).lower()
graphy = _is_graphy(keys)

# A graphy INSTANCE is not the same as a graph-cored PROBLEM. The guard exists to
# catch a module that hands the solver a graph to search while declaring a
# non-discrete core. But a graph can also be scaffolding -- 1604.02195 prescribes a
# matrix's zero-pattern by a path and asks for the rational ENTRIES; the solver never
# searches the graph. Distinguish by whether the ANSWER indexes the graph: a genuine
# graph certificate is vertex/edge indices, all inside [0, max_vertex].
def _answer_indexes_graph(inst, ans):
    # Only GRAPH-NAMED keys define the vertex set. Scanning every list-of-pairs key
    # was wrong: 1604.02195 publishes characteristic polynomials p and q as coefficient
    # lists, whose range [-557573, 63127] swallowed the real vertex range [0, 7] and
    # made every rational answer look like a vertex index.
    VKEY = re.compile(r"edge|adjac|neighbou?r|arc|incidence|vertic|vertex|graph", re.I)
    verts = set()
    for k, v in inst.items():
        if k == "answer" or not isinstance(v, (list, tuple)) or not VKEY.search(k):
            continue
        for e in v:
            if isinstance(e, (list, tuple)) and len(e) == 2 and all(
                    isinstance(x, int) and not isinstance(x, bool) for x in e):
                verts.update(e)
    if not verts:
        return True                     # cannot tell -- keep the old, stricter behaviour
    lo, hi = min(verts), max(verts)
    flat = []
    def walk(a):
        if isinstance(a, dict): [walk(x) for x in a.values()]
        elif isinstance(a, (list, tuple)): [walk(x) for x in a]
        else: flat.append(a)
    walk(ans)
    if not flat:
        return True
    return all(isinstance(x, int) and not isinstance(x, bool) and lo <= x <= hi
               for x in flat)

if graphy and NAT["core"] not in DISCRETE_CORE:
    if _answer_indexes_graph(i, i.get("answer")):
        print(f"ERROR: the solver is handed {sorted(k for k in i if k != 'answer')},\n"
              f"       which is a graph, and the ANSWER indexes it, but NATIVE['core']\n"
              f"       says {NAT['core']!r}.  Label the core by what the solver searches.")
        sys.exit(1)
    print("  note: instance is graphy but the answer does not index the graph "
          f"(core {NAT['core']!r} accepted -- the graph is scaffolding, not the search space)")

# The old guard was NAT["domain"] in CONTINUOUS -- unreachable, because the prompt
# tells builders to set domain by what the SOLVER reasons about, so an honest
# geometry->graph reduction declares domain="combinatorics" and the gate never fired.
# Measured: 0 of 7 NATIVE modules could ever trip it.  Guard on the paper's own arXiv
# categories instead; the builder does not choose those.
NON_DISCRETE_CATS = {
    "math.AG","math.AC","math.RA","math.QA","math.RT","cs.SC",      # symbolic/algebraic
    "math.MG","math.DG","math.GT","math.AT","cs.CG",                # geometric
    "math.OC","math.DS","math.NA","math.AP","math.CA","math.FA",    # analytic/dynamic
    "math.PR","math-ph","math.SP","eess.SY","cs.SY",
}
_pid = os.path.basename(os.path.dirname(os.path.abspath(p)))
_cats = set()
try:
    for _line in open("papers/papers.jsonl"):
        _r = json.loads(_line)
        if _r.get("arxiv_id") == _pid:
            _cats = set(_r.get("all_cats", "").split()); break
except OSError:
    pass
_paper_is_non_discrete = bool(_cats & NON_DISCRETE_CATS)

if _paper_is_non_discrete and NAT["core"] in DISCRETE_CORE and not NAT["reduction"]:
    print(f"ERROR: {_pid} is categorised {sorted(_cats & NON_DISCRETE_CATS)} but ships\n"
          f"       core={NAT['core']!r} with reduction=None.  A non-discrete paper\n"
          "       rendered as a discrete search is a discretised analogue: either\n"
          "       build the family in the paper's own objects, or name the section\n"
          "       that licenses the surrogate in NATIVE['reduction'] (or\n"
          "       PROBLEM_PROFILE['reduction']['citation']).  See STEP 0.")
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
