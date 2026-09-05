"""Verified problem generator for arXiv:2003.00668.

The generated task is native finite-field symplectic linear algebra.  It asks for
the unique normalized coefficient vector whose row combination lies in the
symplectic radical of a displayed code generator.  Instances are obtained from
a known canonical radical by symplectic transvections and a Vandermonde change
of row basis; the answer is carried through those transformations.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import random
import re
import sys
import time

# Keep the repository helpers importable when this file is run from its result
# directory.  This family needs only prime-field arithmetic, so it remains
# standard-library-only if gvlib is absent.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - the documented dependency-free path
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "linear-code generator over F_q in exact factored form",
        "symplectic transvections",
        "finite-field coefficient and coordinate vectors",
    ],
    "verification_operations": [
        "exact finite-field linear combination",
        "exact symplectic inner product",
        "exact Hamming-weight comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Symplectic transvections preserve the canonical Gram form, so the "
        "apparently large radical computation collapses to the left annihilator "
        "of an affine-progression Vandermonde matrix."
    ),
    "hardness_basis": (
        "Track B: the Section II rank/radical formula is mechanically evaluated "
        "by materializing H, forming H_X H_Z^T-H_Z H_X^T, and Gaussian "
        "elimination in O(ell^2 n+ell^3) field operations; at the hard preset "
        "the reference implementation uses about 12.15 million modular operations "
        "and about 0.31 seconds per instance on an unloaded local run (2.88 seconds "
        "in the latest shared-host rerun), while the invariant "
        "route uses 291 exact finite-field "
        "arithmetic operations but must be recognized and executed without tools."
    ),
    "max_answer_tokens": 119,
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
    "demo": {"n": 4, "ell": 5, "q": 7, "transvections": 1},
    "easy": {"n": 32, "ell": 31, "q": 37, "transvections": 3},
    "medium": {"n": 128, "ell": 59, "q": 61, "transvections": 5},
    "hard": {"n": 512, "ell": 59, "q": 61, "transvections": 8},
}
SHIPPING_DIFFICULTY = "hard"

CERTIFICATE_LANGUAGE = {
    "description": (
        "A length-59 full-support coefficient vector over F_61, represented as "
        "JSON integers 1..60, normalized by a[0]=1.  At other presets the "
        "declared length and prime field are the instance's ell and q."
    ),
    "bounds": {
        "length": 59,
        "field_order": 61,
        "full_support": True,
        "normalization": "a[0] = 1",
    },
}

STRUCTURAL_HINT = (
    "Symplectic transvections preserve every pairwise symplectic product in the "
    "displayed canonical row family."
)
PLACEBO_HINT = (
    "Careful bookkeeping of all finite-field coordinates helps avoid small "
    "indexing and normalization mistakes."
)

# Filled from the separately preserved harden.py arms.  All three oracle arms
# are diagnostics under the current contract; only the size/operation caps
# contribute to G9.pass.  The 2026-09-05 run exhausted its OpenRouter quota
# after one scored hard-preset bare attempt, so the partial counts stay explicit.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 1},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "unavailable_quota_exhausted",
}

NOTES = """\
Section II, Theorem 1 fixes the exact object: for a generator H=(H_X|H_Z),
the radical C intersect C^perp_s and rank(H_X H_Z^T-H_Z H_X^T) determine the
entanglement parameter.  The proof of Section II, Theorem 2 supplies the other
load-bearing fact: the symplectic group acts on the relevant subspaces without
changing symplectic products.  Theorem 2 itself is only existential, and the
Conclusion explicitly leaves unrestricted explicit constructions as future
work, so it cannot generate a Track-A promised good code.

