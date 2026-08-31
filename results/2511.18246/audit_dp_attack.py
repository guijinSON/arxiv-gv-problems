"""Independent solver for: find a 2n-product-one subsequence in G = C_n x|_s C_2.

Element (e,a) means x^e y^a.  (x^e1 y^a1)(x^e2 y^a2) = x^(e1+e2) y^(a1*s^e2 + a2).
Product of g_1..g_m = x^(sum e_i) y^E with E = sum_i a_i * s^(q_i),
q_i = #{j>i : e_j=1}.  Since s^2=1 mod n, coeff is 1 or s.

Ordering freedom (proved by construction below):
  - among the 2k type-1 elements, EXACTLY k get coeff s and k get coeff 1,
    and any such split is realisable;
  - each type-0 element gets coeff 1 or s freely (when k>=1);
    when k=0 every coeff is 1.
So: exists 2n-product-one subsequence  <=>  exists T, |T|=2n, and a coeff
assignment with (#type-1 with coeff 1) == (#type-1 with coeff s), summing to 0 mod n.
"""

def mul(g, h, n, s):
    (e1, a1), (e2, a2) = g, h
    return ((e1 + e2) % 2, (a1 * pow(s, e2, n) + a2) % n)

def prod(seq, n, s):
    r = (0, 0)
    for g in seq:
        r = mul(r, g, n, s)
    return r

def solve(elems, n, s, target_len):
    """elems: list of (e,a).  Returns an ORDERED list of indices whose product is
    the identity, of length target_len, or None."""
    full = (1 << n) - 1
    def rot(mask, a):
        a %= n
        return mask if a == 0 else ((mask << a) | (mask >> (n - a))) & full

    L = target_len
    m = len(elems)
    # state (c, d, f) ; f bit0 = some type-1 chosen, bit1 = some type-0 given coeff s
    dp = [dict() for _ in range(m + 1)]
    dp[0][(0, 0, 0)] = 1
    for i, (e, a) in enumerate(elems):
        cur, nxt = dp[i], dp[i + 1]
        as_ = (a * s) % n
        rem = m - i - 1
        def put(k, v):
            if v: nxt[k] = nxt.get(k, 0) | v
        for (c, d, f), mask in cur.items():
            put((c, d, f), mask)                      # skip
            if c + 1 > L or c + 1 + rem < L: continue
            if e == 0:
                put((c + 1, d, f), rot(mask, a))              # coeff 1
                put((c + 1, d, f | 2), rot(mask, as_))        # coeff s
            else:
                if abs(d + 1) <= L: put((c + 1, d + 1, f | 1), rot(mask, a))
                if abs(d - 1) <= L: put((c + 1, d - 1, f | 1), rot(mask, as_))
    goal = None
    for f in (0, 1, 2, 3):
        if f & 2 and not (f & 1):   # type-0 used coeff s but no type-1 present
            continue
        if dp[m].get((L, 0, f), 0) & 1:
            goal = f; break
    if goal is None:
        return None
    c, d, f, E = L, 0, goal, 0
    chosen = []
    for i in range(m - 1, -1, -1):
        e, a = elems[i]
        as_ = (a * s) % n
        if (dp[i].get((c, d, f), 0) >> E) & 1:
            continue                                   # skipped
        moves = ([(0, a, d, f), (1, as_, d, f & ~2)] if e == 0
                 else [(0, a, d - 1, f & ~1), (1, as_, d + 1, f & ~1),
                       (0, a, d - 1, f), (1, as_, d + 1, f)])
        for coeff, av, dd, ff in moves:
            pe = (E - av) % n
            if (dp[i].get((c - 1, dd, ff), 0) >> pe) & 1:
                chosen.append((i, coeff, e)); c -= 1; d = dd; f = ff; E = pe
                break
        else:
            raise RuntimeError("backtrack failed")
    assert c == 0 and d == 0 and E == 0
    return order(chosen, elems)

def order(chosen, elems):
    """chosen: list of (idx, coeff_is_s, type). Build an explicit ordering realising
    those coefficients.  Type-1 elements: those with coeff s must have an ODD number
    of type-1 elements after them.  Interleave: put the k coeff-s ones and k coeff-1
    ones alternating, coeff-s first in each pair (so it sees an odd count after it).
    Type-0 with coeff 1 -> place at the very end (0 type-1 after);
    type-0 with coeff s -> place right after the first type-1 element
    (leaves 2k-1 type-1 after it, odd)."""
    t1 = [x for x in chosen if x[2] == 1]
    t0 = [x for x in chosen if x[2] == 0]
    s_ones = [x for x in t1 if x[1] == 1]
    o_ones = [x for x in t1 if x[1] == 0]
    assert len(s_ones) == len(o_ones)
    seq = []
    # alternate: s_one, o_one, s_one, o_one, ...
    # the j-th pair: s_one at position with (#type-1 after) odd, o_one with even
    for a_, b_ in zip(s_ones, o_ones):
        seq.append(a_); seq.append(b_)
    t0_s = [x for x in t0 if x[1] == 1]
    t0_1 = [x for x in t0 if x[1] == 0]
    if t0_s:
        assert seq, "coeff s on type-0 needs at least one type-1 element"
        out = [seq[0]] + t0_s + seq[1:] + t0_1
    else:
        out = seq + t0_1
    return [i for (i, _, _) in out]


# ---------------------------------------------------------------------------
# Audit harness.  `python3 audit_dp_attack.py` reproduces the two claims made in
# REJECTED.md: (a) the DP is correct, (b) it is fast at the paper's parameters.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import random, time, itertools

    def brute(elems, n, s, L):
        for T in itertools.combinations(range(len(elems)), L):
            for perm in itertools.permutations(T):
                if prod([elems[i] for i in perm], n, s) == (0, 0):
                    return True
        return False

    rng = random.Random(1)
    bad = 0
    for _ in range(400):
        n = rng.choice([3, 5, 6, 9, 10])
        s = rng.choice([t for t in range(n) if (t * t) % n == 1 % n])
        m, L = rng.randint(4, 7), rng.randint(2, 4)
        elems = [(rng.randint(0, 1), rng.randrange(n)) for _ in range(m)]
        got, exp = solve(elems, n, s, L), brute(elems, n, s, L)
        if got is not None:
            assert len(got) == L and len(set(got)) == L
            assert prod([elems[i] for i in got], n, s) == (0, 0)
        if (got is not None) != exp:
            bad += 1
    print(f"agreement with brute force: {400 - bad}/400 exact")

    print("\nGao regime  G = C_{3n2} x|_s C_2,  |S| = E(G) = 9n2,  witness length 6n2:")
    for n2 in (5, 7, 11, 25):
        n = 3 * n2
        s = next(t for t in range(n)
                 if t % 3 == 2 and t % n2 == 1 % n2 and (t * t) % n == 1 % n)
        rng = random.Random(0)
        elems = [(rng.randint(0, 1), rng.randrange(n)) for _ in range(3 * n)]
        t0 = time.time(); r = solve(elems, n, s, 2 * n); dt = time.time() - t0
        ok = r is not None and len(r) == 2 * n and prod([elems[i] for i in r], n, s) == (0, 0)
        print(f"  n2={n2:3d}  |G|={2*n:4d}  |S|={3*n:4d}  witness found={r is not None}"
              f"  verified={ok}  {dt:.2f}s")
