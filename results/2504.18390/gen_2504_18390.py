"""Verified Track-B generator from arXiv:2504.18390.

The paper prints base difference families for point-transitive and
1-rotational unitals of order 5. This module uses the first Z_125 family in
Example 2.1. It hides affine images of its four finite base blocks among
exchangeable affine-image candidates. A witness is the base difference
family itself, not a graph surrogate and not the expanded 525-block design.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import re
import sys
import time


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "exact_cover",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "base blocks in the cyclic group Z_125",
        "1-rotational S(2,6,126) difference family",
        "affine images of six-point blocks",
    ],
    "verification_operations": [
        "exact subtraction modulo 125",
        "directed-difference multiset comparison",
        "candidate-block membership",
        "exact set cardinality comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Centered second and fourth moments transform covariantly under the "
        "shared affine multiplier, replacing row-constrained exact cover by "
        "a short modular-invariant match."
    ),
    "hardness_basis": (
        "Track B: row-constrained Algorithm X solves the family in worst-case "
        "O(p*n^4) mask trials after O(p*n) block preprocessing; at the hard "
        "preset (n=18, p=2) the local reference implementation averaged "
        "4,754 exact difference/mask operations and 0.000459 seconds over eight "
        "seeds, while "
        "the centered-moment route uses at most 98 exact modular operations."
    ),
    "max_answer_tokens": 44,
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
    "demo": {"n": 2, "panels": 1},
    "easy": {"n": 10, "panels": 2},
    "medium": {"n": 14, "panels": 2},
    "hard": {"n": 18, "panels": 2},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The centered second and fourth moments of a block scale by the second "
    "and fourth powers of its affine multiplier."
)
PLACEBO_HINT = (
    "The modular conventions and the row boundaries deserve careful attention "
    "throughout this block-selection problem."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON outer array with one entry per panel; every panel entry has "
        "exactly four six-point blocks, choosing one advertised block from "
        "each row in row order. Points are distinct integers in 0..124 and "
        "order inside a block is ignored."
    ),
    "bounds": {
        "blocks_per_panel": 4,
        "points_per_block": 6,
        "point_min": 0,
        "point_max": 124,
        "choices_per_row": "n",
        "max_choices_per_row": 25,
        "max_panels": 10,
    },
}

G9_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}

NOTES = r"""
Paper grounding. Section 1 identifies an order-5 unital with S(2,6,126),
distinguishes point-transitive actions from order-125 actions with one fixed
point, and specifies left group development. Section 2 lists 1-rotational
designs as fingerprint--difference-family pairs. This module starts with the
first Z_125 family in Example 2.1. Its four finite blocks have 120 distinct
directed differences, exactly the nonzero residues other than 25,50,75,100;
the displayed infinity block {0,25,50,75,100,infinity} supplies the remaining
short orbit. Developing the five blocks gives 525 blocks and covers all 7,875
point-pairs exactly once.

STEP 0 and track choice. The paper is a fixed-order catalogue: it states no
hardness theorem or scalable enumeration algorithm, and direct table lookup
would fail Track A. This generator therefore makes the efficient solver
explicit and claims only Track B. The standard mechanical route forms the 30
directed differences of every advertised block and runs row-constrained exact
cover. Its operation count and wall time are measured at the shipping preset.
The compact route uses redundant exact central moments printed beside each
candidate. For S={u*x+t:x in B}, C_2(S)=u^2 C_2(B) and
C_4(S)=u^4 C_4(B) modulo 125. Rows C and D have invertible C_2 values 48 and
97, so their unique common normalized square q=u^2 is found by scanning them.
Then q and q^2 predict both printed moments in rows A and B. This costs at
most (2n+5) operations per panel plus 16 operations for the two fixed modular
inverses, and never requires expanding the 525-block design.

Construction. The paper's four finite blocks are fixed below. For each panel,
the generator samples the common square class and a global unit first. Each
row is filled with affine images of its corresponding paper block. Rows A/B
and C/D each share only the planted square class; all translations, candidate
orders, and row/panel presentations are randomized afterward. The correct
four blocks are therefore known before the instance exists. Every individual
plant and decoy has the same marginal distribution: a uniform unit multiplier
and uniform translation applied to the same row template. This is a
transformation of a known instance, not a solution obtained by search.

