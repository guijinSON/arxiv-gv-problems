"""Verified generator for an affine-factor Kidney Exchange family.

The source problem is the Kidney Exchange Problem (KEP) as defined in
arXiv:2603.18471.  An instance is a finite directed compatibility graph with no
altruists.  Its vertices are arranged in cyclic layers over a prime field and
its compatibility arcs are represented exactly by short affine-map tables.

Generation is answer-first.  One uniformly positioned map in every layer has a
common global fixed point, and their slopes are sampled so that their product is
one.  Those maps therefore compose to the identity and describe a full packing
of vertex-disjoint bounded cycles.  Verification recomputes this identity using
integer modular arithmetic; it never reads the planted answer.

Only the Python standard library is used.  Importing this module performs no
I/O and has no side effects.
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
from typing import Any, Iterable


TRACK = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "graph",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "directed compatibility graph represented by affine maps over a prime field",
        "bounded directed cycles",
        "path-cycle packing",
    ],
    "verification_operations": [
        "exact finite-field affine composition",
        "table membership",
        "identity and bound comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "After normalizing each local anchor by its layer offset, one fixed point "
        "is shared by a map in every layer; without that invariant, a solver must "
        "search for an identity word in the affine group."
    ),
    "hardness_basis": (
        "Track B: meet-in-the-middle affine-word search solves the shipping "
        "instance in O(L*n^(L/2)) time; seed 2024 used 1,365,236 measured field "
        "operations and about 0.18 seconds, whereas the shared-fixed-point route "
        "takes 259 exact arithmetic operations."
    ),
    "max_answer_tokens": 100,
}

NATIVE: dict = {
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

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "An exact symbolic affine-map word: one record {layer, anchor, slope} "
        "chosen from each displayed layer, with every integer in 0..p-1, whose "
        "maps compose to the identity."
    ),
    "bounds": {
        "records": "layers",
        "choices_per_layer": "n",
        "fields_per_record": 3,
        "field_min": 0,
        "field_max": "modulus-1",
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 3, "layers": 4, "modulus": 101, "screen_restarts": 0},
    "easy": {"n": 5, "layers": 8, "modulus": 1009, "screen_restarts": 512},
    "medium": {"n": 8, "layers": 10, "modulus": 5003, "screen_restarts": 2048},
    "hard": {"n": 12, "layers": 10, "modulus": 10007, "screen_restarts": 4096},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Normalize each displayed anchor by its layer offset: the map tables share "
    "a finite-field fixed point."
)
PLACEBO_HINT = (
    "Compare each displayed anchor with its layer offset and check all finite-field "
    "conditions carefully."
)

# Filled after the three harness arms are run.  These are diagnostics, not gates.
G9_ARMS: dict = {
    "bare": {"solved": 3, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}

NOTES = r"""
Paper reading (arXiv:2603.18471v2).  Section 1 gives the exact Kidney Exchange
Problem definition.  G is a loopless directed compatibility graph, B is the set
of altruistic sources, path and cycle lengths count edges, a feasible path must
start in B, a feasible cycle must avoid B, and t is the required total number of
transplant edges.  This family takes B empty, path limit 0, cycle limit L, and
t=pL.  Its affine word expands to p vertex-disjoint L-cycles, exactly covering
the Lp patient-donor vertices.

The certificate-producing question was asked before construction.  Theorem 1
gives a deterministic O*(6.855^t) algorithm for general KEP; Theorem 2 gives an
O*(2^|V|) dynamic program; and Theorem 3 gives a randomized O*(4^t) color-coding
algorithm.  The construction also has a polynomial-size symbolic description,
so generic affine-word meet-in-the-middle solves it in O(L*n^(L/2)).  It cannot
honestly be Track A.  Track B measures the gap between that million-operation
mechanical route and recognizing the common normalized fixed point.

The paper's easy regimes are not hidden.  KEP is FPT in target t, so t grows
with the field and layer count.  Section 3 separately handles l_p>=t or l_c>=t
using k-Path and Long Directed Cycle routines; here L=l_c<t=pL, inside Lemma 3's
bounded-packing regime.  Section 5 identifies faster algorithms for small fixed
length bounds as an open practical direction.  This generator's additional
affine promise is explicitly disclosed and is exactly why TRACK is B.

