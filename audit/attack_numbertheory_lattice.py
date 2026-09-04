#!/usr/bin/env python3
"""Domain-standard attacks on the numbertheory-lattice group.

Four shipped families, three distinct standard algorithms.

  2310.02137  balanced prime-coordinate quadratic     -> the equation collapses to
              "pick n/2 of the n weights with sum 0"; the standard attack on a
              density-~1 subset sum is MEET-IN-THE-MIDDLE, here the 4-list
              Schroeppel-Shamir variant with a modular filter (audit/_build/mitm4.c).
  2311.00090  balanced doubly-weighted zero sum       -> same core: a balanced
  2603.07251  balanced {+1,-1}-weighted zero sum         +-1 zero sum modulo 2^64,
              which is literally the same 64-bit meet-in-the-middle.
  2502.08624  sum-free subset                          -> not a subset-sum family at
              all: the integer set is a Sidon encoding of a graph, so the standard
              attack is DECODE THE GRAPH and solve the underlying planted 3-SAT.

Lattice reduction (LLL/CJLOSS) is the other classic for this class, so the driver
prints the CJLOSS density of every instance it attacks.  For all three subset-sum
families that density sits at ~0.91-0.96 with a target vector about twice the
Gaussian-heuristic length of the orthogonal lattice, i.e. LLL is *not* expected to
isolate the planted vector -- which is why the meet-in-the-middle is the attack
that is actually run and measured.

Grading is always the module's own verify().  inst["answer"] is never read, and
neither are the modules' private "_" keys.

usage:
  python3 audit/attack_numbertheory_lattice.py all
  python3 audit/attack_numbertheory_lattice.py 2310.02137 [budget_s]
"""
from __future__ import annotations

import importlib.util
import math
import os
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESULTS = os.path.join(ROOT, "results")
BUILD = os.path.join(HERE, "_build")
MITM = os.path.join(BUILD, "mitm4")
SEEDS = [11, 23, 37, 101, 202, 303, 404, 505]
MOD64 = 1 << 64


