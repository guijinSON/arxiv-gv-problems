#!/usr/bin/env python3
"""Domain-standard attacks on the cover/design group.

  2411.14821  supported weakly-stable matching  -> the witness IS an Exact Cover
                by 3-Sets selector.  Algorithm X / DLX with fewest-options-first.
  2506.24001  LS Multi Knapsack (one knapsack)  -> the witness IS a fixed-
                cardinality subset sum.  Meet-in-the-middle (4-list / Schroeppel-
                Shamir style) with a modular filter, in numpy.
  2306.12713  graceful zillion graph            -> constraint search over the
                difference->edge assignment, largest-difference-first, with
                union-find so the required cycle-length profile prunes.

Every candidate is graded ONLY by the module's own verify().  inst["answer"] is
never read.

Usage:
    python3 audit/attack_cover_design.py x3c      [budget_s]
    python3 audit/attack_cover_design.py subsetsum[budget_s]
    python3 audit/attack_cover_design.py graceful [budget_s]
    python3 audit/attack_cover_design.py all      [budget_s]
"""
import importlib.util
import os
import random
import statistics
import sys
import time
from itertools import combinations

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEEDS = [1, 2, 3, 4, 5, 6, 7, 8]


def load(rel):
    path = os.path.join(ROOT, rel)
    spec = importlib.util.spec_from_file_location("m_" + os.path.basename(rel), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------
# 2411.14821 -- Exact Cover by 3-Sets.  Algorithm X with MRV column choice.
# --------------------------------------------------------------------------
def dlx_exact_cover(sets, n_elements, n_pick, deadline):
    """Algorithm X over bitmask rows.  Returns a list of row indices or None."""
    rows = [0] * len(sets)
    for i, t in enumerate(sets):
        m = 0
        for e in t:
            m |= 1 << e
        rows[i] = m
    by_elem = [[] for _ in range(n_elements)]
    for i, t in enumerate(sets):
        for e in t:
            by_elem[e].append(i)

    full = (1 << n_elements) - 1
    chosen = []
    nodes = [0]

    def rec(covered):
        if covered == full:
            return True
        nodes[0] += 1
        if not (nodes[0] & 0x3FF) and time.time() > deadline:
            raise TimeoutError
        # fewest-options-first: uncovered element with the fewest usable rows
        best_e, best_opts = -1, None
        rest = full & ~covered
        while rest:
            low = rest & -rest
            e = low.bit_length() - 1
            rest ^= low
            opts = [r for r in by_elem[e] if not (rows[r] & covered)]
            if best_opts is None or len(opts) < len(best_opts):
                best_e, best_opts = e, opts
                if len(opts) <= 1:
                    break
        if not best_opts:
            return False
        for r in best_opts:
            chosen.append(r)
            if rec(covered | rows[r]):
                return True
            chosen.pop()
        return False

    try:
        if rec(0):
            return sorted(chosen), nodes[0]
    except TimeoutError:
        return None, nodes[0]
    return None, nodes[0]


def attack_x3c(budget):
    mod = load("results/2411.14821/gen_2411_14821.py")
    params = mod.DIFFICULTY[mod.SHIPPING_DIFFICULTY]
    print(f"=== 2411.14821  preset={mod.SHIPPING_DIFFICULTY} {params} "
          f"attack=Algorithm X / DLX (MRV)  budget={budget}s/seed")
    wins, times = 0, []
    for sd in SEEDS:
        inst = mod.make_instance(seed=sd, **params)
        sets = [tuple(s) for s in inst["sets"]]
        t0 = time.time()
        cover, nodes = dlx_exact_cover(sets, int(inst["element_count"]),
                                       int(inst["n"]), t0 + budget)
        el = time.time() - t0
        times.append(el)
        ok, why = (False, "no cover found (timeout)")
        if cover is not None:
            ok, why = mod.verify(inst, list(cover))
        wins += bool(ok)
        print(f"  seed {sd}: sets={len(sets)} elems={inst['element_count']} "
              f"nodes={nodes:<7d} {el:7.3f}s -> {'SOLVED' if ok else 'failed: ' + why}")
    print(f"  RESULT 2411.14821: solved {wins}/{len(SEEDS)}  "
          f"median {statistics.median(times):.3f}s")
    return wins, statistics.median(times)


# --------------------------------------------------------------------------
# 2506.24001 -- fixed-cardinality subset sum.  Meet in the middle.
# --------------------------------------------------------------------------
def _quarter_tables(vals):
    """All subset sums of a <=16 element list, grouped by cardinality.

    Returns card -> (sums int64 array, masks int64 array of local bitmasks)."""
    q = len(vals)
    sums = np.zeros(1 << q, dtype=np.int64)
    for i, v in enumerate(vals):
        bit = 1 << i
        idx = np.arange(1 << q)
        sums[(idx & bit) != 0] += int(v)
    masks = np.arange(1 << q, dtype=np.int64)
    pc = np.zeros(1 << q, dtype=np.int8)
    m = masks.copy()
    while True:
        nz = m != 0
        if not nz.any():
            break
        pc += (m & 1).astype(np.int8)
        m >>= 1
    out = {}
    for c in range(q + 1):
        sel = pc == c
        out[c] = (sums[sel], masks[sel])
    return out


def _side_list(tabA, tabB, card, mod_m, resid, target_mod_base):
    """Sums of `card`-subsets of quarterA+quarterB that are == resid (mod m).

    Returns a single int64 array of sums (values only)."""
    chunks = []
    for c1 in range(0, card + 1):
        c2 = card - c1
        if c1 not in tabA or c2 not in tabB:
            continue
        s1, _ = tabA[c1]
        s2, _ = tabB[c2]
        if s1.size == 0 or s2.size == 0:
            continue
        r1 = (s1 % mod_m).astype(np.int64)
        r2 = (s2 % mod_m).astype(np.int64)
        o1 = np.argsort(r1, kind="stable")
        o2 = np.argsort(r2, kind="stable")
        s1s, r1s = s1[o1], r1[o1]
        s2s, r2s = s2[o2], r2[o2]
        b1 = np.searchsorted(r1s, np.arange(mod_m + 1))
        b2 = np.searchsorted(r2s, np.arange(mod_m + 1))
        for u in range(mod_m):
            a = s1s[b1[u]:b1[u + 1]]
            if a.size == 0:
                continue
            w = (resid - u) % mod_m
            b = s2s[b2[w]:b2[w + 1]]
            if b.size == 0:
                continue
            chunks.append((a[:, None] + b[None, :]).ravel())
    if not chunks:
        return np.zeros(0, dtype=np.int64)
    return np.concatenate(chunks)


def _recover(tabA, tabB, card, want):
    """Find (maskA, cardA, maskB, cardB) with the exact sum `want`."""
    for c1 in range(0, card + 1):
        c2 = card - c1
        if c1 not in tabA or c2 not in tabB:
            continue
        s1, m1 = tabA[c1]
        s2, m2 = tabB[c2]
        if s1.size == 0 or s2.size == 0:
            continue
        d1 = {}
        for i in range(s1.size):
            d1.setdefault(int(s1[i]), int(m1[i]))
        for i in range(s2.size):
            need = want - int(s2[i])
            if need in d1:
                return d1[need], c1, int(m2[i]), c2
    return None


def mitm_subset_sum(offsets, target, card, deadline, rng):
    """Find `card` indices of `offsets` summing exactly to `target`."""
    n = len(offsets)
    idx = list(range(n))
    rng.shuffle(idx)
    quarters = [idx[0:16], idx[16:32], idx[32:48], idx[48:64]]
    tabs = [_quarter_tables([offsets[i] for i in q]) for q in quarters]

    mod_m = 16
    splits = [(card // 2, card - card // 2), (card - card // 2, card // 2),
              (card // 2 - 1, card - card // 2 + 1),
              (card // 2 + 2, card - card // 2 - 2)]
    seen = set()
    for jA, jB in splits:
        if (jA, jB) in seen or jA < 0 or jB < 0 or jA > 32 or jB > 32:
            continue
        seen.add((jA, jB))
        for r in range(mod_m):
            if time.time() > deadline:
                return None
            listA = _side_list(tabs[0], tabs[1], jA, mod_m, r, target)
            if listA.size == 0:
                continue
            rB = (target - r) % mod_m
            listB = _side_list(tabs[2], tabs[3], jB, mod_m, rB, target)
            if listB.size == 0:
                continue
            listA.sort()
            need = target - listB
            pos = np.searchsorted(listA, need)
            pos[pos >= listA.size] = 0
            hit = listA[pos] == need
            if not hit.any():
                continue
            sB = int(listB[np.flatnonzero(hit)[0]])
            sA = target - sB
            ra = _recover(tabs[0], tabs[1], jA, sA)
            rb = _recover(tabs[2], tabs[3], jB, sB)
            if ra is None or rb is None:
                continue
            picked = []
            for (mask, _c), qlist in ((ra[0:2], quarters[0]), (ra[2:4], quarters[1]),
                                      (rb[0:2], quarters[2]), (rb[2:4], quarters[3])):
                for b in range(16):
                    if mask >> b & 1:
                        picked.append(qlist[b])
            if len(picked) == card and sum(offsets[i] for i in picked) == target:
                return picked
    return None


def attack_subsetsum(budget):
    mod = load("results/2506.24001/gen_2506_24001.py")
    params = mod.DIFFICULTY[mod.SHIPPING_DIFFICULTY]
    print(f"=== 2506.24001  preset={mod.SHIPPING_DIFFICULTY} {params} "
          f"attack=meet-in-the-middle (4-list, mod filter)  budget={budget}s/seed")
    wins, times = 0, []
    for sd in SEEDS:
        inst = mod.make_instance(seed=sd, **params)
        ordinary = [it for it in inst["items"] if it["id"] != inst["special_id"]]
        ids = [it["id"] for it in ordinary]
        base = min(it["weight"] for it in ordinary)
        d = int(inst["required_removals"])
        offs = [it["weight"] - base for it in ordinary]
        tgt = int(inst["removal_target"]) - d * base
        t0 = time.time()
        picked = mitm_subset_sum(offs, tgt, d, t0 + budget, random.Random(1000 + sd))
        el = time.time() - t0
        times.append(el)
        ok, why = (False, "no subset found (timeout)")
        if picked is not None:
            ok, why = mod.verify(inst, sorted(ids[i] for i in picked))
        wins += bool(ok)
        print(f"  seed {sd}: n={inst['n']} d={d} bits={inst['value_bits']} "
              f"{el:7.3f}s -> {'SOLVED' if ok else 'failed: ' + why}")
    print(f"  RESULT 2506.24001: solved {wins}/{len(SEEDS)}  "
          f"median {statistics.median(times):.3f}s")
    return wins, statistics.median(times)


# --------------------------------------------------------------------------
# 2306.12713 -- graceful labeling of one path + prescribed cycles.
# Constraint search: assign every difference 1..a to an edge (s, s+d) with all
# degrees in {1,2}; union-find tracks chains so the required cycle-length
# multiset prunes every closure.
# --------------------------------------------------------------------------
class GracefulSearch:
    """Assign every difference d=1..a to an edge (s, s+d).

    All degrees must land in {1,2}; the union-find keeps every open chain's
    vertex count so the prescribed cycle-length multiset prunes each closure and
    each merge.  Differences are chosen most-constrained-first, candidates in
    random order, with restarts on a growing node cap.
    """

    def __init__(self, a, k, cycle_lengths, rng):
        self.a = a
        self.k = k
        self.rng = rng
        self.cycle_lengths = list(cycle_lengths)
        self.nodes = 0

    def solve(self, deadline, node_cap):
        a = self.a
        self.deg = [0] * (a + 1)
        self.par = list(range(a + 1))
        self.csize = [1] * (a + 1)
        self.free = (1 << (a + 1)) - 1
        self.rem = set(range(1, a + 1))
        self.assign = {}
        self.need = {}
        for L in self.cycle_lengths:
            self.need[L] = self.need.get(L, 0) + 1
        self.open_sizes = {1: a + 1}          # multiset of open-chain vertex counts
        self.iso = a + 1                      # vertices of degree 0
        self.deadline = deadline
        self.node_cap = node_cap
        self.nodes = 0
        try:
            if self._rec():
                return dict(self.assign)
        except (TimeoutError, RuntimeError):
            return None
        return None

    def find(self, x):
        # No path compression: the search backtracks, and compression would
        # leave stale parent pointers after a union is rolled back.
        p = self.par
        while p[x] != x:
            x = p[x]
        return x

    def _bump(self, size, delta):
        c = self.open_sizes.get(size, 0) + delta
        if c:
            self.open_sizes[size] = c
        else:
            del self.open_sizes[size]

    def _profile_ok(self):
        """Sound prune: open chains larger than x must land in targets >= x."""
        sizes = self.open_sizes
        targets = dict(self.need)
        targets[self.k + 1] = targets.get(self.k + 1, 0) + 1
        tmax = max(targets)
        if max(sizes) > tmax:
            return False
        for x in sizes:
            if x == 1:
                continue
            sa = sum(s * c for s, c in sizes.items() if s >= x)
            ta = sum(t * c for t, c in targets.items() if t >= x)
            if sa > ta:
                return False
        return True

    def _rec(self):
        self.nodes += 1
        if self.nodes > self.node_cap:
            raise RuntimeError("node cap")
        if not (self.nodes & 0xFF) and time.time() > self.deadline:
            raise TimeoutError
        if not self.rem:
            return (self.free.bit_count() == 2 and self.iso == 0
                    and not self.need)

        free = self.free
        best_d, best_cnt, best_bits = -1, 1 << 30, 0
        for d in self.rem:
            bits = free & (free >> d)
            c = bits.bit_count()
            if c == 0:
                return False
            if c < best_cnt:
                best_d, best_cnt, best_bits = d, c, bits
                if c == 1:
                    break
        d, bits = best_d, best_bits
        starts = []
        while bits:
            low = bits & -bits
            starts.append(low.bit_length() - 1)
            bits ^= low
        self.rng.shuffle(starts)

        self.rem.discard(d)
        nrem = len(self.rem)
        cap = max(self.k + 1, max(self.need) if self.need else 0)
        for s in starts:
            e = s + d
            rs, re = self.find(s), self.find(e)
            closing = rs == re
            if closing:
                L = self.csize[rs]
                if L < 3 or self.need.get(L, 0) == 0:
                    continue
            else:
                if self.csize[rs] + self.csize[re] > cap:
                    continue

            diso = (self.deg[s] == 0) + (self.deg[e] == 0)
            self.deg[s] += 1
            self.deg[e] += 1
            self.iso -= diso
            oldfree = self.free
            if self.deg[s] == 2:
                self.free &= ~(1 << s)
            if self.deg[e] == 2:
                self.free &= ~(1 << e)
            if closing:
                L = self.csize[rs]
                self.need[L] -= 1
                if not self.need[L]:
                    del self.need[L]
                self._bump(L, -1)
                undo = (0, rs, L)
            else:
                if self.csize[rs] < self.csize[re]:
                    rs, re = re, rs
                sa, sb = self.csize[rs], self.csize[re]
                self._bump(sa, -1)
                self._bump(sb, -1)
                self._bump(sa + sb, +1)
                self.par[re] = rs
                self.csize[rs] = sa + sb
                undo = (1, rs, re, sa, sb)
            self.assign[d] = s

            if self.iso <= 2 * nrem and self._profile_ok() and self._rec():
                return True

            del self.assign[d]
            if undo[0] == 0:
                self.need[undo[2]] = self.need.get(undo[2], 0) + 1
                self._bump(undo[2], +1)
            else:
                _, rr, rc, sa, sb = undo
                self.par[rc] = rc
                self.csize[rr] = sa
                self._bump(sa + sb, -1)
                self._bump(sa, +1)
                self._bump(sb, +1)
            self.free = oldfree
            self.deg[s] -= 1
            self.deg[e] -= 1
            self.iso += diso
        self.rem.add(d)
        return False


def _components_from_assign(a, assign):
    adj = [[] for _ in range(a + 1)]
    for d, s in assign.items():
        adj[s].append(s + d)
        adj[s + d].append(s)
    endpoints = [v for v in range(a + 1) if len(adj[v]) == 1]
    if len(endpoints) != 2:
        return None, None
    path, prev, cur = [], None, endpoints[0]
    while True:
        path.append(cur)
        nxt = [v for v in adj[cur] if v != prev]
        if not nxt:
            break
        prev, cur = cur, nxt[0]
    seen = set(path)
    cycles = []
    for start in range(a + 1):
        if start in seen:
            continue
        cyc, prev, cur = [start], None, start
        seen.add(start)
        while True:
            opts = [v for v in adj[cur] if v != prev]
            nv = opts[0]
            if nv == start:
                break
            cyc.append(nv)
            seen.add(nv)
            prev, cur = cur, nv
        cycles.append(cyc)
    return path, cycles


def attack_graceful(budget):
    mod = load("results/2306.12713/gen_2306_12713.py")
    params = mod.DIFFICULTY[mod.SHIPPING_DIFFICULTY]
    print(f"=== 2306.12713  preset={mod.SHIPPING_DIFFICULTY} {params} "
          f"attack=profile-constrained difference search (largest-first + restarts)"
          f"  budget={budget}s/seed")
    wins, times = 0, []
    for sd in SEEDS:
        inst = mod.make_instance(seed=sd, **params)
        a = int(inst["path_edges"]) + sum(inst["cycle_lengths"])
        k = int(inst["path_edges"])
        L = list(inst["cycle_lengths"])
        t0 = time.time()
        deadline = t0 + budget
        rng = random.Random(7000 + sd)
        answer, restarts, cap = None, 0, 4000
        while time.time() < deadline and answer is None:
            g = GracefulSearch(a, k, L, rng)
            assign = g.solve(deadline, cap)
            restarts += 1
            if assign is not None:
                path, cycles = _components_from_assign(a, assign)
                if path is not None:
                    answer = {"path": path, "cycles": cycles}
            cap = min(cap * 2, 400_000)
        el = time.time() - t0
        times.append(el)
        ok, why = (False, "no labeling found (timeout)")
        if answer is not None:
            ok, why = mod.verify(inst, answer)
        wins += bool(ok)
        print(f"  seed {sd}: a={a} path_edges={k} cycles={sorted(L)} "
              f"restarts={restarts} {el:7.3f}s -> "
              f"{'SOLVED' if ok else 'failed: ' + why}")
    print(f"  RESULT 2306.12713: solved {wins}/{len(SEEDS)}  "
          f"median {statistics.median(times):.3f}s")
    return wins, statistics.median(times)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    budget = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
    if which in ("x3c", "all"):
        attack_x3c(budget)
    if which in ("subsetsum", "all"):
        attack_subsetsum(budget)
    if which in ("graceful", "all"):
        attack_graceful(budget)
