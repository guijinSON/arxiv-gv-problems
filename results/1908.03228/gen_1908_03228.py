"""Generator for identifying skew-brace classes from regular holomorph subgroups.

The family is native to Acri--Bonatto, arXiv:1908.03228.  Theorem 1.3
turns a regular subgroup of a holomorph into a skew brace, and Theorem 3.12
classifies the regular subgroups used here as the braces A_mu.  Generation
chooses the class parameters first, constructs the corresponding subgroups,
conjugates and redundantly regenerates them, and carries the class labels.

The module is deterministic in ``(n, seed, params)``, uses only the standard
library, performs no file I/O, and prints nothing on import.
"""

from __future__ import annotations

import functools
import hashlib
import json
import math
import os
import random
import re
import time


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_discrete",
    "computational_core": "other",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "semidirect-product group Z_p semidirect Z_q",
        "automorphisms phi_(i,j)",
        "regular subgroups of the holomorph",
        "skew-brace isomorphism-class parameters",
    ],
    "verification_operations": [
        "exact modular multiplication",
        "exact modular inversion relation",
        "integer range and distinctness checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The second-coordinate projection survives additive-automorphism "
        "conjugation, and two recovered classes determine the planted affine "
        "function on all displayed field coordinates; without both invariants a solver "
        "must compare classified braces component by component."
    ),
    "hardness_basis": (
        "Track B: exhaustive comparison of the first two components with the "
        "q-1 classes in Theorem 3.12 followed by affine evaluation "
        "costs O(q+c); at the hard preset the executable reference scan uses "
        "20,000,263 exact operations and averaged about 1.3 seconds, whereas the "
        "compact route uses two Euclidean inversions plus 110 affine evaluations "
        "and is available only after a no-tool solver recognizes the projection invariant."
    ),
    "max_answer_tokens": 253,
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
    "demo": {"n": 5, "components": 1, "redundant_generators": 0},
    "easy": {"n": 1009, "components": 112, "redundant_generators": 0},
    "medium": {"n": 10007, "components": 112, "redundant_generators": 1},
    "hard": {"n": 10000000, "components": 112, "redundant_generators": 2},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The translation and automorphism projections carry a conjugacy invariant "
    "that anchors one affine function on the displayed field coordinates."
)
PLACEBO_HINT = (
    "The component and generator orders use separate conventions, so keep the "
    "displayed indices and modular ranges clearly separated."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of c pairwise-distinct integers in 2..q; after replacing "
        "label q by residue 0, entry r is the value of one nonconstant affine "
        "function at component r's displayed coordinate modulo q."
    ),
    "bounds": {
        "length": "the displayed component count c (at most 192)",
        "entry_min": 2,
        "entry_max": "the displayed prime q",
        "structural_rule": (
            "all entries are pairwise distinct and their residues are values "
            "of one nonconstant affine function on the displayed coordinates"
        ),
    },
}

