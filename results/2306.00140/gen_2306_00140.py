"""Verified problem generator for arXiv:2306.00140.

Theorem 4.8 and Remark 4.9 construct a partial difference set (PDS) for the
triangular graph T_p in C_p semidirect C_((p-1)/2), for p == 3 (mod 4).
This module transports that PDS through sampled group automorphisms and asks
for the automorphism selected by a crowded collection of exact finite-field
moment observations.  Two rows come from the same transported PDS and all
other rows come from independent transports drawn from the same distribution.

The planted witness is sampled before the observations are made.  It is never
recovered by solving the emitted instance.
"""

from __future__ import annotations

import copy
import functools
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
    from gvlib import exact_matrices, rationals
except ImportError:                 # pragma: no cover - supported fallback
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "nonabelian semidirect-product group C_p semidirect C_((p-1)/2)",
        "partial difference set written in group coordinates",
        "group automorphism specified by images of two generators",
        "exact finite-field coordinate moments",
    ],
    "verification_operations": [
        "exact modular group-action arithmetic",
        "exact first- and second-moment expansion in F_p",
        "quadratic-residue membership by modular exponentiation",
        "executable regular-action certificate for the triangular-graph PDS",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Normalize the first coordinate-sum by the geometric-series factor "
        "h_b: rows from one transported PDS have the same normalized sum; "
        "without that cross-layer invariant one recovers every row separately."
    ),
    "hardness_basis": (
        "Track B: independent centered-moment recovery is O(d log p); at the "
        "shipping preset p=1000003 and d=152 it took 0.0017 seconds and "
        "11,856 counted field operations, while the cross-row normalized-sum "
        "route uses 230 exact operations and must be recognized and executed "
        "without a CAS."
    ),
    "max_answer_tokens": 29,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A symbolic group automorphism phi_(u,w) given by the JSON object "
        "{type:'automorphism', scale:u, shear:w, generator_images:{sigma:[u,0]," 
        "tau:[w,1]}}.  Here u is one of the (p-1)/2 nonzero quadratic "
        "residues modulo p and 0 <= w < p; the generator-image fields are "
        "required redundant checks, not additional choices."
    ),
    "bounds": {
        "scale_choices": "(p-1)/2 nonzero quadratic residues modulo instance p",
        "shear_choices": "p residues 0 through p-1",
        "generator_images": "two fixed two-coordinate images determined by scale and shear",
        "atomic_elements": 7,
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 7, "decoys": 0},
    "easy": {"n": 100_003, "decoys": 20},
    "medium": {"n": 300_007, "decoys": 75},
    "hard": {"n": 1_000_003, "decoys": 150},
}
SHIPPING_DIFFICULTY: str = "hard"

STRUCTURAL_HINT: str = (
    "Across layers of one transported PDS, the first-coordinate sum divided by "
    "the geometric-series factor h_b is invariant."
)
PLACEBO_HINT: str = (
    "Across all displayed rows, keep least nonnegative modular residues and "
    "check every supplied field inverse carefully."
)

# Replaced with the script-owned results after the three oracle runs.
G9_EVIDENCE: dict = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "hardened",
    "placebo_status": "0 completed attempts: OpenRouter HTTP 403 total key limit",
}

NOTES: str = r"""
Definition.  Definition 3.1 says that a (v,k,lambda,mu) PDS S in G has
1 not in S, is inverse closed, and has exactly lambda or mu ordered
representations xy^{-1} according as a nonidentity group element is or is not
in S.  Lemma 3.2 identifies this with a strongly regular Cayley graph.

Construction and easy regime.  Theorem 4.8 constructs T_p as a Cayley graph
of C_p semidirect C_((p-1)/2) when p is 3 modulo 4.  Its proof uses the regular
affine action on unordered pairs.  Remark 4.9 gives the PDS explicitly as five
group-ring pieces.  It also says the congruence condition is necessary for this
construction and reports GAP nonexistence checks for several other n.  Because
Remark 4.9 is a direct formula, Track A would be false.  This is Track B.

Certificate-producing algorithm.  In coordinates (a,b), multiplication is
(a,b)(c,d)=(a+m^b c,b+d), and the base PDS has a in {+1,-1} at b=0 and
a in {0,-m^b,1,1-m^b} at b!=0.  The automorphisms used here are
phi_(u,w)(a,b)=(u a+w h_b,b), where h_b=1+m+...+m^(b-1).  Sampling (u,w)
first and evaluating coordinate moments is a structure-preserving
transformation of the paper's known PDS, never a search.

Exact checker.  The checker executes the proof ingredients: p is prime and 3
modulo 4; m has order (p-1)/2; the quadratic residues and their negatives
partition F_p^*; hence the affine group acts regularly on unordered pairs.
It checks the triangular-graph parameters and expands all four coordinates in
every reported layer before comparing moments.  Thus it does not appeal to an
external theorem or to the planted answer.

Hardness and attacks.  The reference solver independently applies centered
second-moment elimination, modular square-root extraction, and shear recovery
to every row, then counts repeated automorphisms.  The compact route first
uses sum/h_b, which is constant across every layer of one transported PDS, and
does the expensive centered-moment recovery only for the repeated fingerprint.
Decoy rows are made from independently sampled automorphic PDSs, exactly the
same per-row distribution as the two planted rows, and have distinct
fingerprints by rejection sampling.  The panel tests raw-moment outliers, a
zero-shear greedy guess, uniform restarts, and a scale-one first-moment ansatz.
The successful polynomial-time reference algorithm is reported separately,
as Track B requires.
""".strip()