Generation samples all map positions symmetrically.  Each map has a uniformly
distributed global fixed point and a nonzero, nonidentity slope; the planted
maps differ only through a cross-layer correlation.  Their last slope is chosen
as the inverse product of the preceding slopes, so the certificate is known by
composition of identities before any attack is run.

The magnitude/position outlier probe is defeated by random offsets, parameters,
and row order.  The partial-composition greedy probe, random word restarts, and
same-row-index ansatz are screened and recorded.  The expected successful domain
reference is separate: meet-in-the-middle composition of affine normal forms.
The shorter construction-specific route intersects normalized fixed points and
then checks the slope product.
"""


def _is_prime(value: int) -> bool:
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


def _validate_parameters(n: int, layers: int, modulus: int, screen_restarts: int) -> None:
    for name, value in (("n", n), ("layers", layers), ("modulus", modulus),
                        ("screen_restarts", screen_restarts)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
    if n < 2:
        raise ValueError("n must be at least 2")
    if layers < 3:
        raise ValueError("layers must be at least 3")
    if not _is_prime(modulus):
        raise ValueError("modulus must be prime")
    if modulus - 2 < n * layers:
        raise ValueError("modulus is too small for distinct nonidentity slopes")
    if screen_restarts < 0:
        raise ValueError("screen_restarts must be nonnegative")


def _global_fixed(inst: dict, layer: int, pair: list[int] | tuple[int, int]) -> int:
    return (int(pair[0]) + int(inst["offsets"][layer])) % int(inst["modulus"])


def _affine_from_pair(
    inst: dict, layer: int, pair: list[int] | tuple[int, int]
) -> tuple[int, int]:
    """Return (a,b) for z -> a*z+b in the common global coordinate."""
    p = inst["modulus"]
    fixed = _global_fixed(inst, layer, pair)
    slope = int(pair[1])
    return slope, ((1 - slope) * fixed) % p


def _compose(g: tuple[int, int], f: tuple[int, int], p: int) -> tuple[int, int]:
    """Compose affine maps as g after f."""
    return (g[0] * f[0] % p, (g[0] * f[1] + g[1]) % p)


def _word_composition(inst: dict, pairs: Iterable[list[int] | tuple[int, int]]) -> tuple[int, int]:
    total = (1, 0)
    for layer, pair in enumerate(pairs):
        total = _compose(_affine_from_pair(inst, layer, pair), total, inst["modulus"])
    return total


def _answer_from_pairs(pairs: list[list[int]]) -> dict:
    return {
        "maps": [
            {"layer": layer, "anchor": pair[0], "slope": pair[1]}
            for layer, pair in enumerate(pairs)
        ]
    }


def _raw_instance(
    n: int,
    layers: int,
    modulus: int,
    screen_restarts: int,
    rng: random.Random,
    build_round: int,
) -> dict:
    common_fixed = rng.randrange(modulus)
    offsets = rng.sample(range(modulus), layers)

    while True:
        dependent_layer = rng.randrange(layers)
        independent_slopes = rng.sample(range(2, modulus), layers - 1)
        product = 1
        for slope in independent_slopes:
            product = product * slope % modulus
        dependent_slope = pow(product, -1, modulus)
        if dependent_slope != 1 and dependent_slope not in independent_slopes:
            planted_slopes = []
            independent = iter(independent_slopes)
            for layer in range(layers):
                planted_slopes.append(
                    dependent_slope if layer == dependent_layer else next(independent)
                )
            break

    used_slopes = set(planted_slopes)
    remaining_slopes = [s for s in range(2, modulus) if s not in used_slopes]
    decoy_slopes = rng.sample(remaining_slopes, layers * (n - 1))

    maps: list[list[list[int]]] = []
    answer_pairs: list[list[int]] = []
    cursor = 0
    for layer in range(layers):
        planted_anchor = (common_fixed - offsets[layer]) % modulus
        planted_pair = [planted_anchor, planted_slopes[layer]]
        fixed_pool = [x for x in range(modulus) if x != common_fixed]
        decoy_fixed = rng.sample(fixed_pool, n - 1)
        rows = [planted_pair]
        for fixed in decoy_fixed:
            anchor = (fixed - offsets[layer]) % modulus
            rows.append([anchor, decoy_slopes[cursor]])
            cursor += 1
        rng.shuffle(rows)
        maps.append(rows)
        answer_pairs.append(planted_pair)

    return {
        "family": "affine_cycle_factor_kidney_exchange",
        "n": n,
        "layers": layers,
        "modulus": modulus,
        "offsets": offsets,
        "maps": maps,
        "vertex_count": layers * modulus,
        "altruists": [],
        "path_limit": 0,
        "cycle_limit": layers,
        "target": layers * modulus,
        "screen_restarts": screen_restarts,
        "build_round": build_round,
        "answer": _answer_from_pairs(answer_pairs),
    }


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Build a KEP yes-instance and its affine cycle-factor certificate first.

    ``n`` is the number of offered affine maps per layer.  At fixed layer count,
    the certificate length stays constant while the exact word space is n^layers,
    so larger n means harder.  The graph itself has ``layers * modulus`` vertices.
    """
    layers = params.pop("layers", 10)
    modulus = params.pop("modulus", 10007)
    screen_restarts = params.pop("screen_restarts", 0)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_parameters(n, layers, modulus, screen_restarts)

    rng = random.Random(seed)
    for build_round in range(64):
        inst = _raw_instance(
            n, layers, modulus, screen_restarts, rng, build_round
        )
        if not screen_restarts:
            return inst
        attacks = _run_attacks(inst, screen_restarts)
        if not any(
            candidate is not None and verify(inst, candidate)[0]
            for candidate in attacks.values()
        ):
            return inst
    raise RuntimeError("could not draw an instance that passed the heuristic screen")


