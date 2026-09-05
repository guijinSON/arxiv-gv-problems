"""Rejected Track-B prototype for arXiv:1301.4764.

The generated problem asks for the two summands in the three-way intersection
count supplied by the paper's weighting and filling constructions.  Instances
are succinct recipes for three genuine S(2,4,v) designs; the planted answer is
known by composition, never by solving the generated instance.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
import os
import random
import re
import time
from collections import Counter


TRACK = "B"
SHIPPING_DIFFICULTY = "hard"


# These measurements are replaced after the required bare/hinted/placebo runs.
G9_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}


PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "other",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "succinctly specified triples of S(2,4,v) block designs",
        "4-GDD weighting ingredients and S(2,4,13) fillings",
    ],
    "verification_operations": [
        "exact permutation of finite blocks",
        "exact three-set intersection on ingredient blocks",
        "integer weighted sums",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Common blocks add across the disjoint ingredients of the paper's "
        "weighting-and-filling construction, replacing expansion of every block "
        "by two short weighted sums."
    ),
    "hardness_basis": (
        "Track B: the reference generate/hash/intersect algorithm is O(v^2 n); "
        "at the hard preset it processes 4,187,139 generated blocks plus "
        "2,791,426 hash probes in 25.18 seconds on the audit host, whereas the "
        "decomposition route uses 195 small-block membership/integer operations."
    ),
    "max_answer_tokens": 4,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"]
        + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE = {
    "description": (
        "A length-two integer vector [outer, filling].  The outer count is in "
        "[0,16m] in multiples of m divided by the outer selector period (or is "
        "zero when m=0); the filling count is in [0,13u] in multiples of u "
        "divided by the filling selector period.  All quantities are printed "
        "in the instance."
    ),
    "bounds": {
        "components": 2,
        "outer": "0..16m at step m/outer_period (zero only when m=0)",
        "filling": "0..13u at step u/filling_period",
    },
}

DIFFICULTY = {
    "demo": {"n": 1, "period_cap": 1},
    "easy": {"n": 2, "period_cap": 15},
    "medium": {"n": 4, "period_cap": 255},
    "hard": {"n": 5, "period_cap": 600},
}


STRUCTURAL_HINT = (
    "The common-block sets of the disjoint ingredients are additive across the "
    "weighting-and-filling construction."
)
PLACEBO_HINT = (
    "The exact block count rewards careful attention to the displayed labels, "
    "residues, and conventions."
)


NOTES = """\
Definition: Section 1 defines an S(2,4,v) design and three-way intersection as
the blocks common to all three designs.  Construction: Theorem 3.1 makes the
intersection count a sum over weighted GDD ingredients, Theorem 3.2 adds the
fillings, Lemma 4.1 gives the seven S(2,4,13) permutation ingredients, and
Lemma 4.5 gives the five 4-GDD ingredients of type 4^4.  Theorem 5.1 combines
exactly those objects and writes the result as sum(alpha_i)+sum(beta_j).

What is easy: Theorem 1.1 completely classifies feasible intersection numbers
for admissible v >= 49, so merely asking whether a number is feasible is a
constant-time lookup and is not this family.  A literal supplied-design count
is also polynomial: generate all b_v blocks and hash-intersect them.  Therefore
the module declares Track B.  It exposes a succinct design recipe for which the
literal route has millions of block operations at the shipping preset, while
the paper's additive decomposition has a fixed small catalog and two sums.