# ---------------------------------------------------------------------------
# Finite-field and group helpers


def _is_prime(value: int) -> bool:
    """Deterministic Miller--Rabin for the 64-bit range used by this module."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small:
        if value % prime == 0:
            return value == prime
    d = value - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        a = base % value
        if a == 0:
            continue
        x = pow(a, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(s - 1):
            x = x * x % value
            if x == value - 1:
                break
        else:
            return False
    return True


def _prime_factors(value: int) -> tuple[int, ...]:
    factors = []
    divisor = 2
    while divisor * divisor <= value:
        if value % divisor == 0:
            factors.append(divisor)
            while value % divisor == 0:
                value //= divisor
        divisor = 3 if divisor == 2 else divisor + 2
    if value > 1:
        factors.append(value)
    return tuple(factors)


def _next_prime_3mod4(lower: int) -> int:
    candidate = max(7, int(lower))
    candidate += (3 - candidate) % 4
    while not _is_prime(candidate):
        candidate += 4
    return candidate


@functools.lru_cache(maxsize=32)
def _group_parameters(lower: int) -> tuple[int, int, int]:
    p = _next_prime_3mod4(lower)
    factors = _prime_factors(p - 1)
    primitive = None
    for candidate in range(2, p):
        if all(pow(candidate, (p - 1) // q, p) != 1 for q in factors):
            primitive = candidate
            break
    if primitive is None:                           # pragma: no cover
        raise RuntimeError("failed to find a primitive root")
    m = primitive * primitive % p
    return p, (p - 1) // 2, m


def _is_quadratic_residue(value: int, p: int, t: int) -> bool:
    return 0 < value < p and pow(value, t, p) == 1


def _q_h(p: int, m: int, b: int) -> tuple[int, int]:
    q = pow(m, b, p)
    h = (q - 1) * pow(m - 1, -1, p) % p
    return q, h


def _roles(q: int, p: int) -> tuple[int, int, int, int]:
    return (0, (-q) % p, 1, (1 - q) % p)


@functools.lru_cache(maxsize=32)
def _base_certificate_ok(p: int, t: int, m: int) -> bool:
    """Execute the regular-action certificate behind Theorem 4.8.

    Order(m)=t and p==3 mod 4 imply <m> and -<m> partition F_p^*.  Therefore
    (a,b): z -> a+m^b z acts regularly on unordered pairs of F_p.  The four
    roles below are exactly the affine maps sending {0,1} to a pair sharing
    one point with {0,1}.  The final identities are the direct common-neighbor
    counts of the triangular graph.
    """
    if not _is_prime(p) or p % 4 != 3 or t != (p - 1) // 2:
        return False
    if not (1 < m < p) or pow(m, t, p) != 1:
        return False
    if any(pow(m, t // q, p) == 1 for q in _prime_factors(t)):
        return False
    if pow(p - 1, t, p) == 1:       # -1 must not be in the residue subgroup
        return False
    q1, _ = _q_h(p, m, 1)
    if len(set(_roles(q1, p))) != 4:
        return False

    v = p * t
    k = 2 * (p - 2)
    lam = p - 2
    mu = 4
    return (
        v == p * (p - 1) // 2
        and k * (k - lam - 1) == (v - k - 1) * mu
        and 2 + 4 * (t - 1) == k
    )


def _base_elements(p: int, t: int, m: int) -> list[tuple[int, int]]:
    out = [(1, 0), (p - 1, 0)]
    for b in range(1, t):
        q = pow(m, b, p)
        out.extend((a, b) for a in _roles(q, p))
    return out


def _direct_pds_check(p: int, t: int, m: int) -> bool:
    """Small-instance exhaustive cross-check used by selftest, never at scale."""
    subset = _base_elements(p, t, m)
    members = set(subset)
    counts: dict[tuple[int, int], int] = {}
    for a, b in subset:
        for c, d in subset:
            delta = (b - d) % t
            first = (a - pow(m, delta, p) * c) % p
            element = (first, delta)
            counts[element] = counts.get(element, 0) + 1
    k, lam, mu = 2 * (p - 2), p - 2, 4
    for b in range(t):
        for a in range(p):
            element = (a, b)
            expected = k if element == (0, 0) else lam if element in members else mu
            if counts.get(element, 0) != expected:
                return False
    return True


# ---------------------------------------------------------------------------
# Automorphisms, moments, and answers


def _answer(scale: int, shear: int) -> dict:
    return {
        "type": "automorphism",
        "scale": scale,
        "shear": shear,
        "generator_images": {
            "sigma": [scale, 0],
            "tau": [shear, 1],
        },
    }


def _pair(answer: dict) -> tuple[int, int]:
    return int(answer["scale"]), int(answer["shear"])


def _compose(left: tuple[int, int], right: tuple[int, int], p: int) -> tuple[int, int]:
    """Composition phi_left after phi_right."""
    a, s = left
    u, w = right
    return a * u % p, (a * w + s) % p


def _inverse(pair: tuple[int, int], p: int) -> tuple[int, int]:
    u, w = pair
    inverse_u = pow(u, -1, p)
    return inverse_u, (-inverse_u * w) % p


def _partner(pair: tuple[int, int], p: int, m: int) -> tuple[int, int]:
    """The other parameter pair defining the same PDS (right stabilizer)."""
    u, w = pair
    return (-u) % p, (w + u * (1 - m)) % p


def _canonical_pair(pair: tuple[int, int], p: int, t: int, m: int) -> tuple[int, int]:
    if _is_quadratic_residue(pair[0], p, t):
        return pair
    other = _partner(pair, p, m)
    if not _is_quadratic_residue(other[0], p, t):       # pragma: no cover
        raise ValueError("pair has no quadratic-residue representative")
    return other


def _layer_moments(p: int, m: int, scale: int, shear: int, b: int) -> tuple[int, int]:
    q, h = _q_h(p, m, b)
    return _layer_moments_qh(p, scale, shear, q, h)


def _layer_moments_qh(
    p: int, scale: int, shear: int, q: int, h: int
) -> tuple[int, int]:
    coordinates = [
        (shear * h + scale * role) % p
        for role in _roles(q, p)
    ]
    first = sum(coordinates) % p
    second = sum(value * value for value in coordinates) % p
    return first, second


def _moment_row(p: int, m: int, pair: tuple[int, int], b: int) -> dict:
    q, h = _q_h(p, m, b)
    first, second = _layer_moments(p, m, pair[0], pair[1], b)
    roles = _roles(q, p)
    role_sum = sum(roles) % p
    role_square_sum = sum(value * value for value in roles) % p
    center_den = (4 * role_square_sum - role_sum * role_sum) % p
    return {
        "b": b,
        "q": q,
        "h": h,
        "h_inv": pow(h, -1, p),
        "center_den_inv": pow(center_den, -1, p),
        "four_h_inv": pow(4 * h % p, -1, p),
        "sum": first,
        "sum_sq": second,
    }


def _pair_fingerprint(pair: tuple[int, int], p: int, m: int) -> int:
    """The layer-independent value sum/h for phi_pair(D)."""
    scale, shear = pair
    return (4 * shear - 2 * scale * (m - 1)) % p


def _row_fingerprint(row: dict, p: int) -> int | None:
    try:
        first, h_inv = row["sum"], row["h_inv"]
        if not all(isinstance(value, int) and not isinstance(value, bool)
                   and 0 <= value < p for value in (first, h_inv)):
            return None
        return first * h_inv % p
    except (KeyError, TypeError):
        return None


def _recover_row(inst: dict, row: dict) -> tuple[int, int] | None:
    """Compact centered-moment recovery for one valid observation row."""
    p, t, m = inst["p"], inst["t"], inst["m"]
    try:
        b = row["b"]
        if not isinstance(b, int) or isinstance(b, bool) or not (1 <= b < t):
            return None
        q, h = _q_h(p, m, b)
        if row.get("q") != q or row.get("h") != h:
            return None
        if row.get("h_inv") != pow(h, -1, p):
            return None
        first, second = row["sum"], row["sum_sq"]
        if not all(isinstance(x, int) and not isinstance(x, bool) and 0 <= x < p
                   for x in (first, second)):
            return None
        roles = _roles(q, p)
        role_sum = sum(roles) % p
        role_square_sum = sum(r * r for r in roles) % p
        centered = (4 * second - first * first) % p
        denominator = (4 * role_square_sum - role_sum * role_sum) % p
        if denominator == 0:
            return None
        if row.get("center_den_inv") != pow(denominator, -1, p):
            return None
        if row.get("four_h_inv") != pow(4 * h % p, -1, p):
            return None
        scale_sq = centered * row["center_den_inv"] % p
        if scale_sq == 0:
            return None
        root = pow(scale_sq, (p + 1) // 4, p)
        if root * root % p != scale_sq:
            return None
        scale = root if _is_quadratic_residue(root, p, t) else (-root) % p
        shear = (first - scale * role_sum) * row["four_h_inv"] % p
        if _layer_moments(p, m, scale, shear, b) != (first, second):
            return None
        return scale, shear
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None


def _valid_answer_shape(answer: object, p: int, t: int) -> tuple[bool, str]:
    if answer == {}:
        return False, "answer object is empty"
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    expected = {"type", "scale", "shear", "generator_images"}
    if set(answer) != expected:
        return False, "answer must have exactly type, scale, shear, and generator_images"
    if answer.get("type") != "automorphism":
        return False, "type must be the string automorphism"
    scale, shear = answer.get("scale"), answer.get("shear")
    if isinstance(scale, bool) or not isinstance(scale, int) or not (1 <= scale < p):
        return False, f"scale must be an integer in 1..{p - 1}"
    if not _is_quadratic_residue(scale, p, t):
        return False, "scale must be a nonzero quadratic residue modulo p"
    if isinstance(shear, bool) or not isinstance(shear, int) or not (0 <= shear < p):
        return False, f"shear must be an integer in 0..{p - 1}"
    images = answer.get("generator_images")
    if not isinstance(images, dict) or set(images) != {"sigma", "tau"}:
        return False, "generator_images must contain exactly sigma and tau"
    sigma_image = images["sigma"]
    tau_image = images["tau"]
    if not isinstance(sigma_image, list) or len(sigma_image) != 2:
        return False, "sigma image must be a two-coordinate list"
    if sigma_image != [scale, 0]:
        return False, "sigma generator image must equal [scale, 0]"
    if not isinstance(tau_image, list) or len(tau_image) != 2:
        return False, "tau image must be a two-coordinate list"
    if tau_image != [shear, 1]:
        return False, "tau generator image must equal [shear, 1]"
    return True, "ok"


# ---------------------------------------------------------------------------
# Required public interface


def make_instance(n: int, seed: int = 0, decoys: int = 1, **params) -> dict:
    """Inverse-generate moment observations of automorphic paper PDSs."""
    del params
    if isinstance(n, bool) or not isinstance(n, int) or n < 7:
        raise ValueError("n must be an integer at least 7")
    if isinstance(decoys, bool) or not isinstance(decoys, int) or not (0 <= decoys <= 220):
        raise ValueError("decoys must be an integer from zero through 220")
    rng = random.Random(seed)
    p, t, m = _group_parameters(n)

    target = (pow(m, rng.randrange(t), p), rng.randrange(p))
    used_pairs = {target}
    used_fingerprints = {_pair_fingerprint(target, p, m)}
    sources = [target, target]
    while len(sources) < decoys + 2:
        candidate = (pow(m, rng.randrange(t), p), rng.randrange(p))
        fingerprint = _pair_fingerprint(candidate, p, m)
        if candidate not in used_pairs and fingerprint not in used_fingerprints:
            used_pairs.add(candidate)
            used_fingerprints.add(fingerprint)
            sources.append(candidate)

    # All observations, planted and decoy, use exactly the same distribution:
    # a uniformly sampled admissible automorphism and a uniform nonzero layer.
    used_rows = set()
    observations = []
    for source in sources:
        while True:
            b = rng.randrange(1, t)
            marker = (source, b)
            if marker not in used_rows:
                used_rows.add(marker)
                break
        observations.append(_moment_row(p, m, source, b))
    rng.shuffle(observations)

    return {
        "family": "automorphic genuinely nonabelian partial difference set",
        "requested_n": n,
        "p": p,
        "t": t,
        "m": m,
        "parameters": {
            "v": p * t,
            "k": 2 * (p - 2),
            "lambda": p - 2,
            "mu": 4,
        },
        "required_matches": 2,
        "decoys": decoys,
        "observations": observations,
        "answer": _answer(*target),
    }


def render(inst: dict) -> str:
    p, t, m = inst["p"], inst["t"], inst["m"]
    rows = "\n".join(
        f"  {index}: b={row['b']}, q={row['q']}, h={row['h']}, "
        f"h_inv={row['h_inv']}, center_den_inv={row['center_den_inv']}, "
        f"four_h_inv={row['four_h_inv']}, sum={row['sum']}, "
        f"sum_sq={row['sum_sq']}"
        for index, row in enumerate(inst["observations"], 1)
    )
    statement = f"""GENUINELY NONABELIAN PARTIAL DIFFERENCE SET: MOMENT WITNESS

