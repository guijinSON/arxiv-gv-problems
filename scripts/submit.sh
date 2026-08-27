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
  rm -f "$D/.orkey"; rm -rf "$D/__pycache__"
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

echo "== interface check =="
python3 - "$MOD" <<'PY'
import importlib.util, sys
p=sys.argv[1]
s=importlib.util.spec_from_file_location("m",p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
need=["make_instance","render","parse_answer","verify","random_candidate","search_space","enumerate_all"]
miss=[f for f in need if not callable(getattr(m,f,None))]
if miss: print("MISSING:", miss); sys.exit(1)
i=m.make_instance(**(getattr(m,"DIFFICULTY",{}).get(getattr(m,"SHIPPING_DIFFICULTY","medium"),{"n":12})), seed=0)
ok,why=m.verify(i, i["answer"])
if not ok: print("G1 FAIL: planted answer does not verify:", why); sys.exit(1)
rt = m.parse_answer(f"<answer>{', '.join(map(str,i['answer']))}</answer>") == i["answer"] \
     if isinstance(i["answer"], list) else True
print("  interface OK | planted verifies | parse round-trip:", rt)
PY
[ $? -eq 0 ] || { echo "SUBMIT BLOCKED — fix the module first."; exit 3; }

rm -f "$D/.orkey"; rm -rf "$D/__pycache__"
echo "== emitting sample instances =="
bash scripts/emit.sh "$ID" "${EMIT_N:-20}" || { echo "SUBMIT BLOCKED — emit failed."; exit 5; }

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
git pull -q --rebase origin main 2>/dev/null || { git checkout --ours STATUS.md 2>/dev/null; git add STATUS.md; git rebase --continue 2>/dev/null || true; }
bash scripts/status.sh --write >/dev/null; git add STATUS.md
git diff --cached --quiet || git commit -q --amend --no-edit
git push -q origin main && echo "SUBMITTED $ID" || {
  echo "push failed — run: git pull --rebase origin main && git push origin main"; exit 4; }