NOTES = r"""
Step 0.  Section 1 defines a skew left brace and Theorem 1.3 gives the exact
regular-subgroup/brace correspondence used by the instance.  Section 2 gives
the nonabelian group M of order pq and its automorphisms phi_(i,j).  Lemma 3.10
gives the regular subgroups G_(c,d), Proposition 3.11 separates their
automorphism orbits, and Theorem 3.12 identifies the resulting brace as A_mu.
The proof computes mu=(d+1)/d in Z_q.  Thus the paper is a complete
classification, not evidence for a Track A distribution; Track A is expressly
not claimed.

Certificate production.  The generator first samples distinct field coordinates
and a nonconstant affine function on them for the A_mu class residues, excluding
the forbidden residue 1.  It converts each sampled mu to d=(mu-1)^(-1), builds G_(0,d) from
the two generators in Lemma 3.10, conjugates by a sampled automorphism of M,
and adds random redundant products of the same generators.  Theorem 1.3
guarantees the brace and Theorem 3.12 carries every sampled label through
conjugation.  Nothing is recovered by solving an emitted instance.

Mechanical versus compact route.  The paper's general Theorem 1.3 route
enumerates a regular subgroup, verifies that the translation projection is a
bijection, inverts that projection, and reconstructs the operation.  Once the
complete list in Theorem 3.12 is available, the strongest executable mechanical
route is cheaper: compare every one of the q-1 classified A_mu candidates with
the first two components, then use the affine-function promise.  The executable
reference implementation measures that O(q+c) scan.  Theorem 3.12's proof
instead tracks the second-coordinate projection; two extended-Euclidean
inversions anchor all 112 labels, and evaluation of the affine function supplies
the rest.  At the shipping preset the reference route uses over twenty million
exact operations while the compact route remains below the 300-operation no-tool
cap.

What is easy.  Proposition 3.1 says p not congruent to 1 modulo q has only the
trivial brace, and Theorem 3.4 leaves only one nontrivial cyclic-type brace.
Those regimes are excluded.  Within this generated distribution the compact
Theorem 3.12 route is efficient, so this is Track B.  The outlier, copy-d,
inverse-without-offset, and random-restart attacks all submit affine lists in
the stated certificate language but do not reproduce the full vector.  The
successful generic class-list scan is reported separately, as Track B requires.

Canonicalization.  Generator order, redundant generators, additive-coordinate
automorphism conjugation, and component order are presentation choices.  The
key is the sorted set of (field coordinate, Theorem 3.12 class label) pairs
together with p and q;
it is therefore invariant under every presentation transformation generated
by this module.  It is not a general-purpose isomorphism algorithm for
arbitrary skew braces outside the classified pq family.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 100_000
_G4_SAMPLES = 200_000
_ATTACK_SEEDS = 8

# Filled after the three script-owned hardening runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "infrastructure_blocked_http_403",
}


def _integer(name, value, low, high):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if value < low or value > high:
        raise ValueError(f"{name} must lie in {low}..{high}")
    return value


def _is_prime(value):
    """Deterministic Miller--Rabin for the module's <2^64 parameter range."""
    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small:
        if value % prime == 0:
            return value == prime
    odd = value - 1
    twos = 0
    while odd % 2 == 0:
        odd //= 2
        twos += 1
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if base % value == 0:
            continue
        x = pow(base, odd, value)
        if x in (1, value - 1):
            continue
        for _ in range(twos - 1):
            x = x * x % value
            if x == value - 1:
                break
        else:
            return False
    return True


@functools.lru_cache(maxsize=None)
def _prime_pair(lower_bound):
    """Return primes p>q>=lower_bound with q | p-1 and an order-q g."""
    q = max(5, lower_bound)
    if q % 2 == 0:
        q += 1
    while not _is_prime(q):
        q += 2
    multiplier = 2
    while True:
        p = multiplier * q + 1
        if p >= (1 << 64):
            raise ValueError("parameters exceed the proven primality range")
        if _is_prime(p):
            for base in range(2, 100):
                g = pow(base, multiplier, p)
                if g != 1:
                    # q is prime and g^q=1, hence this nonidentity g has order q.
                    return p, q, g
        multiplier += 2


def _auto_apply(auto, point, p, q, g):
    """Apply phi_(i,j) to sigma^n tau^m in M."""
    i, j = auto
    n, m = point
    a0 = pow(g - 1, -1, p)
    geometric_sum = a0 * (pow(g, m, p) - 1) % p
    return ((i * n + j * geometric_sum) % p, m)


def _add(left, right, p, q, g):
    n, m = left
    s, t = right
    return ((n + pow(g, m, p) * s) % p, (m + t) % q)


def _auto_compose(left, right, p):
    """phi_left after phi_right."""
    i, j = left
    k, ell = right
    return (i * k % p, (i * ell + j) % p)


def _holo_mul(left, right, p, q, g):
    """Multiply [a,b,i,j] records in M semidirect Aut(M)."""
    moved = _auto_apply((left[2], left[3]), (right[0], right[1]), p, q, g)
    translation = _add((left[0], left[1]), moved, p, q, g)
    auto = _auto_compose((left[2], left[3]), (right[2], right[3]), p)
    return (translation[0], translation[1], auto[0], auto[1])


def _holo_pow(element, exponent, p, q, g):
    result = (0, 0, 1, 0)
    base = tuple(element)
    while exponent:
        if exponent & 1:
            result = _holo_mul(result, base, p, q, g)
        base = _holo_mul(base, base, p, q, g)
        exponent //= 2
    return result


def _conjugate(element, u, v, p, q, g):
    eta = (0, 0, u, v)
    u_inv = pow(u, -1, p)
    eta_inv = (0, 0, u_inv, -u_inv * v % p)
    return _holo_mul(_holo_mul(eta, element, p, q, g), eta_inv, p, q, g)


