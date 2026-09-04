#!/usr/bin/env python3
"""Second, different standard attack -- on 2412.14615 (binary projective-line
partition over GF(2)), the other finite-field family in the shipped corpus whose
G6 panel ran only generic probes plus its own bounded search.

The solver is handed 3n distinct nonzero vectors of PG(bits-1, 2) and must
partition them into n XOR-zero triples.  Candidate lines are all triples
{a, b, a^b} contained in the point set, so this is exact cover by 3-sets.

The generator's own guard already rejects any instance solved by a DETERMINISTIC
MRV backtracker within 25,000 nodes (_bounded_backtracking).  So the shipped
instances are, by construction, the ones where that one fixed search order gets
unlucky.  The specialist's answer to a heavy-tailed backtracking distribution is
not a bigger budget -- it is RANDOMIZED RESTARTS.  Attack 1 is randomized-order
MRV exact cover with a Luby-ish restart schedule.  Attack 2 is the other standard
move: compile to SAT (exactly-one per point) and hand it to a CDCL solver (z3).

Graded ONLY by the module's own verify().  inst["answer"] is never read.

Usage: python3 audit/attack_ffc_projective.py [budget_seconds] [n_seeds] [mode]
       mode in {dlx, sat, both}   (default both)
"""
import importlib.util
import os
import random
import statistics
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def load(path):
    spec = importlib.util.spec_from_file_location("m_" + os.path.basename(path), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def candidate_lines(points):
    """All triples {a,b,a^b} whose three vectors are all in the point set.
    Returns list of (i,j,k) 0-based index triples, i<j<k."""
    index = {v: i for i, v in enumerate(points)}
    m = len(points)
    out = []
    for i in range(m):
        pi = points[i]
        for j in range(i + 1, m):
            k = index.get(pi ^ points[j])
            if k is not None and k > j:
                out.append((i, j, k))
    return out


# ------------------------------------------------------- attack 1: randomized DLX

def dlx_restart(points, nlines, budget_s, seed):
    lines = candidate_lines(points)
    m = len(points)
    masks = [(1 << i) | (1 << j) | (1 << k) for i, j, k in lines]
    incident = [[] for _ in range(m)]
    for eid, (i, j, k) in enumerate(lines):
        incident[i].append(eid)
        incident[j].append(eid)
        incident[k].append(eid)

    rng = random.Random(seed)
    deadline = time.time() + budget_s
    full = (1 << m) - 1
    total_nodes = 0
    restarts = 0

    def search(remaining, node_cap, order, state):
        state[0] += 1
        if state[0] > node_cap:
            state[1] = True
            return None
        if (state[0] & 2047) == 0 and time.time() > deadline:
            state[1] = True
            state[2] = True          # hard wall-clock stop, not a node-cap stop
            return None
        if remaining == 0:
            return []
        best = None
        best_pt = -1
        for point in order:
            if not (remaining >> point) & 1:
                continue
            here = [e for e in incident[point] if masks[e] & remaining == masks[e]]
            if not here:
                return None
            if best is None or len(here) < len(best):
                best, best_pt = here, point
                if len(best) <= 1:
                    break
        rng.shuffle(best)
        for eid in best:
            suf = search(remaining ^ masks[eid], node_cap, order, state)
            if suf is not None:
                return [lines[eid]] + suf
            if state[1]:
                return None
        return None

    cap = 20_000
    while time.time() < deadline:
        restarts += 1
        order = list(range(m))
        rng.shuffle(order)
        state = [0, False, False]
        sys.setrecursionlimit(10000)
        res = search(full, cap, order, state)
        total_nodes += state[0]
        if res is not None:
            return [[i + 1, j + 1, k + 1] for (i, j, k) in res], total_nodes, restarts
        if state[2]:
            break
        cap = min(cap * 2, 4_000_000)
    return None, total_nodes, restarts


# ------------------------------------------------------- attack 2: compile to SAT (z3)

def sat_solve(points, budget_s):
    lines = candidate_lines(points)
    m = len(points)
    incident = [[] for _ in range(m)]
    for eid, (i, j, k) in enumerate(lines):
        incident[i].append(eid)
        incident[j].append(eid)
        incident[k].append(eid)

    parts = ["(set-option :produce-models true)"]
    for eid in range(len(lines)):
        parts.append(f"(declare-const e{eid} Bool)")
    for p in range(m):
        ids = incident[p]
        if not ids:
            return None, "point with no candidate line"
        lits = " ".join(f"e{e}" for e in ids)
        parts.append(f"(assert (or {lits}))")
        if len(ids) > 1:
            parts.append(f"(assert ((_ at-most 1) {lits}))")
    parts.append("(check-sat)")
    parts.append("(get-model)")
    smt = "\n".join(parts)

    with tempfile.NamedTemporaryFile("w", suffix=".smt2", delete=False) as fh:
        fh.write(smt)
        path = fh.name
    try:
        proc = subprocess.run(["z3", f"-T:{int(budget_s)}", path],
                              capture_output=True, text=True, timeout=budget_s + 15)
    except subprocess.TimeoutExpired:
        os.unlink(path)
        return None, "timeout"
    os.unlink(path)
    out = proc.stdout
    if not out.startswith("sat"):
        return None, out.strip().splitlines()[0] if out.strip() else "no output"
    chosen = []
    import re
    for mo in re.finditer(r"\(define-fun\s+e(\d+)\s*\(\)\s*Bool\s*\n?\s*(true|false)\)", out):
        if mo.group(2) == "true":
            chosen.append(int(mo.group(1)))
    return [[i + 1, j + 1, k + 1] for (i, j, k) in (lines[e] for e in chosen)], "sat"




# ------------------------------------------------------- attack 2b: DIMACS CNF -> z3 SAT core

def cnf_solve(points, budget_s):
    """Exact-one-per-point in plain CNF (pairwise at-most-one) handed to z3's
    DIMACS/SAT front end, which uses the CDCL core rather than the SMT core."""
    lines = candidate_lines(points)
    m = len(points)
    incident = [[] for _ in range(m)]
    for eid, (i, j, k) in enumerate(lines):
        incident[i].append(eid)
        incident[j].append(eid)
        incident[k].append(eid)
    clauses = []
    for p in range(m):
        ids = incident[p]
        if not ids:
            return None, "isolated point"
        clauses.append([e + 1 for e in ids])
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                clauses.append([-(ids[a] + 1), -(ids[b] + 1)])
    body = "\n".join(" ".join(map(str, c)) + " 0" for c in clauses)
    text = f"p cnf {len(lines)} {len(clauses)}\n{body}\n"
    with tempfile.NamedTemporaryFile("w", suffix=".cnf", delete=False) as fh:
        fh.write(text)
        path = fh.name
    try:
        proc = subprocess.run(["z3", "-dimacs", f"-T:{int(budget_s)}", path],
                              capture_output=True, text=True, timeout=budget_s + 15)
    except subprocess.TimeoutExpired:
        os.unlink(path)
        return None, f"timeout ({len(lines)} vars, {len(clauses)} clauses)"
    os.unlink(path)
    out = proc.stdout
    if "unsat" in out.split("\n")[0:2][0].lower() or not out.lstrip().lower().startswith("s"):
        pass
    head = out.strip().splitlines()
    if not head or "SATISFIABLE" not in out.upper():
        return None, f"z3 said: {head[0] if head else 'nothing'} ({len(lines)}v/{len(clauses)}c)"
    if "UNSATISFIABLE" in out.upper():
        return None, "unsat"
    lits = []
    for ln in head:
        if ln.startswith("v "):
            lits.extend(int(x) for x in ln[2:].split())
    chosen = [v - 1 for v in lits if v > 0]
    return [[i + 1, j + 1, k + 1] for (i, j, k) in (lines[e] for e in chosen)], \
           f"sat ({len(lines)}v/{len(clauses)}c)"


# ------------------------------------------------------- driver

def main():
    budget = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    nseeds = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    mode = sys.argv[3] if len(sys.argv) > 3 else "both"
    mod = load(os.path.join(ROOT, "results", "2412.14615", "gen_2412_14615.py"))
    preset = mod.SHIPPING_DIFFICULTY
    params = dict(mod.DIFFICULTY[preset])
    n = params.pop("n")
    seeds = [1, 2, 3, 5, 7, 11, 13, 17, 19, 23][:nseeds]
    print("=" * 74)
    print(f"2412.14615  binary projective-line partition  preset={preset} n={n} {params}")
    print("=" * 74)

    for which in (["dlx", "cnf"] if mode == "both" else [mode]):
        solved, times = 0, []
        print(f"\n--- attack: {'randomized-restart MRV exact cover' if which=='dlx' else 'compile to SAT + z3 CDCL'}")
        for s in seeds:
            inst = mod.make_instance(n, seed=s, **params)
            pts = inst["points"]
            ncand = len(candidate_lines(pts))
            t0 = time.time()
            if which == "dlx":
                res, nodes, restarts = dlx_restart(pts, inst["n"], budget, seed=s)
                extra = f"{nodes:8d} nodes {restarts:3d} restarts"
            elif which == "cnf":
                res, info = cnf_solve(pts, budget)
                extra = f"z3-cnf:{info}"
            else:
                res, info = sat_solve(pts, budget)
                extra = f"z3-smt:{info}"
            el = time.time() - t0
            times.append(el)
            if res is None:
                print(f"  seed {s:>4} pts={len(pts)} cand={ncand:5d}  {el:6.2f}s  {extra}  -> NOT solved")
                continue
            ok, reason = mod.verify(inst, res)
            print(f"  seed {s:>4} pts={len(pts)} cand={ncand:5d}  {el:6.2f}s  {extra}  verify={ok} ({reason})")
            solved += bool(ok)
        print(f"  => SOLVED {solved}/{len(seeds)}  median {statistics.median(times):.2f}s")


if __name__ == "__main__":
    main()
