"""Verified problem generator for arXiv:2112.03442.

The solver is given a succinct binary-action polymatrix game and must return a
compact, exact description of a full-support mixed Nash equilibrium.  The
indifference equations are two disguised Walsh--Hadamard systems.  Generation
is inverse: choose the sparse centred probabilities first, then form the
forcing terms by an exact Hadamard transform.  No instance is solved in order
to manufacture its certificate.
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
import sys
import time


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # pragma: no cover - no helper is needed by this module
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "optimization",
    "object_regime": "rational_exact",
    "computational_core": "linear_algebra",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "binary-action polymatrix game with rational payoffs",
        "product mixed-strategy profile",
        "sparse exact description of centred mixing probabilities",
    ],
    "verification_operations": [
        "exact integer Walsh-character evaluation",
        "exact rational expected-payoff comparison",
        "full-support probability check",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "The indifference equations become signed superincreasing codes after "
        "undoing a rank-one binary shear; without that change of variables one "
        "must invert two long Walsh--Hadamard systems."
    ),
    "hardness_basis": (
        "Track B: fast Walsh--Hadamard inversion solves this distribution in "
        "O(n log n); at the shipping preset it uses 24,576 counted exact/bit "
        "operations and averaged 0.011136 seconds over eight measured runs, whereas the signed-code "
        "and rank-one-shear route uses at most 165 exact arithmetic/bit operations."
    ),
    "max_answer_tokens": 41,
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
    "demo": {"n": 4, "sparsity": 2, "scale_max": 3},
    "easy": {"n": 64, "sparsity": 4, "scale_max": 3},
    "medium": {"n": 256, "sparsity": 4, "scale_max": 5},
    "hard": {"n": 1024, "sparsity": 4, "scale_max": 7},
}
SHIPPING_DIFFICULTY = "hard"

# Scratch G9 runs set this only on a copied module.  Normal imports retain the
# required four-rung ladder and the emitted problem never contains a hint.
if os.environ.get("GV_G9_SINGLE_PRESET") == "1":
    DIFFICULTY = {SHIPPING_DIFFICULTY: dict(DIFFICULTY[SHIPPING_DIFFICULTY])}


STRUCTURAL_HINT = (
    "The forcing values are signed superincreasing codes viewed through a "
    "rank-one binary shear of Walsh characters."
)
PLACEBO_HINT = (
    "Keep the player identifiers and the displayed binary labels aligned "
    "while checking the rational expressions."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object with keys left and right.  Each value is a list of s "
        "[player_id, [signed_numerator, denominator]] terms. IDs are distinct "
        "within a side; the absolute signed numerators use each displayed superincreasing "
        "weight exactly once.  All omitted players have centred latent mixing "
        "probability zero, and the common denominator is displayed in the "
        "instance."
    ),
    "bounds": {
        "max_players_per_side": 1048576,
        "max_sparsity_per_side": 16,
        "max_weight": 1048576,
        "max_atomic_elements": 64,
    },
}

NOTES = (
    "Section 2 (Definitions 2.1--2.4) fixes polymatrix payoffs, L-smoothness, "
    "mixed Nash equilibrium, and epsilon-approximation; those native rational "
    "objects are used directly here. Theorem 2.1 and Section 4, especially "
    "Lemma 4.1, rule out Track A on the paper's dense random regime by giving "
    "a deterministic (Nk)^{O(L^4 log(k)/epsilon^4)} convex-hierarchy/ellipsoid "
    "algorithm. Section 3 also records the polynomial-time zero-sum case. For "
    "this generated distribution an even faster O(n log n) Walsh--Hadamard "
    "algorithm exists and is reported openly as the Track-B reference. The "
    "generator instead samples the sparse full-support equilibrium first and "
    "composes exact Hadamard identities to form the game. Random player/code "
    "assignments, public-action flips, row scales, shear, weights, and signs "
    "remove position and magnitude planting leaks. G6 tests a per-player "
    "outlier rule, a uniform-profile greedy rule, random restarts, and the "
    "obvious but wrong identity-matrix ansatz; the successful transform "
    "algorithm is kept outside attacks as Track B requires."
)

# Replaced after the three isolated oracle runs.  These values are diagnostics,
# not self-reported hardness evidence.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _validate_params(n, sparsity, scale_max):
    if not all(_is_int(x) for x in (n, sparsity, scale_max)):
        raise ValueError("n, sparsity, and scale_max must be integers")
    if n < 4 or n > CERTIFICATE_LANGUAGE["bounds"]["max_players_per_side"]:
        raise ValueError("n is outside the certificate-language bound")
    if n & (n - 1):
        raise ValueError("n must be a power of two")
    if not (2 <= sparsity <= min(n, CERTIFICATE_LANGUAGE["bounds"]["max_sparsity_per_side"])):
        raise ValueError("sparsity is outside the supported range")
    if not (1 <= scale_max <= 7):
        raise ValueError("scale_max must lie in 1..7")


def _parity(x):
    return x.bit_count() & 1


def _matvec(rows, x):
    """M*x over GF(2), with each integer in rows storing one binary row."""
    out = 0
    for k, row in enumerate(rows):
        if _parity(row & x):
            out |= 1 << k
    return out


def _transpose_matvec(rows, x):
    """M^T*x over GF(2), represented as an xor of selected rows."""
    out = 0
    bit = 0
    while x:
        if x & 1:
            out ^= rows[bit]
        bit += 1
        x >>= 1
    return out


def _chi(rows, r, c):
    return -1 if _parity(r & _matvec(rows, c)) else 1


def _make_shear(d, rng):
    """Return M=I+u*v^T with v.u=0, hence M^{-1}=M over GF(2)."""
    limit = 1 << d
    while True:
        u = rng.randrange(1, limit)
        v = rng.randrange(1, limit)
        if not _parity(u & v):
            rows = [((1 << k) ^ (v if ((u >> k) & 1) else 0)) for k in range(d)]
            if any(rows[k] != (1 << k) for k in range(d)):
                return rows


def _make_weights(sparsity, rng):
    weights = [rng.randint(1, 5)]
    total = weights[0]
    for _ in range(1, sparsity):
        nxt = total + rng.randint(1, 5)
        weights.append(nxt)
        total += nxt
    return weights


def _group_records(side, start_id, n, d, scale_max, rng):
    codes = list(range(n))
    rng.shuffle(codes)
    records = []
    for offset in range(n):
        records.append(
            {
                "id": start_id + offset,
                "code": codes[offset],
                "flip": rng.randrange(2),
                "scale": rng.randint(1, scale_max),
                "force": 0,
            }
        )
    rng.shuffle(records)
    return records


def _sample_terms(records, weights, denominator, rows, rng):
    # Condition away the one case that lets the explicit identity-matrix ansatz
    # recover every selected code.  This is a distributional hardening step, not
    # a solve: it only evaluates the sampled shear on sampled labels.
    for _ in range(1000):
        chosen = rng.sample(records, len(weights))
        rng.shuffle(chosen)
        terms = []
        moved = False
        for rec, weight in zip(chosen, weights):
            signed = weight if rng.randrange(2) else -weight
            terms.append([rec["id"], [signed, denominator]])
            moved = moved or (_matvec(rows, rec["code"]) != rec["code"])
        if moved:
            return sorted(terms)
    raise RuntimeError("could not sample a nontrivial sheared support")


def _term_codes(records, terms):
    by_id = {r["id"]: r for r in records}
    return [(by_id[pid]["code"], rational[0]) for pid, rational in terms]


def _fill_forces(equation_records, target_code_terms, rows):
    for rec in equation_records:
        raw = sum(_chi(rows, rec["code"], code) * signed for code, signed in target_code_terms)
        rec["force"] = rec["scale"] * raw


def make_instance(n, seed=0, sparsity=4, scale_max=7):
    """Inverse-generate a native polymatrix game and its exact equilibrium."""
    _validate_params(n, sparsity, scale_max)
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    d = n.bit_length() - 1
    rows = _make_shear(d, rng)
    weights = _make_weights(sparsity, rng)
    denominator = 2 * weights[-1] + 1

    left = _group_records("left", 1, n, d, scale_max, rng)
    right = _group_records("right", n + 1, n, d, scale_max, rng)
    left_terms = _sample_terms(left, weights, denominator, rows, rng)
    right_terms = _sample_terms(right, weights, denominator, rows, rng)

    _fill_forces(left, _term_codes(right, right_terms), rows)
    _fill_forces(right, _term_codes(left, left_terms), rows)
    left.sort(key=lambda r: r["id"])
    right.sort(key=lambda r: r["id"])

    return {
        "n": n,
        "dimension": d,
        "sparsity": sparsity,
        "scale_max": scale_max,
        "weights": list(weights),
        "denominator": denominator,
        "matrix_rows": list(rows),
        "groups": {"left": left, "right": right},
        "standard_ids": True,
        "answer": {"left": left_terms, "right": right_terms},
    }


def _bits(x, d):
    return format(x, f"0{d}b")


def render(inst):
    n = inst["n"]
    d = inst["dimension"]
    s = inst["sparsity"]
    W = inst["denominator"]
    lines = [
        "EXACT MIXED NASH EQUILIBRIUM IN A SUCCINCT POLYMATRIX GAME",
        "",
        f"There are {2*n} players, split into LEFT and RIGHT groups of {n}.",
        "Each player has public actions 0 and 1. Every LEFT player interacts",
        "once with every RIGHT player; there are no same-group interactions.",
        "Payoffs add over all of a player's pairwise interactions.",
        "",
        "Each player record is: id  binary_code  flip  positive_scale  force.",
        f"Codes have {d} bits. The rightmost printed bit is coordinate 0.",
        "For a public action a, define its latent action z = a XOR flip.",
        "All binary matrix/vector arithmetic below is over GF(2).",
        "The matrix M is given by its rows (again coordinate 0 is rightmost):",
    ]
    lines.extend(f"  M[{k}] = {_bits(row, d)}" for k, row in enumerate(inst["matrix_rows"]))
    lines.extend(
        [
            "",
            "For binary codes r,c, define chi(r,c)=(-1)^(r dot (M c)).",
            "For an ordered interaction from player i to opposite-side player j,",
            "the payoff received by i is exactly",
            "",
            "  f_ij(a_i,a_j) = 1/(4n) + z_i/(64n) *",
            "      [scale_i*chi(code_i,code_j)*(2z_j-1) - force_i/(W*n)].",
            "",
            f"Here n={n} and W={W}. These rational payoffs lie in [0,1/n],",
            "so the game is 1-smooth in the paper's normalization.",
            "",
            "A mixed strategy profile is a product distribution: players randomize",
            "independently. It is a Nash equilibrium when no player can increase",
            "expected payoff by replacing its random action with fixed action 0 or 1.",
            "",
            "PROMISED CERTIFICATE LANGUAGE",
            f"There is a full-support equilibrium in which, for each side, exactly {s}",
            "players have nonzero centred latent probability",
            "",
            "  t_i = 2*P(z_i=1)-1 = signed_numerator/W.",
            "",
            "Every omitted player has t_i=0. Within each side the absolute numerators",
            f"must use each weight exactly once: {inst['weights']}. Signs are free.",
            "All resulting probabilities are strictly between 0 and 1.",
            "",
            "LEFT records:",
        ]
    )
    for rec in inst["groups"]["left"]:
        lines.append(
            f"  {rec['id']} {_bits(rec['code'], d)} {rec['flip']} "
            f"{rec['scale']} {rec['force']}"
        )
    lines.append("")
    lines.append("RIGHT records:")
    for rec in inst["groups"]["right"]:
        lines.append(
            f"  {rec['id']} {_bits(rec['code'], d)} {rec['flip']} "
            f"{rec['scale']} {rec['force']}"
        )

    fake_left = [
        [i + 1, [w if i % 2 == 0 else -w, W]]
        for i, w in enumerate(inst["weights"])
    ]
    fake_right = [
        [n + i + 1, [-w if i % 2 == 0 else w, W]]
        for i, w in enumerate(inst["weights"])
    ]
    example = json.dumps({"left": fake_left, "right": fake_right}, separators=(",", ":"))
    lines.extend(
        [
            "",
            "Return exactly one certificate. Pair order is irrelevant; player IDs are",
            "the displayed 1-based IDs, cannot repeat within a side, and must belong",
            "to that side. Every rational must be the exact JSON pair [num,den]",
            "with den=W; do not use decimals or an implicit denominator.",
            "Give your final answer inside <answer></answer> tags as compact JSON:",
            f"Example: <answer>{example}</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, flags=re.I | re.S)
    candidates = list(reversed(matches))
    if not candidates:
        fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.I | re.S)
        candidates.extend(reversed(fenced))
    for raw in candidates:
        try:
            value = json.loads(raw.strip())
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, dict):
            return value
    return None


def _validate_answer_shape(inst, answer):
    if not isinstance(answer, dict) or set(answer) != {"left", "right"}:
        return False, "answer must be an object with exactly keys left and right", None
    parsed = {}
    weights = sorted(inst["weights"])
    for side in ("left", "right"):
        terms = answer[side]
        if not isinstance(terms, list):
            return False, f"{side} must be a list", None
        if len(terms) != inst["sparsity"]:
            return False, f"{side} must contain exactly {inst['sparsity']} terms (got {len(terms)})", None
        if inst.get("standard_ids"):
            low, high = ((1, inst["n"]) if side == "left" else (inst["n"] + 1, 2 * inst["n"]))
            allowed = None
        else:
            allowed = {r["id"] for r in inst["groups"][side]}
        clean = []
        for pos, term in enumerate(terms):
            if (
                not isinstance(term, list)
                or len(term) != 2
                or not _is_int(term[0])
                or not isinstance(term[1], list)
                or len(term[1]) != 2
                or not all(_is_int(x) for x in term[1])
            ):
                return False, f"{side} term {pos} must be [integer player_id, [integer numerator, integer denominator]]", None
            pid, rational = term
            signed, denominator = rational
            if denominator != inst["denominator"]:
                return False, f"{side} term {pos} denominator must equal W={inst['denominator']}", None
            if (allowed is None and not (low <= pid <= high)) or (allowed is not None and pid not in allowed):
                return False, f"{side} term {pos} uses player {pid} outside the {side} group", None
            clean.append((pid, signed))
        ids = [pid for pid, _ in clean]
        if len(set(ids)) != len(ids):
            return False, f"{side} player IDs must be distinct", None
        got_weights = sorted(abs(signed) for _, signed in clean)
        if got_weights != weights:
            return False, f"{side} signed numerators must use absolute weights {weights}", None
        if any(abs(signed) >= inst["denominator"] for _, signed in clean):
            return False, f"{side} creates a probability outside strict (0,1)", None
        parsed[side] = clean
    return True, "ok", parsed


def verify(inst, answer):
    ok, why, parsed = _validate_answer_shape(inst, answer)
    if not ok:
        return False, why
    rows = inst["matrix_rows"]
    if inst.get("standard_ids"):
        by_side = {
            "left": {pid: inst["groups"]["left"][pid - 1] for pid, _ in parsed["left"]},
            "right": {pid: inst["groups"]["right"][pid - inst["n"] - 1] for pid, _ in parsed["right"]},
        }
    else:
        by_side = {
            side: {r["id"]: r for r in inst["groups"][side]}
            for side in ("left", "right")
        }
    code_terms = {
        side: [(by_side[side][pid]["code"], signed) for pid, signed in parsed[side]]
        for side in ("left", "right")
    }
    # Every candidate probability is strictly internal, so both actions are in
    # support. Nash is therefore equivalent to exact indifference at every row.
    for equation_side, target_side in (("left", "right"), ("right", "left")):
        for rec in inst["groups"][equation_side]:
            total = sum(
                _chi(rows, rec["code"], code) * signed
                for code, signed in code_terms[target_side]
            )
            lhs = rec["scale"] * total
            if lhs != rec["force"]:
                return False, (
                    f"player {rec['id']} is not indifferent: scaled character sum "
                    f"{lhs} != force {rec['force']}"
                )
    return True, "ok"


def _payoffs_are_normalized(inst):
    """Check every possible pairwise payoff value by integer inequalities."""
    n = inst["n"]
    W = inst["denominator"]
    # The common denominator is 64*W*n^2.  The upper endpoint 1/n has
    # numerator 64*W*n in that denominator.
    upper_num = 64 * W * n
    for side in ("left", "right"):
        for rec in inst["groups"][side]:
            for opponent_centred_action in (-1, 1):
                for own_latent_action in (0, 1):
                    numerator = 16 * W * n + own_latent_action * (
                        rec["scale"] * opponent_centred_action * W * n
                        - rec["force"]
                    )
                    if not (0 <= numerator <= upper_num):
                        return False
    return True


def _falling(n, s):
    out = 1
    for x in range(n - s + 1, n + 1):
        out *= x
    return out


def search_space(inst):
    per_side = _falling(inst["n"], inst["sparsity"]) * (1 << inst["sparsity"])
    return per_side * per_side


def random_candidate(inst, rng):
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    answer = {}
    for side in ("left", "right"):
        # Sampling records directly avoids rebuilding an O(n) ID list for every
        # G4 candidate; random.sample itself only touches O(sparsity) entries.
        ids = [
            r["id"]
            for r in rng.sample(inst["groups"][side], inst["sparsity"])
        ]
        terms = []
        for pid, weight in zip(ids, sorted(inst["weights"])):
            signed = weight if rng.randrange(2) else -weight
            terms.append([pid, [signed, inst["denominator"]]])
        answer[side] = sorted(terms)
    return answer


def _all_side_candidates(inst, side):
    ids = [r["id"] for r in inst["groups"][side]]
    weights = sorted(inst["weights"])
    for chosen in itertools.permutations(ids, inst["sparsity"]):
        for signs in itertools.product((-1, 1), repeat=inst["sparsity"]):
            yield sorted(
                [
                    [pid, [sign * weight, inst["denominator"]]]
                    for pid, sign, weight in zip(chosen, signs, weights)
                ]
            )


def enumerate_all(inst):
    if search_space(inst) > 100000:
        return None
    count = 0
    right_candidates = list(_all_side_candidates(inst, "right"))
    for left in _all_side_candidates(inst, "left"):
        for right in right_candidates:
            if verify(inst, {"left": left, "right": right})[0]:
                count += 1
    return count


def canonical_key(inst):
    # Player IDs, input ordering, public action names, the left/right names, and
    # the displayed GF(2) coordinate basis are presentation only.  The complete
    # payoff-tensor isomorphism problem is unnecessarily expensive here; this
    # cheap invariant keeps the exact multisets of intrinsic row scale/forcing
    # labels on both sides.  Random row scales make it strongly discriminating
    # on this distribution, while ignoring every supported presentation change.
    group_sigs = []
    for side in ("left", "right"):
        sig = sorted((r["scale"], r["force"]) for r in inst["groups"][side])
        group_sigs.append(sig)
    group_sigs.sort(key=lambda x: json.dumps(x, separators=(",", ":")))
    canonical = {
        "n": inst["n"],
        "sparsity": inst["sparsity"],
        "weights": sorted(inst["weights"]),
        "denominator": inst["denominator"],
        "groups": group_sigs,
    }
    blob = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def escalate(params):
    out = dict(params)
    out.pop("_preset", None)
    n = out.get("n")
    if not _is_int(n):
        return None
    if n >= CERTIFICATE_LANGUAGE["bounds"]["max_players_per_side"]:
        return "cap_bound"
    out["n"] = n * 2
    # A wider positive row-scale range adds construction-neutral numeric decoys
    # while the certificate stays fixed; n grows the transform haystack.
    out["scale_max"] = min(7, int(out.get("scale_max", 1)) + 1)
    return out


def _fwht(values):
    out = list(values)
    h = 1
    while h < len(out):
        for i in range(0, len(out), h * 2):
            for j in range(i, i + h):
                a, b = out[j], out[j + h]
                out[j] = a + b
                out[j + h] = a - b
        h *= 2
    return out


def _reference_algorithm(inst):
    """Exact O(n log n) inversion; expected to succeed on Track B."""
    n = inst["n"]
    rows = inst["matrix_rows"]
    recovered = {}
    for equation_side, target_side in (("left", "right"), ("right", "left")):
        spectrum_input = [0] * n
        for rec in inst["groups"][equation_side]:
            if rec["force"] % rec["scale"]:
                return None
            transformed_row = _transpose_matvec(rows, rec["code"])
            spectrum_input[transformed_row] = rec["force"] // rec["scale"]
        transformed = _fwht(spectrum_input)
        code_to_id = {r["code"]: r["id"] for r in inst["groups"][target_side]}
        terms = []
        for code, value in enumerate(transformed):
            if value % n:
                return None
            signed = value // n
            if signed:
                terms.append([code_to_id[code], [signed, inst["denominator"]]])
        recovered[target_side] = sorted(terms)
    return recovered


def _decode_superincreasing(value, weights):
    signs = {}
    rem = value
    for weight in reversed(sorted(weights)):
        sign = 1 if rem > 0 else -1
        signs[weight] = sign
        rem -= sign * weight
    return signs if rem == 0 else None


def _identity_ansatz(inst):
    """Decode signed rows but incorrectly pretend the displayed M is I."""
    d = inst["dimension"]
    answer = {}
    for equation_side, target_side in (("left", "right"), ("right", "left")):
        by_code = {r["code"]: r for r in inst["groups"][equation_side]}
        base_rec = by_code[0]
        base = _decode_superincreasing(base_rec["force"] // base_rec["scale"], inst["weights"])
        if base is None:
            return None
        guessed_codes = {w: 0 for w in inst["weights"]}
        for bit in range(d):
            rec = by_code[1 << bit]
            signs = _decode_superincreasing(rec["force"] // rec["scale"], inst["weights"])
            if signs is None:
                return None
            for weight in inst["weights"]:
                if signs[weight] != base[weight]:
                    guessed_codes[weight] |= 1 << bit
        code_to_id = {r["code"]: r["id"] for r in inst["groups"][target_side]}
        answer[target_side] = sorted(
            [
                [code_to_id[guessed_codes[w]], [base[w] * w, inst["denominator"]]]
                for w in inst["weights"]
            ]
        )
    return answer


def _rank_candidate(inst, mode):
    answer = {}
    weights = sorted(inst["weights"], reverse=True)
    for side in ("left", "right"):
        records = list(inst["groups"][side])
        if mode == "outlier":
            records.sort(key=lambda r: (-abs(r["force"]), r["id"]))
        else:
            records.sort(key=lambda r: (r["force"], r["id"]))
        terms = []
        for rec, weight in zip(records[: inst["sparsity"]], weights):
            if mode == "outlier":
                sign = 1 if rec["force"] >= 0 else -1
            else:
                sign = -1 if rec["force"] >= 0 else 1
            terms.append([rec["id"], [sign * weight, inst["denominator"]]])
        answer[side] = sorted(terms)
    return answer


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def _permute_bits(value, permutation):
    out = 0
    for old_bit, new_bit in enumerate(permutation):
        if (value >> old_bit) & 1:
            out |= 1 << new_bit
    return out


def _transform_instance(
    inst,
    id_map=None,
    toggle_ids=(),
    swap_groups=False,
    reverse=False,
    bit_permutation=None,
):
    out = copy.deepcopy(inst)
    out["standard_ids"] = False
    if id_map:
        for side in ("left", "right"):
            for rec in out["groups"][side]:
                rec["id"] = id_map[rec["id"]]
            for term in out["answer"][side]:
                term[0] = id_map[term[0]]
    toggle = set(toggle_ids)
    if toggle:
        for side in ("left", "right"):
            for rec in out["groups"][side]:
                if rec["id"] in toggle:
                    rec["flip"] ^= 1
    if bit_permutation is not None:
        d = out["dimension"]
        if sorted(bit_permutation) != list(range(d)):
            raise ValueError("bit_permutation must permute all coordinates")
        for side in ("left", "right"):
            for rec in out["groups"][side]:
                rec["code"] = _permute_bits(rec["code"], bit_permutation)
        # If P permutes coordinates, replace M by P M P^T.  Then
        # (P r)^T (P M P^T) (P c) = r^T M c, so every payoff is unchanged.
        new_rows = [0] * d
        for old_row, row_value in enumerate(out["matrix_rows"]):
            new_row = bit_permutation[old_row]
            new_rows[new_row] = _permute_bits(row_value, bit_permutation)
        out["matrix_rows"] = new_rows
    if swap_groups:
        out["groups"]["left"], out["groups"]["right"] = out["groups"]["right"], out["groups"]["left"]
        out["answer"]["left"], out["answer"]["right"] = out["answer"]["right"], out["answer"]["left"]
    if reverse:
        out["groups"]["left"].reverse()
        out["groups"]["right"].reverse()
        out["answer"]["left"].reverse()
        out["answer"]["right"].reverse()
    return out


def _reference_operations(inst):
    # Two transforms: n*log2(n) additions/subtractions each; plus an O(n)
    # shear reindex and normalization on each side.
    return 2 * inst["n"] * inst["dimension"] + 4 * inst["n"]


def _intended_operations(inst):
    # On each side, inspect code 0 and d basis codes.  Each inspected row needs
    # one exact division and s exact greedy subtractions.  Conservatively count
    # four word-level GF(2) operations for each of the 2s recovered codes, two
    # per displayed matrix row to identify the rank-one shear, and three more
    # to confirm that the shear is involutory.
    d = inst["dimension"]
    s = inst["sparsity"]
    return 2 * (d + 1) * (s + 1) + 4 * (2 * s) + 2 * d + 3


def selftest():
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    g1_total = 0
    g1_payoff_bounds = 0
    g1_failures = []
    # In a G9 one-rung scratch copy, use the available entries without assuming
    # the normal four names.
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_total += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": why})
            if _payoffs_are_normalized(inst):
                g1_payoff_bounds += 1
            else:
                g1_failures.append(
                    {"preset": preset, "seed": seed, "reason": "pair payoff outside [0,1/n]"}
                )
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append({"preset": preset, "seed": seed, "reason": "answer not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "verified": g1_total,
        "payoff_bound_instances": g1_payoff_bounds,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY.get(SHIPPING_DIFFICULTY, next(iter(DIFFICULTY.values())))
    inst = make_instance(seed=314159, **ship_params)
    corruptions = {}

    bad = copy.deepcopy(inst["answer"])
    bad["left"].pop()
    corruptions["drop_one"] = verify(inst, bad)

    bad = copy.deepcopy(inst["answer"])
    bad["left"][0][0], bad["right"][0][0] = bad["right"][0][0], bad["left"][0][0]
    corruptions["swap_across_sides"] = verify(inst, bad)

    bad = copy.deepcopy(inst["answer"])
    bad["left"][1][0] = bad["left"][0][0]
    corruptions["duplicate_id"] = verify(inst, bad)

    corruptions["empty"] = verify(inst, {})

    bad = copy.deepcopy(inst["answer"])
    bad["right"][0][1] = [inst["denominator"] + 1, inst["denominator"]]
    corruptions["out_of_range_weight"] = verify(inst, bad)

    reasons = [why for ok, why in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not ok for ok, _ in corruptions.values()) and len(set(reasons)) == len(reasons),
        "cases": {name: {"accepted": ok, "reason": why} for name, (ok, why) in corruptions.items()},
        "distinct_reasons": len(set(reasons)),
    }

    wire = json.dumps(inst["answer"], separators=(",", ":"))
    response = "I used the indifference equations.\n```json\n<answer>" + wire + "</answer>\n```\nDone."
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and verify(inst, parsed)[0],
        "prose_and_fence": True,
    }

    guess_total = 200000
    guess_hits = 0
    guess_rng = random.Random(8675309)
    t0 = time.perf_counter()
    for _ in range(guess_total):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            guess_hits += 1
    guess_sec = time.perf_counter() - t0
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_hits / guess_total,
        "structure_aware_space": search_space(inst),
        "sampling_wall_clock_sec": round(guess_sec, 6),
    }

    attack_attempts = 8
    attack_results = {
        "outlier_absolute_force": {"successes": 0, "attempts": attack_attempts},
        "greedy_uniform_best_response": {"successes": 0, "attempts": attack_attempts},
        "random_restart_256": {"successes": 0, "attempts": attack_attempts},
        "identity_bilinear_ansatz": {"successes": 0, "attempts": attack_attempts},
    }
    random_candidates_tested = 0
    attack_t0 = time.perf_counter()
    reference_successes = 0
    reference_t0 = time.perf_counter()
    reference_elapsed = 0.0
    for seed in range(100, 100 + attack_attempts):
        trial = make_instance(seed=seed, **ship_params)
        for name, cand in (
            ("outlier_absolute_force", _rank_candidate(trial, "outlier")),
            ("greedy_uniform_best_response", _rank_candidate(trial, "greedy")),
            ("identity_bilinear_ansatz", _identity_ansatz(trial)),
        ):
            if cand is not None and verify(trial, cand)[0]:
                attack_results[name]["successes"] += 1
        rrng = random.Random(seed ^ 0x5A17)
        solved = False
        for _ in range(256):
            random_candidates_tested += 1
            if verify(trial, random_candidate(trial, rrng))[0]:
                solved = True
                break
        if solved:
            attack_results["random_restart_256"]["successes"] += 1

        rt0 = time.perf_counter()
        ref = _reference_algorithm(trial)
        reference_elapsed += time.perf_counter() - rt0
        if ref is not None and verify(trial, ref)[0]:
            reference_successes += 1
    attack_elapsed = time.perf_counter() - attack_t0 - reference_elapsed
    all_failed = all(x["successes"] == 0 for x in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == attack_attempts,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "generalized fast Walsh-Hadamard inversion",
            "complexity": "O(n log n) exact",
            "wall_clock_sec": round(reference_elapsed / attack_attempts, 6),
            "operations": _reference_operations(inst),
            "solves": f"{reference_successes}/{attack_attempts}, as expected",
        },
        "random_candidates_tested": random_candidates_tested,
        "failing_attacks_wall_clock_sec": round(attack_elapsed, 6),
    }

    exact_density_num = 1
    exact_density_den = search_space(inst)
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_hits == 0 and reference_successes == attack_attempts,
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_sampled_solution_fraction": guess_hits / guess_total,
        "unique_full_support_solution_count": exact_density_num,
        "exact_language_density_denominator": exact_density_den,
        "reference_wall_clock_sec": round(reference_elapsed / attack_attempts, 6),
        "reference_operation_count": _reference_operations(inst),
        "strongest_failing_attack_wall_clock_sec": round(attack_elapsed, 6),
        "strongest_failing_attack_budget": random_candidates_tested,
        "demo_enumerated_solution_count": (
            enumerate_all(make_instance(seed=5, **DIFFICULTY["demo"]))
            if "demo" in DIFFICULTY
            else None
        ),
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=271828, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(inst),
        "shipping_n_per_side": inst["n"],
        "doubled_n_per_side": doubled["n"],
        "shipping_space_bits": search_space(inst).bit_length(),
        "doubled_space_bits": search_space(doubled).bit_length(),
        "doubled_verify_reason": doubled_why,
    }

    invariant_checks = 0
    transported_verifications = 0
    distinct_keys = []
    measured_answer_blobs = [json.dumps(inst["answer"])]
    for seed in range(20):
        base = make_instance(seed=7000 + seed, **ship_params)
        key = canonical_key(base)
        distinct_keys.append(key)
        measured_answer_blobs.append(json.dumps(base["answer"]))
        ids = [r["id"] for side in ("left", "right") for r in base["groups"][side]]
        prng = random.Random(9000 + seed)
        shuffled = list(ids)
        prng.shuffle(shuffled)
        mapping = dict(zip(ids, shuffled))
        toggled = shuffled[::3]
        bit_permutation = list(range(base["dimension"]))
        prng.shuffle(bit_permutation)
        variants = [
            _transform_instance(base, reverse=True),
            _transform_instance(base, id_map=mapping),
            _transform_instance(base, toggle_ids=toggled),
            _transform_instance(base, bit_permutation=bit_permutation),
            _transform_instance(base, swap_groups=True),
            _transform_instance(
                base,
                id_map=mapping,
                toggle_ids=toggled,
                swap_groups=True,
                reverse=True,
                bit_permutation=bit_permutation,
            ),
        ]
        for variant in variants:
            invariant_checks += 1
            if canonical_key(variant) == key:
                transported_verifications += int(verify(variant, variant["answer"])[0])
            else:
                transported_verifications -= 1000000
    unique_keys = len(set(distinct_keys))
    report["G8_canonical_key"] = {
        "pass": (
            invariant_checks == 120
            and transported_verifications == invariant_checks
            and unique_keys == 20
        ),
        "invariance_checks": invariant_checks,
        "real_transformation_verifications": transported_verifications,
        "unrelated_distinct": unique_keys,
        "unrelated_attempts": 20,
        "transformations": [
            "input reordering",
            "player-ID permutation",
            "public-action relabelling",
            "simultaneous GF(2) coordinate permutation",
            "left/right group swap",
            "composition of all five",
        ],
    }

    answer_blob = max(measured_answer_blobs, key=len)
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(inst["answer"])
    intended_ops = _intended_operations(inst)
    arms = copy.deepcopy(G9_ORACLE_RESULTS)
    hinted = arms.get("hinted", {"solved": 0, "attempts": 0})
    placebo = arms.get("placebo", {"solved": 0, "attempts": 0})
    hrate = hinted.get("solved", 0) / max(1, hinted.get("attempts", 0))
    prate = placebo.get("solved", 0) / max(1, placebo.get("attempts", 0))
    report["G9_no_tool_suitability"] = {
        "pass": answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300,
        "arms": {
            "bare": arms.get("bare", {"solved": 0, "attempts": 0}),
            "hinted": hinted,
            "placebo": placebo,
        },
        "hinted_minus_placebo": hrate - prate,
        "hinted_verdict": arms.get("hinted_verdict", "not_run"),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "tokens": 500, "elements": 256, "operations": 300},
    }

    gate_values = [v for k, v in report.items() if k.startswith("G") and isinstance(v, dict)]
    report["all_passed"] = all(v.get("pass") is True for v in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
