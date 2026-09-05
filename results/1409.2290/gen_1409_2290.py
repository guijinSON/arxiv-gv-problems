"""Verified problem generator for arXiv:1409.2290.

The paper's stochastic block model asks for labels correlated with hidden random
types, which is not an exact witness relation on the observed graph.  This module
uses the paper's own spectral object instead: an exactly equitable two-community
graph whose normalized sign vector is an exact adjacency eigenvector.  A balanced
switched cyclic two-lift makes the labels known by construction while burying the
associated eigenvalue inside the spectrum.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import sys
import time


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - the family is standard-library-only
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "two-community graph encoded as an exact cyclic two-lift",
        "target integer adjacency eigenvalue",
    ],
    "verification_operations": [
        "exact graph reconstruction from lift twists",
        "exact integer adjacency matrix-vector multiplication",
        "exact sign and antipodal-pair comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The switching signs cancel around each odd cyclic lift, so a cycle-parity "
        "invariant exposes the sign gauge that defines the two communities."
    ),
    "hardness_basis": (
        "Track B: Section 5.2's adjacency spectral method becomes exact nullspace "
        "elimination at the stated eigenvalue, costing O(n^3); at the hard preset "
        "the reference implementation averages 15,917,420 modular operations and "
        "1.106 seconds in the recorded run, while the supplied cycle checksum "
        "leaves 250 XOR/XNOR operations on the compact route; millions of exact "
        "modular operations are not mechanically executable unaided in context."
    ),
    "max_answer_tokens": 126,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {"n": 5, "negative_offsets": 1},
    "easy": {"n": 151, "negative_offsets": 37},
    "medium": {"n": 239, "negative_offsets": 59},
    "hard": {"n": 251, "negative_offsets": 62},
}
SHIPPING_DIFFICULTY = "hard"

CERTIFICATE_LANGUAGE = {
    "description": (
        "A length-n vector of community bits over {0,1}, one for each base fibre; "
        "the other vertex in each fibre has the opposite bit and c[0]=0 fixes the "
        "global swap.  At the hard preset n=251, the language has 2^250 vectors."
    ),
    "bounds": {
        "length_at_shipping": 251,
        "alphabet": [0, 1],
        "antipodal_fibres": 251,
        "normalization": "c[0] = 0",
    },
}

STRUCTURAL_HINT = (
    "Within any fixed offset row, switching bits cancel around its odd cyclic lift."
)
PLACEBO_HINT = (
    "Within any fixed offset row, careful indexing prevents avoidable sign mistakes."
)

# Filled after the independently preserved harden.py runs.  All three arms are
# diagnostic; G9.pass below is determined only by the answer/effort caps.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 3},
    },
    "hinted_verdict": "hardened",
}

NOTES = """\
Section 5.1 (The stochastic block model) fixes the native task: vertices have
types, p_rs is their edge probability, and the goal is to recover types from the
graph.  It also explains why the literal planted labels are not an exact witness:
the graph does not contain all information about the realized types, and inference
is marginalization rather than maximization.  The k=2 threshold statement says
recovery is information-theoretically impossible below lambda*sqrt(c)=1.

Section 5.2 (Spectral methods) supplies the exact object used here: for two groups,
the second adjacency eigenvector has opposite signs on the communities.  It also
identifies the easy algorithm and its failure regime: ordinary adjacency/Laplacian
spectral methods work in dense graphs but localize on high-degree structures in the
sparse O(1)-degree regime, where the non-backtracking matrix is preferred.  This
generator deliberately stays in the dense regular, algorithmically easy regime and
therefore declares Track B, not Track A.

The cyclic two-lift is an exact equitable specialization built for this benchmark,
not a random draw from the paper's SBM.  It keeps the paper's graph, community-sign,
and adjacency-eigenvector objects; it does not claim to reproduce the probabilistic
detectability experiment.

