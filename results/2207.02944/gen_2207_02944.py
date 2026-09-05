"""Verified generator for rank-one isomorphisms of Yang--Baxter solutions.

The source is Theorem 4.1 and Theorem 4.7 of arXiv:2207.02944.  A
generating sequence c in an abelian group G defines the indecomposable
level-2 solution S(G x Z_m, c), and two such constructed solutions are
isomorphic exactly when a group isomorphism sends every c_i to c'_i.

This module works natively in G = GF(p)^d.  It inverse-generates a rank-one
linear automorphism g = I + u v^T, applies it to a generating sequence, and
asks for the normalized factors u,v.  The first d sequence vectors form a
second rank-one perturbation of the standard basis.  Generic elimination is
efficient with tools; recognizing both rank-one invariants gives the intended
no-tool compression.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import time


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "generating sequences in the additive group GF(p)^d",
        "indecomposable involutive Yang--Baxter solutions S(G x Z_m, c)",
        "rank-one linear group isomorphism",
    ],
    "verification_operations": [
        "exact finite-field dot product",
        "exact rank-one linear map evaluation",
        "exact Yang--Baxter left-action intertwining comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Recognize both the unknown automorphism and the displayed generating "
        "frame as rank-one perturbations of identity; without that invariant "
        "one executes dense modular Gaussian elimination."
    ),
    "hardness_basis": (
        "Track B: Theorem 4.7 reduces isomorphism to the linear equations "
        "g(c_i)=c'_i; at the declared shipping preset d=16, exact O(d^3) "
        "Gauss--Jordan elimination took 0.010 seconds in the final congested-host "
        "audit, 4,984 field operations and 17 inversions over eight seeds, versus "
        "at most 195 operations for the rank-one route."
    ),
    "max_answer_tokens": 52,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"]
        + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {"n": 2, "p": 7, "extra": 1},
    "easy": {"n": 16, "p": 65_537, "extra": 12},
    "medium": {"n": 20, "p": 1_000_003, "extra": 24},
    "hard": {"n": 24, "p": 2_147_483_647, "extra": 40},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Both the source frame's deviation from the standard basis and the sought "
    "isomorphism's deviation from identity have rank one."
)
PLACEBO_HINT = (
    "Careful modular bookkeeping and consistent coordinate order are important "
    "throughout every stage of the exact comparison."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A structure-aware JSON object {\"u\":[...],\"v\":[...]} with two "
        "length-d vectors over GF(p).  The normalized u is the direction forced "
        "by c'[1]-c[1]; v is sampled uniformly subject to the freely checked "
        "first equation v dot c[1]=s and 1+v dot u != 0.  It denotes g=I+u v^T."
    ),
    "bounds": {
        "vectors": 2,
        "length_each": "d",
        "entry_min": 0,
        "entry_max": "p-1",
        "normalization": "u is fixed by normalizing c'[1]-c[1]",
        "free_linear_constraints": "v dot c[1] equals the forced scalar s",
        "invertibility": "1 + v dot u != 0 mod p",
    },
}

NOTES = (
    "Section 4, Theorem 4.1 fixes the native objects and formula: a generating "
    "sequence c with c_0=0 in an abelian group G defines S(G x Z_m,c).  "
    "Proposition 4.4 identifies the easy abelian-permutation-group case "
    "c_i=i*c_1, which generation explicitly avoids.  Theorem 4.7 is the STEP 0 "
    "discriminator: constructed solutions are isomorphic exactly when a group "
    "isomorphism maps every c_i to c'_i, so Track A would be false because finite "
    "vector-space instances reduce to Gaussian elimination.  The certificate is "
    "sampled first as g=I+uv^T and the target sequence is built by applying it.  "
    "A source frame B=I+ab^T supplies the compact invariant.  Dense uniform field "
    "coordinates remove a coordinate-magnitude outlier; the nonidentity frame "
    "breaks diagonal and identity-frame guesses; conditioning on the visible first "
    "equation leaves d-1 high-entropy coordinates against sparse and restart attacks. "
    "All are measured separately from the successful reference elimination algorithm."
)

# These values are replaced after the three script-owned oracle runs.  G9(a,b)
# are diagnostics; only the exact size/effort caps gate this module.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3, "error_calls": 0},
    "hinted": {"solved": 0, "attempts": 0, "error_calls": 4},
    "placebo": {"solved": 0, "attempts": 0, "error_calls": 4},
    "hinted_verdict": "blocked_by_openrouter_403",
}

_MERSENNE_61 = 2_305_843_009_213_693_951
_MERSENNE_127 = 170_141_183_460_469_231_731_687_303_715_884_105_727
_KNOWN_PRIMES = {
    7,
    65_537,
    1_000_003,
    2_147_483_647,
    _MERSENNE_61,
    _MERSENNE_127,
}


def _dot(a, b, p):
    return sum(x * y for x, y in zip(a, b)) % p


def _vadd(a, b, p):
    return [(x + y) % p for x, y in zip(a, b)]


def _vsub(a, b, p):
    return [(x - y) % p for x, y in zip(a, b)]


def _vscale(s, a, p):
    return [(s * x) % p for x in a]


def _basis(d, j):
    return [1 if i == j else 0 for i in range(d)]


def _first_nonzero(v):
    for i, value in enumerate(v):
        if value:
            return i
    return None


def _normalize_projective(v, p):
    pivot = _first_nonzero(v)
    if pivot is None:
        return None
    inv = pow(v[pivot], -1, p)
    return [(x * inv) % p for x in v]


def _proportional(a, b, p):
    """Whether two nonzero vectors span the same one-dimensional subspace."""
    pivot = _first_nonzero(a)
    if pivot is None or _first_nonzero(b) is None:
        return False
    scale = b[pivot] * pow(a[pivot], -1, p) % p
    return all((scale * x - y) % p == 0 for x, y in zip(a, b))


def _rank_one_apply(u, v, x, p):
    scalar = _dot(v, x, p)
    return [(x_i + u_i * scalar) % p for x_i, u_i in zip(x, u)]


def _mat_vec(matrix, vector, p):
    return [_dot(row, vector, p) for row in matrix]


def _mat_mul(left, right, p):
    if not left or not right:
        return []
    cols = list(zip(*right))
    return [[_dot(row, col, p) for col in cols] for row in left]


def _identity(n):
    return [[1 if i == j else 0 for j in range(n)] for i in range(n)]


def _transpose(matrix):
    return [list(row) for row in zip(*matrix)]


def _is_prime_64(value):
    """Deterministic Miller--Rabin for unsigned 64-bit integers."""
    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small:
        if value % prime == 0:
            return value == prime
    d = value - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if base % value == 0:
            continue
        x = pow(base, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(s - 1):
            x = x * x % value
            if x == value - 1:
                break
        else:
            return False
    return True


def _gaussian_solve_counted(matrix, rhs, p):
    """Gauss--Jordan solve over GF(p), returning solution and cost counters."""
    n = len(matrix)
    if n == 0 or any(len(row) != n for row in matrix) or len(rhs) != n:
        raise ValueError("expected a square linear system")
    aug = [[value % p for value in row] + [rhs[i] % p]
           for i, row in enumerate(matrix)]
    operations = 0
    inversions = 0
    for col in range(n):
        pivot = next((r for r in range(col, n) if aug[r][col] % p), None)
        if pivot is None:
            raise ValueError("singular matrix")
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]
        inv = pow(aug[col][col], -1, p)
        inversions += 1
        for j in range(col, n + 1):
            aug[col][j] = aug[col][j] * inv % p
            operations += 1
        for row in range(n):
            if row == col or aug[row][col] == 0:
                continue
            factor = aug[row][col]
            for j in range(col, n + 1):
                aug[row][j] = (aug[row][j] - factor * aug[col][j]) % p
                operations += 2
    return [aug[i][n] for i in range(n)], operations, inversions


def _solve(matrix, rhs, p):
    return _gaussian_solve_counted(matrix, rhs, p)[0]


def _columns_to_rows(columns):
    return [list(row) for row in zip(*columns)]


def _matrix_inverse(matrix, p):
    n = len(matrix)
    if n == 0 or any(len(row) != n for row in matrix):
        raise ValueError("expected a square matrix")
    aug = [
        [value % p for value in row] + _basis(n, i)
        for i, row in enumerate(matrix)
    ]
    for col in range(n):
        pivot = next((r for r in range(col, n) if aug[r][col]), None)
        if pivot is None:
            raise ValueError("singular matrix")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        inv = pow(aug[col][col], -1, p)
        aug[col] = [value * inv % p for value in aug[col]]
        for row in range(n):
            if row == col or aug[row][col] == 0:
                continue
            factor = aug[row][col]
            aug[row] = [
                (x - factor * y) % p
                for x, y in zip(aug[row], aug[col])
            ]
    return [row[n:] for row in aug]


def _rank(matrix, p):
    if not matrix:
        return 0
    a = [[x % p for x in row] for row in matrix]
    rows, cols = len(a), len(a[0])
    rank = 0
    for col in range(cols):
        pivot = next((r for r in range(rank, rows) if a[r][col]), None)
        if pivot is None:
            continue
        a[rank], a[pivot] = a[pivot], a[rank]
        inv = pow(a[rank][col], -1, p)
        a[rank] = [x * inv % p for x in a[rank]]
        for r in range(rows):
            if r != rank and a[r][col]:
                factor = a[r][col]
                a[r] = [(x - factor * y) % p
                        for x, y in zip(a[r], a[rank])]
        rank += 1
        if rank == rows:
            break
    return rank


def _random_projective_vector(d, p, rng, force_first=False):
    if force_first:
        return [1] + [rng.randrange(p) for _ in range(d - 1)]
    # A normalized projective vector with pivot k has p^(d-k-1) possible
    # tails.  Sampling from these weighted blocks is exactly uniform over
    # projective points and avoids a modular inverse for every G4 draw.
    ticket = rng.randrange((p ** d - 1) // (p - 1))
    for pivot in range(d):
        block = p ** (d - pivot - 1)
        if ticket < block:
            tail = [0] * (d - pivot - 1)
            value = ticket
            for j in range(len(tail) - 1, -1, -1):
                value, tail[j] = divmod(value, p)
            return [0] * pivot + [1] + tail
        ticket -= block
    raise AssertionError("projective sampler exhausted its exact range")


def _sample_valid_v(
    u, p, rng, *, avoid_normalized=False, avoid_last_equal=False
):
    d = len(u)
    population = p ** d
    while True:
        ticket = rng.randrange(population)
        v = [0] * d
        for i in range(d - 1, -1, -1):
            ticket, v[i] = divmod(ticket, p)
        if not any(v) or (1 + _dot(v, u, p)) % p == 0:
            continue
        if avoid_normalized:
            pivot = _first_nonzero(v)
            if pivot is not None and v[pivot] == 1:
                continue
        if avoid_last_equal and d > 1 and v[-1] == v[-2]:
            continue
        return v


def _is_arithmetic_sequence(sequence, p):
    if not sequence:
        return False
    first = sequence[1] if len(sequence) > 1 else sequence[0]
    return all(vector == _vscale(i, first, p)
               for i, vector in enumerate(sequence))


def make_instance(n, seed=0, **params):
    """Inverse-generate an isomorphism and build both solutions around it."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    p = params.pop("p", 2_147_483_647)
    extra = params.pop("extra", max(1, n // 2))
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(p, bool) or not isinstance(p, int) or p not in _KNOWN_PRIMES:
        raise ValueError("p must be one of the module's audited prime moduli")
    if isinstance(extra, bool) or not isinstance(extra, int) or extra < 0:
        raise ValueError("extra must be a nonnegative integer")

    d = n
    rng = random.Random(seed)

    # The answer is sampled first.  Projective normalization makes the
    # rank-one factorization unique without narrowing v to a biased subset.
    u = _random_projective_vector(d, p, rng, force_first=True)
    v = _sample_valid_v(
        u, p, rng, avoid_normalized=True, avoid_last_equal=True
    )

    # Build a known invertible source frame B=I+a b^T.  Rejection here merely
    # enforces construction-side promises; it never searches for the answer.
    while True:
        a = _random_projective_vector(d, p, rng, force_first=True)
        b = [1] + [rng.randrange(1, p) for _ in range(d - 1)]
        denominator = (1 + _dot(a, b, p)) % p
        if denominator == 0:
            continue
        if any((1 + a[i] * b[i]) % p == 0 for i in range(d)):
            continue
        first_column = _vadd(_basis(d, 0), a, p)
        if _dot(v, first_column, p) == 0:
            continue
        # Keep the first mapping equation and the determinant constraint
        # independent.  This makes the structure-aware candidate language have
        # the same exact size for every generated instance.
        if _proportional(u, first_column, p):
            continue
        if _dot(a, v, p) == 0:
            continue
        break

    columns = [
        _vadd(_basis(d, j), _vscale(b[j], a, p), p)
        for j in range(d)
    ]
    sequence = [[0] * d] + columns
    for _ in range(extra):
        coefficients = [rng.randrange(p) for _ in range(d)]
        # B*w = w + a*(b dot w), composed from the known rank-one frame.
        sequence.append(_vadd(
            coefficients,
            _vscale(_dot(b, coefficients, p), a, p),
            p,
        ))

    target = [_rank_one_apply(u, v, vector, p) for vector in sequence]
    if _is_arithmetic_sequence(sequence, p):
        # With a rank-d frame and d>=2 this should be unreachable; keep the
        # contract explicit in case parameters are changed later.
        raise RuntimeError("construction unexpectedly entered the abelian easy case")

    return {
        "family": "rank-one isomorphism of level-2 Yang--Baxter solutions",
        "d": d,
        "p": p,
        "cycle_length": len(sequence),
        "source_sequence": sequence,
        "target_sequence": target,
        "answer": {"u": u, "v": v},
    }


def _format_sequence(name, sequence):
    lines = [f"{name} (indices 0 through {len(sequence) - 1}):"]
    lines.extend(f"  {i}: " + " ".join(map(str, vector))
                 for i, vector in enumerate(sequence))
    return "\n".join(lines)


def _solution_r(sequence, p, x, y):
    """Evaluate the paper's r map exactly on two encoded elements of X."""
    m = len(sequence)
    a, i = x
    b, j = y
    sigma = (
        tuple(_vadd(
            b,
            _vsub(sequence[(i - j - 1) % m], sequence[(-j - 1) % m], p),
            p,
        )),
        (j + 1) % m,
    )
    tau = (
        tuple(_vsub(
            a,
            _vsub(sequence[(j - i + 1) % m], sequence[(-i) % m], p),
            p,
        )),
        (i - 1) % m,
    )
    return sigma, tau


def _r12(sequence, p, triple):
    first, second = _solution_r(sequence, p, triple[0], triple[1])
    return first, second, triple[2]


def _r23(sequence, p, triple):
    second, third = _solution_r(sequence, p, triple[1], triple[2])
    return triple[0], second, third


def render(inst):
    d = inst["d"]
    p = inst["p"]
    m = inst["cycle_length"]
    statement = f"""Recover an isomorphism between two constructed Yang--Baxter solutions.

All vector coordinates and all additions, subtractions, products, and dot
products below are in the prime field GF(p), where p={p}.  V=GF(p)^{d} uses
the displayed coordinate order.  Sequence indices are residues modulo m={m};
for example c[-1] means c[m-1].

For any sequence c[0],...,c[m-1] in V with c[0]=0 that spans V, define maps
on X=V x Z_m by

  sigma_(a,i)(b,j) = (b + c[i-j-1] - c[-j-1], j+1),
  tau_(a,i)(b,j)   = (b - c[i-j+1] + c[-j], j-1),

where the second coordinate and every sequence subscript are modulo m.  With
the convention r(x,y)=(sigma_x(y),tau_y(x)), these maps define an involutive,
nondegenerate,
indecomposable set-theoretic solution of the Yang--Baxter equation of
multipermutation level 2; that equation is the braid identity
(id x r)(r x id)(id x r)=(r x id)(id x r)(r x id).  The two displayed
sequences c and c' each span V and therefore define two such solutions.

A linear map g:V->V that sends every c[i] to c'[i] gives the solution
isomorphism Phi(a,i)=(g(a),i), meaning
Phi(sigma_x(y))=sigma'_Phi(x)(Phi(y)) for every x,y.  It is promised that the
required map has the rank-one form

  g(x) = x + u * (v dot x).

Find u and v.  They are made unique by requiring u to be nonzero and its first
nonzero coordinate (scanning from coordinate 1 to coordinate {d}) to equal 1.
Also v must be nonzero and 1+v dot u must be nonzero, which makes g invertible.
All answer entries are ordinary decimal integers in the inclusive range
0,...,p-1.  Coordinates and sequence indices in this statement are 1-indexed
and 0-indexed respectively.  Coordinate order matters, repeated field values
are allowed, and each vector must contain exactly {d} entries.

{_format_sequence('Source sequence c', inst['source_sequence'])}

{_format_sequence("Target sequence c'", inst['target_sequence'])}

Return exactly one JSON object with keys \"u\" and \"v\"; each value must be a
JSON list of exactly {d} decimal integers in coordinate order.

Give your final answer inside <answer></answer> tags, as the JSON object just specified.
Example: <answer>{json.dumps({"u": [1] + [0] * (d - 1), "v": [2, 3] + [0] * (d - 2)}, separators=(",", ":"))}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Parse a tagged JSON certificate while tolerating surrounding prose."""
    if not isinstance(text, str):
        return None
    tagged = re.findall(r"<answer\s*>(.*?)</answer\s*>", text,
                        flags=re.IGNORECASE | re.DOTALL)
    candidates = tagged if tagged else [text]
    decoder = json.JSONDecoder()
    for candidate in candidates:
        cleaned = re.sub(r"```(?:json)?", "", candidate, flags=re.IGNORECASE)
        for match in re.finditer(r"\{", cleaned):
            try:
                value, _ = decoder.raw_decode(cleaned[match.start():])
            except (ValueError, TypeError):
                continue
            if isinstance(value, dict):
                return value
    return None


def _validate_vector(name, vector, d, p):
    if not isinstance(vector, list):
        return f"{name} must be a JSON list"
    if len(vector) != d:
        return f"{name} must have exactly {d} entries"
    for index, value in enumerate(vector):
        if isinstance(value, bool) or not isinstance(value, int):
            return f"{name}[{index + 1}] must be an integer"
        if not 0 <= value < p:
            return f"{name}[{index + 1}] is outside 0 <= entry < p"
    return None


def verify(inst, answer):
    """Check any normalized rank-one isomorphism; never inspect inst['answer']."""
    if not isinstance(answer, dict) or set(answer) != {"u", "v"}:
        return False, "answer must be an object with exactly the keys u and v"
    d, p = inst["d"], inst["p"]
    u, v = answer["u"], answer["v"]
    problem = _validate_vector("u", u, d, p)
    if problem:
        return False, problem
    problem = _validate_vector("v", v, d, p)
    if problem:
        return False, problem
    pivot = _first_nonzero(u)
    if pivot is None:
        return False, "u must be nonzero"
    if u[pivot] != 1:
        return False, "u is not projectively normalized"
    if not any(v):
        return False, "v must be nonzero"
    if (1 + _dot(v, u, p)) % p == 0:
        return False, "I + u v^T is singular"

    source = inst.get("source_sequence")
    target = inst.get("target_sequence")
    m = inst.get("cycle_length")
    if (not isinstance(source, list) or not isinstance(target, list)
            or len(source) != m or len(target) != m):
        return False, "instance sequences are malformed"
    if source[0] != [0] * d or target[0] != [0] * d:
        return False, "instance sequences must start at the zero vector"
    for i, (left, right) in enumerate(zip(source, target)):
        if _rank_one_apply(u, v, left, p) != right:
            return False, f"g(c[{i}]) does not equal c'[{i}]"

    # Rank is an instance-consistency check.  Put it after the witness equations
    # so a random wrong certificate is rejected after one vector comparison
    # rather than paying for elimination; valid witnesses still execute it.
    if _rank(source[1:], p) != d or _rank(target[1:], p) != d:
        return False, "instance sequences do not span V"
    if _is_arithmetic_sequence(source, p) or _is_arithmetic_sequence(target, p):
        return False, "instance entered the abelian permutation-group easy case"

    # Execute the left-action intertwining identity on every pair of residue
    # classes.  The free b-coordinate cancels, so this finite symbolic check is
    # exactly Phi sigma = sigma' Phi without enumerating p^d elements.
    for i in range(m):
        for j in range(m):
            shift = _vsub(source[(i - j - 1) % m], source[(-j - 1) % m], p)
            target_shift = _vsub(
                target[(i - j - 1) % m], target[(-j - 1) % m], p
            )
            if _rank_one_apply(u, v, shift, p) != target_shift:
                return False, f"left-action intertwining fails at indices ({i},{j})"
    return True, "ok"


def _forced_mapping_data(inst):
    """The normalized image direction and scalar forced by index 1."""
    p = inst["p"]
    delta = _vsub(inst["target_sequence"][1], inst["source_sequence"][1], p)
    u = _normalize_projective(delta, p)
    if u is None:
        raise ValueError("the first source-target displacement must be nonzero")
    pivot = _first_nonzero(u)
    return u, delta[pivot]


def _condition_on_first_equation(inst, proposal):
    """Project a proposed v onto its obvious affine constraint, preserving shape."""
    d, p = inst["d"], inst["p"]
    u, scalar = _forced_mapping_data(inst)
    source = inst["source_sequence"][1]
    pivot = _first_nonzero(source)
    if pivot is None:
        raise ValueError("c[1] must be nonzero")
    v = [(proposal[i] if i < len(proposal) else 0) % p for i in range(d)]

    def solve_pivot():
        remainder = sum(source[i] * v[i] for i in range(d) if i != pivot) % p
        v[pivot] = (scalar - remainder) * pow(source[pivot], -1, p) % p

    solve_pivot()
    if (1 + _dot(v, u, p)) % p == 0:
        # Because source and u are not proportional, an affine null direction
        # exists that changes u dot v.  Move one free coordinate by one and
        # re-solve the pivot; the formerly zero determinant becomes nonzero.
        for free in range(d):
            if free == pivot:
                continue
            change = (u[free]
                      - u[pivot] * source[free]
                      * pow(source[pivot], -1, p)) % p
            if change:
                v[free] = (v[free] + 1) % p
                solve_pivot()
                break
        else:
            raise ValueError("first equation is dependent on determinant constraint")
    return {"u": u, "v": v}


def random_candidate(inst, rng):
    """Uniformly sample after enforcing the obvious first mapping equation."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    d, p = inst["d"], inst["p"]
    source = inst["source_sequence"][1]
    pivot = _first_nonzero(source)
    if pivot is None:
        raise ValueError("c[1] must be nonzero")
    while True:
        proposal = [rng.randrange(p) if i != pivot else 0 for i in range(d)]
        # Reject a singular draw rather than repairing it, which keeps sampling
        # uniform on the allowed part of the affine hyperplane.
        v = list(proposal)
        u, scalar = _forced_mapping_data(inst)
        remainder = sum(source[i] * v[i] for i in range(d) if i != pivot) % p
        v[pivot] = (scalar - remainder) * pow(source[pivot], -1, p) % p
        if (1 + _dot(v, u, p)) % p:
            return {"u": u, "v": v}


def search_space(inst):
    d, p = inst["d"], inst["p"]
    u, _ = _forced_mapping_data(inst)
    source = inst["source_sequence"][1]
    if _proportional(u, source, p):
        # Generated instances exclude this branch, but retain an exact answer
        # for a valid externally supplied instance.  Invertibility of the held
        # answer implies every point of the affine hyperplane is invertible.
        return p ** (d - 1)
    return (p - 1) * p ** (d - 2)


def enumerate_all(inst):
    """Brute-force the bounded language only when it is genuinely small."""
    if search_space(inst) > 100_000:
        return None
    d, p = inst["d"], inst["p"]
    source = inst["source_sequence"][1]
    pivot = _first_nonzero(source)
    u, scalar = _forced_mapping_data(inst)
    free = [i for i in range(d) if i != pivot]
    count = 0
    for values in itertools.product(range(p), repeat=d - 1):
        v = [0] * d
        for index, value in zip(free, values):
            v[index] = value
        remainder = sum(source[i] * v[i] for i in free) % p
        v[pivot] = (scalar - remainder) * pow(source[pivot], -1, p) % p
        if (1 + _dot(v, u, p)) % p == 0:
            continue
        if verify(inst, {"u": u, "v": v})[0]:
            count += 1
    return count


def _reference_solve(inst):
    """Recover the map using generic exact Gaussian elimination."""
    d, p = inst["d"], inst["p"]
    source, target = inst["source_sequence"], inst["target_sequence"]
    differences = [_vsub(target[i], source[i], p) for i in range(1, d + 1)]
    first = next(vector for vector in differences if any(vector))
    u = _normalize_projective(first, p)
    pivot = _first_nonzero(u)
    scalars = [vector[pivot] for vector in differences]
    matrix = [list(source[i]) for i in range(1, d + 1)]
    v, operations, inversions = _gaussian_solve_counted(matrix, scalars, p)
    return {"u": u, "v": v}, operations + d * d + d, inversions + 1


def _compact_solve(inst):
    """The intended double-rank-one route, used only to audit its claim."""
    d, p = inst["d"], inst["p"]
    source, target = inst["source_sequence"], inst["target_sequence"]

    first_difference = _vsub(target[1], source[1], p)
    u = _normalize_projective(first_difference, p)
    if u is None:
        raise ValueError("compact frame promise was not met")
    pivot_u = _first_nonzero(u)
    scalars = [
        (target[i][pivot_u] - source[i][pivot_u]) % p
        for i in range(1, d + 1)
    ]

    # The first frame deviation is nonzero by construction.  Once it is
    # normalized to a, each scalar b_i is read from a single pivot coordinate
    # of c[i+1]-e_i; expanding all d full deviation vectors would turn this
    # compact route into an unnecessary quadratic calculation.
    first_dev = _vsub(source[1], _basis(d, 0), p)
    a = _normalize_projective(first_dev, p)
    if a is None:
        raise ValueError("compact source-frame promise was not met")
    pivot_a = _first_nonzero(a)
    b = [
        (source[i + 1][pivot_a] - (1 if i == pivot_a else 0)) % p
        for i in range(d)
    ]
    denominator = (1 + _dot(a, b, p)) % p
    correction = _dot(a, scalars, p) * pow(denominator, -1, p) % p
    v = [(s - b_i * correction) % p for s, b_i in zip(scalars, b)]
    return {"u": u, "v": v}


def _attack_outlier_coordinate(inst):
    d, p = inst["d"], inst["p"]
    source = inst["source_sequence"]
    scores = [sum(vector[j] for vector in source) for j in range(d)]
    high = max(range(d), key=lambda j: (scores[j], -j))
    v = [0] * d
    v[high] = 1
    return _condition_on_first_equation(inst, v)


def _mapping_factor_data(inst):
    d, p = inst["d"], inst["p"]
    source, target = inst["source_sequence"], inst["target_sequence"]
    differences = [_vsub(target[i], source[i], p) for i in range(1, d + 1)]
    first = next(vector for vector in differences if any(vector))
    u = _normalize_projective(first, p)
    pivot = _first_nonzero(u)
    scalars = [vector[pivot] for vector in differences]
    return u, scalars


def _attack_diagonal_greedy(inst):
    d, p = inst["d"], inst["p"]
    u, scalars = _mapping_factor_data(inst)
    v = []
    for i in range(d):
        diagonal = inst["source_sequence"][i + 1][i]
        v.append(scalars[i] * pow(diagonal, -1, p) % p)
    return _condition_on_first_equation(inst, v)


def _attack_identity_frame(inst):
    u, scalars = _mapping_factor_data(inst)
    return _condition_on_first_equation(inst, scalars)


def _attack_one_equation(inst):
    d, p = inst["d"], inst["p"]
    u, scalars = _mapping_factor_data(inst)
    first = inst["source_sequence"][1]
    pivot = next((i for i, value in enumerate(first) if value), 0)
    v = [0] * d
    v[pivot] = scalars[0] * pow(first[pivot], -1, p) % p
    return _condition_on_first_equation(inst, v)


def _attack_random_restart(inst, attempts=256):
    rng = random.Random(0xA11CE + inst["d"] + inst["cycle_length"])
    for _ in range(attempts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate, True
    return random_candidate(inst, rng), False


def canonical_key(inst):
    """Canonical under simultaneous changes of basis and side reversal."""
    d, p = inst["d"], inst["p"]
    source, target = inst["source_sequence"], inst["target_sequence"]
    source_basis = source[1:d + 1]
    target_basis = target[1:d + 1]
    source_inverse = _matrix_inverse(_columns_to_rows(source_basis), p)
    target_inverse = _matrix_inverse(_columns_to_rows(target_basis), p)

    forward_columns = [
        _mat_vec(source_inverse, vector, p)
        for vector in target_basis
    ]
    reverse_columns = [
        _mat_vec(target_inverse, vector, p)
        for vector in source_basis
    ]
    source_extras = [
        _mat_vec(source_inverse, vector, p)
        for vector in source[d + 1:]
    ]
    target_extras = [
        _mat_vec(target_inverse, vector, p)
        for vector in target[d + 1:]
    ]
    forward = (forward_columns, source_extras)
    reverse = (reverse_columns, target_extras)
    orientation = min(forward, reverse)
    payload = {
        "p": p,
        "d": d,
        "cycle_length": inst["cycle_length"],
        "orientation": orientation,
    }
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _transform_basis(inst, matrix):
    d, p = inst["d"], inst["p"]
    inverse = _matrix_inverse(matrix, p)
    inverse_transpose = _transpose(inverse)
    source = [_mat_vec(matrix, vector, p)
              for vector in inst["source_sequence"]]
    target = [_mat_vec(matrix, vector, p)
              for vector in inst["target_sequence"]]

    u_raw = _mat_vec(matrix, inst["answer"]["u"], p)
    pivot = _first_nonzero(u_raw)
    scale = u_raw[pivot]
    u = _vscale(pow(scale, -1, p), u_raw, p)
    v_raw = _mat_vec(inverse_transpose, inst["answer"]["v"], p)
    v = _vscale(scale, v_raw, p)
    transformed = dict(inst)
    transformed["source_sequence"] = source
    transformed["target_sequence"] = target
    transformed["answer"] = {"u": u, "v": v}
    return transformed


def _swap_sides(inst):
    p = inst["p"]
    u, v = inst["answer"]["u"], inst["answer"]["v"]
    denominator = (1 + _dot(v, u, p)) % p
    inverse_v = _vscale((-pow(denominator, -1, p)) % p, v, p)
    swapped = dict(inst)
    swapped["source_sequence"] = inst["target_sequence"]
    swapped["target_sequence"] = inst["source_sequence"]
    swapped["answer"] = {"u": list(u), "v": inverse_v}
    return swapped


def _random_relabelling_matrices(d, p, rng):
    permutation = list(range(d))
    rng.shuffle(permutation)
    perm_matrix = [[0] * d for _ in range(d)]
    for column, row in enumerate(permutation):
        perm_matrix[row][column] = 1

    diagonal = _identity(d)
    for i in range(d):
        diagonal[i][i] = rng.randrange(1, p)

    shear = _identity(d)
    row, col = rng.sample(range(d), 2)
    shear[row][col] = rng.randrange(1, p)

    pd = _mat_mul(perm_matrix, diagonal, p)
    ds = _mat_mul(diagonal, shear, p)
    pds = _mat_mul(pd, shear, p)
    return [perm_matrix, diagonal, shear, pd, ds, pds]


def escalate(params):
    """Raise coefficient entropy without adding answer atoms or arithmetic steps."""
    harder = dict(params)
    p = harder.get("p", 2_147_483_647)
    if p < 2_147_483_647:
        harder["p"] = 2_147_483_647
        return harder
    if p < _MERSENNE_61:
        harder["p"] = _MERSENNE_61
        return harder
    if p < _MERSENNE_127:
        harder["p"] = _MERSENNE_127
        return harder
    # The useful fixed-length entropy axis is exhausted.
    # d=24 already costs 12*d+3 = 291 exact operations by the compact route.
    # Raising the dimension would violate G9's 300-operation cap, while the
    # next standard Mersenne prime (2^521-1) would make the 48-entry answer far
    # longer than 2,000 characters.  The benchmark format is therefore at cap.
    return "cap_bound"


def _answer_atoms(answer):
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, list):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def _worst_answer_chars(d, p):
    answer = {"u": [p - 1] * d, "v": [p - 1] * d}
    return len(json.dumps(answer, separators=(",", ":")))


def _corruptions(inst):
    answer = inst["answer"]
    u, v = answer["u"], answer["v"]
    duplicated = list(v)
    duplicated[-1] = duplicated[-2]
    return {
        "drop": {"u": u[:-1], "v": list(v)},
        "swap": {"u": list(v), "v": list(u)},
        "duplicate": {"u": list(u), "v": duplicated},
        "empty": {},
        "out_of_range": {"u": list(u), "v": list(v[:-1]) + [inst["p"]]},
    }


def selftest():
    report = {}

    # G1: every named level, three independent seeds, plus field and JSON checks.
    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        if not _is_prime_64(params["p"]):
            failures.append(f"{preset}: modulus is not prime")
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            attempts += 1
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append(f"{preset}/{seed}: answer is not JSON-native")

    # Independently exercise the displayed sigma/tau formulas on the complete
    # demo set.  Theorem 4.1 is the construction proof; these finite checks catch
    # transcription or sign errors in this module's statement of that theorem.
    demo_identity = make_instance(seed=0, **DIFFICULTY["demo"])
    vectors = list(itertools.product(
        range(demo_identity["p"]), repeat=demo_identity["d"]
    ))
    points = [
        (vector, index)
        for vector in vectors
        for index in range(demo_identity["cycle_length"])
    ]
    involutive_pairs = 0
    ybe_triples = 0
    formula_rng = random.Random(0xB4A1D)
    for label, sequence in (
        ("source", demo_identity["source_sequence"]),
        ("target", demo_identity["target_sequence"]),
    ):
        for x in points:
            for y in points:
                image = _solution_r(sequence, demo_identity["p"], x, y)
                if _solution_r(sequence, demo_identity["p"], *image) != (x, y):
                    failures.append(f"demo {label}: involutivity failed")
                    break
                involutive_pairs += 1
            else:
                continue
            break
        for _ in range(10_000):
            triple = tuple(formula_rng.choice(points) for _ in range(3))
            left = _r23(
                sequence,
                demo_identity["p"],
                _r12(sequence, demo_identity["p"],
                     _r23(sequence, demo_identity["p"], triple)),
            )
            right = _r12(
                sequence,
                demo_identity["p"],
                _r23(sequence, demo_identity["p"],
                     _r12(sequence, demo_identity["p"], triple)),
            )
            if left != right:
                failures.append(f"demo {label}: Yang--Baxter identity failed")
                break
            ybe_triples += 1
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
        "audited_prime_moduli": sorted({v["p"] for v in DIFFICULTY.values()}),
        "demo_involutive_pairs_checked": involutive_pairs,
        "demo_yang_baxter_triples_checked": ybe_triples,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=20260729, **shipping_params)

    # G2: five requested perturbation shapes and five distinct rejection reasons.
    corruption_results = {}
    reasons = []
    for name, candidate in _corruptions(shipping).items():
        ok, reason = verify(shipping, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
        if not ok:
            reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": (len(reasons) == 5 and len(set(reasons)) == 5),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: realistic prose, a fence, and exact tagged JSON.
    encoded = json.dumps(shipping["answer"], separators=(",", ":"))
    model_reply = (
        "The rank-one factors follow from the two deviations.\n\n```json\n"
        f"<answer>{encoded}</answer>\n```\n"
    )
    parsed = parse_answer(model_reply)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and parse_answer("garbage") is None,
        "parsed_equals_answer": parsed == shipping["answer"],
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    # G4: uniform sampling from the exact normalized/invertible language.
    guess_rng = random.Random(0x220702944)
    samples = 200_000
    hits = 0
    t0 = time.perf_counter()
    for _ in range(samples):
        if verify(shipping, random_candidate(shipping, guess_rng))[0]:
            hits += 1
    guess_time = time.perf_counter() - t0
    space = search_space(shipping)
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6 and 1 / space < 1e-6,
        "hits": hits,
        "total": samples,
        "fraction": hits / samples,
        "exact_probability": 1 / space,
        "exact_probability_fraction": f"1/{space}",
        "candidate_space_bits": space.bit_length() - 1,
        "wall_clock_sec": round(guess_time, 6),
    }

    # G5/G6 share an eight-seed audit of attacks and the successful reference.
    attack_functions = {
        "outlier_coordinate_magnitude": _attack_outlier_coordinate,
        "greedy_diagonal_only": _attack_diagonal_greedy,
        "by_hand_identity_frame_ansatz": _attack_identity_frame,
        "single_equation_sparse_v": _attack_one_equation,
    }
    attack_panel = {
        name: {"successes": 0, "attempts": 8, "wall_clock_sec": 0.0}
        for name in attack_functions
    }
    attack_panel["random_restart_256"] = {
        "successes": 0, "attempts": 8, "wall_clock_sec": 0.0
    }
    reference_successes = 0
    compact_successes = 0
    reference_operations = []
    reference_inversions = []
    reference_times = []
    baseline_time = 0.0
    for seed in range(8):
        inst = make_instance(seed=7000 + seed, **shipping_params)
        for name, attack in attack_functions.items():
            start = time.perf_counter()
            candidate = attack(inst)
            elapsed = time.perf_counter() - start
            attack_panel[name]["wall_clock_sec"] += elapsed
            if verify(inst, candidate)[0]:
                attack_panel[name]["successes"] += 1

        start = time.perf_counter()
        _, random_success = _attack_random_restart(inst, 256)
        elapsed = time.perf_counter() - start
        baseline_time += elapsed
        attack_panel["random_restart_256"]["wall_clock_sec"] += elapsed
        if random_success:
            attack_panel["random_restart_256"]["successes"] += 1

        start = time.perf_counter()
        reference, operations, inversions = _reference_solve(inst)
        reference_times.append(time.perf_counter() - start)
        reference_operations.append(operations)
        reference_inversions.append(inversions)
        if verify(inst, reference)[0]:
            reference_successes += 1
        if verify(inst, _compact_solve(inst))[0]:
            compact_successes += 1

    for result in attack_panel.values():
        result["wall_clock_sec"] = round(result["wall_clock_sec"], 6)
    all_failed = all(result["successes"] == 0 for result in attack_panel.values())
    avg_ops = round(sum(reference_operations) / len(reference_operations))
    avg_inversions = round(sum(reference_inversions) / len(reference_inversions))
    avg_reference_time = sum(reference_times) / len(reference_times)
    # Count every modular add/subtract/multiply/inversion in the intended
    # implementation.  Comparisons used to locate nonzero pivots are free.
    intended_ops = 12 * shipping["d"] + 3

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": demo_count == 1 and hits / samples < 1e-6 and reference_successes == 8,
        "shipping_sample_hits": hits,
        "shipping_sample_total": samples,
        "shipping_solution_density_estimate": hits / samples,
        "known_unique_solution_count": 1,
        "exact_density": f"1/{space}",
        "demo_exact_solution_count": demo_count,
        "baseline_attack": "random_restart_256",
        "baseline_attack_iterations": 8 * 256,
        "baseline_attack_wall_clock_sec": round(baseline_time, 6),
        "reference_operations": avg_ops,
        "reference_inversions": avg_inversions,
        "reference_wall_clock_sec": round(avg_reference_time, 6),
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attack_panel,
        "reference_algorithm": {
            "name": "exact modular Gauss--Jordan elimination",
            "complexity": "O(d^3) exact field operations",
            "wall_clock_sec": round(avg_reference_time, 6),
            "operations": avg_ops,
            "inversions": avg_inversions,
            "solves": f"{reference_successes}/8, as expected",
        },
        "intended_compact_route": {
            "name": "two rank-one factorizations and Sherman--Morrison",
            "operations_upper_bound": intended_ops,
            "solves": f"{compact_successes}/8",
        },
    }

    # G7: double the dimension and decoy count; construction and certificate hold.
    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled_params["extra"] *= 2
    start = time.perf_counter()
    doubled = make_instance(seed=314159, **doubled_params)
    doubled_build = time.perf_counter() - start
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > space,
        "shipping_n": shipping["d"],
        "doubled_n": doubled["d"],
        "candidate_space_bits_shipping": space.bit_length() - 1,
        "candidate_space_bits_doubled": search_space(doubled).bit_length() - 1,
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_reason,
    }

    # G8: generators of GL(d,p), their compositions, and side reversal.
    invariant = 0
    real = 0
    keys = []
    for seed in range(20):
        inst = make_instance(seed=9000 + seed, **shipping_params)
        original_key = canonical_key(inst)
        keys.append(original_key)
        rng = random.Random(12000 + seed)
        transformed_instances = [
            _transform_basis(inst, matrix)
            for matrix in _random_relabelling_matrices(inst["d"], inst["p"], rng)
        ]
        transformed_instances.append(_swap_sides(inst))
        transformed_instances.append(_swap_sides(transformed_instances[-2]))
        for changed in transformed_instances:
            if canonical_key(changed) == original_key:
                invariant += 1
            if verify(changed, changed["answer"])[0]:
                real += 1
    expected_transforms = 20 * 8
    report["G8_canonical_key"] = {
        "pass": (invariant == expected_transforms
                 and real == expected_transforms
                 and len(set(keys)) == 20),
        "invariant_relabellings": invariant,
        "real_transformations_verified": real,
        "expected_each": expected_transforms,
        "unrelated_attempts": 20,
        "unrelated_distinct_keys": len(set(keys)),
        "transformations": [
            "coordinate permutation",
            "independent nonzero coordinate scaling",
            "elementary shear",
            "three sampled compositions of those GL generators",
            "source/target reversal",
            "basis change composed with source/target reversal",
        ],
    }

    # G9: oracle arms are diagnostic; exact caps are the sole pass condition.
    compact_answer = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(compact_answer)
    answer_tokens = math.ceil(answer_chars / 4)
    worst_chars = _worst_answer_chars(shipping["d"], shipping["p"])
    worst_tokens = math.ceil(worst_chars / 4)
    arms = {
        key: dict(G9_ORACLE_RESULTS[key])
        for key in ("bare", "hinted", "placebo")
    }
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    within_caps = (worst_chars <= 2000 and _answer_atoms(shipping["answer"]) <= 256
                   and intended_ops <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "worst_case_answer_chars": worst_chars,
        "worst_case_answer_tokens": worst_tokens,
        "answer_elements": _answer_atoms(shipping["answer"]),
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
