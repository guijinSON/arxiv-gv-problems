"""Verified finite-field one-factor C4 generator for arXiv:1906.09291."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import re
import statistics
import time


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "After centering a row at its two matching centers, each mate map has two "
    "linear branches selected by quadratic character."
)
PLACEBO_HINT: str = (
    "Careful modular bookkeeping keeps every row's vertex labels and matching "
    "edges aligned throughout the calculation."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "pairs of one-factors of complete graphs over prime finite fields",
        "quadratic-residue strong-starter mate maps",
    ],
    "verification_operations": [
        "exact modular quadratic-character test",
        "exact one-factor edge membership",
        "four-vertex cycle closure and distinctness",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Center the two starter-generated one-factors so their involutions become "
        "piecewise-linear finite-field maps; without this coordinate change, a "
        "solver traverses the alternating-cycle decomposition row by row."
    ),
    "hardness_basis": (
        "Track B: the standard alternating-cycle traversal is O(rq) after an "
        "O(q) quadratic-residue table and, at the shipping preset, took a measured "
        "median 1.90 seconds and 18,376,459 counted operations over eight instances; "
        "the Lemma 2.1 coordinate calculation took 265 exact modular operations, but a "
        "no-tool solver must discover the branch structure and execute six "
        "large-prime character tests."
    ),
    "max_answer_tokens": 9,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {
    "demo": {"n": 19, "rows": 2, "prime_span": 1},
    "easy": {"n": 1_200_007, "rows": 6, "prime_span": 50_000},
    "medium": {"n": 2_400_019, "rows": 6, "prime_span": 100_000},
    "hard": {"n": 5_000_003, "rows": 6, "prime_span": 200_000},
}
SHIPPING_DIFFICULTY: str = "easy"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "Exactly five base-10 integers [r,v0,v1,v2,v3]: a zero-based row index "
        "and four distinct vertex labels in the stated 0..q range, cyclically "
        "ordered so the first edge belongs to factor A."
    ),
    "bounds": {
        "atomic_elements": 5,
        "row_choices_max": 8,
        "vertex_bits_max": 27,
        "ordering": "A,B,A,B around the cycle",
    },
}

NOTES: str = (
    "Section 1 fixes the native objects: a starter S_beta in the additive group "
    "of F_q and its translated one-factors. Proposition 1.4 gives the exact "
    "quadratic-residue starter, while Lemma 2.1 writes the eight branch equations "
    "that a four-cycle would satisfy. The generator reverses case (ii) of that "
    "proof: it samples beta and a first, sets the second center so the displayed "
    "four vertices close, and therefore knows the witness without cycle search. "
    "Rows satisfying Lemma 2.1 are theorem-backed C4-free decoys. Theorem 2.7 is "
    "an explicit existence construction, not a hardness theorem, and scanning its "
    "set M accepts a constant fraction of nonresidues; Track A would therefore be "
    "false. This family instead makes the paper's generic edge-following method "
    "large while retaining its short centered-coordinate route. Independent affine "
    "relabelings and row shuffles remove positional and magnitude planting signals; "
    "the measured outlier, greedy, random-restart, and infinity-component attacks "
    "all fail, while the disclosed linear-time traversal succeeds."
)


# Filled from the script-owned hardening runs.  These values are deliberately kept
# in one small block so the evidence can be updated without touching the generator.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 3},
    },
    "hinted_verdict": "hardened",
}


def _is_prime_64(value: int) -> bool:
    """Deterministic Miller--Rabin for unsigned 64-bit integers."""
    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small:
        if value % prime == 0:
            return value == prime
    d = value - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if base % value == 0:
            continue
        x = pow(base, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(s - 1):
            x = x * x % value
            if x == value - 1:
                break
        else:
            return False
    return True


def _next_prime_3_mod_4(start: int) -> int:
    value = max(19, int(start))
    value += (3 - value) % 4
    while not _is_prime_64(value):
        value += 4
    return value


def _legendre(value: int, p: int) -> int:
    value %= p
    if value == 0:
        return 0
    symbol = pow(value, (p - 1) // 2, p)
    return -1 if symbol == p - 1 else 1


def _residue_product(beta: int, p: int) -> int:
    # It has the same quadratic character as (beta^2+1)/(beta-1), because a
    # nonzero value and its inverse have the same quadratic character.
    return ((beta * beta + 1) % p) * ((beta - 1) % p) % p


def _plant_beta_ok(beta: int, p: int) -> bool:
    if beta in (0, 1, p - 1) or _legendre(beta, p) != -1:
        return False
    if _legendre(_residue_product(beta, p), p) != -1:
        return False
    if _legendre(beta - 1, p) != _legendre(2, p):
        return False
    # This makes i/a = beta(beta+1)/(beta-1) a square, so all displayed rows
    # use the same residue orientation after the affine disguise.
    coeff_character = beta * (beta + 1) * (beta - 1)
    if _legendre(coeff_character, p) != 1:
        return False
    # Excludes the separate four-cycle through infinity in Lemma 2.1.
    return pow(beta, 3, p) != p - 1


def _decoy_beta_ok(beta: int, p: int) -> bool:
    return (
        beta not in (0, 1, p - 1)
        and _legendre(beta, p) == -1
        and _legendre(_residue_product(beta, p), p) == 1
    )


def _sample_betas(p: int, rows: int, rng: random.Random):
    """Sample one reverse-Lemma plant and rows-1 Lemma-backed decoys."""
    plant = None
    decoys = []
    used_orbits = set()
    budget = max(2_000, 300 * rows)
    candidates = [rng.randrange(2, p - 1) for _ in range(budget)]
    if p <= 1_000:
        tail = list(range(2, p - 1))
        rng.shuffle(tail)
        candidates.extend(tail)
    for beta in candidates:
        orbit = min(beta, pow(beta, -1, p))
        if orbit in used_orbits:
            continue
        if plant is None and _plant_beta_ok(beta, p):
            plant = beta
            used_orbits.add(orbit)
            continue
        if len(decoys) < rows - 1 and _decoy_beta_ok(beta, p):
            decoys.append(beta)
            used_orbits.add(orbit)
        if plant is not None and len(decoys) == rows - 1:
            return plant, decoys
    return None


def _random_square(p: int, rng: random.Random) -> int:
    value = rng.randrange(1, p)
    return value * value % p


def _mate(vertex: int, center: int, beta: int, p: int) -> int:
    """The one-factor involution induced by S_beta and translated to center."""
    if vertex == p:  # p is the external encoding of infinity
        return center
    if vertex == center:
        return p
    delta = (vertex - center) % p
    multiplier = beta if _legendre(delta, p) == 1 else pow(beta, -1, p)
    return (center + multiplier * delta) % p


def _cycle_from_start(inst: dict, row_index: int, start: int) -> list[int]:
    row = inst["rows"][row_index]
    p = inst["p"]
    v0 = start
    v1 = _mate(v0, row["a"], row["beta"], p)
    v2 = _mate(v1, row["b"], row["beta"], p)
    v3 = _mate(v2, row["a"], row["beta"], p)
    return [row_index, v0, v1, v2, v3]


def make_instance(n: int, seed: int = 0, rows: int = 6,
                  prime_span: int = 50_000, **params) -> dict:
    """Construct a certified four-cycle by reversing Lemma 2.1, case (ii)."""
    del params
    if n < 19:
        raise ValueError("n must be at least 19")
    if not 2 <= rows <= 8:
        raise ValueError("rows must lie in 2..8")
    if prime_span < 1:
        raise ValueError("prime_span must be positive")
    rng = random.Random(seed)
    start = n + 4 * rng.randrange(prime_span)
    p = _next_prime_3_mod_4(start)
    sampled = None
    # A suitable beta has positive constant density. Moving to another eligible
    # prime is parameter generation, not a search for the cycle witness.
    for _ in range(64):
        sampled = _sample_betas(p, rows, rng)
        if sampled is not None:
            break
        p = _next_prime_3_mod_4(p + 4)
    if sampled is None:
        raise RuntimeError("could not sample the starter parameters")
    plant_beta, decoy_betas = sampled

    public_rows = []
    for beta in decoy_betas:
        center_a = rng.randrange(p)
        difference = _random_square(p, rng)
        public_rows.append({
            "a": center_a,
            "b": (center_a + difference) % p,
            "beta": beta,
            "is_plant": False,
        })

    # Reverse case (ii) in the proof of Lemma 2.1.  Choosing a first and setting
    # i=a*beta*(beta+1)/(beta-1) makes the four displayed vertices close.
    beta = plant_beta
    a = _random_square(p, rng)
    coefficient = beta * (beta + 1) * pow(beta - 1, -1, p) % p
    i = a * coefficient % p
    v0 = a
    v1 = a * beta % p
    v2 = ((v1 - i) * beta + i) % p
    v3 = ((a - i) * beta + i) % p

    scale = _random_square(p, rng)
    shift = rng.randrange(p)
    plant_row = {
        "a": shift,
        "b": (shift + scale * i) % p,
        "beta": beta,
        "is_plant": True,
    }
    planted_vertices = [(shift + scale * value) % p for value in (v0, v1, v2, v3)]
    public_rows.append(plant_row)
    rng.shuffle(public_rows)
    plant_index = next(index for index, row in enumerate(public_rows) if row["is_plant"])
    for row in public_rows:
        del row["is_plant"]

    answer = [plant_index] + planted_vertices
    inst = {"p": p, "rows": public_rows, "answer": answer}
    ok, reason = verify(inst, answer)
    if not ok:
        raise AssertionError("construction error: " + reason)
    return inst


def render(inst: dict) -> str:
    p = inst["p"]
    lines = [
        "FOUR-CYCLE IN FINITE-FIELD ONE-FACTORS",
        "",
        f"Work in the prime field F_{p}, represented by 0,...,{p - 1}, with all",
        "finite arithmetic reduced modulo p. A nonzero field element x is a",
        "quadratic residue when x=y^2 for some nonzero y; otherwise it is a",
        "quadratic nonresidue. The extra vertex infinity is encoded by the integer",
        f"p itself, namely {p}. Thus every vertex label is an integer in 0..{p}.",
        "",
        "Each input row is an independent labeled copy of this vertex set and",
        "defines two one-factors (perfect matchings), A and B. For a center c and",
        "the row's nonresidue beta, define mate(c,x) as follows:",
        "  * mate(c,infinity)=c and mate(c,c)=infinity;",
        "  * otherwise put d=x-c modulo p. If d is a quadratic residue,",
        "    mate(c,x)=c+beta*d; if d is a nonresidue,",
        "    mate(c,x)=c+beta^(-1)*d, always modulo p.",
        "Factor A joins every x to mate(center_A,x), and factor B uses center_B.",
        "The formula is involutive, so each undirected edge is listed twice by the",
        "mate map but belongs only once to the matching.",
        "",
        "Exactly one row is promised to contain a four-cycle in A union B. Find any",
        "such cycle. If your answer is [r,v0,v1,v2,v3], the five integers must obey",
        "mate(A,v0)=v1, mate(B,v1)=v2, mate(A,v2)=v3, mate(B,v3)=v0, and the four",
        "vertices must be distinct. Rows are 0-based; order and orientation matter",
        "only through this stated A,B,A,B convention. No repeated vertex is allowed.",
        "",
        "Rows (row center_A center_B beta):",
    ]
    for index, row in enumerate(inst["rows"]):
        lines.append(f"  {index} {row['a']} {row['b']} {row['beta']}")
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags as one JSON list of",
        "exactly five base-10 integers [r,v0,v1,v2,v3].",
        f"Example format: <answer>[0, 0, 1, 2, {p}]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str):
    if not isinstance(text, str):
        return None
    tagged = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
    bodies = tagged if tagged else re.findall(r"\[[^\[\]]*\]", text, re.S)
    for body in reversed(bodies):
        candidate = body.strip()
        if not candidate.startswith("["):
            candidate = "[" + candidate + "]"
        try:
            value = json.loads(candidate)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if (
            isinstance(value, list)
            and len(value) == 5
            and all(isinstance(x, int) and not isinstance(x, bool) for x in value)
        ):
            return value
    return None


def verify(inst: dict, answer) -> tuple[bool, str]:
    if answer == [] or answer == "":
        return False, "answer is empty"
    if not isinstance(answer, list) or len(answer) != 5:
        return False, "answer must contain exactly five integers"
    if not all(isinstance(x, int) and not isinstance(x, bool) for x in answer):
        return False, "every answer entry must be an integer"
    row_index, v0, v1, v2, v3 = answer
    if not 0 <= row_index < len(inst.get("rows", [])):
        return False, "row index is outside the displayed range"
    p = inst.get("p")
    if not isinstance(p, int) or p < 3:
        return False, "instance modulus is malformed"
    vertices = [v0, v1, v2, v3]
    if any(vertex < 0 or vertex > p for vertex in vertices):
        return False, "a vertex label is outside 0..p"
    if len(set(vertices)) != 4:
        return False, "cycle vertices must be distinct"
    row = inst["rows"][row_index]
    beta = row["beta"]
    if _mate(v0, row["a"], beta, p) != v1:
        return False, "vertices 0-1 are not an edge of factor A"
    if _mate(v1, row["b"], beta, p) != v2:
        return False, "vertices 1-2 are not an edge of factor B"
    if _mate(v2, row["a"], beta, p) != v3:
        return False, "vertices 2-3 are not an edge of factor A"
    if _mate(v3, row["b"], beta, p) != v0:
        return False, "vertices 3-0 are not an edge of factor B"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random):
    row_index = rng.randrange(len(inst["rows"]))
    start = rng.randrange(inst["p"] + 1)
    return _cycle_from_start(inst, row_index, start)


def search_space(inst: dict) -> int:
    # Once row and v0 are chosen, the three displayed matching equations force
    # v1,v2,v3. This is the structure-aware space, not all ordered quadruples.
    return len(inst["rows"]) * (inst["p"] + 1)


def enumerate_all(inst: dict):
    if search_space(inst) > 100_000:
        return None
    count = 0
    for row_index in range(len(inst["rows"])):
        for start in range(inst["p"] + 1):
            if verify(inst, _cycle_from_start(inst, row_index, start))[0]:
                count += 1
    return count


def _paper_case_cycles(inst: dict):
    """Enumerate C4s via the eight sign cases exhausted in Lemma 2.1's proof."""
    p = inst["p"]
    found = set()
    for row_index, row in enumerate(inst["rows"]):
        difference = (row["b"] - row["a"]) % p
        beta = row["beta"]
        if _legendre(difference, p) == -1:
            beta = pow(beta, -1, p)
        for t1 in (-1, 1):
            for t2 in (-1, 1):
                for t3 in (-1, 1):
                    a_coefficient = (
                        pow(beta, t1 + 1, p) - pow(beta, t2 + t3, p)
                    ) % p
                    constant = (
                        pow(beta, t2 + t3, p)
                        - pow(beta, t3, p)
                        - pow(beta, t1, p)
                        + 1
                    ) % p
                    if a_coefficient == 0:
                        continue
                    a = -constant * pow(a_coefficient, -1, p) % p
                    v0 = a
                    v1 = a * beta % p
                    v2 = ((v1 - 1) * pow(beta, t1, p) + 1) % p
                    v3 = ((a - 1) * pow(beta, t2, p) + 1) % p
                    vertices = [
                        (row["a"] + difference * value) % p
                        for value in (v0, v1, v2, v3)
                    ]
                    candidate = [row_index] + vertices
                    if verify(inst, candidate)[0]:
                        found.add((row_index, tuple(sorted(vertices))))
        infinity_candidate = _cycle_from_start(inst, row_index, p)
        if verify(inst, infinity_candidate)[0]:
            found.add((row_index, tuple(sorted(infinity_candidate[1:]))))
    return found