def load(paper: str):
    path = os.path.join(RESULTS, paper, "gen_" + paper.replace(".", "_") + ".py")
    spec = importlib.util.spec_from_file_location("gen_" + paper.replace(".", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ensure_mitm() -> None:
    src = os.path.join(BUILD, "mitm4.c")
    if os.path.exists(MITM) and os.path.getmtime(MITM) > os.path.getmtime(src):
        return
    subprocess.run(["cc", "-O3", "-march=native", "-pthread", "-o", MITM, src],
                   check=True, cwd=BUILD)


def run_mitm(weights_mod64, budget_s, mbits=None, threads=8):
    """Return every c in {+1,-1}^n with sum c_i w_i == 0 (mod 2^64), as bitmasks
    whose set bits are the -1 coordinates.  Exhaustive; no heuristic pruning."""
    ensure_mitm()
    n = len(weights_mod64)
    payload = f"{n}\n" + "\n".join(str(int(w) % MOD64) for w in weights_mod64) + "\n"
    argv = [MITM]
    if mbits is not None:
        argv += [str(mbits), str(threads)]
    proc = subprocess.run(argv, input=payload, capture_output=True, text=True,
                          timeout=budget_s)
    out = []
    for line in proc.stdout.splitlines():
        if line.startswith("MASK "):
            out.append(int(line.split()[1], 16))
    return out


# --------------------------------------------------------------------------
# density diagnostics (the LLL/CJLOSS regime question, answered up front)
# --------------------------------------------------------------------------
def cjloss_density(n_items: int, log2_space: float, log2_range: float) -> float:
    """n/log2(max) in the shape that matters here: the log of the number of
    admissible sign vectors over the log of the number of reachable sums."""
    return log2_space / log2_range


def gaussian_heuristic(rank: int, log2_det: float) -> float:
    return math.sqrt(rank / (2 * math.pi * math.e)) * 2.0 ** (log2_det / rank)


# --------------------------------------------------------------------------
# family drivers
# --------------------------------------------------------------------------
def attack_2310(budget_s: float):
    """F(x)=A(x)S(x)=0 with x_i in {p,q}, q=p+2, sum(a)=0  <=>  a balanced
    zero-sum subset.  Feed the weights straight to the 64-bit MITM: a genuine
    solution has sum c_i a_i = 0 over Z, hence also 0 mod 2^64."""
    mod = load("2310.02137")
    params = mod.DIFFICULTY[mod.SHIPPING_DIFFICULTY]
    rows = []
    for seed in SEEDS:
        inst = mod.make_instance(seed=seed, **params)
        n = int(inst["variables"])
        need = int(inst["high_count"])
        weights = list(inst["weights"])
        log2_space = math.log2(math.comb(n, need))
        sigma = math.sqrt(sum(float(w) ** 2 for w in weights))
        log2_range = math.log2(sigma) + 1.0
        dens = cjloss_density(n, log2_space, log2_range)
        t0 = time.time()
        solved = False
        try:
            masks = run_mitm(weights, budget_s)
        except subprocess.TimeoutExpired:
            masks, timed_out = [], True
        else:
            timed_out = False
        for mask in masks:
            neg = sorted(i + 1 for i in range(n) if (mask >> i) & 1)
            pos = sorted(i + 1 for i in range(n) if not (mask >> i) & 1)
            for cand in (neg, pos):
                if len(cand) == need and mod.verify(inst, cand)[0]:
                    solved = True
                    break
            if solved:
                break
        rows.append((seed, solved, time.time() - t0, len(masks), dens, timed_out))
        print("  seed %-5d solved=%-5s %6.1fs  masks=%-3d cjloss_density=%.3f%s"
              % (seed, solved, rows[-1][2], len(masks), dens,
                 "  TIMEOUT" if timed_out else ""), flush=True)
    return rows


def attack_pm1(paper: str, budget_s: float, mbits=None):
    """2311.00090 / 2603.07251: choose n/2 plus and n/2 minus signs with
    sum(+-x_i) == 0 mod 2^64.  Straight 64-bit meet-in-the-middle; the balance
    condition is then just a filter on the (very few) masks that come back."""
    mod = load(paper)
    params = mod.DIFFICULTY[mod.SHIPPING_DIFFICULTY]
    rows = []
    for seed in SEEDS:
        inst = mod.make_instance(seed=seed, **params)
        n = int(inst["n"])
        xs = list(inst["sequence"])
        log2_space = math.log2(math.comb(n, n // 2))
        log2_range = float(n)                      # modulus is exactly 2**n
        dens = cjloss_density(n, log2_space, log2_range)
        t0 = time.time()
        solved = False
        try:
            masks = run_mitm(xs, budget_s, mbits=mbits)
            timed_out = False
        except subprocess.TimeoutExpired:
            masks, timed_out = [], True
        for mask in masks:
            minus = sorted(i + 1 for i in range(n) if (mask >> i) & 1)
            plus = sorted(i + 1 for i in range(n) if not (mask >> i) & 1)
            if len(plus) != n // 2:
                continue
            if mod.verify(inst, {"plus": plus, "minus": minus})[0]:
                solved = True
                break
        rows.append((seed, solved, time.time() - t0, len(masks), dens, timed_out))
        print("  seed %-5d solved=%-5s %6.1fs  masks=%-3d cjloss_density=%.3f%s"
              % (seed, solved, rows[-1][2], len(masks), dens,
                 "  TIMEOUT" if timed_out else ""), flush=True)
    return rows


# --------------------------------------------------------------------------
# 2502.08624 -- decode the Sidon graph encoding, then solve the planted 3-SAT
# --------------------------------------------------------------------------
def _relations(values):
    vals = sorted(set(values))
    present = set(vals)
    out = []
    for i, x in enumerate(vals):
        for y in vals[i:]:
            z = x + y
            if z in present:
                out.append((x, y, z))
    return out


def _dpll(nvars, clauses, deadline):
    """Textbook DPLL: unit propagation to fixpoint, conflict detection, then
    branch on the literal that occurs most often in the still-unsatisfied
    clauses.  50 variables / 300 clauses is tiny for this."""
    assign = [None] * (nvars + 1)

    def propagate():
        """Return False on conflict; otherwise assign every forced literal."""
        while True:
            changed = False
            for cl in clauses:
                sat = False
                free = []
                for lit in cl:
                    val = assign[lit if lit > 0 else -lit]
                    if val is None:
                        free.append(lit)
                    elif val == (lit > 0):
                        sat = True
                        break
                if sat:
                    continue
                if not free:
                    return False
                if len(free) == 1:
                    lit = free[0]
                    assign[lit if lit > 0 else -lit] = lit > 0
                    changed = True
            if not changed:
                return True

    def search():
        if time.time() > deadline:
            raise TimeoutError
        saved = list(assign)
        if not propagate():
            assign[:] = saved
            return False
        counts = {}
        for cl in clauses:
            sat = False
            free = []
            for lit in cl:
                val = assign[lit if lit > 0 else -lit]
                if val is None:
                    free.append(lit)
                elif val == (lit > 0):
                    sat = True
                    break
            if sat:
                continue
            for lit in free:
                counts[lit] = counts.get(lit, 0) + 1
        if not counts:
            return True
        best = max(counts, key=counts.__getitem__)
        for polarity in (best > 0, best < 0):
            keep = list(assign)
            assign[best if best > 0 else -best] = polarity
            if search():
                return True
            assign[:] = keep
        assign[:] = saved
        return False

    sys.setrecursionlimit(100000)
    if search():
        return {v: (assign[v] if assign[v] is not None else False)
                for v in range(1, nvars + 1)}
    return None


def attack_2502(budget_s: float):
    mod = load("2502.08624")
    params = mod.DIFFICULTY[mod.SHIPPING_DIFFICULTY]
    rows = []
    for seed in SEEDS:
        inst = mod.make_instance(seed=seed, **params)
        numbers = list(inst["numbers"])          # public: exactly what render() prints
        need = int(inst["deletion_count"])
        t0 = time.time()
        deadline = t0 + budget_s
        solved = False
        note = ""
        try:
            rels = _relations(numbers)
            operands = sorted({u for x, y, _ in rels for u in (x, y)})
            pos = {v: i for i, v in enumerate(operands)}
            adj = [set() for _ in operands]
            edges = []
            for x, y, _z in rels:
                a, b = pos[x], pos[y]
                adj[a].add(b)
                adj[b].add(a)
                edges.append((min(a, b), max(a, b)))
            edges = sorted(set(edges))
            # clause triangles: in this reduction every triangle IS a clause
            tri, in_tri = [], {}
            tri_edges = set()
            for a, b in edges:
                for c in adj[a] & adj[b]:
                    if c > b:
                        tri.append((a, b, c))
                        tri_edges.update({(a, b), (a, c), (b, c)})
            for t_i, (a, b, c) in enumerate(tri):
                for v in (a, b, c):
                    in_tri.setdefault(v, []).append(t_i)
            note = "V=%d E=%d tri=%d" % (len(operands), len(edges), len(tri))
            if any(len(v) != 1 for v in in_tri.values()) or len(in_tri) != len(operands):
                raise ValueError("triangles do not partition the vertices")
            # contradiction graph -> one bipartite component per Boolean variable
            conflict = [set() for _ in operands]
            for a, b in edges:
                if (a, b) not in tri_edges:
                    conflict[a].add(b)
                    conflict[b].add(a)
            colour = [None] * len(operands)
            var_of = [None] * len(operands)
            nvars = 0
            for s in range(len(operands)):
                if colour[s] is not None:
                    continue
                nvars += 1
                colour[s] = 0
                var_of[s] = nvars
                stack = [s]
                while stack:
                    u = stack.pop()
                    for w in conflict[u]:
                        if colour[w] is None:
                            colour[w] = 1 - colour[u]
                            var_of[w] = nvars
                            stack.append(w)
                        elif colour[w] == colour[u]:
                            raise ValueError("conflict graph is not bipartite")
            clauses = [[(var_of[v] if colour[v] == 0 else -var_of[v]) for v in t]
                       for t in tri]
            note += " vars=%d clauses=%d" % (nvars, len(clauses))
            model = _dpll(nvars, clauses, deadline)
            if model is not None:
                keep = set()
                for t in tri:
                    for v in t:
                        lit_true = model[var_of[v]] if colour[v] == 0 else not model[var_of[v]]
                        if lit_true:
                            keep.add(v)
                            break
                delete = [operands[i] for i in range(len(operands)) if i not in keep]
                if len(delete) == need:
                    solved = mod.verify(inst, sorted(delete))[0]
                else:
                    note += " |D|=%d!=%d" % (len(delete), need)
            else:
                note += " UNSAT/exhausted"
        except TimeoutError:
            note += " TIMEOUT"
        except Exception as exc:  # representation mismatch -> say so, do not guess
            note += " ERROR:%s" % exc
        el = time.time() - t0
        rows.append((seed, solved, el, 0, float("nan"), "TIMEOUT" in note))
        print("  seed %-5d solved=%-5s %6.1fs  %s" % (seed, solved, el, note), flush=True)
    return rows


def summarise(paper, label, rows):
    n_solved = sum(1 for r in rows if r[1])
    med = statistics.median(r[2] for r in rows)
    verdict = "BROKEN" if n_solved else "SURVIVED"
    print("ROW | %s | %s | solved %d/%d | median %.1fs | %s"
          % (paper, label, n_solved, len(rows), med, verdict))
    return verdict


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    budget = float(sys.argv[2]) if len(sys.argv) > 2 else 90.0
    jobs = {
        "2310.02137": ("4-list Schroeppel-Shamir meet-in-the-middle (2^30)",
                       lambda: attack_2310(budget)),
        "2311.00090": ("4-list Schroeppel-Shamir meet-in-the-middle (2^32) mod 2^64",
                       lambda: attack_pm1("2311.00090", budget)),
        "2603.07251": ("4-list Schroeppel-Shamir meet-in-the-middle (2^32) mod 2^64",
                       lambda: attack_pm1("2603.07251", budget)),
        "2502.08624": ("Sidon-decode to graph + planted-3-SAT DPLL",
                       lambda: attack_2502(budget)),
    }
    targets = list(jobs) if which == "all" else [which]
    results = []
    for paper in targets:
        label, fn = jobs[paper]
        print("== %s : %s  (budget %.0fs/seed, %d seeds)" % (paper, label, budget, len(SEEDS)),
              flush=True)
        rows = fn()
        results.append((paper, label, rows, summarise(paper, label, rows)))
        print(flush=True)
    print("---- summary ----")
    for paper, label, rows, verdict in results:
        n_solved = sum(1 for r in rows if r[1])
        print("%s | %s | %d/%d | %.1fs | %s"
              % (paper, label, n_solved, len(rows),
                 statistics.median(r[2] for r in rows), verdict))


if __name__ == "__main__":
    main()