Easy regimes and attacks. One or a few choices per row are hand-scale; direct
catalogue lookup is also easy if the paper is available. The attack panel tests
per-block magnitude outliers, a low-overlap greedy rule, random restart, and
the obvious but wrong equality of raw displayed moments. The successful exact
cover implementation is kept outside attacks as Track B requires. Difficulty
grows by adding exchangeable choices while the 48-atom two-panel answer stays
fixed; after the largest 25-choice paired pools are reached, escalation adds
independent panels until the intended-route operation cap binds.

Canonicalization. Translating any base block independently, multiplying every
block in a panel by a unit, reordering candidates/rows/panels, and reordering
points inside a block preserve the problem. canonical_key discards independent
translations through directed differences, minimizes each panel over all 100
unit multipliers, and sorts all remaining unordered structures. It is a strong
invariant for the generated equivalences, not a complete isomorphism test for
arbitrary cyclic designs.
""".strip()


_MOD = 125
_INV6 = 21
_BASE = (
    (0, 1, 3, 15, 47, 74),
    (0, 4, 9, 20, 65, 103),
    (0, 6, 40, 88, 95, 112),
    (0, 8, 18, 41, 76, 104),
)
_ROW_NAMES = ("A", "B", "C", "D")
_UNITS = tuple(x for x in range(_MOD) if math.gcd(x, _MOD) == 1)
_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _central_moment(block, degree):
    mean = sum(block) * _INV6 % _MOD
    return sum(pow((x - mean) % _MOD, degree, _MOD) for x in block) % _MOD


_CALIBRATION = tuple(
    (_central_moment(block, 2), _central_moment(block, 4)) for block in _BASE
)


def _square_representatives():
    reps = []
    seen = set()
    for unit in _UNITS:
        square = unit * unit % _MOD
        if square not in seen:
            seen.add(square)
            reps.append(unit)
    if len(reps) != 50:
        raise AssertionError("Z_125 should have 50 unit square classes modulo sign")
    return tuple(reps)


_SQUARE_REPS = _square_representatives()


def _paired_class_sets(n, planted_class, rng):
    """Two n-sets whose only common class is the planted class."""
    others = [q for q in range(50) if q != planted_class]
    first_extra = set(rng.sample(others, n - 1))
    remaining = [q for q in others if q not in first_extra]
    second_extra = set(rng.sample(remaining, n - 1))
    first = list(first_extra | {planted_class})
    second = list(second_extra | {planted_class})
    rng.shuffle(first)
    rng.shuffle(second)
    return first, second


def make_instance(n, seed=0, panels=2, **params):
    """Plant affine copies of a paper-listed difference family, then add peers."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or not 2 <= n <= 25:
        raise ValueError("n must be an integer from 2 through 25")
    if isinstance(panels, bool) or not isinstance(panels, int) or not 1 <= panels <= 10:
        raise ValueError("panels must be an integer from 1 through 10")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    public_panels = []
    answer = []
    for _ in range(panels):
        planted_class = rng.randrange(50)
        global_unit = rng.choice(_UNITS)
        classes_a, classes_b = _paired_class_sets(n, planted_class, rng)
        classes_c, classes_d = _paired_class_sets(n, planted_class, rng)
        row_classes = (classes_a, classes_b, classes_c, classes_d)

        rows = []
        planted_blocks = []
        for row_index, (template, classes) in enumerate(zip(_BASE, row_classes)):
            candidates = []
            planted_block = None
            for class_index in classes:
                multiplier = global_unit * _SQUARE_REPS[class_index] % _MOD
                translation = rng.randrange(_MOD)
                block = sorted(
                    (multiplier * point + translation) % _MOD for point in template
                )
                candidate = {
                    "block": block,
                    "m2": _central_moment(block, 2),
                    "m4": _central_moment(block, 4),
                }
                candidates.append(candidate)
                if class_index == planted_class:
                    planted_block = list(block)
            rng.shuffle(candidates)
            if planted_block is None:
                raise AssertionError("planted square class disappeared")
            rows.append(
                {
                    "name": _ROW_NAMES[row_index],
                    "template": list(template),
                    "template_m2": _CALIBRATION[row_index][0],
                    "template_m4": _CALIBRATION[row_index][1],
                    "candidates": candidates,
                }
            )
            planted_blocks.append(planted_block)
        public_panels.append({"rows": rows})
        answer.append(planted_blocks)

    return {
        "family": "cyclic 1-rotational unital base-family selection",
        "modulus": _MOD,
        "n": n,
        "panel_count": panels,
        "fixed_infinity_block": [0, 25, 50, 75, 100, "infinity"],
        "panels": public_panels,
        "answer": answer,
    }


