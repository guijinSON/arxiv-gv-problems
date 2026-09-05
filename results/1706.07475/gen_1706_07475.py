"""Verified Track-B generator for connected r-domination on affine paths.

The source is arXiv:1706.07475, especially the definition of Connected
r-Domination in Sections 1--2 and the layering-partition construction in
Section 3.  The first step of that construction computes a minimum connected
r-dominating subtree of a tree in linear time.

Each generated graph is a path whose vertex names are affinely scrambled.
Its radius function is a composed modular polynomial with two planted zeros.
Those zeros force the two ends of the unique minimum connected dominating
interval.  The certificate is carried through the affine maps; it is never
found by solving the emitted instance.
"""

from __future__ import annotations

import json
import math
import os
import random
import re
import time
from functools import lru_cache


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "finite unweighted undirected path under an affine vertex relabelling",
        "integer vertex-radius function",
        "connected r-dominating vertex set",
    ],
    "verification_operations": [
        "exact modular inversion and substitution",
        "integer path-coordinate adjacency",
        "exact connected-interval extremal-bound comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Undo the affine radius coordinates and use the extrema of t+r(t) and "
        "t-r(t) that force a connected interval; without this change of "
        "variables one scans the entire path."
    ),
    "hardness_basis": (
        "Track B: Section 3 (the minimum r-dominating subtree step before "
        "Lemma 2, and Theorem 2) supplies a linear-time tree algorithm; at the "
        "shipping preset n=1,200,007 with three radius encodings, the measured "
        "specialized scan performs 15,600,100 exact operations in 1.89 seconds "
        "per instance, while the "
        "affine-extremizer route uses under 160 exact operations and requires "
        "several exact modular inversions that are not mechanically executable "
        "at full scan scale without tools."
    ),
    "max_answer_tokens": 33,
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
    "demo": {"n": 37, "witness_size": 5, "encoding_layers": 1},
    "easy": {"n": 1_200_007, "witness_size": 16, "encoding_layers": 3},
    "medium": {"n": 3_000_017, "witness_size": 16, "encoding_layers": 4},
    "hard": {"n": 7_000_003, "witness_size": 16, "encoding_layers": 4},
}

SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "On a path, a connected set is an interval whose forced endpoints are the "
    "extremal values of t+r(t) and t-r(t)."
)

PLACEBO_HINT = (
    "The least-nonnegative-residue convention matters throughout, and every "
    "submitted label must remain inside the stated vertex range."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "An unordered JSON list of exactly k distinct vertex labels from "
        "0,...,n-1 whose vertices form one connected k-vertex block of the "
        "stated path; random candidates are uniform over its n-k+1 blocks."
    ),
    "bounds": {
        "atomic_elements": "k",
        "label_min": 0,
        "label_max": "n-1",
        "distinct": True,
        "connected_path_block": True,
        "candidate_count": "n-k+1",
    },
}

NOTES = (
    "Sections 1 and 2 fix r-domination using the radius of the vertex being "
    "served, and require the selected set to induce a connected subgraph. "
    "Section 3, immediately before Lemma 2, states that a minimum connected "
    "r-dominating subtree is computable in linear time; Theorem 2 uses that "
    "routine in the paper's connected approximation algorithm.  Thus this "
    "tree distribution cannot honestly be Track A.  For path coordinate t the "
    "constructed radius is c+n*q(t)^2.  The modular q has exactly two zeros "
    "z0<z1, planted with z1-z0=2c+k-1.  Consequently min(t+r(t))=z0+c and "
    "max(t-r(t))=z1-c, so their unique minimum connected interval has k "
    "vertices.  The generator carries that interval through every affine map. "
    "Graph-label and radius-label maps are independently uniform, the two "
    "small-radius vertices lie outside the answer, and the answer vertices are "
    "ordinary degree-two vertices.  This defeats degree, numeric-label, raw-"
    "root, one-layer-inversion, and short random-restart attacks; the declared "
    "linear scan still solves every instance, as Track B requires."
)