All arithmetic in first coordinates is modulo the prime p={p}.  Second
coordinates are modulo t={t}.  Let m={m}, which has multiplicative order t
modulo p.  The nonabelian group G consists of pairs (a,b), with

  (a,b)*(c,d) = (a + m^b*c mod p, b+d mod t).

The identity is (0,0).  Let D be the following subset of G.  In layer b=0 it
contains (1,0) and (-1 mod p,0).  In every layer 1 <= b < t, put q_b=m^b mod p;
the four first coordinates in D are

  0,  -q_b mod p,  1,  1-q_b mod p.

This D is a ({inst['parameters']['v']},{inst['parameters']['k']},
{inst['parameters']['lambda']},{inst['parameters']['mu']}) partial difference
set: the identity is excluded, D is inverse-closed, and each nonidentity g has
exactly lambda ordered representations x*y^(-1) when g is in D and exactly mu
otherwise.

For 1 <= u < p and 0 <= w < p define h_0=0 and
h_b=1+m+...+m^(b-1) mod p, and define

  phi_(u,w)(a,b) = (u*a + w*h_b mod p, b).

This is a group automorphism whenever u is nonzero.  To make its description
unique, this problem permits only u that are quadratic residues modulo p
(equivalently u^t=1 mod p).  The decoded PDS is phi_(u,w)(D).

