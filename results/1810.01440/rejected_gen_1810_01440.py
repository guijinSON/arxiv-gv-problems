#!/usr/bin/env python3
"""Generator for arXiv:1810.01440 -- "A Novel Algebraic Geometry Compiling
Framework for Adiabatic Quantum Computations" (Dridi, Alghassi, Tayur).

FAMILY: exact-pullback fiber bundle.

The paper's central object (Section 4.2.2, eq. (rep2)) is a fiber bundle

    pi : Vertices(X) -> Vertices(Y) u {0},      pi(x_i) = sum_j alpha_ij y_j

from the hardware graph X onto the logical graph Y, whose fibers pi^{-1}(y_j)
are the connected subtrees ("chains") of the minor embedding phi.  Section
4.2.3 extends pi multiplicatively to polynomials and computes the pullback of
the quadratic form Q_X(x) = sum_{(x_a,x_b) in E(X)} x_a x_b :

    pi^*(Q_X)(y) = sum_{j1<j2} ( sum_{(x_a,x_b) in E(X)}
                     (alpha_{a j1} alpha_{b j2} + alpha_{a j2} alpha_{b j1}) )
                   y_{j1} y_{j2}
                 + sum_j ( sum_{(x_a,x_b) in E(X)} alpha_{aj} alpha_{bj} ) y_j^2

The coefficient of y_{j1} y_{j2} is exactly the number of X-edges joining the
two fibers; the coefficient of y_j^2 is the number of X-edges inside fiber j.
The paper's Pullback Condition proposition only asks that the off-diagonal
coefficient be non-zero (written there as 1 + delta^2).  Here we hand the
solver the pullback quadratic form *with its exact integer coefficients* and
ask for a fiber bundle realising it -- a strictly more constrained instance of
the same variety.

INSTANCE   hardware graph X = Chimera C_{L,L,t} (the paper's own hardware;
           D-Wave 2000Q is C_{16,16,4}), a chain size k, and the integer
           coefficient matrix C of pi^*(Q_X).
ANSWER     the fiber bundle itself: for each logical qubit j, the vertex set of
           pi^{-1}(y_j).
VERIFY     count edges.  Integers only; no float is created anywhere.

VERDICT: this family is REJECTED.  See REJECTED.md.  It is kept because the
project requires a rejected generator to stay on disk with its measurements.
The gates below are real and were run; G6 fails, with numbers.

NOTES
  * Section 4.2.2 (Definition `olddef`, eq. (rep2)) fixed the definition of the
    fiber bundle and of what alpha_ij means; eq. (sc) fixed the chain-size
    condition; eq. (cc) fixed the Connected Fiber Condition (unique chain =>
    each fiber is a subtree, so a fiber of size k has exactly k-1 internal
    edges).  This is why verify() tests "connected AND k-1 internal edges"
    rather than mere connectivity.
  * Section 4.2.3, the displayed pi^*(Q_X) formula and the Pullback Condition
    proposition, fixed what the instance data is.
  * Section 4.2.4 (staircase diagrams) told us the variety is zero-dimensional
    and finite, so enumerate_all() is meaningful.
  * What told us it is EASY: nothing in the paper -- the paper only claims its
    own procedure is not polynomial ("Goals of the paper": "We recognize that
    the (worst-case) computational complexity of our procedure is not
    polynomial").  Measurement did: the exact pullback coefficients are a
    forward-checkable constraint, and CP with MRV ordering solves the planted
    instance in tens of nodes.  See REJECTED.md.
"""

import itertools
import json
import math
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals          # noqa: F401
except ImportError:                 # not present: stay standard-library-only
    exact_matrices = rationals = None


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "exact_cover",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "hardware graph X = Chimera C_{L,L,t}",
        "fiber bundle pi: Vertices(X) -> Vertices(Y) u {0} (eq. (rep2))",
        "pullback quadratic form pi^*(Q_X) as an exact integer coefficient matrix",
    ],
    "verification_operations": [
        "integer edge counting inside each fiber",
        "integer edge counting between each pair of fibers",
        "connectivity test by breadth-first search",
        "set partition / disjointness test",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "The exact coefficient of y_{j1} y_{j2} in the pullback pins the number "
        "of hardware edges joining two chains, so placing one chain fixes how "
        "far every other chain may sit from it; a solver without that "
        "observation must search the whole space of partitions of the hardware "
        "graph into connected k-subtrees."
    ),
    "hardness_basis": (
        "CLAIMED: partitioning a bounded-degree graph into connected k-subtrees "
        "with a prescribed quotient is NP-hard (k>=3), and the paper's own "
        "Groebner route over the nm binary variables alpha_ij is exponential "
        "(Section 'Goals of the paper').  MEASURED: FALSE for this "
        "distribution -- see REJECTED.md; CP with MRV plus forward checking on "
        "the pullback coefficients solves the planted instance in 8-571 nodes."
    ),
    "max_answer_tokens": 220,
}

