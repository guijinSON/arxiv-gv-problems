#!/usr/bin/env python3
"""Render one sample question from every shipped generator.

Usage: python3 scripts/samples.py [seed] [per_module_timeout_s]

Writes samples/SAMPLES.md (human) and samples/samples.jsonl (machine). Each
module runs in its own subprocess so one slow or wedged generator cannot stall
the batch, and every sample is verified with the module's own verify() before it
is written -- a sample we cannot grade is not a sample.
"""
import json, os, subprocess, sys, glob, textwrap

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 42
TIMEOUT = int(sys.argv[2]) if len(sys.argv) > 2 else 120

CHILD = r'''
import importlib.util, json, sys
path, seed = sys.argv[1], int(sys.argv[2])
s = importlib.util.spec_from_file_location("m", path)
m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
D = getattr(m, "DIFFICULTY", {}) or {}
name = getattr(m, "SHIPPING_DIFFICULTY", None) or next(iter(D), None)
params = D.get(name, {})
inst = m.make_instance(seed=seed, **params)
q = m.render(inst)
ans = inst.get("answer")
ok, why = m.verify(inst, ans)
out = {"preset": name, "params": params, "question": q,
       "answer": ans, "verified": bool(ok), "verify_reason": why}
try:
    sp = m.search_space(inst)
    out["search_space"] = str(sp) if sp is not None else None
except Exception:
    out["search_space"] = None
try:
    out["canonical_key"] = str(m.canonical_key(inst))[:80]
except Exception:
    pass
print("<<<JSON>>>" + json.dumps(out, default=str))
'''

papers = {}
for line in open("papers/papers.jsonl"):
    r = json.loads(line); papers[r["arxiv_id"]] = r

mods = sorted(glob.glob("results/*/gen_*.py"))
os.makedirs("samples", exist_ok=True)
rows, failed = [], []

for mp in mods:
    pid = os.path.basename(os.path.dirname(mp))
    try:
        p = subprocess.run([sys.executable, "-c", CHILD, mp, str(SEED)],
                           capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        failed.append((pid, f"timed out after {TIMEOUT}s")); continue
    tag = "<<<JSON>>>"
    if tag not in p.stdout:
        err = (p.stderr.strip().splitlines() or ["no output"])[-1]
        failed.append((pid, err[:160])); continue
    d = json.loads(p.stdout.split(tag, 1)[1])
    d["paper"] = pid
    rec = papers.get(pid, {})
    d["title"] = rec.get("title", "").replace("\n", " ").strip()
    d["family"] = rec.get("family", "")
    d["url"] = rec.get("url", f"https://arxiv.org/abs/{pid}")
    rows.append(d)
    print(f"  {pid:12} {d['preset']:10} verified={d['verified']}  "
          f"{len(d['question']):>6} chars")

with open("samples/samples.jsonl", "w") as f:
    for d in rows:
        f.write(json.dumps(d, default=str) + "\n")

def clip(q, head=45, tail=12):
    L = q.splitlines()
    if len(L) <= head + tail + 3:
        return q
    n = len(L) - head - tail
    return "\n".join(L[:head] + ["", f"    ... [{n} lines of instance data omitted] ...", ""] + L[-tail:])

with open("samples/SAMPLES.md", "w") as f:
    f.write("# One sample question per generator\n\n")
    f.write(f"Rendered from every shipped generator at its **shipping** preset, "
            f"seed `{SEED}`. Each planted answer was checked with the module's own "
            f"`verify()` before inclusion.\n\n")
    f.write(f"- generators rendered: **{len(rows)}**\n")
    f.write(f"- all planted answers verify: **{all(d['verified'] for d in rows)}**\n")
    if failed:
        f.write(f"- failed to render: {len(failed)} — {', '.join(p for p, _ in failed)}\n")
    f.write("\nFull, untruncated questions and answers are in "
            "[`samples.jsonl`](samples.jsonl); long instance data is elided below "
            "only for readability.\n\n---\n\n")
    for d in sorted(rows, key=lambda r: r["paper"]):
        f.write(f"## {d['paper']} — {d['title']}\n\n")
        f.write(f"*{d['family']}* · [paper]({d['url']}) · preset `{d['preset']}` "
                f"`{json.dumps(d['params'])}`")
        if d.get("search_space"):
            ss = d["search_space"]
            f.write(f" · search space ≈ `{ss if len(ss)<28 else ss[:8]+'…('+str(len(ss))+' digits)'}`")
        f.write("\n\n```text\n" + clip(d["question"]).rstrip() + "\n```\n\n")
        a = json.dumps(d["answer"], default=str)
        f.write("**Answer** " + ("(verified ✓)" if d["verified"] else "(FAILED VERIFY)") + ":\n\n")
        f.write("```json\n" + (a if len(a) <= 1400 else a[:1400] + f"  … ({len(a)} chars total)") + "\n```\n\n---\n\n")

print(f"\nwrote samples/SAMPLES.md and samples/samples.jsonl: {len(rows)} samples")
if failed:
    print(f"failed ({len(failed)}):")
    for pid, e in failed:
        print(f"  {pid}: {e}")