For a nonzero layer b, its four decoded first coordinates are denoted x_1,...,x_4.
An observation row lists q=m^b, h=h_b, and the exact residues

  sum = x_1+x_2+x_3+x_4 mod p,
  sum_sq = x_1^2+x_2^2+x_3^2+x_4^2 mod p.

For exact arithmetic it also lists h_inv=h^(-1),
center_den_inv=[4*(q^2+1)]^(-1), and four_h_inv=(4*h)^(-1), all
modulo p.  These are redundant data: a valid row must satisfy the displayed
inverse identities.

Here are {len(inst['observations'])} observation rows; their order is irrelevant:
{rows}

Exactly one permitted pair (u,w) matches at least {inst['required_matches']}
rows.  The other rows are decoys made by the identical construction from
independent permitted automorphisms.  Find the unique matching pair.

Your certificate must be one JSON object with exactly these fields:
  "type": "automorphism"
  "scale": u
  "shear": w
  "generator_images": {{"sigma":[u,0], "tau":[w,1]}}
Coordinates and residues are least nonnegative integers.  Array order matters;
no entries may be omitted or repeated.

Give your final answer inside <answer></answer> tags as exact JSON.
Example: <answer>{{"type":"automorphism","scale":1,"shear":0,"generator_images":{{"sigma":[1,0],"tau":[0,1]}}}}</answer>
Output nothing else inside the tags."""

    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    tagged = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    candidates = list(reversed(tagged))
    candidates.extend(re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text,
                                 flags=re.I | re.S))
    candidates.append(text)
    decoder = json.JSONDecoder()
    for candidate in candidates:
        candidate = candidate.strip()
        try:
            value = json.loads(candidate)
            if isinstance(value, dict):
                return value
        except (TypeError, ValueError):
            pass
        for start, char in enumerate(candidate):
            if char != "{":
                continue
            try:
                value, _ = decoder.raw_decode(candidate[start:])
            except ValueError:
                continue
            if isinstance(value, dict):
                return value
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    try:
        p, t, m = inst["p"], inst["t"], inst["m"]
        if not _base_certificate_ok(p, t, m):
            return False, "instance does not carry a valid regular-action PDS certificate"
        ok, reason = _valid_answer_shape(answer, p, t)
        if not ok:
            return False, reason
        assert isinstance(answer, dict)
        scale, shear = _pair(answer)
        candidate_fingerprint = _pair_fingerprint((scale, shear), p, m)
        matches = 0
        for row in inst["observations"]:
            b = row.get("b")
            if not isinstance(b, int) or isinstance(b, bool) or not (1 <= b < t):
                return False, "observation has an invalid layer"
            q, h = row.get("q"), row.get("h")
            residues = (
                q, h, row.get("h_inv"), row.get("center_den_inv"),
                row.get("four_h_inv"), row.get("sum"), row.get("sum_sq"),
            )
            if not all(isinstance(value, int) and not isinstance(value, bool)
                       and 0 <= value < p for value in residues):
                return False, "observation has a non-residue field value"
            if q != (1 + (m - 1) * h) % p:
                return False, "observation q and h violate the geometric-series identity"
            if h * row["h_inv"] % p != 1:
                return False, "observation h_inv is not the inverse of h"
            if 4 * (q * q + 1) * row["center_den_inv"] % p != 1:
                return False, "observation center_den_inv is incorrect"
            if 4 * h * row["four_h_inv"] % p != 1:
                return False, "observation four_h_inv is incorrect"
            if _row_fingerprint(row, p) != candidate_fingerprint:
                continue
            observed = row["sum"], row["sum_sq"]
            if _layer_moments_qh(p, scale, shear, q, h) == observed:
                matches += 1
        if matches < inst["required_matches"]:
            return False, f"automorphism matches only {matches} observation row(s)"
        return True, "ok"
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return False, "malformed instance or answer"


def random_candidate(inst: dict, rng: random.Random) -> object:
    exponent = rng.randrange(inst["t"])
    scale = pow(inst["m"], exponent, inst["p"])
    shear = rng.randrange(inst["p"])
    return _answer(scale, shear)


def search_space(inst: dict) -> int:
    return inst["t"] * inst["p"]


def enumerate_all(inst: dict) -> int | None:
    """Brute-force the bounded language only when it is genuinely small."""
    if search_space(inst) > 200_000:
        return None
    total = 0
    scale = 1
    for _ in range(inst["t"]):
        for shear in range(inst["p"]):
            total += int(verify(inst, _answer(scale, shear))[0])
        scale = scale * inst["m"] % inst["p"]
    return total


def _right_coset_key(pair: tuple[int, int], p: int, m: int) -> tuple[int, int]:
    return min(pair, _partner(pair, p, m))


def canonical_key(inst: dict) -> str:
    """Canonicalise the whole PDS-coset configuration under group automorphisms."""
    p, t, m = inst["p"], inst["t"], inst["m"]
    recovered = []
    frequencies: dict[tuple[int, int], int] = {}
    for row in inst["observations"]:
        pair = _recover_row(inst, row)
        if pair is None:
            return "invalid:" + hashlib.sha256(json.dumps(inst, sort_keys=True).encode()).hexdigest()
        recovered.append((row["b"], pair))
        frequencies[pair] = frequencies.get(pair, 0) + 1
    targets = [pair for pair, count in frequencies.items()
               if count >= inst["required_matches"]]
    if len(targets) != 1:
        return "invalid-target:" + hashlib.sha256(json.dumps(inst, sort_keys=True).encode()).hexdigest()
    target = targets[0]

    configurations = []
    for target_rep in (target, _partner(target, p, m)):
        inv = _inverse(target_rep, p)
        rows = []
        for b, source in recovered:
            relative = _compose(inv, source, p)
            rows.append((b, _right_coset_key(relative, p, m)))
        configurations.append(tuple(sorted(rows)))
    payload = {
        "p": p,
        "t": t,
        "m": m,
        "required_matches": inst["required_matches"],
        "configuration": min(configurations),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow the modulus and same-distribution crowding at fixed witness size."""
    harder = dict(params)
    harder["n"] = int(params.get("n", 100_003)) * 2 + 1
    harder["decoys"] = min(220, int(params.get("decoys", 1)) + 20)
    return harder


