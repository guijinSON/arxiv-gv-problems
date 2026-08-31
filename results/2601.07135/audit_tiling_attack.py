"""Exact-cover complement search with the standard MRV (fewest-options) rule.

Given A subset Z_M with |A| | M, find B with A (+) B = Z_M.  Tiling Z_M by
translates of A is exact cover: every residue must be covered exactly once.
Branch on the uncovered residue with the FEWEST admissible translates.
"""
import math

def complements(A, M, limit=1, node_cap=2_000_000, skip=None):
    A = sorted({a % M for a in A})
    k = len(A); need = M // k
    full = (1 << M) - 1
    base = 0
    for a in A: base |= 1 << a
    tmask = [base]
    for b in range(1, M):
        tmask.append(((base << b) | (base >> (M - b))) & full)
    out = []; nodes = [0]; capped = [False]

    def rec(cov, B):
        if len(out) >= limit: return
        if nodes[0] > node_cap: capped[0] = True; return
        if cov == full:
            Bs = sorted(B)
            if skip is None or Bs != skip: out.append(Bs)
            return
        # MRV: uncovered residue with fewest admissible translates
        best_i, best = None, None
        rem = ~cov & full
        x = rem
        while x:
            lb = x & -x; i = lb.bit_length() - 1; x ^= lb
            opts = [(i - a) % M for a in A]
            opts = [b for b in opts if not (tmask[b] & cov)]
            if best is None or len(opts) < len(best):
                best_i, best = i, opts
                if not opts: break          # dead end
        if not best: return
        for b in best:
            nodes[0] += 1
            B.append(b)
            rec(cov | tmask[b], B)
            B.pop()
            if len(out) >= limit: return
    rec(0, [])
    return out, nodes[0], capped[0]

def is_factorization(A, B, M):
    seen = [0] * M
    for a in A:
        for b in B: seen[(a + b) % M] += 1
    return all(c == 1 for c in seen)

def in_proper_subgroup(S, M):
    g = 0
    for x in S: g = math.gcd(g, x % M)
    return math.gcd(g, M) > 1


# ---------------------------------------------------------------------------
# Audit harness.  `python3 audit_tiling_attack.py` reproduces the three claims
# made in the "Independent audit" section of REJECTED.md.
# ---------------------------------------------------------------------------
def make_A(p, q, r, rng):
    """A random set of the form Definition 1.1(I):
       A = q^2 r^2 U + r^2 p^2 V + p^2 q^2 W, with u_i = i mod p (free mod p^2)."""
    M = (p * q * r) ** 2
    U = [0] + [i + p * rng.randrange(p) for i in range(1, p)]
    V = [0] + [j + q * rng.randrange(q) for j in range(1, q)]
    W = [0] + [k + r * rng.randrange(r) for k in range(1, r)]
    return sorted({(q * q * r * r * u + r * r * p * p * v + p * p * q * q * w) % M
                   for u in U for v in V for w in W})


def _is_fact(A, B, M):
    seen = bytearray(M)
    for a in A:
        for b in B:
            i = (a + b) % M
            if seen[i]: return False
            seen[i] = 1
    return all(seen)


if __name__ == "__main__":
    import random, time

    print("[1] B0 = pqr*Z_M complements EVERY form-(I) A  (answer ignores A entirely)")
    for (p, q, r) in [(2,3,5), (2,3,7), (2,5,7), (3,5,7), (3,5,11), (3,7,11), (5,7,11)]:
        M = (p * q * r) ** 2
        B0 = list(range(0, M, p * q * r))
        ok = all(_is_fact(make_A(p, q, r, random.Random(t)), B0, M) for t in range(30))
        print(f"    ({p},{q},{r})  M={M:7d}  |A|={p*q*r:4d}   30/30 random A: {ok}")

    p, q, r = 2, 3, 5
    M = (p * q * r) ** 2
    A = make_A(p, q, r, random.Random(0))
    B0 = sorted(range(0, M, p * q * r))

    print("\n[2] MRV exact cover, no structural hint, M = 900")
    t0 = time.time(); sols, nodes, capped = complements(A, M, limit=1); dt = time.time() - t0
    print(f"    first complement: {dt:.2f}s, {nodes} search nodes, valid="
          f"{is_factorization(A, sols[0], M)}")

    print("\n[3] the solution space is dense, and none of it is a Szabo pair")
    t0 = time.time(); sols, nodes, capped = complements(A, M, limit=20000); dt = time.time() - t0
    nonsub = [B for B in sols if not in_proper_subgroup(B, M)]
    print(f"    {len(sols)} distinct complements in {dt:.1f}s ({nodes} nodes, hit cap={capped})")
    print(f"    of which NOT inside a proper subgroup: {len(nonsub)}")
    print(f"    all verified: {all(is_factorization(A, B, M) for B in sols[:200])} (first 200)")