NATIVE = {
    "domain": "combinatorics",
    "core": "exact_cover",
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (PROBLEM_PROFILE["intuition_type"] + ": "
                  + PROBLEM_PROFILE["intuition_description"]),
    "reduction": None,
}

# Each preset maps to kwargs for make_instance.  n = 2*t*L*L is the number of
# physical qubits and also the number of atoms in the answer, so the ladder
# holds n fixed from "medium" on and moves k and t instead.
DIFFICULTY = {
    "demo":   {"L": 2, "t": 2, "k": 2},     # n = 16,  m = 8
    "easy":   {"L": 3, "t": 4, "k": 3},     # n = 72,  m = 24
    "medium": {"L": 4, "t": 4, "k": 4},     # n = 128, m = 32
    "hard":   {"L": 2, "t": 16, "k": 4},    # n = 128, m = 32, denser cells
}
SHIPPING_DIFFICULTY = "medium"

STRUCTURAL_HINT = (
    "Every off-diagonal coefficient of the pullback is an exact edge count "
    "between two chains, so a coefficient of zero forbids the two chains from "
    "touching anywhere in the hardware graph."
)
PLACEBO_HINT = (
    "This problem rewards keeping the qubit indices straight and writing the "
    "chains out in the order the logical qubits are numbered."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "An ordered m-tuple (F_0, ..., F_{m-1}) of pairwise disjoint subsets of "
        "Vertices(X), each of size exactly k, whose union is Vertices(X).  "
        "random_candidate() samples only from the sub-language in which every "
        "F_j is additionally a connected subtree of X, which is the freely "
        "deducible constraint a solver applies before searching."
    ),
    "bounds": {"n_blocks": "m = n/k", "block_size": "k", "ground_set": "n = 2*t*L*L"},
}


# --------------------------------------------------------------------------
# the hardware graph
# --------------------------------------------------------------------------

def _chimera(L, t):
    """Chimera C_{L,L,t}: an LxL grid of K_{t,t} cells.

    Vertex id of (row r, column c, side s in {0,1}, index i in [0,t)) is
    ((r*L + c)*2 + s)*t + i.  Side 0 qubits carry the vertical couplers, side 1
    qubits the horizontal ones.  Returns (n, adj) with adj a list of sets.
    """
    def vid(r, c, s, i):
        return ((r * L + c) * 2 + s) * t + i
    n = 2 * t * L * L
    adj = [set() for _ in range(n)]

    def link(a, b):
        adj[a].add(b)
        adj[b].add(a)

    for r in range(L):
        for c in range(L):
            for i in range(t):
                for j in range(t):
                    link(vid(r, c, 0, i), vid(r, c, 1, j))
            if r + 1 < L:
                for i in range(t):
                    link(vid(r, c, 0, i), vid(r + 1, c, 0, i))
            if c + 1 < L:
                for i in range(t):
                    link(vid(r, c, 1, i), vid(r, c + 1, 1, i))
    return n, adj


def _edges(adj):
    return sorted((a, b) for a in range(len(adj)) for b in adj[a] if a < b)


# --------------------------------------------------------------------------
# G -- plant the answer first
# --------------------------------------------------------------------------

def _plant(adj, n, k, rng, restarts=6000):
    """Partition Vertices(X) into n/k connected k-subtrees.

    Answer-first: the fibers are GROWN, never searched for.  The only loop is a
    restart loop over a randomised growth that can paint itself into a corner;
    it never inspects an instance, because the instance does not exist yet.
    """
    for _ in range(restarts):
        free = set(range(n))
        fibers = []
        ok = True
        while free:
            start = min(free, key=lambda v: (len(adj[v] & free), rng.random()))
            f = {start}
            while len(f) < k:
                cand = sorted(w for v in f for w in adj[v] & free if w not in f)
                if not cand:
                    ok = False
                    break
                f.add(rng.choice(cand))
            if not ok:
                break
            fibers.append(sorted(f))
            free -= f
        if ok:
            rng.shuffle(fibers)
            return [sorted(f) for f in fibers]
    return None


def _pullback(adj, fibers):
    """The exact coefficient matrix of pi^*(Q_X) (Section 4.2.3)."""
    m = len(fibers)
    C = [[0] * m for _ in range(m)]
    idx = {v: j for j, f in enumerate(fibers) for v in f}
    for j, f in enumerate(fibers):
        for v in f:
            for w in adj[v]:
                jj = idx.get(w)
                if jj is None:
                    continue
                if jj == j:
                    C[j][j] += 1
                else:
                    C[j][jj] += 1
    for j in range(m):
        C[j][j] //= 2           # each internal edge seen from both ends
    return C