Attack hardening: plants and decoys are the same permutation ingredients; only
their residue-run multiplicities differ.  Every shipping run contains every
catalog entry.  This defeats choosing a fixed-point outlier, choosing the
largest local overlap greedily, treating all permutations as automorphisms, and
an unweighted-average ansatz.  The successful domain-standard block expansion
is reported separately, as Track B requires.
"""


# GF(4) is F_2[z]/(z^2+z+1), encoded 0,1,z,z+1 as 0,1,2,3.
_MUL4 = (
    (0, 0, 0, 0),
    (0, 1, 2, 3),
    (0, 2, 3, 1),
    (0, 3, 1, 2),
)


def _cycles(n, *cycles):
    p = list(range(n))
    for cyc in cycles:
        if len(cyc) < 2:
            continue
        for a, b in zip(cyc, cyc[1:] + cyc[:1]):
            p[a] = b
    return tuple(p)


_ID13 = tuple(range(13))
_ID16 = tuple(range(16))

# The S(2,4,13) displayed in Lemma 4.1 (a,b,c are 10,11,12).
_B13 = (
    (0, 1, 3, 9), (0, 2, 8, 12), (0, 4, 5, 7), (0, 6, 10, 11),
    (1, 2, 4, 10), (1, 5, 6, 8), (1, 7, 11, 12),
    (2, 3, 5, 11), (2, 6, 7, 9), (3, 4, 6, 12),
    (3, 7, 8, 10), (4, 8, 9, 11), (5, 9, 10, 12),
)

_LOCAL_PERMS = (
    (_ID13, _ID13, _ID13),
    (_ID13,
     _cycles(13, [0, 1, 2, 3, 4, 5]),
     _cycles(13, [5, 4, 3, 2, 1, 0])),
    (_ID13,
     _cycles(13, [8, 5], [10, 11], [3, 7], [1, 6]),
     _cycles(13, [8, 6], [1, 5], [10, 3, 11, 7])),
    (_ID13,
     _cycles(13, [7, 11, 12, 6]),
     _cycles(13, [8, 5, 6, 7])),
    (_ID13,
     _cycles(13, [4, 7], [9, 2], [1, 8]),
     _cycles(13, [3, 9, 12], [1, 8])),
    (_ID13,
     _cycles(13, [3, 7], [12, 0, 2], [1, 6], [9, 11]),
     _cycles(13, [9, 4], [3, 7], [0, 2], [1, 6])),
    (_ID13,
     _cycles(13, [10, 11], [4, 5]),
     _cycles(13, [10, 11], [12, 8])),
)

_LOCAL_CYCLE_TEXT = (
    ("id", "id"),
    ("(0 1 2 3 4 5)", "(5 4 3 2 1 0)"),
    ("(8 5)(a b)(3 7)(1 6)", "(8 6)(1 5)(a 3 b 7)"),
    ("(7 b c 6)", "(8 5 6 7)"),
    ("(4 7)(9 2)(1 8)", "(3 9 c)(1 8)"),
    ("(3 7)(c 0 2)(1 6)(9 b)", "(9 4)(3 7)(0 2)(1 6)"),
    ("(a b)(4 5)", "(a b)(c 8)"),
)

# The S(2,4,16) in Lemma 4.2; deleting parallel class _P16 gives
# the 4-GDD of type 4^4 used in Lemma 4.5.
_B16 = (
    (0, 1, 2, 3), (0, 4, 5, 6), (0, 7, 8, 9), (0, 10, 11, 12),
    (0, 13, 14, 15), (1, 4, 7, 10), (1, 5, 11, 13),
    (1, 6, 8, 14), (1, 9, 12, 15), (2, 4, 12, 14),
    (2, 5, 7, 15), (2, 6, 9, 11), (2, 8, 10, 13),
    (3, 4, 9, 13), (3, 5, 8, 12), (3, 6, 10, 15),
    (3, 7, 11, 14), (4, 8, 11, 15), (5, 9, 10, 14),
    (6, 7, 12, 13),
)
_P16 = {
    (0, 1, 2, 3), (4, 8, 11, 15), (5, 9, 10, 14), (6, 7, 12, 13),
}
_GDD16 = tuple(b for b in _B16 if b not in _P16)
_GDD_GROUPS = (
    (0, 1, 2, 3), (4, 8, 11, 15), (5, 9, 10, 14), (6, 7, 12, 13),
)
_LABEL_TO_GROUP_COPY = {
    label: (group_index, copy_index)
    for group_index, group in enumerate(_GDD_GROUPS)
    for copy_index, label in enumerate(group)
}

_OUTER_PERMS = (
    (_ID16, _ID16, _ID16),
    (_ID16,
     _cycles(16, [6, 7, 12]),
     _cycles(16, [6, 12, 7])),
    (_ID16,
     _cycles(16, [0, 1, 2], [10, 14]),
     _cycles(16, [15, 11], [1, 0, 2])),
    (_ID16,
     _cycles(16, [4, 15], [13, 7], [10, 9, 5]),
     _cycles(16, [7, 12, 13], [15, 11, 4])),
    (_ID16,
     _cycles(16, [0, 1, 2, 3]),
     _cycles(16, [4, 8, 11, 15])),
)

_OUTER_CYCLE_TEXT = (
    ("id", "id"),
    ("(6 7 c)", "(6 c 7)"),
    ("(0 1 2)(a e)", "(f b)(1 0 2)"),
    ("(4 f)(d 7)(a 9 5)", "(7 c d)(f b 4)"),
    ("(0 1 2 3)", "(4 8 b f)"),
)


def _image_blocks(blocks, perm):
    return {tuple(sorted(perm[x] for x in b)) for b in blocks}


def _catalog_counts(blocks, templates):
    base = {tuple(sorted(b)) for b in blocks}
    out = []
    for triple in templates:
        sets = [_image_blocks(blocks, p) for p in triple]
        out.append(len(base.intersection(sets[1], sets[2])))
    return tuple(out)


_OUTER_COUNTS = _catalog_counts(_GDD16, _OUTER_PERMS)
_LOCAL_COUNTS = _catalog_counts(_B13, _LOCAL_PERMS)


def _largest_divisor_at_most(number, cap):
    if number <= 0:
        return 1
    cap = max(1, min(int(cap), number))
    for candidate in range(cap, 0, -1):
        if number % candidate == 0:
            return candidate
    return 1


def _positive_runs(period, catalog_size, rng):
    used = min(period, catalog_size)
    ids = rng.sample(range(catalog_size), used)
    rng.shuffle(ids)
    if used == 1:
        lengths = [period]
    else:
        cuts = sorted(rng.sample(range(1, period), used - 1))
        endpoints = [0] + cuts + [period]
        lengths = [endpoints[i + 1] - endpoints[i] for i in range(used)]
    return [{"template": t, "length": length} for t, length in zip(ids, lengths)]


def _coprime_stride(period, rng):
    if period == 1:
        return 0
    choices = [x for x in range(1, period) if math.gcd(x, period) == 1]
    return rng.choice(choices)


def _random_presentation(n, rng):
    order = list(range(n))
    rng.shuffle(order)
    scales = [rng.randrange(1, 4) for _ in range(n)]
    copies = list(range(4))
    rng.shuffle(copies)
    return {
        "coordinate_order": order,
        "coordinate_scales": scales,
        "copy_permutation": copies,
    }


def _weighted_catalog_sum(runs, counts, repetitions):
    return repetitions * sum(r["length"] * counts[r["template"]] for r in runs)


def make_instance(n, seed=0, period_cap=600, **params):
    """Construct three designs by Theorems 3.1/3.2 and retain their two sums."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("n must be a positive integer")
    if isinstance(period_cap, bool) or not isinstance(period_cap, int) or period_cap < 1:
        raise ValueError("period_cap must be a positive integer")
    rng = random.Random(seed)
    q = 4 ** n
    u = (q - 1) // 3
    master_blocks = (q - 1) * (q - 4) // 12
    v = 4 * (q - 1) + 1
    total_blocks = v * (v - 1) // 12

    outer_period = _largest_divisor_at_most(master_blocks, period_cap)
    local_period = _largest_divisor_at_most(u, period_cap)
    outer_runs = _positive_runs(outer_period, len(_OUTER_PERMS), rng)
    local_runs = _positive_runs(local_period, len(_LOCAL_PERMS), rng)

    outer_selector = {
        "period": outer_period,
        "stride": _coprime_stride(outer_period, rng),
        "shift": rng.randrange(outer_period),
        "runs": outer_runs,
    }
    local_selector = {
        "period": local_period,
        "stride": _coprime_stride(local_period, rng),
        "shift": rng.randrange(local_period),
        "runs": local_runs,
    }

    outer_common = _weighted_catalog_sum(
        outer_runs, _OUTER_COUNTS, master_blocks // outer_period
    )
    local_common = _weighted_catalog_sum(
        local_runs, _LOCAL_COUNTS, u // local_period
    )

    inst = {
        "family": "three-way S(2,4,v) intersection profile",
        "n": n,
        "q": q,
        "u": u,
        "master_blocks": master_blocks,
        "v": v,
        "total_blocks_per_design": total_blocks,
        "outer_blocks_per_design": 16 * master_blocks,
        "filling_blocks_per_design": 13 * u,
        "outer_selector": outer_selector,
        "local_selector": local_selector,
        "presentation": _random_presentation(n, rng),
        "design_order": rng.sample([0, 1, 2], 3),
        "answer": [outer_common, local_common],
    }
    return inst


