"""Independent audit attacks for the balanced {+-1}-weighted zero-sum family.

Self-contained: integral LLL + lattice attack + meet-in-the-middle, stdlib only.
Run `python3 audit_pm1_attacks.py` next to gen_2603_07251.py.

Integral LLL (Cohen, *A Course in Computational Algebraic Number Theory*,
Algorithm 2.6.7) -- exact, integer-only.

Exact arithmetic is required, not a nicety: the subset-sum lattices below carry
entries of size ~N, so a float64 Gram-Schmidt (53-bit mantissa) silently stops
reducing once the modulus passes 2^53, and the attack would look like it failed
when in fact it was never run.
"""


def lll(B, delta_num=99, delta_den=100):
    """B: list of rows (lists of ints), linearly independent.
    Returns an LLL-reduced basis of the same lattice."""
    B = [list(map(int, r)) for r in B]
    n = len(B)
    if n <= 1: return B
    lam = [[0] * n for _ in range(n)]
    d = [1] * (n + 1)

    def dot(u, v): return sum(x * y for x, y in zip(u, v))

    for i in range(n):
        for j in range(i + 1):
            u = dot(B[i], B[j])
            for k in range(j):
                u = (d[k + 1] * u - lam[i][k] * lam[j][k]) // d[k]
            if j < i:
                lam[i][j] = u
            else:
                if u == 0: raise ValueError("linearly dependent basis")
                d[i + 1] = u

    def REDI(k, l):
        if abs(2 * lam[k][l]) <= d[l + 1]: return
        q = (2 * lam[k][l] + d[l + 1]) // (2 * d[l + 1])
        for i in range(len(B[k])): B[k][i] -= q * B[l][i]
        lam[k][l] -= q * d[l + 1]
        for i in range(l): lam[k][i] -= q * lam[l][i]

    def SWAPI(k):
        B[k], B[k - 1] = B[k - 1], B[k]
        for j in range(k - 1):
            lam[k][j], lam[k - 1][j] = lam[k - 1][j], lam[k][j]
        l = lam[k][k - 1]
        Bn = (d[k - 1] * d[k + 1] + l * l) // d[k]
        for i in range(k + 1, n):
            t = lam[i][k]
            lam[i][k] = (d[k + 1] * lam[i][k - 1] - l * t) // d[k]
            lam[i][k - 1] = (Bn * t + l * lam[i][k]) // d[k + 1]
        d[k] = Bn

    k = 1
    while k < n:
        REDI(k, k - 1)
        if delta_den * d[k + 1] * d[k - 1] < delta_num * d[k] * d[k] - delta_den * lam[k][k - 1] ** 2:
            SWAPI(k)
            k = max(k - 1, 1)
        else:
            for l in range(k - 2, -1, -1): REDI(k, l)
            k += 1
    return B

from itertools import combinations, product


def lattice_attack(a, N, balanced=True, extra_combos=True):
    m = len(a)
    lam = mu = m + 1
    rows = []
    for i in range(m):
        r = [0] * m + [lam * (a[i] % N), mu if balanced else 0]
        r[i] = 1
        rows.append(r)
    rows.append([0] * m + [lam * N, 0])
    R = lll(rows)

    cands = []
    for r in R:
        cands.append(r)
        cands.append([-x for x in r])
    if extra_combos:                      # cheap: pairwise sums/differences
        for i in range(len(R)):
            for j in range(i + 1, len(R)):
                cands.append([x + y for x, y in zip(R[i], R[j])])
                cands.append([x - y for x, y in zip(R[i], R[j])])
    for v in cands:
        if v[m] != 0 or (balanced and v[m + 1] != 0):
            continue
        eps = v[:m]
        if all(e in (1, -1) for e in eps):
            if sum(e * ai for e, ai in zip(eps, a)) % N == 0:
                if not balanced or sum(eps) == 0:
                    return eps
    return None


def mitm(a, N, balanced=True):
    """Exact O(2^(m/2)).  Returns eps in {+-1}^m or None."""
    m = len(a); h = m // 2
    left, right = a[:h], a[h:]
    table = {}
    for bits in range(1 << len(left)):
        eps = [1 if (bits >> i) & 1 else -1 for i in range(len(left))]
        s = sum(e * x for e, x in zip(eps, left)) % N
        w = sum(eps)
        table.setdefault((s, w) if balanced else (s, 0), eps)
    for bits in range(1 << len(right)):
        eps = [1 if (bits >> i) & 1 else -1 for i in range(len(right))]
        s = sum(e * x for e, x in zip(eps, right)) % N
        w = sum(eps)
        key = ((-s) % N, -w) if balanced else ((-s) % N, 0)
        if key in table:
            return table[key] + eps
    return None


def brute(a, N, balanced=True):
    m = len(a)
    for signs in product((1, -1), repeat=m):
        if balanced and sum(signs) != 0: continue
        if sum(e * x for e, x in zip(signs, a)) % N == 0:
            return list(signs)
    return None


def check(eps, a, N, balanced=True):
    if eps is None: return False
    return (len(eps) == len(a) and all(e in (1, -1) for e in eps)
            and sum(e * x for e, x in zip(eps, a)) % N == 0
            and (not balanced or sum(eps) == 0))


if __name__ == "__main__":
    import importlib.util, os, random, time
    _p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gen_2603_07251.py")
    _s = importlib.util.spec_from_file_location("gen", _p)
    g = importlib.util.module_from_spec(_s); _s.loader.exec_module(g)

    def to_ans(eps, n):
        return {"plus": sorted(i + 1 for i in range(n) if eps[i] == 1),
                "minus": sorted(i + 1 for i in range(n) if eps[i] == -1)}

    print("[A] meet-in-the-middle vs the real generator (exact, O(2^(n/2)))")
    for n in (16, 24, 32, 40):
        inst = g.make_instance(n=n, seed=1)
        t0 = time.time(); eps = mitm(inst["sequence"], inst["modulus"]); dt = time.time() - t0
        ok = eps is not None and g.verify(inst, to_ans(eps, n))[0]
        print(f"    n={n:3d}  solved={ok}  {dt:6.2f}s   (half-space 2^{n//2})")
    print("    n=64 (shipping) needs 2^32 half-space entries -- not run.")

    print("\n[B] lattice attack vs the real generator (density = 1)")
    for n in (24, 32, 40, 48, 64):
        inst = g.make_instance(n=n, seed=2)
        eps = lattice_attack(inst["sequence"], inst["modulus"])
        ok = eps is not None and g.verify(inst, to_ans(eps, n))[0]
        print(f"    n={n:3d} density=1.00  solved={ok}")

    print("\n[C] CONTROL: same lattice code, modulus inflated so density drops")
    print("    (a null result in [B] is only meaningful if this succeeds)")
    for n, bits in ((32, 64), (32, 80), (40, 100), (48, 120)):
        N = 1 << bits
        rng = random.Random(n * 7 + bits)
        eps = [1] * (n // 2) + [-1] * (n // 2); rng.shuffle(eps)
        a = [rng.randrange(N) for _ in range(n)]
        j = rng.randrange(n)
        s = sum(e * x for e, x in zip(eps, a)) - eps[j] * a[j]
        a[j] = (-eps[j] * s) % N
        got = lattice_attack(a, N)
        ok = got is not None and sum(e * x for e, x in zip(got, a)) % N == 0 and sum(got) == 0
        print(f"    n={n:3d} q=2^{bits:<4d} density={n/bits:4.2f}  solved={ok}")
