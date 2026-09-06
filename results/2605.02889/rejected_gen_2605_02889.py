"""Gluing diagrams for Higman-Thompson isomorphisms -- REJECTED family (fails H).

Paper: arXiv:2605.02889, Roman Gorazd, "Gluing diagrams part 1: A constructive
solution for the Higman-Thompson group isomorphism problem" (math.GR, math.CO).

WHAT THE FAMILY IS
------------------
G_n is the one-vertex graph with n loops e_0..e_{n-1}; P(G_n, l*v) (Sec. 3, the
path space rooted at an element of the free monoid) is a forest of l infinite
n-ary trees.  Definition 3.3 (`sec2-def1`) says a FLOATING GLUING DIAGRAM from
G_n to itself with x_v = l*v is

    * a basis B_v of P(G_n, l*v)  -- the leaf set of a finite complete n-ary
      forest F with l roots; since |B_v| = l + k(n-1) must equal n*l, F has
      exactly l internal nodes and n*l leaves;
    * a partition B_v = C_{e_0} u ... u C_{e_{n-1}} with bijections
      gamma_{e_i} : C_{e_i} -> l*v.

Packing the two together, the diagram IS a bijection

    Lam : Leaves(F)  ->  {0..n-1} x {0..l-1},     leaf |-> (block, state).

Theorem 3.24 (`shift-surj-thm`) + Definition 3.20 (`defn-enable`) + Lemma 3.14
(`unblock-cover-lem`) say the induced monoid homomorphism is an isomorphism of
shift pseudogroups -- hence induces the Higman-Thompson isomorphism
V_{a,n} = V_{b,n} of Theorem 4.17 -- exactly when

  (U) UNBLOCKED.  Reading Lam on the roots that are themselves leaves gives a
      partial map beta : u |-> j.  It must be acyclic.
  (S) SHIFT-SURJECTIVE.  Read the diagram as a transducer whose configurations
      are the l internal nodes of F: from configuration c on letter x go to
      c.x if c.x is internal (emitting nothing), otherwise emit Lam(c.x) = (i,j)
      and jump to the internal node reached from root j through beta.  Then
      Def 3.20 (with the SAME suffix r' on both sides) says the diagram enables
      the shift from p to q iff there is a finite antichain of inputs on each of
      which the two runs COMPLETE SIMULTANEOUSLY IN THE SAME STATE j.  By
      Thm 3.24 this must hold for every pair of internal nodes, which is exactly:
      the product automaton on pairs, with simultaneous-equal-state completion
      made absorbing, has no cycle.

That derivation is the only nontrivial mathematics in this module and it is
cross-validated below: the paper's own ladder (Lemmas 4.9, 4.15, 4.16) produces
diagrams that satisfy (U)+(S) on 132/132 reachable (l,n) with l<=9, n<=8.

THE TASK POSED:  given n, l and the forest F, produce Lam.

WHY IT IS REJECTED -- see REJECTED.md for the numbers.  Both routes are cheap:
the compact route is the paper's Euclidean ladder (5 moves at l=5,n=7) and the
mechanical route is a depth-first search that a no-search greedy rule already
finishes on half the instances.  G and V are fine; H is not.
"""

from __future__ import annotations

import random
from math import gcd
from typing import Optional

TRACK: str = "A"          # attempted; the claim FAILS -- see REJECTED.md

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "basis of the path space P(G_n, l*v) as a complete n-ary forest",
        "gluing diagram: partition of the basis into n blocks with bijections to l*v",
    ],
    "verification_operations": [
        "prefix-code / exact-cover check on the leaf set",
        "bijection check onto {0..n-1} x {0..l-1}",
        "blocking-chain cycle detection (Def 3.13)",
        "cycle detection in the pair automaton (Def 3.20 + Thm 3.24)",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "The diagram is an isomorphism iff its transducer synchronises: any two "
        "internal nodes, fed the same letters, must eventually finish a leaf at the "
        "same moment in the same state; a solver without that reformulation is left "
        "searching the (n*l)! labellings."
    ),
    "hardness_basis": (
        "FAILS.  Claimed Track A on the ground that the labellings satisfying "
        "Thm 3.24 have density 1.0e-5 at l=4,n=6 and below 3.3e-6 at l=5,n=7.  The "
        "claim is false: solutions are astronomically numerous in absolute terms "
        "(>=6e18 at l=4,n=6) and a no-search greedy rule lands on one for 50-100% of "
        "instances."
    ),
    "max_answer_tokens": 200,
}

