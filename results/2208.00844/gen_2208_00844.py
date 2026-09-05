"""Verified generator for a structured dense-MQ family from arXiv:2208.00844.

The paper studies Groebner-basis computation for dense, overdefined quadratic
systems over finite fields.  This module poses the native downstream task: find
a common zero.  Instances are inverse-generated, then hidden behind an
invertible Walsh--Hadamard change of equation basis and nonzero row scalings.
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

_KNOWN_LARGE_PRIMES = (
    2147483647,  # 2^31 - 1
    2305843009213693951,  # 2^61 - 1
    618970019642690137449562111,  # 2^89 - 1
    162259276829213363391578010288127,  # 2^107 - 1
    170141183460469231731687303715884105727,  # 2^127 - 1
)
_ESCALATION_PRIMES = [
    101, 211, 431, 863, 1733, 3467, 6947, 13901, 27803, 55609,
    *_KNOWN_LARGE_PRIMES,
]

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "integer_tuple",
    "native_objects": ["dense quadratic polynomial system over a prime field"],
    "verification_operations": [
        "finite-field polynomial evaluation",
        "modular equality comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "One quadratic coefficient column normalizes the equation rows into Walsh "
        "characters, so changing the equation basis exposes coordinate equations "
        "that a generic reduction would discover mechanically."
    ),
    "hardness_basis": (
        "Track B: degree-2 Macaulay row elimination costs "
        "O(M^2*(binom(N+1,2)+N)) and, at N=15, M=32, p=101, takes about "
        "134000 modular arithmetic operations (roughly 0.06 s here), whereas "
        "the compact normalized-Walsh route takes 297 exact field operations once its "
        "character basis is recognized."
    ),
    "max_answer_tokens": 18,
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

DIFFICULTY = {
    "demo": {"n": 2, "modulus": 101, "equations": 4},
    "easy": {"n": 15, "modulus": 101, "equations": 32},
    "medium": {"n": 15, "modulus": 211, "equations": 32},
    "hard": {"n": 15, "modulus": 431, "equations": 32},
}
SHIPPING_DIFFICULTY = "easy"

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON array of n pairwise-distinct canonical residues in [0,p-1], "
        "representing a point of the stated prime field."
    ),
    "bounds": {"max_dimension": 64, "max_modulus": max(_ESCALATION_PRIMES)},
}

STRUCTURAL_HINT = (
    "The x0*x0 coefficient column simultaneously normalizes the labelled equation "
    "rows into Walsh-Hadamard characters."
)
PLACEBO_HINT = (
    "The constant and quadratic coefficient columns require consistent indexing and "
    "careful modular bookkeeping."
)

# Filled from the separately preserved harden.py runs.  These are diagnostics,
# never used by make_instance or verify.
G9_ARMS = {
    "bare": {"solved": 0, "attempts": 0, "errors": 4},
    "hinted": {"solved": 0, "attempts": 0, "errors": 4},
    "placebo": {"solved": 0, "attempts": 0, "errors": 4},
}

NOTES = (
    "Section 2.1 fixes the finite-field polynomial, leading-term, reduction, and "
    "normal-form definitions. Section 2.3 and its cited signature S-pair criterion "
    "explain how Groebner bases certify the computation; Theorem 2 proves the new "
    "Reduce routine terminates and returns a Sig-normal form. Section 4.2 fixes the "
    "paper's baseline benchmark regime: dense quadratic systems over F_101 with "
    "M=2N; Section 4.3 varies M, reports exponential-looking reduction growth, and "
    "also warns that canonical sparse systems are often easier. This generator stays dense and "
    "overdefined but is honestly Track B: its row-space structure admits Gaussian "
    "elimination, and its shorter Walsh route is the intended insight. Outlier, "
    "single-row greedy, random-restart, and pair-cancellation attacks are defeated "
    "by using an invertible global mix and independent nonzero row scalings, so no "
    "single displayed row or pair exposes the hidden coordinate equations."
)


def _is_prime(p):
    if not isinstance(p, int) or isinstance(p, bool) or p < 2:
        return False
    if p % 2 == 0:
        return p == 2
    if p in _KNOWN_LARGE_PRIMES:
        return True
    d = 3
    while d * d <= p:
        if p % d == 0:
            return False
        d += 2
    return True


def _is_power_of_two(x):
    return isinstance(x, int) and x > 0 and (x & (x - 1)) == 0


def _quad_pairs(n):
    return [(i, j) for i in range(n) for j in range(i, n)]


def _dot_mod(a, b, p):
    return sum(x * y for x, y in zip(a, b)) % p


def _rank_mod(rows, p):
    a = [[x % p for x in row] for row in rows]
    if not a:
        return 0
    r = 0
    for c in range(len(a[0])):
        pivot = next((i for i in range(r, len(a)) if a[i][c]), None)
        if pivot is None:
            continue
        a[r], a[pivot] = a[pivot], a[r]
        inv = pow(a[r][c], p - 2, p)
        a[r] = [(x * inv) % p for x in a[r]]
        for i in range(len(a)):
            if i != r and a[i][c]:
                f = a[i][c]
                a[i] = [(x - f * y) % p for x, y in zip(a[i], a[r])]
        r += 1
        if r == len(a):
            break
    return r


def _walsh_sign(row, col, p):
    return 1 if (row & col).bit_count() % 2 == 0 else p - 1


def make_instance(n, seed=0, **params):
    """Inverse-generate a unique-root dense MQ system and its JSON-native root."""
    p = params.get("modulus", 101)
    m = params.get("equations", 1 << (2 * n - 1).bit_length())
    if not isinstance(n, int) or isinstance(n, bool) or n < 2 or n > 64:
        raise ValueError("n must be an integer in [2,64]")
    if not _is_prime(p) or p <= n:
        raise ValueError("modulus must be a prime greater than n")
    if not _is_power_of_two(m) or m < 2 * n:
        raise ValueError("equations must be a power of two at least 2*n")
    qterms = _quad_pairs(n)
    if m - n > len(qterms) - 1:
        raise ValueError("too many independent quadratic decoys for this n")

    rng = random.Random(seed)
    root = rng.sample(range(p), n)
    values = [(root[i] * root[j]) % p for i, j in qterms]

    # Each homogeneous quadratic part is uniform; its constant is set so that
    # q(root)=0. Independence is checked while sampling decoys; the known root
    # is never obtained by solving the system.
    quadratics = []
    target_rank = m - n
    while len(quadratics) < target_rank:
        coeff = [rng.randrange(p) for _ in qterms]
        coeff[0] = 1 if len(quadratics) == 0 else 0
        if _rank_mod(quadratics + [coeff], p) == len(quadratics) + 1:
            quadratics.append(coeff)

    # Slot zero is a quadratic anchor: its x0^2 coefficient is one, while that
    # coefficient is zero in all other base polynomials.  After the Walsh mix it
    # becomes the all-ones column.  Independent nonzero row scalings hide that
    # normalization in the displayed system without changing its zero set.
    linear_slots = rng.sample(range(1, m), n)
    linear_slot_set = set(linear_slots)
    quadratic_slots = [slot for slot in range(m) if slot not in linear_slot_set]
    linear_scales = [rng.randrange(1, p) for _ in range(n)]

    base = []
    quad_at = {
        slot: (quadratics[k], (-_dot_mod(quadratics[k], values, p)) % p)
        for k, slot in enumerate(quadratic_slots)
    }
    linear_at = {slot: i for i, slot in enumerate(linear_slots)}
    for slot in range(m):
        if slot in quad_at:
            quad, constant = quad_at[slot]
            base.append({"c": constant, "l": [0] * n, "q": quad})
        else:
            i = linear_at[slot]
            scale = linear_scales[i]
            linear = [0] * n
            linear[i] = scale
            base.append({
                "c": (-scale * root[i]) % p,
                "l": linear,
                "q": [0] * len(qterms),
            })

    displayed = []
    for row in range(m):
        c = 0
        linear = [0] * n
        quad = [0] * len(qterms)
        for col, b in enumerate(base):
            s = _walsh_sign(row, col, p)
            c = (c + s * b["c"]) % p
            for i, x in enumerate(b["l"]):
                linear[i] = (linear[i] + s * x) % p
            for k, x in enumerate(b["q"]):
                quad[k] = (quad[k] + s * x) % p
        row_scale = rng.randrange(1, p)
        displayed.append({
            "label": row,
            "c": (row_scale * c) % p,
            "l": [(row_scale * x) % p for x in linear],
            "q": [(row_scale * x) % p for x in quad],
        })
    rng.shuffle(displayed)

    return {
        "n": n,
        "modulus": p,
        "equation_count": m,
        "quadratic_pairs": [[i, j] for i, j in qterms],
        "equations": displayed,
        "answer": list(root),
    }


def _eval_equation(eq, point, pairs, p):
    value = eq["c"] + sum(a * x for a, x in zip(eq["l"], point))
    for coeff, (i, j) in zip(eq["q"], pairs):
        value += coeff * point[i] * point[j]
    return value % p


def verify(inst, answer):
    """Check any well-formed common zero; never inspect the planted answer."""
    n = inst["n"]
    p = inst["modulus"]
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    if not answer:
        return False, "answer cannot be empty"
    if len(answer) != n:
        return False, f"expected exactly {n} coordinates"
    if any(not isinstance(x, int) or isinstance(x, bool) for x in answer):
        return False, "every coordinate must be an integer"
    if any(x < 0 or x >= p for x in answer):
        return False, f"coordinates must lie in [0,{p - 1}]"
    if len(set(answer)) != n:
        return False, "coordinates must be pairwise distinct"
    pairs = inst["quadratic_pairs"]
    for k, eq in enumerate(inst["equations"]):
        residue = _eval_equation(eq, answer, pairs, p)
        if residue:
            return False, f"equation {k} evaluates to nonzero residue {residue}"
    return True, "ok"


def render(inst):
    n = inst["n"]
    p = inst["modulus"]
    m = inst["equation_count"]
    pairs = [tuple(x) for x in inst["quadratic_pairs"]]
    names = [f"x{i}" for i in range(n)]
    monomials = [f"x{i}*x{j}" for i, j in pairs]
    lines = [
        "Find a common zero of a dense quadratic system over a prime field.",
        "",
        f"All arithmetic is modulo the prime p={p}. A field element is written as",
        f"its canonical integer residue in [0,{p - 1}]. There are n={n} variables",
        f"{', '.join(names)} and M={m} equations. The required point must have",
        "pairwise-distinct coordinates.",
        "",
        "Every equation row has the form",
        "  c + sum_i L[i]*x_i + sum_k Q[k]*monomial[k] = 0 (mod p).",
        "The Q entries use this fixed order (indices are 0-based):",
        "  " + ", ".join(f"{k}:{name}" for k, name in enumerate(monomials)),
        "The integer label is part of the row's name; rows below may be out of label order.",
        "",
        "Rows are written as: label | c | L[0..n-1] | Q[0..binom(n+1,2)-1]",
    ]
    for eq in inst["equations"]:
        lines.append(
            f"{eq['label']} | {eq['c']} | "
            + " ".join(map(str, eq["l"]))
            + " | "
            + " ".join(map(str, eq["q"]))
        )
    lines.extend([
        "",
        f"Give your final answer inside <answer></answer> tags as a JSON array of exactly {n}",
        f"pairwise-distinct integers in [0,{p - 1}], ordered x0 through x{n - 1}.",
        "Example format: <answer>" + json.dumps(list(range(n))) + "</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    """Parse tagged JSON, with conservative fallbacks for fenced model output."""
    if not isinstance(text, str):
        return None
    tagged = re.findall(r"<answer>\s*(.*?)\s*</answer>", text, flags=re.I | re.S)
    candidates = list(reversed(tagged))
    if not candidates:
        fences = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.I | re.S)
        candidates.extend(reversed(fences))
    if not candidates:
        candidates.extend(reversed(re.findall(r"\[[\s\d,+-]*\]", text)))
    for raw in candidates:
        try:
            value = json.loads(raw.strip())
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, list) and all(
            isinstance(x, int) and not isinstance(x, bool) for x in value
        ):
            return value
    return None


def random_candidate(inst, rng):
    """Sample uniformly from the stated pairwise-distinct coordinate language."""
    return rng.sample(range(inst["modulus"]), inst["n"])


def search_space(inst):
    p, n = inst["modulus"], inst["n"]
    return math.prod(range(p - n + 1, p + 1))


def enumerate_all(inst):
    """Brute-force the demo language only; larger spaces are deliberately capped."""
    if search_space(inst) > 20000:
        return None
    count = 0
    for point in itertools.permutations(range(inst["modulus"]), inst["n"]):
        if verify(inst, list(point))[0]:
            count += 1
    return count


def _equation_coarse_key(eq, n):
    diag = []
    off = []
    k = 0
    for i in range(n):
        for j in range(i, n):
            (diag if i == j else off).append(eq["q"][k])
            k += 1
    return (eq["c"], tuple(sorted(eq["l"])), tuple(sorted(diag)), tuple(sorted(off)))


def _normalize_equation_scale(eq, n, p):
    """Canonical representative of a polynomial up to nonzero scalar."""
    diag = []
    off = []
    k = 0
    for i in range(n):
        for j in range(i, n):
            (diag if i == j else off).append(eq["q"][k])
            k += 1
    # These linear symmetric functionals are invariant under variable renaming.
    features = [eq["c"] % p, sum(eq["l"]) % p, sum(diag) % p, sum(off) % p]
    first = next((x for x in features if x), None)
    if first is not None:
        multipliers = [pow(first, p - 2, p)]
    else:
        # Extremely rare random fallback: take the lexicographically least scalar
        # multiple using only variable-permutation invariants.
        multipliers = range(1, p)
    best = None
    for factor in multipliers:
        candidate = {
            "label": eq.get("label", 0),
            "c": factor * eq["c"] % p,
            "l": [factor * x % p for x in eq["l"]],
            "q": [factor * x % p for x in eq["q"]],
        }
        key = _equation_coarse_key(candidate, n)
        if best is None or key < best[0]:
            best = (key, candidate)
    return best[1]


def canonical_key(inst):
    """Canonicalize row order/scaling and, generically, variable renaming."""
    n = inst["n"]
    p = inst["modulus"]
    rows = [_normalize_equation_scale(eq, n, p) for eq in inst["equations"]]
    rows.sort(key=lambda e: _equation_coarse_key(e, n))
    pairs = [tuple(x) for x in inst["quadratic_pairs"]]
    qindex = {pair: k for k, pair in enumerate(pairs)}
    signatures = []
    for i in range(n):
        incident = []
        for eq in rows:
            edge = []
            for j in range(n):
                a, b = sorted((i, j))
                edge.append(eq["q"][qindex[(a, b)]])
            incident.append((eq["l"][i], tuple(sorted(edge))))
        signatures.append((tuple(incident), i))
    order = [i for _, i in sorted(signatures)]
    normalized = []
    for eq in rows:
        linear = [eq["l"][i] for i in order]
        quad = []
        for a in range(n):
            for b in range(a, n):
                i, j = sorted((order[a], order[b]))
                quad.append(eq["q"][qindex[(i, j)]])
        normalized.append([eq["c"], linear, quad])
    normalized.sort(key=lambda x: json.dumps(x, separators=(",", ":")))
    payload = json.dumps(
        [inst["modulus"], inst["n"], normalized], separators=(",", ":")
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def escalate(params):
    """Raise field entropy while holding the 15-coordinate witness fixed."""
    p = params.get("modulus", 101)
    nxt = next((x for x in _ESCALATION_PRIMES if x > p), None)
    if nxt is None:
        return "cap_bound"
    out = dict(params)
    out["modulus"] = nxt
    out["n"] = params.get("n", 15)
    out["equations"] = params.get("equations", 32)
    out.pop("seed", None)
    return out


def _row_elimination_reference(inst):
    """Degree-2 Macaulay preprocessing; returns (root, operations, seconds)."""
    p = inst["modulus"]
    qn = len(inst["quadratic_pairs"])
    n = inst["n"]
    rows = [list(eq["q"]) + list(eq["l"]) + [eq["c"]] for eq in inst["equations"]]
    operations = 0
    start = time.perf_counter()
    r = 0
    for c in range(qn):
        pivot = next((i for i in range(r, len(rows)) if rows[i][c] % p), None)
        if pivot is None:
            continue
        rows[r], rows[pivot] = rows[pivot], rows[r]
        inv = pow(rows[r][c] % p, p - 2, p)
        operations += 1
        for j in range(c, len(rows[r])):
            rows[r][j] = (rows[r][j] * inv) % p
            operations += 1
        for i in range(len(rows)):
            if i == r:
                continue
            factor = rows[i][c] % p
            if factor:
                for j in range(c, len(rows[i])):
                    rows[i][j] = (rows[i][j] - factor * rows[r][j]) % p
                    operations += 2
        r += 1
        if r == len(rows):
            break
    linear_rows = [row[qn:] for row in rows if not any(x % p for x in row[:qn])]
    if len(linear_rows) < n:
        return None, operations, time.perf_counter() - start
    rr = 0
    for c in range(n):
        pivot = next((i for i in range(rr, len(linear_rows)) if linear_rows[i][c] % p), None)
        if pivot is None:
            return None, operations, time.perf_counter() - start
        linear_rows[rr], linear_rows[pivot] = linear_rows[pivot], linear_rows[rr]
        inv = pow(linear_rows[rr][c] % p, p - 2, p)
        operations += 1
        for j in range(c, n + 1):
            linear_rows[rr][j] = (linear_rows[rr][j] * inv) % p
            operations += 1
        for i in range(len(linear_rows)):
            if i == rr:
                continue
            factor = linear_rows[i][c] % p
            if factor:
                for j in range(c, n + 1):
                    linear_rows[i][j] = (
                        linear_rows[i][j] - factor * linear_rows[rr][j]
                    ) % p
                    operations += 2
        rr += 1
    root = [(-linear_rows[i][n]) % p for i in range(n)]
    return root, operations, time.perf_counter() - start


def _walsh_compact_route(inst):
    """Execute the intended normalized Walsh shortcut without using the answer."""
    p = inst["modulus"]
    n = inst["n"]
    m = inst["equation_count"]
    by_label = {eq["label"]: eq for eq in inst["equations"]}
    if set(by_label) != set(range(m)):
        return None, 0

    normalized_constants = [0] * m
    anchor_inverses = [0] * m
    for label in range(m):
        anchor = by_label[label]["q"][0] % p
        if not anchor:
            return None, 0
        anchor_inverses[label] = pow(anchor, p - 2, p)
        normalized_constants[label] = by_label[label]["c"] * anchor_inverses[label] % p

    transformed = list(normalized_constants)
    width = 1
    while width < m:
        for start in range(0, m, 2 * width):
            for j in range(start, start + width):
                u, v = transformed[j], transformed[j + width]
                transformed[j] = (u + v) % p
                transformed[j + width] = (u - v) % p
        width *= 2
    point = []
    bits = int(math.log2(m))
    for variable in range(n):
        scale = by_label[0]["l"][variable] * anchor_inverses[0] % p
        if not scale:
            return None, 0
        slot = 0
        for bit in range(bits):
            label = 1 << bit
            value = by_label[label]["l"][variable] * anchor_inverses[label] % p
            if value == (-scale) % p:
                slot |= 1 << bit
            elif value != scale:
                return None, 0
        denominator = m * scale % p
        point.append((-transformed[slot] * pow(denominator, p - 2, p)) % p)

    operations = m + m * bits + n * (bits + 1) + n
    return point, operations


def _attack_candidates(inst, rng):
    p, n = inst["modulus"], inst["n"]
    eqs = inst["equations"]
    # Per-coordinate outlier/ratio guess from a single displayed row.
    outlier = []
    for i in range(n):
        eq = max(eqs, key=lambda e: min(e["l"][i], p - e["l"][i]))
        coeff = eq["l"][i]
        outlier.append((-eq["c"] * pow(coeff or 1, p - 2, p)) % p)

    # Greedy construction-aware linearization: normalize by the anchor column,
    # but treat rows independently instead of recognizing the global transform.
    linear = []
    for e in eqs[:n]:
        inv_anchor = pow(e["q"][0], p - 2, p)
        linear.append(
            [(x * inv_anchor) % p for x in e["l"]]
            + [(e["c"] * inv_anchor) % p]
        )
    greedy = []
    for i in range(n):
        coeff = linear[i][i]
        greedy.append((-linear[i][-1] * pow(coeff or 1, p - 2, p)) % p)

    # Pair attack: look only for two proportional quadratic parts.  The global
    # Walsh mix deliberately leaves no such shortcut.
    pair_guess = list(range(n))
    pair_tests = 0
    found = None
    for i in range(len(eqs)):
        for j in range(i + 1, len(eqs)):
            pair_tests += 1
            qi, qj = eqs[i]["q"], eqs[j]["q"]
            k = next((z for z, x in enumerate(qi) if x), None)
            if k is None or qj[k] == 0:
                continue
            ratio = qj[k] * pow(qi[k], p - 2, p) % p
            if all((ratio * a - b) % p == 0 for a, b in zip(qi, qj)):
                found = (i, j, ratio)
                break
        if found:
            break
    if found:
        i, j, ratio = found
        lin = [(ratio * a - b) % p for a, b in zip(eqs[i]["l"], eqs[j]["l"])]
        const = (ratio * eqs[i]["c"] - eqs[j]["c"]) % p
        k = next((z for z, x in enumerate(lin) if x), None)
        if k is not None:
            pair_guess[k] = (-const * pow(lin[k], p - 2, p)) % p

    random_guesses = [random_candidate(inst, rng) for _ in range(256)]
    return {
        "outlier_single_row_ratio": ([outlier], n),
        "greedy_anchor_normalized_rows": ([greedy], n),
        "random_restart_256": (random_guesses, 256),
        "pairwise_quadratic_cancellation": ([pair_guess], pair_tests),
    }


def _permuted_instance(inst, rng):
    n = inst["n"]
    perm = list(range(n))
    rng.shuffle(perm)
    pairs = [tuple(x) for x in inst["quadratic_pairs"]]
    qindex = {pair: k for k, pair in enumerate(pairs)}
    equations = []
    for eq in reversed(inst["equations"]):
        quad = []
        for i in range(n):
            for j in range(i, n):
                a, b = sorted((perm[i], perm[j]))
                quad.append(eq["q"][qindex[(a, b)]])
        row_scale = rng.randrange(1, inst["modulus"])
        equations.append({
            "label": eq["label"],
            "c": row_scale * eq["c"] % inst["modulus"],
            "l": [row_scale * eq["l"][perm[i]] % inst["modulus"] for i in range(n)],
            "q": [row_scale * x % inst["modulus"] for x in quad],
        })
    return {
        **inst,
        "equations": equations,
        "answer": [inst["answer"][perm[i]] for i in range(n)],
    }


def _answer_elements(answer):
    if isinstance(answer, dict):
        return sum(_answer_elements(v) for v in answer.values())
    if isinstance(answer, list):
        return sum(_answer_elements(v) for v in answer)
    return 1


def selftest():
    report = {}

    planted_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            p = dict(params)
            p["seed"] = seed
            inst = make_instance(**p)
            ok, reason = verify(inst, inst["answer"])
            assert ok, (preset, seed, reason)
            assert json.loads(json.dumps(inst["answer"])) == inst["answer"]
            planted_attempts += 1
    report["G1_planted_verifies"] = {"pass": True, "attempts": planted_attempts}

    sp = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    sp["seed"] = 314159
    inst = make_instance(**sp)
    answer = inst["answer"]
    corruptions = {
        "empty": [],
        "drop": answer[:-1],
        "swap": [answer[1], answer[0]] + answer[2:],
        "duplicate": [answer[0], answer[0]] + answer[2:],
        "out_of_range": [inst["modulus"]] + answer[1:],
    }
    reasons = {}
    for name, bad in corruptions.items():
        ok, reason = verify(inst, bad)
        assert not ok, name
        reasons[name] = reason
    assert len(set(reasons.values())) == len(reasons), reasons
    report["G2_rejects_corruption"] = {"pass": True, "reasons": reasons}

    realistic = (
        "I used the field equations and obtained the following.\n```json\n"
        f"<answer>{json.dumps(answer)}</answer>\n```\n"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {"pass": parsed == answer, "parsed": parsed}
    assert report["G3_round_trip"]["pass"]

    guess_rng = random.Random(8675309)
    guess_total = 200000
    guess_hits = 0
    t0 = time.perf_counter()
    for _ in range(guess_total):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            guess_hits += 1
    guess_sec = time.perf_counter() - t0
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_fraction,
        "candidate_space": search_space(inst),
        "wall_clock_sec": round(guess_sec, 6),
    }
    assert report["G4_guess_resistance"]["pass"]

    demo = make_instance(**DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    recovered, ref_ops, ref_sec = _row_elimination_reference(inst)
    ref_ok = recovered is not None and verify(inst, recovered)[0]
    failing_start = time.perf_counter()
    failing_candidates = _attack_candidates(inst, random.Random(5150))[
        "pairwise_quadratic_cancellation"
    ][0]
    failing_ok = not any(verify(inst, candidate)[0] for candidate in failing_candidates)
    failing_sec = time.perf_counter() - failing_start
    report["G5_density_baseline"] = {
        "pass": demo_count == 1 and ref_ok and failing_ok,
        "shipping_density_hits": guess_hits,
        "shipping_density_total": guess_total,
        "shipping_density_fraction": guess_fraction,
        "demo_exact_solution_count": demo_count,
        "reference_wall_clock_sec": round(ref_sec, 6),
        "reference_modular_operations": ref_ops,
        "strongest_failing_attack_wall_clock_sec": round(failing_sec, 6),
    }
    assert report["G5_density_baseline"]["pass"]

    attack_stats = {}
    attack_start = time.perf_counter()
    for seed in range(8):
        ap = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
        ap["seed"] = 1000 + seed
        attack_inst = make_instance(**ap)
        candidates = _attack_candidates(attack_inst, random.Random(9000 + seed))
        for name, (guesses, effort) in candidates.items():
            stat = attack_stats.setdefault(
                name, {"successes": 0, "attempts": 0, "effort": 0}
            )
            stat["attempts"] += 1
            stat["effort"] += effort
            if any(verify(attack_inst, candidate)[0] for candidate in guesses):
                stat["successes"] += 1
    attack_sec = time.perf_counter() - attack_start
    all_failed = len(attack_stats) >= 4 and all(
        x["successes"] == 0 and x["attempts"] >= 8 for x in attack_stats.values()
    )

    ref_success = 0
    ref_total_ops = 0
    ref_total_sec = 0.0
    for seed in range(8):
        rp = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
        rp["seed"] = 2000 + seed
        ri = make_instance(**rp)
        candidate, ops, sec = _row_elimination_reference(ri)
        ref_total_ops += ops
        ref_total_sec += sec
        if candidate is not None and verify(ri, candidate)[0]:
            ref_success += 1
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_success == 8,
        "attacks": attack_stats,
        "attacks_wall_clock_sec": round(attack_sec, 6),
        "reference_algorithm": {
            "name": "degree-2 Macaulay row elimination over the prime field",
            "complexity": "O(M^2*(binom(N+1,2)+N)) field operations",
            "wall_clock_sec": round(ref_total_sec / 8, 6),
            "operations": round(ref_total_ops / 8),
            "solves": f"{ref_success}/8, as expected",
        },
    }
    assert report["G6_adversary_panel"]["pass"], report["G6_adversary_panel"]

    doubled = make_instance(n=30, seed=77, modulus=101, equations=64)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    escalated = escalate(DIFFICULTY[SHIPPING_DIFFICULTY])
    escalated_inst = make_instance(seed=78, **escalated)
    escalated_ok = verify(escalated_inst, escalated_inst["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and escalated_ok and escalated["modulus"] > inst["modulus"],
        "size_doubled_n": 30,
        "fixed_witness_escalated_modulus": escalated["modulus"],
    }
    assert report["G7_scales"]["pass"]

    invariance = 0
    carried = 0
    distinct_keys = set()
    for seed in range(20):
        kp = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
        kp["seed"] = 3000 + seed
        original = make_instance(**kp)
        transformed = _permuted_instance(original, random.Random(4000 + seed))
        assert canonical_key(original) == canonical_key(transformed)
        invariance += 1
        assert verify(transformed, transformed["answer"])[0]
        carried += 1
        distinct_keys.add(canonical_key(original))
    report["G8_canonical_key"] = {
        "pass": invariance == 20 and carried == 20 and len(distinct_keys) == 20,
        "invariant_relabellings": invariance,
        "carried_witness_verifies": carried,
        "distinct_unrelated": len(distinct_keys),
        "unrelated_attempts": 20,
    }
    assert report["G8_canonical_key"]["pass"]

    blob = json.dumps(answer)
    chars = len(blob)
    elements = _answer_elements(answer)
    tokens = math.ceil(chars / 4)
    intended_ops = (
        inst["equation_count"]
        + inst["equation_count"] * int(math.log2(inst["equation_count"]))
        + inst["n"] * (int(math.log2(inst["equation_count"])) + 1)
        + inst["n"]
    )
    # M divisions normalize constants; a Walsh butterfly produces two additions,
    # so M*log2(M) counts its outputs; N*(log2(M)+1) operations identify character
    # slots/scales; N final field divisions recover the coordinates.
    arms = {k: dict(v) for k, v in G9_ARMS.items()}
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = arms["hinted"]["solved"] / hinted_attempts if hinted_attempts else 0.0
    placebo_rate = (
        arms["placebo"]["solved"] / placebo_attempts if placebo_attempts else 0.0
    )
    compact_answer, measured_intended_ops = _walsh_compact_route(inst)
    compact_ok = (
        measured_intended_ops == intended_ops
        and compact_answer is not None
        and verify(inst, compact_answer)[0]
    )
    within_caps = (
        chars <= 2000 and elements <= 256 and intended_ops <= 300 and compact_ok
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_attempts and placebo_attempts
            else None
        ),
        "hinted_verdict": (
            "infrastructure_blocked_http_403"
            if hinted_attempts == 0
            else ("hardened" if arms["hinted"]["solved"] == 0 else "too_easy")
        ),
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_ops,
        "compact_route_verifies": compact_ok,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }
    assert within_caps

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
