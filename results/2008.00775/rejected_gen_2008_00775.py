"""Succinct vertical-transversal certificates for structured list colourings.

This is a self-contained generator derived from Sections 1, 2, 3.1, and 4 of
Wanless--Wood, *A general framework for hypergraph colouring* (arXiv:2008.00775).
The underlying objects are complete graphs, finite lists of colours, and proper
list colourings.  Lists are represented by exact formulae rather than expanded
to millions of colour triples.
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
    from gvlib import exact_matrices, rationals
except ImportError:  # pragma: no cover - the implementation is stdlib-only
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "other",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "complete graphs",
        "compact list assignments over GF(p)",
        "proper list-colouring functions",
    ],
    "verification_operations": [
        "finite-field circuit evaluation",
        "exact modular equality",
        "permutation check by collision scan",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Each intercept table is a planted permutation circuit viewed through "
        "an unknown linear shear, while a solver missing that shear must test "
        "vertical transversals by collision scans."
    ),
    "hardness_basis": (
        "Track B: exhaustive vertical-transversal scanning is an exact "
        "O(blocks*p^2) algorithm (and ordinary greedy list colouring is also "
        "polynomial); at shipping seed 314159 it used 208,243 collision checks "
        "and 0.024 seconds in the final selftest, whereas recognizing the planted "
        "linear shear used 232 modular operations."
    ),
    "max_answer_tokens": 32,
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
    "demo": {"n": 11, "blocks": 1, "layers": 2},
    "easy": {"n": 521, "blocks": 4, "layers": 7},
    "medium": {"n": 1009, "blocks": 5, "layers": 7},
    "hard": {"n": 2018, "blocks": 5, "layers": 7},
}
SHIPPING_DIFFICULTY = "medium"

STRUCTURAL_HINT = (
    "Across each component, the displayed intercept table differs from its "
    "permutation circuit by one linear function of the slope."
)
PLACEBO_HINT = (
    "Across each component, careful modular bookkeeping prevents accidental "
    "collisions among the displayed slopes and ordinates."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object with exactly one field, vertical_parameters, containing "
        "one integer in [0,p-1] per component; each integer "
        "specifies a common vertical coordinate for that component's colouring."
    ),
    "bounds": {
        "max_components": 5,
        "max_field_order_shipping": 1009,
        "parameter_min": 0,
        "components_are_independent": True,
    },
}

NOTES = r"""
Paper boundary and exact definition. Section 1 defines a proper hypergraph
colouring and a c-list assignment. Section 2 defines good colourings by local
bad patterns. Section 3.1 specializes the framework to proper graph/list
colouring and explicitly notes that the Delta+1 result is proved by the greedy
algorithm. This module uses exactly that native object: each component is
K_p, has maximum degree p-1, and every vertex receives a list of p colours.

Step-0 algorithmic triage. The paper is an existence-and-counting framework,
not an average-case hardness result. Section 4 says entropy compression often
provides an explicit polynomial-expected-time colouring algorithm, and Section
3.1 calls the graph case greedy. A Track A claim would therefore be false. On
Track B, the domain-standard mechanical route is disclosed: test p possible
vertical parameters per component, scanning p slopes for collisions, in
O(blocks*p^2), or expand the lists and greedily find an unrestricted colouring.

Construction and certificate. A parameter t_j is sampled uniformly first. A
composition Q_j of affine maps and coprime power maps over GF(p) is sampled
next; every layer is bijective because its scale is nonzero and its exponent
is coprime to p-1. The public intercepts are b_j(m)=Q_j(m)-t_j*m. Therefore the
symbolic choice (j,t_j,t_j*m+b_j(m))=(j,t_j,Q_j(m)) uses a distinct colour at
every vertex of K_p. No search is used during generation.

Compact route and attacks. Evaluating Q_j(1)-b_j(1) recovers t_j. Repeated
squaring plus the two affine operations per circuit layer costs at most 250
modular operations at the shipping preset. The outlier attack sees only a
small slope sample; the greedy-prefix attack commits to the first locally
collision-free parameter; the random-restart attack gets 256 uniform vectors;
and the one-layer ansatz mistakes the first circuit layer for the composition.
All are checked on eight seeds. Plants and random candidates are uniform in
exactly the same bounded parameter language.

Canonicalization. Vertex records and components are unordered. Independent
affine relabellings (x,y)->(u*x,u*y+c) of each component carry t to u*t and
preserve the list-colouring problem. canonical_key sorts components and
normalizes translations and nonzero scales before hashing; it never uses the
seed or the stored answer.

