"""Inverse-generated additive list colorings on Gossett's triangulated cycles.

The native instance is the graph G_{2k} from Example 5.4 of arXiv:2302.02190.
The variable labels are sampled first, locally checked while they are assembled,
and only then hidden among list decoys.  Verification uses the paper's exact
definition: endpoints of every edge must have different sums of neighbour labels.
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


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # pragma: no cover - this module needs only the stdlib
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "the triangulated even-cycle graph G_{2k} from Example 5.4",
        "positive-integer vertex lists",
        "an additive list coloring",
    ],
    "verification_operations": [
        "exact integer neighbour-sum addition",
        "list membership",
        "integer inequality on every graph edge",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Around the cycle, the selected residue differs from the unique residue "
        "missing from its list by a geometric progression modulo seven; without "
        "that invariant one must propagate a width-three constraint state."
    ),
    "hardness_basis": (
        "Track B: bounded-width dynamic programming solves the six-choice cycle "
        "CSP in O(n*6^7); at shipping n=256 the reference implementation measured "
        "1,619,199 exact operations and 0.109 seconds, while the period-six modular "
        "invariant takes 264 operations and must be recognized without tools."
    ),
    "max_answer_tokens": 129,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}


DIFFICULTY = {
    "demo": {"n": 6, "q": 7},
    "easy": {"n": 224, "q": 7},
    "medium": {"n": 240, "q": 7},
    "hard": {"n": 256, "q": 7},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The non-neutral fixed labels and the residues omitted from the variable "
    "lists share a geometric-progression invariant modulo seven."
)
PLACEBO_HINT = (
    "The fixed labels and the entries of every variable list should be tracked "
    "carefully when comparing neighbouring sums."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of exactly n integers; entry i is one of the six distinct "
        "positive integers in the displayed list for v_i."
    ),
    "bounds": {
        "length": "n",
        "choices_per_position": 6,
        "minimum_label": 1,
        "maximum_label": 7,
        "candidate_count": "6^n",
    },
}

NOTES = r"""
Paper boundary. Definition 2.1 fixes the exact task: a positive-integer vertex
labeling is additive when the sums on the open neighbourhoods of adjacent
vertices differ. Theorem 5.1 proves the list result when every odd cycle meets
a simplicial sink. Theorem 5.2 specializes it to the relevant tripartite
graphs, and Example 5.4 supplies exactly the graph used here: an even cycle
v_i with a degree-two simplicial vertex u_i on every cycle edge, all u_i being
sinks in the displayed orientation. No graph surrogate or external reduction
replaces the paper's objects. Lists of six values are allowed because choosing
any four-element sublist puts the instance directly under Example 5.4 and
Theorem 5.2.

STEP 0 hardness decision. The certificate is not computed by an algorithm run
on the public instance: the variable sequence is sampled first, with each new
term avoiding the sole value that could close a bad local equality, and the
three wrap-around constraints are then checked before any lists exist. Lists
are formed afterward. Nevertheless this graph has constant pathwidth, so a
domain-standard dynamic program over the last three labels solves the public
instance in polynomial time (linear in n for the fixed six-element lists).
Track A would therefore be false. This is Track B, and selftest measures the
full width-three reference implementation at the shipping preset.

Compact route. Exactly two fixed labels are non-neutral. Their disjoint numeric
bands encode a nonzero initial residue A and a primitive ratio R modulo seven,
and their adjacency fixes a direction and origin on the cycle. If o_i is the
unique member of {1,...,7} absent from L(v_i), the planted labels satisfy
x_i-o_i=A*R^t mod 7 in that oriented order. Powers of R have period six, so the
route computes six offsets once and then performs one modular addition per
answer entry. The statement never asserts this relation; recognizing it is the
intended invariant.

What is easy. Theorem 5.2 guarantees existence but its Combinatorial
Nullstellensatz proof is not a certificate-recovery algorithm. The particular
Example 5.4 graphs are algorithmically easy for a different reason: bounded
width makes exact dynamic programming effective. The demo is also small enough
for exhaustive enumeration. Those facts are exposed rather than used for a
Track A claim.

Attack controls. Plants are never placed in a privileged list position: lists
are shuffled and every decoy is another member of the same seven-symbol
alphabet. Construction rejects instances solved by endpoint-value outliers, a
left-to-right no-backtracking greedy pass, or the obvious constant-offset
ansatz. The panel also measures 256 structure-aware random restarts. The
reference dynamic program is reported separately, as Track B requires.

