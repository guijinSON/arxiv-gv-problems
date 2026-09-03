#!/usr/bin/env python3
"""Exact-cover (Algorithm X / DLX) attack on the tiling family 2503.01929.

The instance is 3n interval lengths that must tile n blocks of length T, three
per block.  That is exact cover by sum-T triples -- the domain-standard attack is
DLX with the standard 'fewest options first' heuristic.  The module's own G6 ran
only outlier / greedy / random-restart.
"""
import importlib.util, sys, time
from itertools import combinations


def load(path):
    s = importlib.util.spec_from_file_location("m", path)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


def exact_cover_triples(lengths, T, budget_s):
    """Cover every index exactly once by triples summing to T. Algorithm X."""
    n = len(lengths)
    triples = [t for t in combinations(range(n), 3)
               if lengths[t[0]] + lengths[t[1]] + lengths[t[2]] == T]
    by_item = [[] for _ in range(n)]
    for ti, t in enumerate(triples):
        for v in t:
            by_item[v].append(ti)
    deadline = time.time() + budget_s
    used = [False] * n
    chosen = []

    def rec():
        if time.time() > deadline:
            raise TimeoutError
        # pick the uncovered item with the fewest remaining options (MRV)
        best, bestopts = -1, None
        for v in range(n):
            if used[v]:
                continue
            opts = [ti for ti in by_item[v]
                    if not any(used[u] for u in triples[ti])]
            if bestopts is None or len(opts) < len(bestopts):
                best, bestopts = v, opts
                if not opts:
                    return False
        if best == -1:
            return True
        for ti in bestopts:
            t = triples[ti]
            for u in t:
                used[u] = True
            chosen.append(t)
            if rec():
                return True
            chosen.pop()
            for u in t:
                used[u] = False
        return False

    try:
        if rec():
            return chosen, len(triples)
    except TimeoutError:
        return None, len(triples)
    return None, len(triples)


def main(budget):
    m = load("results/2503.01929/gen_2503_01929.py")
    params = m.DIFFICULTY[m.SHIPPING_DIFFICULTY]
    wins = 0
    seeds = [1, 2, 3, 4, 5, 6, 7, 8]
    for sd in seeds:
        inst = m.make_instance(seed=sd, **params)
        L = inst["lengths"]; T = inst["target_length"]
        blocks = inst["blocks"]
        t0 = time.time()
        cover, ntrip = exact_cover_triples(L, T, budget)
        el = time.time() - t0
        ok = False
        if cover:
            # turn the cover into shifts: block b gets triple b, laid end to end
            answer = [0] * len(L)
            for bi, t in enumerate(cover):
                base = blocks[bi][0]
                cur = base
                for v in t:
                    answer[v] = cur
                    cur += L[v]
            ok, why = m.verify(inst, answer)
        print(f"  seed {sd}: items={len(L)} sumT-triples={ntrip} {el:6.1f}s -> "
              f"{'SOLVED' if ok else 'failed'}")
        wins += bool(ok)
    print(f"2503.01929 exact-cover (Algorithm X) attack: {wins}/{len(seeds)} solved")


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 60)
