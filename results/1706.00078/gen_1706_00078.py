"""Locally verified Track B generator prototype for arXiv:1706.00078.

The generated object is the sparse signed matrix in Section 3 of Gillis and
Shitov, *Low-Rank Matrix Approximation in the Infinity Norm*.  A dense binary
linear system with a hidden cyclic backbone is compiled to NAE-3SAT, then through the
paper's reduction.
The submitted bit string is a compact certificate from which the verifier
constructs rational rank-one factors and checks the infinity-norm bound.

Only the Python standard library is required.  Importing this module performs
no I/O and all randomness is local to ``random.Random(seed)``.
"""

from __future__ import annotations

import hashlib
import heapq
import itertools
import json
import math
import os
import random
import re
import sys
import time
from collections import Counter, defaultdict, deque
from fractions import Fraction


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:                            # Available in the repository, but not required.
    from gvlib import exact_matrices, rationals
except ImportError:             # pragma: no cover - documented fallback
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "logic",
    "object_regime": "finite_discrete",
    "computational_core": "linear_algebra",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "implicitly defined sparse signed matrix over Z",
        "NAE-3SAT clause incidence defining the matrix",
        "exact rational infinity-norm threshold",
    ],
    "verification_operations": [
        "Boolean NAE evaluation",
        "topological sorting of the switched directed graph",
        "exact rational multiplication and comparison",
        "exact infinity-norm bound check",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 3, Lemma 3 and Theorem 2: NAE-3SAT to the oriented-graph "
        "problem and then to the signed matrix M(G,D)"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Complementing each dense equation exposes a cyclic triple system after "
        "the global-parity involution, replacing general elimination by a short "
        "step-three recurrence."
    ),
    "hardness_basis": (
        "Track B: exact GF(2) Gaussian elimination solves the displayed "
        "58-variable, 66-equation shipping system in O(R*n^2) scalar bit "
        "operations; at the shipping preset selftest measured 47,782 mean "
        "scalar bit operations and 0.00084 s, whereas the executable "
        "global-parity recurrence uses 288 exact XORs."
    ),
    "max_answer_tokens": 15,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}


DIFFICULTY: dict = {
    "demo": {"n": 8, "decoys": 0},
    "easy": {"n": 46, "decoys": 5},
    "medium": {"n": 52, "decoys": 6},
    "hard": {"n": 58, "decoys": 8},
}
SHIPPING_DIFFICULTY = "hard"


STRUCTURAL_HINT: str = (
    "The variables omitted from each dense parity equation form triples whose "
    "frequency-two pairs trace a cycle, while global parity is an involution."
)
PLACEBO_HINT: str = (
    "The variables included in each displayed parity equation use consistent "
    "labels, while careful bookkeeping avoids small transcription mistakes."
)


CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "One binary string of exactly n bits, in the displayed base-variable "
        "order; the compiled NAE reference variable is 0 and auxiliaries are "
        "locally extended by the checker."
    ),
    "bounds": {"alphabet": "01", "length": "instance n", "fixed_reference": 0},
}


