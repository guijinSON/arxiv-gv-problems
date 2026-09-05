"""Verified b-vertex generator for arXiv:1607.08453.

The native object is a strong product of two vertex-coloured cycles.  Each
factor colouring is a b-colouring with one certified b-vertex of each of three
colours.  Lemma 2.2 (``b-homomorphism'') and Corollary 3.2 of the paper carry
those witnesses to the product.  Labels are affine-scrambled coordinates, so
generation transports known witnesses rather than solving a generated graph.
"""

from __future__ import annotations

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


TRACK = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "two exactly specified vertex-coloured cycle graphs",
        "their strong graph product",
        "a b-colouring of the product",
        "six factor vertices certifying nine product b-vertices",
    ],
    "verification_operations": [
        "exact modular affine evaluation",
        "cycle-neighbour colour lookup",
        "strong-product neighbourhood colour-set comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Undoing the affine label changes exposes three phase boundaries in "
        "each alternating cycle colouring; without that coordinate change a "
        "solver scans the large factor graphs for b-vertices."
    ),
    "hardness_basis": (
        "Track B: the standard exact neighbourhood scan is "
        "O((|V(A)|+|V(B)|)L) for L decoder stages and at the medium shipping "
        "preset solved 8/8 with 99,603,306 mean exact operations in 17.37 mean "
        "seconds, while composing the inverse affine changes takes 158 exact "
        "operations; the efficient scan rules out a Track A claim."
    ),
    "max_answer_tokens": 17,
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
        "A JSON 2-by-3 matrix [[a0,a1,a2],[b0,b1,b2]]; row A (respectively B) "
        "contains one in-range factor label of each colour 0,1,2 in that fixed "
        "order. Repeats are forbidden within a row."
    ),
    "bounds": {
        "rows": 2,
        "labels_per_row": 3,
        "label_range": "0 through the corresponding factor order minus one",
        "fixed_colour_order": [0, 1, 2],
        "distinct_within_row": True,
    },
}

# n is the minimum odd block length.  Each factor has 3s vertices for an odd
# s in [n,n+2*spread].  The witness always remains six integers.
DIFFICULTY: dict = {
    "medium": {"n": 1_000_001, "spread": 100_000, "chain_len": 14},
}
SHIPPING_DIFFICULTY = "medium"

STRUCTURAL_HINT = (
    "In decoded cycle coordinates, the alternating colour pattern changes "
    "phase at odd-block boundaries."
)
PLACEBO_HINT = (
    "In both factor descriptions, careful attention to modular conventions "
    "prevents indexing mistakes."
)

# Filled from the script-owned runs after STEP 4.  These are diagnostics; only
# the answer-size and intended-route caps gate G9.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}

NOTES = r"""
STEP 0.  Section 1 fixes the exact b-vertex, b-colouring, and fall-colouring
definitions.  Section 2.1 defines b-homomorphisms and Lemma 2.2 proves that
they are preserved by every adjacency product.  Section 3 gives the product
adjacency rules; Proposition 3.1 and Corollary 3.2 specialize the product of
the target complete graphs to a complete graph for the lexicographic, strong,
and co-normal products.  This module uses the strong product.

The certificate-producing method is explicit, so Track A is false.  A factor
is a cycle whose decoded colour word consists of three odd alternating blocks:
0101..., 1212..., 2020....  Direct inspection shows that precisely the first
vertex of each block sees both other colours.  Independent affine bijections
relabel the two cycles, carrying those six known vertices with them.  Lemma
2.2 then says their nine Cartesian pairs are b-vertices for all nine product
colours.  Generation only applies inverse affine maps to the known boundary
coordinates; it never searches the generated graph.

The mechanical certificate algorithm scans every factor label, decodes it,
and compares the colours in its closed cycle neighbourhood.  It is linear in
the displayed factor orders and decoder length and succeeds, as Track B
requires.  The compact route instead composes each decoder's inverse affine
map and applies it to the three block boundaries.  The adversaries test degree
outliers (all factor degrees are two), first-labelled representatives, random
legal representatives, and the obvious but wrong assumption that encoded
labels themselves are decoded block coordinates.
""".strip()


