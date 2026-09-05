"""Verified problem generator for arXiv:1709.02873.

The generated task asks for a certified, denominator-cleared real part of the
determinant of an exactly described transform of Fender--Kharaghani--Suda's
recursive quaternary unit Hadamard matrix.  Generation uses the determinant
formula proved from the paper's character-space recursion; it never solves a
freshly generated instance.
"""

from __future__ import annotations

import copy
import functools
import hashlib
import itertools
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
    from gvlib import exact_matrices, rationals
except ImportError:  # The implementation below remains standard-library-only.
    exact_matrices = rationals = None


TRACK = "B"
SHIPPING_DIFFICULTY = "easy"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "continuous_analytic",
    "computational_core": "linear_algebra",
    "certificate_form": "algebraic_number",
    "native_objects": [
        "recursive matrices over Q(s), where s^2=-3",
        "multicirculant quaternary unit Hadamard matrix",
        "exact unit diagonal phases",
    ],
    "verification_operations": [
        "exact quadratic-ring multiplication",
        "integer exponentiation",
        "primitive linear-polynomial evaluation",
        "exact rational interval comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "Character eigenvalues split into zero, quadratic-residue, and "
        "nonresidue types, collapsing an exponential tensor spectrum to a "
        "closed determinant formula."
    ),
    "hardness_basis": (
        "Track B: the Section 4 tensor-character determinant algorithm is "
        "O(n*3^n), measured at the shipping preset as 1,703 exact "
        "quadratic-ring steps (about 0.0006 seconds for one machine run); the "
        "character-type collapse needs at most 71 exact operations, whereas "
        "carrying out 1,703 exact steps is not "
        "mechanically realistic without tools."
    ),
    "max_answer_tokens": 287,
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
    "demo": {"n": 1, "q": 3, "phase_terms": 1, "phase_bound": 5},
    "easy": {"n": 5, "q": 3, "phase_terms": 2, "phase_bound": 20},
    "medium": {"n": 5, "q": 3, "phase_terms": 4, "phase_bound": 35},
    "hard": {"n": 5, "q": 3, "phase_terms": 6, "phase_bound": 50},
}

CERTIFICATE_LANGUAGE = {
    "description": (
        "A primitive degree-one integer minimal polynomial [c0,c1] with "
        "c1>0 and root T in the instance range -B<=T<=B, together with the "
        "canonical open rational interval (T-1/2,T+1/2)."
    ),
    "bounds": {
        "degree": 1,
        "root_lower": "-B from the instance",
        "root_upper": "B from the instance",
        "interval_denominator": 2,
        "atomic_elements": 6,
    },
}

STRUCTURAL_HINT = (
    "The character eigenvalues split by whether each frequency is zero, a "
    "quadratic residue, or a nonresidue."
)
PLACEBO_HINT = (
    "The indexing and sign conventions in the recursive matrices should be "
    "handled consistently throughout the exact calculation."
)

NOTES = """
Definition and construction: Section 2, Theorem 2.6 gives the exact amicable
matrix identity, and Section 3, equation (3.1), defines J_m and A_m.  Section
3.1 proves that the Paley/Jacobsthal choice is multicirculant.  Section 4 puts
the matrices in the tensor association scheme and supplies the three character
types used here.

Step-0 complexity decision: the paper's recursion directly constructs the
Hadamard matrix, so merely asking for that matrix would fail Track A.  This is
therefore explicitly Track B.  A direct tensor-character evaluation uses
3^n characters and n updates per character (1,703 exact ring steps at the
shipping settings).
Pairing the equally numerous residue and nonresidue character types yields the
closed determinant formula used by the intended route (at most 71 exact
operations at shipping size).

Easy regimes: equation (3.1) makes individual entries directly computable, and
Section 4 makes the complete spectrum mechanically computable.  The task does
not claim complexity-theoretic hardness.  It tests whether the solver sees the
character-type symmetry before attempting the mechanical spectrum product.

Adversaries: exact unit phases, singleton locations, and affine coordinate maps
are all sampled independently.  Ignoring phases, multiplying only their real
parts, selecting a conspicuous phase, random bounded certificates, and treating
the recursion as a Kronecker power all fail.  The exact tensor-character
algorithm succeeds, as Track B requires, and is reported separately.
""".strip()


