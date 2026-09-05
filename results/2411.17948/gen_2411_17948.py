"""Verified Track-B Test Cover generator for arXiv:2411.17948.

The paper defines Test Cover on a finite set system: selected tests must give
different incidence signatures to every pair of items.  Here the items are all
vectors of F_2^d and a test is a parity functional.  Consequently a submitted
set of d tests is a test cover exactly when its d coefficient masks have full
rank over F_2.  The generator samples a full-rank cyclic orbit first and only
then surrounds it with same-weight decoys from a proper subspace.
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
try:  # Repository helpers are optional; integer bit arithmetic suffices here.
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - the module remains stdlib-only.
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "finite item set F_2^d",
        "parity-defined tests in a finite set system",
        "test cover",
        "marked cyclic order on item coordinates",
    ],
    "verification_operations": [
        "integer syntax and range checks",
        "exact Gaussian row reduction over F_2",
        "rank comparison",
        "test-signature injectivity via the kernel criterion",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "Find the coefficient masks forming one complete orbit under rotation "
        "of the displayed coordinate cycle; without that symmetry one must do "
        "row reduction across a long decoy list."
    ),
    "hardness_basis": (
        "Track B: incremental exact Gaussian elimination over F_2 solves this "
        "promised subclass in O(n*d^2) bit operations; at shipping n=120,d=19 "
        "it averaged 15,097 counted bit operations per instance (8/8 solved "
        "in 0.0062 seconds total), while the cyclic-orbit route uses at most "
        "267 exact mask operations once the symmetry is recognized."
    ),
    "max_answer_tokens": 19,
}

NATIVE: dict = {
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


DIFFICULTY: dict = {
    "demo": {"n": 9, "dimension": 7, "subspace_dimension": 4},
    "easy": {"n": 120, "dimension": 19, "subspace_dimension": 12},
    "medium": {"n": 128, "dimension": 19, "subspace_dimension": 12},
    "hard": {"n": 136, "dimension": 19, "subspace_dimension": 12},
}
SHIPPING_DIFFICULTY: str = "easy"


STRUCTURAL_HINT: str = (
    "The support masks contain a complete orbit under one-step rotation around "
    "the displayed coordinate cycle."
)
PLACEBO_HINT: str = (
    "The support masks reward careful attention to the displayed coordinate "
    "labels and output indexing."
)


CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON array of exactly d distinct 0-based test IDs chosen from n "
        "listed tests; order is immaterial and every d-subset is sampled "
        "uniformly by random_candidate."
    ),
    "bounds": {
        "answer_length": "dimension d",
        "test_ids": "integers 0 through n-1",
        "distinct": True,
        "order_matters": False,
        "candidate_count": "binomial(n,d)",
        "max_named_answer_length": 19,
    },
}


G9_ARM_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}
G9_HINTED_VERDICT = "blocked_by_openrouter_key_limit"


NOTES: str = r"""
Definition. Section 1 and Section 2 of arXiv:2411.17948 define Test Cover:
a selected collection of tests must contain exactly one member of every pair
of distinct items in at least one selected test. The present items are all
vectors x in F_2^d. A mask a defines the honest test {x : a dot x = 1}; two
items x,y receive equal signatures precisely when x-y is in the kernel of the
selected mask matrix. Thus the paper's definition is met exactly iff the masks
have rank d. No graph, SAT, or finite-field surrogate replaces the set system.

Step-0 hardness decision. Theorem 1 supplies a
2^{O(|U| log |U|)} polynomial-factor dynamic program for arbitrary Test Cover,
and Section 3 also records brute-force enumeration. In this parity subclass,
Gaussian elimination is even stronger and polynomial. Therefore Track A would
be false: the certificate is exactly what that algorithm outputs. Track B is
honest because the public list is long enough that elimination is mechanical,
whereas one collective symmetry identifies a full-rank orbit with a short
no-tool route. Theorem 3's subquadratic incompressibility is a worst-case
statement and is not misreported as average-case hardness for this generator.