def make_instance(n=None, seed=0, **params):
    """Build an instance whose fiber bundle is known by construction."""
    p = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    p.update({key: val for key, val in params.items() if key in ("L", "t", "k")})
    L, t, k = p["L"], p["t"], p["k"]
    if n is not None and not params:
        pass                                 # `n` is informational; L,t,k rule
    rng = random.Random(seed)
    nv, adj = _chimera(L, t)
    if nv % k:
        raise ValueError("k must divide n = 2*t*L*L (n=%d, k=%d)" % (nv, k))
    fibers = _plant(adj, nv, k, rng)
    if fibers is None:
        raise ValueError("planting failed for L=%d t=%d k=%d" % (L, t, k))
    C = _pullback(adj, fibers)
    return {
        "paper": "1810.01440",
        "L": L, "t": t, "k": k, "n": nv, "m": len(fibers),
        "C": C,
        "answer": [list(f) for f in fibers],
    }


# --------------------------------------------------------------------------
# the output contract
# --------------------------------------------------------------------------

def render(inst):
    L, t, k, n, m = inst["L"], inst["t"], inst["k"], inst["n"], inst["m"]
    C = inst["C"]
    lines = []
    A = lines.append
    A("HARDWARE GRAPH.")
    A("Let X be the Chimera graph C_{%d,%d,%d}.  Its %d vertices ("
      "\"physical qubits\") are numbered 0 .. %d as follows: the qubit in grid "
      "row r, grid column c, side s and index i -- with 0 <= r,c < %d, "
      "s in {0,1}, 0 <= i < %d -- has number" % (L, L, t, n, n - 1, L, t))
    A("    v(r,c,s,i) = ((r*%d + c)*2 + s)*%d + i." % (L, t))
    A("The edges of X are exactly:")
    A("  (a) v(r,c,0,i) -- v(r,c,1,j)   for every r,c and every i,j in [0,%d);"
      % t)
    A("  (b) v(r,c,0,i) -- v(r+1,c,0,i) for every r < %d, every c, every i;"
      % (L - 1))
    A("  (c) v(r,c,1,i) -- v(r,c+1,1,i) for every c < %d, every r, every i."
      % (L - 1))
    A("X has %d edges.  All graphs here are simple and undirected."
      % len(_edges(_chimera(L, t)[1])))
    A("")
    A("WHAT YOU MUST FIND.")
    A("A fiber bundle pi assigning every one of the %d physical qubits to one "
      "of %d logical qubits y_0 .. y_%d.  Write F_j for the set of physical "
      "qubits assigned to y_j (the \"chain\" of y_j).  Required:" % (n, m, m - 1))
    A("  (1) the F_j are pairwise disjoint and together contain every vertex "
        "of X (every physical qubit is used exactly once);")
    A("  (2) |F_j| = %d for every j;" % k)
    A("  (3) the subgraph of X induced on F_j is connected and is a tree, i.e. "
      "it has exactly %d edges;" % (k - 1))
    A("  (4) for every pair j1 < j2, the number of edges of X with one endpoint "
      "in F_{j1} and the other in F_{j2} equals the given integer C[j1][j2] "
      "below -- EXACTLY that number, not merely a positive number.")
    A("")
    A("PULLBACK COEFFICIENTS.")
    A("The list below gives every pair j1 < j2 with C[j1][j2] > 0, as "
      "\"j1 j2 c\".  Every pair NOT listed has C[j1][j2] = 0, meaning no edge "
      "of X may join F_{j1} to F_{j2}.")
    nz = [(j1, j2, C[j1][j2]) for j1 in range(m) for j2 in range(j1 + 1, m)
          if C[j1][j2]]
    for j1, j2, c in nz:
        A("  %d %d %d" % (j1, j2, c))
    A("(%d pairs listed; the remaining %d pairs have coefficient 0.)"
      % (len(nz), m * (m - 1) // 2 - len(nz)))
    A("")
    A("OUTPUT.")
    A("Give your final answer inside <answer></answer> tags as %d "
      "semicolon-separated groups, one per logical qubit in order j = 0, 1, "
      "..., %d, each group being the %d physical qubit numbers of F_j "
      "separated by commas.  Order inside a group does not matter.  "
      "Output nothing else inside the tags." % (m, m - 1, k))
    A("Example format (for m=3, k=2):  <answer>0,5; 1,4; 2,3</answer>")
    out = "\n".join(lines)
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        out += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        out += "\n\nHint: " + PLACEBO_HINT
    return out


def parse_answer(text):
    if not isinstance(text, str):
        return None
    body = text
    if "<answer>" in body and "</answer>" in body:
        body = body.split("<answer>", 1)[1].split("</answer>", 1)[0]
    body = body.replace("`", " ").replace("\n", " ")
    for ch in "[]{}()":
        body = body.replace(ch, " ")
    groups = [g for g in body.split(";") if g.strip()]
    if not groups:
        return None
    out = []
    for g in groups:
        toks = [x for x in g.replace(",", " ").split() if x]
        blk = []
        for x in toks:
            try:
                blk.append(int(x))
            except ValueError:
                return None
        if not blk:
            return None
        out.append(blk)
    return out


# --------------------------------------------------------------------------
# V -- exact verification.  Integers only.
# --------------------------------------------------------------------------

def verify(inst, answer):
    n, k, m, C = inst["n"], inst["k"], inst["m"], inst["C"]
    _, adj = _chimera(inst["L"], inst["t"])
    if not isinstance(answer, (list, tuple)):
        return False, "answer is not a list of fibers"
    if len(answer) != m:
        return False, "answer has %d fibers, expected %d" % (len(answer), m)
    fibers = []
    for j, f in enumerate(answer):
        if not isinstance(f, (list, tuple)):
            return False, "fiber %d is not a list" % j
        if len(f) != k:
            return False, "fiber %d has %d qubits, expected %d" % (j, len(f), k)
        for v in f:
            if not isinstance(v, int) or isinstance(v, bool):
                return False, "fiber %d contains a non-integer qubit" % j
            if not (0 <= v < n):
                return False, "qubit %d in fiber %d is outside [0, %d)" % (v, j, n)
        if len(set(f)) != k:
            return False, "fiber %d repeats a qubit" % j
        fibers.append(set(f))
    seen = set()
    for j, f in enumerate(fibers):
        if seen & f:
            return False, ("fiber %d shares qubit %d with an earlier fiber"
                           % (j, min(seen & f)))
        seen |= f
    if len(seen) != n:
        return False, ("the fibers cover %d of the %d physical qubits"
                       % (len(seen), n))
    for j, f in enumerate(fibers):
        internal = 0
        for a, b in itertools.combinations(sorted(f), 2):
            if b in adj[a]:
                internal += 1
        if internal != C[j][j]:
            return False, ("fiber %d induces %d internal edges, but its "
                           "pullback coefficient is %d" % (j, internal, C[j][j]))
        # connectivity by BFS
        start = min(f)
        comp = {start}
        stack = [start]
        while stack:
            v = stack.pop()
            for w in adj[v]:
                if w in f and w not in comp:
                    comp.add(w)
                    stack.append(w)
        if len(comp) != len(f):
            return False, "fiber %d is not connected in X" % j
    for j1 in range(m):
        for j2 in range(j1 + 1, m):
            cnt = 0
            for a in fibers[j1]:
                for b in adj[a]:
                    if b in fibers[j2]:
                        cnt += 1
            if cnt != C[j1][j2]:
                return False, ("fibers %d and %d are joined by %d edges of X, "
                               "but C[%d][%d] = %d"
                               % (j1, j2, cnt, j1, j2, C[j1][j2]))
    return True, "ok"


# --------------------------------------------------------------------------
# guessing, counting, keys
# --------------------------------------------------------------------------

def random_candidate(inst, rng):
    """Structure-aware: a random partition into CONNECTED k-subtrees."""
    _, adj = _chimera(inst["L"], inst["t"])
    f = _plant(adj, inst["n"], inst["k"], rng, restarts=200)
    if f is None:                       # fall back to shape-only
        vs = list(range(inst["n"]))
        rng.shuffle(vs)
        k = inst["k"]
        f = [sorted(vs[i:i + k]) for i in range(0, inst["n"], k)]
    return [list(x) for x in f]


def search_space(inst):
    """Ordered partitions of V(X) into m labelled blocks of size k.

    This is the NAIVE count; random_candidate samples the strictly smaller
    connected sub-language, and G4 reports the empirical structure-aware
    number alongside this one.
    """
    n, k, m = inst["n"], inst["k"], inst["m"]
    return math.factorial(n) // (math.factorial(k) ** m)


def enumerate_all(inst, cap=200000, time_cap=20.0):
    """Exact number of valid fiber bundles; None if the search is capped."""
    _, adj = _chimera(inst["L"], inst["t"])
    sols = _cp_solve(adj, inst["n"], inst["k"], inst["C"], all_solutions=True,
                     node_cap=cap, time_cap=time_cap)
    return None if sols is None else sols


def canonical_key(inst):
    """Invariant under (a) relabelling the logical qubits y_j (which permutes
    the rows and columns of C simultaneously) and (b) any automorphism of X
    applied to the fibers (which leaves C unchanged).  Built from C alone by
    colour refinement, never from the seed and never from render()."""
    C = inst["C"]
    m = len(C)
    colour = [hash(tuple(sorted(C[j]))) & 0xFFFFFFFF for j in range(m)]
    for _ in range(min(m, 8)):
        new = []
        for j in range(m):
            sig = (colour[j], tuple(sorted((colour[i], C[j][i])
                                           for i in range(m) if i != j)))
            new.append(hash(sig) & 0xFFFFFFFF)
        remap = {c: i for i, c in enumerate(sorted(set(new)))}
        colour = [remap[c] for c in new]
    hist = tuple(sorted(colour))
    edges = tuple(sorted((min(colour[a], colour[b]), max(colour[a], colour[b]),
                          C[a][b])
                         for a in range(m) for b in range(a + 1, m) if C[a][b]))
    return "1810.01440|L=%d|t=%d|k=%d|%s" % (
        inst["L"], inst["t"], inst["k"],
        "%08x" % (hash((hist, edges)) & 0xFFFFFFFF))


def escalate(params):
    """Harder parameters at FIXED answer length.

    The answer is one label per physical qubit, so n = 2*t*L*L is the answer
    length and must not grow.  Two axes move instead:
      * k -- the chain size of eq. (sc); larger k means far more connected
        k-subtrees per qubit and a much larger candidate pool, with the same n
        qubits to label;
      * (t, L) at fixed n -- trading grid size for cell size raises the degree
        of X and the local density of chains without adding a qubit.
    """
    p = dict(params)
    L, t, k = p.get("L", 4), p.get("t", 4), p.get("k", 4)
    n = 2 * t * L * L
    ladder = []
    for tt, LL in [(4, 4), (8, 2 ** 0 * 2), (16, 2), (32, 1), (64, 1)]:
        if 2 * tt * LL * LL == n:
            ladder.append((tt, LL))
    ladder = sorted(set(ladder))
    # 1) raise cell density t at fixed n
    for tt, LL in ladder:
        if tt > t:
            return {"L": LL, "t": tt, "k": k}
    # 2) raise the chain size k at fixed n
    for kk in (k * 2, k + 1):
        if kk <= n and n % kk == 0:
            return {"L": L, "t": t, "k": kk}
    return "cap_bound"


# --------------------------------------------------------------------------
# attacks
# --------------------------------------------------------------------------

def _connected_ksets(adj, n, k):
    out = set()

    def grow(cur, frontier):
        if len(cur) == k:
            out.add(tuple(sorted(cur)))
            return
        for w in sorted(frontier):
            grow(cur | {w}, (frontier | adj[w]) - cur - {w})
    for v in range(n):
        grow({v}, set(adj[v]))
    return sorted(out)


def _cp_solve(adj, n, k, C, all_solutions=False, node_cap=2_000_000,
              time_cap=120.0):
    """THE DOMAIN-STANDARD ATTACK.

    Constraint programming over connected k-subsets with
      * bitmask candidate sets,
      * forward checking on the exact pullback coefficients,
      * MRV dynamic variable ordering,
      * Algorithm-X style coverage pruning.
    Returns the first solution, or (if all_solutions) the number of solutions,
    or None on cap.  Also records node count in _cp_solve.nodes.
    """
    t0 = time.time()
    m = len(C)
    amask = [0] * n
    for v in range(n):
        msk = 0
        for w in adj[v]:
            msk |= 1 << w
        amask[v] = msk
    cands = _connected_ksets(adj, n, k)
    info = []
    for S in cands:
        msk = 0
        nbr = 0
        for v in S:
            msk |= 1 << v
            nbr |= amask[v]
        internal = sum(1 for a, b in itertools.combinations(S, 2) if b in adj[a])
        info.append((S, msk, internal, nbr & ~msk))
    doms = [tuple(i for i, rec_ in enumerate(info) if rec_[2] == C[j][j])
            for j in range(m)]
    full = (1 << n) - 1
    nodes = [0]
    count = [0]
    capped = [False]
    ops = [0]
    _pc = getattr(int, "bit_count", None)
    if _pc is None:
        def popcount(x):
            return bin(x).count("1")
    else:
        def popcount(x):
            return x.bit_count()

    def cross(i2, jmask):
        return sum(popcount(amask[v] & jmask) for v in info[i2][0])

    def rec(doms, placed, covered):
        if nodes[0] > node_cap or time.time() - t0 > time_cap:
            capped[0] = True
            return None
        if len(placed) == m:
            count[0] += 1
            return None if all_solutions else dict(placed)
        j = min((jj for jj in range(m) if jj not in placed),
                key=lambda jj: len(doms[jj]))
        for i in doms[j]:
            nodes[0] += 1
            if nodes[0] > node_cap or time.time() - t0 > time_cap:
                capped[0] = True
                return None
            msk = info[i][1]
            if msk & covered:
                continue
            nbrmsk = info[i][3]
            blocked = msk | nbrmsk | covered
            nd = list(doms)
            ok = True
            reach = 0
            for jj in range(m):
                if jj in placed or jj == j:
                    continue
                need = C[j][jj]
                dj = doms[jj]
                ops[0] += len(dj)
                if need == 0:
                    # no edge may join the two chains: one bitmask test
                    keep = tuple(i2 for i2 in dj if not (info[i2][1] & blocked))
                else:
                    keep = tuple(i2 for i2 in dj
                                 if not (info[i2][1] & (msk | covered))
                                 and (info[i2][1] & nbrmsk)
                                 and cross(i2, msk) == need)
                if not keep:
                    ok = False
                    break
                nd[jj] = keep
                for i2 in keep:
                    reach |= info[i2][1]
            if not ok:
                continue
            newcov = covered | msk
            if (full & ~newcov) & ~reach:
                continue
            placed[j] = i
            r = rec(nd, placed, newcov)
            if r is not None:
                return r
            del placed[j]
        return None

    res = rec(doms, {}, 0)
    _cp_solve.nodes = nodes[0]
    _cp_solve.operations = ops[0]
    _cp_solve.seconds = time.time() - t0
    _cp_solve.candidates = len(cands)
    if all_solutions:
        return None if capped[0] else count[0]
    if res is None:
        return None
    return [sorted(info[res[j]][0]) for j in range(m)]


def attack_cp_mrv(inst, seed=0):
    """Domain-standard: CP + forward checking + MRV (Algorithm-X flavoured)."""
    _, adj = _chimera(inst["L"], inst["t"])
    sol = _cp_solve(adj, inst["n"], inst["k"], inst["C"],
                    node_cap=2_000_000, time_cap=120.0)
    if sol is None:
        return None
    ok, _ = verify(inst, sol)
    return sol if ok else None


def attack_static_backtrack(inst, seed=0, node_cap=2_000_000):
    """The same search WITHOUT MRV or forward checking -- fixed label order."""
    _, adj = _chimera(inst["L"], inst["t"])
    n, k, C = inst["n"], inst["k"], inst["C"]
    m = len(C)
    cands = _connected_ksets(adj, n, k)
    info = []
    for S in cands:
        internal = sum(1 for a, b in itertools.combinations(S, 2) if b in adj[a])
        info.append((S, set(S), internal))
    per = [[x for x in info if x[2] == C[j][j]] for j in range(m)]
    order = sorted(range(m), key=lambda j: (-sum(C[j]), j))
    nodes = [0]
    placed = {}
    used = set()
    t0 = time.time()

    def cross(S, T):
        return sum(1 for a in S for b in adj[a] if b in T)

    def rec(d):
        if nodes[0] > node_cap or time.time() - t0 > 60.0:
            return None
        if d == m:
            return dict(placed)
        j = order[d]
        for S, Sset, _ie in per[j]:
            nodes[0] += 1
            if nodes[0] > node_cap or time.time() - t0 > 60.0:
                return None
            if Sset & used:
                continue
            if any(cross(Sset, placed[jj][1]) != C[j][jj] for jj in placed):
                continue
            placed[j] = (S, Sset)
            used.update(Sset)
            r = rec(d + 1)
            if r is not None:
                return r
            used.difference_update(Sset)
            del placed[j]
        return None

    res = rec(0)
    attack_static_backtrack.nodes = nodes[0]
    if res is None:
        return None
    sol = [sorted(res[j][0]) for j in range(m)]
    ok, _ = verify(inst, sol)
    return sol if ok else None


def attack_greedy_growth(inst, seed=0):
    """Greedy: grow chain 0 from the least-constrained qubit, then chain 1, ..."""
    _, adj = _chimera(inst["L"], inst["t"])
    n, k, C, m = inst["n"], inst["k"], inst["C"], inst["m"]
    rng = random.Random(seed)
    free = set(range(n))
    fibers = []
    for j in range(m):
        best = None
        for start in sorted(free):
            f = {start}
            while len(f) < k:
                cand = sorted(w for v in f for w in adj[v] & free if w not in f)
                if not cand:
                    break
                f.add(cand[0])
            if len(f) != k:
                continue
            bad = sum(abs(sum(1 for a in f for b in adj[a] if b in g)
                          - C[j][jj]) for jj, g in enumerate(fibers))
            if best is None or bad < best[0]:
                best = (bad, sorted(f))
            if bad == 0:
                break
        if best is None:
            return None
        fibers.append(set(best[1]))
        free -= set(best[1])
    sol = [sorted(f) for f in fibers]
    ok, _ = verify(inst, sol)
    return sol if ok else None


def attack_random_restart(inst, seed=0, restarts=1000):
    rng = random.Random(seed * 7919 + 13)
    for _ in range(restarts):
        cand = random_candidate(inst, rng)
        ok, _ = verify(inst, cand)
        if ok:
            return cand
    return None


def attack_outlier_statistics(inst, seed=0):
    """Is a planted chain visible from a per-qubit statistic?

    Rank qubits by (degree, cell position parity) and pair them off greedily
    into chains, in the hope that the plant left a positional signature.
    """
    _, adj = _chimera(inst["L"], inst["t"])
    n, k, m = inst["n"], inst["k"], inst["m"]
    order = sorted(range(n), key=lambda v: (-len(adj[v]), v))
    free = set(order)
    fibers = []
    for _ in range(m):
        f = set()
        for v in order:
            if v in free:
                f.add(v)
                free.discard(v)
                break
        while len(f) < k:
            cand = sorted(w for v in f for w in adj[v] & free if w not in f)
            if not cand:
                return None
            w = cand[0]
            f.add(w)
            free.discard(w)
        fibers.append(sorted(f))
    ok, _ = verify(inst, fibers)
    return fibers if ok else None


def attack_spectral(inst, seed=0):
    """Spectral: Laplacian power iteration, sort qubits by the Fiedler-ish
    coordinate, cut into contiguous k-blocks.  (Floats live here, in the ATTACK
    only; verify() never sees one.)"""
    _, adj = _chimera(inst["L"], inst["t"])
    n, k = inst["n"], inst["k"]
    rng = random.Random(seed)
    x = [rng.random() - 0.5 for _ in range(n)]
    for _ in range(200):
        y = [sum(x[w] for w in adj[v]) - len(adj[v]) * x[v] for v in range(n)]
        mu = sum(y) / n
        y = [v - mu for v in y]
        nrm = math.sqrt(sum(v * v for v in y)) or 1.0
        x = [v / nrm for v in y]
    order = sorted(range(n), key=lambda v: x[v])
    fibers = [sorted(order[i:i + k]) for i in range(0, n, k)]
    for perm in (fibers,):
        ok, _ = verify(inst, perm)
        if ok:
            return perm
    return None


ATTACKS = {
    "outlier_degree_position": attack_outlier_statistics,
    "greedy_chain_growth": attack_greedy_growth,
    "random_restart_1k": attack_random_restart,
    "spectral_laplacian_cut": attack_spectral,
    "static_backtracking_2e6": attack_static_backtrack,
    "cp_mrv_forward_checking": attack_cp_mrv,     # <- the domain standard
}


# --------------------------------------------------------------------------
# gates
# --------------------------------------------------------------------------

def _answer_size(ans):
    s = json.dumps(ans, separators=(",", ":"))
    atoms = sum(len(f) for f in ans)
    return len(s), atoms, max(1, len(s) // 4)


def selftest(shipping=SHIPPING_DIFFICULTY, verbose=True):
    t_start = time.time()
    rep = {"paper": "1810.01440", "track": TRACK, "shipping": shipping}

    def say(*a):
        if verbose:
            print(*a)
            sys.stdout.flush()

    # ---- G1
    ok = tot = 0
    for name, p in DIFFICULTY.items():
        for seed in range(6):
            inst = make_instance(seed=seed, **p)
            good, why = verify(inst, inst["answer"])
            tot += 1
            ok += bool(good)
            if not good:
                say("G1 FAIL", name, seed, why)
    rep["G1_planted_verifies"] = {"pass": ok == tot, "ok": ok, "total": tot}
    say("G1", rep["G1_planted_verifies"])

    ship = DIFFICULTY[shipping]
    inst = make_instance(seed=0, **ship)
    ans = inst["answer"]

    # ---- G2
    reasons = {}
    a = [list(f) for f in ans]
    reasons["drop_one_fiber"] = verify(inst, a[:-1])[1]
    b = [list(f) for f in ans]
    b[0] = b[0][:-1]
    reasons["short_fiber"] = verify(inst, b)[1]
    c = [list(f) for f in ans]
    c[0][0], c[1][0] = c[1][0], c[0][0]
    reasons["swap_two_qubits"] = verify(inst, c)[1]
    d = [list(f) for f in ans]
    d[0][0] = d[1][0]
    reasons["duplicate_qubit"] = verify(inst, d)[1]
    reasons["empty"] = verify(inst, [])[1]
    e = [list(f) for f in ans]
    e[0][0] = inst["n"] + 5
    reasons["out_of_range"] = verify(inst, e)[1]
    f2 = [list(x) for x in ans]
    f2[0], f2[1] = f2[1], f2[0]
    reasons["permuted_labels"] = verify(inst, f2)[1]
    rejected = all(not verify(inst, x)[0] for x in
                   (a[:-1], b, c, d, [], e, f2))
    rep["G2_rejects_corruption"] = {
        "pass": rejected and len(set(reasons.values())) >= 5,
        "distinct_reasons": len(set(reasons.values())),
        "reasons": reasons,
    }
    say("G2", rep["G2_rejects_corruption"]["pass"],
        rep["G2_rejects_corruption"]["distinct_reasons"])

    # ---- G3
    blob = ("Here is my reasoning...\n\nSo the chains are:\n\n<answer>"
            + "; ".join(",".join(str(v) for v in f) for f in ans)
            + "</answer>\n\nHope that helps.")
    got = parse_answer(blob)
    rep["G3_round_trip"] = {"pass": got == [list(f) for f in ans],
                            "recovered": got is not None}
    say("G3", rep["G3_round_trip"])

    # ---- V: planted verifies on >= 20 seeds at the shipping preset
    vok = 0
    for seed in range(24):
        i2 = make_instance(seed=seed, **ship)
        vok += bool(verify(i2, i2["answer"])[0])
    rep["V_exact_verification"] = {"pass": vok == 24, "ok": vok, "total": 24,
                                   "floats_in_verify": 0}

    # ---- G4
    rng = random.Random(12345)
    hits = total = 0
    budget = 3000        # each structure-aware sample costs a full planting run
    #                     (0.046 s each at the shipping preset; 200k is 2.5 h)
    for _ in range(budget):
        cand = random_candidate(inst, rng)
        total += 1
        if verify(inst, cand)[0]:
            hits += 1
    ss = search_space(inst)
    rep["G4_guess_resistance"] = {
        "pass": hits == 0,
        "hits": hits, "total": total,
        "empirical_p": hits / total,
        "naive_search_space": ss,
        "naive_search_space_bits": ss.bit_length(),
        "note": ("structure-aware: every sample is already a partition into "
                 "connected k-subtrees of X"),
    }
    say("G4", rep["G4_guess_resistance"]["hits"], "/",
        rep["G4_guess_resistance"]["total"])

    # ---- G5 density + baseline cost of the STRONGEST attack, at shipping
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    exact_demo = enumerate_all(demo, cap=400000, time_cap=30.0)
    nodes = []
    secs = []
    solved = 0
    for seed in range(8):
        i2 = make_instance(seed=seed, **ship)
        got = attack_cp_mrv(i2)
        nodes.append(_cp_solve.nodes)
        secs.append(_cp_solve.seconds)
        solved += got is not None
    rep["G5_density_and_baseline"] = {
        "pass": False,
        "exact_solution_count_demo": exact_demo,
        "density_at_shipping": hits / total,
        "density_sample_size": total,
        "density_hits": hits,
        "strongest_attack": "cp_mrv_forward_checking",
        "strongest_attack_solved": solved,
        "strongest_attack_attempts": 8,
        "strongest_attack_nodes_median": sorted(nodes)[len(nodes) // 2],
        "strongest_attack_nodes_total": sum(nodes),
        "strongest_attack_wall_clock_sec": round(sum(secs), 3),
        "candidate_pool_size": _cp_solve.candidates,
    }
    say("G5", rep["G5_density_and_baseline"])

    # ---- G6
    attacks = {}
    for name, fn in ATTACKS.items():
        succ = 0
        for seed in range(8):
            i2 = make_instance(seed=seed, **ship)
            try:
                got = fn(i2, seed)
            except Exception:
                got = None
            if got is not None and verify(i2, got)[0]:
                succ += 1
        attacks[name] = {"successes": succ, "attempts": 8}
        say("   attack", name, attacks[name])
    rep["G6_adversary_panel"] = {
        "pass": all(v["successes"] == 0 for v in attacks.values()),
        "attacks": attacks,
    }
    say("G6", rep["G6_adversary_panel"]["pass"])

    # ---- G7
    esc = escalate(dict(ship))
    if isinstance(esc, dict):
        i3 = make_instance(seed=1, **esc)
        g7 = verify(i3, i3["answer"])[0]
        rep["G7_scales"] = {"pass": bool(g7), "escalated_params": esc,
                            "escalated_answer_atoms": sum(len(f) for f
                                                          in i3["answer"])}
    else:
        rep["G7_scales"] = {"pass": False, "escalated_params": esc}
    say("G7", rep["G7_scales"])

    # ---- G8
    inv_ok = inv_tot = 0
    keys = []
    for seed in range(20):
        i2 = make_instance(seed=seed, **ship)
        k0 = canonical_key(i2)
        keys.append(k0)
        m = i2["m"]
        rng2 = random.Random(seed + 77)
        for _ in range(3):
            perm = list(range(m))
            rng2.shuffle(perm)
            j2 = dict(i2)
            j2["C"] = [[i2["C"][perm[a]][perm[b]] for b in range(m)]
                       for a in range(m)]
            j2["answer"] = [i2["answer"][perm[a]] for a in range(m)]
            inv_tot += 1
            inv_ok += (canonical_key(j2) == k0)
            if _ == 0:
                # the relabelling really is the same problem
                assert verify(j2, j2["answer"])[0]
    rep["G8_canonical_key"] = {
        "pass": inv_ok == inv_tot and len(set(keys)) == 20,
        "invariance_ok": inv_ok, "invariance_total": inv_tot,
        "distinct_keys": len(set(keys)), "distinct_of": 20,
    }
    say("G8", rep["G8_canonical_key"])

    # ---- G9(c)
    chars, atoms, toks = _answer_size(ans)
    route = inst["n"] + inst["m"] * (inst["m"] - 1) // 2
    rep["G9_no_tool_suitability"] = {
        "pass": chars <= 2000 and atoms <= 256,
        "arms": {"bare": None, "hinted": None, "placebo": None},
        "hinted_minus_placebo": None,
        "hinted_verdict": "not run (no OPENROUTER_API_KEY in this environment)",
        "answer_chars": chars, "answer_tokens": toks, "answer_elements": atoms,
        "intended_route_operations": route,
    }
    say("G9", rep["G9_no_tool_suitability"])

    rep["all_pass"] = all(rep[k].get("pass") for k in rep
                          if isinstance(rep[k], dict) and "pass" in rep[k])
    rep["selftest_wall_clock_sec"] = round(time.time() - t_start, 2)
    return rep


if __name__ == "__main__":
    r = selftest()
    print(json.dumps(r, indent=2, default=str))