The graph is a switched cyclic two-lift of K_n.  Roughly half the offset cycles
connect within communities and half connect across them, placing the certified
eigenvalue near zero rather than making it extremal.  Sampling the switching gauge
first gives the certificate without solving.  Prime n makes the stated eigenvalue
simple by cyclotomic linear independence.  Regular degree defeats degree outliers;
balanced offset signs defeat direct-anchor and majority-descent heuristics; random
switching defeats index guesses.  Exact modular nullspace elimination succeeds, as
Track B requires.  The first 151-fibre ladder was still solved by the oracle pool.
Adding the exact parity checksum of one already-displayed offset row reduced the
post-insight route to one XOR/XNOR per output bit, allowing 251 fibres without
breaching G9; all three bare oracles then failed.  The next prime, 257, would exceed
the 256-atom answer cap.
"""


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    d = 3
    while d * d <= n:
        if n % d == 0:
            return False
        d += 2
    return True


def _validate_parameters(n: int, negative_offsets: int) -> None:
    if n < 5 or not _is_prime(n):
        raise ValueError("n must be an odd prime at least 5")
    half = (n - 1) // 2
    if not 1 <= negative_offsets <= half:
        raise ValueError("negative_offsets must lie between 1 and (n-1)/2")


def _candidate_from_switches(switches: list[int]) -> list[int]:
    out = [int(bit) & 1 for bit in switches]
    if out and out[0]:
        out = [bit ^ 1 for bit in out]
    return out


def _expanded_vector(answer: list[int]) -> list[int]:
    out = []
    for bit in answer:
        sign = 1 if bit == 0 else -1
        out.extend((sign, -sign))
    return out


def make_instance(n, seed=0, **params) -> dict:
    """Construct a certified equitable two-community graph by inverse generation.

    ``n`` is the odd number of vertex fibres; the graph has 2n vertices.  The
    switching gauge (and hence the answer) is sampled first.  Offset signs and
    lift twists are then assembled around it, so no recovery algorithm is run.
    """
    n = int(n)
    t = int(params.get("negative_offsets", max(1, (n - 1) // 4)))
    _validate_parameters(n, t)
    rng = random.Random(seed)
    half = (n - 1) // 2
    negative = set(rng.sample(range(1, half + 1), t))

    # A global flip is the same partition, so fix the first gauge bit to zero.
    switches = [0] + [rng.randrange(2) for _ in range(n - 1)]
    tables = []
    for g in range(1, half + 1):
        template_twist = int(g in negative)
        bits = [
            template_twist ^ switches[i] ^ switches[(i + g) % n]
            for i in range(n)
        ]
        tables.append({"offset": g, "twists": "".join(map(str, bits))})

    return {
        "paper": "1409.2290",
        "n": n,
        "vertex_count": 2 * n,
        "degree": n - 1,
        "negative_offsets": t,
        "eigenvalue": n - 1 - 4 * t,
        "twist_tables": tables,
        # This redundant exact checksum lets the compact route spend its budget
        # on recovering the answer rather than recomputing a displayed row parity.
        "calibration_offset": 1,
        "calibration_parity": sum(map(int, tables[0]["twists"])) & 1,
        "answer": _candidate_from_switches(switches),
    }


def _tables_by_offset(inst) -> dict[int, str]:
    return {int(row["offset"]): row["twists"] for row in inst["twist_tables"]}


def _row_parity(rows, offset: int) -> int:
    bits = next(row["twists"] for row in rows if int(row["offset"]) == offset)
    return sum(map(int, bits)) & 1


def _twist_between(inst, i: int, j: int) -> int:
    """Twist on the undirected base edge {i,j}, queried in either direction."""
    n = inst["n"]
    half = (n - 1) // 2
    rows = _tables_by_offset(inst)
    d = (j - i) % n
    if not 1 <= d < n:
        raise ValueError("base vertices must be distinct")
    if d <= half:
        return int(rows[d][i])
    g = n - d
    return int(rows[g][j])


def _adjacency_masks(inst) -> list[int]:
    n = inst["n"]
    total = 2 * n
    masks = [0] * total
    for row in inst["twist_tables"]:
        g = int(row["offset"])
        bits = row["twists"]
        if len(bits) != n or any(ch not in "01" for ch in bits):
            raise ValueError("malformed twist table")
        for i, ch in enumerate(bits):
            j = (i + g) % n
            twist = int(ch)
            for b in (0, 1):
                u = 2 * i + b
                v = 2 * j + (b ^ twist)
                masks[u] |= 1 << v
                masks[v] |= 1 << u
    return masks


def _adjacency_lists(inst) -> list[list[int]]:
    rows = []
    for mask in _adjacency_masks(inst):
        nbrs = []
        while mask:
            low = mask & -mask
            nbrs.append(low.bit_length() - 1)
            mask ^= low
        rows.append(nbrs)
    return rows


def render(inst) -> str:
    n = inst["n"]
    lines = [
        "Exact two-community certificate in a cyclic two-lift",
        "",
        f"There are {2*n} vertices (i,b), where i is modulo n={n} and b is 0 or 1.",
        "The output order is (0,0),(0,1),(1,0),(1,1), and so on.",
        "The graph is specified by the twist rows below.  In a row g: t_0...t_{n-1},",
        "bit t_i creates the two undirected edges",
        "  {(i,0),((i+g) mod n,t_i)} and {(i,1),((i+g) mod n,1 XOR t_i)}.",
        "All listed offsets together cover every base pair exactly once; there are no other edges.",
        f"The graph is regular of degree {inst['degree']}.",
        (f"Calibration datum: the XOR of all bits in offset row "
         f"{inst['calibration_offset']} is {inst['calibration_parity']}."),
        "",
        "Find one community bit c_i in {0,1} for each fibre i, with c_0=0 to fix",
        "the global community swap.  These bits define a sign vector on all vertices by",
        "  x_(i,b) = +1 when c_i XOR b = 0, and -1 otherwise.",
        "The required condition is that for every vertex u,",
        f"  sum_{{v adjacent to u}} x_v = {inst['eigenvalue']} x_u.",
        "Thus the two vertices in each fibre lie in opposite communities.  Equality and",
        "all sums are exact over the integers; order matters and repeated bits are allowed.",
        "",
        "Twist rows (the left integer is g and the bitstring is t_0 through t_{n-1}):",
    ]
    for row in inst["twist_tables"]:
        lines.append(f"  {row['offset']}: {row['twists']}")
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags as one JSON array of",
        f"exactly {n} bits c_0 through c_{n-1} in fibre order.",
        "Example format: <answer>[0,1,1,0]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(("", "Hint: " + STRUCTURAL_HINT))
    elif mode == "placebo":
        lines.extend(("", "Hint: " + PLACEBO_HINT))
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    match = re.search(r"<answer\s*>(.*?)</answer\s*>", text,
                      flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    payload = match.group(1).strip()
    payload = re.sub(r"^```(?:json|text)?\s*|\s*```$", "", payload,
                     flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        value = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, list) else None


def _is_exact_witness(inst, answer) -> bool:
    if not isinstance(answer, list) or len(answer) != inst["n"]:
        return False
    if any(type(x) is not int or x not in (0, 1) for x in answer):
        return False
    if answer[0] != 0:
        return False
    vector = _expanded_vector(answer)
    lam = inst["eigenvalue"]
    try:
        adjacency = _adjacency_lists(inst)
    except (KeyError, TypeError, ValueError):
        return False
    return all(sum(vector[v] for v in nbrs) == lam * vector[u]
               for u, nbrs in enumerate(adjacency))


def verify(inst, answer):
    """Check the candidate from graph data only; never consult inst['answer']."""
    if answer is None:
        return False, "no answer was parsed"
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    expected = inst["n"]
    if not answer:
        return False, "answer is empty"
    if len(answer) == expected - 1:
        return False, "answer dropped one vertex entry"
    if len(answer) == expected + 1:
        return False, "answer contains a duplicate or extra entry"
    if len(answer) != expected:
        return False, f"answer length must be exactly {expected}"
    if any(type(x) is not int or x not in (0, 1) for x in answer):
        return False, "every entry must be the integer bit 0 or 1"
    if answer[0] != 0:
        return False, "global community swap is not normalized: c_0 must be 0"
    try:
        adjacency = _adjacency_lists(inst)
    except (KeyError, TypeError, ValueError) as exc:
        return False, f"instance graph is malformed: {exc}"
    lam = inst["eigenvalue"]
    vector = _expanded_vector(answer)
    for u, nbrs in enumerate(adjacency):
        if sum(vector[v] for v in nbrs) != lam * vector[u]:
            return False, f"adjacency eigenvector equation fails at vertex {u}"
    return True, "ok"


def random_candidate(inst, rng):
    mask = rng.getrandbits(inst["n"] - 1)
    switches = [0] + [(mask >> i) & 1 for i in range(inst["n"] - 1)]
    return _candidate_from_switches(switches)


def search_space(inst):
    return 1 << (inst["n"] - 1)


def enumerate_all(inst):
    n = inst["n"]
    space = 1 << (n - 1)
    if space > 1_000_000:
        return None
    count = 0
    for mask in range(space):
        switches = [0] + [(mask >> (i - 1)) & 1 for i in range(1, n)]
        count += int(_is_exact_witness(inst, _candidate_from_switches(switches)))
    return count


def canonical_key(inst):
    """A graph-isomorphism invariant, never a seed or rendered-text hash.

    Full graph canonization is not attempted.  The multiset of degrees and the
    multiset of common-neighbor counts for every vertex pair are invariant under
    arbitrary vertex renumbering and distinguish all audited shipping seeds.
    """
    masks = _adjacency_masks(inst)
    degrees = sorted(mask.bit_count() for mask in masks)
    common = sorted(
        (masks[i] & masks[j]).bit_count()
        for i in range(len(masks)) for j in range(i + 1, len(masks))
    )
    # The target eigenvalue is part of the problem, not merely an annotation on
    # the graph.  Include it so that the same graph paired with a different target
    # cannot be over-collapsed to the same key.
    structural = [len(masks), int(inst["eigenvalue"]), degrees, common]
    blob = json.dumps(structural, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def escalate(params):
    current = {k: v for k, v in params.items() if not k.startswith("_")}
    n = int(current.get("n", 239))
    # The shipping instance already has the most confusing offset balance:
    # moving t away from half the offsets creates a majority signal and makes
    # local search easier.  A supplied parity checksum makes the compact route
    # cost n-1 XOR/XNOR operations.  Prime 251 is the last available rung under
    # the 256-atom answer cap; the next odd prime has 257 answer atoms.
    if n < 251:
        current["n"] = 251
        current["negative_offsets"] = 62
        return current
    return "cap_bound"


def _compact_certificate(inst):
    """Recover by the intended odd-cycle invariant, without planted data."""
    n = inst["n"]
    offset = int(inst["calibration_offset"])
    row = _tables_by_offset(inst)[offset]
    template_twist = int(inst["calibration_parity"])
    operations = 0
    switches = [0] * n
    current = 0
    for _ in range(n - 1):
        bit = int(row[current])
        # With the row parity known, this is one XOR when the template bit is
        # zero and one XNOR when it is one, not two separate Boolean operations.
        nxt = (current + offset) % n
        switches[nxt] = (switches[current] ^ bit if template_twist == 0
                         else int(switches[current] == bit))
        current = nxt
        operations += 1
    return _candidate_from_switches(switches), operations


def _signed_fibre_matrix(inst):
    """The exact signed n-by-n matrix induced on antipodal vectors."""
    n = inst["n"]
    matrix = [[0] * n for _ in range(n)]
    for row in inst["twist_tables"]:
        g = int(row["offset"])
        for i, ch in enumerate(row["twists"]):
            j = (i + g) % n
            value = -1 if ch == "1" else 1
            matrix[i][j] = value
            matrix[j][i] = value
    return matrix


def _modular_nullvector(matrix, modulus):
    """One vector in a one-dimensional modular kernel, with operation count."""
    rows = [[value % modulus for value in row] for row in matrix]
    n = len(rows)
    pivots = []
    r = 0
    operations = n * n
    for c in range(n):
        pivot = next((i for i in range(r, n) if rows[i][c]), None)
        if pivot is None:
            continue
        rows[r], rows[pivot] = rows[pivot], rows[r]
        inverse = pow(rows[r][c], modulus - 2, modulus)
        operations += 2 * modulus.bit_length()
        for j in range(c, n):
            rows[r][j] = rows[r][j] * inverse % modulus
            operations += 1
        for i in range(n):
            if i == r or rows[i][c] == 0:
                continue
            factor = rows[i][c]
            for j in range(c, n):
                rows[i][j] = (rows[i][j] - factor * rows[r][j]) % modulus
                operations += 2
        pivots.append(c)
        r += 1
        if r == n:
            break
    free = [c for c in range(n) if c not in pivots]
    if len(free) != 1:
        return None, operations
    f = free[0]
    vector = [0] * n
    vector[f] = 1
    for row_index, c in enumerate(pivots):
        vector[c] = (-rows[row_index][f]) % modulus
    if vector[0] == 0:
        return None, operations
    scale = pow(vector[0], modulus - 2, modulus)
    operations += 2 * modulus.bit_length()
    vector = [value * scale % modulus for value in vector]
    operations += n
    return vector, operations


def _reference_algorithm(inst):
    """Exact eigenspace recovery by modular Gaussian elimination."""
    start_time = time.perf_counter()
    signed = _signed_fibre_matrix(inst)
    lam = int(inst["eigenvalue"])
    shifted = [
        [signed[i][j] - (lam if i == j else 0) for j in range(inst["n"])]
        for i in range(inst["n"])
    ]
    operations = inst["n"]
    for modulus in (1_000_003, 1_000_033, 1_000_037):
        vector, used = _modular_nullvector(shifted, modulus)
        operations += used
        if vector is None:
            continue
        if any(value not in (1, modulus - 1) for value in vector):
            continue
        candidate = [0 if value == 1 else 1 for value in vector]
        if _is_exact_witness(inst, candidate):
            return candidate, time.perf_counter() - start_time, operations
    return None, time.perf_counter() - start_time, operations


def _attack_candidates(inst, rng):
    n = inst["n"]
    degree = inst["degree"]

    # Per-fibre twist count: an outlier statistic analogous to degree sorting.
    twist_degrees = []
    for i in range(n):
        twist_degrees.append(sum(_twist_between(inst, i, j)
                                 for j in range(n) if j != i))
    outlier_bits = [int(v > degree / 2) for v in twist_degrees]
    anchor = outlier_bits[0]
    outlier_bits = [b ^ anchor for b in outlier_bits]

    # Greedy assumes every direct edge from fibre 0 is within-community.  Every
    # generated instance has at least one negative offset, so this makes errors.
    greedy_bits = [0] + [_twist_between(inst, 0, i) for i in range(1, n)]

    alternating_bits = [i & 1 for i in range(n)]

    # A genuine random-restart heuristic: coordinate-ascent on the signed
    # Rayleigh quotient.  It seeks an extremal eigenvector, while the balanced
    # construction deliberately puts the requested eigenvalue near zero.
    signed = _signed_fibre_matrix(inst)
    majority_tries = []
    for _ in range(64):
        signs = [1] + [rng.choice((-1, 1)) for _ in range(n - 1)]
        for _sweep in range(4):
            order = list(range(1, n))
            rng.shuffle(order)
            for i in order:
                field = sum(signed[i][j] * signs[j] for j in range(n))
                signs[i] = 1 if field >= 0 else -1
        majority_tries.append([0 if sign == 1 else 1 for sign in signs])
    return {
        "outlier_twist_degree": [_candidate_from_switches(outlier_bits)],
        "greedy_direct_anchor": [_candidate_from_switches(greedy_bits)],
        "alternating_index_ansatz": [_candidate_from_switches(alternating_bits)],
        "majority_descent_64_restarts": majority_tries,
    }


def _reorder_tables(inst, rng):
    out = {k: v for k, v in inst.items() if k not in ("twist_tables", "answer")}
    rows = [dict(row) for row in inst["twist_tables"]]
    rng.shuffle(rows)
    out["twist_tables"] = rows
    out["calibration_parity"] = _row_parity(rows, out["calibration_offset"])
    out["answer"] = inst["answer"][:]
    return out


def _fibre_swapped(inst, rng):
    n = inst["n"]
    flips = [rng.randrange(2) for _ in range(n)]
    out = {k: v for k, v in inst.items() if k not in ("twist_tables", "answer")}
    rows = []
    for row in inst["twist_tables"]:
        g = int(row["offset"])
        bits = "".join(str(int(ch) ^ flips[i] ^ flips[(i + g) % n])
                       for i, ch in enumerate(row["twists"]))
        rows.append({"offset": g, "twists": bits})
    carried = [inst["answer"][i] ^ flips[i] for i in range(n)]
    if carried[0]:
        carried = [bit ^ 1 for bit in carried]
    out["twist_tables"] = rows
    out["calibration_parity"] = _row_parity(rows, out["calibration_offset"])
    out["answer"] = carried
    return out


def _base_affine(inst, rng):
    n = inst["n"]
    units = [a for a in range(1, n) if math.gcd(a, n) == 1]
    a = rng.choice(units)
    shift = rng.randrange(n)
    ainv = pow(a, -1, n)
    out = {k: v for k, v in inst.items() if k not in ("twist_tables", "answer")}
    rows = []
    for g in range(1, (n - 1) // 2 + 1):
        bits = []
        for new_i in range(n):
            new_j = (new_i + g) % n
            old_i = (ainv * (new_i - shift)) % n
            old_j = (ainv * (new_j - shift)) % n
            bits.append(str(_twist_between(inst, old_i, old_j)))
        rows.append({"offset": g, "twists": "".join(bits)})
    carried = [0] * n
    for old_i in range(n):
        new_i = (a * old_i + shift) % n
        carried[new_i] = inst["answer"][old_i]
    if carried[0]:
        carried = [bit ^ 1 for bit in carried]
    out["twist_tables"] = rows
    out["calibration_parity"] = _row_parity(rows, out["calibration_offset"])
    out["answer"] = carried
    return out


def _base_permuted(inst, rng):
    """Apply an arbitrary permutation of the n base fibres and carry the witness."""
    n = inst["n"]
    old_to_new = list(range(n))
    rng.shuffle(old_to_new)
    new_to_old = [0] * n
    for old_i, new_i in enumerate(old_to_new):
        new_to_old[new_i] = old_i

    out = {k: v for k, v in inst.items() if k not in ("twist_tables", "answer")}
    rows = []
    for g in range(1, (n - 1) // 2 + 1):
        bits = []
        for new_i in range(n):
            new_j = (new_i + g) % n
            bits.append(str(_twist_between(
                inst, new_to_old[new_i], new_to_old[new_j]
            )))
        rows.append({"offset": g, "twists": "".join(bits)})

    carried = [0] * n
    for old_i, new_i in enumerate(old_to_new):
        carried[new_i] = inst["answer"][old_i]
    if carried[0]:
        carried = [bit ^ 1 for bit in carried]
    out["twist_tables"] = rows
    out["calibration_parity"] = _row_parity(rows, out["calibration_offset"])
    out["answer"] = carried
    return out


def _answer_token_measure(answer):
    blob = json.dumps(answer, separators=(",", ":"))
    return (len(blob) + 3) // 4


def selftest():
    report = {
        "paper": "1409.2290",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    verified = 0
    failures = []
    for name, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            verified += int(ok)
            if not ok:
                failures.append(f"{name}/{seed}: {why}")
    report["G1_planted_verifies"] = {
        "pass": verified == 12,
        "verified": verified,
        "attempts": 12,
        "failures": failures,
    }

    ship = make_instance(seed=3, **DIFFICULTY[SHIPPING_DIFFICULTY])
    ans = ship["answer"]
    swapped = ans[:]
    pair = next((i, j) for i in range(1, len(ans)) for j in range(i + 1, len(ans))
                if ans[i] != ans[j])
    swapped[pair[0]], swapped[pair[1]] = swapped[pair[1]], swapped[pair[0]]
    out_of_range = ans[:]
    out_of_range[2] = 2
    corruptions = {
        "drop": ans[:-1],
        "swap": swapped,
        "duplicate": ans + [ans[-1]],
        "empty": [],
        "out_of_range": out_of_range,
    }
    rejected = {}
    for name, bad in corruptions.items():
        ok, why = verify(ship, bad)
        rejected[name] = {"rejected": not ok, "reason": why}
    distinct_reasons = len({v["reason"] for v in rejected.values()})
    report["G2_rejects_corruption"] = {
        "pass": all(v["rejected"] for v in rejected.values()) and distinct_reasons == 5,
        "cases": rejected,
        "distinct_reasons": distinct_reasons,
    }

    response = (
        "The signs give the normalized eigendirection.\n```json\n"
        "<answer>" + json.dumps(ans) + "</answer>\n```\n"
        "The opposite global sign was excluded by the first coordinate."
    )
    parsed = parse_answer(response)
    json_native = json.loads(json.dumps(ans)) == ans
    report["G3_round_trip"] = {
        "pass": parsed == ans and json_native,
        "parsed_matches": parsed == ans,
        "json_native": json_native,
    }

    density_inst = make_instance(seed=11, **DIFFICULTY[SHIPPING_DIFFICULTY])
    target, _ = _compact_certificate(density_inst)
    density_rng = random.Random(0x14092290)
    samples = 200_000
    hits = 0
    start = time.perf_counter()
    for _ in range(samples):
        hits += int(random_candidate(density_inst, density_rng) == target)
    density_wall = time.perf_counter() - start
    observed = hits / samples
    report["G4_guess_resistance"] = {
        "pass": samples >= 200_000 and observed < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": observed,
        "exact_probability": 1 / search_space(density_inst),
        "exact_language_size": search_space(density_inst),
        "sampling_wall_sec": round(density_wall, 6),
    }

    attempts = 8
    attack_successes = None
    reference_successes = 0
    reference_times = []
    reference_operations = []
    for seed in range(20, 20 + attempts):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        probes = _attack_candidates(inst, random.Random(90_000 + seed))
        if attack_successes is None:
            attack_successes = {name: 0 for name in probes}
        for name, candidates in probes.items():
            if any(verify(inst, candidate)[0] for candidate in candidates):
                attack_successes[name] += 1
        candidate, elapsed, operations = _reference_algorithm(inst)
        ok = candidate is not None and verify(inst, candidate)[0]
        reference_successes += int(ok)
        reference_times.append(elapsed)
        reference_operations.append(operations)
    attacks = {
        name: {"successes": successes, "attempts": attempts}
        for name, successes in attack_successes.items()
    }
    mean_wall = sum(reference_times) / attempts
    mean_ops = sum(reference_operations) // attempts
    report["G6_adversary_panel"] = {
        "pass": all(v["successes"] == 0 for v in attacks.values())
                and reference_successes == attempts,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "exact modular Gaussian nullspace at the stated adjacency eigenvalue",
            "complexity": "O(n^3) modular arithmetic operations",
            "wall_clock_sec": round(mean_wall, 6),
            "operations": mean_ops,
            "solves": f"{reference_successes}/{attempts}, as expected",
        },
    }

    demo_count = enumerate_all(make_instance(seed=0, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline"] = {
        "pass": demo_count is not None and hits == 0 and reference_successes == attempts,
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_density_fraction": observed,
        "shipping_exact_density": 1 / search_space(density_inst),
        "demo_exact_solution_count": demo_count,
        "baseline_wall_clock_sec": round(mean_wall, 6),
        "baseline_iteration_operations": mean_ops,
    }

    doubled_params = dict(DIFFICULTY["hard"])
    doubled_params["n"] = 503
    doubled_params["negative_offsets"] = 125
    doubled = make_instance(seed=101, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["vertex_count"] > 2 * ship["vertex_count"],
        "original_vertices": ship["vertex_count"],
        "scaled_vertices": doubled["vertex_count"],
        "verify_reason": doubled_reason,
    }

    invariant_passed = 0
    transformed_verified = 0
    unrelated_keys = []
    for seed in range(40, 60):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        rng = random.Random(123_000 + seed)
        reordered = _reorder_tables(inst, rng)
        fibres = _fibre_swapped(inst, rng)
        permuted = _base_permuted(inst, rng)
        composed = _reorder_tables(
            _fibre_swapped(_base_permuted(inst, rng), rng), rng
        )
        base_key = canonical_key(inst)
        for changed in (reordered, fibres, permuted, composed):
            invariant_passed += int(canonical_key(changed) == base_key)
        transformed_verified += int(verify(composed, composed["answer"])[0])
        unrelated_keys.append(base_key)
    report["G8_canonical_key"] = {
        "pass": invariant_passed == 80 and transformed_verified == 20
                and len(set(unrelated_keys)) == 20,
        "invariance_checks_passed": invariant_passed,
        "invariance_checks_attempted": 80,
        "transformed_witnesses_verified": transformed_verified,
        "transformed_witnesses_attempted": 20,
        "unrelated_distinct_keys": len(set(unrelated_keys)),
        "unrelated_instances": 20,
        "caveat": (
            "degree/common-neighbor multisets plus the target eigenvalue are a strong "
            "invariant, not full graph canonization"
        ),
    }

    blob = json.dumps(ans, separators=(",", ":"))
    _, intended_operations = _compact_certificate(ship)
    arms = G9_RESULTS["arms"]
    if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]:
        hinted_rate = arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        placebo_rate = arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        hint_effect = hinted_rate - placebo_rate
    else:
        hint_effect = None
    within_caps = (len(blob) <= 2000 and len(ans) <= 256
                   and intended_operations <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hint_effect,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": len(blob),
        "answer_tokens": _answer_token_measure(ans),
        "answer_elements": len(ans),
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [v for k, v in report.items() if k.startswith("G")]
    report["all_passed"] = all(gate.get("pass") for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
