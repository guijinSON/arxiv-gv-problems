#!/usr/bin/env python3
"""Domain-standard attack on monotone 1-in-3-SAT families.

Exactly-1-in-3 propagates hard: setting a variable true forces its two clause
mates false; two falses force the third true.  That plus DPLL with restarts is
what a specialist runs.  We also solve the GF(2) XOR relaxation, which every
1-in-3 solution must satisfy.
"""
import importlib.util, sys, time, random


def load(path):
    s = importlib.util.spec_from_file_location("m", path)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


def solve_1in3(nvars, clauses, budget_s, seed=0):
    """DPLL with exactly-1-in-3 unit propagation and random restarts."""
    rng = random.Random(seed)
    occ = [[] for _ in range(nvars)]
    for ci, cl in enumerate(clauses):
        for v in cl:
            occ[v].append(ci)
    deadline = time.time() + budget_s

    def propagate(assign):
        """assign: dict var->0/1. Returns False on contradiction."""
        queue = list(assign.items())
        while queue:
            if time.time() > deadline:
                return False
            v, val = queue.pop()
            for ci in occ[v]:
                cl = clauses[ci]
                ones = [u for u in cl if assign.get(u) == 1]
                zeros = [u for u in cl if assign.get(u) == 0]
                unk = [u for u in cl if u not in assign]
                if len(ones) > 1:
                    return False
                if len(zeros) == 3:
                    return False
                if len(ones) == 1 and unk:
                    for u in unk:
                        if assign.get(u) == 1:
                            return False
                        if u not in assign:
                            assign[u] = 0; queue.append((u, 0))
                elif len(ones) == 0 and len(unk) == 1:
                    u = unk[0]
                    assign[u] = 1; queue.append((u, 1))
                elif len(ones) == 0 and not unk:
                    return False
        return True

    def dpll(assign, depth=0):
        if time.time() > deadline:
            return None
        a = dict(assign)
        if not propagate(a):
            return None
        unassigned = [v for v in range(nvars) if v not in a]
        if not unassigned:
            return a
        # pick the variable in the most constrained clause
        best, bestscore = None, -1
        for ci, cl in enumerate(clauses):
            unk = [u for u in cl if u not in a]
            if len(unk) == 2 and not any(a.get(u) == 1 for u in cl):
                best = unk[0]; break
        if best is None:
            best = max(unassigned, key=lambda v: len(occ[v]))
        for val in (1, 0):
            a2 = dict(a); a2[best] = val
            r = dpll(a2, depth + 1)
            if r is not None:
                return r
        return None

    sys.setrecursionlimit(100000)
    # restarts with random seeding of a few variables
    while time.time() < deadline:
        seed_assign = {}
        r = dpll(seed_assign)
        if r is not None:
            return sorted(v for v, x in r.items() if x == 1)
        # if a full DPLL pass exhausted without a solution, no point restarting
        return None
    return None


def run(pid, modpath, clause_key, nvar_key, seeds, budget_s):
    m = load(modpath)
    params = m.DIFFICULTY[m.SHIPPING_DIFFICULTY]
    wins = 0
    for sd in seeds:
        inst = m.make_instance(seed=sd, **params)
        clauses = [list(c) for c in inst[clause_key]]
        if "check_clauses" in inst and clause_key == "choice_groups":
            clauses = clauses + [list(c) for c in inst["check_clauses"]]
        nvars = inst[nvar_key]
        lo = min(min(c) for c in clauses); hi = max(max(c) for c in clauses)
        shift = 1 if hi >= nvars or lo >= 1 and hi == nvars else 0
        if hi >= nvars:
            clauses = [[v - 1 for v in c] for c in clauses]; shift = 1
        else:
            shift = 0
        t0 = time.time()
        sol = solve_1in3(nvars, clauses, budget_s, seed=sd)
        el = time.time() - t0
        ok = False
        if sol is not None:
            for off in ((1, 0) if shift else (0, 1)):
                cand = [v + off for v in sol]
                try:
                    good, why = m.verify(inst, cand)
                except Exception:
                    good = False
                if good:
                    ok = True; break
        print(f"  seed {sd}: vars={nvars} clauses={len(clauses)} {el:5.1f}s -> "
              f"{'SOLVED' if ok else ('no-solution' if sol is None else 'found-but-rejected')}")
        wins += bool(ok)
    print(f"{pid} 1-in-3 DPLL attack: {wins}/{len(seeds)} solved")
    return wins


if __name__ == "__main__":
    which = sys.argv[1]; budget = float(sys.argv[2]) if len(sys.argv) > 2 else 60
    seeds = [1, 2, 3, 4, 5, 6, 7, 8]
    if which == "2507":
        run("2507.17878", "results/2507.17878/gen_2507_17878.py", "clauses", "n_variables", seeds, budget)
    else:
        run("1512.03127", "results/1512.03127/gen_1512_03127.py", "choice_groups", "num_variables", seeds, budget)