This module therefore uses Track B.  A canonical one-dimensional radical is
carried through symplectic transvections and a Vandermonde row-basis change.
Generic Gram formation plus Gaussian elimination is the disclosed reference
algorithm.  Random row multipliers defeat the per-row outlier and constant
ansatz; binomial magnitudes defeat the alternating-sign ansatz; the greedy
probe satisfies only the first moment and fails the remaining moments; and 256
uniform full-support restarts per instance do not hit the unique projective
answer.  Transvection vectors and ambient length grow while the 59-entry answer
stays fixed.
"""


def _inv(a: int, q: int) -> int:
    """Multiplicative inverse in the prime field F_q."""
    return pow(a % q, q - 2, q)


def _is_prime(q: int) -> bool:
    if q < 2:
        return False
    if q % 2 == 0:
        return q == 2
    d = 3
    while d * d <= q:
        if q % d == 0:
            return False
        d += 2
    return True


def _symp_xy(ux, uz, vx, vz, q: int) -> int:
    return sum((a * d - b * c) for a, b, c, d in zip(ux, uz, vx, vz)) % q


def _signed_binomial_row(m: int, q: int) -> list[int]:
    """Return ((-1)^k binom(m,k))_k modulo q, using O(m) work."""
    out = [1]
    for k in range(m):
        nxt = (-out[-1] * (m - k) * _inv(k + 1, q)) % q
        out.append(nxt)
    return out


def _answer_from_factors(points, multipliers, origin: int, step: int,
                         ell: int, q: int) -> list[int]:
    """Carry the canonical radical through D*V without solving a system."""
    m = ell - 1
    signed_binom = _signed_binomial_row(m, q)
    step_inv = _inv(step, q)
    raw = []
    for x, d in zip(points, multipliers):
        k = ((x - origin) * step_inv) % q
        if not 0 <= k < ell:
            raise ValueError("evaluation point is outside the declared progression")
        raw.append(signed_binom[k] * _inv(d, q) % q)
    scale = _inv(raw[0], q)
    return [(v * scale) % q for v in raw]


def make_instance(n, seed=0, **params) -> dict:
    """Construct a certified radical by exact structure-preserving maps.

    ``n`` is the physical code length.  ``ell`` is the odd number of generator
    rows, q is a prime larger than ell, and ``transvections`` controls the amount
    of symplectic-coordinate camouflage.  No search for the answer occurs.
    """
    ell = int(params.get("ell", 59))
    q = int(params.get("q", 61))
    n_trans = int(params.get("transvections", 5))
    n = int(n)
    if ell < 3 or ell % 2 != 1:
        raise ValueError("ell must be an odd integer at least 3")
    c = (ell - 1) // 2
    if n < c + 2:
        raise ValueError("need n >= (ell-1)/2 + 2 (the paper's ell < n+c regime)")
    if not _is_prime(q) or q <= ell:
        raise ValueError("q must be prime and strictly larger than ell")
    if n_trans < 0:
        raise ValueError("transvections must be nonnegative")

    rng = random.Random(seed)

    # The canonical B rows use c hyperbolic coordinate pairs and one radical
    # coordinate.  Their physical locations are randomized without changing the
    # row labels, which makes qudit relabelling a real tested symmetry.
    base_positions = rng.sample(range(n), c + 1)
    radical_position = base_positions[-1]

    trans = []
    for _ in range(n_trans):
        vx = [rng.randrange(q) for _ in range(n)]
        vz = [rng.randrange(q) for _ in range(n)]
        # The canonical radical is X_rad.  Setting v_z[rad]=0 makes every
        # transvection fix it exactly: <X_rad,v>=0.
        vz[radical_position] = 0
        if not any(vx) and not any(vz):
            vx[(radical_position + 1) % n] = 1
        trans.append({"alpha": rng.randrange(1, q), "x": vx, "z": vz})

    origin = rng.randrange(q)
    step = rng.randrange(1, q)
    progression_positions = list(range(ell))
    rng.shuffle(progression_positions)
    points = [(origin + step * k) % q for k in progression_positions]
    multipliers = [rng.randrange(1, q) for _ in range(ell)]
    answer = _answer_from_factors(points, multipliers, origin, step, ell, q)

    return {
        "paper": "2003.00668",
        "q": q,
        "n": n,
        "ell": ell,
        "c": c,
        "base_positions": base_positions,
        "transvections": trans,
        "evaluation_origin": origin,
        "evaluation_step": step,
        "evaluation_points": points,
        "row_multipliers": multipliers,
        "answer": answer,
    }


def _compact_vector(x, z) -> str:
    terms = []
    for i, a in enumerate(x):
        if a:
            terms.append(f"X{i}:{a}")
    for i, a in enumerate(z):
        if a:
            terms.append(f"Z{i}:{a}")
    return " ".join(terms) if terms else "0"


def render(inst) -> str:
    q, n, ell, c = inst["q"], inst["n"], inst["ell"], inst["c"]
    pos = inst["base_positions"]
    lines = [
        "Find a symplectic-radical row combination over a prime field.",
        "",
        f"All arithmetic is in F_{q}, represented by integers 0,...,{q-1} modulo {q}.",
        f"A vector is (x|z) in F_{q}^(2*{n}), with coordinates numbered 0 through {n-1}.",
        "Its symplectic product with (x'|z') is",
        f"  <(x|z),(x'|z')> = sum_r (x_r z'_r - z_r x'_r) mod {q}.",
        "The X-weight (respectively Z-weight) is the number of nonzero x "
        "(respectively z) coordinates.",
        "",
        f"There are ell={ell}=2*{c}+1 canonical rows b^0_0,...,b^0_{ell-1}.",
        "For k=0,...,c-1, b^0_(2k) is the X-unit vector and b^0_(2k+1) "
        "is the Z-unit vector at the listed physical coordinate:",
        "  pair positions k:coordinate = "
        + ", ".join(f"{k}:{pos[k]}" for k in range(c)),
        f"The final row b^0_{ell-1} is the X-unit vector at coordinate {pos[-1]}.",
        "All unmentioned coordinates are zero.",
        "",
        "Apply the following symplectic transvections in the displayed order to "
        "every canonical row.  A line 'alpha ; v' means replace b by",
        f"  b <- b + alpha*<b,v>*v mod {q}.",
        "Each v is written sparsely as Xindex:value or Zindex:value; omitted entries are zero.",
    ]
    for j, t in enumerate(inst["transvections"]):
        lines.append(
            f"  T{j}: {t['alpha']} ; {_compact_vector(t['x'], t['z'])}"
        )
    lines += [
        "Call the resulting rows b_0,...,b_(ell-1).",
        "",
        "Define the displayed generator rows H_i by the exact factorization",
        f"  H_i = d_i * sum_{{j=0}}^{{ell-1}} x_i^j b_j mod {q}.",
        f"The evaluation points form x_i = {inst['evaluation_origin']} + "
        f"{inst['evaluation_step']}*k_i mod {q}, with k_i a permutation of 0,...,{ell-1}.",
        "The row data are 0-indexed and listed as i : x_i, d_i:",
    ]
    for i, (x, d) in enumerate(zip(inst["evaluation_points"], inst["row_multipliers"])):
        lines.append(f"  {i}: {x}, {d}")
    lines += [
        "",
        f"Let C be the F_{q} row span of H_0,...,H_(ell-1).  Find coefficients",
        "a=[a_0,...,a_(ell-1)] such that w=sum_i a_i H_i is nonzero,",
        "has X-weight exactly 1 and Z-weight exactly 0, and satisfies",
        "<w,H_i>=0 for every i.  Thus w is in C intersect C^{perp_s}.",
        f"Your answer must contain exactly {ell} integers, every one in 1,...,{q-1};",
        "the first coefficient must be a_0=1.  Order matters and repetitions are allowed.",
        "",
        "Give your final answer inside <answer></answer> tags, as one JSON array of integers.",
        f"Example format only: <answer>{json.dumps([1] * ell)}</answer>",
        "Output nothing else inside the tags.",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines += ["", "Hint: " + STRUCTURAL_HINT]
    elif mode == "placebo":
        lines += ["", "Hint: " + PLACEBO_HINT]
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer>\s*(.*?)\s*</answer>", text, flags=re.I | re.S)
    if not blocks:
        return None
    body = blocks[-1].strip()
    # Tolerate a fenced payload inside the required tags as well as ordinary
    # model prose outside them.
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        ans = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(ans, list):
        return None
    if any(isinstance(v, bool) or not isinstance(v, int) for v in ans):
        return None
    return ans


def _materialize_base(inst):
    """Execute the instance's transvections on its canonical row family."""
    q, n, ell, c = inst["q"], inst["n"], inst["ell"], inst["c"]
    positions = inst["base_positions"]
    bx = [[0] * n for _ in range(ell)]
    bz = [[0] * n for _ in range(ell)]
    for k in range(c):
        bx[2 * k][positions[k]] = 1
        bz[2 * k + 1][positions[k]] = 1
    bx[-1][positions[-1]] = 1
    for t in inst["transvections"]:
        alpha, vx, vz = t["alpha"], t["x"], t["z"]
        for i in range(ell):
            s = alpha * _symp_xy(bx[i], bz[i], vx, vz, q) % q
            if s:
                bx[i] = [(a + s * b) % q for a, b in zip(bx[i], vx)]
                bz[i] = [(a + s * b) % q for a, b in zip(bz[i], vz)]
    return bx, bz