def render(inst: dict) -> str:
    """Return the complete self-contained problem statement shown to a solver."""
    layer_rows = []
    for layer, rows in enumerate(inst["maps"]):
        layer_rows.append(
            f"Layer {layer}, offset {inst['offsets'][layer]}: "
            + " ".join(f"[{anchor},{slope}]" for anchor, slope in rows)
        )
    tables = "\n".join(layer_rows)
    statement = f"""Kidney exchange: certify a full bounded-cycle packing

All arithmetic below is modulo the prime p={inst['modulus']}.  The directed
compatibility graph has {inst['layers']} layers.  Its vertices are pairs (i,x),
where the 0-based layer i is in 0..{inst['layers'] - 1} and the residue x is in
0..{inst['modulus'] - 1}.  Every vertex is a patient-donor pair; there are no
altruistic donors.  Thus paths are forbidden (path limit 0).  The cycle-length
limit is {inst['layers']} edges and the transplant target is
{inst['target']} edges.

The complete arc set is specified by the map tables below.  In layer i, choose
any displayed pair [q,a].  For every residue x, that pair supplies the arc

  (i,x) -> ((i+1) mod {inst['layers']}, y),

where

  y = q + offset[i] - offset[(i+1) mod {inst['layers']}]
      + a*(x-q)  (mod {inst['modulus']}).

No other arcs exist.  Each displayed slope is nonzero, so each row describes a
bijection between consecutive layers.  A full affine cycle-factor certificate
selects exactly one displayed [q,a] from every layer.  Starting with every x in
layer 0 and following the selected maps must return to the same x after exactly
{inst['layers']} arcs.  If it does, the selected arcs form exactly
{inst['modulus']} vertex-disjoint cycles of length {inst['layers']}, cover every
vertex once, and meet the transplant target.

Map tables; row order is arbitrary and [q,a] means [anchor,slope]:
{tables}

Return one JSON object with the sole key "maps".  Its value must contain exactly
{inst['layers']} records, one for each layer.  Each record has integer fields
"layer", "anchor", and "slope"; records may be in any order, but layer numbers
must be distinct and cover 0..{inst['layers'] - 1}.  The anchor and slope must
exactly match one displayed pair in that layer.  Repeats and omitted layers are
not allowed.

Give your final answer inside <answer></answer> tags.
Example format: <answer>{{"maps":[{{"layer":0,"anchor":3,"slope":7}}]}}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Extract the last tagged JSON certificate, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, flags=re.I | re.S)
    for raw in reversed(blocks):
        body = raw.strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, flags=re.I | re.S)
        if fenced:
            body = fenced.group(1).strip()
        try:
            value = json.loads(body)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(value, dict) or not isinstance(value.get("maps"), list):
            continue
        return value
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid affine cycle-factor witness without reading inst['answer']."""
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if set(answer) != {"maps"}:
        return False, "answer must contain only the maps field"
    records = answer["maps"]
    if not isinstance(records, list):
        return False, "maps must be a JSON array"
    if not records:
        return False, "map selection is empty"
    if len(records) != inst["layers"]:
        return False, f"expected {inst['layers']} map records, got {len(records)}"

    by_layer: dict[int, list[int]] = {}
    for index, record in enumerate(records):
        if not isinstance(record, dict) or set(record) != {"layer", "anchor", "slope"}:
            return False, f"record {index} must have exactly layer, anchor, and slope"
        values = (record["layer"], record["anchor"], record["slope"])
        if not all(isinstance(v, int) and not isinstance(v, bool) for v in values):
            return False, f"record {index} contains a non-integer field"
        layer, anchor, slope = values
        if layer < 0 or layer >= inst["layers"]:
            return False, f"record {index} has an out-of-range layer"
        if layer in by_layer:
            return False, f"layer {layer} is selected more than once"
        if not (0 <= anchor < inst["modulus"] and 0 <= slope < inst["modulus"]):
            return False, f"record {index} has an out-of-range affine parameter"
        pair = [anchor, slope]
        if pair not in inst["maps"][layer]:
            return False, f"record {index} is not an offered map in layer {layer}"
        by_layer[layer] = pair

    if set(by_layer) != set(range(inst["layers"])):
        return False, "the selected layer numbers are incomplete"
    composition = _word_composition(
        inst, [by_layer[layer] for layer in range(inst["layers"])]
    )
    if composition != (1, 0):
        return False, "selected affine maps do not compose to the identity"
    if inst["cycle_limit"] != inst["layers"] or inst["target"] != inst["vertex_count"]:
        return False, "instance cycle bound or transplant target is inconsistent"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from one offered map per layer, the statement-aware space."""
    pairs = [list(rng.choice(rows)) for rows in inst["maps"]]
    records = _answer_from_pairs(pairs)["maps"]
    rng.shuffle(records)
    return {"maps": records}


def search_space(inst: dict) -> int | None:
    """Return the exact size of the declared map-word language."""
    return inst["n"] ** inst["layers"]


def enumerate_all(inst: dict) -> int | None:
    """Count identity words exactly when the declared space has at most two million."""
    if search_space(inst) > 2_000_000:
        return None
    count = 0
    for word in itertools.product(*inst["maps"]):
        if _word_composition(inst, word) == (1, 0):
            count += 1
    return count


def _candidate_from_indices(inst: dict, indices: list[int]) -> dict:
    return _answer_from_pairs(
        [list(inst["maps"][layer][index]) for layer, index in enumerate(indices)]
    )


def _decode_word(code: int, length: int, base: int) -> list[int]:
    digits = [0] * length
    for position in range(length - 1, -1, -1):
        digits[position] = code % base
        code //= base
    return digits


def _reference_solution(inst: dict) -> tuple[dict | None, dict[str, int]]:
    """Meet in the middle on affine normal forms; do not use the planted invariant."""
    p = inst["modulus"]
    split = inst["layers"] // 2
    affine_layers = [
        [_affine_from_pair(inst, layer, pair) for pair in rows]
        for layer, rows in enumerate(inst["maps"])
    ]
    left_table: dict[tuple[int, int], int] = {}
    extensions = 0
    field_operations = 0
    left_leaves = 0
    right_leaves = 0

    def build_left(position: int, total: tuple[int, int], code: int) -> None:
        nonlocal extensions, field_operations, left_leaves
        if position == split:
            left_leaves += 1
            left_table.setdefault(total, code)
            return
        for index, affine in enumerate(affine_layers[position]):
            extensions += 1
            field_operations += 5
            build_left(position + 1, _compose(affine, total, p),
                       code * inst["n"] + index)

    build_left(0, (1, 0), 0)
    found: tuple[int, list[int]] | None = None

    def search_right(
        position: int, total: tuple[int, int], indices: list[int]
    ) -> bool:
        nonlocal extensions, field_operations, right_leaves, found
        if position == inst["layers"]:
            right_leaves += 1
            inverse_a = pow(total[0], -1, p)
            inverse_b = (-inverse_a * total[1]) % p
            field_operations += 3
            left_code = left_table.get((inverse_a, inverse_b))
            if left_code is None:
                return False
            found = (left_code, list(indices))
            return True
        for index, affine in enumerate(affine_layers[position]):
            extensions += 1
            field_operations += 5
            if search_right(position + 1, _compose(affine, total, p), indices + [index]):
                return True
        return False

    search_right(split, (1, 0), [])
    stats = {
        "composition_extensions": extensions,
        "field_operations": field_operations,
        "left_leaves": left_leaves,
        "right_leaves": right_leaves,
        "stored_normal_forms": len(left_table),
    }
    if found is None:
        return None, stats
    left_code, right_indices = found
    left_indices = _decode_word(left_code, split, inst["n"])
    return _candidate_from_indices(inst, left_indices + right_indices), stats


def _compact_solution(inst: dict) -> tuple[dict | None, int]:
    """Construction-specific shared-fixed-point route used only for measurement."""
    tables: list[dict[int, list[int]]] = []
    operations = 0
    for layer, rows in enumerate(inst["maps"]):
        table = {}
        for pair in rows:
            operations += 2  # one addition and one modular reduction
            table[_global_fixed(inst, layer, pair)] = pair
        tables.append(table)
    common = set(tables[0])
    for table in tables[1:]:
        common &= set(table)
    for fixed in sorted(common):
        pairs = [list(table[fixed]) for table in tables]
        product = 1
        for pair in pairs[:-1]:
            product = product * pair[1] % inst["modulus"]
            operations += 2
        expected_last = pow(product, -1, inst["modulus"])
        operations += 1
        if pairs[-1][1] == expected_last:
            candidate = _answer_from_pairs(pairs)
            if verify(inst, candidate)[0]:
                return candidate, operations
    return None, operations


def _attack_minimum_parameters(inst: dict) -> dict:
    pairs = [min(rows, key=lambda pair: (pair[0], pair[1])) for rows in inst["maps"]]
    return _answer_from_pairs([list(pair) for pair in pairs])


def _attack_greedy_partial_identity(inst: dict) -> dict:
    total = (1, 0)
    indices = []
    p = inst["modulus"]
    for layer, rows in enumerate(inst["maps"]):
        choices = []
        for index, pair in enumerate(rows):
            composed = _compose(_affine_from_pair(inst, layer, pair), total, p)
            centered_a = min((composed[0] - 1) % p, (1 - composed[0]) % p)
            centered_b = min(composed[1], (-composed[1]) % p)
            choices.append(((centered_a, centered_b, index), composed))
        score, total = min(choices, key=lambda item: item[0])
        indices.append(score[2])
    return _candidate_from_indices(inst, indices)


def _attack_random_words(inst: dict, restarts: int) -> dict | None:
    digest = hashlib.sha256(
        json.dumps(
            {"offsets": inst["offsets"], "maps": inst["maps"]},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _attack_same_row(inst: dict) -> dict | None:
    for index in range(inst["n"]):
        candidate = _candidate_from_indices(inst, [index] * inst["layers"])
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _run_attacks(inst: dict, restarts: int) -> dict[str, dict | None]:
    return {
        "outlier_minimum_parameters": _attack_minimum_parameters(inst),
        "greedy_partial_identity": _attack_greedy_partial_identity(inst),
        f"random_word_restart_{restarts}": _attack_random_words(inst, restarts),
        "same_row_index_ansatz": _attack_same_row(inst),
    }


def _normalized_layers(inst: dict) -> tuple[tuple[tuple[int, int], ...], ...]:
    global_layers = [
        sorted((_global_fixed(inst, layer, pair), pair[1]) for pair in rows)
        for layer, rows in enumerate(inst["maps"])
    ]
    flat = sorted(
        (slope, layer, fixed)
        for layer, rows in enumerate(global_layers)
        for fixed, slope in rows
    )
    origin = flat[0][2]
    unit_record = next(record for record in flat if record[2] != origin)
    unit = unit_record[2]
    inverse_scale = pow((unit - origin) % inst["modulus"], -1, inst["modulus"])
    normalized = []
    for rows in global_layers:
        normalized.append(
            tuple(sorted((((fixed - origin) * inverse_scale) % inst["modulus"], slope)
                         for fixed, slope in rows))
        )
    rotations = [
        tuple(normalized[shift:] + normalized[:shift])
        for shift in range(inst["layers"])
    ]
    return min(rotations)


def canonical_key(inst: dict) -> str:
    """Canonicalize row order, cyclic layers, and global affine coordinate changes."""
    payload = {
        "n": inst["n"],
        "layers": inst["layers"],
        "modulus": inst["modulus"],
        "path_limit": inst["path_limit"],
        "cycle_limit": inst["cycle_limit"],
        "target": inst["target"],
        "normalized_layers": _normalized_layers(inst),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow the map-choice haystack while leaving the certificate length fixed."""
    current = {k: v for k, v in params.items() if k != "_preset"}
    n = int(current.get("n", 12))
    layers = int(current.get("layers", 10))
    modulus = int(current.get("modulus", 10007))
    restarts = int(current.get("screen_restarts", 4096))
    if n < 14:
        n = 14
        modulus = max(modulus, 10007)
        restarts = max(restarts, 8192)
        return {"n": n, "layers": layers, "modulus": modulus,
                "screen_restarts": restarts}
    # At n=16, normalizing all anchors and checking the slope product takes
    # 338 exact arithmetic operations.  Search can grow further, but the
    # no-tool route would cross the 300-operation cap.
    return "cap_bound"