# ---------------------------------------------------------------------------
# Exact factor construction


def _validate_params(n: int, spread: int, chain_len: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 3:
        raise ValueError("n must be an integer at least 3")
    if isinstance(spread, bool) or not isinstance(spread, int) or spread < 0:
        raise ValueError("spread must be a nonnegative integer")
    if (isinstance(chain_len, bool) or not isinstance(chain_len, int)
            or chain_len < 1 or chain_len > 26):
        raise ValueError("chain_len must be an integer from 1 through 26")


def _next_odd(value: int) -> int:
    return value if value % 2 else value + 1


def _unit(modulus: int, rng: random.Random) -> int:
    """Draw a nontrivial unit for an affine permutation."""
    while True:
        value = rng.randrange(2, modulus)
        if math.gcd(value, modulus) == 1:
            return value


def _make_factor(s: int, chain_len: int, rng: random.Random) -> dict:
    modulus = 3 * s
    stages = []
    for _ in range(chain_len):
        multiplier = _unit(modulus, rng)
        shift = rng.randrange(modulus)
        stages.append([multiplier, shift, pow(multiplier, -1, modulus)])
    return {"s": s, "order": modulus, "stages": stages}


def _decode(factor: dict, label: int, counter: dict | None = None) -> int:
    value = label
    modulus = factor["order"]
    for multiplier, shift, _inverse in factor["stages"]:
        value = (multiplier * value + shift) % modulus
        if counter is not None:
            counter["decoder_stages"] += 1
    return value


def _encode(factor: dict, coordinate: int) -> int:
    value = coordinate % factor["order"]
    modulus = factor["order"]
    for _multiplier, shift, inverse in reversed(factor["stages"]):
        value = (inverse * (value - shift)) % modulus
    return value


def _base_colour(factor: dict, coordinate: int) -> int:
    block, offset = divmod(coordinate % factor["order"], factor["s"])
    return (block + (offset & 1)) % 3


def _factor_colour(factor: dict, label: int) -> int:
    return _base_colour(factor, _decode(factor, label))


def _is_factor_b_vertex(factor: dict, label: int) -> bool:
    coordinate = _decode(factor, label)
    colours = {
        _base_colour(factor, coordinate - 1),
        _base_colour(factor, coordinate),
        _base_colour(factor, coordinate + 1),
    }
    return colours == {0, 1, 2}


def _product_colour(inst: dict, vertex: tuple[int, int]) -> int:
    first, second = inst["factors"]
    return 3 * _factor_colour(first, vertex[0]) + _factor_colour(second, vertex[1])


def _is_product_b_vertex(inst: dict, vertex: tuple[int, int]) -> bool:
    first, second = inst["factors"]
    x = _decode(first, vertex[0])
    y = _decode(second, vertex[1])
    # The strong-product closed neighbourhood is the Cartesian product of the
    # two closed cycle neighbourhoods.  Seeing all nine colours is exactly the
    # b-vertex condition for the eight colours other than the vertex's own.
    colours = {
        3 * _base_colour(first, x + dx) + _base_colour(second, y + dy)
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
    }
    return colours == set(range(9))


def make_instance(n: int, seed: int = 0, spread: int = 0,
                  chain_len: int = 8, **params) -> dict:
    """Transform known factor b-vertices through random affine relabellings."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, spread, chain_len)
    rng = random.Random(seed)
    base = _next_odd(n)
    sizes = [base + 2 * rng.randrange(spread + 1) for _ in range(2)]
    factors = [_make_factor(s, chain_len, rng) for s in sizes]

    # In decoded coordinates c*s is the unique b-vertex of colour c.  Applying
    # the inverse label maps is transportation of a known certificate.
    answer = [
        [_encode(factor, colour * factor["s"]) for colour in range(3)]
        for factor in factors
    ]
    inst = {
        "paper": "arXiv:1607.08453",
        "product": "strong",
        "number_of_product_colours": 9,
        "factors": factors,
        "answer": answer,
    }
    ok, reason = verify(inst, answer)
    if not ok:
        raise AssertionError("transported certificate failed: " + reason)
    return inst


# ---------------------------------------------------------------------------
# Solver-facing contract


def _factor_render(name: str, factor: dict) -> str:
    lines = [
        f"Factor {name}: s={factor['s']} (odd), order m=3s={factor['order']}.",
        f"Its encoded vertex labels are the integers 0 through {factor['order'] - 1}.",
        "To decode a label x, start z=x and apply these rows in order;",
        "a row (a,b,a_inv) means z <- (a*z+b) mod m, and a_inv is",
        "the displayed multiplicative inverse of a modulo m:",
    ]
    lines.extend(
        f"  ({a}, {b}, {inverse})"
        for a, b, inverse in factor["stages"]
    )
    lines.extend([
        "Two encoded labels are adjacent exactly when their decoded coordinates",
        "differ by +1 or -1 modulo m, so this factor is a cycle.",
        "For decoded coordinate t, write t=q*s+r with q in {0,1,2} and",
        "0<=r<s. Its colour is (q + (r mod 2)) mod 3.",
    ])
    return "\n".join(lines)


def render(inst: dict) -> str:
    """Render the complete native graph-product certificate problem."""
    statement = f"""Find b-vertices for a strong-product b-colouring

A proper k-colouring assigns one colour in {{0,...,k-1}} to every vertex and
gives adjacent vertices different colours.  A vertex of colour c is a
b-vertex if it has at least one neighbour of every colour other than c.  A
proper colouring is a b-colouring if every colour has a b-vertex.

{_factor_render('A', inst['factors'][0])}

{_factor_render('B', inst['factors'][1])}

The strong product P of A and B has ordered-pair vertices (x,y).  Distinct
(x,y) and (x',y') are adjacent exactly when one of the following holds:
  * x=x' and y is adjacent to y' in B;
  * y=y' and x is adjacent to x' in A;
  * x is adjacent to x' in A and y is adjacent to y' in B.
The displayed product colouring is
  C(x,y) = 3*colour_A(x) + colour_B(y),
so its colours are the integers 0 through 8.

Your certificate must be [[a0,a1,a2],[b0,b1,b2]].  For c=0,1,2, ac must be
an encoded label of a b-vertex of colour c in A, and bc must be an encoded
label of a b-vertex of colour c in B.  Equivalently, every one of the nine
ordered pairs (ai,bj) must be a b-vertex of product colour 3i+j.  The order of
the two rows and the colour order 0,1,2 within each row are fixed.  Labels are
decimal integers, all bounds above are inclusive, and repeats are forbidden
within either row.

"""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "Hint: " + STRUCTURAL_HINT + "\n\n"
    elif mode == "placebo":
        statement += "Hint: " + PLACEBO_HINT + "\n\n"
    statement += (
        "Give your final answer inside <answer></answer> tags as one JSON "
        "2-by-3 matrix of decimal integers.\n"
        "Example: <answer>[[3,17,42],[8,29,11]]</answer>\n"
        "Output nothing else inside the tags."
    )
    return statement


def parse_answer(text: str) -> object | None:
    """Extract the last tagged JSON 2-by-3 matrix, tolerating prose/fences."""
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\s*>(.*?)</answer\s*>", text,
                        flags=re.IGNORECASE | re.DOTALL)
    if not blocks:
        return None
    body = blocks[-1].strip()
    body = re.sub(r"^```(?:json|text)?\s*", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\s*```$", "", body).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    if any(not isinstance(row, list) for row in value):
        return None
    if any(any(isinstance(x, bool) or not isinstance(x, int) for x in row)
           for row in value):
        return None
    return value


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any six-label certificate locally and exactly; never read answer."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON matrix"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) != 2 or any(not isinstance(row, list) for row in answer):
        return False, "answer must have exactly two list rows"
    if any(len(row) != 3 for row in answer):
        return False, "each factor row must contain exactly three labels"
    if any(isinstance(value, bool) or not isinstance(value, int)
           for row in answer for value in row):
        return False, "every factor label must be a decimal integer"

    local_colour_sets: list[list[set[int]]] = []
    for factor_index, (factor, row) in enumerate(zip(inst["factors"], answer)):
        name = "A" if factor_index == 0 else "B"
        if any(value < 0 or value >= factor["order"] for value in row):
            return False, f"a factor-{name} label is outside its inclusive range"
        if len(set(row)) != 3:
            return False, f"factor {name} contains a repeated label"
        factor_sets = []
        for expected_colour, label in enumerate(row):
            coordinate = _decode(factor, label)
            actual_colour = _base_colour(factor, coordinate)
            if actual_colour != expected_colour:
                return False, (
                    f"factor {name} entry {expected_colour} has colour "
                    f"{actual_colour}, not {expected_colour}"
                )
            local = {
                _base_colour(factor, coordinate - 1),
                actual_colour,
                _base_colour(factor, coordinate + 1),
            }
            if local != {0, 1, 2}:
                return False, (
                    f"factor {name} entry {expected_colour} is not a b-vertex"
                )
            factor_sets.append(local)
        local_colour_sets.append(factor_sets)

    for first_colour, x in enumerate(answer[0]):
        for second_colour, y in enumerate(answer[1]):
            expected = 3 * first_colour + second_colour
            product_colours = {
                3 * left + right
                for left in local_colour_sets[0][first_colour]
                for right in local_colour_sets[1][second_colour]
            }
            if expected not in product_colours:
                return False, f"pair ({x},{y}) has the wrong product colour"
            if product_colours != set(range(9)):
                return False, f"pair ({x},{y}) is not a product b-vertex"
    return True, "ok"


# ---------------------------------------------------------------------------
# Bounded answer language and canonicalization


def _sample_label_of_colour(factor: dict, colour: int,
                            rng: random.Random) -> int:
    """Uniformly sample one of the exactly s labels of a stated colour."""
    s = factor["s"]
    even_count = (s + 1) // 2
    choice = rng.randrange(s)
    if choice < even_count:
        block = colour
        offset = 2 * choice
    else:
        block = (colour - 1) % 3
        offset = 2 * (choice - even_count) + 1
    return _encode(factor, block * s + offset)


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly after enforcing shape, ranges, colours, and uniqueness."""
    return [
        [_sample_label_of_colour(factor, colour, rng) for colour in range(3)]
        for factor in inst["factors"]
    ]


def search_space(inst: dict) -> int | None:
    first, second = inst["factors"]
    return first["s"] ** 3 * second["s"] ** 3


def enumerate_all(inst: dict) -> int | None:
    """Brute-force the exact bounded language only when it is genuinely small."""
    size = search_space(inst)
    if size is None or size > 200_000:
        return None
    choices = []
    for factor in inst["factors"]:
        rows = [
            [label for label in range(factor["order"])
             if _factor_colour(factor, label) == colour]
            for colour in range(3)
        ]
        choices.append(rows)
    count = 0
    for a0 in choices[0][0]:
        for a1 in choices[0][1]:
            for a2 in choices[0][2]:
                for b0 in choices[1][0]:
                    for b1 in choices[1][1]:
                        for b2 in choices[1][2]:
                            count += int(verify(
                                inst, [[a0, a1, a2], [b0, b1, b2]])[0]
                            )
    return count


def canonical_key(inst: dict) -> str:
    """Canonical coloured-product key under factor swaps and vertex relabelling."""
    # Every decoder chain is a label bijection onto the same canonical coloured
    # cycle word for its s.  Thus the unordered pair of s values is a complete
    # invariant for the represented family, including the strong-product swap.
    sizes = sorted(factor["s"] for factor in inst["factors"])
    return json.dumps(["odd-phase-cycle-strong-product-v1", sizes],
                      separators=(",", ":"))


def escalate(params: dict) -> dict | str | None:
    """Grow both factor orders and decoder crowding at fixed witness length."""
    if len(DIFFICULTY) == 1:  # isolated G9 shipping-arm copy
        return None
    try:
        n = int(params["n"])
        spread = int(params.get("spread", 0))
        chain_len = int(params.get("chain_len", 8))
    except (KeyError, TypeError, ValueError):
        return None
    if chain_len >= 26:
        # The factor orders can continue growing indefinitely even after the
        # route reaches 278 operations, so this is not a cap or hardness end.
        return {"n": 3 * n, "spread": max(1, 2 * spread),
                "chain_len": chain_len}
    return {"n": 3 * n, "spread": max(1, 2 * spread),
            "chain_len": min(26, chain_len + 2)}


# ---------------------------------------------------------------------------
# Compact route, domain-standard reference scan, adversaries, and relabelling


def _inverse_affine(factor: dict) -> tuple[int, int, int]:
    """Return P,Q,operations with encode(t)=P*t+Q modulo order."""
    modulus = factor["order"]
    coefficient, constant = 1, 0
    operations = 0
    for _multiplier, shift, inverse in reversed(factor["stages"]):
        coefficient = (inverse * coefficient) % modulus
        constant = (inverse * (constant - shift)) % modulus
        operations += 5  # multiply/mod; subtract/multiply/mod
    return coefficient, constant, operations


def _compact_route(inst: dict) -> dict:
    start = time.perf_counter()
    answer = []
    operations = 0
    for factor in inst["factors"]:
        coefficient, constant, used = _inverse_affine(factor)
        operations += used
        row = []
        for colour in range(3):
            row.append((coefficient * (colour * factor["s"]) + constant)
                       % factor["order"])
            operations += 3  # multiply, add, remainder
        answer.append(row)
    ok, reason = verify(inst, answer)
    return {
        "answer": answer,
        "ok": ok,
        "reason": reason,
        "operations": operations,
        "wall_clock_sec": time.perf_counter() - start,
    }


def _reference_scan(inst: dict) -> dict:
    """Standard exact scan of closed neighbourhood colours in both factors."""
    start = time.perf_counter()
    counter = {"decoder_stages": 0, "local_colour_checks": 0,
               "labels_examined": 0}
    answer = []
    for factor in inst["factors"]:
        found: list[int | None] = [None, None, None]
        for label in range(factor["order"]):
            coordinate = _decode(factor, label, counter)
            counter["labels_examined"] += 1
            local = {
                _base_colour(factor, coordinate - 1),
                _base_colour(factor, coordinate),
                _base_colour(factor, coordinate + 1),
            }
            counter["local_colour_checks"] += 3
            if local == {0, 1, 2}:
                colour = _base_colour(factor, coordinate)
                counter["local_colour_checks"] += 1
                if found[colour] is None:
                    found[colour] = label
            if all(value is not None for value in found):
                break
        answer.append(found)
    ok = all(all(value is not None for value in row) for row in answer)
    reason = "missing a factor b-vertex"
    if ok:
        ok, reason = verify(inst, answer)
    operations = (counter["decoder_stages"]
                  + counter["local_colour_checks"])
    return {
        "answer": answer,
        "ok": ok,
        "reason": reason,
        "operations": operations,
        "decoder_stages": counter["decoder_stages"],
        "local_colour_checks": counter["local_colour_checks"],
        "labels_examined": counter["labels_examined"],
        "wall_clock_sec": time.perf_counter() - start,
    }


def _attack_first_labels(inst: dict) -> list[list[int]]:
    answer = []
    for factor in inst["factors"]:
        row = []
        for colour in range(3):
            for label in range(factor["order"]):
                if _factor_colour(factor, label) == colour:
                    row.append(label)
                    break
        answer.append(row)
    return answer


def _attack_degree_outlier(inst: dict) -> list[list[int]]:
    # Every factor vertex has degree two.  A degree-only tie break selects the
    # first legal label in each class.
    return _attack_first_labels(inst)


def _attack_random_restart(inst: dict, seed: int,
                           restarts: int = 256) -> list[list[int]]:
    rng = random.Random(seed ^ 0x160708453)
    last = _attack_first_labels(inst)
    for _ in range(restarts):
        last = random_candidate(inst, rng)
        if verify(inst, last)[0]:
            return last
    return last


def _attack_native_boundaries(inst: dict) -> list[list[int]]:
    # Obvious no-tool ansatz: forget the decoder and treat encoded labels as
    # native coordinates.  Reorder by actual colour so shape constraints hold.
    out = []
    for factor in inst["factors"]:
        candidates = [0, factor["s"], 2 * factor["s"]]
        row: list[int | None] = [None, None, None]
        for label in candidates:
            colour = _factor_colour(factor, label)
            if row[colour] is None:
                row[colour] = label
        # Fill missing colours by a tiny, in-context first-label scan.
        for colour in range(3):
            if row[colour] is None:
                for label in range(factor["order"]):
                    if _factor_colour(factor, label) == colour:
                        row[colour] = label
                        break
        out.append([int(value) for value in row])
    return out


def _attack_single_decoded_probe(inst: dict) -> list[list[int]]:
    # Inspect the decoded colour of label zero and extrapolate consecutive
    # labels, an affordable but invalid assumption after affine scrambling.
    out = []
    for factor in inst["factors"]:
        start = _factor_colour(factor, 0)
        guesses = [[0, 1, 2][(colour - start) % 3] for colour in range(3)]
        # Repair only the explicit colour/order constraint.
        row = []
        for colour, guess in enumerate(guesses):
            if _factor_colour(factor, guess) == colour:
                row.append(guess)
            else:
                row.append(next(label for label in range(factor["order"])
                                if _factor_colour(factor, label) == colour))
        out.append(row)
    return out


def _pick_relabel_unit(modulus: int, seed: int) -> int:
    rng = random.Random(seed)
    return _unit(modulus, rng)


def _relabel_factor(factor: dict, unit: int, shift: int) -> dict:
    """Represent y=unit*x+shift while preserving the decoded coloured cycle."""
    modulus = factor["order"]
    if math.gcd(unit, modulus) != 1:
        raise ValueError("relabel multiplier must be a unit")
    inverse = pow(unit, -1, modulus)
    prefix = [inverse, (-inverse * shift) % modulus, unit]
    return {
        "s": factor["s"],
        "order": modulus,
        "stages": [prefix] + [stage[:] for stage in factor["stages"]],
    }


def _relabel_instance(inst: dict, specifications: list[tuple[int, int]],
                      swap: bool = False) -> tuple[dict, list[list[int]]]:
    factors = []
    carried = []
    for factor, row, (unit, shift) in zip(
            inst["factors"], inst["answer"], specifications):
        factors.append(_relabel_factor(factor, unit, shift))
        carried.append([
            (unit * label + shift) % factor["order"] for label in row
        ])
    if swap:
        factors.reverse()
        carried.reverse()
    moved = {
        "paper": inst["paper"],
        "product": inst["product"],
        "number_of_product_colours": inst["number_of_product_colours"],
        "factors": factors,
        "answer": carried,
    }
    return moved, carried


# ---------------------------------------------------------------------------
# Mandatory gates


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest() -> dict:
    report: dict = {}

    # G1: every preset, multiple seeds, plus JSON-native answers.
    planted_attempts = 0
    planted_successes = 0
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 23):
            inst = make_instance(seed=seed, **params)
            planted_attempts += 1
            planted_successes += int(verify(inst, inst["answer"])[0])
            json_roundtrips += int(
                json.loads(json.dumps(inst["answer"])) == inst["answer"]
            )
    report["G1_planted_verifies"] = {
        "pass": (planted_successes == planted_attempts
                 and json_roundtrips == planted_attempts),
        "successes": planted_successes,
        "attempts": planted_attempts,
        "json_roundtrips": json_roundtrips,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=7, **shipping_params)

    # G2: mutations deliberately reach distinct validation branches.
    answer = inst["answer"]
    corruptions = {
        "empty": [],
        "drop": [answer[0][:-1], answer[1][:]],
        "swap": [[answer[0][1], answer[0][0], answer[0][2]], answer[1][:]],
        "duplicate": [[answer[0][0], answer[0][0], answer[0][2]], answer[1][:]],
        "out_of_range": [[inst["factors"][0]["order"], answer[0][1],
                          answer[0][2]], answer[1][:]],
    }
    rejected = {}
    for name, bad in corruptions.items():
        ok, reason = verify(inst, bad)
        rejected[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in rejected.values()]
    report["G2_rejects_corruption"] = {
        "pass": (all(entry["rejected"] for entry in rejected.values())
                 and len(set(reasons)) == len(reasons)),
        "cases": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "The phase changes give the following certificate.\n"
        "<answer>\n```json\n"
        + json.dumps(answer)
        + "\n```\n</answer>\nThis is my final result."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": (parsed == answer and verify(inst, parsed)[0]
                 and parse_answer("no tagged answer") is None
                 and parse_answer("<answer>not json</answer>") is None),
        "parsed_matches": parsed == answer,
        "garbage_returns_none": parse_answer("<answer>not json</answer>") is None,
    }

    # G4/G5 shipping density from the exact stated prior.
    samples = 200_000
    rng = random.Random(0x160708453)
    guess_start = time.perf_counter()
    hits = 0
    for _ in range(samples):
        hits += int(verify(inst, random_candidate(inst, rng))[0])
    guess_wall = time.perf_counter() - guess_start
    rate = hits / samples
    report["G4_guess_resistance"] = {
        "pass": rate < 1e-6,
        "hits": hits,
        "total": samples,
        "probability": rate,
        "candidate_space": search_space(inst),
        "prior": "uniform one label from each stated factor colour class",
        "wall_clock_sec": guess_wall,
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    baseline_start = time.perf_counter()
    baseline = _attack_random_restart(inst, 91, restarts=4096)
    baseline_wall = time.perf_counter() - baseline_start
    baseline_ok = verify(inst, baseline)[0]
    reference = _reference_scan(inst)
    report["G5_density_and_baseline"] = {
        "pass": (demo_count is not None and demo_count >= 1
                 and rate < 1e-6 and not baseline_ok and reference["ok"]),
        "shipping_valid_hits": hits,
        "shipping_density_samples": samples,
        "shipping_density_estimate": rate,
        "demo_exact_valid_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "baseline_random_restarts": 4096,
        "baseline_random_wall_sec": baseline_wall,
        "baseline_random_success": baseline_ok,
        "reference_scan_wall_sec": reference["wall_clock_sec"],
        "reference_scan_operations": reference["operations"],
        "reference_scan_labels_examined": reference["labels_examined"],
        "reference_scan_success": reference["ok"],
    }

    # Track B: four attacks that a no-tool solver can try must fail.  The
    # domain-standard scan succeeds and is reported separately.
    attack_names = {
        "outlier_degree_tie_break": lambda current, seed: _attack_degree_outlier(current),
        "greedy_first_label_per_colour": lambda current, seed: _attack_first_labels(current),
        "random_restart_256": lambda current, seed: _attack_random_restart(
            current, seed, 256),
        "encoded_boundary_ansatz": lambda current, seed: _attack_native_boundaries(current),
        "single_decoded_probe_extrapolation": lambda current, seed: (
            _attack_single_decoded_probe(current)),
    }
    attacks = {name: {"successes": 0, "attempts": 0}
               for name in attack_names}
    reference_successes = 0
    reference_operations = []
    reference_seconds = []
    for seed in range(100, 108):
        current = make_instance(seed=seed, **shipping_params)
        for name, attack in attack_names.items():
            attacks[name]["attempts"] += 1
            attacks[name]["successes"] += int(
                verify(current, attack(current, seed))[0]
            )
        scanned = _reference_scan(current)
        reference_successes += int(scanned["ok"])
        reference_operations.append(scanned["operations"])
        reference_seconds.append(scanned["wall_clock_sec"])
    all_failed = all(entry["successes"] == 0 for entry in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "exact closed-neighbourhood scan of both coloured factors",
            "complexity": "O((|V(A)|+|V(B)|)*chain_len) exact operations",
            "successes": reference_successes,
            "attempts": 8,
            "mean_wall_clock_sec": sum(reference_seconds) / len(reference_seconds),
            "max_wall_clock_sec": max(reference_seconds),
            "mean_operations": sum(reference_operations) / len(reference_operations),
            "max_operations": max(reference_operations),
        },
    }

    doubled = dict(shipping_params)
    doubled["n"] *= 2
    doubled_inst = make_instance(seed=314159, **doubled)
    harder = escalate(shipping_params)
    report["G7_scales"] = {
        "pass": (verify(doubled_inst, doubled_inst["answer"])[0]
                 and doubled_inst["factors"][0]["order"]
                 > inst["factors"][0]["order"]
                 and isinstance(harder, dict)
                 and harder["n"] > shipping_params["n"]
                 and harder["chain_len"] >= shipping_params["chain_len"]),
        "shipping_factor_orders": [f["order"] for f in inst["factors"]],
        "doubled_factor_orders": [f["order"] for f in doubled_inst["factors"]],
        "shipping_answer_elements": _answer_atoms(inst["answer"]),
        "doubled_answer_elements": _answer_atoms(doubled_inst["answer"]),
        "escalated_params": harder,
    }

    invariant_checks = 0
    carried_checks = 0
    unrelated_keys = []
    for seed in range(200, 220):
        current = make_instance(seed=seed, **shipping_params)
        unrelated_keys.append(canonical_key(current))
        specs = []
        for index, factor in enumerate(current["factors"]):
            unit = _pick_relabel_unit(factor["order"], seed * 17 + index)
            shift = (seed * 101 + index * 37) % factor["order"]
            specs.append((unit, shift))
        identity_specs = [(1, 0), (1, 0)]
        transforms = [
            [specs[0], identity_specs[1]],
            [identity_specs[0], specs[1]],
            specs,
        ]
        for transform in transforms:
            moved, carried = _relabel_instance(current, transform)
            invariant_checks += int(canonical_key(moved) == canonical_key(current))
            carried_checks += int(verify(moved, carried)[0])
        moved, carried = _relabel_instance(current, specs, swap=True)
        invariant_checks += int(canonical_key(moved) == canonical_key(current))
        carried_checks += int(verify(moved, carried)[0])
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": (invariant_checks == 80 and carried_checks == 80
                 and distinct == 20),
        "invariance_successes": invariant_checks,
        "invariance_attempts": 80,
        "carried_witness_successes": carried_checks,
        "carried_witness_attempts": 80,
        "unrelated_distinct_keys": distinct,
        "unrelated_attempts": 20,
        "symmetries_tested": [
            "affine relabelling of A",
            "affine relabelling of B",
            "composed relabelling of both factors",
            "both relabellings composed with factor swap",
        ],
    }

    compact = _compact_route(inst)
    compact_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(compact_blob)
    # Lexical token count is deterministic and conservative for this integer
    # matrix: count every integer and every punctuation character separately.
    answer_tokens = len(re.findall(r"\d+|[^\s\w]", compact_blob))
    answer_elements = _answer_atoms(inst["answer"])
    arms = {
        key: dict(G9_EVIDENCE.get(key, {"solved": 0, "attempts": 0}))
        for key in ("bare", "hinted", "placebo")
    }
    hinted_attempts = arms["hinted"].get("attempts", 0)
    placebo_attempts = arms["placebo"].get("attempts", 0)
    hinted_rate = (arms["hinted"].get("solved", 0) / hinted_attempts
                   if hinted_attempts else 0.0)
    placebo_rate = (arms["placebo"].get("solved", 0) / placebo_attempts
                    if placebo_attempts else 0.0)
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and compact["operations"] <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_EVIDENCE.get("hinted_verdict", "not_run"),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": compact["operations"],
        "intended_route_verified": compact["ok"],
        "intended_route_wall_sec": compact["wall_clock_sec"],
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping_params)
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