def render(inst):
    """Render a self-contained cyclic difference-family witness problem."""
    lines = [
        "CYCLIC 1-ROTATIONAL UNITAL BASE-FAMILY SELECTION",
        "",
        "All finite point labels are residues in Z_125, with addition modulo 125.",
        "There is also one fixed point called infinity. A block is an unordered",
        "set of six distinct finite residues. For each panel, choose exactly one",
        "advertised block from each displayed row, in displayed row order.",
        "",
        "For a chosen finite block B, its development is all translates",
        "B+t={x+t mod 125:x in B}. The fifth base block is fixed as",
        "{0,25,50,75,100,infinity}, together with all of its translates.",
        "Your four choices are valid exactly when their 120 directed differences",
        "x-y mod 125 (over all ordered distinct x,y in each chosen block) are",
        "each of the residues 1,...,124 except 25,50,75,100 exactly once.",
        "Equivalently, the five developed base blocks form an S(2,6,126): every",
        "unordered pair of the 126 points occurs in exactly one developed block.",
        "",
        "Candidate promise and redundant checksums: every candidate in a row is",
        "an affine image {u*x+t mod 125:x in T} of that row's displayed template",
        "T, where gcd(u,125)=1. For a block S define mean(S)=21*sum(S) mod 125",
        "and C_k(S)=sum((x-mean(S))^k for x in S) mod 125. Each line gives the",
        "exact C_2 and C_4 values; they are redundant and can be recomputed.",
        "Order of candidates and order of residues inside a submitted block do",
        "not matter. Repeated blocks within a panel are not allowed by the rows.",
    ]
    for panel_index, panel in enumerate(inst["panels"], 1):
        lines.extend(["", f"PANEL {panel_index}"])
        for row in panel["rows"]:
            lines.append(
                f"ROW {row['name']} template={row['template']} "
                f"C2(T)={row['template_m2']} C4(T)={row['template_m4']}"
            )
            for candidate_index, candidate in enumerate(row["candidates"], 1):
                compact = ",".join(map(str, candidate["block"]))
                lines.append(
                    f"  {candidate_index}: [{compact}] "
                    f"C2={candidate['m2']} C4={candidate['m4']}"
                )
    lines.extend(
        [
            "",
            "Output one JSON outer array. Its entries correspond to panels in the",
            "displayed order. Each panel entry must be an array of exactly four",
            "chosen six-integer blocks in displayed row order. Use integers 0..124;",
            "do not output candidate numbers or the fixed infinity block.",
            "Give your final answer inside <answer></answer> tags, as that JSON array.",
            "Example: <answer>[[[0,1,2,3,4,5],[6,7,8,9,10,11],"
            "[12,13,14,15,16,17],[18,19,20,21,22,23]]]</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    statement = "\n".join(lines)
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def _answer_shape(value):
    if not isinstance(value, list):
        return False
    for panel in value:
        if not isinstance(panel, list):
            return False
        for block in panel:
            if not isinstance(block, list):
                return False
            if any(isinstance(x, bool) or not isinstance(x, int) for x in block):
                return False
    return True


def parse_answer(text):
    """Extract nested JSON from prose, tags, or a Markdown fence; never raise."""
    if not isinstance(text, str):
        return None
    bodies = list(reversed(_ANSWER_RE.findall(text)))
    bodies.extend(
        reversed(re.findall(r"```(?:json)?\s*(.*?)\s*```", text, re.I | re.S))
    )
    decoder = json.JSONDecoder()
    for body in bodies:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", body.strip(), flags=re.I)
        try:
            value = json.loads(cleaned)
        except (TypeError, ValueError):
            continue
        if _answer_shape(value):
            return value
    for start, char in enumerate(text):
        if char != "[":
            continue
        try:
            value, _ = decoder.raw_decode(text[start:])
        except (TypeError, ValueError):
            continue
        if _answer_shape(value):
            return value
    return None


def _normal_block(raw, panel_index, row_name):
    where = f"panel {panel_index} row {row_name}"
    if not isinstance(raw, (list, tuple)):
        return None, f"{where} block must be an array"
    if len(raw) != 6:
        return None, f"{where} block must contain exactly 6 points"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in raw):
        return None, f"{where} block contains a non-integer point"
    if any(x < 0 or x >= _MOD for x in raw):
        return None, f"{where} block contains a point outside 0..124"
    if len(set(raw)) != 6:
        return None, f"{where} block repeats a point"
    return tuple(sorted(raw)), None


def _difference_tuple(block):
    return tuple(sorted((x - y) % _MOD for x in block for y in block if x != y))


def _difference_mask(block):
    mask = 0
    for difference in _difference_tuple(block):
        mask |= 1 << difference
    return mask


_TARGET_DIFFERENCES = frozenset(
    difference for difference in range(1, _MOD) if difference % 25
)
_TARGET_MASK = sum(1 << difference for difference in _TARGET_DIFFERENCES)


def verify(inst, answer):
    """Check any advertised difference family without reading inst['answer']."""
    if not isinstance(answer, (list, tuple)):
        return False, "answer must be an outer array of panels"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) != inst["panel_count"]:
        return False, (
            f"wrong number of panels: expected {inst['panel_count']}, got {len(answer)}"
        )
    for panel_index, (submitted, panel) in enumerate(zip(answer, inst["panels"])):
        if not isinstance(submitted, (list, tuple)):
            return False, f"panel {panel_index} must be an array of four blocks"
        if len(submitted) != 4:
            return False, (
                f"panel {panel_index} has wrong number of blocks: expected 4, "
                f"got {len(submitted)}"
            )
        chosen = []
        row_sets = [
            {tuple(candidate["block"]) for candidate in row["candidates"]}
            for row in panel["rows"]
        ]
        for row_index, raw in enumerate(submitted):
            row_name = panel["rows"][row_index]["name"]
            block, reason = _normal_block(raw, panel_index, row_name)
            if reason:
                return False, reason
            if block not in row_sets[row_index]:
                other = next(
                    (j for j, candidates in enumerate(row_sets) if block in candidates),
                    None,
                )
                if other is not None:
                    return False, (
                        f"panel {panel_index} row assignment mismatch: a row "
                        f"{panel['rows'][other]['name']} block was placed in row {row_name}"
                    )
                return False, (
                    f"panel {panel_index} row {row_name} block is not "
                    "an advertised candidate"
                )
            chosen.append(block)

        seen = set()
        for row_index, block in enumerate(chosen):
            for difference in _difference_tuple(block):
                if difference % 25 == 0:
                    return False, (
                        f"panel {panel_index} row {panel['rows'][row_index]['name']} "
                        "has forbidden "
                        f"subgroup difference {difference}"
                    )
                if difference in seen:
                    return False, (
                        f"panel {panel_index} directed difference {difference} occurs "
                        "more than once"
                    )
                seen.add(difference)
        if seen != _TARGET_DIFFERENCES:
            missing = min(_TARGET_DIFFERENCES - seen)
            return False, f"panel {panel_index} is missing directed difference {missing}"
    return True, "ok"


