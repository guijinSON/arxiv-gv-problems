"""Verified generator for maximal empty squares in a succinct rational point set.

The native object comes from Section 3 of arXiv:1806.09562.  For a lower-left
anchor s, the paper determines its maximal empty square from the closest blocker
in the two 45-degree wedges above s.  Here every point is given exactly by a
quadratic coordinate formula.  Generation chooses the blocking point first and
raises every other batch minimum by a known positive offset; it never searches
the generated point set.

The family is Track B.  Direct blocker scanning is linear in the expanded point
count and is deliberately measured.  A solver that notices that the difference
of the two squared coordinate numerators is affine in the index can inspect only
three indices per batch.
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


# Keep the optional repository helpers importable under harden.py's working
# directory.  This module needs only integers, but making the documented import
# robust prevents later exact-rational extensions from acquiring a dependency.
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import rationals  # noqa: F401
except ImportError:  # The implementation below remains standard-library-only.
    rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "geometry",
    "object_regime": "rational_exact",
    "computational_core": "other",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "finite point set over Q given by exact coordinate formulas",
        "lower-left anchored axis-aligned square",
        "blocking point on the square boundary",
    ],
    "verification_operations": [
        "exact integer evaluation of rational coordinates",
        "exact rational containment comparison",
        "exact emptiness scan",
        "maximality check from a boundary blocker",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Subtract the two quadratic coordinate numerators so their squares "
        "cancel to an affine function of the point index; without this change "
        "of variables one must scan the expanded point set."
    ),
    "hardness_basis": (
        "Track B: the direct closest-blocker scan underlying Section 3 is O(n) "
        "for one anchor and performs 9n exact operations (21,600,072 at the "
        "shipping n=2,400,008); the measured wall-clock cost "
        "is recorded by selftest, while affine cancellation needs at most 240 "
        "exact operations over eight batches."
    ),
    "max_answer_tokens": 32,
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
    "demo": {"n": 16, "batches": 2, "scale": 2},
    "easy": {"n": 2_400_008, "batches": 8, "scale": 100_000},
    "medium": {"n": 4_800_008, "batches": 8, "scale": 1_000_000},
    "hard": {"n": 9_600_016, "batches": 8, "scale": 10_000_000},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The difference between the two squared coordinate numerators is affine in "
    "the point index within every batch."
)
PLACEBO_HINT = (
    "Keep all rational comparisons exact and check the point indexing carefully "
    "before submitting the blocker."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "Choose exactly one of the n displayed non-anchor points as a blocker "
        "and give the side of its lower-left anchored square as the exact "
        "rational max(X,Y)/D.  Batch and within-batch indices are 0-based."
    ),
    "bounds": {
        "max_batches": 64,
        "max_points": 1_000_000_000_000,
        "coordinate_bits": 512,
        "candidate_count": "n",
    },
}

NOTES = (
    "Section 1 fixes emptiness (no anchor in the square interior), anchoring "
    "at a corner, and interior-disjoint packings.  Section 3, especially the "
    "paragraph beginning 'It remains to compute the 4n anchored maximal empty "
    "squares,' fixes the blocker definition, and Theorem 2 gives an O(n log n) "
    "all-anchors reach algorithm; for one named anchor a direct exact scan is "
    "O(n).  Theorem 3 is only worst-case NP-hardness for "
    "full maximum-area packings produced by a Planar-Monotone-3SAT reduction, "
    "so it does not license a Track A claim for inverse-planted point clouds.  "
    "This module therefore uses Track B.  Generation samples a target batch and "
    "index first, makes its L-infinity distance S0, and gives every other batch "
    "minimum S0+c with c>0.  Coordinate-minimum, coordinate-sum, midpoint, "
    "offset-blind crossing, and random-blocker attacks are separated from the "
    "paper's linear reference scan."
)

# The bare and hinted figures are measured harness results.  The placebo arm was
# not run because the protocol says to stop once the one allowed G9(b) escalation
# is broken a second time.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 1, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "too_easy",
}


def _base_index(spec, shown_index, length):
    return length - 1 - shown_index if spec["reverse"] else shown_index


def _shown_index(spec, base_index, length):
    return length - 1 - base_index if spec["reverse"] else base_index


def _point_raw(inst, batch_index, shown_index):
    """Return the two coordinate numerators of a displayed point."""
    length = inst["points_per_batch"]
    spec = inst["batches"][batch_index]
    j = _base_index(spec, shown_index, length)
    z = spec["P"] * j + spec["Q"]
    x = spec["T"] + z * z
    rz = spec["R"] - z
    y = spec["T"] + spec["K"] + rz * rz
    if inst["swap_xy"]:
        x, y = y, x
    return x, y


def _candidate_for_point(inst, batch_index, shown_index):
    x, y = _point_raw(inst, batch_index, shown_index)
    return {
        "blocker": [batch_index, shown_index],
        "side": [max(x, y), inst["denominator"]],
    }


def _make_preliminary_batch(rng, length, scale):
    """Build one monotone crossing, retaining its planted local minimizer."""
    p = rng.randint(max(2, scale), max(3, 2 * scale))
    q = rng.randint(max(1, scale), max(2, 3 * scale))
    # This lies safely to the right of R/(2P), defeating the offset-blind and
    # coordinate-sum crossings while staying away from either endpoint.
    lo = 13 * length // 20
    hi = 3 * length // 4
    r = rng.randint(lo, hi)
    delta = max(1, p // rng.randint(7, 10))
    z_last = p * (length - 1) + q
    extra = rng.randint(max(1, p * length // 10), max(2, p * length // 6))
    big_r = z_last + extra
    z_r = p * r + q
    crossing = z_r + delta
    k = 2 * big_r * crossing - big_r * big_r
    if k <= 0:
        raise AssertionError("construction failed to put crossing right of R/2")
    raw_min = z_r * z_r + 2 * big_r * delta
    # At r the y-coordinate is raw_min (before T), while at r+1 the
    # x-coordinate is larger because delta < P*z_r/R + P^2/(2R).
    if 2 * big_r * delta >= 2 * z_r * p + p * p:
        raise AssertionError("construction failed to make the planted index unique")
    return {
        "P": p,
        "Q": q,
        "R": big_r,
        "K": k,
        "_r": r,
        "_raw_min": raw_min,
    }


def make_instance(n, seed=0, **params):
    """Inverse-generate a maximal empty square and its exact blocker.

    The target batch, target index, and target L-infinity distance are fixed
    before the public batch order and index reversals are chosen.  Other batches
    receive strictly positive offsets, so no closest-point search is performed.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n < 8:
        raise ValueError("n must be an integer at least 8")
    batches = params.pop("batches", 8)
    scale = params.pop("scale", 10_000)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if (
        isinstance(batches, bool)
        or not isinstance(batches, int)
        or not 2 <= batches <= 64
    ):
        raise ValueError("batches must be an integer in [2,64]")
    if n % batches:
        raise ValueError("n must be divisible by batches")
    length = n // batches
    if length < 8:
        raise ValueError("each batch must contain at least 8 points")
    if n > CERTIFICATE_LANGUAGE["bounds"]["max_points"]:
        raise ValueError("n exceeds the declared certificate-language bound")
    if isinstance(scale, bool) or not isinstance(scale, int) or scale < 1:
        raise ValueError("scale must be a positive integer")

    rng = random.Random(seed)
    prelim = [_make_preliminary_batch(rng, length, scale) for _ in range(batches)]

    # The rank-zero batch is chosen before any public order is sampled.  Its
    # minimum will be S0; all others have the known larger minimum S0+rank*gap.
    ranks = list(range(batches))
    rng.shuffle(ranks)
    s0 = max(spec["_raw_min"] for spec in prelim) + rng.randint(
        scale * scale, 3 * scale * scale
    )
    gap = rng.randint(scale * scale, 4 * scale * scale)
    base_batches = []
    target_base_batch = None
    target_base_index = None
    for base_index, (spec, rank) in enumerate(zip(prelim, ranks)):
        public = {key: value for key, value in spec.items() if not key.startswith("_")}
        public["T"] = s0 + rank * gap - spec["_raw_min"]
        public["reverse"] = bool(rng.randrange(2))
        if public["T"] <= 0:
            raise AssertionError("construction produced a nonpositive offset")
        base_batches.append(public)
        if rank == 0:
            target_base_batch = base_index
            target_base_index = spec["_r"]

    order = list(range(batches))
    rng.shuffle(order)
    shown_batches = [base_batches[index] for index in order]
    shown_target_batch = order.index(target_base_batch)
    shown_target_index = _shown_index(
        shown_batches[shown_target_batch], target_base_index, length
    )
    swap_xy = bool(rng.randrange(2))

    endpoint_max = 0
    temporary = {
        "points_per_batch": length,
        "batches": shown_batches,
        "swap_xy": swap_xy,
    }
    for b in range(batches):
        for i in (0, length - 1):
            endpoint_max = max(endpoint_max, *_point_raw(temporary, b, i))
    denominator = endpoint_max + rng.randint(scale * scale, 5 * scale * scale)
    if denominator.bit_length() > CERTIFICATE_LANGUAGE["bounds"]["coordinate_bits"]:
        raise ValueError("coordinates exceed the declared bit bound")

    inst = {
        "n": n,
        "batch_count": batches,
        "points_per_batch": length,
        "denominator": denominator,
        "batches": shown_batches,
        "swap_xy": swap_xy,
        "answer": {
            "blocker": [shown_target_batch, shown_target_index],
            "side": [s0, denominator],
        },
    }

    # Constant-size construction checks are theorem premises, not a search.
    tx, ty = _point_raw(inst, shown_target_batch, shown_target_index)
    if max(tx, ty) != s0 or tx == ty:
        raise AssertionError("planted blocker does not have the promised distance")
    return inst


