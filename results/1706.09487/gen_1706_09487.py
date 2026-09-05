"""Verified problem generator for arXiv:1706.09487.

The native problem is Seeded Highly Connected Edge Deletion from Section 3.1.
The generated graph is an exact finite-field power-fibre graph: its components
are cliques, and a supplied seed selects one clique.  The selected fibre and a
compressed deletion witness are carried through construction by a root-of-unity
identity; generation never searches the graph it has just made.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time


# Keep the repository helpers importable when harden.py is launched here.  This
# family needs only the standard library, so a missing gvlib is harmless.
sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ),
)
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "finite undirected graph specified by an exact adjacency rule",
        "seeded vertex set",
        "highly connected induced component",
        "compressed edge-deletion set",
    ],
    "verification_operations": [
        "finite-field modular exponentiation",
        "exact induced-degree comparison",
        "exact edge-count comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "The seed component is a power-map fibre, so an order-s root of unity "
        "generates it without scanning the graph; without recognizing that "
        "symmetry one mechanically tests every residue."
    ),
    "hardness_basis": (
        "Track B: exhaustive exact power-residue scanning solves this structured "
        "Seeded Highly Connected Edge Deletion subclass in O(p log s), averaging "
        "141,557,859 exact modular operations and 4.65 seconds at the shipping "
        "preset, whereas the root-of-unity fibre route uses at most 73 "
        "exact operations; Theorem 4 also gives the paper's generic "
        "2^{O(sqrt(k) log k)} algorithm."
    ),
    "max_answer_tokens": 16,
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
    "demo": {"n": 13, "s": 4, "spread": 0},
    "easy": {"n": 524_288, "s": 8, "spread": 8_192},
    "medium": {"n": 4_194_304, "s": 8, "spread": 65_536},
    "hard": {"n": 33_554_432, "s": 8, "spread": 524_288},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The seed's clique is the fibre of a power map under multiplication by "
    "the order-s roots of unity."
)
PLACEBO_HINT = (
    "The modular graph rewards careful attention to the stated residue and "
    "indexing conventions."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "An unordered JSON list of exactly s-1 distinct graph vertices, excluding "
        "the supplied seed; together with the seed these vertices define the one "
        "retained component, and every graph edge not wholly inside it is deleted."
    ),
    "bounds": {
        "answer_vertices": "s-1, with generated s in {4,8}",
        "vertex_range": "0..p-1 except the omitted residue shift",
        "distinct": True,
        "order_matters": False,
        "max_atomic_elements": 7,
    },
}

NOTES = (
    "Section 1 fixes Highly Connected Deletion and the strict condition that a "
    "component on r vertices has minimum degree greater than r/2.  Section 3.1 "
    "fixes Seeded Highly Connected Edge Deletion: after at most k edge deletions "
    "there must be only isolated vertices and one highly connected component C, "
    "with the supplied seed contained in C and |C|=|S|+a.  Theorem 4 gives a "
    "2^{O(sqrt(k) log k)} algorithm and Theorem 5 gives a polynomial kernel; more "
    "importantly at Step 0, this generated disjoint-clique subclass is solved by "
    "an ordinary component scan.  It is therefore Track B, never Track A.  The "
    "generator first samples a primitive field generator and the seed, then "
    "carries the complete power fibre through the root-of-unity identity.  Every "
    "vertex has the same degree, the affine shift hides small labels, and the "
    "attack panel checks degree tie-breaking, nearest-label greed, an additive "
    "misreading of the multiplicative orbit, a reflection-only by-hand ansatz, "
    "primitive-generator powers without order reduction, and random restarts."
)


# These are diagnostics, not local gates.  They are replaced after the three
# script-owned oracle runs; zero attempts means simply "not run yet".
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}


_ENUMERATION_CAP = 200_000
_G4_SAMPLES = 200_000
_ATTACK_SEEDS = 8
_SEED_SLOTS = 64


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_prime(value):
    """Deterministic Miller--Rabin in the unsigned 64-bit range."""
    if not _is_int(value) or value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small:
        if value % prime == 0:
            return value == prime
    d = value - 1
    power = 0
    while d % 2 == 0:
        power += 1
        d //= 2
    for base in (2, 325, 9_375, 28_178, 450_775, 9_780_504, 1_795_265_022):
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


def _next_prime_one_mod_s(start, s):
    candidate = max(start, 3 * s + 1)
    candidate += (1 - candidate) % s
    while not _is_prime(candidate):
        candidate += s
    return candidate


def _prime_factors(value):
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
    return factors


def _primitive_root(prime, rng):
    factors = _prime_factors(prime - 1)
    while True:
        candidate = rng.randrange(2, prime)
        if all(
            pow(candidate, (prime - 1) // factor, prime) != 1
            for factor in factors
        ):
            return candidate


def _validate_parameters(n, s, spread):
    if not _is_int(n) or n < 13:
        raise ValueError("n must be an integer at least 13")
    if not _is_int(s) or s not in (4, 8):
        raise ValueError("s must be 4 or 8")
    if not _is_int(spread) or spread < 0:
        raise ValueError("spread must be a non-negative integer")
    if spread and spread < s:
        raise ValueError("positive spread must be at least s")


def _power(inst, vertex):
    return pow((vertex - inst["shift"]) % inst["p"], inst["s"], inst["p"])


def _same_fibre(inst, left, right):
    return left != right and _power(inst, left) == _power(inst, right)


def _answer_by_composition(p, s, generator, shift, seed_vertex):
    """Carry the seed fibre through the cyclic group of s-th roots."""
    zeta = pow(generator, (p - 1) // s, p)
    delta = (seed_vertex - shift) % p
    roots = []
    multiplier = zeta
    for _ in range(1, s):
        roots.append((shift + delta * multiplier) % p)
        multiplier = multiplier * zeta % p
    if len(set(roots + [seed_vertex])) != s:
        raise AssertionError("root-of-unity fibre construction failed")
    return sorted(roots)


def make_instance(n, seed=0, **params):
    """Construct an instance and carry its witness without solving it.

    Nonzero displacements in F_p are partitioned into fibres of x -> x^s.
    Because s divides p-1, each fibre has exactly s elements.  The graph makes
    each fibre a clique and has no other edges.  The selected seed fibre is
    computed from the sampled primitive generator before the instance is posed.
    """
    s = params.pop("s", 8)
    spread = params.pop("spread", 0)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_parameters(n, s, spread)
    if not _is_int(seed):
        raise ValueError("seed must be an integer")

    start = n + (seed % _SEED_SLOTS) * spread
    p = _next_prime_one_mod_s(start, s)
    rng = random.Random(seed)
    generator = _primitive_root(p, rng)
    shift = rng.randrange(p)
    seed_vertex = (shift + rng.randrange(1, p)) % p
    answer = _answer_by_composition(
        p, s, generator, shift, seed_vertex
    )
    fibre_count = (p - 1) // s
    edges_per_fibre = s * (s - 1) // 2
    total_edges = fibre_count * edges_per_fibre
    budget = total_edges - edges_per_fibre
    return {
        "paper": "arXiv:1706.09487",
        "family": "seeded highly connected deletion in a power-fibre graph",
        "n": n,
        "p": p,
        "s": s,
        "spread": spread,
        "shift": shift,
        "primitive_generator": generator,
        "vertex_count": p - 1,
        "seed_set": [seed_vertex],
        "additional_vertices": s - 1,
        "edge_budget": budget,
        "total_edges": total_edges,
        "answer": answer,
    }


def _format_example(inst):
    target = _power(inst, inst["seed_set"][0])
    values = []
    for value in range(inst["p"]):
        if value in (inst["shift"], inst["seed_set"][0]):
            continue
        if _power(inst, value) == target:
            continue
        values.append(value)
        if len(values) == inst["s"] - 1:
            break
    return values


def render(inst):
    """Render the complete native graph problem and exact answer contract."""
    example = _format_example(inst)
    p = inst["p"]
    s = inst["s"]
    shift = inst["shift"]
    seed_vertex = inst["seed_set"][0]
    lines = [
        "Seeded Highly Connected Edge Deletion in a finite graph.",
        "",
        "Definitions.",
        "A finite undirected loopless graph on r vertices is highly connected when every vertex has degree strictly greater than r/2.",
        "For a chosen vertex set C, use the following compressed deletion set: delete every graph edge that is not wholly inside C.",
        "This leaves the induced graph on C and makes every vertex outside C isolated.",
        "",
        "The graph is specified exactly by the following rule; there is no unstated edge list.",
        f"All arithmetic is modulo the prime p = {p}.",
        f"The vertices are the residues 0,1,...,{p - 1}, except shift = {shift}, which is omitted.",
        f"Set s = {s} and phi(x) = (x-shift)^s modulo p.",
        "Two distinct vertices x and y are adjacent exactly when phi(x) = phi(y).",
        f"A primitive generator of the nonzero residues modulo p is g = {inst['primitive_generator']}.",
        f"The graph has exactly {inst['total_edges']} edges.",
        "",
        f"The supplied seed set is S = {{{seed_vertex}}}.",
        f"Choose exactly a = {inst['additional_vertices']} additional vertices X, and put C = S union X.",
        f"The compressed deletion set defined above may contain at most k = {inst['edge_budget']} edges.",
        "After those deletions, C must be the one highly connected component and every other vertex must be isolated.",
        "",
        f"Output X as an unordered JSON list of exactly {s - 1} distinct base-10 integers.",
        f"Every entry must lie in the inclusive range 0..{p - 1}; the omitted shift and the seed are forbidden.",
        "Order does not matter and repetitions are forbidden.",
        "",
        "Give your final answer inside <answer></answer> tags, as one JSON list of integers.",
        "Format-only example (not an answer to this instance): <answer>"
        + json.dumps(example, separators=(",", ":"))
        + "</answer>",
        "Output nothing else inside the tags.",
    ]
    statement = "\n".join(lines)
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Parse a tagged JSON list, tolerating prose, fences, and whitespace."""
    if not isinstance(text, str):
        return None
    matches = re.findall(
        r"<answer\b[^>]*>(.*?)</answer\s*>", text, flags=re.I | re.S
    )
    bodies = list(reversed(matches)) if matches else [text]
    decoder = json.JSONDecoder()
    for body in bodies:
        body = body.strip()
        if body.startswith("```"):
            body = re.sub(r"^```(?:json|text)?\s*", "", body, flags=re.I)
            body = re.sub(r"\s*```$", "", body).strip()
        try:
            value = json.loads(body)
            if isinstance(value, list):
                return value
        except (TypeError, ValueError):
            pass
        for start, character in enumerate(body):
            if character != "[":
                continue
            try:
                value, _end = decoder.raw_decode(body[start:])
            except (TypeError, ValueError):
                continue
            if isinstance(value, list):
                return value
    return None