def _moments(inst, answer):
    q, ell = inst["q"], inst["ell"]
    beta = [0] * ell
    for a, d, x in zip(answer, inst["row_multipliers"], inst["evaluation_points"]):
        term = a * d % q
        power = 1
        for j in range(ell):
            beta[j] = (beta[j] + term * power) % q
            power = power * x % q
    return beta


def verify(inst, answer):
    """Check the witness exactly, without consulting ``inst['answer']``."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    ell, q = inst["ell"], inst["q"]
    if len(answer) < ell:
        return False, f"too few coefficients: expected {ell}"
    if len(answer) > ell:
        return False, f"too many coefficients: expected {ell}"
    if any(isinstance(a, bool) or not isinstance(a, int) for a in answer):
        return False, "every coefficient must be an integer"
    if any(a <= 0 or a >= q for a in answer):
        return False, f"coefficient outside the required range 1..{q-1}"
    if answer[0] != 1:
        return False, "the projective normalization requires a_0=1"

    # A fast necessary filter keeps the 200k-candidate density measurement
    # cheap.  Successful candidates still undergo the native symplectic check.
    first = sum(a * d for a, d in zip(answer, inst["row_multipliers"])) % q
    if first:
        return False, "the row combination fails the degree-0 moment"
    beta = _moments(inst, answer)
    if any(beta[:-1]):
        j = next(j for j, v in enumerate(beta[:-1]) if v)
        return False, f"the row combination fails the degree-{j} moment"

    bx, bz = _materialize_base(inst)
    n = inst["n"]
    wx = [0] * n
    wz = [0] * n
    for coeff, xrow, zrow in zip(beta, bx, bz):
        if coeff:
            wx = [(a + coeff * b) % q for a, b in zip(wx, xrow)]
            wz = [(a + coeff * b) % q for a, b in zip(wz, zrow)]
    if not any(wx) and not any(wz):
        return False, "the resulting codeword is zero"

    # Execute the actual symplectic witness test against every factored H_i.
    wb = [_symp_xy(wx, wz, xrow, zrow, q) for xrow, zrow in zip(bx, bz)]
    for i, (x, d) in enumerate(zip(inst["evaluation_points"], inst["row_multipliers"])):
        power = 1
        inner = 0
        for s in wb:
            inner = (inner + d * power * s) % q
            power = power * x % q
        if inner:
            return False, f"symplectic product <w,H_{i}> is {inner}, not zero"
    x_weight = sum(v != 0 for v in wx)
    z_weight = sum(v != 0 for v in wz)
    if x_weight != 1:
        return False, f"X-weight is {x_weight}, not 1"
    if z_weight != 0:
        return False, f"Z-weight is {z_weight}, not 0"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the declared normalized full-support language."""
    return [1] + [rng.randrange(1, inst["q"]) for _ in range(inst["ell"] - 1)]


