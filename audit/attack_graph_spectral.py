#!/usr/bin/env python3
"""Domain-standard attacks on the four `graph-spectral` group families that
shipped with only the three generic G6 probes (outlier / greedy / random
restart).

One attack per paper, each the algorithm a specialist reaches for first for
that problem class.  Nothing here reads ``inst["answer"]`` and nothing here
reads the private ``_variable_edges`` / ``_clause_triangles`` hint fields of
2506.23363 -- the gadget blocks are re-derived from the public edge list.
Every verdict is decided by the module's own ``verify(inst, answer)``.

    python3 audit/attack_graph_spectral.py all            # 60 s / seed
    python3 audit/attack_graph_spectral.py 2112 60
    python3 audit/attack_graph_spectral.py spectral-probe  # why (a) is wrong here

Attacks
-------
2110.05917  Non-Monotone 2-3Sat        -> CDCL (z3 -dimacs) on the literal CNF
2112.06333  planted proper 3-colouring -> DSATUR + branch & bound, pure python
2506.23363  Critical Node Cut, x = 0   -> gadget recovery from the graph, then
                                          CDCL on the decoded 3-SAT
2509.03064  exact 3-uniform word repr. -> interleaving-order CP model in z3
"""

import argparse
import collections
import importlib.util
import os
import statistics
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEEDS = [1, 2, 3, 4, 5, 6, 7, 8]


# --------------------------------------------------------------------------- #
# plumbing
# --------------------------------------------------------------------------- #
def load(relpath, name):
    path = os.path.join(REPO, relpath)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cdcl(nvars, clauses, budget_s):
    """Run z3's CDCL core over DIMACS.  Returns {var: bool} or None."""
    fd, path = tempfile.mkstemp(suffix=".cnf")
    os.close(fd)
    try:
        with open(path, "w") as handle:
            handle.write(f"p cnf {nvars} {len(clauses)}\n")
            handle.write("".join(" ".join(map(str, c)) + " 0\n" for c in clauses))
        proc = subprocess.run(
            ["z3", "-dimacs", f"-T:{max(1, int(budget_s))}", path],
            capture_output=True, text=True,
        )
    finally:
        os.unlink(path)
    if "s SATISFIABLE" not in proc.stdout:
        return None
    model = {}
    for line in proc.stdout.splitlines():
        if line.startswith("v "):
            for token in line[2:].split():
                lit = int(token)
                if lit:
                    model[abs(lit)] = lit > 0
    return model


def report(paper, attack, wins, times, total):
    med = statistics.median(times) if times else float("nan")
    verdict = "BROKEN" if wins else "SURVIVED"
    print(f"\n  {paper} | {attack} | solved {wins}/{total} | "
          f"median {med:.3f}s | {verdict}")
    return wins, total, med


# --------------------------------------------------------------------------- #
# 2110.05917 -- Non-Monotone 2-3Sat.  The instance IS a CNF; the standard
# attack for a CNF is a CDCL solver.  No spectral/colouring reading applies.
# --------------------------------------------------------------------------- #
def attack_2110(seeds, budget):
    mod = load("results/2110.05917/gen_2110_05917.py", "g2110")
    params = mod.DIFFICULTY[mod.SHIPPING_DIFFICULTY]
    wins, times = 0, []
    for seed in seeds:
        inst = mod.make_instance(seed=seed, **params)
        n = inst["n"]
        clauses = [list(c) for c in inst["clauses"]]
        t0 = time.time()
        model = cdcl(n, clauses, budget)
        answer = None
        if model is not None:
            answer = [(v if model.get(v, False) else -v) for v in range(1, n + 1)]
        elapsed = time.time() - t0
        ok, why = mod.verify(inst, answer) if answer is not None else (False, "no model in budget")
        times.append(elapsed)
        wins += bool(ok)
        print(f"    seed {seed}: n={n} clauses={len(clauses)} -> "
              f"{'SOLVED' if ok else 'failed (' + why + ')'} in {elapsed:.3f}s")
    return report("2110.05917", "CDCL on the shipped CNF", wins, times, len(seeds))