G9_ORACLE_RESULTS = {
    # The hard-preset rows of the script-owned bare transcript. The hinted and
    # placebo diagnostics were not rerun after the bare loop reached cap_bound:
    # the task specification says to park the family and stop at that verdict.
    "bare": {"solved": 3, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run_after_cap_bound",
}


NOTES = (
    "Section 2, Problem 1 fixes the decision question: find real u,v with "
    "max_ij |M_ij-u_i v_j| <= k. Lemma 1 makes a known sign pattern a linear "
    "feasibility problem, Corollary 1 makes nonnegative M polynomial, and "
    "Theorem 1 is polynomial when the threshold graph has O(log n) components. "
    "Those easy regimes rule out the naive quantized rank-one planting proposed "
    "at triage. Section 3, Lemma 3 and Theorems 2--3 give the paper-central "
    "NAE-3SAT -> switching/acyclicity -> signed-matrix reduction and the hard "
    "regime with only diagonal entries above k, hence the maximum number of "
    "threshold-graph components. This generator inverse-samples a binary vector, "
    "forms an invertible cyclic system x_i+x_(i+1)+x_(i+2)=b_i over GF(2), "
    "applies the involution x_i=z_i+sum_j z_j to make every displayed equation "
    "dense, adds seed-dependent same-format equations, compiles the system to "
    "NAE-3SAT, and applies that reduction. Because the "
    "generated distribution has an efficient decoder and Gaussian solver, it is "
    "Track B, not a false Track A claim. The outlier, all-zero/alternating, "
    "greedy local-repair, polarity-majority, random restart, and bounded native "
    "NAE-DPLL attacks are tested; exact elimination is reported separately and "
    "is expected to succeed. The ladder was placed near the 300-operation G9 "
    "ceiling because the earlier 26-bit prototype was solved by the oracle pool; "
    "the current bare hardening run also solved every 58-bit hard instance and "
    "returned cap_bound, so this module is retained as a parked prototype rather "
    "than shipped or rejected."
)


# A clause is a list of three [variable, negated] pairs.  A literal has value
# assignment[variable] XOR negated, so [v, 0] is y_v and [v, 1] is not y_v.


def _nae(values):
    return not (values[0] == values[1] == values[2])


def _validate_params(n, decoys):
    if isinstance(n, bool) or not isinstance(n, int) or n < 8:
        raise ValueError("n must be an integer at least 8")
    if n % 2 or n % 3 == 0:
        raise ValueError("n must be even and not divisible by 3")
    if isinstance(decoys, bool) or not isinstance(decoys, int):
        raise ValueError("decoys must be an integer")
    if not 0 <= decoys <= 2 * n:
        raise ValueError("decoys must be between 0 and 2*n")


def _make_equations(base_values, rng, decoys):
    """Make dense parity equations with a hidden cyclic missing-set backbone.

    Missing triples consist of a cyclic backbone plus seed-dependent extras.
    Extra triples use previously unused pairs, so frequency-two missing pairs
    reveal exactly the backbone cycle.  The equation support is the complement
    of its missing triple.  For even n, changing variables by
    x_i = z_i XOR XOR_j(z_j) turns each backbone equation into the nonsingular
    cyclic system on x; n is not divisible by three.
    """
    n = len(base_values)
    missing = [(i, (i + 1) % n, (i + 2) % n) for i in range(n)]
    used_pairs = {
        tuple(sorted(pair))
        for triple in missing
        for pair in itertools.combinations(triple, 2)
    }
    candidates = list(itertools.combinations(range(n), 3))
    rng.shuffle(candidates)
    if decoys:
        for triple in candidates:
            pairs = {tuple(sorted(pair)) for pair in itertools.combinations(triple, 2)}
            if pairs.isdisjoint(used_pairs):
                missing.append(triple)
                used_pairs.update(pairs)
                if len(missing) == n + decoys:
                    break
    if len(missing) != n + decoys:
        raise ValueError("too many decoy supports for this n")
    equations = []
    universe = set(range(n))
    for triple in missing:
        support = tuple(sorted(universe - set(triple)))
        rhs = 0
        for var in support:
            rhs ^= base_values[var]
        equations.append((support, rhs))
    return equations


def _chain_xor_rows(base_values, equations):
    """Decompose high-arity XOR equations into ternary XOR rows."""
    logical_values = list(base_values)
    ternary_rows = []
    for support, rhs in equations:
        if len(support) == 3:
            ternary_rows.append((tuple(support), rhs))
            continue
        previous = len(logical_values)
        logical_values.append(base_values[support[0]] ^ base_values[support[1]])
        ternary_rows.append(((support[0], support[1], previous), 0))
        for offset in range(2, len(support) - 2):
            nxt = len(logical_values)
            logical_values.append(logical_values[previous] ^ base_values[support[offset]])
            ternary_rows.append(((previous, support[offset], nxt), 0))
            previous = nxt
        ternary_rows.append(((previous, support[-2], support[-1]), rhs))
    return logical_values, ternary_rows


def _xor_to_nae(base_values, xor_rows):
    """Return unpermuted clauses, F id, auxiliary values, and variable count.

    A parity equation is four ordinary 3-CNF clauses.  Each ordinary clause
    (a or b or c), interpreted relative to F=0, becomes
        NAE(a,b,z) and NAE(not z,c,F).
    The equivalence is checked exhaustively in selftest.
    """
    n = len(base_values)
    fixed = n
    next_var = n + 1
    clauses = []
    full_assignment = {i: int(base_values[i]) for i in range(n)}
    full_assignment[fixed] = 0
    for support, rhs in xor_rows:
        for forbidden in itertools.product((0, 1), repeat=3):
            if forbidden[0] ^ forbidden[1] ^ forbidden[2] == rhs:
                continue
            # Literal [x, forbidden_bit] is false exactly on the forbidden bit.
            ordinary = [[support[t], forbidden[t]] for t in range(3)]
            aux = next_var
            next_var += 1
            c1 = [ordinary[0], ordinary[1], [aux, 0]]
            c2 = [[aux, 1], ordinary[2], [fixed, 0]]
            choices = []
            for bit in (0, 1):
                trial = dict(full_assignment)
                trial[aux] = bit
                vals1 = [trial[v] ^ neg for v, neg in c1]
                vals2 = [trial[v] ^ neg for v, neg in c2]
                if _nae(vals1) and _nae(vals2):
                    choices.append(bit)
            if not choices:
                raise AssertionError("3-CNF to NAE encoding lost a satisfying clause")
            full_assignment[aux] = choices[0]
            clauses.extend((c1, c2))
    return clauses, fixed, full_assignment, next_var


def _assemble_instance(n, decoys, equations, base_values, base_variables=None):
    logical_values, ternary_rows = _chain_xor_rows(base_values, equations)
    clauses, fixed, full_assignment, variable_count = _xor_to_nae(
        logical_values, ternary_rows
    )
    clause_count = len(clauses)
    matrix_dimension = 2 * variable_count + 3 * clause_count
    epsilon = Fraction(1, 100 * matrix_dimension * matrix_dimension)
    threshold = Fraction(3, 2) - epsilon / 8
    output_order = list(range(n)) if base_variables is None else list(base_variables)
    return {
        "family": "paper Section 3 signed-matrix reduction",
        "n": n,
        "decoys": decoys,
        "equations": [
            {"vars": list(support), "rhs": rhs} for support, rhs in equations
        ],
        "xor_row_count": len(ternary_rows),
        "logical_variable_count": len(logical_values),
        "variable_count": variable_count,
        "fixed_zero": fixed,
        "base_variables": output_order,
        "clauses": clauses,
        "matrix_dimension": matrix_dimension,
        "threshold": [threshold.numerator, threshold.denominator],
        "answer": "".join(str(base_values[v]) for v in output_order),
    }


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate a parity witness and carry it through Section 3.

    The answer is sampled first.  No search or solver is called during
    generation.  ``n`` is the number of base variables and therefore the
    logarithm of the structure-aware candidate space.
    """
    decoys = params.pop("decoys", 0)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, decoys)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    base_values = [rng.randrange(2) for _ in range(n)]
    equations = _make_equations(base_values, rng, decoys)

    # Apply a genuine base-variable relabelling before presentation.
    old_to_new = list(range(n))
    rng.shuffle(old_to_new)
    presented_values = [0] * n
    for old, new in enumerate(old_to_new):
        presented_values[new] = base_values[old]
    presented_equations = []
    for support, rhs in equations:
        presented_equations.append(
            (tuple(sorted(old_to_new[v] for v in support)), rhs)
        )
    rng.shuffle(presented_equations)
    return _assemble_instance(
        n, decoys, presented_equations, presented_values
    )


def _literal_text(literal):
    var, neg = literal
    return ("-" if neg else "+") + f"y{var}"


def render(inst) -> str:
    """Render the complete implicit sparse matrix problem and output format."""
    vcount = inst["variable_count"]
    q = inst["matrix_dimension"]
    kn, kd = inst["threshold"]
    base = ", ".join(f"y{x}" for x in inst["base_variables"])
    equation_lines = []
    for ei, equation in enumerate(inst["equations"]):
        omitted = sorted(set(range(inst["n"])) - set(equation["vars"]))
        missing_text = ", ".join(f"y{x}" for x in omitted)
        equation_lines.append(
            f"  e{ei}: omit {{{missing_text}}}; XOR of all other base bits = "
            f"{equation['rhs']}"
        )

    statement = f"""Certified rank-one approximation of a sparse signed matrix

XOR means addition modulo 2.  There are {inst['n']} base bits y0,...,y{inst['n'] - 1}.
Submit their values in exactly this displayed order:
  {base}

They must satisfy all {len(inst['equations'])} dense parity equations below.
For each row, XOR every base bit exactly once except the three named after
"omit"; that XOR must equal the displayed right-hand side.  Braces denote an
unordered set and do not add another operation.
{chr(10).join(equation_lines)}

For completeness, these equations define an exact q-by-q signed integer matrix
M, q={q}, by the following deterministic compilation.  This is part of the
instance, so no knowledge of the source paper is assumed.

1. Process equations e0,e1,... in displayed order.  Within each equation use
   its variables in increasing subscript order.  Replace an XOR of
   a0,...,a(w-1), where w={inst['n'] - 3}, by a left-associated chain of ternary
   XOR relations.  Introduce fresh connector bits starting at y{inst['n']}:
   a0 XOR a1 XOR p0=0; for each t=1,...,w-4 add
   p(t-1) XOR a(t+1) XOR pt=0; and finish with
   p(last) XOR a(w-2) XOR a(w-1)=the displayed right-hand side.  Fresh bits are
   numbered consecutively across equations.  This produces
   {inst['xor_row_count']} ternary XOR relations and
   {inst['logical_variable_count']} logical bits.
2. Introduce the fixed bit F=y{inst['fixed_zero']}=0.  For each ternary relation
   a XOR b XOR c=r, take the four forbidden triples (fa,fb,fc) whose XOR is not
   r, in lexicographic order.  For each forbidden triple introduce one fresh
   gate bit g and the two NAE clauses
       NAE(L(a,fa), L(b,fb), +g),  NAE(-g, L(c,fc), +F),
   where L(y,0)=+y, L(y,1)=-y, +y has value y, -y has value 1-y, and NAE means
   that the three literal values are not all equal.  Gate bits are consecutive
   after F.  This gives {vcount} Boolean variables and {len(inst['clauses'])}
   NAE clauses, in the order just specified.
3. From those clauses build the oriented graph and matrix.  For every Boolean
   variable ya create vertices P(a)=2a and N(a)=2a+1.  For clause ct and
   position h create O(t,h)=2*{vcount}+3t+h.  Set M[i,i]=2.  Set both entries
   between P(a),N(a) to -1.  If clause position (t,h) is +ya, set both entries
   between O(t,h),N(a) to -1; for -ya use P(a).  Finally direct the three-cycle
   O(t,0)->O(t,1)->O(t,2)->O(t,0), putting -1 in each forward matrix entry and
   +1 in its reverse.  Every unassigned matrix entry is 0.

No pair receives conflicting rules.  The threshold is the exact rational
k={kn}/{kd}.  The checker extends valid base bits through the XOR chains and NAE
gates, applies the matrix construction, reverses directed edges whose endpoint
bits differ, topologically orders the result, constructs explicit rational
vectors u,v, and checks exactly that
max(i,j) |M[i,j]-u[i]*v[j]| <= k.  Thus the submitted bits are a compressed,
executable certificate for a rank-one approximation; no floating point is used.

The answer is one string of exactly {inst['n']} characters from {{0,1}}.  Bit
position 0 is the value of the first displayed base variable, and so on.
Order matters and there are no separators.

Give your final answer inside <answer></answer> tags, as that binary string.
Example format only: <answer>{'01' * (inst['n'] // 2) + ('0' if inst['n'] % 2 else '')}</answer>
Output nothing else inside the tags."""

    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Extract one tagged binary string; return None on all malformed input."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\s*>(.*?)</answer\s*>", text,
                         flags=re.IGNORECASE | re.DOTALL)
    if len(matches) != 1:
        return None
    body = matches[0].strip()
    body = re.sub(r"^```(?:text)?\s*", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\s*```$", "", body).strip()
    if len(body) >= 2 and body[0] == body[-1] == '"':
        try:
            body = json.loads(body)
        except (TypeError, ValueError):
            return None
    if not isinstance(body, str) or not re.fullmatch(r"[01]+", body):
        return None
    return body


def _decode_xor(inst):
    """Validate and return the displayed high-arity parity equations."""
    rows = []
    for equation in inst["equations"]:
        support = tuple(equation["vars"])
        rhs = equation["rhs"]
        if (len(support) != inst["n"] - 3 or len(set(support)) != len(support)
                or any(isinstance(v, bool) or not isinstance(v, int)
                       or not 0 <= v < inst["n"] for v in support)
                or rhs not in (0, 1)):
            raise ValueError("malformed dense parity equation")
        rows.append((support, rhs))
    if len(rows) != inst["n"] + inst["decoys"]:
        raise ValueError("dense parity equation count is wrong")
    return tuple(rows)


def _base_assignment(inst, answer):
    return {var: int(answer[i]) for i, var in enumerate(inst["base_variables"])}


def _base_satisfies_xor(inst, assignment):
    # This is the hot rejection path for G4.  Shape validation is deliberately
    # deferred to _extend_assignment: almost every candidate fails an equation,
    # while a candidate that passes all equations is then checked against the
    # fully validated compilation before it can be accepted.
    for equation in inst["equations"]:
        support, rhs = equation["vars"], equation["rhs"]
        value = 0
        for var in support:
            value ^= assignment[var]
        if value != rhs:
            return False
    return True


def _extend_assignment(inst, base_assignment):
    """Construct all chain and NAE-gate bits from submitted base bits."""
    base_values = [base_assignment[i] for i in range(inst["n"])]
    logical, ternary = _chain_xor_rows(base_values, _decode_xor(inst))
    clauses, fixed, assignment, variable_count = _xor_to_nae(logical, ternary)
    if (clauses != inst["clauses"] or fixed != inst["fixed_zero"]
            or variable_count != inst["variable_count"]):
        return None
    return assignment


def _graph_certificate(inst, assignment):
    """Return switching signs, reverse-topological positions, D pairs, edges."""
    vcount = inst["variable_count"]
    clauses = inst["clauses"]
    q = inst["matrix_dimension"]
    colors = [0] * q
    d_pairs = []
    edges = []

    for var in range(vcount):
        p, n = 2 * var, 2 * var + 1
        colors[p] = assignment[var]
        colors[n] = 1 - assignment[var]
        d_pairs.append((p, n))
    offset = 2 * vcount
    for ci, clause in enumerate(clauses):
        occ = [offset + 3 * ci + h for h in range(3)]
        for h, (var, neg) in enumerate(clause):
            literal_value = assignment[var] ^ neg
            colors[occ[h]] = literal_value
            opposite_vertex = 2 * var + (1 if neg == 0 else 0)
            d_pairs.append((occ[h], opposite_vertex))
        edges.extend(((occ[0], occ[1]), (occ[1], occ[2]), (occ[2], occ[0])))

    switched = []
    for a, b in edges:
        switched.append((b, a) if colors[a] != colors[b] else (a, b))
    outgoing = [[] for _ in range(q)]
    indegree = [0] * q
    for a, b in switched:
        outgoing[a].append(b)
        indegree[b] += 1
    ready = [i for i in range(q) if indegree[i] == 0]
    heapq.heapify(ready)
    topological = []
    while ready:
        a = heapq.heappop(ready)
        topological.append(a)
        for b in outgoing[a]:
            indegree[b] -= 1
            if indegree[b] == 0:
                heapq.heappush(ready, b)
    if len(topological) != q:
        return None
    # Paper Observation 1 uses a>b along an edge; reverse source-first order.
    position = [0] * q
    for rank, vertex in enumerate(topological):
        position[vertex] = q - 1 - rank
    signs = [1 if color == 0 else -1 for color in colors]
    return signs, position, d_pairs, edges


def _factor_vectors(inst, signs, position):
    q = inst["matrix_dimension"]
    epsilon = Fraction(1, 100 * q * q)
    u, v = [], []
    for i in range(q):
        t = position[i]
        positive_u = 1 - t * epsilon
        positive_v = Fraction(1, 2) + Fraction(t, 2) * epsilon + epsilon / 4
        u.append(signs[i] * positive_u)
        v.append(signs[i] * positive_v)
    return u, v


def _matrix_certificate_ok(inst, assignment):
    graph = _graph_certificate(inst, assignment)
    if graph is None:
        return False, "switched directed graph contains a cycle"
    signs, position, d_pairs, edges = graph
    q = inst["matrix_dimension"]

    # Evaluate the proof's rational factors with cross-multiplied integers.
    # If D=100q^2 and t is the reverse-topological position, then
    #   u=(D-t)/D,  v=(2D+2t+1)/(4D),
    # up to the switching signs.  The common product denominator is 4D^2 and
    # k=(12D-1)/(8D).  This is exactly the same check as Fraction arithmetic,
    # but avoids allocating hundreds of thousands of Fraction objects.
    d = 100 * q * q
    product_den = 4 * d * d
    k_num, k_den = 12 * d - 1, 8 * d

    def within(entry, a, b):
        t_a, t_b = position[a], position[b]
        product_num = (d - t_a) * (2 * d + 2 * t_b + 1)
        if signs[a] != signs[b]:
            product_num = -product_num
        return (abs(entry * product_den - product_num) * k_den
                <= k_num * product_den)

    for i in range(q):
        if not within(2, i, i):
            return False, f"diagonal matrix entry {i} exceeds the error bound"
    for a, b in d_pairs:
        if not within(-1, a, b):
            return False, "a symmetric -1 entry exceeds the error bound"
        if not within(-1, b, a):
            return False, "the reverse symmetric -1 entry exceeds the error bound"
    for a, b in edges:
        if not within(-1, a, b):
            return False, "a directed -1 entry exceeds the error bound"
        if not within(1, b, a):
            return False, "a directed +1 entry exceeds the error bound"

    # Every remaining entry is exactly zero.  This exact product bound checks
    # all of them at once and is stronger than enumerating q^2 sparse zeros.
    max_product_num = d * (2 * d + 2 * (q - 1) + 1)
    if max_product_num * k_den > k_num * product_den:
        return False, "an unlisted zero entry could exceed the error bound"
    return True, "ok"


def verify(inst, answer):
    """Verify any submitted base assignment without consulting the planted witness."""
    if not isinstance(answer, str):
        return False, "answer must be a binary string"
    if answer == "":
        return False, "answer string is empty"
    n = inst["n"]
    if len(answer) < n:
        return False, f"bit string is too short: expected {n}, got {len(answer)}"
    if len(answer) > n:
        return False, f"bit string is too long: expected {n}, got {len(answer)}"
    if not re.fullmatch(r"[01]+", answer):
        return False, "answer contains a character outside {0,1}"
    assignment = _base_assignment(inst, answer)
    try:
        if not _base_satisfies_xor(inst, assignment):
            return False, "base assignment violates a displayed dense parity equation"
        extended = _extend_assignment(inst, assignment)
    except (KeyError, ValueError) as exc:
        return False, "malformed instance encoding: " + str(exc)
    if extended is None:
        return False, "base assignment has no exact compiled NAE extension"
    return _matrix_certificate_ok(inst, extended)


def random_candidate(inst, rng):
    """Uniformly sample the exact n-bit, fixed-reference language."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    return format(rng.getrandbits(inst["n"]), f"0{inst['n']}b")


def search_space(inst):
    return 1 << inst["n"]


def enumerate_all(inst):
    n = inst["n"]
    if n > 16:
        return None
    count = 0
    for value in range(1 << n):
        candidate = format(value, f"0{n}b")
        count += int(verify(inst, candidate)[0])
    return count


def _cycle_data(inst):
    """Recover one orientation of the frequency-two backbone cycle."""
    rows = _decode_xor(inst)
    pair_count = Counter()
    rhs_by_support = {}
    for support, rhs in rows:
        missing = frozenset(set(range(inst["n"])) - set(support))
        rhs_by_support[missing] = rhs
        for pair in itertools.combinations(missing, 2):
            pair_count[tuple(sorted(pair))] += 1
    adjacency = defaultdict(list)
    for (a, b), count in pair_count.items():
        if count == 2:
            adjacency[a].append(b)
            adjacency[b].append(a)
    vertices = sorted(inst["base_variables"])
    if any(len(adjacency[v]) != 2 for v in vertices):
        raise ValueError("decoded supports do not form one cycle")
    start = vertices[0]
    second = min(adjacency[start])
    seq = [start, second]
    while len(seq) < len(vertices):
        prev, cur = seq[-2], seq[-1]
        nxt = adjacency[cur][0] if adjacency[cur][0] != prev else adjacency[cur][1]
        if nxt == start:
            break
        seq.append(nxt)
    if len(seq) != len(vertices):
        raise ValueError("could not canonically traverse support cycle")
    rhs = []
    backbone = set()
    for i in range(len(seq)):
        support = frozenset((seq[i], seq[(i + 1) % len(seq)],
                             seq[(i + 2) % len(seq)]))
        if support not in rhs_by_support:
            raise ValueError("a cyclic-backbone parity row is missing")
        backbone.add(support)
        rhs.append(rhs_by_support[support])
    return tuple(seq), tuple(rhs), frozenset(backbone)


def _compact_recurrence(inst):
    """Solve through the global-parity involution; count exact XORs.

    XORing adjacent equations gives x[i+3] = x[i] XOR b[i] XOR b[i+1].
    Because gcd(n,3)=1, stepping by three visits every coordinate.  One
    original equation then fixes the remaining global bit.  For even n the
    map x_i = z_i XOR XOR_j(z_j) is its own inverse.
    """
    seq, rhs, _ = _cycle_data(inst)
    n = len(seq)
    constants = [None] * n
    constants[0] = 0
    current = 0
    xor_operations = 0
    for _ in range(n - 1):
        nxt = (current + 3) % n
        if constants[nxt] is not None:
            raise ValueError("step-three recurrence closed before visiting the cycle")
        constants[nxt] = constants[current] ^ rhs[current] ^ rhs[(current + 1) % n]
        xor_operations += 2
        current = nxt
    x0 = rhs[0] ^ constants[1] ^ constants[2]
    xor_operations += 2
    values = [0] * n
    values[0] = x0
    for i in range(1, n):
        values[i] = x0 ^ constants[i]
        xor_operations += 1
    global_xor = values[0]
    for i in range(1, n):
        global_xor ^= values[i]
        xor_operations += 1
    z_values = [value ^ global_xor for value in values]
    xor_operations += n
    by_variable = {seq[i]: z_values[i] for i in range(n)}
    answer = "".join(str(by_variable[v]) for v in inst["base_variables"])
    return answer, {"xor_operations": xor_operations}


def _canonical_support_signature(inst):
    """Canonicalise backbone plus decoys under all cycle dihedral symmetries."""
    rows = _decode_xor(inst)
    supports = {
        frozenset(set(range(inst["n"])) - set(support))
        for support, _ in rows
    }
    seq, _, backbone = _cycle_data(inst)
    candidates = []
    for oriented in (seq, tuple(reversed(seq))):
        for shift in range(len(oriented)):
            order = oriented[shift:] + oriented[:shift]
            position = {v: i for i, v in enumerate(order)}
            decoys = sorted(
                tuple(sorted(position[v] for v in support))
                for support in supports
                if support not in backbone
            )
            candidates.append(tuple(decoys))
    if not candidates:
        raise ValueError("could not canonicalise support hypergraph")
    return min(candidates)


def canonical_key(inst):
    payload = {
        "family": "cyclic-xor-to-nae-to-M",
        "n": inst["n"],
        # Right-hand sides are intentionally absent: complementing any Boolean
        # variable and all of its literal occurrences is a signed-variable
        # relabelling, and can carry one RHS vector to another.  Seed diversity
        # comes from the extra support hypergraph, not from planted values.
        "decoy_supports": _canonical_support_signature(inst),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def escalate(params):
    current = dict(params)
    n = int(current.get("n", 5))
    decoys = int(current.get("decoys", 0))
    # The earlier sweep established that adding redundant equations makes the
    # displayed system easier for no-tool solvers, not harder.  Grow n only
    # while the compact recurrence remains inside the 300-XOR G9 ceiling.
    if n < 58:
        candidate = min(58, n + 6)
        return {"n": candidate, "decoys": min(8, max(decoys, candidate // 10))}
    return "cap_bound"


def _reference_gaussian(inst):
    """Decode and solve by exact GF(2) RREF; return answer and operation counts."""
    t0 = time.perf_counter()
    variables = list(inst["base_variables"])
    index = {v: i for i, v in enumerate(variables)}
    n = len(variables)
    rows = []
    for support, rhs in _decode_xor(inst):
        mask = 0
        for var in support:
            mask ^= 1 << index[var]
        rows.append(mask | (rhs << n))
    pivot_row = 0
    row_xors = 0
    swaps = 0
    for col in range(n):
        pivot = next((r for r in range(pivot_row, len(rows))
                      if (rows[r] >> col) & 1), None)
        if pivot is None:
            continue
        if pivot != pivot_row:
            rows[pivot], rows[pivot_row] = rows[pivot_row], rows[pivot]
            swaps += 1
        for r in range(len(rows)):
            if r != pivot_row and ((rows[r] >> col) & 1):
                rows[r] ^= rows[pivot_row]
                row_xors += 1
        pivot_row += 1
    if pivot_row != n:
        return None, {
            "row_xors": row_xors, "scalar_bit_operations": row_xors * (n + 1),
            "swaps": swaps, "elapsed_sec": time.perf_counter() - t0,
        }
    solution = [0] * n
    for r in range(n):
        lead = next(c for c in range(n) if (rows[r] >> c) & 1)
        solution[lead] = (rows[r] >> n) & 1
    answer = "".join(str(x) for x in solution)
    stats = {
        "row_xors": row_xors,
        "scalar_bit_operations": row_xors * (n + 1),
        "swaps": swaps,
        "elapsed_sec": time.perf_counter() - t0,
    }
    return answer, stats


def _attack_all_zero(inst):
    return "0" * inst["n"]


def _attack_alternating(inst):
    return "".join(str(i & 1) for i in range(inst["n"]))


def _attack_polarity_majority(inst):
    score = {v: [0, 0] for v in inst["base_variables"]}
    for clause in inst["clauses"]:
        for var, neg in clause:
            if var in score:
                score[var][neg] += 1
    return "".join("1" if score[v][0] > score[v][1] else "0"
                   for v in inst["base_variables"])


def _violated_rows(inst, bits):
    assignment = _base_assignment(inst, bits)
    bad = []
    for support, rhs in _decode_xor(inst):
        value = 0
        for var in support:
            value ^= assignment[var]
        if value != rhs:
            bad.append(support)
    return bad


def _attack_greedy_flip(inst):
    bits = list(_attack_polarity_majority(inst))
    variables = inst["base_variables"]
    for _ in range(inst["n"]):
        current = len(_violated_rows(inst, "".join(bits)))
        best = current
        best_index = None
        for i in range(inst["n"]):
            bits[i] = "1" if bits[i] == "0" else "0"
            value = len(_violated_rows(inst, "".join(bits)))
            bits[i] = "1" if bits[i] == "0" else "0"
            if value < best:
                best, best_index = value, i
        if best_index is None:
            break
        bits[best_index] = "1" if bits[best_index] == "0" else "0"
        if best == 0:
            break
    return "".join(bits)


def _attack_random_restart(inst, seed, restarts=256):
    rng = random.Random(seed ^ 0x170600078)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _attack_dpll_unit(inst, node_budget=2048):
    """Bounded, dependency-free DPLL with native NAE unit propagation."""
    clauses = inst["clauses"]
    occurrence = [0] * inst["variable_count"]
    for clause in clauses:
        for var, _ in clause:
            occurrence[var] += 1
    start = [-1] * inst["variable_count"]
    start[inst["fixed_zero"]] = 0
    nodes = 0
    exhausted = False

    def propagate(values):
        changed = True
        while changed:
            changed = False
            for clause in clauses:
                known = []
                missing = []
                for var, neg in clause:
                    if values[var] < 0:
                        missing.append((var, neg))
                    else:
                        known.append(values[var] ^ neg)
                if not missing:
                    if known[0] == known[1] == known[2]:
                        return False
                elif len(missing) == 1 and len(known) == 2 and known[0] == known[1]:
                    var, neg = missing[0]
                    required = (1 - known[0]) ^ neg
                    if values[var] >= 0 and values[var] != required:
                        return False
                    if values[var] < 0:
                        values[var] = required
                        changed = True
        return True

    def search(values):
        nonlocal nodes, exhausted
        if nodes >= node_budget:
            exhausted = True
            return None
        nodes += 1
        if not propagate(values):
            return None
        unresolved = set()
        for clause in clauses:
            literal_values = [None if values[v] < 0 else values[v] ^ neg
                              for v, neg in clause]
            if 0 in literal_values and 1 in literal_values:
                continue
            unresolved.update(v for v, _ in clause if values[v] < 0)
        if not unresolved:
            return values
        var = max(unresolved, key=lambda x: (occurrence[x], -x))
        for bit in (0, 1):
            trial = list(values)
            trial[var] = bit
            result = search(trial)
            if result is not None:
                return result
        return None

    solution = search(start)
    candidate = None
    if solution is not None:
        candidate = "".join(
            str(0 if solution[v] < 0 else solution[v])
            for v in inst["base_variables"]
        )
    return candidate, {"nodes": nodes, "exhausted": exhausted}


def _relabel_instance(inst, rng, reorder_base=False, flip_polarities=False):
    n = inst["n"]
    perm = list(range(n))
    rng.shuffle(perm)
    flips = [rng.randrange(2) if flip_polarities else 0 for _ in range(n)]
    old_bits = {v: inst["answer"][i] for i, v in enumerate(inst["base_variables"])}
    new_values = [0] * n
    for old in range(n):
        new_values[perm[old]] = int(old_bits[old]) ^ flips[old]
    equations = []
    for support, rhs in _decode_xor(inst):
        transformed_rhs = rhs
        for var in support:
            transformed_rhs ^= flips[var]
        equations.append((tuple(sorted(perm[v] for v in support)), transformed_rhs))
    rng.shuffle(equations)
    base_variables = [perm[v] for v in inst["base_variables"]]
    if reorder_base:
        rng.shuffle(base_variables)
    else:
        base_variables.sort()
    return _assemble_instance(
        n, inst["decoys"], equations, new_values, base_variables=base_variables
    )


def _answer_metrics(answer):
    encoded = json.dumps(answer, separators=(",", ":"))
    return len(encoded), math.ceil(len(encoded) / 4), len(answer)


def selftest() -> dict:
    """Run G1--G9 and return JSON-native measured evidence."""
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}
    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]

    # Also exhaustively validate the two logical compilation identities.
    logical_checks = 0
    logical_ok = True
    for vals in itertools.product((0, 1), repeat=4):
        target = len(set(vals)) > 1
        reduced = any(
            _nae((vals[0], vals[1], z)) and _nae((1 - z, vals[2], vals[3]))
            for z in (0, 1)
        )
        logical_checks += 1
        logical_ok &= target == reduced

    failures = []
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            checks += 1
            if not ok:
                failures.append([preset, seed, why])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not failures and logical_ok,
        "checks": checks,
        "logical_compilation_checks": logical_checks,
        "failures": failures,
    }

    inst = make_instance(seed=12345, **shipping_params)
    planted = inst["answer"]
    differing = next(i for i in range(1, len(planted)) if planted[i] != planted[0])
    swapped = list(planted)
    swapped[0], swapped[differing] = swapped[differing], swapped[0]
    corruptions = {
        "drop_one": planted[:-1],
        "swap_one": "".join(swapped),
        "duplicate_one": planted + planted[-1],
        "empty": "",
        "out_of_range": "2" + planted[1:],
    }
    rejected = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        rejected[name] = {"rejected": not ok, "reason": why}
    reasons = [item["reason"] for item in rejected.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in rejected.values())
        and len(set(reasons)) == len(reasons),
        "corruptions": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "The parity supports form one cycle.\n```text\n<answer>"
        + planted + "</answer>\n```\nThat is my final certificate."
    )
    parsed = parse_answer(realistic)
    garbage_none = parse_answer("No tagged binary answer here.") is None
    report["G3_round_trip"] = {
        "pass": parsed == planted and garbage_none,
        "realistic_response_parsed": parsed == planted,
        "garbage_returns_none": garbage_none,
    }

    guess_rng = random.Random(0x170600078)
    guess_total = 200_000
    guess_hits = 0
    t0 = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - t0
    probability = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_total >= 200_000 and probability < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": probability,
        "structure_aware_space": str(search_space(inst)),
        "sampler": "uniform n-bit base assignment in the exact output language",
        "sample_wall_clock_sec": guess_seconds,
    }

    attack_results = {
        "outlier_literal_polarity": {"successes": 0, "attempts": 8},
        "greedy_local_flip": {"successes": 0, "attempts": 8},
        "random_restart_256": {"successes": 0, "attempts": 8},
        "dpll_nae_unit_128_nodes": {"successes": 0, "attempts": 8,
                                     "nodes": 0, "exhausted": 0},
        "by_hand_all_zero": {"successes": 0, "attempts": 8},
        "by_hand_alternating": {"successes": 0, "attempts": 8},
    }
    ref_stats = []
    ref_successes = 0
    compact_stats = []
    compact_successes = 0
    for seed in range(800, 808):
        attack_inst = make_instance(seed=seed, **shipping_params)
        # Time the mechanical reference before any attack warms the decoder cache.
        recovered, stats = _reference_gaussian(attack_inst)
        stats["verified"] = recovered is not None and verify(attack_inst, recovered)[0]
        ref_successes += int(stats["verified"])
        ref_stats.append(stats)
        compact, compact_stat = _compact_recurrence(attack_inst)
        compact_stat["verified"] = verify(attack_inst, compact)[0]
        compact_successes += int(compact_stat["verified"])
        compact_stats.append(compact_stat)
        dpll_candidate, dpll_stats = _attack_dpll_unit(attack_inst, node_budget=128)
        candidates = {
            "outlier_literal_polarity": _attack_polarity_majority(attack_inst),
            "greedy_local_flip": _attack_greedy_flip(attack_inst),
            "random_restart_256": _attack_random_restart(attack_inst, seed),
            "dpll_nae_unit_128_nodes": dpll_candidate,
            "by_hand_all_zero": _attack_all_zero(attack_inst),
            "by_hand_alternating": _attack_alternating(attack_inst),
        }
        for name, candidate in candidates.items():
            solved = candidate is not None and verify(attack_inst, candidate)[0]
            attack_results[name]["successes"] += int(solved)
        attack_results["dpll_nae_unit_128_nodes"]["nodes"] += dpll_stats["nodes"]
        attack_results["dpll_nae_unit_128_nodes"]["exhausted"] += int(
            dpll_stats["exhausted"]
        )
    all_attacks_failed = all(x["successes"] == 0 for x in attack_results.values())
    mean_seconds = sum(x["elapsed_sec"] for x in ref_stats) / len(ref_stats)
    mean_row_xors = sum(x["row_xors"] for x in ref_stats) // len(ref_stats)
    mean_scalar = sum(x["scalar_bit_operations"] for x in ref_stats) // len(ref_stats)
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and ref_successes == 8 and compact_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "exact GF(2) Gaussian elimination on the displayed dense equations",
            "complexity": "O(R*n^2) scalar bit operations for R equations",
            "wall_clock_sec_mean": mean_seconds,
            "wall_clock_sec_max": max(x["elapsed_sec"] for x in ref_stats),
            "row_xors_mean": mean_row_xors,
            "row_xors_max": max(x["row_xors"] for x in ref_stats),
            "scalar_bit_operations_mean": mean_scalar,
            "scalar_bit_operations_max": max(x["scalar_bit_operations"] for x in ref_stats),
            "successes": ref_successes,
            "attempts": 8,
            "solves": f"{ref_successes}/8, as expected for Track B",
        },
        "compact_route": {
            "name": "frequency-two cycle recovery and step-three XOR recurrence",
            "successes": compact_successes,
            "attempts": 8,
            "xor_operations_max": max(x["xor_operations"] for x in compact_stats),
        },
    }

    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    report["G5_density_and_baseline_cost"] = {
        "pass": probability < 1e-6 and ref_successes == 8,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_estimate": probability,
        "shipping_candidate_space": str(search_space(inst)),
        "shipping_dense_equations": len(inst["equations"]),
        "shipping_compiled_ternary_equations": inst["xor_row_count"],
        "demo_exact_valid_answers": enumerate_all(demo),
        "demo_candidate_space": search_space(demo),
        "baseline_wall_clock_sec_mean": mean_seconds,
        "baseline_row_xors_mean": mean_row_xors,
        "baseline_scalar_bit_operations_mean": mean_scalar,
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    if doubled_params["n"] % 3 == 0:
        doubled_params["n"] += 1
    doubled = make_instance(seed=77, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] > inst["n"]
        and search_space(doubled) > search_space(inst),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "shipping_search_bits": inst["n"],
        "doubled_search_bits": doubled["n"],
        "shipping_matrix_dimension": inst["matrix_dimension"],
        "doubled_matrix_dimension": doubled["matrix_dimension"],
        "doubled_verify_reason": doubled_why,
    }

    crowded_params = dict(shipping_params)
    crowded_params["decoys"] = min(2 * crowded_params["n"],
                                    crowded_params["decoys"] + crowded_params["n"])
    crowded = make_instance(seed=78, **crowded_params)
    crowded_ok, crowded_why = verify(crowded, crowded["answer"])
    report["G7_scales"].update({
        "pass": report["G7_scales"]["pass"] and crowded_ok,
        "fixed_answer_n": crowded["n"],
        "shipping_decoys": inst["decoys"],
        "crowded_decoys": crowded["decoys"],
        "crowded_matrix_dimension": crowded["matrix_dimension"],
        "crowded_verify_reason": crowded_why,
    })

    invariance_checks = 0
    witness_checks = 0
    keys = []
    g8_ok = True
    for seed in range(20):
        base_inst = make_instance(seed=2000 + seed, **shipping_params)
        key = canonical_key(base_inst)
        keys.append(key)
        for variant in range(4):
            transformed = _relabel_instance(
                base_inst, random.Random(9000 + 10 * seed + variant),
                reorder_base=(variant >= 2),
                flip_polarities=(variant % 2 == 1),
            )
            invariance_checks += 1
            witness_checks += 1
            g8_ok &= canonical_key(transformed) == key
            g8_ok &= verify(transformed, transformed["answer"])[0]
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": bool(g8_ok and distinct == 20),
        "invariance_checks": invariance_checks,
        "real_transformation_witness_checks": witness_checks,
        "distinct_unrelated_keys": distinct,
        "unrelated_instances": 20,
        "transformations": [
            "arbitrary base-variable renaming",
            "arbitrary equation reordering",
            "independent base-variable complementation with RHS transport",
            "base-output coordinate reordering, all composed",
        ],
    }

    metrics = [_answer_metrics(make_instance(seed=s, **shipping_params)["answer"])
               for s in range(20)]
    answer_chars = max(x[0] for x in metrics)
    answer_tokens = max(x[1] for x in metrics)
    answer_elements = max(x[2] for x in metrics)
    compact_checks = [
        _compact_recurrence(make_instance(seed=s, **shipping_params))
        for s in range(20)
    ]
    compact_verified = all(verify(make_instance(seed=s, **shipping_params), answer)[0]
                           for s, (answer, _) in enumerate(compact_checks))
    intended_operations = max(stats["xor_operations"]
                              for _, stats in compact_checks)
    arms = {name: dict(G9_ORACLE_RESULTS[name])
            for name in ("bare", "hinted", "placebo")}
    if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]:
        hinted_rate = arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        placebo_rate = arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        hinted_delta = hinted_rate - placebo_rate
    else:
        hinted_delta = None
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and intended_operations <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps and compact_verified,
        "arms": arms,
        "hinted_minus_placebo": hinted_delta,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "intended_route_verified": compact_verified,
        "within_caps": within_caps,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