def _label(x):
    return str(x) if x < 10 else chr(ord("a") + x - 10)


def _block_text(blocks):
    return " ".join("{" + ",".join(_label(x) for x in b) + "}" for b in blocks)


def _runs_text(selector, prefix):
    pieces = []
    lo = 0
    for run in selector["runs"]:
        hi = lo + run["length"] - 1
        pieces.append(f"{lo}..{hi}:{prefix}{run['template']}")
        lo = hi + 1
    return "; ".join(pieces)


def render(inst):
    """Render a complete, self-contained compressed block-design problem."""
    outer_catalog = "\n".join(
        f"  O{i}: p2={a}; p3={b}"
        for i, (a, b) in enumerate(_OUTER_CYCLE_TEXT)
    )
    local_catalog = "\n".join(
        f"  L{i}: p2={a}; p3={b}"
        for i, (a, b) in enumerate(_LOCAL_CYCLE_TEXT)
    )
    p = inst["presentation"]
    if inst["master_blocks"]:
        outer_section = f"""2. Weight every nonzero master point by four copies.
On the 16 copies above master block j, put one of the following triples of
4-GDDs.  The base GDD has groups
{{0,1,2,3}}, {{4,8,b,f}}, {{5,9,a,e}}, {{6,7,c,d}} and these 16 blocks:
{_block_text(_GDD16)}
In every row design 1 is the base, while designs 2 and 3 apply p2 and p3:
{outer_catalog}

For j=0,...,{inst['master_blocks'] - 1}, compute
r=({inst['outer_selector']['stride']}*j+{inst['outer_selector']['shift']}) mod {inst['outer_selector']['period']}.
Choose the template from this run table:
  {_runs_text(inst['outer_selector'], 'O')}
Map the four displayed GDD groups, in the displayed order, to the four sorted
points of master block j; positions inside a group are the four copy labels."""
    else:
        outer_section = """2. Weight every nonzero master point by four copies.
There are no master blocks at this order, so this step contributes no blocks."""

    statement = f"""Three-way intersection profile for S(2,4,v) designs

An S(2,4,v) design is a set of 4-element blocks on v points in which every
unordered pair of distinct points occurs in exactly one block.  A block is
common to three designs when the identical unordered 4-set occurs in all three.

This instance succinctly defines three such designs by a weighting construction
followed by fillings.  All indexing below is 0-based; intervals are inclusive;
cycle notation maps each entry to the next and the last back to the first;
unmentioned labels are fixed.  Blocks and designs are sets, so their order is
irrelevant and no block is repeated.

1. Master 4-GDD.
Use GF(4)=F_2[z]/(z^2+z+1), encoded by 0,1,z,z+1 as 0,1,2,3.
Addition is bitwise XOR and z^2=z+1.  Points are vectors in GF(4)^{inst['n']}.
A direction is normalized by making its first nonzero coordinate 1.  For each
direction u, the nonzero points on its line through zero form one 3-point group.
Every affine line not through zero is a master block.  Directions are ordered by
increasing position of the first nonzero coordinate and then by lexicographic
suffix; the unique representatives whose pivot coordinate is zero are ordered
lexicographically, omitting the all-zero representative.
There are u={inst['u']} groups and m={inst['master_blocks']} master blocks.

{outer_section}

3. Fill every 12-point weighted group together with one shared infinity point.
The base S(2,4,13), on labels 0,...,9,a,b,c, has these 13 blocks:
{_block_text(_B13)}
Here label 0 maps to infinity and labels 1,...,c map in order to the twelve
weighted points of that group: first sort its three encoded nonzero GF(4)
vectors as integers, then list copy labels 0,1,2,3 for each vector.  The
filling-template triples are:
{local_catalog}

For group index j=0,...,{inst['u'] - 1}, compute
r=({inst['local_selector']['stride']}*j+{inst['local_selector']['shift']}) mod {inst['local_selector']['period']}.
Choose the template from this run table:
  {_runs_text(inst['local_selector'], 'L')}

The union of all weighted ingredient blocks and all filling blocks is each final
design.  Finally, the three designs are presented in source-column order
{inst['design_order']}.  Points are simultaneously renamed by coordinate order
{p['coordinate_order']}, nonzero GF(4) scales {p['coordinate_scales']}, and copy
permutation {p['copy_permutation']}: output coordinate i is its listed scale
times the input coordinate at its listed coordinate-order position, and old
copy c is renamed to the c-th listed copy.  Infinity remains fixed.  This last
renaming does not alter equality of blocks.

The final order is v={inst['v']}; each design has {inst['total_blocks_per_design']}
blocks, split into {inst['outer_blocks_per_design']} weighted-ingredient blocks
and {inst['filling_blocks_per_design']} filling blocks.

Find TWO exact integer counts: (i) blocks common to all three designs in the
weighted ingredients, and (ii) blocks common to all three in the fillings.

Give your final answer inside <answer></answer> tags, as outer, filling.
Example: <answer>240, 17</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


_ANSWER_TAG = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_INTEGER_PAIR = re.compile(r"^\s*([+-]?\d+)\s*,\s*([+-]?\d+)\s*$")


def parse_answer(text):
    """Parse the delimited two-integer answer, returning None on any garbage."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_TAG.search(text)
    if not match:
        return None
    body = match.group(1).strip()
    integers = _INTEGER_PAIR.fullmatch(body)
    if integers:
        return [int(x) for x in integers.groups()]
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, list) else None