def _count_atoms(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_count_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_count_atoms(v) for v in value)
    return 1


def _corruptions(inst: dict) -> dict[str, object]:
    answer = json.loads(json.dumps(inst["answer"]))
    empty = {"maps": []}
    dropped = {"maps": json.loads(json.dumps(answer["maps"][:-1]))}
    swapped = json.loads(json.dumps(answer))
    swapped["maps"][0]["anchor"], swapped["maps"][0]["slope"] = (
        swapped["maps"][0]["slope"], swapped["maps"][0]["anchor"]
    )
    duplicated = json.loads(json.dumps(answer))
    duplicated["maps"][1]["layer"] = duplicated["maps"][0]["layer"]
    out_of_range = json.loads(json.dumps(answer))
    out_of_range["maps"][0]["slope"] = inst["modulus"]
    return {
        "empty": empty,
        "drop": dropped,
        "swap": swapped,
        "duplicate": duplicated,
        "out_of_range": out_of_range,
    }


def _transform_instance(
    inst: dict,
    rng: random.Random,
    layer_shift: int = 0,
    affine_scale: int = 1,
    affine_translate: int = 0,
    reorder: bool = False,
) -> dict:
    p = inst["modulus"]
    layers = inst["layers"]
    shift = layer_shift % layers
    old_order = [(new_layer + shift) % layers for new_layer in range(layers)]
    offsets = [
        (affine_scale * inst["offsets"][old] + affine_translate) % p
        for old in old_order
    ]
    maps = []
    for old in old_order:
        rows = [[affine_scale * pair[0] % p, pair[1]] for pair in inst["maps"][old]]
        if reorder:
            rng.shuffle(rows)
        maps.append(rows)

    old_answer = {record["layer"]: record for record in inst["answer"]["maps"]}
    answer_pairs = []
    for old in old_order:
        record = old_answer[old]
        answer_pairs.append([
            affine_scale * record["anchor"] % p,
            record["slope"],
        ])
    answer = _answer_from_pairs(answer_pairs)
    if reorder:
        rng.shuffle(answer["maps"])
    return {
        **inst,
        "offsets": offsets,
        "maps": maps,
        "answer": answer,
    }