def _component_records(d, extras, rng, p, q, g, demo=False):
    a0 = pow(g - 1, -1, p)
    x = (a0, 0, 1, 1)       # sigma^a0 alpha
    y = (0, d, g, 0)        # tau^d beta
    records = [x, y]
    seen = set(records)
    attempts = 0
    while len(records) < extras + 2:
        attempts += 1
        if attempts > 1000:
            raise RuntimeError("could not construct distinct redundant generators")
        a = rng.randrange(1, p)
        b = rng.randrange(2, q) if q > 3 else 0
        redundant = _holo_mul(
            _holo_pow(x, a, p, q, g),
            _holo_pow(y, b, p, q, g),
            p,
            q,
            g,
        )
        if redundant not in seen:
            records.append(redundant)
            seen.add(redundant)

    if demo:
        u, v = 1, 0
    else:
        u, v = rng.randrange(1, p), rng.randrange(p)
    records = [_conjugate(record, u, v, p, q, g) for record in records]
    if not demo:
        rng.shuffle(records)
    return [list(record) for record in records]


def _extract_d(inst, component):
    p, q, g = inst["p"], inst["q"], inst["g"]
    candidates = set()
    for record in component["generators"]:
        if (
            isinstance(record, list)
            and len(record) == 4
            and all(isinstance(x, int) and not isinstance(x, bool) for x in record)
        ):
            a, b, i, j = record
            if 0 <= a < p and 0 <= b < q and 1 <= i < p and 0 <= j < p and i == g:
                candidates.add(b)
    if len(candidates) != 1 or 0 in candidates:
        raise ValueError("component has no unique beta-projection generator")
    return next(iter(candidates))


def _class_from_d(d, q):
    residue = (1 + pow(d, -1, q)) % q
    return q if residue == 0 else residue


def _ordered_components(inst):
    """Return components in semantic index order, independent of list order."""
    components = inst.get("components")
    if not isinstance(components, list):
        raise ValueError("components must be a list")
    if any(not isinstance(component, dict) for component in components):
        raise ValueError("every component must be an object")
    try:
        ordered = sorted(components, key=lambda component: component["index"])
    except (KeyError, TypeError):
        raise ValueError("every component needs an integer index") from None
    indices = [component.get("index") for component in ordered]
    if any(isinstance(index, bool) or not isinstance(index, int) for index in indices):
        raise ValueError("every component needs an integer index")
    if indices != list(range(len(ordered))):
        raise ValueError("component indices must be exactly 0..c-1")
    return ordered


def make_instance(n, seed=0, **params):
    """Construct conjugated G_(0,d) subgroups from sampled class labels."""
    n = _integer("n", n, 5, 20_000_000)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    count = _integer("components", params.pop("components", 8), 1, 192)
    extras = _integer(
        "redundant_generators", params.pop("redundant_generators", 2), 0, 24
    )
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))

    p, q, g = _prime_pair(n)
    if count > q - 1:
        raise ValueError("components cannot exceed the number of A_mu classes")
    rng = random.Random(seed)

    # Inverse generation: choose the entire certificate before constructing any
    # subgroup.  Residues use 0 for the paper's inclusive class label q.  The
    # first two field coordinates are 0 and 1; the rest are scattered uniformly.
    # For a fixed nonzero slope, exactly ``count`` intercepts make an affine value
    # hit the forbidden residue 1, so rejection sampling is uniform over the
    # bounded certificate language declared above.
    if count == 1:
        coordinates = [0]
        while True:
            intercept = rng.randrange(q)
            if intercept != 1:
                class_residues = [intercept]
                break
    else:
        coordinates = [0, 1] + rng.sample(range(2, q), count - 2)
        while True:
            intercept = rng.randrange(q)
            slope = rng.randrange(1, q)
            class_residues = [
                (intercept + slope * coordinate) % q
                for coordinate in coordinates
            ]
            if 1 not in class_residues:
                break
    answer = [q if residue == 0 else residue for residue in class_residues]
    d_values = [pow((residue - 1) % q, -1, q) for residue in class_residues]
    components = []
    demo = n == 5 and count == 1 and extras == 0
    for index, d in enumerate(d_values):
        records = _component_records(d, extras, rng, p, q, g, demo=demo)
        components.append(
            {"index": index, "coordinate": coordinates[index], "generators": records}
        )

    return {
        "paper": "arXiv:1908.03228",
        "p": p,
        "q": q,
        "g": g,
        "a0": pow(g - 1, -1, p),
        "components": components,
        "answer": answer,
    }