# --------------------------------------------------------------------------- #
# 2112.06333 -- planted proper 3-colouring.
# (c) DSATUR + branch & bound with forward checking.  Pure python, no solver.
# --------------------------------------------------------------------------- #
def dsatur_bb(n, q, adj, deadline):
    domain = [(1 << q) - 1] * n
    colour = [-1] * n
    nodes = [0]

    def rec():
        nodes[0] += 1
        if nodes[0] % 8192 == 0 and time.time() > deadline:
            raise TimeoutError
        best, best_size, best_deg = -1, q + 1, -1
        for v in range(n):
            if colour[v] != -1:
                continue
            size = bin(domain[v]).count("1")
            if size == 0:
                return False
            if size < best_size or (size == best_size and len(adj[v]) > best_deg):
                best, best_size, best_deg = v, size, len(adj[v])
        if best == -1:
            return True
        v = best
        for c in range(q):
            if not (domain[v] >> c) & 1:
                continue
            colour[v] = c
            touched, alive = [], True
            for u in adj[v]:
                if colour[u] == -1 and (domain[u] >> c) & 1:
                    domain[u] &= ~(1 << c)
                    touched.append(u)
                    if domain[u] == 0:
                        alive = False
            if alive and rec():
                return True
            for u in touched:
                domain[u] |= 1 << c
            colour[v] = -1
        return False

    try:
        return colour if rec() else None
    except TimeoutError:
        return None


def attack_2112(seeds, budget):
    mod = load("results/2112.06333/gen_2112_06333.py", "g2112")
    params = mod.DIFFICULTY[mod.SHIPPING_DIFFICULTY]
    wins, times = 0, []
    for seed in seeds:
        inst = mod.make_instance(seed=seed, **params)
        n, q = inst["num_vertices"], inst["num_colors"]
        adj = [[] for _ in range(n)]
        for u, v in inst["edges"]:
            adj[u].append(v)
            adj[v].append(u)
        t0 = time.time()
        colouring = dsatur_bb(n, q, adj, t0 + budget)
        elapsed = time.time() - t0
        ok, why = mod.verify(inst, colouring) if colouring else (False, "no colouring in budget")
        times.append(elapsed)
        wins += bool(ok)
        print(f"    seed {seed}: V={n} E={len(inst['edges'])} q={q} -> "
              f"{'SOLVED' if ok else 'failed (' + why + ')'} in {elapsed:.3f}s")
    return report("2112.06333", "DSATUR + branch&bound", wins, times, len(seeds))


def spectral_probe(seeds):
    """Why attack (a) is the WRONG tool for 2112.06333, measured.

    The planted 3-partition is an equitable partition of an 8-regular graph, so
    its quotient eigenvalues are {8, -4, -4}.  The Alon-Boppana / Friedman bulk
    of a random 8-regular graph reaches -2*sqrt(7) = -5.2915, which swallows the
    -4 signal.  Nothing sticks out of the semicircle to seed a greedy repair.

    This diagnostic (and only this diagnostic) reads inst["answer"], to measure
    the overlap between the planted class-indicator space and the bottom
    eigenvectors.  It constructs no candidate and is not graded.
    """
    import numpy as np
    mod = load("results/2112.06333/gen_2112_06333.py", "g2112s")
    params = mod.DIFFICULTY[mod.SHIPPING_DIFFICULTY]
    print("  spectral probe on 2112.06333 (adjacency, shipping preset)")
    print(f"  planted quotient eigenvalue = -d/(q-1) = -4.0 ; "
          f"random-regular bulk edge = -2*sqrt(d-1) = {-2 * (7 ** 0.5):.4f}")
    for seed in seeds:
        inst = mod.make_instance(seed=seed, **params)
        n = inst["num_vertices"]
        A = np.zeros((n, n))
        for u, v in inst["edges"]:
            A[u, v] = A[v, u] = 1.0
        vals, vecs = np.linalg.eigh(A)
        # overlap of the planted class-indicator space with the bottom-2 space
        ans = inst["answer"]
        ind = np.zeros((n, 3))
        for v, c in enumerate(ans):
            ind[v, c] = 1.0
        ind -= ind.mean(0)
        Q, _ = np.linalg.qr(ind[:, :2])
        bottom = vecs[:, :2]
        overlap = np.linalg.norm(Q.T @ bottom, "fro") ** 2 / 2.0
        print(f"    seed {seed}: lambda_min={vals[0]:.4f} lambda_2={vals[1]:.4f} "
              f"lambda_max={vals[-1]:.4f} | overlap(planted, bottom-2)={overlap:.4f}")


