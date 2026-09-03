#!/usr/bin/env python3
"""Report the shipped corpus by native domain and computational core.

An aggregate count hides the failure this exists to catch: a benchmark can look
domain-diverse while every problem is internally graph search.  Modules that
declare NATIVE are reported as declared; older modules get a core DERIVED from
what the solver is actually handed, which is the same signal the submit gate uses.

    python3 scripts/corpus_report.py            # summary
    python3 scripts/corpus_report.py --rows     # one line per paper
"""
import glob, importlib.util, json, os, re, sys, warnings
from collections import Counter

warnings.filterwarnings("ignore")

GRAPHY = ("adjac", "edges", "neighb", "vertex", "vertic", "conflict", "incid")
ASSIGN = ("clause", "assign", "variab", "literal", "colour", "color", "constraint")
COVER = ("lengths", "items", "weights", "subset", "blocks", "target", "capacit")


def derive_core(inst):
    keys = " ".join(k for k in inst if k != "answer").lower()
    if any(w in keys for w in GRAPHY):
        return "graph"
    if any(w in keys for w in ASSIGN):
        return "csp_sat"
    if any(w in keys for w in COVER):
        return "exact_cover"
    return "other"


def main():
    show_rows = "--rows" in sys.argv
    papers = {}
    for line in open("papers/papers.jsonl"):
        r = json.loads(line)
        papers[r["arxiv_id"]] = r

    done = []
    for f in glob.glob("claims/*.json"):
        d = json.load(open(f))
        if d.get("status") == "done":
            done.append(d["paper"])

    rows = []
    for pid in sorted(done):
        mods = glob.glob(f"results/{pid}/gen_*.py")
        if not mods:
            continue
        try:
            s = importlib.util.spec_from_file_location("m", mods[0])
            m = importlib.util.module_from_spec(s)
            s.loader.exec_module(m)
            inst = m.make_instance(seed=1, **m.DIFFICULTY[m.SHIPPING_DIFFICULTY])
        except Exception as e:
            rows.append((pid, "?", "?", "load-failed", str(e)[:40]))
            continue
        nat = getattr(m, "NATIVE", None)
        if isinstance(nat, dict):
            rows.append((pid, nat.get("domain", "?"), nat.get("core", "?"),
                         "declared" if not nat.get("reduction") else "analogue",
                         nat.get("intuition", "")))
        else:
            rows.append((pid, papers.get(pid, {}).get("family", "?"),
                         derive_core(inst), "derived", ""))

    print(f"shipped generators: {len(rows)}\n")
    core = Counter(r[2] for r in rows)
    tot = sum(core.values()) or 1
    print("=== computational core ===")
    for c, n in core.most_common():
        bar = "#" * int(40 * n / tot)
        print(f"  {n:3} ({100*n/tot:5.1f}%)  {c:<14} {bar}")
    disc = sum(n for c, n in core.items()
               if c in ("graph", "csp_sat", "exact_cover", "subset_sum", "permutation"))
    print(f"\n  discrete-search core: {disc}/{tot} = {100*disc/tot:.0f}%")

    print("\n=== label provenance ===")
    for k, n in Counter(r[3] for r in rows).most_common():
        print(f"  {n:3}  {k}")

    mism = [r for r in rows if r[3] == "derived" and r[2] == "graph"
            and "graph" not in str(r[1])]
    if mism:
        print(f"\n=== stated family disagrees with derived core ({len(mism)}) ===")
        for pid, fam, c, prov, _ in mism:
            print(f"  {pid:12} family={fam!r} -> core={c}")

    if show_rows:
        print("\n=== rows ===")
        for pid, dom, c, prov, extra in rows:
            print(f"  {pid:12} {dom:<32} {c:<14} [{prov}] {extra}")


if __name__ == "__main__":
    main()