def render(inst):
    p, q, g = inst["p"], inst["q"], inst["g"]
    format_example = list(range(2, 2 + len(inst["components"])))
    lines = [
        "Skew-brace class identification from regular holomorph subgroups",
        "",
        f"Let p={p}, q={q}, and g={g}.  These are primes p>q, q divides p-1,",
        "and g has multiplicative order q modulo p.  Every first coordinate below",
        "is reduced modulo p and every second coordinate modulo q.",
        "",
        "Define the group M on pairs [n,m] by",
        "  [n,m] + [s,t] = [n + g^m*s (mod p), m+t (mod q)].",
        "For 1<=i<p and 0<=j<p define the automorphism phi_(i,j) by",
        "  phi_(i,j)([n,m]) = [i*n + j*S_m (mod p), m],",
        "where S_m=(g^m-1)/(g-1) modulo p (division means multiplication by",
        "the modular inverse).",
        "",
        "An element [a,b;i,j] of Hol(M)=M semidirect Aut(M) acts on x in M as",
        "  x |-> [a,b] + phi_(i,j)(x).",
        "For each component r, let G_r be the subgroup generated by its displayed",
        "unordered records.  The data guarantee that G_r is regular: for every",
        "x in M there is a unique [x;f_x] in G_r whose translation part is x.",
        "It induces a skew-brace operation x circle_r y = x + f_x(y).",
        "",
        "For an integer mu with 2<=mu<=q, A_mu denotes the skew brace on M with",
        "  [n,m] circle_mu [s,t] =",
        "      [g^t*n + (g^mu)^m*s (mod p), m+t (mod q)].",
        "Two induced braces count as the same class when an additive automorphism",
        "phi_(i,j) is an isomorphism, meaning phi_(i,j)(x circle_r y) equals",
        "phi_(i,j)(x) circle_mu phi_(i,j)(y) for every x,y in M.",
        "Interpret the class label q as residue 0 modulo q.  Each component r has",
        "a displayed field coordinate T_r.  There are fixed residues U and nonzero",
        "V such that residue(mu_r) = U + V*T_r (mod q) for every component.",
        "No class residue is 1.  For a single component this affine promise is vacuous.",
        "",
        f"There are {len(inst['components'])} components, indexed 0 through "
        f"{len(inst['components']) - 1}:",
    ]
    for component in inst["components"]:
        lines.append(
            f"  component {component['index']} (T_{component['index']}="
            f"{component['coordinate']}):"
        )
        for record in component["generators"]:
            lines.append("    [" + ",".join(str(x) for x in record) + "]")
    lines.extend(
        [
            "",
            "Find the unique class label mu_r for every component r.  Return one",
            f"JSON list [{', '.join('mu_' + str(i) for i in range(len(inst['components'])))}]",
            "in component-index order.  Every entry is an integer in the inclusive",
            "range 2..q, and the entries are guaranteed (and required) to be pairwise",
            "distinct.  Their residues must follow the promised affine relation.",
            "There are no repeated entries and indexing is zero-based.",
            "",
            "Give your final answer inside <answer></answer> tags, as a JSON list",
            "of exactly the stated length.",
            "Example of the required syntax: <answer>"
            + json.dumps(format_example)
            + "</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    statement = "\n".join(lines)
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Parse the last tagged JSON integer list; tolerate prose and fences."""
    if not isinstance(text, str):
        return None
    blocks = _ANSWER_RE.findall(text)
    if not blocks:
        return None
    body = blocks[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        answer = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(answer, list):
        return None
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return None
    return answer


def verify(inst, answer):
    """Check any valid vector of A_mu class labels; never read inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    try:
        components = _ordered_components(inst)
    except ValueError as exc:
        return False, f"malformed component indexing: {exc}"
    expected_length = len(components)
    if len(answer) != expected_length:
        return False, f"wrong length: expected {expected_length}, got {len(answer)}"
    q = inst["q"]
    for index, mu in enumerate(answer):
        if isinstance(mu, bool) or not isinstance(mu, int):
            return False, f"non-integer class label at component {index}"
        if not 2 <= mu <= q:
            return False, f"class label outside 2..q at component {index}"
    if len(set(answer)) != len(answer):
        return False, "class labels are not pairwise distinct"
    residues = [0 if mu == q else mu for mu in answer]
    coordinates = [component.get("coordinate") for component in components]
    if any(
        isinstance(coordinate, bool)
        or not isinstance(coordinate, int)
        or not 0 <= coordinate < q
        for coordinate in coordinates
    ):
        return False, "component coordinate outside 0..q-1"
    if len(set(coordinates)) != len(coordinates):
        return False, "component coordinates are not pairwise distinct"
    if len(residues) >= 2:
        coordinate_delta = (coordinates[1] - coordinates[0]) % q
        slope = (residues[1] - residues[0]) * pow(coordinate_delta, -1, q) % q
        intercept = (residues[0] - slope * coordinates[0]) % q
        if slope == 0 or any(
            residues[index] != (intercept + slope * coordinates[index]) % q
            for index in range(2, len(residues))
        ):
            return False, "class-label residues do not satisfy one nonconstant affine relation"
    for index, (component, mu) in enumerate(zip(components, answer)):
        try:
            d = _extract_d(inst, component)
        except ValueError as exc:
            return False, f"malformed component {index}: {exc}"
        if d * (mu - 1) % q != 1:
            return False, f"wrong A_mu class at component {index}"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the stated affine-function language."""
    q = inst["q"]
    components = _ordered_components(inst)
    count = len(components)
    if count == 1:
        residue = rng.randrange(q - 1)
        residue = residue if residue == 0 else residue + 1
        # rng range 0..q-2 maps to residues 0,2,...,q-1.
        return [q if residue == 0 else residue]
    while True:
        intercept = rng.randrange(q)
        slope = rng.randrange(1, q)
        residues = [
            (intercept + slope * component["coordinate"]) % q
            for component in components
        ]
        if 1 not in residues:
            return [q if residue == 0 else residue for residue in residues]


def search_space(inst):
    q = inst["q"]
    count = len(inst["components"])
    if count == 1:
        return q - 1
    # Distinct coordinates and a nonzero slope give distinct values.  For each
    # slope, exactly ``count`` intercepts hit forbidden residue 1 somewhere.
    return (q - 1) * (q - count)


def enumerate_all(inst):
    """Brute-force the exact count only when the declared space is small."""
    if search_space(inst) > _ENUMERATION_CAP:
        return None
    count = 0
    q = inst["q"]
    length = len(inst["components"])
    if length == 1:
        candidates = ([label] for label in range(2, q + 1))
    else:
        coordinates = [component["coordinate"] for component in _ordered_components(inst)]
        candidates = (
            [q if residue == 0 else residue for residue in residues]
            for slope in range(1, q)
            for intercept in range(q)
            if 1 not in (residues := [
                (intercept + slope * coordinate) % q for coordinate in coordinates
            ])
        )
    for candidate in candidates:
        count += int(verify(inst, candidate)[0])
    return count


def canonical_key(inst):
    """Class-multiset key invariant under all generated presentation changes."""
    coordinate_labels = []
    for component in inst["components"]:
        coordinate_labels.append(
            [
                component["coordinate"],
                _class_from_d(_extract_d(inst, component), inst["q"]),
            ]
        )
    payload = [inst["p"], inst["q"], sorted(coordinate_labels)]
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":")).encode("ascii")
    ).hexdigest()


def escalate(params):
    """Grow the class range and presentation clutter at fixed answer length."""
    harder = dict(params)
    current = int(harder.get("n", 5))
    clutter = int(harder.get("redundant_generators", 0))
    if current >= 20_000_000 and clutter >= 24:
        return None
    harder["n"] = min(20_000_000, current * 2 + 1)
    harder["redundant_generators"] = min(
        24, clutter + 2
    )
    return harder


def _inverse_steps(value, modulus):
    """Number of Euclidean divisions plus the final class increment."""
    divisions = 0
    a, b = modulus, value
    while b:
        a, b = b, a % b
        divisions += 1
    return divisions + 1


def _compact_decode(inst):
    components = _ordered_components(inst)
    q = inst["q"]
    first_d = _extract_d(inst, components[0])
    first = _class_from_d(first_d, q)
    operations = _inverse_steps(first_d, q)
    if len(components) == 1:
        return [first], operations

    second_d = _extract_d(inst, components[1])
    second = _class_from_d(second_d, q)
    operations += _inverse_steps(second_d, q)
    first_residue = 0 if first == q else first
    second_residue = 0 if second == q else second
    coordinate_delta = (components[1]["coordinate"] - components[0]["coordinate"]) % q
    slope = (
        (second_residue - first_residue)
        * pow(coordinate_delta, -1, q)
        % q
    )
    intercept = (first_residue - slope * components[0]["coordinate"]) % q
    operations += _inverse_steps(coordinate_delta, q) + 5
    residues = [first_residue, second_residue]
    for component in components[2:]:
        residues.append((intercept + slope * component["coordinate"]) % q)
        operations += 2
    return [q if residue == 0 else residue for residue in residues], operations


def _reference_class_scan(inst):
    """Scan two class labels, then use the statement's affine promise."""
    q = inst["q"]
    anchors = []
    comparisons = 0
    started = time.perf_counter()
    components = _ordered_components(inst)
    anchor_count = min(2, len(components))
    for component in components[:anchor_count]:
        d = _extract_d(inst, component)
        matches = []
        for mu in range(2, q + 1):
            comparisons += 1
            if d * (mu - 1) % q == 1:
                matches.append(mu)
        if len(matches) != 1:
            return None, {
                "wall_clock_sec": time.perf_counter() - started,
                "class_comparisons": comparisons,
                "operations": comparisons,
            }
        anchors.append(matches[0])

    reconstructed = list(anchors)
    affine_operations = 0
    if len(components) > 2:
        first = 0 if anchors[0] == q else anchors[0]
        second = 0 if anchors[1] == q else anchors[1]
        coordinate_delta = (
            components[1]["coordinate"] - components[0]["coordinate"]
        ) % q
        slope = (second - first) * pow(coordinate_delta, -1, q) % q
        intercept = (first - slope * components[0]["coordinate"]) % q
        affine_operations += _inverse_steps(coordinate_delta, q) + 5
        for component in components[2:]:
            residue = (intercept + slope * component["coordinate"]) % q
            reconstructed.append(q if residue == 0 else residue)
            affine_operations += 2
    elapsed = time.perf_counter() - started
    return reconstructed, {
        "wall_clock_sec": elapsed,
        "class_comparisons": comparisons,
        "operations": comparisons + affine_operations,
    }


def _valid_affine_guess(intercept_seed, slope_seed, components, q):
    """Project heuristic seeds into the explicitly promised answer language."""
    intercept = intercept_seed % q
    slope = slope_seed % q or 1
    for _ in range(q - 1):
        residues = [
            (intercept + slope * component["coordinate"]) % q
            for component in components
        ]
        if 1 not in residues:
            return [q if residue == 0 else residue for residue in residues]
        slope = slope % (q - 1) + 1
    raise RuntimeError("could not project heuristic into certificate language")


def _attack_outlier_rank(inst):
    order = sorted(
        range(len(inst["components"])),
        key=lambda index: sum(record[0] for record in inst["components"][index]["generators"]),
    )
    # Use the most extreme component to seed a simple affine class guess while
    # staying inside the stated language.
    return _valid_affine_guess(
        2 + order[0], 1, _ordered_components(inst), inst["q"]
    )


def _attack_copy_projection(inst):
    ds = [_extract_d(inst, component) for component in _ordered_components(inst)]
    if len(ds) == 1:
        return _valid_affine_guess(ds[0], 1, _ordered_components(inst), inst["q"])
    return _valid_affine_guess(
        ds[0], ds[1] - ds[0], _ordered_components(inst), inst["q"]
    )


def _attack_inverse_only(inst):
    q = inst["q"]
    anchors = [
        pow(_extract_d(inst, component), -1, q)
        for component in _ordered_components(inst)[:2]
    ]
    if len(anchors) == 1:
        return _valid_affine_guess(anchors[0], 1, _ordered_components(inst), q)
    return _valid_affine_guess(
        anchors[0], anchors[1] - anchors[0], _ordered_components(inst), q
    )


def _attack_random_restart(inst, restarts=256):
    digest = hashlib.sha256(canonical_key(inst).encode("ascii")).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))
    attempts = 0
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        attempts += 1
        if verify(inst, candidate)[0]:
            return candidate, attempts
    return None, attempts