Construction. A fixed-weight logical mask is sampled, and all of its cyclic
rotations are formed. A base is rejected before the instance exists unless the
orbit has rank d. These orbit tests are the answer sampled first. Decoys are
then sampled from the proper span of the first h orbit rows, conditioned to
have exactly the same support weight; immediate rotational neighbors are
excluded at named presets. Finally a random relabelling of coordinate names and
a random test ordering are applied, carrying the witness. All tests therefore
have the same cardinality 2^(d-1), the same displayed support size, and (over
the generator's random coordinate relabelling) the same one-test support
distribution. The planted/decoy distinction is collective rather than a
per-test magnitude or size marker.

Easy regimes. The paper states that Test Cover is FPT by solution size, gives
the |U|-parameter algorithm in Theorem 1, and notes Bondy's |U|-1 upper bound.
Our succinct parity representation exposes the still easier rank criterion.
Trees, bounded feedback-edge-set graphs, twin cover, distance to clique, and
neighbourhood diversity are Locating-Dominating Set regimes from Sections 3--4
and are not used here.

Attacks. Support-size outliers are neutralized exactly, and a coordinate-
frequency outlier score is measured. Greedy coordinate novelty, bounded random
restarts, and a single-anchor cyclic ansatz all fail on the measured panel. The
last is deliberately close to the intended symmetry
but commits to the first displayed decoy instead of locating the collective
orbit. Full Gaussian elimination is reported separately as the successful
Track-B reference algorithm.

Canonicalization. Tests may be reordered, and coordinate names may be
arbitrarily relabelled provided the marked coordinate order is carried with
them. canonical_key converts masks back to marked-cycle positions and sorts
them, so both symmetries disappear. It does not attempt abstract set-system
isomorphism after expanding all 2^d items; that limitation is documented in
README.md.
""".strip()


_ANSWER_RE = re.compile(
    r"<answer\b[^>]*>(.*?)</answer\s*>", re.IGNORECASE | re.DOTALL
)


def _rank(rows: list[int]) -> int:
    """Exact rank of binary row masks."""
    pivots: dict[int, int] = {}
    for value in rows:
        x = value
        while x:
            pivot = x.bit_length() - 1
            if pivot in pivots:
                x ^= pivots[pivot]
            else:
                pivots[pivot] = x
                break
    return len(pivots)


def _rotate(mask: int, dimension: int) -> int:
    full = (1 << dimension) - 1
    return ((mask << 1) & full) | (mask >> (dimension - 1))


def _unrotate(mask: int, dimension: int) -> int:
    return (mask >> 1) | ((mask & 1) << (dimension - 1))


def _orbit(mask: int, dimension: int) -> list[int]:
    rows = []
    value = mask
    for _ in range(dimension):
        rows.append(value)
        value = _rotate(value, dimension)
    return rows


def _support_weight(dimension: int) -> int:
    weight = dimension // 2
    if weight % 2 == 0:
        weight -= 1
    return max(1, weight)


def _random_fixed_weight_mask(
    dimension: int, weight: int, rng: random.Random
) -> int:
    result = 0
    for position in rng.sample(range(dimension), weight):
        result |= 1 << position
    return result


def _span_vector(basis: list[int], selector: int) -> int:
    result = 0
    index = 0
    while selector:
        if selector & 1:
            result ^= basis[index]
        selector >>= 1
        index += 1
    return result


def _logical_to_named(mask: int, coordinate_cycle: list[int]) -> int:
    named = 0
    for logical, name in enumerate(coordinate_cycle):
        if (mask >> logical) & 1:
            named |= 1 << name
    return named


def _named_to_logical(mask: int, coordinate_cycle: list[int]) -> int:
    logical = 0
    for position, name in enumerate(coordinate_cycle):
        if (mask >> name) & 1:
            logical |= 1 << position
    return logical


def _make_decoys(
    orbit: list[int], count: int, subspace_dimension: int, weight: int,
    rng: random.Random,
) -> list[int]:
    """Sample distinct same-weight rows from a planted proper subspace."""
    dimension = len(orbit)
    span_basis = orbit[:subspace_dimension]
    used = set(orbit)
    decoys: list[int] = []
    attempts = 0
    limit = max(20_000, count * 300)

    # At all named presets these exclusions make the planted orbit the only
    # collection closed under one-step rotation.  They are a collective rule:
    # every individual row still has exactly the same support weight.
    while len(decoys) < count and attempts < limit:
        attempts += 1
        selector = rng.randrange(1, 1 << subspace_dimension)
        value = _span_vector(span_basis, selector)
        if value in used or value.bit_count() != weight:
            continue
        if _rotate(value, dimension) in used or _unrotate(value, dimension) in used:
            continue
        used.add(value)
        decoys.append(value)

    if len(decoys) < count:
        # A size-doubled G7 probe can exhaust the no-neighbour packing even
        # though the subspace still contains enough distinct decoys.  Fill from
        # the same declared distribution; named/G9 presets never need this.
        selectors = list(range(1, 1 << subspace_dimension))
        rng.shuffle(selectors)
        for selector in selectors:
            value = _span_vector(span_basis, selector)
            if value in used or value.bit_count() != weight:
                continue
            used.add(value)
            decoys.append(value)
            if len(decoys) == count:
                break

    if len(decoys) != count:
        raise ValueError(
            "not enough distinct same-weight decoys; raise subspace_dimension"
        )
    return decoys


def make_instance(
    n: int,
    seed: int = 0,
    dimension: int = 19,
    subspace_dimension: int = 12,
    **params,
) -> dict:
    """Inverse-generate a parity Test Cover with a carried rank certificate.

    ``n`` is the number of available tests—the haystack—so increasing it at
    fixed ``dimension`` makes the problem harder without lengthening the answer.
    """
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    for name, value in (
        ("n", n), ("dimension", dimension),
        ("subspace_dimension", subspace_dimension),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer")
    if dimension < 3:
        raise ValueError("dimension must be at least 3")
    if not (1 <= subspace_dimension < dimension):
        raise ValueError("subspace_dimension must lie in [1, dimension-1]")
    if n < dimension + 2:
        raise ValueError("n must leave room for at least two decoy tests")
    if n > (1 << subspace_dimension) - 1:
        raise ValueError("n exceeds the available proper-subspace masks")

    rng = random.Random(seed)
    weight = _support_weight(dimension)

    # The planted answer is selected before any public decoy exists.  Rank is
    # checked only on this sampled construction, never searched for in the
    # completed public instance.
    for _ in range(10_000):
        base = _random_fixed_weight_mask(dimension, weight, rng)
        planted_rows = _orbit(base, dimension)
        if len(set(planted_rows)) == dimension and _rank(planted_rows) == dimension:
            break
    else:  # pragma: no cover - supported dimensions find one almost instantly.
        raise ValueError("could not construct a full-rank cyclic orbit")

    decoys = _make_decoys(
        planted_rows, n - dimension, subspace_dimension, weight, rng
    )

    # Random coordinate relabelling makes each fixed-weight individual mask
    # uniform over named supports.  The marked cycle carries the intended
    # collective relation through the relabelling.
    coordinate_cycle = list(range(dimension))
    rng.shuffle(coordinate_cycle)
    tagged = [
        (_logical_to_named(mask, coordinate_cycle), True)
        for mask in planted_rows
    ] + [
        (_logical_to_named(mask, coordinate_cycle), False)
        for mask in decoys
    ]
    rng.shuffle(tagged)

    # Keep test 0 as an ordinary decoy.  This removes a positional planting
    # shortcut and makes the deliberately weak single-anchor attack honest.
    if tagged[0][1]:
        swap_index = next(i for i, (_, planted) in enumerate(tagged) if not planted)
        tagged[0], tagged[swap_index] = tagged[swap_index], tagged[0]

    tests = [mask for mask, _ in tagged]
    answer = sorted(i for i, (_, planted) in enumerate(tagged) if planted)
    return {
        "family": "parity Test Cover on all binary items",
        "dimension": dimension,
        "item_count": 1 << dimension,
        "test_count": n,
        "solution_size": dimension,
        "support_weight": weight,
        "coordinate_cycle": coordinate_cycle,
        "test_masks": tests,
        "answer": answer,
    }


def _mask_support(mask: int, dimension: int) -> str:
    return "{" + ",".join(
        str(i) for i in range(dimension) if (mask >> i) & 1
    ) + "}"


def render(inst: dict) -> str:
    """Render the complete finite Test Cover problem."""
    d = inst["dimension"]
    n = inst["test_count"]
    tests = "\n".join(
        f"T{index}: {_mask_support(mask, d)}"
        for index, mask in enumerate(inst["test_masks"])
    )
    cycle = ", ".join(str(x) for x in inst["coordinate_cycle"])
    statement = f"""Parity Test Cover on a finite binary item set

The item set U consists of all {inst['item_count']} binary vectors
x=(x_0,...,x_{d - 1}) in {{0,1}}^{d}. Coordinate subscripts and test IDs are
0-based. The marked, oriented coordinate cycle (including its marked starting
position) is:

    ({cycle})

There are {n} tests. A displayed support A defines the set

    T_A = {{x in U : sum_(j in A) x_j is 1 modulo 2}}.

Thus every listed test is an actual subset of the finite item set U, described
exactly rather than by enumerating its {1 << (d - 1)} members. The tests are:

{tests}

A collection C of tests is a test cover if every two distinct items u,v in U
are separated: at least one selected test contains exactly one of u and v.
Equivalently, write each selected support as a length-{d} binary row; C is a
test cover exactly when those rows have rank {d} over F_2. This follows because
u and v have the same selected-test signature exactly when their nonzero XOR
u XOR v lies in the row matrix's kernel.

Find a test cover containing at most {d} tests. Since {d} binary answers cannot
give distinct signatures to {inst['item_count']} items with fewer than {d}
tests, your answer must contain exactly {d} distinct test IDs. Order does not
matter and repeated IDs are forbidden.

Give your final answer inside <answer></answer> tags, as one JSON array of
exactly {d} distinct integers from 0 through {n - 1}.
Example: <answer>{json.dumps(list(range(d)))}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Extract the final tagged JSON list, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```") and body.endswith("```"):
        body = re.sub(r"^```(?:json|text)?\s*", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\s*```$", "", body).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        # Be liberal with a common model response while keeping the advertised
        # JSON format unambiguous.
        if not re.fullmatch(r"\s*\d+(?:\s*,\s*\d+)*\s*", body):
            return None
        try:
            value = [int(part.strip()) for part in body.split(",")]
        except ValueError:
            return None
    if not isinstance(value, list):
        return None
    if any(isinstance(x, bool) or not isinstance(x, int) for x in value):
        return None
    return value


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any submitted Test Cover without consulting inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON array of test IDs"
    if not answer:
        return False, "answer is empty"
    d = inst["dimension"]
    n = inst["test_count"]
    if len(answer) != d:
        return False, f"wrong number of test IDs: expected {d}, got {len(answer)}"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return False, "every test ID must be an integer"
    if len(set(answer)) != len(answer):
        return False, "test IDs must be distinct"
    if any(x < 0 or x >= n for x in answer):
        return False, f"test ID out of range 0..{n - 1}"
    rank = _rank([inst["test_masks"][i] for i in answer])
    if rank != d:
        return False, f"selected support masks have rank {rank}, not {d}, over F_2"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniform d-subset: all immediately visible constraints are enforced."""
    return sorted(rng.sample(range(inst["test_count"]), inst["dimension"]))


def search_space(inst: dict) -> int:
    return math.comb(inst["test_count"], inst["dimension"])


def enumerate_all(inst: dict) -> int | None:
    """Count all covers exactly only when the bounded language is small."""
    total = search_space(inst)
    if total > 500_000:
        return None
    count = 0
    for candidate in itertools.combinations(
        range(inst["test_count"]), inst["dimension"]
    ):
        if _rank([inst["test_masks"][i] for i in candidate]) == inst["dimension"]:
            count += 1
    return count


def canonical_key(inst: dict) -> str:
    """Canonicalize test order and coordinate-name relabellings.

    The marked coordinate cycle provides a canonical coordinate position.  A
    relabelling carries that ordered cycle, so converting every mask to cycle
    positions erases coordinate names; sorting erases test IDs.
    """
    logical_masks = sorted(
        _named_to_logical(mask, inst["coordinate_cycle"])
        for mask in inst["test_masks"]
    )
    payload = {
        "dimension": inst["dimension"],
        "tests": logical_masks,
        "solution_size": inst["solution_size"],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow/tighten the haystack while keeping the 19-ID witness fixed."""
    p = {k: v for k, v in params.items() if k != "_preset"}
    n = int(p.get("n", 120))
    dimension = int(p.get("dimension", 19))
    subspace_dimension = int(p.get("subspace_dimension", 12))

    # Grow only while the complete orbit-index route remains below 300 exact
    # mask operations: build an index, probe each possible anchor, follow d.
    if dimension == 19 and n < 136:
        p["n"] = min(136, n + 8)
        return p
    # A smaller decoy span makes still fewer d-subsets full-rank, at fixed
    # answer length and fixed rendered size.
    if dimension == 19 and subspace_dimension > 10:
        p["subspace_dimension"] = subspace_dimension - 1
        return p
    return "cap_bound"


def _reference_gaussian(inst: dict) -> tuple[list[int] | None, int]:
    """Incremental Gaussian basis and a conservative bit-operation count."""
    d = inst["dimension"]
    pivots: dict[int, tuple[int, int]] = {}
    selected: list[int] = []
    operations = 0
    for test_id, row in enumerate(inst["test_masks"]):
        value = row
        for pivot in sorted(pivots, reverse=True):
            operations += 1  # exact pivot-bit inspection
            if (value >> pivot) & 1:
                value ^= pivots[pivot][0]
                operations += d  # d exact bit XORs
        if value:
            pivot = value.bit_length() - 1
            operations += d  # exact pivot search, conservatively charged
            pivots[pivot] = (value, test_id)
            selected.append(test_id)
            if len(selected) == d:
                return sorted(selected), operations
    return None, operations


def _compact_orbit_route(inst: dict) -> tuple[list[int] | None, int]:
    """Execute the intended symmetry route and count exact mask operations."""
    d = inst["dimension"]
    cycle = inst["coordinate_cycle"]
    logical = [_named_to_logical(row, cycle) for row in inst["test_masks"]]
    operations = len(logical)  # construct the exact mask -> test-ID index
    by_mask = {mask: test_id for test_id, mask in enumerate(logical)}
    anchor = None
    for mask in logical:
        operations += 1  # one rotate-and-membership probe
        if _rotate(mask, d) in by_mask:
            anchor = mask
            break
    if anchor is None:
        return None, operations
    selected = []
    value = anchor
    for _ in range(d):
        operations += 1  # exact indexed lookup
        test_id = by_mask.get(value)
        if test_id is None:
            return None, operations
        selected.append(test_id)
        value = _rotate(value, d)
    return sorted(selected), operations


def _attack_outlier_coordinate_frequency(
    inst: dict, rng: random.Random
) -> list[int]:
    del rng
    d = inst["dimension"]
    rows = inst["test_masks"]
    frequencies = [sum((row >> bit) & 1 for row in rows) for bit in range(d)]
    # A planted orbit is collectively balanced.  This construction-aware probe
    # asks whether its individual rows can be recovered by favoring supports on
    # globally rare coordinates.  Every row already has equal support size.
    scores = [
        sum(frequencies[bit] for bit in range(d) if (row >> bit) & 1)
        for row in rows
    ]
    return sorted(
        sorted(range(inst["test_count"]), key=lambda i: (scores[i], i))[:d]
    )


def _attack_greedy_coordinate_novelty(
    inst: dict, rng: random.Random
) -> list[int]:
    del rng
    d = inst["dimension"]
    chosen: list[int] = []
    unseen = (1 << d) - 1
    remaining = set(range(inst["test_count"]))
    while len(chosen) < d:
        pick = min(
            remaining,
            key=lambda i: (-((inst["test_masks"][i] & unseen).bit_count()), i),
        )
        chosen.append(pick)
        remaining.remove(pick)
        unseen &= ~inst["test_masks"][pick]
    return sorted(chosen)


def _attack_random_restart(
    inst: dict, rng: random.Random, restarts: int = 256
) -> list[int]:
    last = []
    for _ in range(restarts):
        last = random_candidate(inst, rng)
        if verify(inst, last)[0]:
            return last
    return last


def _attack_single_anchor_orbit(
    inst: dict, rng: random.Random
) -> list[int]:
    del rng
    d = inst["dimension"]
    cycle = inst["coordinate_cycle"]
    logical = [_named_to_logical(x, cycle) for x in inst["test_masks"]]
    by_mask = {mask: i for i, mask in enumerate(logical)}
    value = logical[0]  # make_instance deliberately makes test 0 a decoy.
    chosen: list[int] = []
    for _ in range(d):
        if value not in by_mask:
            break
        chosen.append(by_mask[value])
        value = _rotate(value, d)
    for test_id in range(inst["test_count"]):
        if len(chosen) == d:
            break
        if test_id not in chosen:
            chosen.append(test_id)
    return sorted(chosen)


def _reorder_tests(
    inst: dict, permutation: list[int]
) -> tuple[dict, list[int]]:
    """Return a test reorder and the answer carried to new IDs."""
    if sorted(permutation) != list(range(inst["test_count"])):
        raise ValueError("not a test permutation")
    transformed = dict(inst)
    transformed["test_masks"] = [inst["test_masks"][old] for old in permutation]
    inverse = {old: new for new, old in enumerate(permutation)}
    carried = sorted(inverse[old] for old in inst["answer"])
    transformed["answer"] = carried
    return transformed, carried


def _relabel_coordinates(inst: dict, relabel: list[int]) -> dict:
    """Relabel coordinate names and carry the marked order."""
    d = inst["dimension"]
    if sorted(relabel) != list(range(d)):
        raise ValueError("not a coordinate permutation")

    def move(mask: int) -> int:
        out = 0
        for old in range(d):
            if (mask >> old) & 1:
                out |= 1 << relabel[old]
        return out

    transformed = dict(inst)
    transformed["test_masks"] = [move(mask) for mask in inst["test_masks"]]
    transformed["coordinate_cycle"] = [
        relabel[old] for old in inst["coordinate_cycle"]
    ]
    transformed["answer"] = list(inst["answer"])
    return transformed


def _answer_atoms(answer: object) -> int:
    if isinstance(answer, dict):
        return sum(_answer_atoms(v) for v in answer.values())
    if isinstance(answer, (list, tuple)):
        return sum(_answer_atoms(v) for v in answer)
    return 1


def selftest() -> dict:
    """Run all mandatory gates and return their measured evidence."""
    report: dict = {"track": TRACK}

    # G1: every named preset, several unrelated seeds.
    g1_failures = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            g1_attempts += 1
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
            if make_instance(seed=seed, **params) != inst:
                g1_failures.append(
                    {"preset": preset, "seed": seed, "reason": "nondeterministic"}
                )
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(
                    {"preset": preset, "seed": seed, "reason": "answer not JSON-native"}
                )
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=123, **shipping_params)
    answer = list(inst["answer"])

    # G2: five semantically different corruptions and five diagnostic reasons.
    nonanswer = [i for i in range(inst["test_count"]) if i not in set(answer)]
    replacement = None
    for drop_pos in range(len(answer)):
        for candidate in nonanswer:
            trial = list(answer)
            trial[drop_pos] = candidate
            if not verify(inst, trial)[0]:
                replacement = trial
                break
        if replacement is not None:
            break
    if replacement is None:
        replacement = list(answer)
        replacement[0] = nonanswer[0]
    corruptions = {
        "drop": answer[:-1],
        "swap": replacement,
        "duplicate": [answer[0], answer[0]] + answer[2:],
        "empty": [],
        "out_of_range": answer[:-1] + [inst["test_count"]],
    }
    g2_cases = {}
    for name, bad in corruptions.items():
        accepted, reason = verify(inst, bad)
        g2_cases[name] = {"accepted": accepted, "reason": reason}
    reasons = {entry["reason"] for entry in g2_cases.values()}
    report["G2_rejects_corruption"] = {
        "pass": (
            all(not entry["accepted"] for entry in g2_cases.values())
            and len(reasons) == len(g2_cases)
        ),
        "distinct_reasons": len(reasons),
        "cases": g2_cases,
    }

    # G3: model-like prose, a markdown fence, and the exact JSON wire format.
    wrapped = (
        "I used the parity signatures.\n<answer>```json\n"
        + json.dumps(answer)
        + "\n```</answer>\nThe array is 0-based."
    )
    parsed = parse_answer(wrapped)
    garbage_is_none = parse_answer("There is no tagged answer here.") is None
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0] and garbage_is_none,
        "parsed_matches": parsed == answer,
        "realistic_wrapper": True,
        "garbage_returns_none": garbage_is_none,
    }

    # G4/G5 density: one shipping population and structure-aware prior.
    guess_rng = random.Random(0x241117948)
    guess_total = 200_000
    guess_hits = 0
    t0 = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(inst, guess_rng)
        if verify(inst, candidate)[0]:
            guess_hits += 1
    guess_elapsed = time.perf_counter() - t0
    observed = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": observed < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_fraction": observed,
        "candidate_space": search_space(inst),
        "sampling_prior": (
            "uniform over all d-subsets of listed tests; exact answer length, "
            "distinctness, range, and order-indifference are already enforced"
        ),
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    # G6 panel: four failures plus the successful Track-B reference algorithm.
    attacks = {
        "outlier_coordinate_frequency": _attack_outlier_coordinate_frequency,
        "greedy_coordinate_novelty": _attack_greedy_coordinate_novelty,
        "random_restart_256": _attack_random_restart,
        "single_anchor_cycle_orbit": _attack_single_anchor_orbit,
    }
    attack_results = {
        name: {"successes": 0, "attempts": 0, "steps": 0, "wall_clock_sec": 0.0}
        for name in attacks
    }
    reference_successes = 0
    reference_operations = 0
    reference_start = time.perf_counter()
    panel_instances = []
    for seed in range(800, 808):
        panel_inst = make_instance(seed=seed, **shipping_params)
        panel_instances.append(panel_inst)
        candidate, operations = _reference_gaussian(panel_inst)
        reference_operations += operations
        if candidate is not None and verify(panel_inst, candidate)[0]:
            reference_successes += 1
    reference_elapsed = time.perf_counter() - reference_start

    for attack_index, (name, attack) in enumerate(attacks.items()):
        start = time.perf_counter()
        for offset, panel_inst in enumerate(panel_instances):
            rng = random.Random(10_000 * attack_index + offset)
            candidate = attack(panel_inst, rng)
            attack_results[name]["attempts"] += 1
            if name == "random_restart_256":
                attack_results[name]["steps"] += 256
            elif name == "single_anchor_cycle_orbit":
                attack_results[name]["steps"] += panel_inst["dimension"]
            else:
                attack_results[name]["steps"] += panel_inst["dimension"]
            if verify(panel_inst, candidate)[0]:
                attack_results[name]["successes"] += 1
        attack_results[name]["wall_clock_sec"] = round(
            time.perf_counter() - start, 6
        )

    all_attacks_failed = all(
        result["successes"] == 0 and result["attempts"] >= 8
        for result in attack_results.values()
    )
    reference = {
        "name": "incremental Gaussian elimination over F_2",
        "complexity": "O(n*d^2) exact bit operations",
        "operations": reference_operations,
        "average_operations_per_instance": reference_operations // 8,
        "wall_clock_sec": round(reference_elapsed, 6),
        "solves": f"{reference_successes}/8, as expected",
    }
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": reference,
    }

    demo_inst = make_instance(seed=5, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)
    strongest = attack_results["random_restart_256"]
    report["G5_density_and_baseline"] = {
        "pass": (
            observed < 1e-6
            and demo_count is not None
            and reference_successes == 8
        ),
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_sampled_valid_total": guess_total,
        "shipping_sampled_density": observed,
        "shipping_candidate_space": search_space(inst),
        "demo_n": demo_inst["test_count"],
        "demo_exact_solution_count": demo_count,
        "strongest_failing_attack": "random_restart_256",
        "strongest_failing_attack_steps": strongest["steps"],
        "strongest_failing_attack_wall_clock_sec": strongest["wall_clock_sec"],
        "reference_algorithm_operations": reference_operations,
        "reference_algorithm_wall_clock_sec": round(reference_elapsed, 6),
    }

    # G7: named ladder, doubled haystack, and a tighter span at fixed answer.
    preset_spaces = {}
    preset_ok = True
    for preset, params in DIFFICULTY.items():
        probe = make_instance(seed=17, **params)
        preset_spaces[preset] = search_space(probe)
        preset_ok = preset_ok and verify(probe, probe["answer"])[0]
    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=77, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    tightened_params = dict(shipping_params)
    tightened_params["subspace_dimension"] -= 1
    tightened = make_instance(seed=78, **tightened_params)
    tightened_ok, tightened_reason = verify(tightened, tightened["answer"])
    ordered_spaces = [preset_spaces[name] for name in DIFFICULTY]
    report["G7_scales"] = {
        "pass": (
            preset_ok
            and doubled_ok
            and tightened_ok
            and all(a < b for a, b in zip(ordered_spaces, ordered_spaces[1:]))
        ),
        "preset_candidate_spaces": preset_spaces,
        "doubled_n": doubled_params["n"],
        "doubled_candidate_space": search_space(doubled),
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
        "fixed_answer_axis": tightened_params,
        "fixed_answer_verifies": tightened_ok,
        "fixed_answer_reason": tightened_reason,
    }

    # G8: test reorder, coordinate relabel, and their composition over 20 seeds.
    invariance_checks = 0
    carried_checks = 0
    invariance_failures = []
    unrelated_keys = []
    for seed in range(20):
        base_inst = make_instance(seed=20_000 + seed, **shipping_params)
        base_key = canonical_key(base_inst)
        unrelated_keys.append(base_key)
        rng = random.Random(30_000 + seed)

        test_perm = list(range(base_inst["test_count"]))
        rng.shuffle(test_perm)
        reordered, carried = _reorder_tests(base_inst, test_perm)

        coord_perm = list(range(base_inst["dimension"]))
        rng.shuffle(coord_perm)
        relabelled = _relabel_coordinates(base_inst, coord_perm)
        composed = _relabel_coordinates(reordered, coord_perm)

        for label, transformed, transformed_answer in (
            ("test reorder", reordered, carried),
            ("coordinate relabelling", relabelled, base_inst["answer"]),
            ("composition", composed, carried),
        ):
            invariance_checks += 1
            if canonical_key(transformed) != base_key:
                invariance_failures.append({"seed": seed, "transform": label})
            carried_checks += 1
            if not verify(transformed, transformed_answer)[0]:
                invariance_failures.append(
                    {"seed": seed, "transform": label + " witness"}
                )
    report["G8_canonical_key"] = {
        "pass": not invariance_failures and len(set(unrelated_keys)) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "distinct_keys": len(set(unrelated_keys)),
        "invariance_failures": invariance_failures,
        "transformations": [
            "arbitrary test reorder",
            "arbitrary coordinate-name relabelling carrying the marked order",
            "composition of both",
        ],
    }

    # G9(a,b) are diagnostic; only exact size/effort caps gate.
    blob = json.dumps(inst["answer"])
    answer_chars = len(blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(inst["answer"])
    intended_ops = 2 * inst["test_count"] + inst["dimension"] + 8
    compact_answer, compact_operations = _compact_orbit_route(inst)
    compact_ok = (
        compact_answer is not None and verify(inst, compact_answer)[0]
    )
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_ops <= 300
    )
    arms = {name: dict(value) for name, value in G9_ARM_RESULTS.items()}
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = arms["hinted"]["solved"] / hinted_attempts if hinted_attempts else 0.0
    placebo_rate = (
        arms["placebo"]["solved"] / placebo_attempts if placebo_attempts else 0.0
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps and compact_ok and compact_operations <= intended_ops,
        "within_caps": within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_attempts and placebo_attempts
            else None
        ),
        "hinted_verdict": G9_HINTED_VERDICT,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "compact_route_measured_operations": compact_operations,
        "compact_route_verifies": compact_ok,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    gate_values = [
        value for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    ]
    report["all_passed"] = all(value.get("pass") for value in gate_values)
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping_params)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