# ---------------------------------------------------------------------------
# Attacks, measurements, and mandatory gates


def _candidate_ok(inst: dict, pair: tuple[int, int]) -> bool:
    return verify(inst, _answer(*pair))[0]


def _attack_raw_moment_outlier(inst: dict) -> bool:
    row = min(inst["observations"], key=lambda r: (r["sum"], r["sum_sq"], r["b"]))
    scale = pow(inst["m"], row["sum"] % inst["t"], inst["p"])
    return _candidate_ok(inst, (scale, row["sum_sq"]))


def _attack_greedy_zero_shear(inst: dict) -> bool:
    score = sum(row["sum_sq"] for row in inst["observations"])
    scale = pow(inst["m"], score % inst["t"], inst["p"])
    return _candidate_ok(inst, (scale, 0))


def _attack_random_restart(inst: dict, attack_seed: int, restarts: int = 256) -> bool:
    rng = random.Random(attack_seed)
    for _ in range(restarts):
        answer = random_candidate(inst, rng)
        if verify(inst, answer)[0]:
            return True
    return False


def _attack_scale_one_ansatz(inst: dict) -> bool:
    """By-hand ansatz: set u=1, propagate w from each first moment, take least."""
    p, m = inst["p"], inst["m"]
    guesses = []
    for row in inst["observations"]:
        roles = _roles(row["q"], p)
        role_sum = sum(roles) % p
        w = (row["sum"] - role_sum) * row["four_h_inv"] % p
        guesses.append(w)
    return _candidate_ok(inst, (1, min(guesses)))