# Elements a+b*s are pairs (a,b), with s^2=-q.
def _pair_add(x, y):
    return (x[0] + y[0], x[1] + y[1])


def _pair_neg(x):
    return (-x[0], -x[1])


def _pair_mul(x, y, q):
    return (x[0] * y[0] - q * x[1] * y[1],
            x[0] * y[1] + x[1] * y[0])


def _pair_s_mul(x, q):
    return (-q * x[1], x[0])


def _pair_pow(x, exponent, q):
    out = (1, 0)
    base = x
    e = exponent
    while e:
        if e & 1:
            out = _pair_mul(out, base, q)
        base = _pair_mul(base, base, q)
        e >>= 1
    return out


def _legendre(a, q):
    a %= q
    if a == 0:
        return 0
    r = pow(a, (q - 1) // 2, q)
    return 1 if r == 1 else -1


def _is_prime(q):
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


def _permutation_sign(perm):
    inversions = sum(perm[i] > perm[j]
                     for i in range(len(perm))
                     for j in range(i + 1, len(perm)))
    return -1 if inversions & 1 else 1


def _map_sign(mapping, q):
    # For q == 3 mod 4, a coordinate transposition and a nonsquare scaling
    # each induce an odd permutation of F_q^m; translations are even.
    sign = _permutation_sign(mapping["perm"])
    for scale in mapping["scale"]:
        sign *= _legendre(scale, q)
    return sign


def _random_map(m, q, rng):
    perm = list(range(m))
    rng.shuffle(perm)
    return {
        "perm": perm,
        "scale": [rng.randrange(1, q) for _ in range(m)],
        "shift": [rng.randrange(q) for _ in range(m)],
    }


def _apply_map(mapping, point, q):
    return [
        (mapping["scale"][j] * point[mapping["perm"][j]]
         + mapping["shift"][j]) % q
        for j in range(len(point))
    ]


def _compose_maps(first, second, q):
    """Return first o second for monomial affine coordinate maps."""
    m = len(first["perm"])
    perm, scale, shift = [], [], []
    for j in range(m):
        k = first["perm"][j]
        perm.append(second["perm"][k])
        scale.append((first["scale"][j] * second["scale"][k]) % q)
        shift.append((first["scale"][j] * second["shift"][k]
                      + first["shift"][j]) % q)
    return {"perm": perm, "scale": scale, "shift": shift}


def _inverse_map(mapping, q):
    m = len(mapping["perm"])
    perm = [0] * m
    scale = [0] * m
    shift = [0] * m
    for j, k in enumerate(mapping["perm"]):
        inv = pow(mapping["scale"][j], -1, q)
        perm[k] = j
        scale[k] = inv
        shift[k] = (-inv * mapping["shift"][j]) % q
    return {"perm": perm, "scale": scale, "shift": shift}


def _phase_triple(q, u, orientation):
    # (u^2-q + 2u*s)/(u^2+q) has norm one for s^2=-q.
    a, b, c = u * u - q, orientation * 2 * u, u * u + q
    g = math.gcd(math.gcd(abs(a), abs(b)), c)
    return [a // g, b // g, c // g]


def _base_determinant(q, m):
    """det(J_m+s*A_m) as an integer pair in Z[s], s^2=-q.

    Character splitting in the tensor scheme gives

      (-1)^ceil(m/2) q^floor(m q^m/2) (q+1)^((q^m-1)/2)
      times (q+s) for odd m and (1+s) for even m.
    """
    order = q ** m
    sign = -1 if ((m + 1) // 2) & 1 else 1
    scalar = (sign * pow(q, (m * order) // 2)
              * pow(q + 1, (order - 1) // 2))
    return (scalar * (q if m & 1 else 1), scalar)


def _phase_numerator_product(inst):
    out = (1, 0)
    q = inst["q"]
    for term in inst["phases"]:
        a, b, _ = term["phase"]
        out = _pair_mul(out, (a, b), q)
    return out


def _total_map_sign(inst):
    return (_map_sign(inst["row_map"], inst["q"])
            * _map_sign(inst["column_map"], inst["q"]))


@functools.lru_cache(maxsize=512)
def _target_cached(q, m, row_map_blob, column_map_blob, phases_blob):
    holder = {
        "q": q,
        "m": m,
        "row_map": json.loads(row_map_blob),
        "column_map": json.loads(column_map_blob),
        "phases": json.loads(phases_blob),
    }
    base = _base_determinant(q, m)
    numerator = _phase_numerator_product(holder)
    transformed = _pair_mul(base, numerator, q)
    return _total_map_sign(holder) * transformed[0]


def _target(inst):
    compact = lambda x: json.dumps(x, sort_keys=True, separators=(",", ":"))
    return _target_cached(
        inst["q"], inst["m"], compact(inst["row_map"]),
        compact(inst["column_map"]), compact(inst["phases"]),
    )


def _candidate_bound(inst):
    q = inst["q"]
    d0, d1 = _base_determinant(q, inst["m"])
    bound = abs(d0) + q * abs(d1)
    for term in inst["phases"]:
        a, b, _ = term["phase"]
        bound *= abs(a) + q * abs(b)
    return bound


def _answer_for_integer(value):
    return {
        "minpoly": [-value, 1],
        "interval": [[2 * value - 1, 2], [2 * value + 1, 2]],
    }


def make_instance(n, seed=0, q=3, phase_terms=3, phase_bound=50, **params):
    """Construct an instance and its certificate from the determinant identity."""
    if not isinstance(n, int) or n < 1:
        raise ValueError("n must be a positive recursion depth")
    if not isinstance(q, int) or not _is_prime(q) or q % 4 != 3:
        raise ValueError("q must be a prime congruent to 3 modulo 4")
    if not isinstance(phase_terms, int) or not 1 <= phase_terms <= 12:
        raise ValueError("phase_terms must lie in 1..12")
    if not isinstance(phase_bound, int) or phase_bound < 2:
        raise ValueError("phase_bound must be at least 2")

    rng = random.Random(seed)
    row_map = _random_map(n, q, rng)
    column_map = _random_map(n, q, rng)
    phases = []
    for _ in range(phase_terms):
        side = "row" if rng.randrange(2) == 0 else "column"
        position = [rng.randrange(q) for _ in range(n)]
        u = rng.randint(2, phase_bound)
        orientation = -1 if rng.randrange(2) else 1
        phases.append({
            "side": side,
            "position": position,
            "phase": _phase_triple(q, u, orientation),
        })

    inst = {
        "q": q,
        "m": n,
        "order": q ** n,
        "row_map": row_map,
        "column_map": column_map,
        "phases": phases,
    }
    inst["candidate_bound"] = _candidate_bound(inst)
    value = _target(inst)
    # A zero real part would make a conspicuously easy numeric instance.  The
    # deterministic fallback changes only the last phase orientation.
    if value == 0:
        phases[-1]["phase"][1] *= -1
        value = _target(inst)
        if value == 0:
            raise AssertionError("unexpected zero determinant real part")
    inst["answer"] = _answer_for_integer(value)
    return inst


def _format_map(mapping):
    return json.dumps(mapping, separators=(",", ":"))


def render(inst):
    q, m, order = inst["q"], inst["m"], inst["order"]
    phase_lines = []
    for k, term in enumerate(inst["phases"], 1):
        a, b, c = term["phase"]
        phase_lines.append(
            f"  {k}. {term['side']} {term['position']}: "
            f"({a} + ({b})*s)/{c}"
        )
    text = f"""Exact determinant certificate for a recursive quaternary matrix

All arithmetic is exact.  Let q={q}, m={m}, N=q^m={order}, and let s denote
the complex number i*sqrt(q), so s^2=-q and conjugation sends s to -s.

Rows and columns are indexed by vectors in F_q^m, represented as length-m
lists with entries 0,...,q-1.  Define the q by q Jacobsthal matrix Q by
Q[u,v]=chi(u-v), where chi(0)=0, chi(t)=1 when nonzero t is a square modulo q,
and chi(t)=-1 otherwise.  Let J_q be the all-ones q by q matrix and I_q the
identity.  Starting with the 1 by 1 matrices J_0=A_0=[1], recursively define

  J_r = J_q tensor A_(r-1)
  A_r = I_q tensor J_(r-1) + Q tensor A_(r-1).

Set K=J_m+s*A_m.  (The paper's unit Hadamard matrix is K/sqrt(q+1).)

An affine coordinate map f below means
  f(x)[j] = scale[j]*x[perm[j]] + shift[j] (mod q),
with 0-based j and 0-based coordinates.  The row and column maps are

  row map:    {_format_map(inst['row_map'])}
  column map: {_format_map(inst['column_map'])}

Begin with row multipliers r(x)=1 and column multipliers c(y)=1.  Apply every
listed phase: multiply r(position) or c(position), according to its side, by
the displayed exact number.  Repeated positions are allowed and their factors
multiply.  Every displayed phase (a+b*s)/d has norm one.

Phase list:
{chr(10).join(phase_lines)}

The exact N by N matrix in this problem is

  M[x,y] = r(x) * K[row_map(x), column_map(y)] * c(y).

Let S be the product of the positive denominators d in the phase list.  Your
target is the integer

  T = S * Re(det(M)).

Return an algebraic-number certificate for T.  The certificate language is:

* `minpoly` is the primitive degree-one integer polynomial [c0,c1], in
  ascending coefficient order, with c1>0 and root T.  Thus c0+c1*T=0.
* `interval` is the canonical OPEN isolating interval
  [[2*T-1,2],[2*T+1,2]], with each rational encoded [numerator,denominator].
* The promised bound is -B <= T <= B, inclusively, for
  B={inst['candidate_bound']}.

Give your final answer inside <answer></answer> tags as one JSON object with
exactly the keys `minpoly` and `interval`.
Example: <answer>{{"minpoly":[0,1],"interval":[[-1,2],[1,2]]}}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


def parse_answer(text):
    if not isinstance(text, str):
        return None
    bodies = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text,
                        flags=re.IGNORECASE | re.DOTALL)
    candidates = list(reversed(bodies)) if bodies else [text]
    decoder = json.JSONDecoder()
    for body in candidates:
        cleaned = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", body.strip(),
                         flags=re.IGNORECASE | re.DOTALL)
        starts = [i for i, ch in enumerate(cleaned) if ch == "{"]
        if not starts:
            starts = [0]
        for start in starts:
            try:
                obj, _ = decoder.raw_decode(cleaned[start:])
            except (ValueError, TypeError):
                continue
            if isinstance(obj, dict):
                return obj
    return None


def _is_plain_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def verify(inst, answer):
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if not answer:
        return False, "answer object is empty"
    if set(answer) != {"minpoly", "interval"}:
        return False, "answer must contain minpoly and interval only"

    poly = answer["minpoly"]
    if not isinstance(poly, list) or len(poly) != 2:
        return False, "minpoly must contain exactly two integers"
    if not all(_is_plain_int(x) for x in poly):
        return False, "minpoly coefficients must be integers"
    c0, c1 = poly
    if c1 <= 0:
        return False, "minpoly must have positive leading coefficient"
    if math.gcd(abs(c0), c1) != 1:
        return False, "minpoly must be primitive"
    if abs(c0) > inst["candidate_bound"] * c1:
        return False, "claimed root is outside certificate-language bound"

    interval = answer["interval"]
    if (not isinstance(interval, list) or len(interval) != 2
            or any(not isinstance(x, list) or len(x) != 2 for x in interval)):
        return False, "interval must contain exactly two rational endpoints"
    if not all(_is_plain_int(v) for endpoint in interval for v in endpoint):
        return False, "interval endpoint entries must be integers"
    (ln, ld), (un, ud) = interval
    if ld <= 0 or ud <= 0:
        return False, "interval denominators must be positive"
    if ln * ud >= un * ld:
        return False, "interval endpoints must be strictly increasing"

    target = _target(inst)
    if c0 + c1 * target != 0:
        return False, "minimal polynomial does not vanish at the target"
    expected_interval = [[2 * target - 1, 2], [2 * target + 1, 2]]
    if interval != expected_interval:
        return False, "interval is not the required canonical isolating interval"
    return True, "ok"


def random_candidate(inst, rng):
    value = rng.randint(-inst["candidate_bound"], inst["candidate_bound"])
    return _answer_for_integer(value)


def search_space(inst):
    return 2 * inst["candidate_bound"] + 1


def enumerate_all(inst):
    size = search_space(inst)
    if size > 100_000:
        return None
    hits = 0
    bound = inst["candidate_bound"]
    for value in range(-bound, bound + 1):
        if verify(inst, _answer_for_integer(value))[0]:
            hits += 1
    return hits


def canonical_key(inst):
    # Singleton positions and their ordering change under row/column relabelling.
    # The normalized phase product and the two affine permutation signs do not.
    invariant = {
        "q": inst["q"],
        "m": inst["m"],
        "map_sign": _total_map_sign(inst),
        "phase_numerator_product": list(_phase_numerator_product(inst)),
    }
    blob = json.dumps(invariant, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def escalate(params):
    # n=6 would still be mathematically harder, but its repeated exact integers
    # exceed the 2,000-character answer cap.  The assignments document that the
    # ladder already used fixed-answer-shape entropy axes as well as n.
    p = dict(params)
    p["phase_terms"] = min(12, int(p.get("phase_terms", 3)) + 1)
    p["phase_bound"] = int(p.get("phase_bound", 50)) * 2
    return "cap_bound"


def _spectral_determinant(q, m):
    """Mechanical tensor-character evaluation and its ring-step count."""
    det = (1, 0)
    steps = 0
    for frequency in itertools.product(range(q), repeat=m):
        j = (1, 0)
        a = (1, 0)
        for digit in frequency:
            old_j, old_a = j, a
            if digit == 0:
                j = (q * old_a[0], q * old_a[1])
                a = old_j
            else:
                ga = _pair_s_mul(old_a, q)
                if _legendre(digit, q) == 1:
                    ga = _pair_neg(ga)
                j = (0, 0)
                a = _pair_add(old_j, ga)
            steps += 1
        eigenvalue = _pair_add(j, _pair_s_mul(a, q))
        det = _pair_mul(det, eigenvalue, q)
        steps += 2
    return det, steps


def _spectral_target(inst):
    base, steps = _spectral_determinant(inst["q"], inst["m"])
    transformed = _pair_mul(base, _phase_numerator_product(inst), inst["q"])
    return _total_map_sign(inst) * transformed[0], steps + len(inst["phases"])


def _compact_operation_count(inst):
    q, m, order = inst["q"], inst["m"], inst["order"]
    e1 = (m * order) // 2
    e2 = (order - 1) // 2
    # Binary powers, phase pair-products, parity scans, and final checks.
    return (e1.bit_length() + e1.bit_count()
            + e2.bit_length() + e2.bit_count()
            + 5 * len(inst["phases"]) + 4 * m + 12)


def _relabel_instance(inst, relabel):
    """Conjugate external row/column labels by the same affine bijection."""
    out = copy.deepcopy(inst)
    q = inst["q"]
    inv = _inverse_map(relabel, q)
    out["row_map"] = _compose_maps(inst["row_map"], relabel, q)
    out["column_map"] = _compose_maps(inst["column_map"], relabel, q)
    for term in out["phases"]:
        term["position"] = _apply_map(inv, term["position"], q)
    out["candidate_bound"] = _candidate_bound(out)
    out["answer"] = copy.deepcopy(inst["answer"])
    return out


def _attack_values(inst):
    q = inst["q"]
    base = _base_determinant(q, inst["m"])
    sign = _total_map_sign(inst)
    phases = inst["phases"]
    denominator_product = math.prod(t["phase"][2] for t in phases)

    ignore_phases = sign * denominator_product * base[0]
    real_parts_only = sign * base[0] * math.prod(t["phase"][0] for t in phases)

    conspicuous = max(phases,
                      key=lambda t: abs(t["phase"][1]) / t["phase"][2])
    a, b, _ = conspicuous["phase"]
    one_phase = sign * _pair_mul(base, (a, b), q)[0]

    first_level = _base_determinant(q, 1)
    tensor_guess = _pair_pow(first_level, inst["order"] // q, q)
    tensor_guess = sign * _pair_mul(
        tensor_guess, _phase_numerator_product(inst), q)[0]
    return {
        "outlier_largest_phase_only": one_phase,
        "greedy_ignore_unit_phases": ignore_phases,
        "greedy_multiply_real_parts": real_parts_only,
        "in_context_kronecker_power_ansatz": tensor_guess,
    }


def _answer_atoms(obj):
    if isinstance(obj, dict):
        return sum(_answer_atoms(v) for v in obj.values())
    if isinstance(obj, list):
        return sum(_answer_atoms(v) for v in obj)
    return 1


# Filled from the mandatory external oracle runs after hardening.  Keeping these
# as data makes selftest deterministic and prevents it from making network calls.
G9_MEASUREMENTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {
        "solved": 0,
        "attempts": 0,
        "status": "unmeasured: OpenRouter key total limit exceeded after timeout",
    },
    "hinted_verdict": "hardened",
}


def selftest():
    report = {}

    planted_checks = 0
    spectral_crosschecks = 0
    json_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            if not ok:
                raise AssertionError((preset, seed, why))
            planted_checks += 1
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                raise AssertionError("answer is not JSON-native")
            json_checks += 1
            spectral, _ = _spectral_target(inst)
            if spectral != _target(inst):
                raise AssertionError((preset, seed, "spectral mismatch"))
            spectral_crosschecks += 1
    # The shipping ladder uses q=3, but the public constructor accepts every
    # prime q == 3 (mod 4); cross-check two additional Paley regimes too.
    for q, depth in ((7, 2), (11, 1)):
        inst = make_instance(n=depth, q=q, phase_terms=2,
                             phase_bound=8, seed=q)
        ok, why = verify(inst, inst["answer"])
        if not ok or _spectral_target(inst)[0] != _target(inst):
            raise AssertionError((q, depth, why, "general-q crosscheck"))
        planted_checks += 1
        spectral_crosschecks += 1
        if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
            raise AssertionError("general-q answer is not JSON-native")
        json_checks += 1
    report["G1_planted_verifies"] = {
        "pass": True,
        "checks": planted_checks,
        "spectral_crosschecks": spectral_crosschecks,
        "json_native_checks": json_checks,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    good = shipping["answer"]
    corruptions = {}
    variants = {}
    variants["drop"] = {"minpoly": good["minpoly"]}
    swapped = copy.deepcopy(good)
    swapped["interval"] = list(reversed(swapped["interval"]))
    variants["swap"] = swapped
    duplicated = copy.deepcopy(good)
    duplicated["minpoly"].append(duplicated["minpoly"][-1])
    variants["duplicate"] = duplicated
    variants["empty"] = {}
    outside = _answer_for_integer(shipping["candidate_bound"] + 1)
    variants["out_of_range"] = outside
    for name, candidate in variants.items():
        ok, why = verify(shipping, candidate)
        if ok:
            raise AssertionError((name, "corruption accepted"))
        corruptions[name] = why
    if len(set(corruptions.values())) != len(corruptions):
        raise AssertionError("corruption reasons are not distinct")
    report["G2_rejects_corruption"] = {
        "pass": True, "cases": corruptions,
    }

    model_style = (
        "I used the tensor character classes.  My exact certificate is:\n"
        "```json\n<answer>" + json.dumps(good) + "</answer>\n```\n"
        "The endpoints are open."
    )
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == good,
        "model_style_response_parsed": parsed == good,
    }

    guess_rng = random.Random(0x170902873)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        candidate = random_candidate(shipping, guess_rng)
        if verify(shipping, candidate)[0]:
            guess_hits += 1
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_hits / guess_total,
        "certificate_space": search_space(shipping),
    }

    demo = make_instance(seed=9, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    t0 = time.perf_counter()
    ref_value, ref_steps = _spectral_target(shipping)
    ref_wall = time.perf_counter() - t0
    if ref_value != _target(shipping):
        raise AssertionError("reference algorithm failed")
    report["G5_density_and_baseline"] = {
        "pass": demo_count == 1 and guess_hits / guess_total < 1e-6,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_sampled_density": guess_hits / guess_total,
        "demo_exact_solution_count": demo_count,
        "demo_certificate_space": search_space(demo),
        "baseline_wall_seconds": ref_wall,
        "baseline_exact_ring_steps": ref_steps,
    }

    attack_seeds = list(range(800, 808))
    attack_results = {
        "outlier_largest_phase_only": {"successes": 0, "attempts": 0},
        "greedy_ignore_unit_phases": {"successes": 0, "attempts": 0},
        "greedy_multiply_real_parts": {"successes": 0, "attempts": 0},
        "in_context_kronecker_power_ansatz": {"successes": 0, "attempts": 0},
        "random_restart_256": {"successes": 0, "attempts": 0},
    }
    reference_successes = 0
    reference_steps = 0
    reference_start = time.perf_counter()
    for seed in attack_seeds:
        inst = make_instance(seed=seed,
                             **DIFFICULTY[SHIPPING_DIFFICULTY])
        for name, value in _attack_values(inst).items():
            ok = verify(inst, _answer_for_integer(value))[0]
            attack_results[name]["successes"] += int(ok)
            attack_results[name]["attempts"] += 1
        rrng = random.Random(seed ^ 0xBAD5EED)
        random_solved = False
        for _ in range(256):
            if verify(inst, random_candidate(inst, rrng))[0]:
                random_solved = True
                break
        attack_results["random_restart_256"]["successes"] += int(random_solved)
        attack_results["random_restart_256"]["attempts"] += 1
        ref, steps = _spectral_target(inst)
        reference_successes += int(ref == _target(inst))
        reference_steps = max(reference_steps, steps)
    reference_wall = time.perf_counter() - reference_start
    all_failed = all(v["successes"] == 0 for v in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == len(attack_seeds),
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "tensor-character eigenvalue product",
            "complexity": "O(n*3^n) exact quadratic-ring operations",
            "wall_clock_sec": reference_wall,
            "operations": reference_steps,
            "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
        },
    }

    doubled = make_instance(
        n=2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"],
        q=DIFFICULTY[SHIPPING_DIFFICULTY]["q"],
        phase_terms=DIFFICULTY[SHIPPING_DIFFICULTY]["phase_terms"],
        phase_bound=DIFFICULTY[SHIPPING_DIFFICULTY]["phase_bound"],
        seed=271828,
    )
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["order"] > shipping["order"],
        "shipping_depth": shipping["m"],
        "shipping_order": shipping["order"],
        "doubled_depth": doubled["m"],
        "doubled_order": doubled["order"],
    }

    invariant_checks = 0
    real_transform_checks = 0
    keys = []
    for seed in range(20):
        inst = make_instance(seed=20_000 + seed,
                             **DIFFICULTY[SHIPPING_DIFFICULTY])
        base_key = canonical_key(inst)
        keys.append(base_key)
        rrng = random.Random(90_000 + seed)
        relabel = _random_map(inst["m"], inst["q"], rrng)
        moved = _relabel_instance(inst, relabel)
        reordered = copy.deepcopy(inst)
        reordered["phases"].reverse()
        composed = _relabel_instance(reordered, relabel)
        for transformed in (moved, reordered, composed):
            if canonical_key(transformed) != base_key:
                raise AssertionError("canonical key changed under relabelling")
            invariant_checks += 1
            if not verify(transformed, inst["answer"])[0]:
                raise AssertionError("relabelling did not preserve the problem")
            real_transform_checks += 1
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": invariant_checks == 60 and real_transform_checks == 60
                and distinct == 20,
        "invariance_checks": invariant_checks,
        "problem_preserving_transform_checks": real_transform_checks,
        "unrelated_distinct": distinct,
        "unrelated_attempts": 20,
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(shipping["answer"])
    intended_ops = _compact_operation_count(shipping)
    arms = {
        k: dict(G9_MEASUREMENTS[k])
        for k in ("bare", "hinted", "placebo")
    }
    hint_delta = None
    if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]:
        hint_delta = (
            (arms["hinted"]["solved"] / arms["hinted"]["attempts"])
            - (arms["placebo"]["solved"] / arms["placebo"]["attempts"])
        )
    hinted_hardened = G9_MEASUREMENTS["hinted_verdict"] == "hardened"
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and intended_ops <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hint_delta,
        "hinted_verdict": G9_MEASUREMENTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["all_passed"] = all(
        v.get("pass") is True for k, v in report.items()
        if k.startswith("G") and isinstance(v, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2))
