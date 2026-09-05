"""Verified generator for maximal standard monomials of monomial ideals.

The source is arXiv:0806.3680, especially Section 2.2 (maximal standard
monomials and irreducible components), Section 3 (the Slice Algorithm), and
Section 4.7 (order-preserving remapping of exponents).

Generation is inverse.  We first choose an antichain of maximal standard
monomials, then write down the minimal generators of their intersection.  The
shipped task asks for one sparse maximal standard monomial.  The generator
never decomposes the ideal it has just built.
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
    "object_regime": "integer_lattice",
    "computational_core": "other",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "artinian monomial ideal given by its minimal monomial generators",
        "sparse monomial over an arbitrary coefficient field",
        "maximal standard monomial (socle basis element)",
    ],
    "verification_operations": [
        "exact monomial divisibility",
        "exact multiplication by each variable",
        "exact integer exponent comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The pure-power caps carry an affine residue invariant whose equal-value "
        "classes are exactly the supports of the maximal standard monomials; "
        "without it one must process the much larger list of mixed generators."
    ),
    "hardness_basis": (
        "Track B: a quadratic-generator incidence scan finds one requested "
        "maximal standard monomial in O(|min(I)|+n) time; at shipping n=112 it "
        "averages 5,757 mixed-generator inspections, 11,514 endpoint comparisons, "
        "and about 0.0008 seconds over eight seeds, whereas the affine-residue "
        "route uses 224 exact field operations once noticed."
    ),
    "max_answer_tokens": 21,
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
    "demo": {"n": 6, "block_size": 2, "calibration_prime": 13},
    "easy": {"n": 96, "block_size": 8, "calibration_prime": 193},
    "medium": {"n": 112, "block_size": 8, "calibration_prime": 227},
    "hard": {"n": 128, "block_size": 8, "calibration_prime": 257},
}

SHIPPING_DIFFICULTY = "medium"

# G9 scratch copies set this so harden.py runs exactly the shipping rung.
if os.environ.get("GV_G9_SINGLE") == "1":
    DIFFICULTY = {
        "easy": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }


STRUCTURAL_HINT = (
    "Modulo the largest displayed cap, the residues c_i minus i times c_1 "
    "are constant on the concealed coordinate classes."
)

PLACEBO_HINT = (
    "Across the displayed generators, careful treatment of indices and "
    "exponents is important for an exact final monomial."
)


CERTIFICATE_LANGUAGE = {
    "description": (
        "One sparse monomial as a JSON list [[i_1,e_1],...,[i_w,e_w]] of "
        "exactly w nonzero factors.  Variable indices are distinct, 1-based, "
        "and increasing; each exponent e_j must equal the displayed cap of "
        "that variable.  Thus the bounded, structure-aware language contains "
        "C(n,w) candidates.  The task requests a maximal standard monomial with "
        "exactly w factors; the ideal can also have maxima of other support sizes."
    ),
    "bounds": {
        "nonzero_factors": "exactly block_size",
        "variable_min": 1,
        "variable_max": "n",
        "exponent": "the selected variable's displayed cap",
        "ordering": "strictly increasing variable index",
        "candidate_count": "binomial(n, block_size)",
    },
}


NOTES = (
    "Section 2.1 fixes monomial ideals, pure powers, irreducibility and the "
    "unique irredundant decomposition. Section 2.2 fixes maximal standard "
    "monomials: d is outside I while d*x_i is in I for every variable; these "
    "monomials form a socle basis and map bijectively to irreducible components. "
    "Step-0 triage therefore identifies direct divisibility as a finite exact "
    "witness check. It also rules out Track A: Section 3 gives the terminating "
    "Slice Algorithm, Section 5 gives its pivot strategies, and Section 7 "
    "benchmarks working implementations against Alexander-dual and Scarf-complex "
    "algorithms. Section 3.2 makes square-free base slices easy; Section 4.2 "
    "detects independent variable sets almost linearly; Section 4.3 solves two "
    "variables directly; and Section 4.7 sorts/remaps large exponents because "
    "their order, not their magnitude, matters. The shipping family avoids "
    "those declared base cases but honestly remains Track B because an incidence "
    "scan is efficient. Generation samples coordinate classes, including at "
    "least one of the requested size, and their capped monomials first. Their "
    "irreducible ideals intersect to the "
    "published pure powers plus one x_i*x_j generator for every cross-class pair. "
    "Class sizes are randomly balanced around the requested witness size, so "
    "seeds remain genuinely different even after variable and exponent remapping. "
    "Caps and the held class are exchangeable, so largest-cap, smallest-cap, "
    "contiguous-index, index-residue, unit-slope-residue, and random-restart "
    "attacks have no planted advantage."
)


# Filled from the three transcripts after running scripts/harden.py.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3, "errors": 0},
    "hinted": {"solved": 2, "attempts": 3, "errors": 0},
    "placebo": {"solved": 0, "attempts": 0, "errors": 4},
    "hinted_verdict": "too_easy_at_shipping",
}


def _is_prime(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 2:
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
    candidate = max(2, value)
    while not _is_prime(candidate):
        candidate += 1
    return candidate


def _validate_params(n, block_size, calibration_prime):
    values = (n, block_size, calibration_prime)
    if not all(isinstance(v, int) and not isinstance(v, bool) for v in values):
        raise TypeError("n, block_size, and calibration_prime must be integers")
    if block_size < 2:
        raise ValueError("block_size must be at least 2")
    if n < 2 * block_size or n % block_size:
        raise ValueError("n must be a multiple of block_size with at least two blocks")
    if not _is_prime(calibration_prime) or calibration_prime <= n:
        raise ValueError("calibration_prime must be prime and strictly greater than n")
    if n // block_size >= calibration_prime:
        raise ValueError("the calibration prime is too small for distinct class tags")


def _sample_class_sizes(n, block_size, rng):
    """A random size multiset summing to n, with one block kept at block_size."""
    block_count = n // block_size
    sizes = [block_size] * block_count
    if block_count < 3:
        return sizes
    # Index 0 is reserved, guaranteeing that the requested language is nonempty.
    # Pairwise transfers keep the total fixed and create structural, not merely
    # numerical, diversity between seeds.
    for _ in range(8 * block_count):
        a, b = rng.sample(range(1, block_count), 2)
        if sizes[a] < 2 * block_size - 2 and sizes[b] > 2:
            sizes[a] += 1
            sizes[b] -= 1
    return sizes


def _answer_from_support(inst, support):
    return [[i + 1, inst["caps"][i]] for i in sorted(support)]


def make_instance(n, seed=0, block_size=8, calibration_prime=257):
    """Inverse-generate an ideal from known maximal standard monomials.

    If B_1,...,B_k partition the variables, the sampled maximal standard
    monomial d_r has exponent cap_i on B_r and exponent zero elsewhere.  The
    intersection of the corresponding irreducible ideals has exactly these
    minimal generators:

      x_i^(cap_i+1), and x_i*x_j whenever i and j lie in different blocks.

    This identity is used forward to build the instance; no maximal standard
    monomial is recovered from the completed generator list.
    """
    _validate_params(n, block_size, calibration_prime)
    rng = random.Random(seed)
    p = calibration_prime
    class_sizes = _sample_class_sizes(n, block_size, rng)
    block_count = len(class_sizes)

    shuffled = list(range(n))
    rng.shuffle(shuffled)
    blocks = []
    offset = 0
    for size in class_sizes:
        blocks.append(shuffled[offset : offset + size])
        offset += size
    anchor_pos = next(i for i, block in enumerate(blocks) if 0 in block)
    blocks[0], blocks[anchor_pos] = blocks[anchor_pos], blocks[0]

    # The affine slope is encoded by cap_1.  Slope 1 is excluded so the obvious
    # unit-slope residue ansatz is a genuine negative control.
    slope = rng.randrange(2, p)
    tags = [0]
    used_tags = {0}

    # Force at least one cap to equal p, making p recoverable as max(caps)
    # without adding non-algebraic metadata to the rendered instance.
    forced_index = blocks[1][0]
    forced_tag = (-slope * (forced_index + 1)) % p
    if forced_tag == 0:
        raise AssertionError("prime larger than n should make the forced tag nonzero")
    tags.append(forced_tag)
    used_tags.add(forced_tag)
    while len(tags) < block_count:
        tag = rng.randrange(1, p)
        if tag not in used_tags:
            used_tags.add(tag)
            tags.append(tag)

    class_of = [None] * n
    caps = [None] * n
    for class_index, block in enumerate(blocks):
        tag = tags[class_index]
        for i in block:
            class_of[i] = class_index
            residue = (slope * (i + 1) + tag) % p
            caps[i] = residue if residue else p

    mixed_pairs = [
        [i + 1, j + 1]
        for i in range(n)
        for j in range(i + 1, n)
        if class_of[i] != class_of[j]
    ]
    rng.shuffle(mixed_pairs)

    eligible_blocks = [block for block in blocks if len(block) == block_size]
    held_block = eligible_blocks[rng.randrange(len(eligible_blocks))]
    answer = _answer_from_support({"caps": caps}, held_block)
    return {
        "family": "maximal standard monomial of an artinian monomial ideal",
        "n": n,
        "block_size": block_size,
        "caps": caps,
        "mixed_pairs": mixed_pairs,
        "minimal_generator_count": n + len(mixed_pairs),
        "answer": answer,
    }


def _pair_lines(pairs, per_line=18):
    tokens = [f"({i},{j})" for i, j in pairs]
    if not tokens:
        return "  (none)"
    return "\n".join(
        "  " + " ".join(tokens[start : start + per_line])
        for start in range(0, len(tokens), per_line)
    )


def render(inst):
    n = inst["n"]
    caps = inst["caps"]
    cap_lines = "\n".join(
        "  " + " ".join(
            f"{i + 1}:{caps[i]}" for i in range(start, min(n, start + 16))
        )
        for start in range(0, n, 16)
    )
    syntax_example = [[i + 1, caps[i]] for i in range(inst["block_size"])]
    statement = f"""Find a maximal standard monomial of prescribed support size in an exact monomial ideal.