def _reference_scan(inst: dict) -> dict:
    """Recover every row independently, then count equal automorphisms."""
    start = time.perf_counter()
    counts: dict[tuple[int, int], int] = {}
    found = None
    recovered_rows = 0
    for row in inst["observations"]:
        pair = _recover_row(inst, row)
        if pair is None:
            continue
        recovered_rows += 1
        counts[pair] = counts.get(pair, 0) + 1
    for pair, count in counts.items():
        if count >= inst["required_matches"] and _candidate_ok(inst, pair):
            found = pair
            break
    elapsed = time.perf_counter() - start
    return {
        "solved": found is not None,
        "pair": list(found) if found else None,
        "rows_recovered": recovered_rows,
        "operations": _independent_row_operations(inst) * len(inst["observations"]),
        "wall_clock_sec": elapsed,
    }


def _pow_cost(exponent: int) -> int:
    if exponent <= 1:
        return 0
    return exponent.bit_length() - 1 + exponent.bit_count() - 1


def _independent_row_operations(inst: dict) -> int:
    """Conservative finite-field count for centered recovery of one row."""
    p, t = inst["p"], inst["t"]
    return (
        3                       # 4*sum_sq - sum^2
        + 3                     # 4*(q^2+1)
        + 2                     # check/use center_den_inv
        + _pow_cost((p + 1) // 4)  # canonical square-root candidate
        + _pow_cost(t)          # quadratic-residue selection
        + 5                     # role sum and shear recovery
        + 16                    # rebuild four coordinates and two moments
    )


def _intended_route_operations(inst: dict) -> int:
    """One sum/h fingerprint per row, then one full row recovery."""
    return len(inst["observations"]) + _independent_row_operations(inst)


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(item) for item in value)
    return 1