Canonicalization. The degree-four v vertices and degree-two u vertices are
intrinsically distinguished. The remaining graph automorphisms are the
dihedral symmetries of the cycle, while list order is irrelevant. canonical_key
sorts each list and minimizes over every rotation and reflection; selftest
carries witnesses through all three kinds of relabeling.
""".strip()


G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 1, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "cap_bound_after_one_solve",
}


def _validate_parameters(n, seed, q):
    if isinstance(n, bool) or not isinstance(n, int) or n < 6 or n % 2:
        raise ValueError("n must be an even integer at least 6")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if q != 7:
        raise ValueError("this family uses q=7")


def _residue_to_label(value, q):
    value %= q
    return q if value == 0 else value


def _neighbour_sums(fixed, variable):
    n = len(variable)
    sum_u = [variable[i] + variable[(i + 1) % n] for i in range(n)]
    sum_v = [
        variable[(i - 1) % n] + variable[(i + 1) % n]
        + fixed[(i - 1) % n] + fixed[i]
        for i in range(n)
    ]
    return sum_u, sum_v


def _coloring_failure(fixed, variable):
    """Return the first additive-coloring failure, or None."""
    n = len(variable)
    sum_u, sum_v = _neighbour_sums(fixed, variable)
    for i in range(n):
        j = (i + 1) % n
        if sum_v[i] == sum_v[j]:
            return (
                f"neighbour-sum collision on cycle edge v_{i}--v_{j}: "
                f"both sums are {sum_v[i]}"
            )
        if sum_u[i] == sum_v[i]:
            return (
                f"neighbour-sum collision on spoke edge u_{i}--v_{i}: "
                f"both sums are {sum_u[i]}"
            )
        if sum_u[i] == sum_v[j]:
            return (
                f"neighbour-sum collision on spoke edge u_{i}--v_{j}: "
                f"both sums are {sum_u[i]}"
            )
    return None


def _sample_valid_variable_sequence(n, q, fixed, rng):
    """Sample the witness before lists exist; retries concern only three seams."""
    for _ in range(10_000):
        values = [rng.randrange(1, q + 1) for _ in range(3)]
        for j in range(3, n):
            i = j - 2
            # S(v_i)=S(v_{i+1}) for exactly this candidate value, if it lies
            # in 1..q. All earlier cycle constraints are already closed.
            forbidden = (
                values[j - 3] + values[j - 1] + fixed[j - 3]
                - values[j - 2] - fixed[j - 1]
            )
            choices = [x for x in range(1, q + 1) if x != forbidden]
            values.append(rng.choice(choices))
        if _coloring_failure(fixed, values) is None:
            return values
    raise RuntimeError("failed to close the three cyclic seam constraints")


def _missing_values(inst):
    universe = set(range(1, inst["q"] + 1))
    return [next(iter(universe - set(row))) for row in inst["lists"]]


def _local_cycle_ok(fixed, a, b, c, d, i):
    """Check edge v_i--v_(i+1) for x_(i-1),x_i,x_(i+1),x_(i+2)."""
    left = a + c + fixed[(i - 1) % len(fixed)]
    right = b + d + fixed[(i + 1) % len(fixed)]
    return left != right


def _greedy_candidate(inst):
    lists = [sorted(row) for row in inst["lists"]]
    fixed = inst["fixed"]
    values = [row[0] for row in lists[:3]]
    for j in range(3, inst["n"]):
        i = j - 2
        choice = next((x for x in lists[j]
                       if _local_cycle_ok(fixed, values[j - 3],
                                          values[j - 2], values[j - 1], x, i)),
                      lists[j][0])
        values.append(choice)
    return values


def _constant_offset_candidates(inst):
    q = inst["q"]
    missing = _missing_values(inst)
    return [
        [_residue_to_label(o + delta, q) for o in missing]
        for delta in range(1, q)
    ]


def _attack_solved(inst, answer):
    return verify(inst, answer)[0]


def _dihedral_data(lists, fixed, answer, start, direction):
    """Rename v/u around the sun graph, carrying an optional answer."""
    n = len(lists)
    if direction == 1:
        new_lists = [list(lists[(start + j) % n]) for j in range(n)]
        new_fixed = [fixed[(start + j) % n] for j in range(n)]
        new_answer = None if answer is None else [answer[(start + j) % n]
                                                  for j in range(n)]
    else:
        new_lists = [list(lists[(start - j) % n]) for j in range(n)]
        new_fixed = [fixed[(start - j - 1) % n] for j in range(n)]
        new_answer = None if answer is None else [answer[(start - j) % n]
                                                  for j in range(n)]
    return new_lists, new_fixed, new_answer


def make_instance(n, seed=0, **params):
    """Plant a native additive coloring first, then construct and relabel lists."""
    q = params.pop("q", 7)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    _validate_parameters(n, seed, q)
    rng = random.Random(seed)

    for _ in range(2_000):
        initial = rng.randrange(1, q)
        ratio = rng.choice((3, 5))  # the two primitive roots modulo seven
        fixed = [4 * q] * n
        fixed[0] = q + initial
        fixed[1] = 2 * q + ratio

        answer = _sample_valid_variable_sequence(n, q, fixed, rng)
        offset = initial
        missing = []
        for value in answer:
            missing.append(_residue_to_label(value - offset, q))
            offset = offset * ratio % q
        lists = []
        for omitted in missing:
            row = [value for value in range(1, q + 1) if value != omitted]
            rng.shuffle(row)
            lists.append(row)

        # Apply a genuine graph automorphism so the calibration edge and the
        # direction of the recurrence are not tied to renderer positions.
        start = rng.randrange(n)
        direction = rng.choice((-1, 1))
        lists, fixed, answer = _dihedral_data(
            lists, fixed, answer, start, direction
        )
        trial = {"n": n, "q": q, "fixed": fixed, "lists": lists}

        # Construction-aware filters: retain the held certificate, but reject
        # instances exposed by the declared cheap attacks.
        cheap = [
            [min(row) for row in lists],
            [max(row) for row in lists],
            _greedy_candidate(trial),
        ]
        cheap.extend(_constant_offset_candidates(trial))
        if not any(_attack_solved(trial, candidate) for candidate in cheap):
            trial["answer"] = answer
            return trial
    raise RuntimeError("could not construct an attack-resistant instance")


def render(inst):
    """Render a self-contained statement in the paper's native objects."""
    n = inst["n"]
    rows = "\n".join(
        f"  {i}: fixed(u_{i})={inst['fixed'][i]}; "
        f"list(v_{i})={json.dumps(inst['lists'][i], separators=(',', ':'))}"
        for i in range(n)
    )
    statement = f"""Additive list coloring of a triangulated even cycle

The graph has {2 * n} vertices v_0,...,v_{n - 1} and u_0,...,u_{n - 1}.
All subscripts below are reduced modulo {n}.  Its undirected edges are exactly

  v_i--v_(i+1),  u_i--v_i,  and  u_i--v_(i+1)  for every i=0,...,{n - 1}.

Thus the v-vertices form an even cycle and u_i completes a triangle on its
i-th edge.  A vertex's neighbour sum is the ordinary integer sum of the labels
on all vertices adjacent to it.  A labeling is additive when the two endpoints
of every edge have different neighbour sums.

Each u_i already has the fixed positive-integer label shown below.  Choose
exactly one integer from each six-element list for v_i so that the complete
labeling is additive.  List order has no meaning, repeated labels at different
vertices are allowed, and all sums are ordinary integers (not residues).

Instance rows, indexed from 0:
{rows}

Return a JSON list of exactly {n} integers in v-index order: entry i is the
chosen member of list(v_i).  Indices are 0-based and no u-label is repeated in
the answer.

Give your final answer inside <answer></answer> tags, as one JSON list.
Example: <answer>[1,2,3,4,5,6]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Extract the final tagged JSON list, tolerating prose and code fences."""
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text,
                        flags=re.IGNORECASE | re.DOTALL)
    if not blocks:
        return None
    body = blocks[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, list) else None