def _batch_lines(inst):
    lines = []
    for b, spec in enumerate(inst["batches"]):
        lines.append(
            "  batch {b}: P={P}, Q={Q}, R={R}, K={K}, T={T}, reverse={rev}".format(
                b=b,
                P=spec["P"],
                Q=spec["Q"],
                R=spec["R"],
                K=spec["K"],
                T=spec["T"],
                rev=1 if spec["reverse"] else 0,
            )
        )
    return "\n".join(lines)


def render(inst):
    """Render the complete exact problem, with no default hint."""
    swap_text = (
        "After computing (X,Y), swap the two numerators before forming the point."
        if inst["swap_xy"]
        else "Do not swap the two coordinate numerators."
    )
    statement = f"""Maximal empty lower-left anchored square

The container is the closed unit square U=[0,1] x [0,1].  The distinguished
anchor is s=(0,0).  In addition to s, the finite point set contains exactly
{inst['n']} rational points, divided into {inst['batch_count']} displayed batches.
Each batch contains L={inst['points_per_batch']} points and every index is 0-based.

For the point with displayed batch b and displayed index i, read P,Q,R,K,T and
reverse from the batch line below.  Put j=i when reverse=0, and put j=L-1-i when
reverse=1.  Define, using exact integers,

    z = P*j + Q
    X = T + z^2
    Y = T + K + (R-z)^2.

{swap_text}
The point is (X/{inst['denominator']}, Y/{inst['denominator']}).  Here are all
batch parameters:
{_batch_lines(inst)}

A lower-left anchored square of side a is [0,a] x [0,a].  It is empty when no
point of the given set lies in its open interior; points on its boundary are
allowed.  Find the maximum possible side a.  Certify maximality by naming a
non-anchor point on the top or right boundary of that square.  The named blocker
must use its displayed (b,i) indices.  Give a as an exact rational p/q with
integers p>=0 and q>0; unreduced fractions are allowed.

Give your final answer inside <answer></answer> tags, exactly as
<answer>b, i, p/q</answer>.  Example: <answer>2, 17, 314/997</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


_ANSWER_RE = re.compile(
    r"<answer>\s*([+-]?\d+)\s*,\s*([+-]?\d+)\s*,\s*"
    r"([+-]?\d+)\s*/\s*([+-]?\d+)\s*</answer>",
    re.IGNORECASE | re.DOTALL,
)


def parse_answer(text):
    """Parse tagged output amid prose or Markdown; return None on garbage."""
    if not isinstance(text, str):
        return None
    matches = list(_ANSWER_RE.finditer(text))
    if len(matches) != 1:
        return None
    try:
        b, i, p, q = (int(value) for value in matches[0].groups())
    except (TypeError, ValueError):
        return None
    return {"blocker": [b, i], "side": [p, q]}


def verify(inst, answer):
    """Check the blocker, square emptiness, and maximality using exact integers."""
    if not isinstance(answer, dict):
        return False, "answer must be an object with blocker and side"
    if not answer:
        return False, "empty answer object"
    expected_keys = {"blocker", "side"}
    if "blocker" not in answer:
        return False, "missing blocker"
    if "side" not in answer:
        return False, "missing side"
    if set(answer) != expected_keys:
        return False, "unexpected answer fields"

    blocker = answer["blocker"]
    side = answer["side"]
    if not isinstance(blocker, list) or len(blocker) != 2:
        return False, "blocker must contain exactly two indices"
    if not isinstance(side, list) or len(side) != 2:
        return False, "side must contain numerator and denominator"
    if any(isinstance(v, bool) or not isinstance(v, int) for v in blocker):
        return False, "blocker indices must be integers"
    if any(isinstance(v, bool) or not isinstance(v, int) for v in side):
        return False, "side numerator and denominator must be integers"

    b, i = blocker
    p, q = side
    if not 0 <= b < inst["batch_count"]:
        return False, "blocker batch is out of range"
    if not 0 <= i < inst["points_per_batch"]:
        return False, "blocker index is out of range"
    if q <= 0:
        return False, "side denominator must be positive"
    if p <= 0:
        return False, "side length must be positive"
    if p > q:
        return False, "square is not contained in the unit container"

    denominator = inst["denominator"]
    bx, by = _point_raw(inst, b, i)
    boundary = max(bx, by)
    if p * denominator != boundary * q:
        return False, "claimed side does not pass through the named blocker"
    if bx == by:
        boundary_kind = "corner"
    elif bx == boundary:
        boundary_kind = "right"
    else:
        boundary_kind = "top"

    # This is deliberately the mechanical reference check: expand every point
    # and test strict interior containment.  It never consults inst['answer'].
    threshold = p * denominator
    for batch_index in range(inst["batch_count"]):
        for shown_index in range(inst["points_per_batch"]):
            x, y = _point_raw(inst, batch_index, shown_index)
            if x * q < threshold and y * q < threshold:
                return (
                    False,
                    f"square is not empty: point ({batch_index},{shown_index}) "
                    "lies in its interior",
                )

    # The blocker has both positive coordinates and lies on the boundary.  Any
    # strict increase therefore moves it into the interior, proving maximality.
    if bx <= 0 or by <= 0:
        return False, "named blocker cannot certify a strict enlargement"
    return True, "ok" if boundary_kind else "ok"


def random_candidate(inst, rng):
    """Uniformly choose a blocker and enforce the obvious boundary equation."""
    flat = rng.randrange(inst["n"])
    b, i = divmod(flat, inst["points_per_batch"])
    return _candidate_for_point(inst, b, i)


def search_space(inst):
    return inst["n"]


def _scan_minimum(inst):
    """The domain-standard direct scan, with a transparent operation count."""
    best = None
    best_points = []
    for b in range(inst["batch_count"]):
        for i in range(inst["points_per_batch"]):
            x, y = _point_raw(inst, b, i)
            value = max(x, y)
            if best is None or value < best:
                best = value
                best_points = [(b, i)]
            elif value == best:
                best_points.append((b, i))
    return best, best_points, 9 * inst["n"]


def enumerate_all(inst):
    if inst["n"] > 100_000:
        return None
    _best, points, _operations = _scan_minimum(inst)
    return len(points)


def _canonical_batch_tuple(spec):
    return (spec["P"], spec["Q"], spec["R"], spec["K"], spec["T"])


def canonical_key(inst):
    """Canonical under batch relabeling, index reversal, and x/y reflection."""
    payload = {
        "n": inst["n"],
        "length": inst["points_per_batch"],
        "denominator": inst["denominator"],
        "batches": sorted(_canonical_batch_tuple(spec) for spec in inst["batches"]),
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def escalate(params):
    """Increase scan length and coefficient entropy without growing the answer."""
    n = params.get("n")
    batches = params.get("batches", 8)
    scale = params.get("scale", 10_000)
    if not isinstance(n, int) or not isinstance(batches, int) or not isinstance(scale, int):
        return None
    if n >= CERTIFICATE_LANGUAGE["bounds"]["max_points"] // 2:
        return None
    length = n // batches
    harder_length = max(length + 1, 2 * length)
    return {
        "n": harder_length * batches,
        "batches": batches,
        "scale": min(scale * 10, 10**30),
    }


def _nearest_indices_to_fraction(numerator, denominator, length):
    floor_value = numerator // denominator
    return sorted(
        {
            max(0, min(length - 1, floor_value + shift))
            for shift in (-1, 0, 1, 2)
        }
    )


def _compact_solve(inst):
    """Cancel the squares and inspect O(1) points in every batch."""
    length = inst["points_per_batch"]
    candidates = []
    for b, spec in enumerate(inst["batches"]):
        # X-Y = 2R(Pj+Q)-R^2-K.  The sign change is therefore at the
        # following rational base index.
        numerator = spec["R"] * spec["R"] + spec["K"] - 2 * spec["R"] * spec["Q"]
        denominator = 2 * spec["R"] * spec["P"]
        for j in _nearest_indices_to_fraction(numerator, denominator, length):
            i = _shown_index(spec, j, length)
            x, y = _point_raw(inst, b, i)
            candidates.append((max(x, y), b, i))
    _value, b, i = min(candidates)
    return _candidate_for_point(inst, b, i)


def _is_scan_witness(inst, candidate, best, best_points):
    if not isinstance(candidate, dict):
        return False
    try:
        b, i = candidate["blocker"]
        p, q = candidate["side"]
    except (KeyError, TypeError, ValueError):
        return False
    return (
        (b, i) in best_points
        and q > 0
        and p * inst["denominator"] == best * q
    )


def _endpoint_min_coordinate(inst, coordinate):
    best = None
    choice = None
    length = inst["points_per_batch"]
    for b in range(inst["batch_count"]):
        for i in (0, length - 1):
            point = _point_raw(inst, b, i)
            item = (point[coordinate], b, i)
            if best is None or item < best:
                best = item
                choice = (b, i)
    return _candidate_for_point(inst, *choice)


def _greedy_coordinate_sum(inst):
    """Minimize X+Y while ignoring that the objective is max(X,Y)."""
    best = None
    choice = None
    length = inst["points_per_batch"]
    for b, spec in enumerate(inst["batches"]):
        numerator = spec["R"] - 2 * spec["Q"]
        denominator = 2 * spec["P"]
        for j in _nearest_indices_to_fraction(numerator, denominator, length):
            i = _shown_index(spec, j, length)
            x, y = _point_raw(inst, b, i)
            item = (x + y, b, i)
            if best is None or item < best:
                best = item
                choice = (b, i)
    return _candidate_for_point(inst, *choice)


def _midpoint_candidate(inst):
    best = None
    choice = None
    length = inst["points_per_batch"]
    for b, spec in enumerate(inst["batches"]):
        i = _shown_index(spec, length // 2, length)
        x, y = _point_raw(inst, b, i)
        item = (max(x, y), b, i)
        if best is None or item < best:
            best = item
            choice = (b, i)
    return _candidate_for_point(inst, *choice)


def _offset_blind_crossing(inst):
    """Use z=R/2, the tempting crossing obtained by dropping K."""
    best = None
    choice = None
    length = inst["points_per_batch"]
    for b, spec in enumerate(inst["batches"]):
        numerator = spec["R"] - 2 * spec["Q"]
        denominator = 2 * spec["P"]
        for j in _nearest_indices_to_fraction(numerator, denominator, length):
            i = _shown_index(spec, j, length)
            x, y = _point_raw(inst, b, i)
            item = (max(x, y), b, i)
            if best is None or item < best:
                best = item
                choice = (b, i)
    return _candidate_for_point(inst, *choice)


def _relabel_variants(inst, seed):
    rng = random.Random(seed)
    order = list(range(inst["batch_count"]))
    rng.shuffle(order)
    variants = []
    old_b, old_i = inst["answer"]["blocker"]
    for mask in range(1, 8):
        use_order = order if mask & 1 else list(range(inst["batch_count"]))
        batches = [dict(inst["batches"][old]) for old in use_order]
        new_b = use_order.index(old_b)
        new_i = old_i
        if mask & 2:
            for spec in batches:
                spec["reverse"] = not spec["reverse"]
            new_i = inst["points_per_batch"] - 1 - new_i
        transformed = {
            "n": inst["n"],
            "batch_count": inst["batch_count"],
            "points_per_batch": inst["points_per_batch"],
            "denominator": inst["denominator"],
            "batches": batches,
            "swap_xy": inst["swap_xy"] ^ bool(mask & 4),
            "answer": {
                "blocker": [new_b, new_i],
                "side": list(inst["answer"]["side"]),
            },
        }
        variants.append(transformed)
    return variants


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest():
    report = {}
    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]

    g1_failures = []
    attempts = 0
    # Several seeds at every rung; the very large rungs get two because each
    # verification deliberately performs the full mechanical scan.
    for preset, params in DIFFICULTY.items():
        seeds = (0, 1, 7) if preset == "demo" else (0, 1)
        for seed in seeds:
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                g1_failures.append([preset, seed, why])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": attempts,
        "failures": g1_failures,
    }

    inst = make_instance(seed=19, **shipping)
    answer = inst["answer"]
    corruptions = {
        "drop": {"blocker": list(answer["blocker"])},
        "swap": {
            "blocker": list(answer["side"]),
            "side": list(answer["blocker"]),
        },
        "duplicate": {
            "blocker": list(answer["blocker"]),
            "side": list(answer["side"]),
            "again": list(answer["side"]),
        },
        "empty": {},
        "out_of_range": {
            "blocker": list(answer["blocker"]),
            "side": [answer["side"][0], 0],
        },
    }
    rejected = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        rejected[name] = {"rejected": not ok, "reason": why}
    reasons = [item["reason"] for item in rejected.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in rejected.values())
        and len(set(reasons)) == len(reasons),
        "cases": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    b, i = answer["blocker"]
    p, q = answer["side"]
    response = (
        "The affine crossing identifies this boundary point.\n```text\n"
        f"<answer>{b}, {i}, {p}/{q}</answer>\n```\n"
        "The fraction is intentionally left unreduced."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == answer,
    }

    # One scan establishes the unique valid blocker.  Sampling then compares
    # candidates with that independently found result instead of paying 200,000
    # full scans of a million-point instance.
    scan_start = time.perf_counter()
    best, best_points, operations = _scan_minimum(inst)
    scan_seconds = time.perf_counter() - scan_start
    guess_rng = random.Random(0x180609562)
    guess_total = 200_000
    guess_hits = 0
    guess_start = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(inst, guess_rng)
        guess_hits += int(_is_scan_witness(inst, candidate, best, best_points))
    guess_seconds = time.perf_counter() - guess_start
    guess_fraction = guess_hits / guess_total
    exact_density = len(best_points) / search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": exact_density < 1e-6 and guess_total >= 200_000,
        "hits": guess_hits,
        "total": guess_total,
        "sampled_fraction": guess_fraction,
        "exact_fraction": exact_density,
        "valid_blockers": len(best_points),
        "candidate_space": search_space(inst),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    attack_names = [
        "outlier_min_x_coordinate",
        "outlier_min_y_coordinate",
        "greedy_min_coordinate_sum",
        "by_hand_midpoint",
        "by_hand_offset_blind_crossing",
        "random_restart_256",
    ]
    successes = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    compact_successes = 0
    reference_seconds = 0.0
    reference_operations = 0
    for seed in range(101, 109):
        trial = make_instance(seed=seed, **shipping)
        start = time.perf_counter()
        trial_best, trial_points, trial_operations = _scan_minimum(trial)
        reference_seconds += time.perf_counter() - start
        reference_operations += trial_operations
        reference_candidate = _candidate_for_point(trial, *trial_points[0])
        reference_successes += int(verify(trial, reference_candidate)[0])

        candidates = {
            "outlier_min_x_coordinate": [_endpoint_min_coordinate(trial, 0)],
            "outlier_min_y_coordinate": [_endpoint_min_coordinate(trial, 1)],
            "greedy_min_coordinate_sum": [_greedy_coordinate_sum(trial)],
            "by_hand_midpoint": [_midpoint_candidate(trial)],
            "by_hand_offset_blind_crossing": [_offset_blind_crossing(trial)],
        }
        rrng = random.Random(seed ^ 0x180609562)
        candidates["random_restart_256"] = [
            random_candidate(trial, rrng) for _ in range(256)
        ]
        for name in attack_names:
            start = time.perf_counter()
            won = any(
                _is_scan_witness(trial, candidate, trial_best, trial_points)
                for candidate in candidates[name]
            )
            attack_seconds[name] += time.perf_counter() - start
            successes[name] += int(won)

        compact = _compact_solve(trial)
        compact_successes += int(
            _is_scan_witness(trial, compact, trial_best, trial_points)
            and verify(trial, compact)[0]
        )

    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_seconds[name], 6),
        }
        for name in attack_names
    }
    all_failed = all(value == 0 for value in successes.values())
    reference = {
        "name": "direct exact closest-blocker scan",
        "complexity": "O(n) exact integer operations for the named anchor",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": reference_operations // 8,
        "solves": f"{reference_successes}/8, as expected",
    }
    intended_operations = 30 * inst["batch_count"]
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
        "intended_compact_route": {
            "name": "affine cancellation of the quadratic coordinate difference",
            "solves": f"{compact_successes}/8",
            "operations_upper_bound": intended_operations,
        },
    }

    demo_count = enumerate_all(make_instance(seed=3, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline_cost"] = {
        "pass": exact_density < 1e-6
        and len(best_points) == 1
        and demo_count == 1
        and all_failed
        and reference_successes == 8,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_solution_density": guess_fraction,
        "shipping_exact_valid_count": len(best_points),
        "shipping_exact_density": exact_density,
        "demo_exact_solution_count": demo_count,
        "baseline_attack_wall_clock_sec": round(
            attack_seconds["random_restart_256"] / 8, 6
        ),
        "baseline_attack_iterations": 256,
        "reference_wall_clock_sec": reference["wall_clock_sec"],
        "reference_operation_count": reference["operations"],
        "single_shipping_scan_wall_clock_sec": round(scan_seconds, 6),
        "single_shipping_scan_operations": operations,
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    start = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_build = time.perf_counter() - start
    start = time.perf_counter()
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    doubled_verify = time.perf_counter() - start
    ladder = [DIFFICULTY[name]["n"] for name in DIFFICULTY]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] == 2 * inst["n"]
        and search_space(doubled) == 2 * search_space(inst)
        and ladder == sorted(ladder)
        and len(set(ladder)) == len(ladder),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_sec": round(doubled_verify, 6),
        "doubled_verify_reason": doubled_why,
        "reference_operations_shipping": 9 * inst["n"],
        "reference_operations_doubled": 9 * doubled["n"],
    }

    invariant_count = 0
    real_transform_count = 0
    unrelated_keys = []
    # Use a moderate exact set for this structural test: canonicalization depends
    # only on the batch formulas, not on expanding their points.
    key_params = {"n": 8_008, "batches": 8, "scale": 1_000}
    for seed in range(201, 221):
        original = make_instance(seed=seed, **key_params)
        key = canonical_key(original)
        for transformed in _relabel_variants(original, seed ^ 0x5A5A):
            invariant_count += int(key == canonical_key(transformed))
            real_transform_count += int(
                verify(transformed, transformed["answer"])[0]
            )
        unrelated_keys.append(key)
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_count == 140
        and real_transform_count == 140
        and distinct_count == 20,
        "invariant_relabellings": invariant_count,
        "real_transformations_verified": real_transform_count,
        "unrelated_distinct_keys": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "batch permutation with carried blocker label",
            "reversal of every within-batch index with carried blocker index",
            "reflection across x=y",
            "all nonempty compositions of those three transformations",
        ],
    }

    encoded = json.dumps(answer, separators=(",", ":"))
    answer_chars = len(encoded)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(answer)
    worst = json.dumps(
        {
            "blocker": [inst["batch_count"] - 1, inst["points_per_batch"] - 1],
            "side": [inst["denominator"], inst["denominator"]],
        },
        separators=(",", ":"),
    )
    worst_tokens = math.ceil(len(worst) / 4)
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] >= worst_tokens
    )
    report["G9_no_tool_suitability"] = {
        "pass": G9_ORACLE_RESULTS["hinted_verdict"] == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "worst_case_answer_chars": len(worst),
        "worst_case_answer_tokens": worst_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") is True for value in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