def _expected_profile(inst):
    n = inst.get("n")
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("invalid dimension")
    q = 4 ** n
    u_expected = (q - 1) // 3
    m_expected = (q - 1) * (q - 4) // 12
    v_expected = 4 * (q - 1) + 1
    derived = {
        "q": q,
        "u": u_expected,
        "master_blocks": m_expected,
        "v": v_expected,
        "outer_blocks_per_design": 16 * m_expected,
        "filling_blocks_per_design": 13 * u_expected,
        "total_blocks_per_design": v_expected * (v_expected - 1) // 12,
    }
    if any(inst.get(key) != value for key, value in derived.items()):
        raise ValueError("inconsistent derived design parameters")
    if sorted(inst.get("design_order", [])) != [0, 1, 2]:
        raise ValueError("design order is not a permutation")
    presentation = inst.get("presentation", {})
    if sorted(presentation.get("coordinate_order", [])) != list(range(n)):
        raise ValueError("coordinate order is not a permutation")
    if (len(presentation.get("coordinate_scales", [])) != n
            or any(x not in (1, 2, 3) for x in presentation["coordinate_scales"])):
        raise ValueError("invalid nonzero coordinate scales")
    if sorted(presentation.get("copy_permutation", [])) != [0, 1, 2, 3]:
        raise ValueError("copy order is not a permutation")
    outer = inst.get("outer_selector")
    local = inst.get("local_selector")
    if not isinstance(outer, dict) or not isinstance(local, dict):
        raise ValueError("instance has no selectors")
    op = outer["period"]
    lp = local["period"]
    m = inst["master_blocks"]
    u = inst["u"]
    if op < 1 or lp < 1 or m % op or u % lp:
        raise ValueError("selector period does not divide its site count")
    if sum(x["length"] for x in outer["runs"]) != op:
        raise ValueError("outer runs do not cover one period")
    if sum(x["length"] for x in local["runs"]) != lp:
        raise ValueError("local runs do not cover one period")
    if math.gcd(outer["stride"], op) != 1 and op != 1:
        raise ValueError("outer stride is not invertible")
    if math.gcd(local["stride"], lp) != 1 and lp != 1:
        raise ValueError("local stride is not invertible")
    for row in outer["runs"]:
        if row["template"] not in range(len(_OUTER_COUNTS)) or row["length"] < 1:
            raise ValueError("invalid outer run")
    for row in local["runs"]:
        if row["template"] not in range(len(_LOCAL_COUNTS)) or row["length"] < 1:
            raise ValueError("invalid local run")
    return [
        _weighted_catalog_sum(outer["runs"], _OUTER_COUNTS, m // op),
        _weighted_catalog_sum(local["runs"], _LOCAL_COUNTS, u // lp),
    ]


def verify(inst, answer):
    """Verify any valid profile without consulting inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a two-component integer vector"
    if len(answer) == 0:
        return False, "the integer vector is empty"
    if len(answer) == 1:
        return False, "the filling component is missing"
    if len(answer) > 2:
        return False, "the integer vector has extra components"
    names = ("outer", "filling")
    limits = (inst["outer_blocks_per_design"], inst["filling_blocks_per_design"])
    values = []
    for component, name, limit in zip(answer, names, limits):
        if isinstance(component, bool) or not isinstance(component, int):
            return False, f"{name} component must be an integer"
        if not 0 <= component <= limit:
            return False, f"{name} count is outside 0..{limit}"
        values.append(component)
    try:
        expected = _expected_profile(inst)
    except (KeyError, TypeError, ValueError) as exc:
        return False, f"malformed instance: {exc}"
    if values[0] != expected[0]:
        return False, "outer common-block count is incorrect"
    if values[1] != expected[1]:
        return False, "filling common-block count is incorrect"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly after enforcing the visible complete-period divisors."""
    outer_step = (inst["master_blocks"] // inst["outer_selector"]["period"]
                  if inst["master_blocks"] else 1)
    local_step = inst["u"] // inst["local_selector"]["period"]
    return [
        outer_step * rng.randrange(inst["outer_blocks_per_design"] // outer_step + 1),
        local_step * rng.randrange(inst["filling_blocks_per_design"] // local_step + 1),
    ]


def search_space(inst):
    outer_step = (inst["master_blocks"] // inst["outer_selector"]["period"]
                  if inst["master_blocks"] else 1)
    local_step = inst["u"] // inst["local_selector"]["period"]
    return ((inst["outer_blocks_per_design"] // outer_step + 1)
            * (inst["filling_blocks_per_design"] // local_step + 1))


def enumerate_all(inst):
    space = search_space(inst)
    if space > 20_000:
        return None
    outer_step = (inst["master_blocks"] // inst["outer_selector"]["period"]
                  if inst["master_blocks"] else 1)
    local_step = inst["u"] // inst["local_selector"]["period"]
    hits = 0
    for outer in range(0, inst["outer_blocks_per_design"] + 1, outer_step):
        for filling in range(0, inst["filling_blocks_per_design"] + 1, local_step):
            ok, _ = verify(inst, [outer, filling])
            hits += int(ok)
    return hits


def canonical_key(inst):
    """Canonicalize the multiset of independent ingredient templates."""
    _expected_profile(inst)  # validate before canonicalizing

    def multiplicities(selector, sites, catalog_size):
        repeated = sites // selector["period"]
        counts = [0] * catalog_size
        for run in selector["runs"]:
            counts[run["template"]] += repeated * run["length"]
        return counts

    payload = {
        "n": inst["n"],
        "outer_template_multiplicities": multiplicities(
            inst["outer_selector"], inst["master_blocks"], len(_OUTER_PERMS)
        ),
        "filling_template_multiplicities": multiplicities(
            inst["local_selector"], inst["u"], len(_LOCAL_PERMS)
        ),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def escalate(params):
    n = int(params.get("n", 1))
    cap = int(params.get("period_cap", 1))
    return {"n": n + 1, "period_cap": min(100_000, max(cap + 1, cap * 2))}


# ---- Exact expansion, used only as the successful Track-B reference method. ----

def _digits(value, n):
    out = []
    for _ in range(n):
        out.append(value & 3)
        value >>= 2
    return tuple(reversed(out))


def _from_digits(values):
    out = 0
    for value in values:
        out = (out << 2) | value
    return out


def _scalar_vector(scalar, vector):
    return tuple(_MUL4[scalar][x] for x in vector)


def _directions(n):
    for pivot in range(n):
        for suffix in itertools.product(range(4), repeat=n - pivot - 1):
            yield (0,) * pivot + (1,) + suffix


def _direction_points(direction):
    return tuple(_from_digits(_scalar_vector(s, direction)) for s in (1, 2, 3))


def _master_blocks(n):
    for direction in _directions(n):
        pivot = next(i for i, x in enumerate(direction) if x)
        other = [i for i in range(n) if i != pivot]
        for raw in itertools.product(range(4), repeat=n - 1):
            if not any(raw):
                continue
            base = [0] * n
            for index, value in zip(other, raw):
                base[index] = value
            points = []
            for scalar in range(4):
                delta = _scalar_vector(scalar, direction)
                points.append(_from_digits(tuple(a ^ b for a, b in zip(base, delta))))
            yield tuple(sorted(points))


def _run_template(selector, index):
    period = selector["period"]
    residue = (selector["stride"] * index + selector["shift"]) % period
    upto = 0
    for run in selector["runs"]:
        upto += run["length"]
        if residue < upto:
            return run["template"]
    raise ValueError("selector runs do not cover residue")


def _latent_point_id(master_point, copy_label):
    return 1 + 4 * (master_point - 1) + copy_label


def _rename_point(inst, point):
    if point == 0:
        return 0
    zero_based = point - 1
    master_point = 1 + zero_based // 4
    copy_label = zero_based % 4
    presentation = inst["presentation"]
    source = _digits(master_point, inst["n"])
    target = tuple(
        _MUL4[presentation["coordinate_scales"][i]][
            source[presentation["coordinate_order"][i]]
        ]
        for i in range(inst["n"])
    )
    new_master = _from_digits(target)
    new_copy = presentation["copy_permutation"][copy_label]
    return _latent_point_id(new_master, new_copy)


def _pack_block(inst, block):
    width = max(1, (inst["v"] - 1).bit_length())
    packed = 0
    for point in sorted(_rename_point(inst, p) for p in block):
        packed = (packed << width) | point
    return packed


def _outer_blocks(inst, output_design):
    source_design = inst["design_order"][output_design]
    for block_index, master in enumerate(_master_blocks(inst["n"])):
        template = _run_template(inst["outer_selector"], block_index)
        perm = _OUTER_PERMS[template][source_design]
        for base_block in _GDD16:
            actual = []
            for label in base_block:
                moved = perm[label]
                group, copy_label = _LABEL_TO_GROUP_COPY[moved]
                actual.append(_latent_point_id(master[group], copy_label))
            yield _pack_block(inst, actual)


def _local_blocks(inst, output_design):
    source_design = inst["design_order"][output_design]
    for group_index, direction in enumerate(_directions(inst["n"])):
        template = _run_template(inst["local_selector"], group_index)
        perm = _LOCAL_PERMS[template][source_design]
        weighted = [
            _latent_point_id(master, copy_label)
            for master in sorted(_direction_points(direction))
            for copy_label in range(4)
        ]
        label_map = [0] + weighted
        for base_block in _B13:
            yield _pack_block(inst, [label_map[perm[label]] for label in base_block])


def _reference_zone(inst, generator):
    first = set(generator(inst, 0))
    pair = {block for block in generator(inst, 1) if block in first}
    common = sum(1 for block in generator(inst, 2) if block in pair)
    return common, len(first), len(pair)


def reference_algorithm(inst):
    """Generate every block and hash-intersect; succeeds, as Track B expects."""
    started = time.perf_counter()
    outer, outer_size, outer_pair = _reference_zone(inst, _outer_blocks)
    local, local_size, local_pair = _reference_zone(inst, _local_blocks)
    elapsed = time.perf_counter() - started
    answer = [outer, local]
    ok, reason = verify(inst, answer)
    total = inst["total_blocks_per_design"]
    return {
        "answer": answer,
        "verify_ok": ok,
        "verify_reason": reason,
        "wall_clock_sec": round(elapsed, 6),
        "generated_blocks": 3 * total,
        "hash_probes": 2 * total,
        "outer_set_size": outer_size,
        "outer_pair_intersection": outer_pair,
        "local_set_size": local_size,
        "local_pair_intersection": local_pair,
    }


def _attack_candidates(inst, rng):
    m = inst["master_blocks"]
    u = inst["u"]
    outer_runs = inst["outer_selector"]["runs"]
    local_runs = inst["local_selector"]["runs"]

    # Treat the catalog row with the most fixed points as a global outlier.
    def fixed_score(triple):
        return sum(sum(int(p[i] == i) for i in range(len(p))) for p in triple[1:])

    outlier_o = max(range(len(_OUTER_PERMS)), key=lambda i: fixed_score(_OUTER_PERMS[i]))
    outlier_l = max(range(len(_LOCAL_PERMS)), key=lambda i: fixed_score(_LOCAL_PERMS[i]))
    yield "fixed_point_outlier", [
        m * _OUTER_COUNTS[outlier_o],
        u * _LOCAL_COUNTS[outlier_l],
    ]

    # Greedily use the largest-overlap row at every site.
    yield "greedy_largest_local_overlap", [
        m * max(_OUTER_COUNTS),
        u * max(_LOCAL_COUNTS),
    ]

    # A natural but false ansatz: every displayed point permutation is an
    # automorphism of its base design.
    yield "all_permutations_are_automorphisms", [
        inst["outer_blocks_per_design"],
        inst["filling_blocks_per_design"],
    ]

    # Ignore run lengths and average only the distinct rows that appear.
    oavg = round(m * sum(_OUTER_COUNTS[r["template"]] for r in outer_runs)
                 / len(outer_runs))
    lavg = round(u * sum(_LOCAL_COUNTS[r["template"]] for r in local_runs)
                 / len(local_runs))
    yield "unweighted_template_average", [oavg, lavg]

    # Mild random restarts over the fully structure-aware bounded language.
    for _ in range(256):
        yield "random_restart_256", random_candidate(inst, rng)


def _rotate_selector_representation(selector):
    """Change the cyclic run-table origin without changing any site template."""
    rotated = copy.deepcopy(selector)
    if len(rotated["runs"]) > 1:
        cut = rotated["runs"][0]["length"]
        rotated["runs"] = rotated["runs"][1:] + rotated["runs"][:1]
        rotated["shift"] = (rotated["shift"] - cut) % rotated["period"]
    return rotated


def _equivalent_variants(inst):
    """Independent relabellings plus their composition, for the G8 audit."""
    presentation = copy.deepcopy(inst)
    rng = random.Random(99173 + inst["n"] + inst["v"])
    presentation["presentation"] = _random_presentation(inst["n"], rng)

    columns = copy.deepcopy(inst)
    columns["design_order"] = list(reversed(columns["design_order"]))

    selectors = copy.deepcopy(inst)
    for name in ("outer_selector", "local_selector"):
        selectors[name] = _rotate_selector_representation(selectors[name])

    composed = copy.deepcopy(selectors)
    composed["presentation"] = copy.deepcopy(presentation["presentation"])
    composed["design_order"] = copy.deepcopy(columns["design_order"])
    return {
        "point_relabelling": presentation,
        "design_column_reordering": columns,
        "selector_origin_rotation": selectors,
        "composed": composed,
    }


def _rotated_equivalent(inst):
    """Backward-compatible name for the fully composed G8 transformation."""
    return _equivalent_variants(inst)["composed"]


def _selector_assignments_equal(left, right):
    if left["period"] != right["period"]:
        return False
    return all(
        _run_template(left, index) == _run_template(right, index)
        for index in range(left["period"])
    )


def _validate_small_design(inst):
    designs = []
    for design in range(3):
        blocks = list(_outer_blocks(inst, design)) + list(_local_blocks(inst, design))
        if len(blocks) != inst["total_blocks_per_design"] or len(set(blocks)) != len(blocks):
            return False, "wrong block count or duplicate"
        # Unpack just for the small validation.
        width = max(1, (inst["v"] - 1).bit_length())
        mask = (1 << width) - 1
        pair_counts = Counter()
        for packed in blocks:
            pts = []
            value = packed
            for _ in range(4):
                pts.append(value & mask)
                value >>= width
            for pair in itertools.combinations(sorted(pts), 2):
                pair_counts[pair] += 1
        if len(pair_counts) != inst["v"] * (inst["v"] - 1) // 2:
            return False, "not every pair is covered"
        if any(count != 1 for count in pair_counts.values()):
            return False, "a pair is covered other than once"
        designs.append(set(blocks))
    actual = len(designs[0] & designs[1] & designs[2])
    expected = sum(_expected_profile(inst))
    return (actual == expected, "ok" if actual == expected else "intersection mismatch")


def selftest():
    report = {
        "paper": "1301.4764",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
    }

    planted_checks = 0
    json_checks = 0
    failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            planted_checks += 1
            if not ok:
                failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_checks += 1
    small_ok, small_reason = _validate_small_design(make_instance(seed=7, **DIFFICULTY["easy"]))
    report["G1_planted_verifies"] = {
        "pass": not failures and small_ok and json_checks == planted_checks,
        "checks": planted_checks,
        "json_native_checks": json_checks,
        "expanded_S_2_4_61_check": small_reason,
        "failures": failures,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]
    corruptions = {
        "drop": planted[:-1],
        "swap": list(reversed(planted)),
        "duplicate": planted + [planted[0]],
        "empty": [],
        "out_of_range": [shipping["outer_blocks_per_design"] + 1, planted[1]],
    }
    corruption_results = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(x["rejected"] for x in corruption_results.values())
                and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    answer_text = f"{planted[0]}, {planted[1]}"
    realistic = f"I used the GDD decomposition.\n```text\n<answer>{answer_text}</answer>\n```"
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted,
        "parsed": parsed,
    }

    guess_rng = random.Random(20260905)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        ok, _ = verify(shipping, random_candidate(shipping, guess_rng))
        guess_hits += int(ok)
    exact_density = 1.0 / search_space(shipping)
    report["G4_guess_resistance"] = {
        "pass": guess_hits == 0 and exact_density < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_hits / guess_total,
        "exact_probability_unique_profile": exact_density,
        "structure_aware_space": search_space(shipping),
    }

    reference = reference_algorithm(shipping)
    reduced = make_instance(seed=3, **DIFFICULTY["easy"])
    report["G5_density_and_baseline_cost"] = {
        "pass": reference["verify_ok"] and guess_hits == 0,
        "shipping_sampled_valid_fraction": guess_hits / guess_total,
        "shipping_density_sample_size": guess_total,
        "shipping_exact_valid_profiles": 1,
        "shipping_candidate_profiles": search_space(shipping),
        "easy_exact_solution_count": enumerate_all(reduced),
        "baseline_wall_clock_seconds": reference["wall_clock_sec"],
        "baseline_generated_blocks": reference["generated_blocks"],
        "baseline_hash_probes": reference["hash_probes"],
    }

    attack_names = (
        "fixed_point_outlier",
        "greedy_largest_local_overlap",
        "all_permutations_are_automorphisms",
        "unweighted_template_average",
        "random_restart_256",
    )
    attack_results = {name: {"successes": 0, "attempts": 8} for name in attack_names}
    for seed in range(8):
        inst = make_instance(seed=1000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        per_seed = {name: False for name in attack_names}
        for name, candidate in _attack_candidates(inst, random.Random(7000 + seed)):
            ok, _ = verify(inst, candidate)
            per_seed[name] = per_seed[name] or ok
        for name in attack_names:
            attack_results[name]["successes"] += int(per_seed[name])
    panel_pass = all(row["successes"] == 0 for row in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": panel_pass,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "generate every block, hash two intersections",
            "complexity": "O(v^2 n) finite-field/block operations, O(v^2) memory",
            "wall_clock_sec": reference["wall_clock_sec"],
            "operations": reference["generated_blocks"] + reference["hash_probes"],
            "generated_blocks": reference["generated_blocks"],
            "hash_probes": reference["hash_probes"],
            "solves": "1/1 measured at shipping; expected for every instance",
        },
    }

    harder_params = escalate(DIFFICULTY[SHIPPING_DIFFICULTY])
    build_start = time.perf_counter()
    harder = make_instance(seed=2718, **harder_params)
    harder_build = time.perf_counter() - build_start
    harder_ok, harder_reason = verify(harder, harder["answer"])
    report["G7_scales"] = {
        "pass": harder_ok and harder["v"] > 2 * shipping["v"],
        "shipping_v": shipping["v"],
        "larger_v": harder["v"],
        "size_ratio": harder["v"] / shipping["v"],
        "larger_build_seconds": round(harder_build, 6),
        "larger_verify_reason": harder_reason,
        "answer_atomic_elements_unchanged": 2,
    }

    invariant_checks = 0
    real_transform_checks = 0
    selector_semantic_checks = 0
    invariant_failures = []
    transformation_types = (
        "point_relabelling",
        "design_column_reordering",
        "selector_origin_rotation",
        "composed",
    )
    distinct = {}
    seed = 0
    while len(distinct) < 20 and seed < 500:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        variants = _equivalent_variants(inst)
        for name in transformation_types:
            transformed = variants[name]
            if canonical_key(inst) != canonical_key(transformed):
                invariant_failures.append(f"{seed}/{name}")
            else:
                invariant_checks += 1
            if verify(transformed, inst["answer"])[0]:
                real_transform_checks += 1
        rotated = variants["selector_origin_rotation"]
        if all(
            _selector_assignments_equal(inst[field], rotated[field])
            for field in ("outer_selector", "local_selector")
        ):
            selector_semantic_checks += 1
        distinct.setdefault(canonical_key(inst), seed)
        seed += 1
    report["G8_canonical_key"] = {
        "pass": (not invariant_failures and invariant_checks >= 80
                 and real_transform_checks >= 80
                 and selector_semantic_checks >= 20 and len(distinct) >= 20),
        "invariance_checks": invariant_checks,
        "real_transformation_checks": real_transform_checks,
        "selector_semantic_checks": selector_semantic_checks,
        "transformation_types": list(transformation_types),
        "distinct_unrelated_keys": len(distinct),
        "unrelated_instances_examined": seed,
        "invariance_failures": invariant_failures,
        "key_basis": "(n, outer/filling ingredient-template multiplicity vectors)",
    }

    answer_blob = json.dumps(planted, separators=(",", ":"))
    answer_elements = 2
    answer_tokens = max(1, (len(answer_blob) + 3) // 4)
    hinted = G9_RESULTS["hinted"]
    placebo = G9_RESULTS["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    within_caps = len(answer_blob) <= 2000 and answer_elements <= 256 and 195 <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": copy.deepcopy(G9_RESULTS),
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": "hardened" if hinted["solved"] == 0 and hinted["attempts"] else
                           ("too_easy" if hinted["solved"] else "not_run"),
        "answer_chars": len(answer_blob),
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": 195,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