NATIVE: dict = {
    "domain": "algebra",
    "core": "csp_sat",
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": " +
                 PROBLEM_PROFILE["intuition_description"],
    "reduction": None,
}

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A bijection from the n*l leaves of the given forest (listed in the "
        "statement's order) onto {0..n-1} x {0..l-1}, written as n*l pairs i,j."
    ),
    "bounds": {"entries": "n*l", "block_range": "n", "state_range": "l"},
}

STRUCTURAL_HINT: str = (
    "Only the second coordinate of the labels decides the two conditions; read the "
    "labelled forest as a machine whose memory is the internal node it currently sits on."
)
PLACEBO_HINT: str = (
    "Only careful bookkeeping of the label indices decides the two conditions; write "
    "the leaves out in the order the statement lists them before you start."
)

DIFFICULTY: dict = {
    "demo":   {"n": 4, "l": 2},
    "easy":   {"n": 5, "l": 3},
    "medium": {"n": 6, "l": 4},
    "hard":   {"n": 7, "l": 5},
}
SHIPPING_DIFFICULTY = "hard"


# ---------------------------------------------------------------- structure

def _leaves(n: int, l: int, internal) -> list:
    out = [(u,) for u in range(l) if (u,) not in internal]
    for c in internal:
        for x in range(n):
            if c + (x,) not in internal:
                out.append(c + (x,))
    return sorted(out)


