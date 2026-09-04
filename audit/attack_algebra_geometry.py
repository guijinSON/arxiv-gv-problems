#!/usr/bin/env python3
"""Domain-standard attacks on the three shipped `algebra-geometry` families whose
G6 panel ran only the generic outlier / greedy / random-restart probes.

  2205.04710  matrix Waring  A^k+B^k=T over F_p, 2x2, k=2^24
                -> the paper's OWN blockwise reduction (Jordan/rational canonical
                   form) plus a meet-in-the-middle in the character group
                   F_p^* / (F_p^*)^k.
  2511.01003  "Dillon hexanomial CCZ"
                -> the solver is actually handed two 64-point subsets of GF(2)^12,
                   i.e. binary affine point-set / code equivalence.  Standard
                   attack: XOR-autocorrelation (Walsh) invariants + individual-
                   ization-refinement backtracking.
  2411.04916  "kissing numbers"
                -> the solver is actually handed a 5-regular graph on 108
                   vertices.  Standard attack: DSATUR order + backtracking with
                   unit propagation (exact 3-colouring).

Every verdict is decided by the module's own verify(inst, answer).  No attack
reads inst["answer"].

Usage:
    python3 audit/attack_algebra_geometry.py all
    python3 audit/attack_algebra_geometry.py waring --seeds 1 2 3 --budget 90
    python3 audit/attack_algebra_geometry.py colour --preset hard
"""
from __future__ import annotations

import argparse
import collections
import importlib.util
import math
import os
import random
import sys
import time

RESULTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
DEFAULT_SEEDS = [1, 2, 3, 4, 5, 6, 7, 8]