def canonical_key(inst: dict) -> str:
    # Each row is an independent copy. Affine relabeling is transitive on its two
    # distinct centers; a nonsquare scale replaces beta by beta^-1. Hence the exact
    # row orbit is represented by min(beta,beta^-1), and rows may be reordered.
    p = inst["p"]
    row_orbits = sorted(min(row["beta"], pow(row["beta"], -1, p)) for row in inst["rows"])
    structural = json.dumps([p, row_orbits], separators=(",", ":"))
    return hashlib.sha256(structural.encode("ascii")).hexdigest()


def escalate(params: dict):
    current = {key: value for key, value in params.items() if key != "_preset"}
    n = int(current.get("n", DIFFICULTY["hard"]["n"]))
    rows = int(current.get("rows", DIFFICULTY["hard"]["rows"]))
    span = int(current.get("prime_span", DIFFICULTY["hard"]["prime_span"]))
    current["n"] = n * (2 if rows < 7 else 4)
    current["prime_span"] = span * 2
    if rows < 7:
        current["rows"] = rows + 1
    else:
        current["rows"] = rows
    # The fixed five-integer witness never approaches the answer cap. The rows
    # stop at seven so the centered route remains within G9's arithmetic cap.
    return current


def _pow_multiplications(exponent: int) -> int:
    if exponent <= 1:
        return 0
    return exponent.bit_length() - 1 + exponent.bit_count() - 1