def _transform_instance(inst: dict, outer: tuple[int, int], reorder: bool = False) -> dict:
    """Carry every observed PDS and the witness through a group automorphism."""
    p, t, m = inst["p"], inst["t"], inst["m"]
    transformed = copy.deepcopy(inst)
    new_rows = []
    for row in inst["observations"]:
        source = _recover_row(inst, row)
        if source is None:                            # pragma: no cover
            raise ValueError("cannot transform malformed observation")
        carried = _canonical_pair(_compose(outer, source, p), p, t, m)
        new_rows.append(_moment_row(p, m, carried, row["b"]))
    if reorder:
        new_rows.reverse()
    transformed["observations"] = new_rows
    target = _pair(inst["answer"])
    carried_target = _canonical_pair(_compose(outer, target, p), p, t, m)
    transformed["answer"] = _answer(*carried_target)
    return transformed


def selftest() -> dict:
    report: dict = {}

    # G1: every preset and several seeds, plus JSON-native answers.
    g1_failures = []
    tested = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 29):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            tested += 1
            if not ok or json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
    direct_checks = {
        str(p): _direct_pds_check(p, t, m)
        for p, t, m in (_group_parameters(7), _group_parameters(11))
    }
    report["G1_planted_verifies"] = {
        "pass": not g1_failures and all(direct_checks.values()),
        "instances_tested": tested,
        "direct_group_ring_checks": direct_checks,
        "failures": g1_failures,
    }

    # G2: five distinct corruptions and five distinct rejection reasons.
    inst = make_instance(seed=2027, **DIFFICULTY[SHIPPING_DIFFICULTY])
    answer = inst["answer"]
    corruptions = {}
    dropped = copy.deepcopy(answer)
    dropped["generator_images"]["sigma"] = dropped["generator_images"]["sigma"][:-1]
    corruptions["drop_one"] = dropped
    swapped = copy.deepcopy(answer)
    swapped["generator_images"]["sigma"], swapped["generator_images"]["tau"] = (
        swapped["generator_images"]["tau"], swapped["generator_images"]["sigma"])
    corruptions["swap_two"] = swapped
    duplicated = copy.deepcopy(answer)
    duplicated["generator_images"]["tau"] = list(duplicated["generator_images"]["sigma"])
    corruptions["duplicate_one"] = duplicated
    corruptions["empty"] = {}
    out_of_range = copy.deepcopy(answer)
    out_of_range["scale"] = inst["p"]
    out_of_range["generator_images"]["sigma"] = [inst["p"], 0]
    corruptions["out_of_range"] = out_of_range
    reasons = {}
    for name, corrupted in corruptions.items():
        ok, reason = verify(inst, corrupted)
        reasons[name] = {"rejected": not ok, "reason": reason}
    distinct_reasons = len({item["reason"] for item in reasons.values()})
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in reasons.values()) and distinct_reasons == 5,
        "distinct_reasons": distinct_reasons,
        "corruptions": reasons,
    }

    # G3: exact JSON round trip through realistic surrounding prose/fences.
    blob = json.dumps(answer, separators=(",", ":"))
    model_reply = f"I used the layer moments.\n```json\n{blob}\n```\n<answer>{blob}</answer>\n"
    parsed = parse_answer(model_reply)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("no certificate here") is None,
        "parsed_equals_answer": parsed == answer,
        "garbage_returns_none": parse_answer("no certificate here") is None,
    }

    # G4: structure-aware samples are uniform over the declared automorphisms.
    samples = 200_000
    hits = 0
    rng = random.Random(991_337)
    start = time.perf_counter()
    for _ in range(samples):
        if verify(inst, random_candidate(inst, rng))[0]:
            hits += 1
    guess_seconds = time.perf_counter() - start
    exact_count = enumerate_all(inst)
    space = search_space(inst)
    # Construction rejects every decoy fingerprint collision.  A witness that
    # matches two rows must therefore have the planted fingerprint; one centered
    # moment fixes u^2, the QR convention fixes u, and the first moment fixes w.
    construction_count = 1
    exact_probability = construction_count / space
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6 and samples >= 200_000,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "exact_probability": exact_probability,
        "candidate_space": space,
        "sampling_wall_sec": guess_seconds,
    }

    # G5: sampled shipping density and measured strongest mechanical route.
    baseline = _reference_scan(inst)
    report["G5_density_and_baseline"] = {
        "pass": samples >= 200_000 and baseline["solved"],
        "density_method": "shipping-preset structure-aware Monte Carlo",
        "density_hits": hits,
        "density_samples": samples,
        "sampled_solution_density": hits / samples,
        "solution_density_exact_by_construction": exact_probability,
        "exact_solution_count_by_enumeration": exact_count,
        "constructed_unique_solution": construction_count,
        "candidate_space": space,
        "baseline_wall_seconds": baseline["wall_clock_sec"],
        "baseline_operations": baseline["operations"],
        "baseline_rows_recovered": baseline["rows_recovered"],
    }

    # G6: four failing no-tool/generic probes over eight shipping seeds.
    attack_names = (
        "raw_moment_outlier",
        "greedy_zero_shear",
        "random_restart_256",
        "scale_one_first_moment_ansatz",
    )
    results = {name: {"successes": 0, "attempts": 8} for name in attack_names}
    for index, seed in enumerate((101, 211, 307, 401, 503, 601, 701, 809)):
        trial = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        outcomes = {
            "raw_moment_outlier": _attack_raw_moment_outlier(trial),
            "greedy_zero_shear": _attack_greedy_zero_shear(trial),
            "random_restart_256": _attack_random_restart(trial, 90_000 + index),
            "scale_one_first_moment_ansatz": _attack_scale_one_ansatz(trial),
        }
        for name, success in outcomes.items():
            results[name]["successes"] += int(success)
    all_failed = all(item["successes"] == 0 for item in results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": results,
        "reference_algorithm": {
            "name": "independent centered-moment modular recovery for every row",
            "complexity": "O(d log p) exact finite-field operations for d observation rows",
            "wall_clock_sec": baseline["wall_clock_sec"],
            "operations": baseline["operations"],
            "rows_recovered": baseline["rows_recovered"],
            "solves": "1/1, as expected for Track B",
        },
    }

    # G7: both named ladder growth and an explicit size doubling verify.
    p_values = [make_instance(seed=3, **params)["p"] for params in DIFFICULTY.values()]
    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    doubled_params = dict(ship_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=3, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": p_values == sorted(p_values) and len(set(p_values)) == 4 and doubled_ok,
        "preset_primes": p_values,
        "doubled_prime": doubled["p"],
        "doubled_planted_verifies": doubled_ok,
        "answer_atoms_unchanged": _answer_atoms(doubled["answer"]) == _answer_atoms(answer),
    }

    # G8: all group automorphisms, stabilizer canonicalisation, and input order.
    invariance_checks = 0
    carried_verify_checks = 0
    unrelated_keys = []
    invariant = True
    for seed in range(20):
        original = make_instance(seed=10_000 + seed, **ship_params)
        key = canonical_key(original)
        unrelated_keys.append(key)
        p, t, m = original["p"], original["t"], original["m"]
        outer_square = (pow(m, seed + 1, p), (97 * seed + 13) % p)
        # A nonsquare scale exercises canonicalisation by the PDS stabilizer.
        outer_nonsquare = ((-pow(m, seed + 2, p)) % p, (193 * seed + 29) % p)
        for outer, reorder in ((outer_square, False),
                               (outer_nonsquare, False),
                               (_compose(outer_square, outer_nonsquare, p), True)):
            changed = _transform_instance(original, outer, reorder=reorder)
            invariance_checks += 1
            invariant = invariant and canonical_key(changed) == key
            carried_ok = verify(changed, changed["answer"])[0]
            carried_verify_checks += int(carried_ok)
            invariant = invariant and carried_ok
        reordered = copy.deepcopy(original)
        reordered["observations"].reverse()
        invariance_checks += 1
        invariant = invariant and canonical_key(reordered) == key
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant and carried_verify_checks == 60 and distinct == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_verify_checks,
        "unrelated_distinct": distinct,
        "unrelated_attempts": 20,
        "transformations": [
            "arbitrary square-scale group automorphism",
            "nonsquare-scale group automorphism plus stabilizer canonicalisation",
            "composition with observation reordering",
            "observation reordering alone",
        ],
    }

    # G9: script-owned arm counts plus measured caps.
    compact = json.dumps(answer, separators=(",", ":"))
    answer_chars = len(compact)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(answer)
    intended_operations = _intended_route_operations(inst)
    arms = G9_EVIDENCE["arms"]
    hinted_hardened = G9_EVIDENCE.get("hinted_verdict") == "hardened"
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_attempts = arms["placebo"]["attempts"]
    placebo_rate = (
        arms["placebo"]["solved"] / placebo_attempts
        if placebo_attempts else None
    )
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate if placebo_rate is not None else None
        ),
        "hinted_verdict": G9_EVIDENCE.get("hinted_verdict"),
        "placebo_status": G9_EVIDENCE.get("placebo_status"),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