# --------------------------------------------------------------------------- #
# 2506.23363 -- Critical Node Cut with x = 0, i.e. Vertex Cover of size k.
# The graph is the textbook SAT->VC gadget graph.  Recover the gadgets from the
# public edge list, decode to 3-SAT, solve with CDCL, re-encode the cover.
# --------------------------------------------------------------------------- #
def recover_gadgets(vertex_count, edges):
    """Blocks from the PUBLIC edge list only.  Returns (pairs, triangles, adj)
    or None when the graph does not have the expected gadget shape."""
    adj = collections.defaultdict(set)
    for u, v in edges:
        adj[u].add(v)
        adj[v].add(u)
    deg3 = {v for v in range(1, vertex_count + 1) if len(adj[v]) == 3}
    literals = [v for v in range(1, vertex_count + 1) if v not in deg3]
    literal_set = set(literals)

    seen, triangles = set(), []
    for v in sorted(deg3):
        if v in seen:
            continue
        seen.add(v)
        stack, comp = [v], []
        while stack:
            x = stack.pop()
            comp.append(x)
            for y in adj[x]:
                if y in deg3 and y not in seen:
                    seen.add(y)
                    stack.append(y)
        if len(comp) != 3:
            return None
        triangles.append(comp)

    pairs = []
    for v in literals:
        inside = adj[v] & literal_set
        if len(inside) != 1:
            return None
        w = next(iter(inside))
        if v < w:
            pairs.append((v, w))
    if 2 * len(pairs) != len(literals):
        return None
    for tri in triangles:
        for x in tri:
            if len(adj[x] - set(tri)) != 1:
                return None
    return pairs, triangles, adj


def attack_2506(seeds, budget):
    mod = load("results/2506.23363/gen_2506_23363.py", "g2506")
    params = mod.DIFFICULTY[mod.SHIPPING_DIFFICULTY]
    wins, times = 0, []
    for seed in seeds:
        inst = mod.make_instance(seed=seed, **params)
        vertex_count = inst["vertex_count"]
        edges = [tuple(e) for e in inst["edges"]]
        t0 = time.time()
        rec = recover_gadgets(vertex_count, edges)
        if rec is None:
            elapsed = time.time() - t0
            times.append(elapsed)
            print(f"    seed {seed}: gadget recovery failed -> failed in {elapsed:.3f}s")
            continue
        pairs, triangles, adj = rec
        # boolean var i  <=>  endpoint pairs[i][0] is the one taken into the cover
        index = {}
        for i, (a, b) in enumerate(pairs, 1):
            index[a] = i
            index[b] = -i
        clauses = []
        for tri in triangles:
            lits = []
            for x in tri:
                outside = next(iter(adj[x] - set(tri)))
                lits.append(index[outside])
            clauses.append(lits)
        model = cdcl(len(pairs), clauses, budget)
        answer = None
        if model is not None:
            chosen = set()
            for i, (a, b) in enumerate(pairs, 1):
                chosen.add(a if model.get(i, False) else b)
            cover = list(chosen)
            for tri in triangles:
                omit = None
                for x in tri:
                    if next(iter(adj[x] - set(tri))) in chosen:
                        omit = x
                        break
                if omit is None:
                    omit = tri[0]
                cover.extend(y for y in tri if y != omit)
            answer = cover
        elapsed = time.time() - t0
        ok, why = mod.verify(inst, answer) if answer is not None else (False, "no model in budget")
        times.append(elapsed)
        wins += bool(ok)
        print(f"    seed {seed}: V={vertex_count} E={len(edges)} k={inst['k']} "
              f"(decoded {len(pairs)} vars / {len(triangles)} clauses) -> "
              f"{'SOLVED' if ok else 'failed (' + why + ')'} in {elapsed:.3f}s")
    return report("2506.23363", "gadget recovery + CDCL on decoded 3-SAT",
                  wins, times, len(seeds))


