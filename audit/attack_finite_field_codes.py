#!/usr/bin/env python3
"""Domain-standard attack on the finite-field-codes group.

2411.19413 ships "exact-weight binary syndrome decoding": given a parity-check
matrix H (r x n over F_2) and a syndrome s, find x of Hamming weight exactly h
with Hx = s.  That is textbook syndrome decoding, and the standard algorithm for
it is Information-Set Decoding (Prange 1962 / Lee-Brickell 1988), not local
search.  Each iteration picks a random information set, runs Gauss-Jordan over
F_2, and enumerates p error positions outside the set.

Shipping preset is n=160, r=92, h=16 -> k = n-r = 68.  Per-iteration success
probability for Lee-Brickell with parameter p is

    C(k,p) * C(r, h-p) / C(n, h)

    p=0  7.77e-05   (~12877 iters)      p=2  7.07e-03   (~142 iters)
    p=1  1.10e-03   (~911 iters)        p=3  2.76e-02   (~36 iters)

so a few hundred Gaussian eliminations suffice -- against a nominal
C(160,16) = 4.06e21 = 2^71.8 "exact-shape" search space.

Graded ONLY by the module's own verify().  inst["answer"] is never read.

Usage:  python3 audit/attack_finite_field_codes.py [budget_seconds] [n_seeds]
"""
import importlib.util
import math
import os
import random
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def load(path):
    spec = importlib.util.spec_from_file_location("gen_mod_" + os.path.basename(path), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- ISD core

def isd_solve(columns, target, n, r, h, budget_s, seed, p_max=2):
    """Lee-Brickell information-set decoding.

    columns[i] is the i-th column of H as an r-bit integer.
    Returns a sorted list of 0-based indices of size h with XOR == target,
    or None if the budget expires.
    """
    rng = random.Random(seed)
    deadline = time.time() + budget_s

    # Row form: row j is a bitmask over the n columns; bit n carries the syndrome.
    base_rows = []
    for j in range(r):
        bits = 0
        for i in range(n):
            if (columns[i] >> j) & 1:
                bits |= 1 << i
        if (target >> j) & 1:
            bits |= 1 << n
        base_rows.append(bits)

    syn_bit = 1 << n
    iters = 0

    while time.time() < deadline:
        iters += 1
        rows = list(base_rows)
        order = list(range(n))
        rng.shuffle(order)

        pivots = []          # pivots[t] = original column index pivoting row t
        used = bytearray(n)
        cursor = 0
        t = 0
        while t < r and cursor < n:
            c = order[cursor]
            cursor += 1
            # find a row >= t with a 1 in column c
            piv = -1
            for j in range(t, r):
                if (rows[j] >> c) & 1:
                    piv = j
                    break
            if piv < 0:
                continue                      # column dependent on chosen ones
            rows[t], rows[piv] = rows[piv], rows[t]
            rt = rows[t]
            for j in range(r):
                if j != t and ((rows[j] >> c) & 1):
                    rows[j] ^= rt
            pivots.append(c)
            used[c] = 1
            t += 1
        if t < r:
            continue                          # should not happen: H has full row rank

        free = [c for c in range(n) if not used[c]]

        # syndrome vector in the reduced basis: bit t = rows[t]'s augmented bit
        synvec = 0
        for tt in range(r):
            if rows[tt] & syn_bit:
                synvec |= 1 << tt
        # reduced free columns: bit t of rc[c] = rows[t][c]
        rc = {}
        for c in free:
            v = 0
            for tt in range(r):
                if (rows[tt] >> c) & 1:
                    v |= 1 << tt
            rc[c] = v

        def build(res, extra):
            sup = [pivots[tt] for tt in range(r) if (res >> tt) & 1] + list(extra)
            return sorted(sup)

        # p = 0
        if bin(synvec).count("1") == h:
            return build(synvec, []), iters

        if p_max >= 1:
            for c in free:
                v = synvec ^ rc[c]
                if bin(v).count("1") == h - 1:
                    return build(v, [c]), iters

        if p_max >= 2:
            m = len(free)
            for ia in range(m):
                a = free[ia]
                va = synvec ^ rc[a]
                for ib in range(ia + 1, m):
                    b = free[ib]
                    v = va ^ rc[b]
                    if bin(v).count("1") == h - 2:
                        return build(v, [a, b]), iters
    return None, iters


# ---------------------------------------------------------------- driver

def run(paper_dir, module_name, budget_s, seeds):
    mod = load(os.path.join(paper_dir, module_name))
    preset = mod.SHIPPING_DIFFICULTY
    params = dict(mod.DIFFICULTY[preset])
    print(f"paper dir     : {paper_dir}")
    print(f"preset        : {preset}  {params}")

    solved = 0
    times = []
    for s in seeds:
        inst = mod.make_instance(seed=s, **params)
        n, r, h = inst["n"], inst["rows"], inst["weight"]
        space = mod.search_space(inst)
        t0 = time.time()
        sup, iters = isd_solve(inst["columns"], inst["target"], n, r, h, budget_s, seed=s)
        el = time.time() - t0
        times.append(el)
        if sup is None:
            print(f"  seed {s:>6}  TIMEOUT after {el:6.2f}s ({iters} ISD iters)  -> NOT solved")
            continue
        answer = [i + 1 for i in sup]
        ok, reason = mod.verify(inst, answer)
        print(f"  seed {s:>6}  {el:6.2f}s  {iters:5d} ISD iters  verify={ok} ({reason})")
        if ok:
            solved += 1
    print(f"\n  space C({params['n']},{params['weight']}) = {space} = 2^{math.log2(space):.1f}")
    print(f"  SOLVED {solved}/{len(seeds)}   median {statistics.median(times):.2f}s"
          f"   mean {statistics.mean(times):.2f}s")
    return solved, statistics.median(times)


if __name__ == "__main__":
    budget = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    nseeds = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    seeds = [1, 2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31][:nseeds]
    print("=" * 74)
    print("2411.19413  exact-weight binary syndrome  --  Lee-Brickell ISD (p<=2)")
    print("=" * 74)
    run(os.path.join(ROOT, "results", "2411.19413"), "gen_2411_19413.py", budget, seeds)