def selftest() -> dict:
    """Run gates G1--G9 and return their machine-readable measurements."""
    report: dict[str, Any] = {
        "paper": "2603.18471",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
    }

    g1_attempts = 0
    g1_successes = 0
    json_native = 0
    for params in DIFFICULTY.values():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            g1_attempts += 1
            if verify(inst, inst["answer"])[0]:
                g1_successes += 1
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_native += 1
    report["G1_planted_verifies"] = {
        "pass": g1_successes == g1_attempts and json_native == g1_attempts,
        "verified": g1_successes,
        "attempts": g1_attempts,
        "json_native": json_native,
    }

    shipping = make_instance(seed=2024, **DIFFICULTY[SHIPPING_DIFFICULTY])

    rejection_reasons = {}
    for name, candidate in _corruptions(shipping).items():
        ok, reason = verify(shipping, candidate)
        rejection_reasons[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in rejection_reasons.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in rejection_reasons.values())
        and len(set(reasons)) == len(reasons),
        "cases": rejection_reasons,
        "distinct_reasons": len(set(reasons)),
    }

    wire = json.dumps(shipping["answer"], separators=(",", ":"))
    response = f"I found the affine factor.\n<answer>```json\n{wire}\n```</answer>\nDone."
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"]
        and parse_answer("no tagged answer") is None
        and parse_answer("<answer>{bad}</answer>") is None,
        "prose_and_fence": parsed == shipping["answer"],
        "garbage_is_none": parse_answer("<answer>{bad}</answer>") is None,
    }

    guess_rng = random.Random(0x260318471)
    sample_total = 200_000
    sample_hits = 0
    for _ in range(sample_total):
        if verify(shipping, random_candidate(shipping, guess_rng))[0]:
            sample_hits += 1
    observed = sample_hits / sample_total
    report["G4_guess_resistance"] = {
        "pass": observed < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "observed_probability": observed,
        "candidate_space": search_space(shipping),
        "prior": "uniform over one offered map per layer, with shape and membership enforced",
    }

    started = time.perf_counter()
    reference_answer, reference_stats = _reference_solution(shipping)
    reference_seconds = time.perf_counter() - started
    reference_ok = reference_answer is not None and verify(shipping, reference_answer)[0]
    compact_answer, compact_operations = _compact_solution(shipping)
    compact_ok = compact_answer is not None and verify(shipping, compact_answer)[0]
    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_exact = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": reference_ok and compact_ok and demo_exact is not None and observed < 1e-6,
        "shipping_density_hits": sample_hits,
        "shipping_density_samples": sample_total,
        "shipping_observed_solution_fraction": observed,
        "shipping_exact_solution_count": None,
        "demo_exact_solution_count": demo_exact,
        "demo_candidate_space": search_space(demo),
        "baseline_wall_seconds": reference_seconds,
        "baseline_composition_extensions": reference_stats["composition_extensions"],
        "baseline_field_operations": reference_stats["field_operations"],
        "baseline_left_leaves": reference_stats["left_leaves"],
        "baseline_right_leaves": reference_stats["right_leaves"],
        "baseline_stored_normal_forms": reference_stats["stored_normal_forms"],
        "baseline_solved": reference_ok,
        "compact_route_operations": compact_operations,
        "compact_route_solved": compact_ok,
    }

    attack_names = [
        "outlier_minimum_parameters",
        "greedy_partial_identity",
        "random_word_restart_4096",
        "same_row_index_ansatz",
    ]
    attack_successes = {name: 0 for name in attack_names}
    reference_successes = 0
    reference_total_operations = 0
    reference_total_extensions = 0
    reference_total_seconds = 0.0
    compact_successes = 0
    compact_total_operations = 0
    panel_seeds = list(range(100, 108))
    for seed in panel_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        attacks = _run_attacks(inst, 4096)
        for name in attack_names:
            candidate = attacks[name]
            if candidate is not None and verify(inst, candidate)[0]:
                attack_successes[name] += 1
        started = time.perf_counter()
        candidate, stats = _reference_solution(inst)
        reference_total_seconds += time.perf_counter() - started
        reference_total_operations += stats["field_operations"]
        reference_total_extensions += stats["composition_extensions"]
        if candidate is not None and verify(inst, candidate)[0]:
            reference_successes += 1
        candidate, operations = _compact_solution(inst)
        compact_total_operations += operations
        if candidate is not None and verify(inst, candidate)[0]:
            compact_successes += 1
    attack_report = {
        name: {"successes": attack_successes[name], "attempts": len(panel_seeds)}
        for name in attack_names
    }
    report["G6_adversary_panel"] = {
        "pass": all(value == 0 for value in attack_successes.values())
        and reference_successes == len(panel_seeds)
        and compact_successes == len(panel_seeds),
        "attacks": attack_report,
        "reference_algorithm": {
            "name": "meet-in-the-middle affine normal-form composition",
            "complexity": "O(L*n^(ceil(L/2))) time and O(n^floor(L/2)) memory",
            "wall_clock_sec": reference_total_seconds,
            "composition_extensions": reference_total_extensions,
            "field_operations": reference_total_operations,
            "attempts": len(panel_seeds),
            "successes": reference_successes,
            "solves": f"{reference_successes}/{len(panel_seeds)}, as expected",
        },
        "construction_shortcut": {
            "name": "intersection of normalized fixed points",
            "complexity": "O(L*n)",
            "exact_arithmetic_operations": compact_total_operations,
            "attempts": len(panel_seeds),
            "successes": compact_successes,
        },
    }

    doubled = make_instance(
        n=2 * shipping["n"],
        seed=991,
        layers=shipping["layers"],
        modulus=shipping["modulus"],
        screen_restarts=0,
    )
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(shipping),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "shipping_search_space": search_space(shipping),
        "doubled_search_space": search_space(doubled),
        "doubled_vertices": doubled["vertex_count"],
        "doubled_verified": doubled_ok,
    }

    invariance_checks = 0
    invariance_failures = 0
    carried_checks = 0
    carried_failures = 0
    for seed in range(20):
        inst = make_instance(seed=10_000 + seed, **DIFFICULTY["medium"])
        original_key = canonical_key(inst)
        p = inst["modulus"]
        scale = random.Random(seed + 90).randrange(1, p)
        variants = [
            _transform_instance(inst, random.Random(seed + 1), reorder=True),
            _transform_instance(inst, random.Random(seed + 2), layer_shift=3),
            _transform_instance(inst, random.Random(seed + 3),
                                affine_scale=scale, affine_translate=seed + 17),
            _transform_instance(inst, random.Random(seed + 4), layer_shift=3,
                                affine_scale=scale, affine_translate=seed + 17,
                                reorder=True),
        ]
        for variant in variants:
            invariance_checks += 1
            if canonical_key(variant) != original_key:
                invariance_failures += 1
            carried_checks += 1
            if not verify(variant, variant["answer"])[0]:
                carried_failures += 1
    unrelated_keys = {
        canonical_key(make_instance(seed=20_000 + seed, **DIFFICULTY["medium"]))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": invariance_failures == 0
        and carried_failures == 0
        and len(unrelated_keys) == 20,
        "invariance_checks": invariance_checks,
        "invariance_failures": invariance_failures,
        "carried_witness_checks": carried_checks,
        "carried_witness_failures": carried_failures,
        "unrelated_distinct": len(unrelated_keys),
        "unrelated_attempts": 20,
        "transformations": [
            "map-table and answer-record reorder",
            "cyclic layer renumbering",
            "global affine field-coordinate relabelling",
            "composition of all three",
        ],
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _count_atoms(shipping["answer"])
    intended_operations = (
        2 * shipping["n"] * shipping["layers"]
        + 2 * (shipping["layers"] - 1)
        + 1
    )
    hinted_rate = (
        G9_ARMS["hinted"]["solved"] / G9_ARMS["hinted"]["attempts"]
        if G9_ARMS["hinted"]["attempts"]
        else 0.0
    )
    placebo_rate = (
        G9_ARMS["placebo"]["solved"] / G9_ARMS["placebo"]["attempts"]
        if G9_ARMS["placebo"]["attempts"]
        else 0.0
    )
    report["G9_no_tool_suitability"] = {
        "pass": answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300,
        "arms": G9_ARMS,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": (
            "hardened"
            if G9_ARMS["hinted"]["attempts"] and G9_ARMS["hinted"]["solved"] == 0
            else "too_easy"
            if G9_ARMS["hinted"]["attempts"]
            else "not_yet_run"
        ),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "operation_model": (
            "two arithmetic operations per anchor normalization and two per "
            "slope-product update"
        ),
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass") for key, value in report.items() if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