Definitions. Work in a polynomial ring K[x_1,...,x_{n}] over an arbitrary
field K. A monomial is x_1^a_1...x_{n}^a_{n} with nonnegative integer
exponents. A monomial u divides v when every exponent of u is at most the
corresponding exponent of v. The monomial ideal generated by a list G contains
exactly the monomials divisible by at least one member of G. A monomial d is
standard when d is not in the ideal. It is maximal standard when d is standard
but d*x_i belongs to the ideal for every i=1,...,{n}. The support of d is the
set of indices i whose exponent in d is positive.

The ideal I below is given by its complete minimal generating set. First, for
every i it contains the pure power x_i^(c_i+1). The caps c_i are:
{cap_lines}

Second, for every pair (i,j) in the following complete list it contains the
quadratic generator x_i*x_j. Pairs are unordered, their displayed indices are
1-based, and no unlisted quadratic monomial is a generator:
{_pair_lines(inst['mixed_pairs'])}

There are {inst['minimal_generator_count']} minimal generators in total.

Return one maximal standard monomial whose support has exactly
w={inst['block_size']} nonzero factors, in sparse JSON form. Write
[[i_1,e_1],...,[i_w,e_w]], where 1 <= i_1 < ... < i_w <= {n}, there are no
repeated variables, and e_t must equal the displayed cap c_(i_t). Every
unlisted variable has exponent zero. Order inside the list matters only for the
required increasing-index canonical format.