def search_space(inst):
    return (inst["q"] - 1) ** (inst["ell"] - 1)


def enumerate_all(inst):
    size = search_space(inst)
    if size > 200_000:
        return None
    hits = 0
    symbols = range(1, inst["q"])
    for tail in itertools.product(symbols, repeat=inst["ell"] - 1):
        ok, _ = verify(inst, [1, *tail])
        hits += int(ok)
    return hits


def canonical_key(inst):
    """Canonicalize row order/scaling, affine evaluation labels, and qudit labels.

    Exact code equivalence under arbitrary row operations and monomial
    symplectic transformations is not attempted; the README records this
    limitation.  The normal form below is exact for every relabelling used by
    this generator and by G8.
    """
    q, n, ell, c = inst["q"], inst["n"], inst["ell"], inst["c"]
    origin, step = inst["evaluation_origin"], inst["evaluation_step"]
    sinv = _inv(step, q)
    # Individual H-row scalings are merely a generator-basis change.  Discard
    # their multipliers here and retain only the affine-normalized row labels.
    rows = sorted(((x - origin) * sinv) % q for x in inst["evaluation_points"])
    pair_positions = set(inst["base_positions"][:-1])
    rad = inst["base_positions"][-1]
    roles = []
    for r in range(n):
        if r in pair_positions:
            roles.append((1, 0))
        elif r == rad:
            roles.append((2, 0))
        else:
            roles.append((0, 0))

    # T_(alpha,v) = T_(alpha/s^2, s*v).  Canonicalize this inexpensive
    # representation symmetry before combining the coordinate features.  The
    # sorted role/value multiset makes the chosen scale independent of qudit
    # numbering and of the ordering of the hyperbolic pairs.
    normalized_trans = []
    for t in inst["transvections"]:
        best = None
        for s in range(1, q):
            alpha = t["alpha"] * _inv(s * s, q) % q
            pairs = sorted(
                (*roles[r], s * t["x"][r] % q, s * t["z"][r] % q)
                for r in range(n)
            )
            candidate = (alpha, pairs, s)
            if best is None or candidate[:2] < best[:2]:
                best = candidate
        alpha, _, scale = best
        normalized_trans.append({
            "alpha": alpha,
            "x": [scale * v % q for v in t["x"]],
            "z": [scale * v % q for v in t["z"]],
        })

    coords = []
    for r in range(n):
        trail = []
        for t in normalized_trans:
            trail.extend((t["x"][r], t["z"][r]))
        coords.append((*roles[r], *trail))
    coords.sort()
    normal = {
        "q": q,
        "n": n,
        "ell": ell,
        "rows": rows,
        "alphas": [t["alpha"] for t in normalized_trans],
        "coordinate_features": coords,
    }
    blob = json.dumps(normal, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def escalate(params):
    """Grow ambient camouflage and field entropy at fixed witness length."""
    p = dict(params)
    # Ambient length is an unlimited fixed-answer-length axis, so every call is
    # strictly harder even after the finite transvection/field ladder saturates.
    p["n"] = int(p.get("n", 512)) * 2
    p["transvections"] = min(int(p.get("transvections", 8)) + 2, 16)
    q = int(p.get("q", 61))
    if q < 131:
        p["q"] = 131
    elif q < 257:
        p["q"] = 257
    else:
        p["q"] = q
    return p


# --- Reference algorithm and adversarial probes used only by selftest --------

def _materialize_h(inst):
    q, n, ell = inst["q"], inst["n"], inst["ell"]
    bx, bz = _materialize_base(inst)
    hx = []
    hz = []
    for x, d in zip(inst["evaluation_points"], inst["row_multipliers"]):
        rx = [0] * n
        rz = [0] * n
        power = 1
        for j in range(ell):
            coeff = d * power % q
            if coeff:
                rx = [(a + coeff * b) % q for a, b in zip(rx, bx[j])]
                rz = [(a + coeff * b) % q for a, b in zip(rz, bz[j])]
            power = power * x % q
        hx.append(rx)
        hz.append(rz)
    return hx, hz


def _generic_gram(inst, hx, hz):
    q, ell = inst["q"], inst["ell"]
    gram = [[0] * ell for _ in range(ell)]
    for i in range(ell):
        for j in range(i + 1, ell):
            v = _symp_xy(hx[i], hz[i], hx[j], hz[j], q)
            gram[i][j] = v
            gram[j][i] = (-v) % q
    return gram


def _nullspace_one(matrix, q: int):
    """Generic RREF nullspace; return one vector and an operation count."""
    a = [row[:] for row in matrix]
    rows, cols = len(a), len(a[0])
    pivots = []
    r = 0
    ops = 0
    for col in range(cols):
        pivot = next((i for i in range(r, rows) if a[i][col] % q), None)
        if pivot is None:
            continue
        a[r], a[pivot] = a[pivot], a[r]
        invp = _inv(a[r][col], q)
        ops += 1
        for j in range(col, cols):
            a[r][j] = a[r][j] * invp % q
            ops += 1
        for i in range(rows):
            if i == r or not a[i][col]:
                continue
            f = a[i][col]
            for j in range(col, cols):
                a[i][j] = (a[i][j] - f * a[r][j]) % q
                ops += 2
        pivots.append(col)
        r += 1
        if r == rows:
            break
    free = [j for j in range(cols) if j not in pivots]
    if not free:
        return None, ops
    fcol = free[0]
    x = [0] * cols
    x[fcol] = 1
    for i in range(len(pivots) - 1, -1, -1):
        pcol = pivots[i]
        x[pcol] = (-sum(a[i][j] * x[j] for j in range(pcol + 1, cols))) % q
        ops += 2 * (cols - pcol - 1)
    if x[0] == 0:
        return x, ops
    scale = _inv(x[0], q)
    x = [v * scale % q for v in x]
    ops += cols + 1
    return x, ops


def _reference_algorithm(inst):
    start = time.perf_counter()
    hx, hz = _materialize_h(inst)
    gram = _generic_gram(inst, hx, hz)
    vec, elim_ops = _nullspace_one(gram, inst["q"])
    elapsed = time.perf_counter() - start
    ell, n, t = inst["ell"], inst["n"], len(inst["transvections"])
    # Count modular primitive operations in the direct loops: dot/update for
    # transvections, H materialization, Gram formation, and elimination.
    operations = (
        t * ell * 6 * n
        + ell * ell * 4 * n
        + (ell * (ell - 1) // 2) * 4 * n
        + elim_ops
    )
    return vec, elapsed, operations


def _normalize_full(values, q):
    values = [v % q or 1 for v in values]
    scale = _inv(values[0], q)
    return [v * scale % q for v in values]


def _attack_candidates(inst, rng):
    q = inst["q"]
    d = inst["row_multipliers"]
    x = inst["evaluation_points"]
    o = inst["evaluation_origin"]
    si = _inv(inst["evaluation_step"], q)
    kpos = [((v - o) * si) % q for v in x]

    outlier = [1] * inst["ell"]
    outlier[d.index(min(d))] = 2
    outlier = _normalize_full(outlier, q)

    # Greedily meet only the first moment, leaving all other constraints alone.
    greedy = [1] * inst["ell"]
    pivot = inst["ell"] - 1
    for trial in range(1, q):
        greedy[1] = trial
        need = -sum(greedy[i] * d[i] for i in range(inst["ell"] - 1))
        last = need * _inv(d[pivot], q) % q
        if last:
            greedy[pivot] = last
            break
    greedy = _normalize_full(greedy, q)

    constant_unscaled = _normalize_full([_inv(v, q) for v in d], q)
    alternating = _normalize_full([
        ((-1 if k % 2 else 1) * _inv(di, q)) % q
        for k, di in zip(kpos, d)
    ], q)
    linear = _normalize_full([
        (k + 1) * _inv(di, q) % q for k, di in zip(kpos, d)
    ], q)
    return {
        "outlier_smallest_multiplier": [outlier],
        "greedy_cancel_degree0": [greedy],
        "undo_multipliers_constant_ansatz": [constant_unscaled],
        "progression_alternating_ansatz": [alternating],
        "progression_linear_ansatz": [linear],
        "random_restart_256": [random_candidate(inst, rng) for _ in range(256)],
    }


def _row_permuted(inst, rng):
    out = {k: v for k, v in inst.items() if k != "answer"}
    perm = list(range(inst["ell"]))
    rng.shuffle(perm)
    out["evaluation_points"] = [inst["evaluation_points"][i] for i in perm]
    out["row_multipliers"] = [inst["row_multipliers"][i] for i in perm]
    carried = [inst["answer"][i] for i in perm]
    carried = _normalize_full(carried, inst["q"])
    out["answer"] = carried
    return out


def _qudit_permuted(inst, rng):
    out = {k: v for k, v in inst.items() if k not in ("answer", "transvections")}
    perm = list(range(inst["n"]))  # old coordinate -> new coordinate
    rng.shuffle(perm)
    out["base_positions"] = [perm[p] for p in inst["base_positions"]]
    trans = []
    for t in inst["transvections"]:
        vx = [0] * inst["n"]
        vz = [0] * inst["n"]
        for old, new in enumerate(perm):
            vx[new] = t["x"][old]
            vz[new] = t["z"][old]
        trans.append({"alpha": t["alpha"], "x": vx, "z": vz})
    out["transvections"] = trans
    out["answer"] = inst["answer"][:]
    return out


def _row_rescaled(inst, rng):
    """Apply independent nonzero scalings to the displayed H rows."""
    out = {k: v for k, v in inst.items() if k != "answer"}
    q = inst["q"]
    scales = [rng.randrange(1, q) for _ in range(inst["ell"])]
    out["row_multipliers"] = [
        d * s % q for d, s in zip(inst["row_multipliers"], scales)
    ]
    carried = [
        a * _inv(s, q) % q for a, s in zip(inst["answer"], scales)
    ]
    out["answer"] = _normalize_full(carried, q)
    return out


def _affine_evaluation_changed(inst, rng):
    out = {k: v for k, v in inst.items() if k != "answer"}
    q = inst["q"]
    u = rng.randrange(1, q)
    t = rng.randrange(q)
    out["evaluation_origin"] = (u * inst["evaluation_origin"] + t) % q
    out["evaluation_step"] = u * inst["evaluation_step"] % q
    out["evaluation_points"] = [(u * x + t) % q for x in inst["evaluation_points"]]
    out["answer"] = inst["answer"][:]
    return out


def _hyperbolic_pairs_permuted(inst, rng):
    """Reorder canonical hyperbolic pairs without changing their span."""
    out = {k: v for k, v in inst.items() if k != "answer"}
    pairs = inst["base_positions"][:-1]
    perm = list(range(len(pairs)))
    rng.shuffle(perm)
    out["base_positions"] = [pairs[i] for i in perm] + [inst["base_positions"][-1]]
    out["answer"] = inst["answer"][:]
    return out


def _transvection_rescaled(inst, rng):
    """Use T_(alpha,v)=T_(alpha/s^2,s*v) for every listed map."""
    out = {k: v for k, v in inst.items() if k not in ("answer", "transvections")}
    q = inst["q"]
    trans = []
    for t in inst["transvections"]:
        s = rng.randrange(1, q)
        sinv = _inv(s, q)
        trans.append({
            "alpha": t["alpha"] * sinv * sinv % q,
            "x": [s * v % q for v in t["x"]],
            "z": [s * v % q for v in t["z"]],
        })
    out["transvections"] = trans
    out["answer"] = inst["answer"][:]
    return out


def _answer_token_measure(answer):
    # A conservative lexical count: every integer and punctuation mark is an
    # atomic token.  This overestimates common BPE tokenizers for these values.
    blob = json.dumps(answer)
    return len(re.findall(r"\d+|[\[\],-]", blob))


def selftest():
    report = {"paper": "2003.00668", "track": TRACK,
              "shipping_difficulty": SHIPPING_DIFFICULTY}

    # G1: every preset, several independently generated instances.
    planted = 0
    g1_reasons = []
    for name, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            planted += int(ok)
            if not ok:
                g1_reasons.append(f"{name}/{seed}: {why}")
    report["G1_planted_verifies"] = {
        "pass": planted == 12, "verified": planted, "attempts": 12,
        "failures": g1_reasons,
    }

    # G2: five distinct corruption classes and five distinct rejection reasons.
    ship = make_instance(seed=3, **DIFFICULTY[SHIPPING_DIFFICULTY])
    ans = ship["answer"]
    swap = ans[:]
    pair = next(((i, j) for i in range(1, len(ans))
                 for j in range(i + 1, len(ans)) if ans[i] != ans[j]), (1, 2))
    swap[pair[0]], swap[pair[1]] = swap[pair[1]], swap[pair[0]]
    corruptions = {
        "drop": ans[:-1],
        "swap": swap,
        "duplicate": ans + [ans[-1]],
        "empty": [],
        "out_of_range": ans[:1] + [ship["q"]] + ans[2:],
    }
    rejected = {}
    for name, bad in corruptions.items():
        ok, why = verify(ship, bad)
        rejected[name] = {"rejected": not ok, "reason": why}
    reasons = {v["reason"] for v in rejected.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(v["rejected"] for v in rejected.values()) and len(reasons) == 5,
        "cases": rejected, "distinct_reasons": len(reasons),
    }

    # G3: realistic prose/fence wrapper and JSON-native round trip.
    reply = "I used the radical relation.\n```text\n" + (
        "<answer>" + json.dumps(ans) + "</answer>\n```")
    parsed = parse_answer(reply)
    json_native = json.loads(json.dumps(ans)) == ans
    report["G3_round_trip"] = {
        "pass": parsed == ans and json_native,
        "parsed_matches": parsed == ans, "json_native": json_native,
    }

    # G4 and the shipping density component of G5 share the same 200k uniform
    # structure-aware samples from the declared full-support projective language.
    density_inst = make_instance(seed=11, **DIFFICULTY[SHIPPING_DIFFICULTY])
    density_rng = random.Random(0x200300668)
    samples = 200_000
    hits = 0
    start = time.perf_counter()
    for _ in range(samples):
        candidate = random_candidate(density_inst, density_rng)
        hits += int(verify(density_inst, candidate)[0])
    density_wall = time.perf_counter() - start
    guess_probability = hits / samples
    report["G4_guess_resistance"] = {
        "pass": samples >= 200_000 and guess_probability < 1e-6,
        "hits": hits, "total": samples,
        "observed_probability": guess_probability,
        "exact_language_size": search_space(density_inst),
        "sampling_wall_sec": round(density_wall, 6),
    }

    # G6: five cheap/no-tool probes plus random restarts all fail; the domain
    # standard algorithm is separately reported because Track B expects it to win.
    attack_names = None
    attack_success = {}
    ref_times = []
    ref_ops = []
    ref_success = 0
    attempts = 8
    for seed in range(20, 20 + attempts):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        probes = _attack_candidates(inst, random.Random(90_000 + seed))
        if attack_names is None:
            attack_names = list(probes)
            attack_success = {name: 0 for name in attack_names}
        for name, candidates in probes.items():
            if any(verify(inst, candidate)[0] for candidate in candidates):
                attack_success[name] += 1
        vec, elapsed, operations = _reference_algorithm(inst)
        ok = vec is not None and verify(inst, vec)[0]
        ref_success += int(ok)
        ref_times.append(elapsed)
        ref_ops.append(operations)
    attacks = {
        name: {"successes": attack_success[name], "attempts": attempts}
        for name in attack_names
    }
    all_failed = all(v["successes"] == 0 for v in attacks.values())
    ref_mean_wall = sum(ref_times) / len(ref_times)
    ref_mean_ops = sum(ref_ops) // len(ref_ops)
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_success == attempts,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "materialize H, form the symplectic Gram matrix, Gaussian elimination",
            "complexity": "O(ell^2*n + ell^3) exact field operations",
            "wall_clock_sec": round(ref_mean_wall, 6),
            "operations": ref_mean_ops,
            "solves": f"{ref_success}/{attempts}, as expected",
        },
    }

    demo_count = enumerate_all(make_instance(seed=0, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline"] = {
        "pass": demo_count == 1 and hits == 0 and ref_success == attempts,
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_density_fraction": guess_probability,
        "demo_exact_solution_count": demo_count,
        "baseline_wall_clock_sec": round(ref_mean_wall, 6),
        "baseline_operation_count": ref_mean_ops,
    }

    # G7: double the physical length while keeping the 59-symbol witness fixed.
    doubled_params = dict(DIFFICULTY["hard"])
    doubled_params["n"] *= 2
    doubled_params["transvections"] += 1
    doubled = make_instance(seed=101, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and len(doubled["answer"]) == len(ans),
        "original_n": ship["n"], "doubled_n": doubled["n"],
        "answer_elements_before": len(ans),
        "answer_elements_after": len(doubled["answer"]),
        "verify_reason": doubled_why,
    }

    # G8: row permutations/scalings, qudit and hyperbolic-pair permutations,
    # affine evaluation changes, transvection-vector rescalings, and their
    # composition.  Every comparison is structural.
    invariant_checks = 0
    transformed_verified = 0
    keys = []
    for seed in range(40, 60):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        rng = random.Random(123_000 + seed)
        row = _row_permuted(inst, rng)
        scaled = _row_rescaled(inst, rng)
        qudit = _qudit_permuted(inst, rng)
        affine = _affine_evaluation_changed(inst, rng)
        pairs = _hyperbolic_pairs_permuted(inst, rng)
        trans_scaled = _transvection_rescaled(inst, rng)
        composed = _transvection_rescaled(_hyperbolic_pairs_permuted(
            _affine_evaluation_changed(_qudit_permuted(_row_rescaled(
                _row_permuted(inst, rng), rng), rng), rng), rng), rng)
        base_key = canonical_key(inst)
        for changed in (row, scaled, qudit, affine, pairs, trans_scaled, composed):
            invariant_checks += int(canonical_key(changed) == base_key)
        transformed_verified += int(verify(composed, composed["answer"])[0])
        keys.append(base_key)
    report["G8_canonical_key"] = {
        "pass": invariant_checks == 140 and transformed_verified == 20
                and len(set(keys)) == 20,
        "invariance_checks_passed": invariant_checks,
        "invariance_checks_attempted": 140,
        "transformed_witnesses_verified": transformed_verified,
        "transformed_witnesses_attempted": 20,
        "unrelated_distinct_keys": len(set(keys)),
        "unrelated_instances": 20,
    }

    blob = json.dumps(ans)
    answer_tokens = _answer_token_measure(ans)
    answer_elements = len(ans)
    # Compact route accounting in exact F_q operations: ell-1 additions recover
    # the affine-progression lookup table; 2(ell-1) multiplication/division
    # operations generate the signed binomial weights; ell divisions remove the
    # row multipliers; and ell-1 divisions normalize the remaining coefficients.
    intended_ops = (
        (ship["ell"] - 1)
        + 2 * (ship["ell"] - 1)
        + ship["ell"]
        + (ship["ell"] - 1)
    )
    arms = G9_RESULTS["arms"]
    arms_complete = all(arms[name]["attempts"] >= 3
                        for name in ("bare", "hinted", "placebo"))
    hinted_minus_placebo = None
    if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]:
        hinted_minus_placebo = (
            arms["hinted"]["solved"] / arms["hinted"]["attempts"]
            - arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        )
    within_caps = len(blob) <= 2000 and answer_elements <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        # Since 2026-09-05, both the three-arm comparison and the hinted verdict
        # are recorded diagnostics.  G9(c)'s exact size/effort caps are the only
        # gating part of G9.
        "pass": within_caps,
        "arms": arms,
        "arms_complete": arms_complete,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": len(blob),
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
    }

    gates = [v for k, v in report.items() if k.startswith("G")]
    report["all_passed"] = all(g.get("pass") for g in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