def load(paper: str, mod: str):
    path = os.path.normpath(os.path.join(RESULTS, paper, mod + ".py"))
    spec = importlib.util.spec_from_file_location(mod, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ===========================================================================
# 2205.04710 -- matrix Waring
# ===========================================================================
#
# Attack outline (all of it is textbook for this class):
#
#  * k-th powers of 2x2 matrices are completely understood through the
#    canonical form, exactly as the paper's constructive proof does it:
#      - X diagonalisable with distinct eigenvalues x1 != x2 is a k-th power
#        iff x1,x2 lie in K = (F_p^*)^k, and then A = alpha*X + beta*I with
#        alpha=(a-b)/(x1-x2), beta=a-alpha*x1, a^k=x1, b^k=x2.
#      - Y with a repeated eigenvalue s (so Y = sI+M, M^2=0) is a k-th power
#        iff s in K, and then B = w*(I + M/(k*s)) with w^k = s.
#  * So it suffices to split T = X + Y with spec(X)={x1,x2} subset K and
#    spec(Y)={s,s}, s in K.  The trace constraint is x1+x2+2s = tr(T); the
#    remaining conditions (det X = x1x2, det Y = s^2) are one linear plus one
#    quadratic equation in the four entries of X, so X is recovered by solving
#    a quadratic over F_p.
#  * That leaves the scalar problem "x1+x2 = c with x1,x2 in K".  The naive
#    version costs |F_p^*/K| = k = 2^24 character tests -- the cost the README
#    advertises.  But s is FREE, so c = tr(T)-2s is a free parameter too:
#    build L targets c_j = tr(T)-2*w_j^k, then walk rho over K testing
#    chi(1+rho) against the whole table at once.  A collision needs only
#    ~2^24/L trials; with L = 4096 the total is ~2*2^12 modular exponentiations.
#    This is a plain meet-in-the-middle in F_p^*/K, which is cyclic of order
#    2^24 because p-1 = coefficient*2^(16n) is a Proth prime.

def _factor_small(x: int) -> dict:
    f: dict = {}
    d = 2
    while d * d <= x:
        while x % d == 0:
            f[d] = f.get(d, 0) + 1
            x //= d
        d += 1
    if x > 1:
        f[x] = f.get(x, 0) + 1
    return f


class SmoothField:
    """F_p^* with p-1 = odd * 2^S smooth enough for Pohlig-Hellman dlogs."""

    def __init__(self, p: int):
        self.p = p
        self.N = p - 1
        self.S = 0
        t = self.N
        while t % 2 == 0:
            t //= 2
            self.S += 1
        self.odd = t
        self.fac = _factor_small(self.odd)
        primes = [2] + sorted(self.fac)
        g = 2
        while any(pow(g, self.N // r, p) == 1 for r in primes):
            g += 1
        self.g = g
        self.g2 = pow(g, self.odd, p)                    # generates the 2-Sylow
        inv = pow(self.g2, p - 2, p)
        self.g2inv_pow = []
        for _ in range(self.S):
            self.g2inv_pow.append(inv)
            inv = inv * inv % p

    def _dlog2(self, y: int) -> int:
        p, S = self.p, self.S
        x, acc = 0, y
        for i in range(S):
            t = acc
            for _ in range(S - 1 - i):
                t = t * t % p
            if t != 1:
                x |= 1 << i
                acc = acc * self.g2inv_pow[i] % p
        return x

    def dlog(self, y: int) -> int:
        p, N = self.p, self.N
        residues = [(1 << self.S, self._dlog2(pow(y, self.odd, p)))]
        for q, e in self.fac.items():
            qe = q ** e
            gq = pow(self.g, N // qe, p)
            yq = pow(y, N // qe, p)
            cur, found = 1, None
            for j in range(qe):
                if cur == yq:
                    found = j
                    break
                cur = cur * gq % p
            if found is None:
                raise ArithmeticError("dlog failed on odd part")
            residues.append((qe, found))
        mod_all, x = 1, 0
        for mod, res in residues:
            step = ((res - x) * pow(mod_all % mod, -1, mod)) % mod
            x += mod_all * step
            mod_all *= mod
        if pow(self.g, x, p) != y % p:
            raise ArithmeticError("dlog verification failed")
        return x

    def kth_root(self, y: int, k: int) -> int:
        x = self.dlog(y)
        if x % k:
            raise ArithmeticError("argument is not a k-th power")
        return pow(self.g, x // k, self.p)

    def sqrt(self, y: int):
        x = self.dlog(y)
        return None if x % 2 else pow(self.g, x // 2, self.p)


def attack_waring(inst: dict, budget: float, table_size: int | None = None,
                  rng_seed: int = 0, verbose: bool = False):
    t0 = time.time()
    p, k, T = inst["p"], inst["k"], inst["target"]
    # balanced meet-in-the-middle: table side ~ sqrt(index of K) = sqrt(k)
    if table_size is None:
        table_size = max(256, math.isqrt(k))
    field = SmoothField(p)
    chi_exp = (p - 1) // k                      # v^chi_exp == 1  <=>  v in K
    rng = random.Random(rng_seed)
    (T00, T01), (T10, T11) = T[0], T[1]
    trT = (T00 + T11) % p
    detT = (T00 * T11 - T01 * T10) % p

    # ---- side A: L free targets c_j = tr(T) - 2*s_j with s_j = w_j^k in K
    table = {}
    for _ in range(table_size):
        if time.time() - t0 > budget:
            return None, time.time() - t0, 0
        w = rng.randrange(2, p)
        s = pow(w, k, p)
        c = (trT - 2 * s) % p
        if c:
            table.setdefault(pow(c, chi_exp, p), (c, s, w))
    if verbose:
        print(f"    table: {len(table)} classes  ({time.time()-t0:.1f}s)", flush=True)

    # ---- side B: walk rho over K, test chi(1+rho) against the whole table
    g = field.g
    r0 = rng.randrange(2, p)
    G = pow(g, k, p)
    rho = pow(r0, k, p)
    hit, trials = None, 0
    while time.time() - t0 < budget:
        trials += 1
        rho = rho * G % p
        if rho == 1:
            continue
        v = (1 + rho) % p
        if v == 0:
            continue
        got = table.get(pow(v, chi_exp, p))
        if got is not None:
            hit = (got, rho, trials)
            break
    if hit is None:
        return None, time.time() - t0, trials
    (c_j, s, w), rho, trials = hit
    if verbose:
        print(f"    character collision after {trials} trials "
              f"({time.time()-t0:.1f}s)", flush=True)

    # ---- scalar witnesses:  x1 + x2 = c_j,  both k-th powers, roots known
    r = r0 * pow(g, trials, p) % p
    x2 = c_j * pow(1 + rho, p - 2, p) % p
    x1 = rho * x2 % p
    root2 = field.kth_root(x2, k)
    root1 = r * root2 % p
    assert pow(root1, k, p) == x1 and pow(root2, k, p) == x2

    # ---- solve for X:  tr X = x1+x2, det X = x1x2, det(T-X) = s^2
    tX, dX = c_j, x1 * x2 % p
    R2 = (detT + dX - s * s) % p
    R3 = (R2 - T00 * tX) % p
    invT01 = pow(T01, p - 2, p)
    inv2T10 = pow(2 * T10 % p, p - 2, p)
    X = None
    for _ in range(400):
        if time.time() - t0 > budget:
            return None, time.time() - t0, trials
        q = rng.randrange(p)
        B1 = (R3 - q * (T11 - T00)) % p
        C1 = T01 * (q * tX - q * q - dX) % p
        disc = (B1 * B1 - 4 * T10 * C1) % p
        if disc == 0 or pow(disc, (p - 1) // 2, p) != 1:
            continue
        sq = field.sqrt(disc)
        if sq is None:
            continue
        u = (-B1 + sq) * inv2T10 % p
        wv = (q * (T11 - T00) - T10 * u - R3) * invT01 % p
        X = [[q % p, u], [wv, (tX - q) % p]]
        break
    if X is None:
        return None, time.time() - t0, trials
    Y = [[(T[i][j] - X[i][j]) % p for j in range(2)] for i in range(2)]

    # ---- k-th roots of the two blocks
    alpha = (root1 - root2) * pow(x1 - x2, p - 2, p) % p
    beta = (root1 - alpha * x1) % p
    A = [[(alpha * X[0][0] + beta) % p, alpha * X[0][1] % p],
         [alpha * X[1][0] % p, (alpha * X[1][1] + beta) % p]]
    inv_ks = pow(k * s % p, p - 2, p)
    B = [[w * (1 + (Y[0][0] - s) * inv_ks) % p, w * Y[0][1] % p * inv_ks % p],
         [w * Y[1][0] % p * inv_ks % p, w * (1 + (Y[1][1] - s) * inv_ks) % p]]
    return {"A": A, "B": B}, time.time() - t0, trials


# ===========================================================================
# 2511.01003 -- binary affine point-set equivalence  (the "CCZ" family)
# ===========================================================================
#
# The solver is handed two unordered 64-point subsets S,T of GF(2)^12 and must
# find M in GL(12,2), t with M(S)+t = T.  Standard attack for point-set / code
# equivalence: compute a complete family of linear invariants, then do
# individualization-refinement backtracking over a source basis.
#
# Invariants: with the Walsh-Hadamard transform F = WHT(1_S),
#     C_j(v) = #{(a_1..a_j) in S^j : a_1 ^ ... ^ a_j = v} = IWHT(F^j)(v).
# For EVEN j these are invariant under translation of S and equivariant under
# the linear part:  C_j^T(Mv) = C_j^S(v).  The tuple (C_2,C_4,C_6,C_8) already
# splits GF(2)^12 into classes of size 1,1,1,6,8,9,22,24,... so a basis can be
# individualised out of the rare classes and every partial assignment is checked
# on the whole span it generates.  The offset is then read off in 64 tries.

def _wht(a):
    """In-place-style vectorised Walsh-Hadamard transform (no normalisation)."""
    a = a.copy()
    n = len(a)
    h = 1
    while h < n:
        b = a.reshape(-1, 2, h)
        x = b[:, 0, :].copy()
        y = b[:, 1, :].copy()
        b[:, 0, :] = x + y
        b[:, 1, :] = x - y
        h *= 2
    return a


def _xor_colours(points, width):
    """(C_2, C_4, ...) as an integer label per point of GF(2)^width."""
    import numpy as np
    n = 1 << width
    ind = np.zeros(n, dtype=np.int64)
    ind[list(points)] = 1
    F = _wht(ind)
    size = len(points)
    ks = []
    j = 2
    # keep n * size**j inside int64
    while j <= 8 and (width + j * max(1, size.bit_length() - 1)) < 62:
        ks.append(j)
        j += 2
    return np.stack([_wht(F ** j) // n for j in ks], axis=1)


def attack_ccz(inst: dict, budget: float, verbose: bool = False):
    t0 = time.time()
    width = inst["ambient_width"]
    n = 1 << width
    S, T = list(inst["source"]), list(inst["target"])
    colS, colT = _xor_colours(S, width), _xor_colours(T, width)
    labels: dict = {}

    def lab(row):
        key = tuple(row)
        if key not in labels:
            labels[key] = len(labels)
        return labels[key]

    labS = [lab(r) for r in colS]
    labT = [lab(r) for r in colT]
    if collections.Counter(labS) != collections.Counter(labT):
        return None, time.time() - t0, 0
    class_T = collections.defaultdict(list)
    for v, c in enumerate(labT):
        class_T[c].append(v)
    size_S = collections.Counter(labS)
    if verbose:
        hist = collections.Counter(size_S.values())
        print(f"    colour classes {len(size_S)}; size histogram "
              f"{dict(sorted(hist.items()))}", flush=True)

    # individualise the source basis, rarest colour class first
    basis, pivots = [], [0] * width
    for v in sorted(range(1, n), key=lambda x: (size_S[labS[x]], x)):
        x = v
        while x:
            b = x.bit_length() - 1
            if pivots[b]:
                x ^= pivots[b]
            else:
                pivots[b] = x
                basis.append(v)
                break
        if len(basis) == width:
            break
    if len(basis) != width:
        return None, time.time() - t0, 0

    Tset = set(T)
    leaves = [0]
    deadline = t0 + budget

    def rec(j, span_src, span_img):
        if time.time() > deadline:
            raise TimeoutError
        if j == width:
            leaves[0] += 1
            table = dict(zip(span_src, span_img))
            image = [table[x] for x in S]
            base, iset = image[0], set(image)
            for y in T:
                shift = base ^ y
                if {x ^ shift for x in iset} == Tset:
                    return table, shift
            return None
        b = basis[j]
        want = labS[b]
        seen = set(span_img)
        for y in class_T[want]:
            if y in seen:
                continue
            ok = True
            new_src, new_img = [], []
            for u, iu in zip(span_src, span_img):
                ns, ni = u ^ b, iu ^ y
                if labT[ni] != labS[ns]:
                    ok = False
                    break
                new_src.append(ns)
                new_img.append(ni)
            if not ok:
                continue
            got = rec(j + 1, span_src + new_src, span_img + new_img)
            if got is not None:
                return got
        return None

    try:
        out = rec(0, [0], [0])
    except TimeoutError:
        return None, time.time() - t0, leaves[0]
    if out is None:
        return None, time.time() - t0, leaves[0]
    table, shift = out
    cols = [table[1 << i] for i in range(width)]
    rows = []
    for i in range(width):
        row = 0
        for j in range(width):
            if (cols[j] >> (width - 1 - i)) & 1:
                row |= 1 << j
        rows.append(row)
    return {"matrix": rows, "offset": shift}, time.time() - t0, leaves[0]


# ===========================================================================
# 2411.04916 -- exact 3-colouring  (the "kissing number" family)
# ===========================================================================
#
# The rendered instance is BASE_EDGES: a 5-regular graph on n vertices, plus a
# formula that turns "proper 3-colouring" into "pairwise inner product <= 1/2".
# The solver never sees a vector.  Standard attack: DSATUR variable order with
# unit propagation and chronological backtracking -- an exact solver.

def attack_colour(inst: dict, budget: float, verbose: bool = False):
    t0 = time.time()
    n, adj = inst["n"], inst["adjacency"]
    deadline = t0 + budget
    dom = [0b111] * n
    col = [-1] * n
    nodes = [0]

    def assign(v, c, trail):
        stack = [(v, c)]
        while stack:
            u, cc = stack.pop()
            if col[u] == cc:
                continue
            if col[u] != -1 or not (dom[u] >> cc) & 1:
                return False
            col[u] = cc
            trail.append((u, dom[u], True))
            dom[u] = 1 << cc
            for w in adj[u]:
                if col[w] == cc:
                    return False
                if col[w] == -1 and (dom[w] >> cc) & 1:
                    trail.append((w, dom[w], False))
                    dom[w] &= ~(1 << cc)
                    if dom[w] == 0:
                        return False
                    if dom[w].bit_count() == 1:
                        stack.append((w, dom[w].bit_length() - 1))
        return True

    def undo(trail):
        while trail:
            u, old, was_col = trail.pop()
            dom[u] = old
            if was_col:
                col[u] = -1

    def pick():
        best, best_key = -1, None
        for v in range(n):
            if col[v] != -1:
                continue
            key = (dom[v].bit_count(), -sum(1 for w in adj[v] if col[w] != -1))
            if best_key is None or key < best_key:
                best_key, best = key, v
        return best

    def rec():
        if time.time() > deadline:
            raise TimeoutError
        v = pick()
        if v == -1:
            return True
        nodes[0] += 1
        for c in range(3):
            if not (dom[v] >> c) & 1:
                continue
            trail = []
            if assign(v, c, trail) and rec():
                return True
            undo(trail)
        return False

    trail = []
    assign(0, 0, trail)          # colour-permutation symmetry break
    assign(adj[0][0], 1, trail)
    try:
        ok = rec()
    except TimeoutError:
        return None, time.time() - t0, nodes[0]
    if not ok:
        return None, time.time() - t0, nodes[0]
    answer = sorted(3 * v + col[v] for v in range(n))
    return answer, time.time() - t0, nodes[0]


# ===========================================================================
# driver
# ===========================================================================

JOBS = {
    "waring": ("2205.04710", "gen_2205_04710", attack_waring, "matrix Waring A^k+B^k=T"),
    "ccz":    ("2511.01003", "gen_2511_01003", attack_ccz, "binary affine point-set equivalence"),
    "colour": ("2411.04916", "gen_2411_04916", attack_colour, "exact 3-colouring"),
}


def run(job: str, seeds, budget: float, preset: str | None, verbose: bool):
    paper, modname, attack, label = JOBS[job]
    mod = load(paper, modname)
    name = preset or mod.SHIPPING_DIFFICULTY
    params = dict(mod.DIFFICULTY[name])
    print(f"\n=== {paper}  [{job}]  preset={name} {params}  ({label})")
    print(f"    budget {budget:.0f}s/seed, graded by {modname}.verify()")
    solved, times = 0, []
    for seed in seeds:
        gen0 = time.time()
        inst = mod.make_instance(seed=seed, **params)
        gen = time.time() - gen0
        answer, elapsed, work = attack(inst, budget, verbose=verbose)
        if answer is None:
            times.append(budget)
            print(f"  seed {seed:>4}: FAILED/timeout after {elapsed:6.2f}s "
                  f"(work={work}, gen={gen:.1f}s)")
            continue
        ok, reason = mod.verify(inst, answer)
        solved += bool(ok)
        times.append(elapsed)
        print(f"  seed {seed:>4}: verify={ok} ({reason})  {elapsed:6.2f}s  "
              f"work={work}  (gen={gen:.1f}s)")
    times.sort()
    median = times[len(times) // 2] if times else float("nan")
    verdict = "BROKEN" if solved else "SURVIVED"
    print(f"  --> {paper}: solved {solved}/{len(seeds)}  median {median:.2f}s  "
          f"VERDICT {verdict}")
    return solved, len(seeds), median, verdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job", choices=list(JOBS) + ["all"])
    ap.add_argument("--seeds", type=int, nargs="*", default=DEFAULT_SEEDS)
    ap.add_argument("--budget", type=float, default=90.0)
    ap.add_argument("--preset", default=None)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    sys.setrecursionlimit(100000)
    jobs = list(JOBS) if args.job == "all" else [args.job]
    rows = []
    for job in jobs:
        rows.append((JOBS[job][0], job) + run(job, args.seeds, args.budget,
                                              args.preset, args.verbose))
    print("\n" + "=" * 78)
    for paper, job, solved, total, median, verdict in rows:
        print(f"{paper}  {job:<7}  solved {solved}/{total}  "
              f"median {median:6.2f}s  {verdict}")


if __name__ == "__main__":
    main()