Give your final answer inside <answer></answer> tags, as one JSON list of
exactly {inst['block_size']} [variable_index,exponent] pairs. A syntax-only
example (not asserted to solve this instance) is
<answer>{json.dumps(syntax_example, separators=(',', ':'))}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer>\s*(.*?)\s*</answer>", text, flags=re.I | re.S)
    if not matches:
        return None
    try:
        value = json.loads(matches[-1])
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, list) else None


def _pair_set(inst):
    cached = inst.get("_pair_lookup")
    if cached is not None:
        return cached
    return {tuple(pair) for pair in inst["mixed_pairs"]}


def _with_pair_lookup(inst):
    """Ephemeral selftest acceleration; never returned by make_instance."""
    cached = dict(inst)
    cached["_pair_lookup"] = {tuple(pair) for pair in inst["mixed_pairs"]}
    return cached


def verify(inst, answer):
    """Check the maximal-standard-monomial definition, never inst['answer']."""
    if answer == []:
        return False, "answer is empty"
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    w = inst["block_size"]
    if len(answer) != w:
        return False, f"expected exactly {w} nonzero factors"

    parsed = []
    for factor in answer:
        if not isinstance(factor, list) or len(factor) != 2:
            return False, "each factor must be a two-integer JSON list"
        index, exponent = factor
        if (
            isinstance(index, bool)
            or isinstance(exponent, bool)
            or not isinstance(index, int)
            or not isinstance(exponent, int)
        ):
            return False, "variable indices and exponents must be integers"
        if not 1 <= index <= inst["n"]:
            return False, "variable index is out of range"
        parsed.append((index, exponent))

    indices = [index for index, _ in parsed]
    if len(set(indices)) != len(indices):
        return False, "variable indices must be distinct"
    if indices != sorted(indices):
        return False, "factors must be in strictly increasing variable order"
    for index, exponent in parsed:
        cap = inst["caps"][index - 1]
        if exponent != cap:
            return False, f"exponent of x_{index} must equal its cap {cap}"

    pairs = _pair_set(inst)
    # The candidate is outside I exactly when no quadratic generator divides it;
    # pure generators do not divide because every listed exponent equals its cap.
    for a, b in itertools.combinations(indices, 2):
        if (a, b) in pairs:
            return False, f"candidate is in I because x_{a}*x_{b} divides it"

    # Multiplication by a supported variable reaches its pure-power generator.
    # Multiplication by an unsupported variable must reach a displayed quadratic
    # generator.  This executes the definition for every variable.
    selected = set(indices)
    for index in range(1, inst["n"] + 1):
        if index in selected:
            continue
        if not any((min(index, j), max(index, j)) in pairs for j in indices):
            return False, f"candidate*x_{index} is still standard"
    return True, "ok"