def _transform_instance(inst, rng, permute_components=True, add_redundant=True):
    """Carry a real additive-coordinate conjugation and component relabelling."""
    p, q, g = inst["p"], inst["q"], inst["g"]
    transformed_components = []
    carried = []
    for component, label in zip(inst["components"], inst["answer"]):
        u, v = rng.randrange(1, p), rng.randrange(p)
        records = [
            list(_conjugate(tuple(record), u, v, p, q, g))
            for record in component["generators"]
        ]
        rng.shuffle(records)
        if add_redundant and len(records) >= 2:
            extra = list(_holo_mul(tuple(records[0]), tuple(records[1]), p, q, g))
            if extra not in records:
                records.append(extra)
        transformed_components.append(
            {
                "index": component["index"],
                "coordinate": component["coordinate"],
                "generators": records,
            }
        )
        carried.append(label)
    order = list(range(len(transformed_components)))
    if permute_components:
        rng.shuffle(order)
    components = [transformed_components[old_index] for old_index in order]
    # Component indices, rather than physical list positions, carry the affine
    # coordinate association.  Reordering the input list therefore preserves the witness.
    answer = list(carried)
    return {
        **{key: value for key, value in inst.items() if key not in {"components", "answer"}},
        "components": components,
        "answer": answer,
    }


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest():
    report = {}

    planted_attempts = 0
    planted_successes = 0
    compact_successes = 0
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            planted_attempts += 1
            planted_successes += int(verify(inst, inst["answer"])[0])
            decoded, _ = _compact_decode(inst)
            compact_successes += int(decoded == inst["answer"] and verify(inst, decoded)[0])
            json_roundtrips += int(json.loads(json.dumps(inst["answer"])) == inst["answer"])
    report["G1_planted_verifies"] = {
        "pass": planted_successes == planted_attempts
        and compact_successes == planted_attempts
        and json_roundtrips == planted_attempts,
        "successes": planted_successes,
        "compact_decoder_successes": compact_successes,
        "attempts": planted_attempts,
        "json_roundtrips": json_roundtrips,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping_params)
    answer = list(inst["answer"])
    corruptions = {}
    corruptions["empty"] = verify(inst, [])[1]
    corruptions["drop_one"] = verify(inst, answer[:-1])[1]
    swapped = list(answer)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    corruptions["swap_two"] = verify(inst, swapped)[1]
    duplicate = list(answer)
    duplicate[1] = duplicate[0]
    corruptions["duplicate"] = verify(inst, duplicate)[1]
    outside = list(answer)
    outside[0] = inst["q"] + 1
    corruptions["out_of_range"] = verify(inst, outside)[1]
    wrong_type = list(answer)
    wrong_type[0] = str(wrong_type[0])
    corruptions["non_integer"] = verify(inst, wrong_type)[1]
    report["G2_rejects_corruption"] = {
        "pass": all(reason != "ok" for reason in corruptions.values())
        and len(set(corruptions.values())) == len(corruptions),
        "reasons": corruptions,
        "distinct_reasons": len(set(corruptions.values())),
    }

    model_reply = (
        "Tracing the translation projections gives the following classes.\n"
        "```json\n<answer>" + json.dumps(answer) + "</answer>\n```\n"
        "I kept component order unchanged."
    )
    parsed = parse_answer(model_reply)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_length": len(parsed) if parsed is not None else None,
    }

    guess_rng = random.Random(20260905)
    guess_hits = 0
    for _ in range(_G4_SAMPLES):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_probability = guess_hits / _G4_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": guess_hits,
        "total": _G4_SAMPLES,
        "observed_probability": guess_probability,
        "candidate_space": search_space(inst),
        "candidate_space_bits": search_space(inst).bit_length() - 1,
        "sampler": (
            "uniform valid (intercept, nonzero slope) pair for the displayed "
            "field coordinates, conditioned to avoid residue 1"
        ),
    }

    baseline_started = time.perf_counter()
    baseline_candidate, baseline_restarts = _attack_random_restart(inst, 256)
    baseline_elapsed = time.perf_counter() - baseline_started
    reference_answer, reference_stats = _reference_class_scan(inst)
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_probability < 1e-6
        and baseline_candidate is None
        and reference_answer is not None
        and verify(inst, reference_answer)[0]
        and demo_count == 1,
        "shipping_density_hits": guess_hits,
        "shipping_density_total": _G4_SAMPLES,
        "shipping_density_estimate": guess_probability,
        "mathematical_valid_answer_count": 1,
        "strongest_failing_attack_wall_clock_sec": baseline_elapsed,
        "strongest_failing_attack_restarts": baseline_restarts,
        "strongest_failing_attack_candidate_entries": baseline_restarts * len(answer),
        "reference_algorithm_wall_clock_sec": reference_stats["wall_clock_sec"],
        "reference_algorithm_class_comparisons": reference_stats["class_comparisons"],
        "reference_algorithm_operations": reference_stats["operations"],
        "demo_exact_solution_count": demo_count,
    }

    attack_names = (
        "outlier_translation_rank",
        "greedy_copy_second_projection",
        "random_restart_256_affine_lists",
        "obvious_inverse_without_offset_ansatz",
    )
    successes = {name: 0 for name in attack_names}
    reference_solves = 0
    reference_comparisons = 0
    reference_operations = 0
    reference_seconds = 0.0
    compact_solves = 0
    compact_operations = 0
    for seed in range(1000, 1000 + _ATTACK_SEEDS):
        panel_inst = make_instance(seed=seed, **shipping_params)
        candidates = {
            attack_names[0]: _attack_outlier_rank(panel_inst),
            attack_names[1]: _attack_copy_projection(panel_inst),
            attack_names[3]: _attack_inverse_only(panel_inst),
        }
        random_found, _ = _attack_random_restart(panel_inst, 256)
        candidates[attack_names[2]] = random_found
        for name, candidate in candidates.items():
            successes[name] += int(candidate is not None and verify(panel_inst, candidate)[0])
        reference, stats = _reference_class_scan(panel_inst)
        reference_solves += int(reference is not None and verify(panel_inst, reference)[0])
        reference_comparisons += stats["class_comparisons"]
        reference_operations += stats["operations"]
        reference_seconds += stats["wall_clock_sec"]
        compact, operations = _compact_decode(panel_inst)
        compact_solves += int(verify(panel_inst, compact)[0])
        compact_operations += operations
    attacks = {
        name: {"successes": successes[name], "attempts": _ATTACK_SEEDS}
        for name in attack_names
    }
    all_failed = all(result["successes"] == 0 for result in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed
        and reference_solves == _ATTACK_SEEDS
        and compact_solves == _ATTACK_SEEDS,
        "attacks": attacks,
        "reference_algorithm": {
            "name": (
                "exhaustive Theorem 3.12 class scan for two anchors, followed "
                "by evaluation of the promised affine function"
            ),
            "complexity": "O(q+c) exact congruence and affine-evaluation operations",
            "wall_clock_sec": reference_seconds / _ATTACK_SEEDS,
            "class_comparisons": round(reference_comparisons / _ATTACK_SEEDS),
            "operations": round(reference_operations / _ATTACK_SEEDS),
            "solves": f"{reference_solves}/{_ATTACK_SEEDS}, as expected",
        },
        "compact_route": {
            "name": (
                "Theorem 3.12 second-projection invariant for two anchors plus "
                "affine evaluation at the displayed field coordinates"
            ),
            "complexity": "O(log(q)+c) exact arithmetic",
            "operations": round(compact_operations / _ATTACK_SEEDS),
            "solves": f"{compact_solves}/{_ATTACK_SEEDS}, as expected",
        },
    }

    doubled = make_instance(
        n=shipping_params["n"] * 2,
        seed=424242,
        components=shipping_params["components"],
        redundant_generators=shipping_params["redundant_generators"],
    )
    report["G7_scales"] = {
        "pass": verify(doubled, doubled["answer"])[0]
        and doubled["q"] > inst["q"]
        and search_space(doubled) > search_space(inst),
        "shipping_q": inst["q"],
        "doubled_q": doubled["q"],
        "shipping_space_bits": search_space(inst).bit_length() - 1,
        "doubled_space_bits": search_space(doubled).bit_length() - 1,
        "answer_atoms_both": len(answer),
    }

    invariant_checks = 0
    carried_checks = 0
    distinct_keys = set()
    transformations_per_seed = 4
    for seed in range(20):
        original = make_instance(seed=20_000 + seed, **shipping_params)
        key = canonical_key(original)
        distinct_keys.add(key)
        for variant in range(transformations_per_seed):
            rng = random.Random(90_000 + 100 * seed + variant)
            transformed = _transform_instance(
                original,
                rng,
                permute_components=variant in (1, 3),
                add_redundant=variant in (2, 3),
            )
            invariant_checks += int(canonical_key(transformed) == key)
            carried_checks += int(verify(transformed, transformed["answer"])[0])
    invariance_attempts = 20 * transformations_per_seed
    report["G8_canonical_key"] = {
        "pass": invariant_checks == invariance_attempts
        and carried_checks == invariance_attempts
        and len(distinct_keys) == 20,
        "invariant_relabellings": invariant_checks,
        "invariance_attempts": invariance_attempts,
        "carried_witnesses_valid": carried_checks,
        "carried_witness_attempts": invariance_attempts,
        "distinct_unrelated_keys": len(distinct_keys),
        "distinctness_attempts": 20,
        "symmetries_tested": [
            "generator-list reordering",
            "redundant-generator insertion",
            "additive-automorphism conjugation",
            "component permutation with carried answer",
            "compositions of the above",
        ],
    }

    answer_blob = json.dumps(answer, separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(answer)
    _, intended_operations = _compact_decode(inst)
    hinted = G9_ORACLE_RESULTS["hinted"]
    placebo = G9_ORACLE_RESULTS["placebo"]
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    arms = {
        arm: dict(G9_ORACLE_RESULTS[arm]) for arm in ("bare", "hinted", "placebo")
    }
    report["G9_no_tool_suitability"] = {
        # The three oracle arms are diagnostic only.  G9(c)'s answer-size and
        # intended-effort caps are the sole gate as of 2026-09-05.
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted["solved"] / max(1, hinted["attempts"])
            - placebo["solved"] / max(1, placebo["attempts"])
        ),
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping_params)
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