# Filled from the script-owned hardening runs after all three arms are executed.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run_openrouter_quota",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_prime(value):
    """Deterministic Miller--Rabin for the 64-bit range used here."""
    if not _is_int(value) or value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small:
        if value == prime:
            return True
        if value % prime == 0:
            return False
    d = value - 1
    power = 0
    while d % 2 == 0:
        power += 1
        d //= 2
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if base % value == 0:
            continue
        x = pow(base, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(power - 1):
            x = x * x % value
            if x == value - 1:
                break
        else:
            return False
    return True


def _next_prime(value):
    candidate = max(3, value | 1)
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _validate_parameters(n, witness_size, encoding_layers):
    if not _is_prime(n):
        raise ValueError("n must be a prime")
    if not _is_int(witness_size) or witness_size < 1 or witness_size > 256:
        raise ValueError("witness_size must be an integer in 1..256")
    if not _is_int(encoding_layers) or not 1 <= encoding_layers <= 4:
        raise ValueError("encoding_layers must be an integer in 1..4")
    if n < 6 * witness_size + 7:
        raise ValueError("n is too small for the planted interior interval")


def _random_nonzero(rng, modulus):
    # The modulus is prime, so every nonzero residue is a unit.
    return rng.randrange(1, modulus)


def _apply_layers(value, layers, modulus):
    for multiplier, offset in layers:
        value = (multiplier * value + offset) % modulus
    return value


@lru_cache(maxsize=512)
def _mod_inverse(value, modulus):
    return pow(value, -1, modulus)


def _invert_layers(value, layers, modulus):
    for multiplier, offset in reversed(layers):
        value = ((value - offset) * _mod_inverse(multiplier, modulus)) % modulus
    return value


@lru_cache(maxsize=256)
def _decode_roots_cached(modulus, layers, roots):
    decoded = []
    for root in roots:
        value = root
        for multiplier, offset in reversed(layers):
            value = (
                (value - offset) * _mod_inverse(multiplier, modulus)
            ) % modulus
        decoded.append(value)
    return tuple(sorted(decoded))


def _decode_tight_coordinates(inst):
    modulus = inst["n"]
    layers = tuple(tuple(layer) for layer in inst["radius_layers"])
    encoded_roots = tuple(inst["encoded_roots"])
    roots = _decode_roots_cached(
        modulus, layers, encoded_roots
    )
    if len(roots) != 2 or roots[0] == roots[1]:
        raise ValueError("encoded radius roots are not two distinct coordinates")
    return roots[0], roots[1]


def _path_label(inst, coordinate):
    return (inst["path_start"] + inst["path_step"] * coordinate) % inst["n"]


def _path_coordinate(inst, label):
    return (
        (label - inst["path_start"])
        * _mod_inverse(inst["path_step"], inst["n"])
    ) % inst["n"]


def _radius_at_coordinate(inst, coordinate):
    modulus = inst["n"]
    encoded = _apply_layers(coordinate, inst["radius_layers"], modulus)
    first, second = inst["encoded_roots"]
    q_value = ((encoded - first) * (encoded - second)) % modulus
    return inst["slack"] + modulus * q_value * q_value


def _bounds_from_structure(inst):
    left_zero, right_zero = _decode_tight_coordinates(inst)
    left = left_zero + inst["slack"]
    right = right_zero - inst["slack"]
    return left, right


def make_instance(n, seed=0, witness_size=16, encoding_layers=3) -> dict:
    """Inverse-generate a uniquely optimal connected r-dominating interval.

    The answer endpoints and the two zero coordinates are sampled first.  The
    radius identity and affine relabellings are composed around them.  No graph
    search, domination algorithm, or certificate recovery is run here.
    """
    _validate_parameters(n, witness_size, encoding_layers)
    rng = random.Random(seed)

    # The two radius minima sit well outside the answer.  Their common radius c
    # is deliberately not an outlier of the answer vertices themselves.
    c_min = max(2, n // 7)
    c_max = max(c_min + 1, n // 4)
    slack = rng.randrange(c_min, c_max)
    root_gap = 2 * slack + witness_size - 1
    margin = max(2, witness_size)
    room = n - root_gap - 2 * margin
    if room <= 0:
        raise ValueError("parameters leave no room for the planted interval")
    left_zero = margin + rng.randrange(room)
    right_zero = left_zero + root_gap
    left = left_zero + slack
    right = right_zero - slack

    path_step = _random_nonzero(rng, n)
    path_start = rng.randrange(n)
    layers = [
        [_random_nonzero(rng, n), rng.randrange(n)]
        for _ in range(encoding_layers)
    ]
    encoded_roots = [
        _apply_layers(left_zero, layers, n),
        _apply_layers(right_zero, layers, n),
    ]
    rng.shuffle(encoded_roots)

    answer = [
        (path_start + path_step * coordinate) % n
        for coordinate in range(left, right + 1)
    ]
    return {
        "n": n,
        "k": witness_size,
        "path_start": path_start,
        "path_step": path_step,
        "slack": slack,
        "radius_layers": layers,
        "encoded_roots": encoded_roots,
        "answer": answer,
    }


def render(inst) -> str:
    """Render a complete, self-contained problem statement."""
    layers = "\n".join(
        f"  {index}: u <- ({multiplier}*u + {offset}) mod {inst['n']}"
        for index, (multiplier, offset) in enumerate(inst["radius_layers"], 1)
    )
    example = ", ".join(str(i) for i in range(inst["k"]))
    statement = f"""CONNECTED VERTEX-RADIUS DOMINATION ON AN AFFINELY LABELLED PATH

All arithmetic described as `mod n` uses the least nonnegative residue.

The graph has n = {inst['n']} vertices, labelled by the integers 0 through
{inst['n'] - 1}.  For a label x, its path coordinate t(x) is the unique integer
in 0,...,n-1 satisfying

    x = {inst['path_start']} + {inst['path_step']}*t(x)  (mod {inst['n']}).

Two vertices are adjacent exactly when their ordinary integer path coordinates
differ by 1.  In particular coordinates 0 and n-1 are not adjacent, so this is
a path rather than a cycle.  Every edge has length 1, and graph distance is the
minimum number of edges in a path.

Each vertex x has an integer service radius r(x).  To compute it, start with
u = t(x), apply every line below in the displayed order,

{layers}

then set

    q = ((u - {inst['encoded_roots'][0]})*(u - {inst['encoded_roots'][1]})) mod {inst['n']}
    r(x) = {inst['slack']} + {inst['n']}*q^2.

A set D r-dominates the graph when, for every vertex x, the distance from x to
the nearest vertex of D is at most r(x).  It is connected when the subgraph
induced by D is connected.  Find a connected r-dominating set containing
exactly k = {inst['k']} distinct vertices.  The instance promises that k is the
minimum possible cardinality.  Vertex order in your answer is irrelevant.

Give your final answer inside <answer></answer> tags, as one JSON list of exactly
{inst['k']} comma-separated integer labels in 0,...,{inst['n'] - 1}.
Example of the required syntax: <answer>[{example}]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Extract a list of integer labels from tagged model output."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, re.I | re.S)
    if not matches:
        return None
    for body in reversed(matches):
        cleaned = body.strip()
        fence = re.fullmatch(
            r"```(?:json|python|text)?\s*(.*?)\s*```", cleaned, re.I | re.S
        )
        if fence:
            cleaned = fence.group(1).strip()
        try:
            value = json.loads(cleaned)
        except (TypeError, ValueError):
            if not re.fullmatch(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*", cleaned):
                continue
            try:
                value = [int(part.strip()) for part in cleaned.split(",")]
            except ValueError:
                continue
        if isinstance(value, list) and all(_is_int(item) for item in value):
            return value
    return None


def verify(inst, answer):
    """Check any valid optimum witness without consulting inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer_not_a_list"
    if not answer:
        return False, "empty_answer"
    if len(answer) != inst["k"]:
        return False, "wrong_length"
    if not all(_is_int(label) for label in answer):
        return False, "non_integer_label"
    if any(label < 0 or label >= inst["n"] for label in answer):
        return False, "label_out_of_range"
    if len(set(answer)) != len(answer):
        return False, "duplicate_label"

    try:
        coordinates = sorted(_path_coordinate(inst, label) for label in answer)
        left_bound, right_bound = _bounds_from_structure(inst)
    except (TypeError, ValueError, ZeroDivisionError):
        return False, "malformed_instance_structure"

    if any(b != a + 1 for a, b in zip(coordinates, coordinates[1:])):
        return False, "selected_subgraph_disconnected"
    if coordinates[0] > left_bound:
        return False, "left_boundary_not_dominated"
    if coordinates[-1] < right_bound:
        return False, "right_boundary_not_dominated"
    if right_bound - left_bound + 1 != inst["k"]:
        return False, "minimum_size_promise_inconsistent"

    # A connected k-set is one interval.  The two exact inequalities above are
    # necessary and sufficient for all vertices because min(t+r(t))=left_bound
    # and max(t-r(t))=right_bound for this checked modular-square construction.
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from all connected k-vertex subsets of the path."""
    start = rng.randrange(inst["n"] - inst["k"] + 1)
    return [_path_label(inst, t) for t in range(start, start + inst["k"])]


def search_space(inst):
    """Count connected k-vertex blocks, the structure-aware language."""
    return inst["n"] - inst["k"] + 1


def enumerate_all(inst):
    """Brute-force every connected block when the exact work is small."""
    space = search_space(inst)
    if space > 100_000:
        return None
    valid = 0
    for start in range(space):
        candidate = [_path_label(inst, t) for t in range(start, start + inst["k"])]
        valid += int(verify(inst, candidate)[0])
    return valid


def _total_radius_multiplier(inst):
    multiplier = 1
    for factor, _ in inst["radius_layers"]:
        multiplier = multiplier * factor % inst["n"]
    return multiplier


def canonical_key(inst):
    """Canonical invariant under path reflection and affine label renaming."""
    left_zero, right_zero = _decode_tight_coordinates(inst)
    reflected = (inst["n"] - 1 - right_zero, inst["n"] - 1 - left_zero)
    normalized_roots = min((left_zero, right_zero), reflected)
    # Offsets cancel from q; the total multiplier enters q only through H^2.
    scale = pow(_total_radius_multiplier(inst), 2, inst["n"])
    data = [
        inst["n"],
        inst["k"],
        inst["slack"],
        list(normalized_roots),
        scale,
    ]
    return json.dumps(data, separators=(",", ":"))


def _euclid_steps(value, modulus):
    steps = 0
    a, b = modulus, value % modulus
    while b:
        a, b = b, a % b
        steps += 1
    return steps


def _compact_operation_count(inst):
    inverse_steps = sum(
        _euclid_steps(multiplier, inst["n"])
        for multiplier, _ in inst["radius_layers"]
    )
    return (
        inverse_steps
        + 6 * len(inst["radius_layers"])
        + 3 * inst["k"]
        + 5
    )


def _reference_operation_count(inst):
    return 13 * inst["n"] + 3 * len(inst["radius_layers"])


def _reference_linear_scan(inst):
    """Mechanical O(nL) path algorithm; intentionally scans every vertex."""
    modulus = inst["n"]
    # A standard preprocessing pass composes the displayed affine encodings.
    total_multiplier = 1
    total_offset = 0
    for multiplier, offset in inst["radius_layers"]:
        total_multiplier = multiplier * total_multiplier % modulus
        total_offset = (multiplier * total_offset + offset) % modulus
    encoded = total_offset
    first, second = inst["encoded_roots"]
    minimum_left = None
    maximum_right = None
    for coordinate in range(inst["n"]):
        q_value = ((encoded - first) * (encoded - second)) % modulus
        radius = inst["slack"] + modulus * q_value * q_value
        left_value = coordinate + radius
        right_value = coordinate - radius
        if minimum_left is None or left_value < minimum_left:
            minimum_left = left_value
        if maximum_right is None or right_value > maximum_right:
            maximum_right = right_value
        encoded += total_multiplier
        if encoded >= modulus:
            encoded -= modulus
    return [
        _path_label(inst, coordinate)
        for coordinate in range(minimum_left, maximum_right + 1)
    ]


def _compact_solution(inst):
    left, right = _bounds_from_structure(inst)
    return [_path_label(inst, coordinate) for coordinate in range(left, right + 1)]


def _block_at(inst, start):
    start = max(0, min(inst["n"] - inst["k"], int(start)))
    return [_path_label(inst, t) for t in range(start, start + inst["k"])]


def _attack_candidates(inst):
    k = inst["k"]
    n = inst["n"]
    roots = inst["encoded_roots"]

    # Degree-one vertices suggest an endpoint block, but the answer is interior.
    endpoint_block = _block_at(inst, 0)

    # Numeric labels ignore the independent affine path relabelling.
    numeric_labels = list(range(k))

    # Treat the two encoded q-roots as if they were already path coordinates.
    raw_root_start = (min(roots) + inst["slack"]) % (n - k + 1)
    raw_root_block = _block_at(inst, raw_root_start)

    # A plausible by-hand shortcut: undo only the final displayed affine layer.
    multiplier, offset = inst["radius_layers"][-1]
    inverse = pow(multiplier, -1, n)
    partial = sorted(((root - offset) * inverse) % n for root in roots)
    one_layer_start = (partial[0] + inst["slack"]) % (n - k + 1)
    one_layer_block = _block_at(inst, one_layer_start)
    return {
        "degree_endpoint_block": endpoint_block,
        "greedy_smallest_numeric_labels": numeric_labels,
        "raw_encoded_root_block": raw_root_block,
        "single_layer_inverse_ansatz": one_layer_block,
    }


def _affine_relabel(inst, multiplier, shift):
    modulus = inst["n"]
    transformed = {
        key: json.loads(json.dumps(value))
        for key, value in inst.items()
        if key != "answer"
    }
    transformed["path_start"] = (
        multiplier * inst["path_start"] + shift
    ) % modulus
    transformed["path_step"] = multiplier * inst["path_step"] % modulus
    transformed["answer"] = [
        (multiplier * label + shift) % modulus for label in inst["answer"]
    ]
    return transformed


def _reflect_path_representation(inst):
    modulus = inst["n"]
    transformed = json.loads(json.dumps(inst))
    old_step = transformed["path_step"]
    transformed["path_start"] = (
        transformed["path_start"] + old_step * (modulus - 1)
    ) % modulus
    transformed["path_step"] = (-old_step) % modulus
    first_multiplier, first_offset = transformed["radius_layers"][0]
    transformed["radius_layers"][0] = [
        (-first_multiplier) % modulus,
        (first_multiplier * (modulus - 1) + first_offset) % modulus,
    ]
    return transformed


def _collapse_layers(inst):
    modulus = inst["n"]
    multiplier = 1
    offset = 0
    for factor, translation in inst["radius_layers"]:
        multiplier = factor * multiplier % modulus
        offset = (factor * offset + translation) % modulus
    transformed = json.loads(json.dumps(inst))
    transformed["radius_layers"] = [[multiplier, offset]]
    return transformed


def _swap_roots(inst):
    transformed = json.loads(json.dumps(inst))
    transformed["encoded_roots"].reverse()
    return transformed


def escalate(params):
    """Grow the path and, until capped, the encoding at fixed answer length."""
    current_n = int(params["n"])
    current_layers = int(params.get("encoding_layers", 1))
    witness_size = int(params.get("witness_size", 16))
    next_n = _next_prime(2 * current_n + 1)
    next_layers = min(4, current_layers + 1)

    # A conservative extended-Euclid bound protects the 300-operation compact
    # route cap even after repeated external escalations.
    projected = (
        2 * next_n.bit_length() * next_layers
        + 6 * next_layers
        + 3 * witness_size
        + 5
    )
    worst_chars = 2 + witness_size * len(str(next_n - 1)) + witness_size - 1
    if projected > 300 or worst_chars > 2_000:
        return "cap_bound"
    out = dict(params)
    out["n"] = next_n
    out["encoding_layers"] = next_layers
    out["witness_size"] = witness_size
    return out


def _atomic_elements(value):
    if isinstance(value, dict):
        return sum(_atomic_elements(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atomic_elements(item) for item in value)
    return 1


def selftest():
    """Run all mandatory construction, parsing, attack, scale, and size gates."""
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    # G1: every preset over several seeds, including JSON-native certificates.
    g1_attempts = 0
    g1_verified = 0
    json_native = True
    prime_checks = {}
    for preset, params in DIFFICULTY.items():
        prime_checks[preset] = _is_prime(params["n"])
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            ok, _ = verify(inst, inst["answer"])
            g1_attempts += 1
            g1_verified += int(ok)
            json_native &= json.loads(json.dumps(inst["answer"])) == inst["answer"]
    report["G1_planted_verifies"] = {
        "pass": (
            g1_verified == g1_attempts
            and json_native
            and all(prime_checks.values())
        ),
        "verified": g1_verified,
        "attempts": g1_attempts,
        "answer_json_native": json_native,
        "preset_moduli_prime": prime_checks,
        "generation_route": "inverse generation plus composition of affine identities",
    }

    shipping_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    inst = make_instance(seed=12_345, **shipping_params)
    planted = list(inst["answer"])
    left, right = _bounds_from_structure(inst)

    # G2: distinct corruptions deliberately reach distinct verifier checks.
    shifted = _block_at(inst, left + 1)
    corruptions = {
        "drop_one": planted[:-1],
        "swap_one_element": shifted,
        "duplicate_one": planted[:-1] + [planted[-2]],
        "empty": [],
        "out_of_range": planted[:-1] + [inst["n"]],
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = {item["reason"] for item in corruption_results.values()}
    report["G2_rejects_corruption"] = {
        "pass": (
            all(item["rejected"] for item in corruption_results.values())
            and len(reasons) == len(corruption_results)
        ),
        "corruptions": corruption_results,
        "distinct_reasons": len(reasons),
    }

    # G3: realistic surrounding prose, markdown fencing, and garbage handling.
    encoded = json.dumps(planted, separators=(",", ":"))
    response = (
        "The two extremal constraints give one interval.\n"
        f"<answer>\n```json\n{encoded}\n```\n</answer>\n"
        "Those are vertex labels, not path coordinates."
    )
    parsed = parse_answer(response)
    garbage = parse_answer("No tagged final answer is present here.")
    report["G3_round_trip"] = {
        "pass": parsed == planted and garbage is None,
        "realistic_response_recovered": parsed == planted,
        "garbage_returns_none": garbage is None,
    }

    # G4: exact structure-aware prior, uniform over connected k-blocks.
    guess_rng = random.Random(0x170607475)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_fraction = guess_hits / guess_total
    exact_density = 1 / search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": guess_total >= 200_000 and guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_fraction,
        "exact_probability": exact_density,
        "candidate_space": search_space(inst),
        "sampling_prior": "uniform over connected k-vertex path blocks",
    }

    # G6: five failing no-tool attacks and the successful Track-B reference scan.
    attack_names = (
        "degree_endpoint_block",
        "greedy_smallest_numeric_labels",
        "raw_encoded_root_block",
        "single_layer_inverse_ansatz",
        "random_restart_256",
    )
    successes = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    compact_successes = 0
    compact_seconds = 0.0
    compact_counts = []

    for seed in range(80, 88):
        test_inst = make_instance(seed=seed, **shipping_params)
        for name, candidate in _attack_candidates(test_inst).items():
            started = time.perf_counter()
            solved = verify(test_inst, candidate)[0]
            attack_seconds[name] += time.perf_counter() - started
            successes[name] += int(solved)

        restart_rng = random.Random(seed ^ 0xBAD5EED)
        started = time.perf_counter()
        restart_solved = False
        for _ in range(256):
            if verify(test_inst, random_candidate(test_inst, restart_rng))[0]:
                restart_solved = True
                break
        attack_seconds["random_restart_256"] += time.perf_counter() - started
        successes["random_restart_256"] += int(restart_solved)

        started = time.perf_counter()
        reference = _reference_linear_scan(test_inst)
        reference_seconds += time.perf_counter() - started
        reference_successes += int(verify(test_inst, reference)[0])

        started = time.perf_counter()
        compact = _compact_solution(test_inst)
        compact_seconds += time.perf_counter() - started
        compact_successes += int(verify(test_inst, compact)[0])
        compact_counts.append(_compact_operation_count(test_inst))

    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_seconds[name], 6),
        }
        for name in attack_names
    }
    reference_ops = _reference_operation_count(inst)
    compact_ops = max(compact_counts + [_compact_operation_count(inst)])
    reference_algorithm = {
        "name": "linear scan for the minimum connected r-dominating interval on a tree",
        "complexity": "O(n+L) exact after composing L affine radius encodings",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": reference_ops,
        "solves": f"{reference_successes}/8, as expected",
    }
    all_attacks_failed = all(value == 0 for value in successes.values())
    report["G6_adversary_panel"] = {
        "pass": (
            all_attacks_failed
            and reference_successes == 8
            and compact_successes == 8
        ),
        "attacks": attacks,
        "reference_algorithm": reference_algorithm,
        "intended_compact_route": {
            "name": "invert affine radius coordinates and use interval extremizers",
            "operations_worst_of_8": compact_ops,
            "wall_clock_sec": round(compact_seconds / 8, 6),
            "solves": f"{compact_successes}/8",
        },
    }

    # G5: shipping density and measured strongest/reference costs, both numeric.
    demo_count = enumerate_all(make_instance(seed=3, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline_cost"] = {
        "pass": (
            guess_fraction < 1e-6
            and demo_count == 1
            and all_attacks_failed
            and reference_successes == 8
        ),
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_sampled_solution_density": guess_fraction,
        "shipping_exact_density_from_interval_identity": exact_density,
        "shipping_exact_solution_count_from_interval_identity": 1,
        "demo_bruteforce_solution_count": demo_count,
        "baseline_random_restart_iterations": 256,
        "baseline_random_restart_wall_clock_sec": round(
            attack_seconds["random_restart_256"] / 8, 6
        ),
        "reference_wall_clock_sec": reference_algorithm["wall_clock_sec"],
        "reference_operation_count": reference_ops,
    }

    # G7: more vertices and encodings enlarge the haystack at fixed witness size.
    doubled_params = dict(shipping_params)
    doubled_params["n"] = _next_prime(2 * doubled_params["n"] + 1)
    doubled_params["encoding_layers"] = min(
        4, doubled_params["encoding_layers"] + 1
    )
    started = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_build_seconds = time.perf_counter() - started
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    costs = [
        13 * params["n"] + 3 * params["encoding_layers"]
        for params in DIFFICULTY.values()
    ]
    report["G7_scales"] = {
        "pass": (
            doubled_ok
            and doubled["n"] > 2 * inst["n"]
            and doubled["k"] == inst["k"]
            and search_space(doubled) > 2 * search_space(inst)
            and costs == sorted(costs)
            and len(set(costs)) == len(costs)
        ),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "shipping_encoding_layers": len(inst["radius_layers"]),
        "doubled_encoding_layers": len(doubled["radius_layers"]),
        "answer_atoms_shipping": _atomic_elements(inst["answer"]),
        "answer_atoms_doubled": _atomic_elements(doubled["answer"]),
        "doubled_build_sec": round(doubled_build_seconds, 6),
        "doubled_verify_reason": doubled_reason,
        "reference_operations_shipping": _reference_operation_count(inst),
        "reference_operations_doubled": _reference_operation_count(doubled),
    }

    # G8: label relabelling, reflection, root order, representation collapse,
    # and compositions.  Every map is checked on 20 independently seeded inputs.
    invariant_count = 0
    real_transform_count = 0
    unrelated_keys = []
    transformations_per_seed = 7
    for seed in range(201, 221):
        original = make_instance(seed=seed, **shipping_params)
        key = canonical_key(original)
        reflected = _reflect_path_representation(original)
        variants = (
            _affine_relabel(original, 2, 1),
            _affine_relabel(original, 3, 37),
            _swap_roots(original),
            reflected,
            _collapse_layers(original),
            _affine_relabel(reflected, 5, 91),
            _collapse_layers(_affine_relabel(_swap_roots(reflected), 7, 112)),
        )
        for transformed in variants:
            invariant_count += int(canonical_key(transformed) == key)
            real_transform_count += int(verify(transformed, transformed["answer"])[0])
        unrelated_keys.append(key)
    expected_invariants = 20 * transformations_per_seed
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": (
            invariant_count == expected_invariants
            and real_transform_count == expected_invariants
            and distinct_count == 20
        ),
        "invariant_relabellings": invariant_count,
        "invariant_attempts": expected_invariants,
        "real_transformations_verified": real_transform_count,
        "unrelated_distinct_keys": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "two affine vertex-label permutations",
            "encoded-root order swap",
            "path-coordinate reflection",
            "equivalent affine-layer collapse",
            "reflection composed with affine relabelling",
            "root swap, reflection, affine relabelling, and layer collapse composed",
        ],
    }

    # G9: arm outcomes are external diagnostics; only exact size/effort caps gate.
    encoded_answer = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(encoded_answer)
    answer_tokens = math.ceil(answer_chars / 4)
    worst_answer = [inst["n"] - 1] * inst["k"]
    worst_chars = len(json.dumps(worst_answer, separators=(",", ":")))
    worst_tokens = math.ceil(worst_chars / 4)
    answer_elements = _atomic_elements(inst["answer"])
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and compact_ops <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] == worst_tokens
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "worst_case_answer_chars": worst_chars,
        "worst_case_answer_tokens": worst_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": compact_ops,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