def random_candidate(inst, rng):
    """Choose one already-well-formed advertised block uniformly from every row."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    return [
        [list(rng.choice(row["candidates"])["block"]) for row in panel["rows"]]
        for panel in inst["panels"]
    ]


def search_space(inst):
    return inst["n"] ** (4 * inst["panel_count"])


def _panel_rows_with_masks(panel):
    return [
        [(candidate, _difference_mask(candidate["block"])) for candidate in row["candidates"]]
        for row in panel["rows"]
    ]


def _count_panel_solutions(panel):
    rows = _panel_rows_with_masks(panel)
    count = 0
    for _, a in rows[0]:
        for _, b in rows[1]:
            if a & b:
                continue
            ab = a | b
            for _, c in rows[2]:
                if ab & c:
                    continue
                abc = ab | c
                for _, d in rows[3]:
                    if not (abc & d) and (abc | d) == _TARGET_MASK:
                        count += 1
    return count


def enumerate_all(inst):
    """Count all valid answers exactly when row products stay under a fixed cap."""
    work = inst["panel_count"] * inst["n"] ** 4
    if work > 2_000_000:
        return None
    total = 1
    for panel in inst["panels"]:
        total *= _count_panel_solutions(panel)
    return total


def _canonical_panel(panel):
    raw_rows = [
        [_difference_tuple(candidate["block"]) for candidate in row["candidates"]]
        for row in panel["rows"]
    ]
    forms = []
    for unit in _UNITS:
        rows = []
        for row in raw_rows:
            transformed = [
                tuple(sorted(unit * difference % _MOD for difference in block_diffs))
                for block_diffs in row
            ]
            rows.append(tuple(sorted(transformed)))
        forms.append(tuple(sorted(rows)))
    return min(forms)


def canonical_key(inst):
    """Invariant under the generated affine, translation, and reorder symmetries."""
    panels = sorted(_canonical_panel(panel) for panel in inst["panels"])
    payload = json.dumps(panels, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _intended_operations(n, panels):
    return (2 * n + 5) * panels + 16


def escalate(params):
    """Grow affine-image haystacks first; add panels only after they are full."""
    if not isinstance(params, dict) or not set(params) <= {"n", "panels"}:
        return None
    n = params.get("n")
    panels = params.get("panels", 2)
    if not isinstance(n, int) or not isinstance(panels, int):
        return None
    if n < 25:
        out = dict(params)
        out["n"] = min(25, n + 4)
        out["panels"] = panels
        return out
    next_panels = panels + 1
    if _intended_operations(n, next_panels) <= 300 and 24 * next_panels <= 256:
        out = dict(params)
        out["n"] = n
        out["panels"] = next_panels
        return out
    return "cap_bound"


def _reference_algorithm(inst):
    """Row-constrained exact-cover backtracking, the Track-B standard method."""
    answer = []
    nodes = 0
    difference_operations = 0
    for panel in inst["panels"]:
        rows = _panel_rows_with_masks(panel)
        difference_operations += sum(len(row) for row in rows) * 30
        found = None

        def visit(row_index, used, selected):
            nonlocal nodes, found
            if found is not None:
                return
            if row_index == 4:
                if used == _TARGET_MASK:
                    found = [list(candidate["block"]) for candidate in selected]
                return
            for candidate, mask in rows[row_index]:
                nodes += 1
                if not (used & mask):
                    visit(row_index + 1, used | mask, selected + [candidate])

        visit(0, 0, [])
        if found is None:
            return None, {
                "nodes": nodes,
                "difference_operations": difference_operations,
                "operations": nodes + difference_operations,
            }
        answer.append(found)
    return answer, {
        "nodes": nodes,
        "difference_operations": difference_operations,
        "operations": nodes + difference_operations,
    }


def _compact_moment_algorithm(inst):
    """Execute the intended invariant route using only displayed checksums."""
    answer = []
    operations = 16  # conservative extended-Euclid cost for two fixed inverses
    inverse_c = pow(_CALIBRATION[2][0], -1, _MOD)
    inverse_d = pow(_CALIBRATION[3][0], -1, _MOD)
    for panel in inst["panels"]:
        rows = panel["rows"]
        by_name = {row["name"]: row for row in rows}
        keys_c = {}
        keys_d = {}
        for candidate in by_name["C"]["candidates"]:
            key = candidate["m2"] * inverse_c % _MOD
            operations += 1
            keys_c[key] = candidate
        for candidate in by_name["D"]["candidates"]:
            key = candidate["m2"] * inverse_d % _MOD
            operations += 1
            keys_d[key] = candidate
        common = set(keys_c) & set(keys_d)
        if len(common) != 1:
            return None, operations
        q = common.pop()
        q_squared = q * q % _MOD
        operations += 1
        selected = {"C": keys_c[q], "D": keys_d[q]}
        for row_index, row_name in ((0, "A"), (1, "B")):
            expected_m2 = _CALIBRATION[row_index][0] * q % _MOD
            expected_m4 = _CALIBRATION[row_index][1] * q_squared % _MOD
            operations += 2
            matches = [
                candidate
                for candidate in by_name[row_name]["candidates"]
                if candidate["m2"] == expected_m2
                and candidate["m4"] == expected_m4
            ]
            if len(matches) != 1:
                return None, operations
            selected[row_name] = matches[0]
        answer.append([list(selected[row["name"]]["block"]) for row in rows])
    return answer, operations


def _attack_minimum_sum(inst):
    return [
        [
            list(min(row["candidates"], key=lambda c: (sum(c["block"]), c["block"]))["block"])
            for row in panel["rows"]
        ]
        for panel in inst["panels"]
    ]


def _attack_greedy_overlap(inst):
    answer = []
    for panel in inst["panels"]:
        used = 0
        chosen = []
        for row in panel["rows"]:
            candidate = min(
                row["candidates"],
                key=lambda c: (
                    (_difference_mask(c["block"]) & used).bit_count(),
                    sum(c["block"]),
                    c["block"],
                ),
            )
            chosen.append(list(candidate["block"]))
            used |= _difference_mask(candidate["block"])
        answer.append(chosen)
    return answer


def _attack_random_restart(inst, seed, restarts=64):
    rng = random.Random(seed)
    last = None
    for _ in range(restarts):
        last = random_candidate(inst, rng)
        if verify(inst, last)[0]:
            return last
    return last


def _cyclic_distance(a, b):
    delta = abs(a - b) % _MOD
    return min(delta, _MOD - delta)


def _attack_equal_raw_moment(inst):
    answer = []
    for panel in inst["panels"]:
        anchor = min(panel["rows"][2]["candidates"], key=lambda c: (c["m2"], c["block"]))
        target = anchor["m2"]
        chosen = []
        for row in panel["rows"]:
            candidate = min(
                row["candidates"],
                key=lambda c: (_cyclic_distance(c["m2"], target), c["block"]),
            )
            chosen.append(list(candidate["block"]))
        answer.append(chosen)
    return answer


def _transformed_instance(inst, seed):
    """Apply real problem symmetries and carry the witness through them."""
    rng = random.Random(seed)
    transformed = copy.deepcopy(inst)
    new_panel_pairs = []
    for panel_index, panel in enumerate(inst["panels"]):
        unit = rng.choice(_UNITS)
        row_pairs = []
        for row_index, row in enumerate(panel["rows"]):
            selected = tuple(sorted(inst["answer"][panel_index][row_index]))
            carried = None
            candidates = []
            for candidate in row["candidates"]:
                translation = rng.randrange(_MOD)
                block = sorted(
                    (unit * x + translation) % _MOD for x in candidate["block"]
                )
                updated = {
                    "block": block,
                    "m2": _central_moment(block, 2),
                    "m4": _central_moment(block, 4),
                }
                candidates.append(updated)
                if tuple(candidate["block"]) == selected:
                    carried = list(block)
            rng.shuffle(candidates)
            updated_row = dict(row)
            updated_row["candidates"] = candidates
            if carried is None:
                raise AssertionError("could not carry planted block")
            row_pairs.append((updated_row, carried))
        rng.shuffle(row_pairs)
        new_panel_pairs.append(
            ({"rows": [pair[0] for pair in row_pairs]}, [pair[1] for pair in row_pairs])
        )
    rng.shuffle(new_panel_pairs)
    transformed["panels"] = [pair[0] for pair in new_panel_pairs]
    transformed["answer"] = [pair[1] for pair in new_panel_pairs]
    return transformed


def _answer_atoms(answer):
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, (list, tuple)):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def selftest():
    """Run correctness, density, attacks, scaling, symmetry, and output gates."""
    report = {"track": TRACK}

    planted_checks = 0
    planted_failures = []
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(5):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            planted_checks += 1
            if not ok:
                planted_failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_roundtrips += 1
    report["G1_planted_verifies"] = {
        "pass": not planted_failures and json_roundtrips == planted_checks,
        "checks": planted_checks,
        "json_native_roundtrips": json_roundtrips,
        "failures": planted_failures,
    }

    shipping_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    ship = make_instance(seed=424242, **shipping_params)

    corruptions = {}
    corruptions["empty"] = []
    corruptions["drop_panel"] = copy.deepcopy(ship["answer"][:-1])
    drop_block = copy.deepcopy(ship["answer"])
    drop_block[0] = drop_block[0][:-1]
    corruptions["drop_block"] = drop_block
    drop_point = copy.deepcopy(ship["answer"])
    drop_point[0][0] = drop_point[0][0][:-1]
    corruptions["drop_point"] = drop_point
    swapped = copy.deepcopy(ship["answer"])
    swapped[0][0], swapped[0][1] = swapped[0][1], swapped[0][0]
    corruptions["swap_rows"] = swapped
    duplicated = copy.deepcopy(ship["answer"])
    duplicated[0][0][-1] = duplicated[0][0][0]
    corruptions["duplicate_point"] = duplicated
    out_of_range = copy.deepcopy(ship["answer"])
    out_of_range[0][0][0] = 125
    corruptions["out_of_range"] = out_of_range
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(ship, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = {item["reason"] for item in corruption_results.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in corruption_results.values())
        and len(reasons) == len(corruption_results),
        "cases": corruption_results,
        "distinct_reasons": len(reasons),
    }

    serialized = json.dumps(ship["answer"], separators=(",", ":"))
    response = (
        "The directed differences partition correctly.\n"
        "<answer>```json\n" + serialized + "\n```</answer>\n"
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == ship["answer"]
        and verify(ship, parsed)[0]
        and parse_answer("garbage") is None,
        "parsed_equals_answer": parsed == ship["answer"],
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    samples = 200_000
    hits = 0
    guess_rng = random.Random(991827)
    started = time.perf_counter()
    for _ in range(samples):
        hits += int(verify(ship, random_candidate(ship, guess_rng))[0])
    guess_seconds = time.perf_counter() - started
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "search_space": search_space(ship),
        "sampling_seconds": round(guess_seconds, 6),
        "prior": "one uniform advertised candidate from every row of every panel",
    }

    exact_count = enumerate_all(ship)
    started = time.perf_counter()
    reference_answer, reference_stats = _reference_algorithm(ship)
    baseline_seconds = time.perf_counter() - started
    reference_ok = reference_answer is not None and verify(ship, reference_answer)[0]
    report["G5_density_and_baseline"] = {
        "pass": exact_count is not None and exact_count > 0 and reference_ok,
        "shipping_exact_valid_count": exact_count,
        "shipping_search_space": search_space(ship),
        "shipping_exact_solution_fraction": exact_count / search_space(ship),
        "shipping_sample_hits": hits,
        "shipping_sample_total": samples,
        "baseline_wall_seconds": round(baseline_seconds, 6),
        "baseline_nodes": reference_stats["nodes"],
        "baseline_difference_operations": reference_stats["difference_operations"],
        "baseline_total_operations": reference_stats["operations"],
        "baseline_solved": reference_ok,
    }

    attack_functions = {
        "outlier_minimum_block_sum": lambda inst, seed: _attack_minimum_sum(inst),
        "greedy_low_difference_overlap": lambda inst, seed: _attack_greedy_overlap(inst),
        "random_restart_64": lambda inst, seed: _attack_random_restart(inst, seed, 64),
        "in_context_equal_raw_moment": lambda inst, seed: _attack_equal_raw_moment(inst),
    }
    attempts = 8
    attack_results = {
        name: {"successes": 0, "attempts": attempts} for name in attack_functions
    }
    ref_successes = 0
    ref_total_seconds = 0.0
    ref_total_ops = 0
    ref_total_nodes = 0
    compact_successes = 0
    compact_operations = []
    for offset in range(attempts):
        inst = make_instance(seed=900_000 + offset, **shipping_params)
        for name, attack in attack_functions.items():
            candidate = attack(inst, 700_000 + offset)
            attack_results[name]["successes"] += int(verify(inst, candidate)[0])
        started = time.perf_counter()
        candidate, stats = _reference_algorithm(inst)
        ref_total_seconds += time.perf_counter() - started
        ref_total_ops += stats["operations"]
        ref_total_nodes += stats["nodes"]
        ref_successes += int(candidate is not None and verify(inst, candidate)[0])
        compact_candidate, operation_count = _compact_moment_algorithm(inst)
        compact_operations.append(operation_count)
        compact_successes += int(
            compact_candidate is not None and verify(inst, compact_candidate)[0]
        )
    all_failed = all(item["successes"] == 0 for item in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": (
            all_failed
            and ref_successes == attempts
            and compact_successes == attempts
        ),
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "row-constrained Algorithm X / exact-cover backtracking",
            "complexity": "O(p*n^4) mask trials after O(p*n) block preprocessing",
            "wall_clock_sec": round(ref_total_seconds / attempts, 6),
            "operations": round(ref_total_ops / attempts),
            "nodes": round(ref_total_nodes / attempts),
            "solves": f"{ref_successes}/{attempts}, as expected",
        },
        "compact_route": {
            "name": "centered C2/C4 affine-covariant match",
            "operations_max": max(compact_operations),
            "solves": f"{compact_successes}/{attempts}",
        },
    }

    if 2 * shipping_params["n"] <= 25:
        doubled_params = dict(shipping_params)
        doubled_params["n"] *= 2
        doubled_axis = "choices_per_row"
    else:
        doubled_params = dict(shipping_params)
        doubled_params["panels"] *= 2
        doubled_axis = "panels"
    doubled = make_instance(seed=314159, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    next_params = escalate(shipping_params)
    escalated_ok = False
    if isinstance(next_params, dict):
        escalated = make_instance(seed=271828, **next_params)
        escalated_ok = verify(escalated, escalated["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and escalated_ok,
        "shipping_params": shipping_params,
        "doubled_params": doubled_params,
        "doubled_axis": doubled_axis,
        "candidate_blocks_before": 4 * ship["n"] * ship["panel_count"],
        "candidate_blocks_after": 4 * doubled["n"] * doubled["panel_count"],
        "answer_atoms_before": _answer_atoms(ship["answer"]),
        "answer_atoms_after": _answer_atoms(doubled["answer"]),
        "doubled_verified": doubled_ok,
        "escalated_params": next_params,
        "escalated_verified": escalated_ok,
    }

    invariance_checks = 0
    witness_checks = 0
    failures = []
    unrelated_keys = []
    for offset in range(20):
        inst = make_instance(seed=1_200_000 + offset, **shipping_params)
        key = canonical_key(inst)
        unrelated_keys.append(key)
        changed = _transformed_instance(inst, 1_300_000 + offset)
        invariance_checks += 1
        if canonical_key(changed) != key:
            failures.append([offset, "affine/translation/reorder key"])
        if verify(changed, changed["answer"])[0]:
            witness_checks += 1
        else:
            failures.append([offset, "carried witness"])

        reordered = copy.deepcopy(inst)
        for panel in reordered["panels"]:
            for row in panel["rows"]:
                row["candidates"].reverse()
        invariance_checks += 1
        if canonical_key(reordered) != key:
            failures.append([offset, "candidate reorder key"])
        if verify(reordered, inst["answer"])[0]:
            witness_checks += 1
        else:
            failures.append([offset, "candidate reorder witness"])
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not failures
        and witness_checks == invariance_checks
        and distinct_count == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": witness_checks,
        "unrelated_distinct": distinct_count,
        "unrelated_attempts": 20,
        "failures": failures,
        "transformations": [
            "independent base-block translations",
            "global unit multiplication per panel",
            "candidate, row, and panel reorderings",
        ],
    }

    compact_lengths = []
    for seed in range(20):
        answer = make_instance(seed=seed, **shipping_params)["answer"]
        compact_lengths.append(len(json.dumps(answer, separators=(",", ":"))))
    answer_chars = max(compact_lengths)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(ship["answer"])
    intended_ops = _intended_operations(ship["n"], ship["panel_count"])
    arms = {name: dict(G9_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
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
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G")
    )
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = shipping_params
    report["certificate_language"] = CERTIFICATE_LANGUAGE
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