def _decode_answer(inst, answer):
    if not isinstance(answer, list):
        return None, "answer must be one JSON list"
    if not answer:
        return None, "answer list is empty"
    expected = inst["additional_vertices"]
    if len(answer) != expected:
        return None, f"expected exactly {expected} additional vertices, got {len(answer)}"
    if any(not _is_int(value) for value in answer):
        return None, "every answer entry must be an integer"
    if len(set(answer)) != len(answer):
        return None, "repeated vertices are forbidden"
    p = inst["p"]
    if any(value < 0 or value >= p for value in answer):
        return None, f"a vertex is outside the inclusive residue range 0..{p - 1}"
    if inst["shift"] in answer:
        return None, "the omitted shift is not a graph vertex"
    if inst["seed_set"][0] in answer:
        return None, "the supplied seed cannot be repeated among the additions"
    return answer, "ok"


def verify(inst, answer):
    """Check any valid compressed deletion witness without reading the plant."""
    decoded, reason = _decode_answer(inst, answer)
    if decoded is None:
        return False, reason

    p = inst.get("p")
    s = inst.get("s")
    if not _is_prime(p) or not _is_int(s) or s < 3 or (p - 1) % s:
        return False, "instance field parameters do not define equal power fibres"
    seed_set = inst.get("seed_set")
    if (
        not isinstance(seed_set, list)
        or len(seed_set) != 1
        or not _is_int(seed_set[0])
    ):
        return False, "instance seed set is malformed"

    component = seed_set + decoded
    degrees = []
    internal_edges = 0
    for i, left in enumerate(component):
        degree = 0
        for right in component[i + 1 :]:
            if _same_fibre(inst, left, right):
                degree += 1
                internal_edges += 1
        for right in component[:i]:
            if _same_fibre(inst, left, right):
                degree += 1
        degrees.append(degree)
    if any(2 * degree <= len(component) for degree in degrees):
        return False, "the retained induced component is not highly connected"

    fibre_count = (p - 1) // s
    total_edges = fibre_count * s * (s - 1) // 2
    deleted_edges = total_edges - internal_edges
    if deleted_edges > inst["edge_budget"]:
        return False, f"compressed deletion set has {deleted_edges} edges, exceeding k"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly after shape, range, distinctness, and exclusions."""
    if not callable(getattr(rng, "sample", None)):
        raise TypeError("rng must supply sample()")
    excluded = sorted((inst["shift"], inst["seed_set"][0]))
    ranks = rng.sample(
        range(inst["p"] - 2), inst["additional_vertices"]
    )
    values = []
    for rank in ranks:
        value = rank
        for omitted in excluded:
            if value >= omitted:
                value += 1
        values.append(value)
    return sorted(values)


def search_space(inst):
    return math.comb(inst["p"] - 2, inst["additional_vertices"])


def enumerate_all(inst):
    total = search_space(inst)
    if total > _ENUMERATION_CAP:
        return None
    population = [
        value
        for value in range(inst["p"])
        if value not in (inst["shift"], inst["seed_set"][0])
    ]
    valid = 0
    for candidate in itertools.combinations(
        population, inst["additional_vertices"]
    ):
        valid += int(verify(inst, list(candidate))[0])
    return valid


def canonical_key(inst):
    """Key the marked graph up to every generated-family graph relabelling.

    For fixed p and s the graph is a disjoint union of (p-1)/s copies of K_s,
    and its one marked seed vertex lies in the unique vertex orbit.  Thus the
    affine shift, primitive generator, and seed label are all presentation data.
    """
    payload = {
        "vertices": inst["p"] - 1,
        "component_count": (inst["p"] - 1) // inst["s"],
        "component_type": ["complete", inst["s"]],
        "marked_seed_orbit": "unique",
        "addition_count": inst["additional_vertices"],
        "edge_budget": inst["edge_budget"],
    }
    data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest()


def escalate(params):
    """Grow the residue haystack while the seven-entry witness stays fixed."""
    n = params.get("n")
    s = params.get("s", 8)
    spread = params.get("spread", 0)
    if not _is_int(n) or not _is_int(spread):
        return None
    return {"n": n * 8, "s": s, "spread": spread * 8}


def _mod_power_counted(base, exponent, modulus):
    result = 1
    base %= modulus
    operations = 0
    while exponent:
        if exponent & 1:
            result = result * base % modulus
            operations += 1
        exponent >>= 1
        if exponent:
            base = base * base % modulus
            operations += 1
    return result, operations


def _small_power_counted(base, exponent, modulus):
    result = 1
    operations = 0
    for bit in range(exponent.bit_length() - 1, -1, -1):
        result = result * result % modulus
        operations += 1
        if (exponent >> bit) & 1:
            result = result * base % modulus
            operations += 1
    return result, operations


def _reference_residue_scan(inst):
    """Formula-aware mechanical component scan over every graph vertex."""
    p = inst["p"]
    s = inst["s"]
    shift = inst["shift"]
    seed_vertex = inst["seed_set"][0]
    seed_delta = (seed_vertex - shift) % p
    if s == 8:
        seed_square = seed_delta * seed_delta % p
        seed_fourth = seed_square * seed_square % p
        target = seed_fourth * seed_fourth % p
        operations = 3
    else:
        target, operations = _small_power_counted(seed_delta, s, p)
    found = []
    for vertex in range(p):
        if vertex in (shift, seed_vertex):
            continue
        delta = (vertex - shift) % p
        if s == 8:
            square = delta * delta % p
            fourth = square * square % p
            value = fourth * fourth % p
            used = 3
        else:
            value, used = _small_power_counted(delta, s, p)
        operations += used + 1
        if value == target:
            found.append(vertex)
    return found, operations


def _compact_fibre_recovery(inst):
    """Intended root-of-unity route, with exact operations counted."""
    p = inst["p"]
    s = inst["s"]
    zeta, operations = _mod_power_counted(
        inst["primitive_generator"], (p - 1) // s, p
    )
    delta = (inst["seed_set"][0] - inst["shift"]) % p
    operations += 1
    roots = []
    multiplier = zeta
    for _ in range(1, s):
        roots.append((inst["shift"] + delta * multiplier) % p)
        multiplier = multiplier * zeta % p
        operations += 3
    roots.sort()
    operations += math.ceil(s * math.log2(max(2, s)))
    return roots, operations


def _fill_candidate(inst, preferred):
    answer = []
    for value in preferred:
        value %= inst["p"]
        if value in (inst["shift"], inst["seed_set"][0]) or value in answer:
            continue
        answer.append(value)
        if len(answer) == inst["additional_vertices"]:
            return sorted(answer)
    for value in range(inst["p"]):
        if (
            value not in (inst["shift"], inst["seed_set"][0])
            and value not in answer
        ):
            answer.append(value)
        if len(answer) == inst["additional_vertices"]:
            break
    return sorted(answer)


def _attack_candidates(inst, seed):
    p = inst["p"]
    s = inst["s"]
    shift = inst["shift"]
    query = inst["seed_set"][0]
    needed = inst["additional_vertices"]

    # All vertices have degree s-1.  The only available outlier tie-break is label.
    smallest = [value for value in range(needed + 2)]
    nearest = []
    for distance in range(1, 3 * s + 2):
        nearest.extend(((query - distance) % p, (query + distance) % p))
    additive_step = (p - 1) // s
    additive = [query + index * additive_step for index in range(1, 3 * s)]
    delta = (query - shift) % p
    generator_powers = [
        shift + delta * pow(inst["primitive_generator"], index, p)
        for index in range(1, 3 * s)
    ]
    reflection = (2 * shift - query) % p
    reflection_completion = [reflection] + nearest

    candidates = {
        "outlier_equal_degree_small_label": [_fill_candidate(inst, smallest)],
        "greedy_nearest_seed_labels": [_fill_candidate(inst, nearest)],
        "by_hand_additive_quotient_step": [_fill_candidate(inst, additive)],
        "obvious_reflection_then_nearest": [
            _fill_candidate(inst, reflection_completion)
        ],
        "primitive_generator_powers_without_order_reduction": [
            _fill_candidate(inst, generator_powers)
        ],
    }
    rrng = random.Random(seed ^ 0x170609487)
    candidates["random_restart_256"] = [
        random_candidate(inst, rrng) for _ in range(256)
    ]
    return candidates


def _affine_variant(inst, rng):
    p = inst["p"]
    multiplier = rng.randrange(1, p)
    new_shift = rng.randrange(p)

    def carry(value):
        return (
            new_shift + multiplier * (value - inst["shift"])
        ) % p

    out = dict(inst)
    out["shift"] = new_shift
    out["seed_set"] = [carry(inst["seed_set"][0])]
    carried = sorted(carry(value) for value in inst["answer"])
    out["answer"] = carried
    return out, carried


def _generator_variant(inst):
    out = dict(inst)
    out["primitive_generator"] = pow(
        inst["primitive_generator"], -1, inst["p"]
    )
    carried = list(reversed(inst["answer"]))
    out["answer"] = carried
    return out, carried


def _seed_twin_swap_variant(inst):
    """Apply a non-affine graph automorphism swapping two clique twins."""
    old_seed = inst["seed_set"][0]
    new_seed = inst["answer"][0]
    out = dict(inst)
    out["seed_set"] = [new_seed]
    carried = sorted([old_seed] + list(inst["answer"][1:]))
    out["answer"] = carried
    return out, carried


def _replacement_vertex(inst):
    target = _power(inst, inst["seed_set"][0])
    excluded = set(inst["answer"]) | {
        inst["shift"], inst["seed_set"][0]
    }
    for value in range(inst["p"]):
        if value not in excluded and _power(inst, value) != target:
            return value
    raise AssertionError("no legal corruption vertex exists")


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest():
    report = {}
    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]

    g1_failures = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append([preset, seed, why])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    inst = make_instance(seed=19, **shipping)
    answer = inst["answer"]
    dropped = answer[:-1]
    swapped = list(answer)
    swapped[0] = _replacement_vertex(inst)
    duplicated = list(answer)
    duplicated[-1] = duplicated[0]
    corruptions = {
        "drop": dropped,
        "swap_one": swapped,
        "duplicate": duplicated,
        "empty": [],
        "out_of_range": list(answer[:-1]) + [inst["p"]],
    }
    corruption_results = {
        name: verify(inst, value) for name, value in corruptions.items()
    }
    reasons = [why for ok, why in corruption_results.values() if not ok]
    report["G2_rejects_corruption"] = {
        "pass": (
            all(not ok for ok, _why in corruption_results.values())
            and len(set(reasons)) == len(reasons)
        ),
        "cases": {
            name: {"accepted": ok, "reason": why}
            for name, (ok, why) in corruption_results.items()
        },
    }

    wire = json.dumps(answer, separators=(",", ":"))
    parsed = parse_answer(
        "The retained component meets the strict degree bound.\n```json\n"
        + "<answer>\n"
        + wire
        + "\n</answer>\n```\n"
    )
    garbage = parse_answer("I could not determine the component.")
    report["G3_round_trip"] = {
        "pass": parsed == answer and garbage is None,
        "model_style_round_trip": parsed == answer,
        "garbage_returns_none": garbage is None,
    }

    guess_total = _G4_SAMPLES
    guess_hits = 0
    guess_rng = random.Random(0x170609487)
    guess_inst = make_instance(seed=314_159, **shipping)
    guess_started = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(
            verify(guess_inst, random_candidate(guess_inst, guess_rng))[0]
        )
    guess_elapsed = time.perf_counter() - guess_started
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_total >= 200_000 and guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_fraction,
        "structure_aware_space": search_space(guess_inst),
        "elapsed_sec": guess_elapsed,
    }

    demo_inst = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)

    attack_names = None
    attack_successes = {}
    attack_attempts = {}
    attack_candidate_count = 0
    attack_started = time.perf_counter()
    for seed in range(_ATTACK_SEEDS):
        attack_inst = make_instance(seed=seed, **shipping)
        attacks = _attack_candidates(attack_inst, seed)
        if attack_names is None:
            attack_names = list(attacks)
            attack_successes = {name: 0 for name in attack_names}
            attack_attempts = {name: 0 for name in attack_names}
        for name, candidates in attacks.items():
            solved = any(
                verify(attack_inst, candidate)[0] for candidate in candidates
            )
            attack_successes[name] += int(solved)
            attack_attempts[name] += 1
            attack_candidate_count += len(candidates)
    attack_elapsed = time.perf_counter() - attack_started

    reference_successes = 0
    reference_times = []
    reference_operations = []
    reference_vertices = []
    compact_operations = []
    for seed in range(_ATTACK_SEEDS):
        reference_inst = make_instance(seed=seed, **shipping)
        started = time.perf_counter()
        recovered, operations = _reference_residue_scan(reference_inst)
        reference_times.append(time.perf_counter() - started)
        reference_operations.append(operations)
        reference_vertices.append(reference_inst["vertex_count"])
        reference_successes += int(verify(reference_inst, recovered)[0])

        compact, operations = _compact_fibre_recovery(reference_inst)
        compact_operations.append(operations)
        if not verify(reference_inst, compact)[0]:
            compact_operations[-1] = 10**9

    attacks_report = {
        name: {
            "successes": attack_successes[name],
            "attempts": attack_attempts[name],
        }
        for name in attack_names
    }
    all_failed = all(
        result["successes"] == 0 and result["attempts"] >= 8
        for result in attacks_report.values()
    )
    reference_mean_time = sum(reference_times) / len(reference_times)
    reference_mean_ops = sum(reference_operations) / len(reference_operations)
    report["G5_density_and_baseline_cost"] = {
        "pass": (
            demo_count == 1
            and guess_total >= 200_000
            and all_failed
            and reference_successes == 8
        ),
        "shipping_density_hits": guess_hits,
        "shipping_density_total": guess_total,
        "shipping_density_fraction": guess_fraction,
        "known_shipping_valid_answers": 1,
        "known_count_basis": "degree-s power fibre containing the seed",
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo_inst),
        "strongest_failing_attack_wall_clock_sec": attack_elapsed,
        "strongest_failing_attack_iterations": attack_candidate_count,
        "reference_wall_clock_sec_mean": reference_mean_time,
        "reference_operations_mean": reference_mean_ops,
        "reference_vertex_count_mean": (
            sum(reference_vertices) / len(reference_vertices)
        ),
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attacks_report,
        "reference_algorithm": {
            "name": "exhaustive exact power-residue component scan",
            "complexity": "O(p log s) exact modular operations",
            "wall_clock_sec_mean": reference_mean_time,
            "operations_mean": reference_mean_ops,
            "vertices_mean": sum(reference_vertices) / len(reference_vertices),
            "solves": f"{reference_successes}/8, as expected on Track B",
            "paper_generic_bound": (
                "Theorem 4: 2^{O(sqrt(k) log k)} for Seeded Highly "
                "Connected Edge Deletion after Theorem 5's kernel"
            ),
        },
    }

    scale_inst = make_instance(seed=23, **shipping)
    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    doubled_params["spread"] *= 2
    doubled = make_instance(seed=23, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (
            doubled_ok
            and doubled["vertex_count"] > scale_inst["vertex_count"]
            and len(doubled["answer"]) == len(scale_inst["answer"])
        ),
        "shipping_n": shipping["n"],
        "shipping_vertices": scale_inst["vertex_count"],
        "doubled_n": doubled_params["n"],
        "doubled_vertices": doubled["vertex_count"],
        "answer_elements_both": len(doubled["answer"]),
        "doubled_verification": doubled_why,
    }

    g8_failures = []
    invariance_checks = 0
    carried_checks = 0
    unrelated_keys = []
    distinct_primes = []
    for seed in range(20):
        base = make_instance(seed=seed, **shipping)
        base_key = canonical_key(base)
        unrelated_keys.append(base_key)
        distinct_primes.append(base["p"])
        rrng = random.Random(seed ^ 0xC4A0C1CA1)
        variants = []
        first, first_answer = _affine_variant(base, rrng)
        variants.append((first, first_answer))
        second, second_answer = _generator_variant(base)
        variants.append((second, second_answer))
        third, third_answer = _affine_variant(second, rrng)
        variants.append((third, third_answer))
        twin_swapped, twin_swapped_answer = _seed_twin_swap_variant(base)
        variants.append((twin_swapped, twin_swapped_answer))
        for variant, carried in variants:
            invariance_checks += 1
            if canonical_key(variant) != base_key:
                g8_failures.append([seed, "canonical key changed"])
            carried_checks += 1
            if not verify(variant, carried)[0]:
                g8_failures.append([seed, "carried witness failed"])
    unrelated_distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": (
            not g8_failures
            and invariance_checks >= 80
            and carried_checks >= 80
            and unrelated_distinct == 20
        ),
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_distinct": unrelated_distinct,
        "unrelated_attempts": 20,
        "distinct_prime_parameters": len(set(distinct_primes)),
        "failures": g8_failures,
    }

    size_inst = make_instance(seed=98765, **shipping)
    answer_blob = json.dumps(size_inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(size_inst["answer"])
    intended_ops = max(compact_operations)
    arms = {
        key: dict(G9_ORACLE_RESULTS[key])
        for key in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"]
        else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"]
        else 0.0
    )
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_ops <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=False))
