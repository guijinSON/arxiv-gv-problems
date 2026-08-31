"""Capsets in F_3^n.  Points are ints 0..3^n-1 read as base-3 digit vectors.

capset      : no three distinct points on a line, i.e. for all distinct a,b in C,
              -(a+b) not in C.   (that third point is automatically != a,b)
complete    : maximal -- every x outside C lies on a line through two points of C,
              i.e. every x not in C equals -(a+b) for some distinct a,b in C.
"""
def tables(n):
    N = 3 ** n
    dig = [None] * N
    for x in range(N):
        d, t = [], x
        for _ in range(n):
            d.append(t % 3); t //= 3
        dig[x] = d
    pw = [3 ** i for i in range(n)]
    neg = [sum(((-d) % 3) * p for d, p in zip(dig[x], pw)) for x in range(N)]
    return dig, pw, neg

def add(x, y, dig, pw):
    return sum(((a + b) % 3) * p for a, b, p in zip(dig[x], dig[y], pw))

def is_capset(C, n, T=None):
    dig, pw, neg = T or tables(n)
    S = set(C)
    if len(S) != len(C): return False, "duplicate points"
    L = sorted(S)
    for i, a in enumerate(L):
        for b in L[i + 1:]:
            if neg[add(a, b, dig, pw)] in S:
                return False, f"collinear triple {a},{b},{neg[add(a,b,dig,pw)]}"
    return True, "ok"

def is_complete(C, n, T=None):
    """Assumes C is a capset. Returns (bool, #uncovered outside points)."""
    dig, pw, neg = T or tables(n)
    S = set(C); L = sorted(S)
    covered = bytearray(3 ** n)
    for i, a in enumerate(L):
        for b in L[i + 1:]:
            covered[neg[add(a, b, dig, pw)]] = 1
    bad = [x for x in range(3 ** n) if x not in S and not covered[x]]
    return (not bad), len(bad)

def greedy_maximal(n, rng, seed_pts=(), T=None):
    """Extend seed_pts to a MAXIMAL capset by random greedy. Always succeeds."""
    dig, pw, neg = T or tables(n)
    C = list(seed_pts); S = set(C)
    blocked = set()          # points that would create a collinear triple
    for i, a in enumerate(C):
        for b in C[i + 1:]:
            blocked.add(neg[add(a, b, dig, pw)])
    order = list(range(3 ** n)); rng.shuffle(order)
    for x in order:
        if x in S or x in blocked: continue
        for a in C: blocked.add(neg[add(a, x, dig, pw)])
        C.append(x); S.add(x)
    return sorted(C)

def two_conics(m):
    """Theorem 2.1: C = {(x,x^2)} u {(x,-x^2)}, x in F_q*, q=3^m, viewed in F_3^(2m).
    Complete capset of size 2(q-1) when m is odd.  Returns points of F_3^(2m)."""
    q = 3 ** m
    # build F_q = F_3[t]/(f) with f a monic irreducible of degree m
    f = _irreducible(m)
    def mulf(a, b):                       # a,b as coefficient lists length m
        res = [0] * (2 * m - 1)
        for i, ai in enumerate(a):
            if ai:
                for j, bj in enumerate(b):
                    res[i + j] = (res[i + j] + ai * bj) % 3
        for i in range(2 * m - 2, m - 1, -1):   # reduce
            c = res[i]
            if c:
                res[i] = 0
                for j in range(m):
                    res[i - m + j] = (res[i - m + j] - c * f[j]) % 3
        return res[:m]
    pts = []
    for k in range(1, q):                 # x ranges over F_q^*
        x = [(k // 3 ** i) % 3 for i in range(m)]
        x2 = mulf(x, x)
        nx2 = [(-c) % 3 for c in x2]
        for y in (x2, nx2):
            v = x + y                     # (x,y) in F_q^2 = F_3^(2m)
            pts.append(sum(c * 3 ** i for i, c in enumerate(v)))
    return sorted(set(pts))

def _irreducible(m):
    """Monic irreducible f of degree m over F_3, returned as its low-m coeffs
    (so t^m = -(f[0] + f[1] t + ... + f[m-1] t^(m-1)))."""
    from itertools import product
    for tail in product(range(3), repeat=m):
        f = list(tail)
        if _is_irred(f, m): return f
    raise RuntimeError

def _is_irred(f, m):
    # brute: f has no root-free factorisation -> test by trial division over all
    # monic polys of degree 1..m//2
    from itertools import product
    def polymod(num, den):
        num = num[:]; dn = len(den) - 1
        for i in range(len(num) - 1, dn - 1, -1):
            c = num[i]
            if c:
                inv = 1 if den[dn] == 1 else 2
                c = (c * inv) % 3
                for j in range(dn + 1):
                    num[i - dn + j] = (num[i - dn + j] - c * den[j]) % 3
        return num[:dn]
    F = f + [1]                            # full poly, monic degree m
    for d in range(1, m // 2 + 1):
        for tail in product(range(3), repeat=d):
            g = list(tail) + [1]
            if not any(polymod(F, g)): return False
    return True


# ---------------------------------------------------------------------------
# Audit harness.  `python3 audit_capset_attack.py`  (~2.5 min) reproduces the
# numbers in the "Independent audit" section of REJECTED.md.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import random, time, statistics

    n, m = 6, 3
    T = tables(n)
    print("[1] reproduce Theorem 2.1 in F_3^6  (q = 27, m odd)")
    C = two_conics(m)
    ok, msg = is_capset(C, n, T)
    comp, bad = is_complete(C, n, T)
    print(f"    |C| = {len(C)} (paper: 2(q-1) = {2*(3**m-1)})   capset={ok}  complete={comp}")
    lb = 1
    while lb * (lb + 1) // 2 < 3 ** n: lb += 1
    print(f"    Lemma 1.1 lower bound for a complete capset in F_3^6: N >= {lb}")
    target = len(C)

    print("\n[2] does generic search reach that size without the formula?")
    t0 = time.time()
    sizes = [len(greedy_maximal(n, random.Random(10000 + s), T=T)) for s in range(2000)]
    print(f"    2000 random greedy MAXIMAL capsets in {time.time()-t0:.0f}s:")
    print(f"      min={min(sizes)}  median={statistics.median(sizes)}  max={max(sizes)}")
    print(f"      runs reaching <= {target}: {sum(1 for x in sizes if x <= target)} / 2000")

    best = min((greedy_maximal(n, random.Random(s), T=T) for s in range(200)), key=len)
    rng = random.Random(7); cur = best[:]; t0 = time.time(); it = 0
    while time.time() - t0 < 120:
        it += 1
        k = rng.randint(3, 12)
        keep = cur[:]; rng.shuffle(keep); keep = keep[:max(0, len(keep) - k)]
        cand = greedy_maximal(n, rng, seed_pts=keep, T=T)
        if len(cand) <= len(cur): cur = cand
    ok2, _ = is_capset(cur, n, T); comp2, _ = is_complete(cur, n, T)
    print(f"    destroy-and-repair local search: {it} iters / 120s -> |C| = {len(cur)} "
          f"(capset={ok2} complete={comp2}), target {target}")
    print("\n    => greedy and local search do NOT solve the size-constrained task;")
    print("       the formula does, instantly. The family fails G, not the greedy test.")