def verify(inst, answer):
    """Check list membership and every exact neighbour-sum inequality."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    n = inst.get("n")
    if len(answer) != n:
        return False, f"wrong answer length: expected {n}, got {len(answer)}"
    lists = inst.get("lists")
    fixed = inst.get("fixed")
    if (not isinstance(lists, list) or len(lists) != n
            or not isinstance(fixed, list) or len(fixed) != n):
        return False, "malformed instance arrays"
    for i, value in enumerate(answer):
        if isinstance(value, bool) or not isinstance(value, int):
            return False, f"label for v_{i} is not an integer"
        if value not in lists[i]:
            return False, f"label {value} for v_{i} is not in its list"
    failure = _coloring_failure(fixed, answer)
    if failure is not None:
        return False, failure
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample one already-legal list member independently per vertex."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    return [rng.choice(row) for row in inst["lists"]]


def search_space(inst):
    """Every list choice is structural and has already been enforced."""
    return math.prod(len(row) for row in inst["lists"])


def enumerate_all(inst):
    """Count every valid list choice exactly when at most one million exist."""
    if search_space(inst) > 1_000_000:
        return None
    count = 0
    for candidate in itertools.product(*inst["lists"]):
        count += int(verify(inst, list(candidate))[0])
    return count


def canonical_key(inst):
    """Canonical structural key under list reorderings and all dihedral maps."""
    n = inst["n"]
    lists = [tuple(sorted(row)) for row in inst["lists"]]
    fixed = list(inst["fixed"])
    forms = []
    for start in range(n):
        for direction in (-1, 1):
            ls, fs, _ = _dihedral_data(lists, fixed, None, start, direction)
            forms.append(tuple((fs[i], tuple(ls[i])) for i in range(n)))
    payload = json.dumps(min(forms), separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def escalate(params):
    """Grow the cyclic haystack while the fixed-size certificate cap permits."""
    clean = {k: v for k, v in params.items() if not k.startswith("_")}
    n = clean.get("n")
    q = clean.get("q", 7)
    if not isinstance(n, int):
        return None
    if n < 256:
        return {"n": min(256, n + 16), "q": q}
    return "cap_bound"


def _compact_solve(inst):
    """Use the planted invariant, without consulting inst['answer']."""
    n, q = inst["n"], inst["q"]
    fixed = inst["fixed"]
    a_positions = [i for i, value in enumerate(fixed) if q < value < 2 * q]
    r_positions = [i for i, value in enumerate(fixed) if 2 * q < value < 3 * q]
    if len(a_positions) != 1 or len(r_positions) != 1:
        return None
    ai, ri = a_positions[0], r_positions[0]
    initial = fixed[ai] - q
    ratio = fixed[ri] - 2 * q
    if ri == (ai + 1) % n:
        positions = [(ai + t) % n for t in range(n)]
    elif ri == (ai - 1) % n:
        positions = [(ai + 1 - t) % n for t in range(n)]
    else:
        return None
    missing = _missing_values(inst)
    offsets = [initial]
    for _ in range(5):
        offsets.append(offsets[-1] * ratio % q)
    answer = [None] * n
    for step, position in enumerate(positions):
        offset = offsets[step % 6]
        answer[position] = _residue_to_label(missing[position] + offset, q)
    return answer


def _reference_dynamic_program(inst):
    """Generic width-three CSP dynamic program; never uses the planted invariant."""
    n = inst["n"]
    lists = [sorted(row) for row in inst["lists"]]
    fixed = inst["fixed"]
    stats = {"constraint_evaluations": 0, "exact_operations": 0,
             "initial_triples": 0, "max_states": 0}

    for first in itertools.product(lists[0], lists[1], lists[2]):
        stats["initial_triples"] += 1
        paths = {tuple(first): list(first)}
        for j in range(3, n):
            i = j - 2
            nxt = {}
            for state, path in paths.items():
                a, b, c = state
                for value in lists[j]:
                    stats["constraint_evaluations"] += 1
                    if _local_cycle_ok(fixed, a, b, c, value, i):
                        key = (b, c, value)
                        if key not in nxt:
                            nxt[key] = path + [value]
            paths = nxt
            stats["max_states"] = max(stats["max_states"], len(paths))
            if not paths:
                break
        for path in paths.values():
            # Three seam constraints and all spoke constraints are most simply
            # checked by the exact public verifier.
            stats["constraint_evaluations"] += 3
            if verify(inst, path)[0]:
                stats["exact_operations"] = 5 * stats["constraint_evaluations"]
                return path, stats
    stats["exact_operations"] = 5 * stats["constraint_evaluations"]
    return None, stats


def _find_corruption(inst, kind, used_reasons):
    base = list(inst["answer"])
    candidates = []
    if kind == "swapped":
        for i in range(inst["n"]):
            for j in range(i + 1, inst["n"]):
                if base[j] in inst["lists"][i] and base[i] in inst["lists"][j]:
                    candidate = list(base)
                    candidate[i], candidate[j] = candidate[j], candidate[i]
                    if candidate != base:
                        candidates.append(candidate)
    elif kind == "duplicated":
        for i in range(inst["n"]):
            for j in range(inst["n"]):
                if i != j and base[i] != base[j] and base[i] in inst["lists"][j]:
                    candidate = list(base)
                    candidate[j] = base[i]
                    candidates.append(candidate)
    for candidate in candidates:
        ok, reason = verify(inst, candidate)
        if not ok and reason not in used_reasons:
            return candidate, reason
    return None, "no distinct rejected corruption found"


def selftest():
    """Run all mandatory gates and return measured, JSON-native evidence."""
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}
    shipping_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    shipping = make_instance(seed=0, **shipping_params)

    failures = []
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            checks += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures, "checks": checks, "failures": failures,
    }

    used = set()
    corruption_results = {}
    fixed_corruptions = {
        "empty": [],
        "dropped_element": shipping["answer"][:-1],
        "out_of_range": [99] + shipping["answer"][1:],
    }
    for name, candidate in fixed_corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
        used.add(reason)
    for name in ("swapped", "duplicated"):
        candidate, reason = _find_corruption(shipping, name, used)
        ok = True if candidate is None else verify(shipping, candidate)[0]
        corruption_results[name] = {"rejected": candidate is not None and not ok,
                                    "reason": reason}
        used.add(reason)
    reasons = [entry["reason"] for entry in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": (all(entry["rejected"] for entry in corruption_results.values())
                 and len(reasons) == len(set(reasons))),
        "corruptions": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    encoded = json.dumps(shipping["answer"], separators=(",", ":"))
    realistic = ("I compared every exact neighbour sum.\n```json\n"
                 f"<answer>{encoded}</answer>\n```\n")
    parsed = parse_answer(realistic)
    garbage = ["", "no tags", "<answer>not json</answer>",
               "<answer>{\"x\":1}</answer>"]
    report["G3_round_trip"] = {
        "pass": (parsed == shipping["answer"]
                 and all(parse_answer(text) is None for text in garbage)),
        "realistic_response_round_trips": parsed == shipping["answer"],
        "garbage_cases_rejected": sum(parse_answer(text) is None
                                      for text in garbage),
    }

    guess_rng = random.Random(0x230202190)
    guess_total = 200_000
    guess_hits = 0
    start_time = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(shipping,
                                 random_candidate(shipping, guess_rng))[0])
    guess_seconds = time.perf_counter() - start_time
    guess_probability = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_probability,
        "candidate_space": f"6^{shipping['n']}",
        "candidate_space_bits": search_space(shipping).bit_length(),
        "structure_aware": True,
        "sampling_wall_clock_sec": round(guess_seconds, 6),
    }

    attack_names = (
        "outlier_endpoint_values",
        "greedy_smallest_no_backtracking",
        "random_restart_256",
        "by_hand_constant_missing_offset",
    )
    successes = {name: 0 for name in attack_names}
    elapsed = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    reference_operations = 0
    reference_constraints = 0
    reference_initials = 0
    compact_successes = 0
    for seed in range(100, 108):
        inst = make_instance(seed=seed, **shipping_params)
        candidates = {
            "outlier_endpoint_values": [
                [min(row) for row in inst["lists"]],
                [max(row) for row in inst["lists"]],
            ],
            "greedy_smallest_no_backtracking": [_greedy_candidate(inst)],
            "random_restart_256": [
                random_candidate(inst, random.Random((seed << 16) + restart))
                for restart in range(256)
            ],
            "by_hand_constant_missing_offset":
                _constant_offset_candidates(inst),
        }
        for name in attack_names:
            started = time.perf_counter()
            won = any(verify(inst, candidate)[0]
                      for candidate in candidates[name])
            elapsed[name] += time.perf_counter() - started
            successes[name] += int(won)

        started = time.perf_counter()
        recovered, stats = _reference_dynamic_program(inst)
        reference_seconds += time.perf_counter() - started
        reference_successes += int(
            recovered is not None and verify(inst, recovered)[0]
        )
        reference_operations += stats["exact_operations"]
        reference_constraints += stats["constraint_evaluations"]
        reference_initials += stats["initial_triples"]
        compact = _compact_solve(inst)
        compact_successes += int(compact is not None
                                 and verify(inst, compact)[0])

    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(elapsed[name], 6),
        }
        for name in attack_names
    }
    reference = {
        "name": "width-three dynamic programming on the cyclic CSP",
        "complexity": "O(n*s^7), hence O(n) for fixed s=6",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": reference_operations // 8,
        "constraint_evaluations": reference_constraints // 8,
        "initial_triples_tried": reference_initials // 8,
        "solves": f"{reference_successes}/8, as expected",
    }
    all_failed = all(value == 0 for value in successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
        "intended_compact_route": {
            "name": "missing-residue geometric progression",
            "solves": f"{compact_successes}/8",
            "operations": shipping["n"] + 8,
        },
    }

    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": (guess_probability < 1e-6 and demo_count is not None
                 and demo_count > 0 and all_failed
                 and reference_successes == 8 and compact_successes == 8),
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_solution_density": guess_probability,
        "demo_n": demo["n"],
        "demo_exact_solution_count": demo_count,
        "baseline_attack": "random_restart_256",
        "baseline_attack_wall_clock_sec": round(
            elapsed["random_restart_256"] / 8, 6
        ),
        "baseline_attack_iterations": 256,
        "reference_wall_clock_sec": reference["wall_clock_sec"],
        "reference_operation_count": reference["operations"],
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    started = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_seconds = time.perf_counter() - started
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    ladder = [DIFFICULTY[name]["n"] for name in DIFFICULTY]
    report["G7_scales"] = {
        "pass": (doubled_ok and doubled["n"] == 2 * shipping["n"]
                 and ladder == sorted(ladder)
                 and len(ladder) == len(set(ladder))
                 and search_space(doubled) > search_space(shipping)),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "doubled_build_sec": round(doubled_seconds, 6),
        "doubled_verify_reason": doubled_reason,
        "candidate_space_bits_shipping": search_space(shipping).bit_length(),
        "candidate_space_bits_doubled": search_space(doubled).bit_length(),
    }

    invariant_count = 0
    carried_count = 0
    unrelated = []
    for seed in range(201, 221):
        inst = make_instance(seed=seed, **shipping_params)
        key = canonical_key(inst)
        rng = random.Random(seed ^ 0xD1EED)
        reordered = {
            "n": inst["n"], "q": inst["q"], "fixed": list(inst["fixed"]),
            "lists": [rng.sample(row, len(row)) for row in inst["lists"]],
            "answer": list(inst["answer"]),
        }
        shift = rng.randrange(inst["n"])
        rot_l, rot_f, rot_a = _dihedral_data(
            inst["lists"], inst["fixed"], inst["answer"], shift, 1
        )
        rotated = {"n": inst["n"], "q": inst["q"], "fixed": rot_f,
                   "lists": rot_l, "answer": rot_a}
        ref_l, ref_f, ref_a = _dihedral_data(
            reordered["lists"], reordered["fixed"], reordered["answer"],
            shift, -1
        )
        reflected = {"n": inst["n"], "q": inst["q"], "fixed": ref_f,
                     "lists": ref_l, "answer": ref_a}
        for transformed in (reordered, rotated, reflected):
            invariant_count += int(canonical_key(transformed) == key)
            carried_count += int(verify(transformed,
                                        transformed["answer"])[0])
        unrelated.append(key)
    report["G8_canonical_key"] = {
        "pass": (invariant_count == 60 and carried_count == 60
                 and len(set(unrelated)) == 20),
        "invariant_relabellings": invariant_count,
        "relabelled_witnesses_verified": carried_count,
        "unrelated_distinct_keys": len(set(unrelated)),
        "unrelated_attempts": 20,
        "transformations": [
            "independent reordering inside every vertex list",
            "cycle rotation with the witness carried through",
            "reflection composed with list reordering and carried witness",
        ],
    }

    answer_chars = len(encoded)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = len(shipping["answer"])
    intended_operations = shipping["n"] + 8
    arms = {name: dict(G9_EVIDENCE[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] == answer_tokens
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items()
             if key.startswith("G") and isinstance(value, dict)]
    report["all_passed"] = all(value.get("pass") is True for value in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