def _compact_solve(inst: dict):
    """Paper-derived centered-coordinate route, never reading inst['answer']."""
    p = inst["p"]
    operations = 0
    target = None
    legendre_cost = _pow_multiplications((p - 1) // 2)
    inverse_cost = _pow_multiplications(p - 2)
    for index, row in enumerate(inst["rows"]):
        beta = row["beta"]
        product = _residue_product(beta, p)
        operations += 4 + legendre_cost
        if _legendre(product, p) == -1:
            if target is not None:
                return None, {"exact_operations": operations, "reason": "ambiguous row"}
            target = index
    if target is None:
        return None, {"exact_operations": operations, "reason": "no candidate row"}
    row = inst["rows"][target]
    difference = (row["b"] - row["a"]) % p
    operations += 1 + legendre_cost
    beta = row["beta"]
    if _legendre(difference, p) == -1:
        beta = pow(beta, -1, p)
        operations += inverse_cost
    denominator = beta * (beta + 1) % p
    normalized_a = (beta - 1) * pow(denominator, -1, p) % p
    operations += 4 + inverse_cost
    v0 = normalized_a
    v1 = v0 * beta % p
    v2 = ((v1 - 1) * beta + 1) % p
    v3 = ((v0 - 1) * beta + 1) % p
    operations += 7
    vertices = [(row["a"] + difference * value) % p for value in (v0, v1, v2, v3)]
    operations += 8
    return [target] + vertices, {
        "exact_operations": operations,
        "legendre_multiplications": legendre_cost,
        "inverse_multiplications": inverse_cost,
    }


def _qr_table(p: int):
    table = bytearray(p)
    for value in range(1, (p + 1) // 2):
        table[value * value % p] = 1
    return table


def _mate_fast(vertex: int, center: int, beta: int, beta_inv: int,
               p: int, qr_table: bytearray) -> int:
    if vertex == p:
        return center
    if vertex == center:
        return p
    delta = (vertex - center) % p
    multiplier = beta if qr_table[delta] else beta_inv
    return (center + multiplier * delta) % p


def _reference_traversal(inst: dict):
    """Standard O(rq) alternating-cycle decomposition."""
    p = inst["p"]
    qr_table = _qr_table(p)
    partner_steps = 0
    vertices_started = 0
    for row_index, row in enumerate(inst["rows"]):
        seen = bytearray(p + 1)
        beta = row["beta"]
        beta_inv = pow(beta, -1, p)
        for start in range(p + 1):
            if seen[start]:
                continue
            vertices_started += 1
            component = []
            current = start
            use_a = True
            while not seen[current]:
                seen[current] = 1
                component.append(current)
                center = row["a"] if use_a else row["b"]
                current = _mate_fast(current, center, beta, beta_inv, p, qr_table)
                partner_steps += 1
                use_a = not use_a
            if len(component) == 4 and current == start and use_a:
                candidate = [row_index] + component
                if verify(inst, candidate)[0]:
                    return candidate, {
                        "residue_table_squarings": (p - 1) // 2,
                        "partner_steps": partner_steps,
                        "components_started": vertices_started,
                        "operations": (p - 1) // 2 + 4 * partner_steps,
                    }
    return None, {
        "residue_table_squarings": (p - 1) // 2,
        "partner_steps": partner_steps,
        "components_started": vertices_started,
        "operations": (p - 1) // 2 + 4 * partner_steps,
    }


def _attack_outlier(inst: dict):
    p = inst["p"]
    index = max(range(len(inst["rows"])), key=lambda j: abs(inst["rows"][j]["beta"] - p // 2))
    return _cycle_from_start(inst, index, inst["rows"][index]["a"])


def _attack_greedy(inst: dict):
    p = inst["p"]
    index = min(
        range(len(inst["rows"])),
        key=lambda j: min(
            (inst["rows"][j]["b"] - inst["rows"][j]["a"]) % p,
            (inst["rows"][j]["a"] - inst["rows"][j]["b"]) % p,
        ),
    )
    start = min(inst["rows"][index]["a"], inst["rows"][index]["b"])
    return _cycle_from_start(inst, index, start)


def _attack_infinity_component(inst: dict):
    for index in range(len(inst["rows"])):
        candidate = _cycle_from_start(inst, index, inst["p"])
        if verify(inst, candidate)[0]:
            return candidate
    return _cycle_from_start(inst, 0, inst["p"])


def _attack_midpoint_ansatz(inst: dict):
    p = inst["p"]
    inv2 = (p + 1) // 2
    for index, row in enumerate(inst["rows"]):
        midpoint = (row["a"] + row["b"]) * inv2 % p
        candidate = _cycle_from_start(inst, index, midpoint)
        if verify(inst, candidate)[0]:
            return candidate
    return _cycle_from_start(inst, 0, 0)


def _attack_random(inst: dict, rng: random.Random, restarts: int = 4096):
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return _cycle_from_start(inst, 0, inst["rows"][0]["a"])


def _transform_instance(inst: dict, rng: random.Random):
    """Independent affine row relabelings, factor swaps, and row reordering."""
    p = inst["p"]
    original_answer = inst["answer"]
    plant_old = original_answer[0]
    transformed_rows = []
    row_maps = []
    swaps = []
    for row in inst["rows"]:
        scale = rng.randrange(1, p)
        shift = rng.randrange(p)
        beta = row["beta"] if _legendre(scale, p) == 1 else pow(row["beta"], -1, p)
        new_row = {
            "a": (scale * row["a"] + shift) % p,
            "b": (scale * row["b"] + shift) % p,
            "beta": beta,
        }
        swap = bool(rng.randrange(2))
        if swap:
            new_row["a"], new_row["b"] = new_row["b"], new_row["a"]
        transformed_rows.append(new_row)
        row_maps.append((scale, shift))
        swaps.append(swap)
    vertices = [p if value == p else (row_maps[plant_old][0] * value + row_maps[plant_old][1]) % p
                for value in original_answer[1:]]
    if swaps[plant_old]:
        vertices = vertices[1:] + vertices[:1]
    order = list(range(len(transformed_rows)))
    rng.shuffle(order)
    new_rows = [transformed_rows[old] for old in order]
    new_plant = order.index(plant_old)
    return {"p": p, "rows": new_rows, "answer": [new_plant] + vertices}


def _answer_size(answer):
    encoded = json.dumps(answer, separators=(",", ":"))
    return {
        "chars": len(encoded),
        "tokens": math.ceil(len(encoded) / 4),
        "elements": len(answer),
    }


def selftest() -> dict:
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    failures = []
    json_roundtrips = 0
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            checks += 1
            if not ok:
                failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_roundtrips += 1
    report["G1_planted_verifies"] = {
        "pass": not failures and json_roundtrips == checks,
        "attempts": checks,
        "json_roundtrips": json_roundtrips,
        "failures": failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=90_291, **ship_params)
    answer = inst["answer"]
    swapped = answer[:]
    swapped[2], swapped[3] = swapped[3], swapped[2]
    corruptions = {
        "empty": [],
        "drop_one": answer[:-1],
        "duplicate": [answer[0], answer[1], answer[1], answer[3], answer[4]],
        "out_of_range": [answer[0], inst["p"] + 1] + answer[2:],
        "swap_two": swapped,
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in cases.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in cases.values())
        and len(set(reasons)) == len(reasons),
        "cases": cases,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "The centered involutions give the following cycle.\n\n```json\n"
        "<answer>" + json.dumps(answer) + "</answer>\n```\n"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("no cycle supplied") is None,
        "realistic_response_round_trip": parsed == answer,
        "garbage_returns_none": parse_answer("no cycle supplied") is None,
        "parsed": parsed,
    }

    samples = 200_000
    guess_rng = random.Random(0x190609291)
    hits = 0
    density_start = time.perf_counter()
    for _ in range(samples):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    density_wall = time.perf_counter() - density_start
    case_cycles = _paper_case_cycles(inst)
    exact_valid_answers = 4 * len(case_cycles)
    exact_probability = exact_valid_answers / search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6 and exact_probability < 1e-6 and len(case_cycles) == 1,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "exact_probability": exact_probability,
        "exact_valid_ordered_answers": exact_valid_answers,
        "paper_case_exhaustion_cycles": len(case_cycles),
        "structure_aware_space": search_space(inst),
        "sampler": "uniform row and start vertex; the first three alternating edges are forced",
        "wall_clock_sec": round(density_wall, 6),
    }

    baseline_rng = random.Random(11_358)
    baseline_start = time.perf_counter()
    baseline_candidate = _attack_random(inst, baseline_rng, restarts=4096)
    baseline_wall = time.perf_counter() - baseline_start
    baseline_success = verify(inst, baseline_candidate)[0]
    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": exact_probability < 1e-6 and not baseline_success and demo_count is not None,
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_sampled_valid_fraction": hits / samples,
        "shipping_exact_valid_fraction": exact_probability,
        "shipping_exact_valid_ordered_answers": exact_valid_answers,
        "demo_exact_valid_ordered_answers": demo_count,
        "strongest_failing_attack_wall_seconds": round(baseline_wall, 6),
        "strongest_failing_attack_restarts": 4096,
    }

    attack_results = {
        "outlier_beta_magnitude": {"successes": 0, "attempts": 0},
        "greedy_smallest_center_gap": {"successes": 0, "attempts": 0},
        "random_restart_4096": {"successes": 0, "attempts": 0},
        "in_context_infinity_component": {"successes": 0, "attempts": 0},
        "in_context_midpoint_ansatz": {"successes": 0, "attempts": 0},
    }
    reference_successes = 0
    reference_times = []
    reference_operations = []
    reference_steps = []
    compact_successes = 0
    compact_times = []
    compact_operations = []
    for seed in range(3100, 3108):
        attacked = make_instance(seed=seed, **ship_params)
        candidates = {
            "outlier_beta_magnitude": _attack_outlier(attacked),
            "greedy_smallest_center_gap": _attack_greedy(attacked),
            "random_restart_4096": _attack_random(
                attacked, random.Random(seed ^ 0xA5A5), restarts=4096
            ),
            "in_context_infinity_component": _attack_infinity_component(attacked),
            "in_context_midpoint_ansatz": _attack_midpoint_ansatz(attacked),
        }
        for name, candidate in candidates.items():
            attack_results[name]["attempts"] += 1
            if verify(attacked, candidate)[0]:
                attack_results[name]["successes"] += 1

        start = time.perf_counter()
        reference_answer, stats = _reference_traversal(attacked)
        reference_times.append(time.perf_counter() - start)
        reference_operations.append(stats["operations"])
        reference_steps.append(stats["partner_steps"])
        if reference_answer is not None and verify(attacked, reference_answer)[0]:
            reference_successes += 1

        start = time.perf_counter()
        compact_answer, compact_stats = _compact_solve(attacked)
        compact_times.append(time.perf_counter() - start)
        compact_operations.append(compact_stats["exact_operations"])
        if compact_answer is not None and verify(attacked, compact_answer)[0]:
            compact_successes += 1

    all_attacks_failed = all(entry["successes"] == 0 for entry in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "quadratic-residue table plus alternating-cycle traversal",
            "complexity": "O(q+r*q) exact operations and O(q) memory",
            "median_wall_clock_sec": round(statistics.median(reference_times), 6),
            "operations": int(statistics.median(reference_operations)),
            "median_operations": int(statistics.median(reference_operations)),
            "median_partner_steps": int(statistics.median(reference_steps)),
            "operation_definition": "one residue-table square or four primitive modular operations per mate step",
            "solves": f"{reference_successes}/8, as expected",
        },
        "compact_route": {
            "name": "Lemma 2.1 centered branch equation",
            "complexity": "O(r log q) modular multiplications by binary exponentiation",
            "median_wall_clock_sec": round(statistics.median(compact_times), 8),
            "operations": int(statistics.median(compact_operations)),
            "median_operations": int(statistics.median(compact_operations)),
            "operation_definition": "modular adds/multiplies, counting every binary-power square and multiply",
            "solves": f"{compact_successes}/8, as expected",
        },
    }

    doubled = make_instance(
        n=2 * ship_params["n"], rows=ship_params["rows"],
        prime_span=ship_params["prime_span"], seed=77,
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    escalated = escalate(ship_params)
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["p"] > inst["p"] and search_space(doubled) > search_space(inst),
        "shipping_prime": inst["p"],
        "doubled_prime": doubled["p"],
        "shipping_structure_aware_space": search_space(inst),
        "doubled_structure_aware_space": search_space(doubled),
        "doubled_verify_reason": doubled_reason,
        "next_parameters": escalated,
    }

    invariance_checks = 0
    witness_checks = 0
    invariant_failures = []
    distinct_keys = []
    for seed in range(20):
        original = make_instance(seed=7000 + seed, **DIFFICULTY["easy"])
        original_key = canonical_key(original)
        distinct_keys.append(original_key)
        variant = copy.deepcopy(original)
        for round_index in range(4):
            variant = _transform_instance(variant, random.Random(80_000 + 17 * seed + round_index))
            invariance_checks += 1
            if canonical_key(variant) != original_key:
                invariant_failures.append([seed, round_index, "key changed"])
            witness_checks += 1
            ok, reason = verify(variant, variant["answer"])
            if not ok:
                invariant_failures.append([seed, round_index, "carried witness: " + reason])
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and len(set(distinct_keys)) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": witness_checks,
        "distinct_unrelated_keys": len(set(distinct_keys)),
        "unrelated_instances": 20,
        "failures": invariant_failures,
        "symmetries": "independent affine row relabelings, A/B swaps, row permutations, and compositions",
        "key_basis": "prime and sorted beta-orbits under inversion; never seed or rendered text",
    }

    size_measurements = [_answer_size(answer)]
    for seed in range(200):
        measured = make_instance(seed=90_000 + seed, **ship_params)
        size_measurements.append(_answer_size(measured["answer"]))
    size = {
        key: max(measurement[key] for measurement in size_measurements)
        for key in ("chars", "tokens", "elements")
    }
    arms = copy.deepcopy(G9_RESULTS["arms"])
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = arms["hinted"]["solved"] / hinted_attempts if hinted_attempts else 0.0
    placebo_rate = arms["placebo"]["solved"] / placebo_attempts if placebo_attempts else 0.0
    intended_operations = int(statistics.median(compact_operations))
    hinted_hardened = G9_RESULTS["hinted_verdict"] == "hardened"
    within_caps = (
        size["chars"] <= 2000
        and size["elements"] <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": size["chars"],
        "answer_tokens": size["tokens"],
        "answer_elements": size["elements"],
        "answer_measurement_instances": len(size_measurements),
        "intended_route_operations": intended_operations,
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
