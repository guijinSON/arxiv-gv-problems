#!/usr/bin/env python3
"""Domain-standard attacks on the two planted-clique families that shipped
without one.  Spectral + randomized-greedy-with-local-search, i.e. what a
specialist reaches for first.  Verdict is decided by the module's own verify().
"""
import importlib.util, sys, time, random
import numpy as np


def load(path):
    s = importlib.util.spec_from_file_location("m", path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def adj_from_edges(n, edges, one_indexed=True):
    A = np.zeros((n, n), dtype=np.int8)
    off = 1 if one_indexed else 0
    for u, v in edges:
        A[u - off, v - off] = 1
        A[v - off, u - off] = 1
    return A


def greedy_clique_from(A, order):
    """Grow a clique taking vertices in `order`, keeping only mutual neighbours."""
    clique = []
    for v in order:
        if all(A[v, u] for u in clique):
            clique.append(v)
    return clique


def spectral_candidates(A, k, topm=6):
    """AKS-style: top eigenvectors of the centred adjacency; the planted set
    shows up as large-|component| vertices."""
    n = A.shape[0]
    M = A.astype(float) * 2 - 1          # centre at +-1
    np.fill_diagonal(M, 0)
    vals, vecs = np.linalg.eigh(M)
    cands = []
    for idx in list(range(n - topm, n)) + list(range(topm)):   # top and bottom
        v = vecs[:, idx]
        for sign in (1, -1):
            order = np.argsort(-sign * v)
            cands.append(list(order[: max(4 * k, 40)]))
    return cands


def find_clique(A, k, budget_s=90, seed=0):
    """Spectral seeding + randomized greedy + local search. Returns a k-clique or None."""
    n = A.shape[0]
    rng = random.Random(seed)
    deadline = time.time() + budget_s
    deg = A.sum(1)

    # 1. spectral
    for cand in spectral_candidates(A, k):
        sub = list(cand)
        sub.sort(key=lambda v: -A[np.ix_([v], sub)].sum())
        c = greedy_clique_from(A, sub)
        if len(c) >= k:
            return sorted(c[:k])
        if time.time() > deadline:
            return None

    # 2. degree-ordered greedy
    c = greedy_clique_from(A, list(np.argsort(-deg)))
    if len(c) >= k:
        return sorted(c[:k])

    # 3. randomized greedy with restarts + local search
    best = 0
    while time.time() < deadline:
        order = list(range(n))
        rng.shuffle(order)
        c = greedy_clique_from(A, order)
        # local search: try swapping one out for two in
        for _ in range(60):
            if len(c) >= k:
                break
            common = [v for v in range(n) if v not in c and all(A[v, u] for u in c)]
            if common:
                c.append(rng.choice(common)); continue
            if not c:
                break
            c.pop(rng.randrange(len(c)))
            cand = [v for v in range(n) if v not in c and all(A[v, u] for u in c)]
            if cand:
                c.append(rng.choice(cand))
        best = max(best, len(c))
        if len(c) >= k:
            return sorted(c[:k])
    return None


def attack_planted_clique(modpath, seeds, budget_s):
    m = load(modpath)
    params = m.DIFFICULTY[m.SHIPPING_DIFFICULTY]
    wins = 0
    for sd in seeds:
        inst = m.make_instance(seed=sd, **params)
        n = inst["vertex_count"]; k = inst["clique_size"]
        A = adj_from_edges(n, inst["edges"], one_indexed=True)
        got = find_clique(A, k, budget_s=budget_s, seed=sd)
        ok = False
        if got is not None:
            ans = [v + 1 for v in got]           # module is 1-indexed
            ok, why = m.verify(inst, ans)
        print(f"  seed {sd}: n={n} k={k} sqrt(n)={n**0.5:.1f} -> "
              f"{'SOLVED' if ok else 'failed'}")
        wins += bool(ok)
    return wins, len(seeds)


def attack_disjoint_cliques(modpath, seeds, budget_s):
    m = load(modpath)
    params = m.DIFFICULTY[m.SHIPPING_DIFFICULTY]
    wins = 0
    for sd in seeds:
        inst = m.make_instance(seed=sd, **params)
        n = inst["n"]; k = inst["k"]; cs = inst["clique_size"]
        A = np.array([[1 if ch == "1" else 0 for ch in row]
                      for row in inst["adjacency"]], dtype=np.int8)
        found, used = [], set()
        t_each = budget_s / max(1, k)
        for _ in range(k):
            mask = [v for v in range(n) if v not in used]
            sub = A[np.ix_(mask, mask)]
            c = find_clique(sub, cs, budget_s=t_each, seed=sd)
            if c is None:
                break
            real = sorted(mask[v] for v in c)
            found.append(real); used.update(real)
        ok = False
        if len(found) == k:
            ok, why = m.verify(inst, found)
        print(f"  seed {sd}: n={n} k={k} size={cs} sqrt(n)={n**0.5:.1f} -> "
              f"{'SOLVED' if ok else 'failed'} ({len(found)}/{k} cliques found)")
        wins += bool(ok)
    return wins, len(seeds)


if __name__ == "__main__":
    which = sys.argv[1]
    budget = float(sys.argv[2]) if len(sys.argv) > 2 else 90
    seeds = [1, 2, 3, 4, 5, 6, 7, 8]
    if which == "clique":
        w, t = attack_planted_clique("results/0901.3348/gen_0901_3348.py", seeds, budget)
        print(f"0901.3348 spectral+greedy attack: {w}/{t} solved")
    else:
        w, t = attack_disjoint_cliques("results/1008.2814/gen_1008_2814.py", seeds, budget)
        print(f"1008.2814 spectral+greedy attack: {w}/{t} solved")