Final disposition. The bare four-vendor harness held at p=1009 (0/3 solved),
but the admissible one-sentence structural hint produced verified solutions
from 2/3 vendors; the same-register placebo remained 0/3. Thus the family
fails mandatory G9(b) after the single allowed ladder move and is retained as
a rejected generator rather than shipped.
""".strip()


# Filled from the three script-owned hardening runs after the module is stable.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 2, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "too_easy",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_prime(value):
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _next_prime(value):
    candidate = max(3, value)
    if candidate % 2 == 0:
        candidate += 1
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _eval_circuit(layers, value, p):
    z = value % p
    for scale, exponent, shift in layers:
        z = (scale * pow(z, exponent, p) + shift) % p
    return z


def _pow_multiplications(exponent):
    """Multiplications in left-to-right binary powering, excluding mod ops."""
    return exponent.bit_length() - 1 + exponent.bit_count() - 1


def _compact_route_operations(inst):
    total = 0
    for component in inst["components"]:
        for _scale, exponent, _shift in component["circuit"]:
            total += _pow_multiplications(exponent) + 2  # scale and addition
        total += 1  # Q(1)-b(1)
    return total


def _ordered_intercepts(component, p):
    records = component.get("intercepts")
    if not isinstance(records, list) or len(records) != p:
        raise ValueError("component has the wrong number of intercept records")
    values = [None] * p
    for record in records:
        if (not isinstance(record, (list, tuple)) or len(record) != 2
                or not all(_is_int(x) for x in record)):
            raise ValueError("malformed intercept record")
        slope, intercept = record
        if not (0 <= slope < p and 0 <= intercept < p):
            raise ValueError("intercept record outside GF(p)")
        if values[slope] is not None:
            raise ValueError("duplicate slope record")
        values[slope] = intercept
    if any(value is None for value in values):
        raise ValueError("missing slope record")
    return values


def make_instance(n, seed=0, **params):
    """Inverse-generate a compact proper list-colouring certificate."""
    blocks = params.pop("blocks", None)
    layers_count = params.pop("layers", None)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if not _is_int(n) or n < 7:
        raise ValueError("n must be an integer at least 7")
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    if not _is_int(blocks) or blocks < 1 or blocks > 8:
        raise ValueError("blocks must be an integer from 1 through 8")
    if not _is_int(layers_count) or layers_count < 1 or layers_count > 20:
        raise ValueError("layers must be an integer from 1 through 20")

    p = _next_prime(n)
    if blocks > p:
        raise ValueError("blocks cannot exceed the field order")
    exponents = [
        exponent for exponent in (3, 5, 7, 11, 13, 17)
        if exponent < p and math.gcd(exponent, p - 1) == 1
    ]
    if not exponents:
        raise ValueError("no supported coprime power exponent for this field")

    rng = random.Random(seed)
    # The answer is sampled before any public constraint data is assembled.
    planted = [rng.randrange(p) for _ in range(blocks)]
    components = []
    for block in range(blocks):
        circuit = []
        for _ in range(layers_count):
            circuit.append([
                rng.randrange(1, p),
                rng.choice(exponents),
                rng.randrange(p),
            ])
        t = planted[block]
        records = []
        for slope in range(p):
            q_value = _eval_circuit(circuit, slope, p)
            records.append([slope, (q_value - t * slope) % p])
        # Input order is semantically irrelevant.  Keep slope 1 first so that
        # the intended route is arithmetic, not a thousand-entry lookup chore.
        pivot = records[1]
        rest = records[:1] + records[2:]
        rng.shuffle(rest)
        records = [pivot] + rest
        components.append({
            "name": f"C{block}",
            "circuit": circuit,
            "intercepts": records,
        })

    return {
        "family": "compact_complete_graph_list_colouring",
        "p": p,
        "requested_n": n,
        "blocks": blocks,
        "layers": layers_count,
        "components": components,
        "answer": {"vertical_parameters": planted},
    }


def render(inst):
    p = inst["p"]
    blocks = inst["blocks"]
    example = json.dumps(
        {"vertical_parameters": list(range(blocks))}, separators=(",", ":")
    )
    lines = [
        "PROBLEM: succinct proper list colouring by vertical transversals",
        "",
        f"All arithmetic below is in the finite field GF({p}), represented by",
        f"the integers 0,...,{p - 1} with reduction modulo {p}.",
        f"There are {blocks} independent components.  Component j is a complete",
        f"graph K_{p} whose vertices are the slopes m in GF({p}).",
        "",
        "At slope m in component j, the allowed colours are all triples",
        "    (j, x, x*m + b_j(m) mod p),   x in GF(p).",
        "Thus every vertex has exactly p allowed colours.  A proper list",
        "colouring chooses an allowed colour at every vertex and gives adjacent",
        "vertices different colour triples.  Since each component is complete,",
        "all chosen triples inside it must be distinct; different components",
        "have different first coordinates and never conflict.",
        "",
        "Your certificate is one shared vertical parameter t_j for each component.",
        "It induces at every slope m the allowed colour",
        "    (j, t_j, t_j*m + b_j(m) mod p).",
        "Components are independent, so their parameters may repeat.  A parameter",
        "is valid exactly when its p induced third coordinates are pairwise distinct.",
        "",
        "Each component also displays an auxiliary circuit Q_j.  Starting at z=m,",
        "a layer [a,e,c] replaces z by a*z^e+c modulo p.  Layers are applied in",
        "the displayed order.  Every a is nonzero and every gcd(e,p-1)=1, so each",
        "circuit is a permutation of GF(p).  Intercept records are written m:b",
        "and may appear in any order.",
        "",
        "INSTANCE DATA",
    ]
    for index, component in enumerate(inst["components"]):
        circuit = " ".join(
            f"[{a},{e},{c}]" for a, e, c in component["circuit"]
        )
        records = " ".join(f"{m}:{b}" for m, b in component["intercepts"])
        lines.extend([
            f"component {index}",
            f"circuit: {circuit}",
            f"intercepts: {records}",
        ])
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags as one JSON object",
        f"with exactly the key vertical_parameters and a list of {blocks}",
        f"integers from 0 through {p - 1}, in component order.",
        f"Example: <answer>{example}</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def _answer_object(value):
    if not isinstance(value, dict) or set(value) != {"vertical_parameters"}:
        return None
    params = value["vertical_parameters"]
    if not isinstance(params, list) or not all(_is_int(x) for x in params):
        return None
    return {"vertical_parameters": list(params)}


def parse_answer(text):
    """Parse the tagged JSON object, tolerating prose and Markdown fences."""
    if not isinstance(text, str):
        return None
    match = re.search(r"<answer\b[^>]*>(.*?)</answer\s*>", text,
                      flags=re.IGNORECASE | re.DOTALL)
    candidates = [match.group(1)] if match else []
    # A forgiving fallback handles a model that gives valid JSON in a code fence
    # while accidentally omitting the requested tags.
    candidates.extend(re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text,
                                 flags=re.IGNORECASE | re.DOTALL))
    decoder = json.JSONDecoder()
    for raw in candidates:
        cleaned = raw.strip()
        if cleaned.startswith("```="):
            cleaned = cleaned[4:].strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            value = json.loads(cleaned)
        except (TypeError, ValueError):
            value = None
        parsed = _answer_object(value)
        if parsed is not None:
            return parsed
    # Last resort: scan prose for the first decodable JSON object.
    for pos, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _end = decoder.raw_decode(text[pos:])
        except ValueError:
            continue
        parsed = _answer_object(value)
        if parsed is not None:
            return parsed
    return None


def verify(inst, answer):
    """Check any valid vertical-transversal witness; never inspect inst['answer']."""
    if not isinstance(answer, dict) or set(answer) != {"vertical_parameters"}:
        return False, "answer must be an object with exactly vertical_parameters"
    params = answer["vertical_parameters"]
    if not isinstance(params, list) or not all(_is_int(x) for x in params):
        return False, "vertical_parameters must be a list of integers"
    blocks = inst["blocks"]
    if len(params) != blocks:
        return False, f"expected exactly {blocks} vertical parameters"
    p = inst["p"]
    for index, value in enumerate(params):
        if not 0 <= value < p:
            return False, f"parameter {index} is outside 0..{p - 1}"
    for index, (component, parameter) in enumerate(
            zip(inst["components"], params)):
        records = component.get("intercepts")
        if not isinstance(records, list) or len(records) != p:
            return False, f"malformed instance component {index}: wrong record count"
        previous = [-1] * p
        for record in records:
            if (not isinstance(record, (list, tuple)) or len(record) != 2
                    or not all(_is_int(x) for x in record)):
                return False, f"malformed instance component {index}: bad record"
            slope, intercept = record
            if not (0 <= slope < p and 0 <= intercept < p):
                return False, f"malformed instance component {index}: field range"
            ordinate = (parameter * slope + intercept) % p
            if previous[ordinate] >= 0:
                return False, (
                    f"component {index} has an ordinate collision at slopes "
                    f"{previous[ordinate]} and {slope}"
                )
            previous[ordinate] = slope
    return True, "ok"


def random_candidate(inst, rng):
    if not hasattr(rng, "randrange"):
        raise TypeError("rng must provide randrange()")
    return {"vertical_parameters": [rng.randrange(inst["p"])
                                    for _ in range(inst["blocks"])]}


def search_space(inst):
    return inst["p"] ** inst["blocks"]


def _valid_parameters(component, p, operation_box=None):
    records = component["intercepts"]
    valid = []
    operations = 0
    for parameter in range(p):
        seen = bytearray(p)
        good = True
        for slope, intercept in records:
            ordinate = (parameter * slope + intercept) % p
            operations += 1
            if seen[ordinate]:
                good = False
                break
            seen[ordinate] = 1
        if good:
            valid.append(parameter)
    if operation_box is not None:
        operation_box[0] += operations
    return valid


def enumerate_all(inst):
    # This is exact at all supported presets: scan the p vertical parameters in
    # each independent component, then multiply their independent counts.
    valid_sets = [_valid_parameters(component, inst["p"])
                  for component in inst["components"]]
    product_bound = math.prod(max(1, len(values)) for values in valid_sets)
    if product_bound > 2_000_000:
        return None
    return math.prod(len(values) for values in valid_sets)


def _component_signature(component, p):
    b_values = _ordered_intercepts(component, p)
    q_values = [_eval_circuit(component["circuit"], slope, p)
                for slope in range(p)]
    b0, q0 = b_values[0], q_values[0]
    normalized = ([(value - b0) % p for value in b_values]
                  + [(value - q0) % p for value in q_values])
    pivot = next((value for value in normalized if value), 1)
    inv = pow(pivot, p - 2, p)
    normalized = [(value * inv) % p for value in normalized]
    payload = json.dumps([p, normalized], separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def canonical_key(inst):
    signatures = sorted(_component_signature(component, inst["p"])
                        for component in inst["components"])
    payload = json.dumps([inst["p"], signatures], separators=(",", ":")).encode()
    return "list-colouring:" + hashlib.sha256(payload).hexdigest()


def escalate(params):
    current = params.get("n")
    blocks = params.get("blocks")
    layers = params.get("layers")
    if not all(_is_int(x) for x in (current, blocks, layers)):
        return None
    # Grow the conceptual graph/list haystack and field entropy while leaving
    # the five-number certificate fixed.
    return {"n": 2 * current, "blocks": blocks, "layers": layers}


def _first_prefix_candidate(inst, prefix, limited_range=None):
    p = inst["p"]
    output = []
    for component in inst["components"]:
        records = component["intercepts"][:min(prefix, p)]
        choices = range(p if limited_range is None else min(p, limited_range))
        selected = 0
        best_score = -1
        for parameter in choices:
            score = len({(parameter * slope + intercept) % p
                         for slope, intercept in records})
            if score > best_score:
                selected, best_score = parameter, score
            if score == len(records):
                selected = parameter
                break
        output.append(selected)
    return {"vertical_parameters": output}


def _one_layer_candidate(inst):
    p = inst["p"]
    output = []
    for component in inst["components"]:
        a, exponent, shift = component["circuit"][0]
        first_layer_at_one = (a * pow(1, exponent, p) + shift) % p
        intercepts = _ordered_intercepts(component, p)
        output.append((first_layer_at_one - intercepts[1]) % p)
    return {"vertical_parameters": output}


def _reference_scan(inst):
    operation_box = [0]
    valid_sets = [_valid_parameters(component, inst["p"], operation_box)
                  for component in inst["components"]]
    if any(not values for values in valid_sets):
        return None, operation_box[0], valid_sets
    answer = [values[0] for values in valid_sets]
    return {"vertical_parameters": answer}, operation_box[0], valid_sets


def _transformed_instance(inst, rng):
    """Compose all declared relabellings and carry the certificate through."""
    p = inst["p"]
    transformed_components = []
    carried = []
    for component, parameter in zip(
            inst["components"], inst["answer"]["vertical_parameters"]):
        scale = rng.randrange(1, p)
        translation = rng.randrange(p)
        records = [[slope, (scale * intercept + translation) % p]
                   for slope, intercept in component["intercepts"]]
        rng.shuffle(records)
        circuit = [list(layer) for layer in component["circuit"]]
        circuit[-1][0] = (scale * circuit[-1][0]) % p
        circuit[-1][2] = (scale * circuit[-1][2] + translation) % p
        transformed_components.append({
            "name": component["name"] + "'",
            "circuit": circuit,
            "intercepts": records,
        })
        carried.append((scale * parameter) % p)
    order = list(range(inst["blocks"]))
    rng.shuffle(order)
    out = dict(inst)
    out["components"] = [transformed_components[index] for index in order]
    out["answer"] = {"vertical_parameters": [carried[index] for index in order]}
    return out


def _answer_atoms(answer):
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, list):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def selftest():
    report = {
        "paper": "arXiv:2008.00775",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: every named rung, several independent seeds.
    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            instance = make_instance(seed=seed, **params)
            ok, reason = verify(instance, instance["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append([preset, seed, reason])
            if json.loads(json.dumps(instance["answer"])) != instance["answer"]:
                g1_failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    instance = make_instance(seed=314159, **shipping)

    # G2: five qualitatively different corruptions and five different reasons.
    original = instance["answer"]["vertical_parameters"]
    corruptions = {
        "drop": {"vertical_parameters": original[:-1]},
        "duplicate": {"vertical_parameters": [original[0]] * len(original)},
        "empty": [],
        "out_of_range": {
            "vertical_parameters": [instance["p"]] + original[1:]
        },
    }
    swapped = None
    for left in range(len(original)):
        for right in range(left + 1, len(original)):
            trial = list(original)
            trial[left], trial[right] = trial[right], trial[left]
            if not verify(instance, {"vertical_parameters": trial})[0]:
                swapped = {"vertical_parameters": trial}
                break
        if swapped is not None:
            break
    corruptions["swap"] = swapped if swapped is not None else {
        "vertical_parameters": list(reversed(original))
    }
    g2_results = {}
    reasons = []
    for name, bad in corruptions.items():
        ok, reason = verify(instance, bad)
        g2_results[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": (all(item["rejected"] for item in g2_results.values())
                 and len(set(reasons)) == len(reasons)),
        "cases": g2_results,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: prose, a Markdown fence, and the required tags all survive parsing.
    answer_json = json.dumps(instance["answer"], separators=(",", ":"))
    response = (
        "I used the collision condition component by component.\n\n"
        "```text\nThe requested object follows.\n```\n"
        f"<answer>\n{answer_json}\n</answer>\n"
        "This is my final certificate."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == instance["answer"] and verify(instance, parsed)[0],
        "parsed": parsed,
    }

    # G4: sample the stated independent parameter language.
    guess_rng = random.Random(8675309)
    guess_total = 200_000
    guess_hits = 0
    start = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(instance, guess_rng)
        guess_hits += int(verify(instance, candidate)[0])
    guess_seconds = time.perf_counter() - start
    guess_probability = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_probability,
        "candidate_space": search_space(instance),
        "sampling_wall_clock_sec": round(guess_seconds, 6),
    }

    # G5: exact shipping density and a measured full reference scan.
    start = time.perf_counter()
    reference_answer, reference_ops, valid_sets = _reference_scan(instance)
    reference_seconds = time.perf_counter() - start
    exact_count = math.prod(len(values) for values in valid_sets)
    exact_density = exact_count / search_space(instance)
    reference_ok = (reference_answer is not None
                    and verify(instance, reference_answer)[0])
    report["G5_density_and_baseline"] = {
        "pass": exact_density < 1e-6 and reference_ok,
        "exact_solution_count": exact_count,
        "candidate_space": search_space(instance),
        "exact_solution_density": exact_density,
        "baseline_wall_clock_sec": round(reference_seconds, 6),
        "baseline_collision_checks": reference_ops,
        "valid_parameters_per_component": [len(x) for x in valid_sets],
    }

    # G6: attacks available in context fail; the polynomial reference succeeds.
    attack_names = (
        "outlier_small_sample",
        "greedy_first_collision_free_prefix",
        "random_restart_256",
        "one_layer_linear_ansatz",
    )
    attack_counts = {name: {"successes": 0, "attempts": 8}
                     for name in attack_names}
    reference_successes = 0
    reference_total_ops = 0
    reference_total_seconds = 0.0
    for seed in range(8):
        trial_inst = make_instance(seed=seed + 9000, **shipping)
        candidates = {
            "outlier_small_sample": _first_prefix_candidate(
                trial_inst, prefix=9, limited_range=64),
            "greedy_first_collision_free_prefix": _first_prefix_candidate(
                trial_inst, prefix=24),
            "one_layer_linear_ansatz": _one_layer_candidate(trial_inst),
        }
        restart_rng = random.Random(seed + 700_001)
        restart_won = False
        for _ in range(256):
            if verify(trial_inst, random_candidate(trial_inst, restart_rng))[0]:
                restart_won = True
                break
        candidates["random_restart_256"] = None
        for name, candidate in candidates.items():
            success = restart_won if name == "random_restart_256" else (
                verify(trial_inst, candidate)[0]
            )
            attack_counts[name]["successes"] += int(success)

        start = time.perf_counter()
        found, operations, _sets = _reference_scan(trial_inst)
        reference_total_seconds += time.perf_counter() - start
        reference_total_ops += operations
        reference_successes += int(found is not None and verify(trial_inst, found)[0])

    all_attacks_failed = all(item["successes"] == 0
                             for item in attack_counts.values())
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == 8,
        "attacks": attack_counts,
        "reference_algorithm": {
            "name": "exhaustive vertical-parameter scan with collision marking",
            "complexity": "O(blocks*p^2) exact modular checks",
            "wall_clock_sec": round(reference_total_seconds, 6),
            "operations": reference_total_ops,
            "attempts": 8,
            "successes": reference_successes,
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    # G7: double the size axis without lengthening the answer.
    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    start = time.perf_counter()
    doubled = make_instance(seed=271828, **doubled_params)
    doubled_seconds = time.perf_counter() - start
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["p"] > instance["p"],
        "shipping_field_order": instance["p"],
        "doubled_field_order": doubled["p"],
        "answer_atoms_before": _answer_atoms(instance["answer"]),
        "answer_atoms_after": _answer_atoms(doubled["answer"]),
        "build_wall_clock_sec": round(doubled_seconds, 6),
        "verify_reason": doubled_reason,
    }

    # G8: permutations, affine colour relabellings, their composition, and
    # unrelated-seed distinctness.
    invariance_checks = 0
    carried_witness_checks = 0
    original_keys = []
    invariant_failures = []
    for seed in range(20):
        base = make_instance(seed=seed + 120_000, **shipping)
        key = canonical_key(base)
        original_keys.append(key)
        transformed = _transformed_instance(base, random.Random(seed + 44_000))
        transformed_key = canonical_key(transformed)
        invariance_checks += 1
        if key != transformed_key:
            invariant_failures.append([seed, "composed relabelling changed key"])
        ok, reason = verify(transformed, transformed["answer"])
        carried_witness_checks += 1
        if not ok:
            invariant_failures.append([seed, "carried witness failed: " + reason])
        # A second independent record permutation checks input-order invariance.
        reordered = dict(base)
        reordered_components = []
        reorder_rng = random.Random(seed + 55_000)
        for component in base["components"]:
            clone = dict(component)
            clone["intercepts"] = [list(record) for record in component["intercepts"]]
            reorder_rng.shuffle(clone["intercepts"])
            reordered_components.append(clone)
        reorder_rng.shuffle(reordered_components)
        reordered["components"] = reordered_components
        if canonical_key(reordered) != key:
            invariant_failures.append([seed, "input reordering changed key"])
        invariance_checks += 1
    distinct_keys = len(set(original_keys))
    report["G8_canonical_key"] = {
        "pass": (not invariant_failures and distinct_keys == 20
                 and carried_witness_checks == 20),
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_witness_checks,
        "distinct_unrelated_keys": distinct_keys,
        "unrelated_instances": 20,
        "failures": invariant_failures,
    }

    # G9(a) evidence is script-owned; only the hinted verdict and caps gate pass.
    answer_blob = json.dumps(instance["answer"], separators=(",", ":"))
    token_measure = len(re.findall(r"[A-Za-z_]+|\d+|[^\w\s]", answer_blob))
    answer_elements = _answer_atoms(instance["answer"])
    route_operations = _compact_route_operations(instance)
    arms = {
        name: dict(G9_EVIDENCE[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    within_caps = (len(answer_blob) <= 2000 and answer_elements <= 256
                   and route_operations <= 300)
    hinted_hardened = (G9_EVIDENCE["hinted_verdict"] == "hardened"
                       and arms["hinted"]["attempts"] >= 3
                       and arms["hinted"]["solved"] == 0)
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": len(answer_blob),
        "answer_tokens": token_measure,
        "answer_elements": answer_elements,
        "intended_route_operations": route_operations,
    }

    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
