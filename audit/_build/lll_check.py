"""Measured LLL / CJLOSS control for 2310.02137.

Exact-integer LLL (de Weger's integral variant, delta = 99/100) on the CJLOSS
lattice for the balanced zero-sum subset problem:

    row i (i<n) : [ 2*e_i | N*a_i | N ]
    row n       : [ 1 ... 1 | 0    | N*(n/2) ]

sum_i x_i*row_i - row_n = [ 2x-1 | N*(a.x) | N*(|x| - n/2) ], so a balanced
zero-sum subset is a lattice vector of norm sqrt(n) with all first-n entries +-1.
Reports whether such a vector appears in the reduced basis.  Graded by the
module's own verify().
"""
import importlib.util, sys, time
from fractions import Fraction

def load(p, name):
    s = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def lll(B, delta=Fraction(99, 100), deadline=None):
    """Textbook LLL (Cohen 2.6.3) with exact rational Gram-Schmidt."""
    B = [list(r) for r in B]
    n = len(B)
    Bs = [None]*n
    mu = [[Fraction(0)]*n for _ in range(n)]
    Bn = [Fraction(0)]*n

    def gso_row(k):
        v = [Fraction(x) for x in B[k]]
        for j in range(k):
            if Bn[j] == 0:
                mu[k][j] = Fraction(0)
                continue
            mu[k][j] = sum(Fraction(a)*b for a, b in zip(B[k], Bs[j])) / Bn[j]
            v = [x - mu[k][j]*y for x, y in zip(v, Bs[j])]
        Bs[k] = v
        Bn[k] = sum(x*x for x in v)

    for k in range(n):
        gso_row(k)

    def red(k, j):
        if abs(mu[k][j]) <= Fraction(1, 2):
            return
        q = (2*mu[k][j].numerator + mu[k][j].denominator) // (2*mu[k][j].denominator)
        B[k] = [a - q*b for a, b in zip(B[k], B[j])]
        for i in range(j):
            mu[k][i] -= q*mu[j][i]
        mu[k][j] -= q

    k = 1
    while k < n:
        if deadline and time.time() > deadline:
            raise TimeoutError
        red(k, k-1)
        if Bn[k] >= (delta - mu[k][k-1]**2) * Bn[k-1]:
            for j in range(k-2, -1, -1):
                red(k, j)
            k += 1
        else:
            B[k], B[k-1] = B[k-1], B[k]
            gso_row(k-1)
            gso_row(k)
            for i in range(k+1, n):
                for j in range(k+1):
                    pass
            for i in range(k+1, n):
                gso_row(i)
            k = max(k-1, 1)
    return B


def main(seeds, cap, n_over=None, wb_over=None):
    R = "/private/tmp/claude-501/-Users-songuijin-claude-aug/239a527d-78de-4edb-a803-387c36f15c2a/scratchpad/arxiv-gv-problems/results/"
    g = load(R + "2310.02137/gen_2310_02137.py", "g1")
    params = dict(g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
    if n_over: params = {"n": n_over, "weight_bits": wb_over or n_over}
    for seed in seeds:
        inst = g.make_instance(seed=seed, **params)
        n = inst["variables"]; half = inst["high_count"]; a = inst["weights"]
        N = 1 << (max(x.bit_length() for x in a) + 10)
        rows = []
        for i in range(n):
            r = [0]*n; r[i] = 2; r += [N*a[i], N]
            rows.append(r)
        rows.append([1]*n + [0, N*half])
        t0 = time.time(); status = "no_short_pm1_vector"
        try:
            red = lll(rows, deadline=t0 + cap)
            solved = False
            for v in red:
                head = v[:n]
                if v[n] == 0 and v[n+1] == 0 and all(x in (-1, 1) for x in head):
                    for sign in (1, -1):
                        cand = sorted(i+1 for i in range(n) if sign*head[i] == 1)
                        if len(cand) == half and g.verify(inst, cand)[0]:
                            solved = True
                    if solved: break
            status = "SOLVED" if solved else "no_short_pm1_vector"
        except TimeoutError:
            status = "TIMEOUT(%ds)" % cap
        print("  LLL n=%-3d seed %-5d %-18s %6.1fs" % (n, seed, status, time.time()-t0), flush=True)

if __name__ == "__main__":
    main([int(x) for x in sys.argv[1].split(",")], float(sys.argv[2]),
         int(sys.argv[3]) if len(sys.argv) > 3 else None)
