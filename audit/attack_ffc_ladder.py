#!/usr/bin/env python3
"""Same Lee-Brickell ISD, run against 2411.19413's reserve escalation rungs
(hard / extreme) and the generator's own escalate() ladder, to show whether the
documented escalation path recovers any hardness.  Graded by the module's verify().
"""
import os, sys, time, statistics, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from attack_finite_field_codes import load, isd_solve, ROOT

mod = load(os.path.join(ROOT, "results", "2411.19413", "gen_2411_19413.py"))
budget = float(sys.argv[1]) if len(sys.argv) > 1 else 90.0
seeds = [1, 2, 3, 5, 7, 11, 13, 17]

for preset in ("standard", "hard", "extreme"):
    params = dict(mod.DIFFICULTY[preset])
    solved, times = 0, []
    for s in seeds:
        inst = mod.make_instance(seed=s, **params)
        t0 = time.time()
        sup, iters = isd_solve(inst["columns"], inst["target"], inst["n"],
                               inst["rows"], inst["weight"], budget, seed=s)
        el = time.time() - t0
        times.append(el)
        ok = False
        if sup is not None:
            ok, _ = mod.verify(inst, [i + 1 for i in sup])
        solved += bool(ok)
    sp = mod.search_space(mod.make_instance(seed=1, **params))
    print(f"{preset:9s} n={params['n']:3d} r={params['rows']:3d} h={params['weight']:2d} "
          f"space=2^{math.log2(sp):.1f}  solved {solved}/{len(seeds)}  "
          f"median {statistics.median(times):.2f}s  max {max(times):.2f}s")