def random_candidate(inst, rng):
    support = sorted(rng.sample(range(inst["n"]), inst["block_size"]))
    return _answer_from_support(inst, support)


def search_space(inst):
    return math.comb(inst["n"], inst["block_size"])


def enumerate_all(inst):
    space = search_space(inst)
    if space > 200_000:
        return None
    count = 0
    for support in itertools.combinations(range(inst["n"]), inst["block_size"]):
        count += int(verify(inst, _answer_from_support(inst, support))[0])
    return count


def _classes_from_instance(inst):
    n = inst["n"]
    adjacency = [set() for _ in range(n)]
    for a, b in inst["mixed_pairs"]:
        adjacency[a - 1].add(b - 1)
        adjacency[b - 1].add(a - 1)
    unseen = set(range(n))
    classes = []
    while unseen:
        anchor = min(unseen)
        block = {j for j in range(n) if j == anchor or j not in adjacency[anchor]}
        classes.append(block)
        unseen -= block
    return classes


def canonical_key(inst):
    """Canonical under variables, generators, and exponent-order remapping."""
    class_sizes = sorted(len(block) for block in _classes_from_instance(inst))
    payload = {
        "n": inst["n"],
        "block_size": inst["block_size"],
        "class_sizes": class_sizes,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def escalate(params):
    """Grow the ambient ideal while the sparse witness keeps the same length."""
    # G9 scratch runs are diagnostics of the shipping rung, not a second
    # hardening ladder.  Returning None makes the repository harness finish
    # after recording its three shipping-preset calls.
    if os.environ.get("GV_G9_SINGLE") == "1":
        return None
    out = dict(params)
    next_n = out["n"] + 16
    # Two field operations per coordinate are left after recognizing the affine
    # invariant.  There is no remaining in-family axis once the next rung would
    # exceed G9(c)'s 300-operation cap; the answer itself remains fixed-length.
    if 2 * next_n > 300:
        return None
    out["n"] = next_n
    out["calibration_prime"] = _next_prime(max(out["calibration_prime"] + 1, next_n + 1))
    return out


def _candidate_from_indices(inst, indices):
    return _answer_from_support(inst, [i - 1 for i in sorted(indices)])


def _affine_compact_solve(inst):
    """The intended route; never called by make_instance."""
    p = max(inst["caps"])
    slope = inst["caps"][0] % p
    buckets = {}
    for i, cap in enumerate(inst["caps"], 1):
        residue = (cap - slope * i) % p
        buckets.setdefault(residue, []).append(i)
    candidates = [indices for indices in buckets.values() if len(indices) == inst["block_size"]]
    if not candidates:
        return None
    return _candidate_from_indices(inst, min(candidates))


def _incidence_reference(inst):
    """Exact standard scan of the quadratic generators, with operation counts."""
    n = inst["n"]
    adjacency = [set() for _ in range(n)]
    endpoint_comparisons = 0
    for a, b in inst["mixed_pairs"]:
        endpoint_comparisons += 2
        adjacency[a - 1].add(b - 1)
        adjacency[b - 1].add(a - 1)
    anchor = next(
        (i for i in range(n) if n - len(adjacency[i]) == inst["block_size"]),
        None,
    )
    if anchor is None:
        return None, {
            "pair_inspections": len(inst["mixed_pairs"]),
            "endpoint_comparisons": endpoint_comparisons,
        }
    support = [i + 1 for i in range(n) if i == anchor or i not in adjacency[anchor]]
    if len(support) != inst["block_size"]:
        return None, {
            "pair_inspections": len(inst["mixed_pairs"]),
            "endpoint_comparisons": endpoint_comparisons,
        }
    return _candidate_from_indices(inst, support), {
        "pair_inspections": len(inst["mixed_pairs"]),
        "endpoint_comparisons": endpoint_comparisons,
    }


def _residue_bucket_candidates(inst, slope):
    p = max(inst["caps"])
    buckets = {}
    for i, cap in enumerate(inst["caps"], 1):
        buckets.setdefault((cap - slope * i) % p, []).append(i)
    answers = [
        _candidate_from_indices(inst, indices)
        for indices in buckets.values()
        if len(indices) == inst["block_size"]
    ]
    if not answers:
        answers.append(_candidate_from_indices(inst, range(1, inst["block_size"] + 1)))
    return answers


def _attack_candidates(inst, seed):
    n, w = inst["n"], inst["block_size"]
    ranked = sorted(range(1, n + 1), key=lambda i: (inst["caps"][i - 1], i))
    contiguous = []
    for start in range(n):
        indices = sorted(((start + offset) % n) + 1 for offset in range(w))
        contiguous.append(_candidate_from_indices(inst, indices))
    block_count = n // w
    index_residue = [
        _candidate_from_indices(inst, [residue + 1 + t * block_count for t in range(w)])
        for residue in range(block_count)
    ]
    rrng = random.Random(seed ^ 0x08063680)
    return {
        "outlier_largest_caps": [_candidate_from_indices(inst, ranked[-w:])],
        "outlier_smallest_caps": [_candidate_from_indices(inst, ranked[:w])],
        "greedy_contiguous_windows": contiguous,
        "obvious_index_residue_classes": index_residue,
        "by_hand_unit_slope_residue": _residue_bucket_candidates(inst, 1),
        "random_restart_256": [random_candidate(inst, rrng) for _ in range(256)],
    }


def _relabel_variants(inst, seed):
    rng = random.Random(seed)
    n = inst["n"]
    order = list(range(n))  # new position -> old position
    rng.shuffle(order)
    old_to_new = {old: new for new, old in enumerate(order)}

    relabelled = {
        key: value
        for key, value in inst.items()
        if key not in {"caps", "mixed_pairs", "answer"}
    }
    relabelled["caps"] = [inst["caps"][old] for old in order]
    relabelled["mixed_pairs"] = []
    for a, b in inst["mixed_pairs"]:
        na, nb = old_to_new[a - 1] + 1, old_to_new[b - 1] + 1
        relabelled["mixed_pairs"].append([min(na, nb), max(na, nb)])
    relabelled["answer"] = sorted(
        [[old_to_new[index - 1] + 1, exponent] for index, exponent in inst["answer"]]
    )

    reordered = {
        key: (list(value) if isinstance(value, list) else value)
        for key, value in inst.items()
    }
    reordered["caps"] = list(inst["caps"])
    reordered["answer"] = [list(x) for x in inst["answer"]]
    reordered["mixed_pairs"] = [list(x) for x in inst["mixed_pairs"]]
    rng.shuffle(reordered["mixed_pairs"])

    def remap_caps(base):
        out = {
            key: (list(value) if isinstance(value, list) else value)
            for key, value in base.items()
        }
        out["caps"] = [cap + 1000 + 17 * i for i, cap in enumerate(base["caps"])]
        out["mixed_pairs"] = [list(x) for x in base["mixed_pairs"]]
        out["answer"] = [
            [index, out["caps"][index - 1]] for index, _old_exponent in base["answer"]
        ]
        return out

    relabelled_reordered = {
        key: (list(value) if isinstance(value, list) else value)
        for key, value in relabelled.items()
    }
    relabelled_reordered["caps"] = list(relabelled["caps"])
    relabelled_reordered["answer"] = [list(x) for x in relabelled["answer"]]
    relabelled_reordered["mixed_pairs"] = [list(x) for x in relabelled["mixed_pairs"]]
    rng.shuffle(relabelled_reordered["mixed_pairs"])

    remapped = remap_caps(inst)
    remapped_reordered = remap_caps(reordered)
    relabelled_remapped = remap_caps(relabelled)
    all_three = remap_caps(relabelled_reordered)
    return [
        reordered,
        relabelled,
        remapped,
        relabelled_reordered,
        remapped_reordered,
        relabelled_remapped,
        all_three,
    ]


def _atomic_elements(value):
    if isinstance(value, dict):
        return sum(_atomic_elements(v) for v in value.values())
    if isinstance(value, list):
        return sum(_atomic_elements(v) for v in value)
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
        "construction": "inverse intersection of sampled irreducible monomial ideals",
    }

    inst = _with_pair_lookup(make_instance(seed=19, **shipping))
    answer = [list(x) for x in inst["answer"]]
    swapped = [list(x) for x in answer]
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicated = [list(x) for x in answer]
    duplicated[1][0] = duplicated[0][0]
    out_of_range = [list(x) for x in answer]
    out_of_range[0][0] = 0
    corruptions = {
        "drop": answer[:-1],
        "swap": swapped,
        "duplicate": duplicated,
        "empty": [],
        "out_of_range": out_of_range,
    }
    rejected = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        rejected[name] = {"rejected": not ok, "reason": why}
    reasons = [value["reason"] for value in rejected.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(value["rejected"] for value in rejected.values())
        and len(set(reasons)) == len(reasons),
        "cases": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The support is one residue class, so the sparse monomial is:\n"
        "```json\n<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\nAll omitted exponents are zero."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == answer,
    }

    guess_rng = random.Random(0x08063680)
    guess_total = 200_000
    guess_hits = 0
    started = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - started
    guess_fraction = guess_hits / guess_total
    exact_answers = sum(
        len(block) == inst["block_size"] for block in _classes_from_instance(inst)
    )
    exact_density = exact_answers / search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_fraction,
        "exact_structure_aware_density": exact_density,
        "candidate_space": search_space(inst),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    attack_names = list(_attack_candidates(inst, 0))
    successes = {name: 0 for name in attack_names}
    attempts = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    reference_pairs = 0
    reference_comparisons = 0
    compact_successes = 0
    for seed in range(101, 109):
        trial = _with_pair_lookup(make_instance(seed=seed, **shipping))
        candidates_by_attack = _attack_candidates(trial, seed)
        for name, candidates in candidates_by_attack.items():
            started = time.perf_counter()
            won = any(verify(trial, candidate)[0] for candidate in candidates)
            attack_seconds[name] += time.perf_counter() - started
            successes[name] += int(won)
            attempts[name] += 1

        started = time.perf_counter()
        recovered, counts = _incidence_reference(trial)
        reference_seconds += time.perf_counter() - started
        reference_pairs += counts["pair_inspections"]
        reference_comparisons += counts["endpoint_comparisons"]
        reference_successes += int(
            recovered is not None and verify(trial, recovered)[0]
        )
        compact = _affine_compact_solve(trial)
        compact_successes += int(compact is not None and verify(trial, compact)[0])

    attacks = {
        name: {
            "successes": successes[name],
            "attempts": attempts[name],
            "wall_clock_sec": round(attack_seconds[name], 6),
        }
        for name in attack_names
    }
    reference = {
        "name": "quadratic-generator incidence scan from one anchor variable",
        "complexity": "O(|min(I)| + n) exact pair inspections",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": reference_pairs // 8,
        "endpoint_comparisons": reference_comparisons // 8,
        "solves": f"{reference_successes}/8, as expected",
    }
    all_failed = all(value == 0 for value in successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
        "intended_compact_route": {
            "name": "affine cap-residue bucketing",
            "solves": f"{compact_successes}/8",
            "operations_upper_bound": 2 * inst["n"],
        },
    }

    demo_count = enumerate_all(make_instance(seed=3, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6
        and demo_count == 3
        and all_failed
        and reference_successes == 8,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_sampled_solution_density": guess_fraction,
        "shipping_exact_valid_answer_count": exact_answers,
        "shipping_exact_solution_density": exact_density,
        "demo_exact_solution_count": demo_count,
        "baseline_reference_wall_clock_sec": reference["wall_clock_sec"],
        "baseline_reference_pair_inspections": reference["operations"],
        "baseline_reference_endpoint_comparisons": reference["endpoint_comparisons"],
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    if doubled_params["calibration_prime"] <= doubled_params["n"]:
        doubled_params["calibration_prime"] = _next_prime(doubled_params["n"] + 1)
    started = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_build = time.perf_counter() - started
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    ladder = [DIFFICULTY[name]["n"] for name in DIFFICULTY]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] == 2 * inst["n"]
        and search_space(doubled) > search_space(inst)
        and _atomic_elements(doubled["answer"]) == _atomic_elements(inst["answer"])
        and ladder == sorted(ladder)
        and len(set(ladder)) == len(ladder),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_why,
        "answer_atoms_shipping": _atomic_elements(inst["answer"]),
        "answer_atoms_doubled": _atomic_elements(doubled["answer"]),
        "candidate_space_bits_shipping": search_space(inst).bit_length(),
        "candidate_space_bits_doubled": search_space(doubled).bit_length(),
    }

    invariant_count = 0
    real_transform_count = 0
    unrelated_keys = []
    for seed in range(201, 221):
        original = make_instance(seed=seed, **shipping)
        key = canonical_key(original)
        for transformed in _relabel_variants(original, seed ^ 0x5A5A):
            invariant_count += int(key == canonical_key(transformed))
            real_transform_count += int(verify(transformed, transformed["answer"])[0])
        unrelated_keys.append(key)
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_count == 140
        and real_transform_count == 140
        and distinct_count == 20,
        "invariant_relabellings": invariant_count,
        "invariance_attempts": 140,
        "real_transformations_verified": real_transform_count,
        "real_transformation_attempts": 140,
        "unrelated_distinct_keys": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "minimal-generator list reordering",
            "arbitrary variable relabelling with carried sparse monomial",
            "coordinatewise order-preserving exponent remapping",
            "all nonempty compositions of those three transformations",
        ],
    }

    answer_blobs = []
    for seed in range(20):
        sample = make_instance(seed=seed, **shipping)
        answer_blobs.append(json.dumps(sample["answer"], separators=(",", ":")))
    encoded_answer = json.dumps(inst["answer"], separators=(",", ":"))
    worst_chars = max(map(len, answer_blobs))
    worst_tokens = math.ceil(worst_chars / 4)
    pair_bound_chars = len(
        json.dumps([inst["n"], max(inst["caps"])], separators=(",", ":"))
    )
    answer_bound_chars = 2 + inst["block_size"] * pair_bound_chars + inst["block_size"] - 1
    answer_bound_tokens = math.ceil(answer_bound_chars / 4)
    arms = {name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
    if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]:
        hinted_rate = arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        placebo_rate = arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        hinted_minus_placebo = hinted_rate - placebo_rate
    else:
        hinted_minus_placebo = None
    answer_elements = _atomic_elements(inst["answer"])
    intended_operations = 2 * inst["n"]
    within_caps = (
        len(encoded_answer) <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
        and answer_bound_tokens <= PROBLEM_PROFILE["max_answer_tokens"]
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": len(encoded_answer),
        "answer_tokens": math.ceil(len(encoded_answer) / 4),
        "worst_case_answer_chars_measured": worst_chars,
        "worst_case_answer_tokens_measured": worst_tokens,
        "worst_case_answer_chars_bound": answer_bound_chars,
        "worst_case_answer_tokens_bound": answer_bound_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") is True for value in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