def _valid(n: int, l: int, internal, lam) -> tuple:
    """(U)+(S) of the module docstring.  Exact, integer-only, O(l^2 n)."""
    internal = frozenset(internal)
    lv = _leaves(n, l, internal)
    if set(lam.keys()) != set(lv):
        return False, "labels are not exactly the leaves of the forest"
    if sorted(lam.values()) != sorted((i, j) for i in range(n) for j in range(l)):
        return False, "labels are not a bijection onto {0..n-1}x{0..l-1}"
    beta = {u: lam[(u,)][1] for u in range(l) if (u,) not in internal}
    for u in list(beta):
        seen, cur = set(), u
        while cur in beta:
            if cur in seen:
                return False, "blocking cycle: the diagram is blocked (Def 3.13)"
            seen.add(cur)
            cur = beta[cur]
    res = {}
    for j in range(l):
        cur, steps = j, 0
        while cur in beta:
            cur = beta[cur]
            steps += 1
            if steps > l + 1:
                return False, "blocking cycle: the diagram is blocked (Def 3.13)"
        res[j] = (cur,)
    T = {}
    for c in internal:
        for x in range(n):
            d = c + (x,)
            if d in internal:
                T[(c, x)] = (False, None, d)
            else:
                i, j = lam[d]
                T[(c, x)] = (True, j, res[j])
    I = sorted(internal)
    idx = {c: k for k, c in enumerate(I)}
    m = len(I)
    succ = [[] for _ in range(m * m)]
    for a in I:
        for b in I:
            s = idx[a] * m + idx[b]
            for x in range(n):
                f1, j1, a2 = T[(a, x)]
                f2, j2, b2 = T[(b, x)]
                if f1 and f2 and j1 == j2:
                    continue
                succ[s].append(idx[a2] * m + idx[b2])
    color = [0] * (m * m)
    for s0 in range(m * m):
        if color[s0]:
            continue
        stack = [(s0, iter(succ[s0]))]
        color[s0] = 1
        while stack:
            v, it = stack[-1]
            adv = False
            for w in it:
                if color[w] == 1:
                    return False, ("the shift from internal node %s to internal node %s "
                                   "is not enabled (Thm 3.24)" % (I[v // m], I[v % m]))
                if color[w] == 0:
                    color[w] = 1
                    stack.append((w, iter(succ[w])))
                    adv = True
                    break
            if not adv:
                color[v] = 2
                stack.pop()
    return True, "ok"


# ------------------------------------------------- the paper's ladder (G)

def _trivial(n, perm):
    return (n, 1, {(0,)}, {(0, x): (perm[x], 0) for x in range(n)})


def _expand(D, u):
    """Def 3.31 / Lemma 4.9:  (l,n) -> (l+n-1, n)."""
    n, l, internal, lam = D
    inv = {v: k for k, v in lam.items()}
    I2, L2 = set(internal), dict(lam)
    for i in range(n):
        leaf = inv[(i, u)]
        del L2[leaf]
        I2.add(leaf)
        for x in range(n):
            L2[leaf + (x,)] = (i, ("NEW", x))
    old = [w for w in range(l) if w != u]
    remap = {w: k for k, w in enumerate(old)}
    for x in range(n):
        remap[("NEW", x)] = len(old) + x

    def mv(nd):
        if nd[0] == u:
            return (remap[("NEW", nd[1])],) + nd[2:]
        return (remap[nd[0]],) + nd[1:]

    return (n, l + n - 1,
            {mv(c) for c in I2 if c != (u,)},
            {mv(k): (i, remap[j]) for k, (i, j) in L2.items()})


def _add(D, rho, gplus):
    """G -> G^+ of Sec. 4 / Lemma 4.15:  (l,n) -> (l, n+l)."""
    n, l, internal, lam = D
    L2 = dict(lam)
    where = {c: k for k, c in enumerate(rho)}
    for c in internal:
        for k in range(l):
            L2[c + (n + k,)] = (n + where[c], gplus[k])
    return (n + l, l, set(internal), L2)


def _ladder_moves(l, n):
    """Lemma 4.16 (reach-lem): the Euclidean descent of (l, n-1)."""
    moves = []
    while l > 1:
        if l > n - 1:
            l -= (n - 1)
            moves.append("E")
        else:
            n -= l
            moves.append("A")
    return (l, n), list(reversed(moves))


def _build(n, l, rng):
    (l0, n0), moves = _ladder_moves(l, n)
    perm = list(range(n0))
    rng.shuffle(perm)
    D = _trivial(n0, perm)
    for mv in moves:
        if mv == "E":
            cand = [u for u in range(D[1]) if (u,) in D[2]]
            D = _expand(D, rng.choice(cand))
        else:
            rho = sorted(D[2]); rng.shuffle(rho)
            gp = list(range(D[1])); rng.shuffle(gp)
            D = _add(D, rho, gp)
    # global symmetries: relabel roots, letters, blocks (these preserve (U)+(S))
    n_, l_, I, lam = D
    sig = list(range(l_)); rng.shuffle(sig)
    pi = list(range(n_)); rng.shuffle(pi)
    tau = list(range(n_)); rng.shuffle(tau)

    def mv(nd):
        return (sig[nd[0]],) + tuple(pi[x] for x in nd[1:])

    return (n_, l_, {mv(c) for c in I},
            {mv(k): (tau[i], sig[j]) for k, (i, j) in lam.items()})


# ----------------------------------------------------------------- API

def make_instance(seed: int = 0, **params) -> dict:
    n = params.get("n", 7)
    l = params.get("l", 5)
    if gcd(l, n - 1) != 1:
        raise ValueError("(l, n) unreachable: Lemma 4.16 needs gcd(l, n-1) = 1")
    rng = random.Random(seed)
    nn, ll, internal, lam = _build(n, l, rng)     # answer built FIRST, no search
    leaves = _leaves(nn, ll, internal)
    return {
        "n": nn, "l": ll,
        "internal": [list(c) for c in sorted(internal)],
        "leaves": [list(p) for p in leaves],
        "answer": [[lam[p][0], lam[p][1]] for p in leaves],
        "seed": seed,
    }


def render(inst: dict) -> str:
    import os
    n, l = inst["n"], inst["l"]
    lv = [tuple(p) for p in inst["leaves"]]
    intr = [tuple(c) for c in inst["internal"]]

    def s(p):
        return "r%d" % p[0] if len(p) == 1 else "r%d." % p[0] + ".".join(map(str, p[1:]))

    txt = f"""A FOREST.  Take {l} rooted trees, with roots r0..r{l-1}.  Every node has
{n} children, addressed by the letters 0..{n-1}: the child of node p by letter x is
written p.x.  The following {l} nodes are the INTERNAL nodes of a finite forest F:

  {', '.join(s(c) for c in intr)}

Every other node that is a root or a child of an internal node is a LEAF of F.  The
{n*l} leaves, in this exact order, are:

  {', '.join(s(p) for p in lv)}

YOUR TASK.  Assign to each leaf a label (i, j) with 0 <= i < {n} and 0 <= j < {l}, so
that the assignment is a BIJECTION from the {n*l} leaves onto all {n*l} pairs (i, j),
and so that both conditions below hold.

Read the labelled forest as a machine.  Its CONFIGURATIONS are the {l} internal nodes.
Running the machine from configuration c on a letter x:
  * if c.x is internal, the new configuration is c.x and nothing is emitted;
  * if c.x is a leaf with label (i, j), the machine EMITS at this step and its new
    configuration is found by starting at root r_j and, while the current root r_u is
    itself a leaf with label (i', j'), moving to root r_{{j'}}, until an internal root
    is reached; that internal root is the new configuration.

CONDITION 1 (the walk above must terminate).  There must be no cycle among the roots:
if you define beta(u) = j whenever root r_u is a leaf with label (i, j), then
u, beta(u), beta(beta(u)), ... must never return to a root it has already visited.

CONDITION 2 (synchronisation).  Run TWO copies of the machine side by side, started at
any two internal nodes c and d, and feed them the SAME letters.  Say the pair SUCCEEDS
at a step if at that step BOTH copies emit and the two emitted labels have the SAME
second coordinate j.  The requirement is: for every ordered pair (c, d) of internal
nodes and every infinite sequence of letters, the pair must succeed at some step.
Equivalently: build the directed graph whose vertices are the {l*l} ordered pairs of
internal nodes, with an edge from (c, d) to (c', d') labelled x whenever feeding x does
NOT succeed and leaves the copies in configurations c' and d'; this graph must contain
no directed cycle.

OUTPUT.  Give the labels of the {n*l} leaves in exactly the order the leaves are listed
above, as {n*l} pairs "i,j" separated by spaces.

Give your final answer inside <answer></answer> tags.
Example: <answer>{' '.join('%d,%d' % (k % n, k % l) for k in range(min(4, n*l)))} ...</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        txt += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        txt += "\n\n" + PLACEBO_HINT
    return txt


def parse_answer(text: str) -> Optional[list]:
    if text is None:
        return None
    import re
    m = re.findall(r"<answer>(.*?)</answer>", text, re.S | re.I)
    body = m[-1] if m else text
    body = body.replace("`", " ").replace("(", " ").replace(")", " ")
    pairs = re.findall(r"(-?\d+)\s*,\s*(-?\d+)", body)
    if not pairs:
        return None
    try:
        return [[int(a), int(b)] for a, b in pairs]
    except ValueError:
        return None


def verify(inst: dict, answer) -> tuple:
    n, l = inst["n"], inst["l"]
    lv = [tuple(p) for p in inst["leaves"]]
    if not isinstance(answer, (list, tuple)):
        return False, "answer must be a list of pairs"
    if len(answer) != len(lv):
        return False, "answer must have exactly %d pairs" % len(lv)
    lam = {}
    for p, e in zip(lv, answer):
        if not isinstance(e, (list, tuple)) or len(e) != 2:
            return False, "each entry must be a pair i,j"
        try:
            i, j = int(e[0]), int(e[1])
        except (TypeError, ValueError):
            return False, "labels must be integers"
        if not (0 <= i < n and 0 <= j < l):
            return False, "label out of range: need 0<=i<%d and 0<=j<%d" % (n, l)
        lam[p] = (i, j)
    return _valid(n, l, {tuple(c) for c in inst["internal"]}, lam)


def random_candidate(inst, rng):
    """Structure-aware: already a bijection onto {0..n-1}x{0..l-1}."""
    n, l = inst["n"], inst["l"]
    tgt = [[i, j] for i in range(n) for j in range(l)]
    rng.shuffle(tgt)
    return tgt


def search_space(inst) -> int:
    from math import factorial
    return factorial(inst["n"] * inst["l"])


def enumerate_all(inst) -> Optional[int]:
    from math import factorial
    from itertools import permutations
    n, l = inst["n"], inst["l"]
    if factorial(n * l) > 5 * 10 ** 7:
        return None
    lv = [tuple(p) for p in inst["leaves"]]
    I = {tuple(c) for c in inst["internal"]}
    tgt = [(i, j) for i in range(n) for j in range(l)]
    return sum(1 for pm in permutations(tgt) if _valid(n, l, I, dict(zip(lv, pm)))[0])


def canonical_key(inst) -> str:
    """Invariant under the symmetries of the family: relabelling roots (S_l), the
    tree letters (global S_n) and the blocks (S_n).  Keys on the multiset of
    root-relative leaf-depth profiles of the forest, which those maps preserve."""
    import hashlib
    n, l = inst["n"], inst["l"]
    I = {tuple(c) for c in inst["internal"]}
    prof = []
    for u in range(l):
        d = sorted(len(c) - 1 for c in I if c[0] == u)
        prof.append(tuple(d))
    prof.sort()
    depth_ms = sorted(len(p) - 1 for p in map(tuple, inst["leaves"]))
    blob = repr((n, l, prof, depth_ms))
    return hashlib.sha256(blob.encode()).hexdigest()[:32]


def escalate(params: dict) -> Optional[dict]:
    """Grow the ground set (n, l) at (near-)fixed answer length is impossible here:
    the answer is inherently the n*l leaf labels."""
    n, l = params["n"], params["l"]
    for dl in range(1, 12):
        for dn in range(1, 12):
            n2, l2 = n + dn, l + dl
            if gcd(l2, n2 - 1) == 1 and n2 * l2 <= 128:
                return {"n": n2, "l": l2}
    return "cap_bound"