# --------------------------------------------------------------------------- #
# 2509.03064 -- exact 3-uniform word representation.
# Not spectral and not a colouring: it is an ordering problem.  Model it as a
# CP/SMT problem over the 3n occurrence positions.  x and y alternate exactly
# when their six occurrences strictly interleave, which is two order chains.
# --------------------------------------------------------------------------- #
def attack_2509(seeds, budget):
    import z3
    mod = load("results/2509.03064/gen_2509_03064.py", "g2509")
    params = mod.DIFFICULTY[mod.SHIPPING_DIFFICULTY]

    def chain(P, Q):
        return z3.And(P[0] < Q[0], Q[0] < P[1], P[1] < Q[1], Q[1] < P[2], P[2] < Q[2])

    wins, times = 0, []
    for seed in seeds:
        inst = mod.make_instance(seed=seed, **params)
        n, k = inst["n"], inst["k"]
        target = {tuple(sorted(e)) for e in inst["edges"]}
        t0 = time.time()
        P = [[z3.Int(f"p_{x}_{j}") for j in range(k)] for x in range(n)]
        solver = z3.Solver()
        solver.set("timeout", int(budget * 1000))
        flat = [P[x][j] for x in range(n) for j in range(k)]
        for var in flat:
            solver.add(var >= 0, var < n * k)
        solver.add(z3.Distinct(flat))
        for x in range(n):
            for j in range(k - 1):
                solver.add(P[x][j] < P[x][j + 1])
        for a in range(n):
            for b in range(a + 1, n):
                alt = z3.Or(chain(P[a], P[b]), chain(P[b], P[a]))
                solver.add(alt if (a, b) in target else z3.Not(alt))
        status = solver.check()
        word = None
        if status == z3.sat:
            model = solver.model()
            order = sorted((model[P[x][j]].as_long(), x)
                           for x in range(n) for j in range(k))
            word = [x for _, x in order]
        elapsed = time.time() - t0
        ok, why = mod.verify(inst, word) if word is not None else (False, f"z3 {status}")
        times.append(elapsed)
        wins += bool(ok)
        print(f"    seed {seed}: n={n} k={k} |E|={len(inst['edges'])} "
              f"word_len={n * k} -> "
              f"{'SOLVED' if ok else 'failed (' + str(why) + ')'} in {elapsed:.3f}s")
    return report("2509.03064", "interleaving-order CP model in z3", wins, times, len(seeds))


# --------------------------------------------------------------------------- #
ATTACKS = {
    "2110": attack_2110,
    "2112": attack_2112,
    "2506": attack_2506,
    "2509": attack_2509,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("which", nargs="?", default="all",
                    choices=["all", "spectral-probe", *ATTACKS])
    ap.add_argument("budget", nargs="?", type=float, default=60.0,
                    help="per-seed wall-clock budget in seconds")
    args = ap.parse_args()
    seeds = SEEDS

    if args.which == "spectral-probe":
        spectral_probe(seeds)
        return

    names = list(ATTACKS) if args.which == "all" else [args.which]
    rows = []
    for name in names:
        print(f"\n=== {name} (budget {args.budget:.0f}s/seed, {len(seeds)} seeds) ===")
        rows.append(ATTACKS[name](seeds, args.budget))
    print("\n" + "=" * 62)
    for name, (wins, total, med) in zip(names, rows):
        print(f"  {name}: {wins}/{total} solved, median {med:.3f}s, "
              f"{'BROKEN' if wins else 'SURVIVED'}")


if __name__ == "__main__":
    sys.exit(main())
