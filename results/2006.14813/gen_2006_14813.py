"""Verified Track-B problems from quaternion tensor simultaneous diagonalization.

The paper's Lemma 1.7 says that an n x p x n quaternion tensor with an
invertible first frontal slice has rank n exactly when the remaining slices,
after normalizing by the first, are simultaneously diagonalizable.  This
module specializes to a tensor (I; A), and asks for a compact exact
diagonalizer of A.

Generation starts with a diagonal quaternion matrix D and the Walsh matrix H.
It applies an independently sampled signed permutation R to form

                  A = R H D H^T R^T / n.

The diagonal entries of D are additive functions of binary column indices, so
A is sparse, but its rows and signs are shuffled.  The planted answer records
R, not a solution recovered from A.  A candidate expands to the real matrix
P=R H.  Verification checks exactly that P^T A P is diagonal; because P is a
signed row permutation of H, this is equivalent to checking that the changed
basis is an XOR-convolution matrix.

The generic mechanical route projects the quaternion entries to a real matrix
with a supplied simple spectrum and performs n exact nullspace solves.  The
compact route recognizes the repeated quaternion displacement classes and
recovers binary coordinates and signs.  The former is deliberately reported
as Track B's successful reference algorithm, never as a failed attack.
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
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # Quaternion arithmetic below remains standard-library-only.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "linear_algebra",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "three-way tensor over the rational quaternions",
        "quaternion frontal slices",
        "compressed signed-Walsh diagonalizing matrix",
    ],
    "verification_operations": [
        "exact quaternion coordinate comparison",
        "exact signed change of basis",
        "exact off-diagonal zero test",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "After the right signed row relabelling, the quaternion slice is an "
        "XOR-convolution matrix, so Walsh characters diagonalize it; without "
        "recognizing that basis, one solves a full exact eigenvector problem."
    ),
    "hardness_basis": (
        "Track B: Lemma 1.7 reduces rank n to simultaneous diagonalization; the "
        "implemented exact modular spectral-projector algorithm uses the supplied "
        "simple spectrum in O(n^4) dense time (O(n^3 log n) on these sparse "
        "slices), measured at 37,494,912 field operations and 4.06 seconds at "
        "n=128, while the signed-XOR change of variables uses 127 exact sign "
        "operations and is not a mechanical in-context eigensolve."
    ),
    "max_answer_tokens": 192,
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
    "demo": {"n": 2, "height": 3},
    "easy": {"n": 32, "height": 136},
    "medium": {"n": 64, "height": 273},
    "hard": {"n": 128, "height": 546},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Up to one signed simultaneous row-column relabelling, the quaternion "
    "slice is an XOR-convolution matrix."
)
PLACEBO_HINT = (
    "Careful attention to the coordinate order and signs is useful for this "
    "quaternion matrix."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A normalized compressed n by n real matrix P: row_for_word is a "
        "permutation of 0,...,n-1 that maps the displayed nonzero off-diagonal "
        "pattern exactly to pairs x,z with popcount(x XOR z)=1; row_signs has "
        "n entries in {-1,+1}, and row_signs[0]=+1; P[row_for_word[x],y]="
        "row_signs[x](-1)^popcount(x&y)."
    ),
    "bounds": {
        "permutation_length": "n",
        "sign_length": "n",
        "sign_alphabet": [-1, 1],
        "normalization": "row_signs[0]=1",
        "structural_rule": "off-diagonal support is mapped to Hamming-distance-one word pairs",
        "maximum_shipping_atomic_elements": 256,
    },
}

NOTES = (
    "Definition 1.1 fixes a simple tensor entry as the ordered quaternion "
    "product a_i b_j c_k, and Definition 1.3 defines rank as the minimum number "
    "of such terms. Lemma 1.7 is the construction used here: with an invertible "
    "first slice, rank n is equivalent to simultaneous diagonalizability of the "
    "normalized remaining slices. Lemma 1.5 supplies the paper's mechanical "
    "complex-adjoint diagonalizability route. Theorem 0.1 and Sections 2--5 "
    "only bound dimensions two and three; Proposition 2.1 even writes the "
    "2x2x2 decomposition explicitly. Consequently the paper supplies no "
    "distributional hardness basis for Track A. This module is Track B and "
    "openly runs exact projected eigensolves as its reference algorithm. "
    "Instances are transformations of a known diagonal quaternion tensor by a "
    "signed Walsh matrix, so the certificate is carried through the map. The "
    "per-row outlier, unsigned coordinate greedy, random-restart, and separable "
    "sign ansatz attacks omit either the coupled binary coordinates or the "
    "non-character row signs; the exact eigensolve remains successful as "
    "expected."
)


# These are diagnostics, not gates.  They are replaced with the script-owned
# transcript measurements after the three hardening runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


_ZERO = (0, 0, 0, 0)
_PROJECTION = (1, 2, 3, 5)


def _q_add(left, right):
    return tuple(left[i] + right[i] for i in range(4))


def _q_neg(value):
    return tuple(-x for x in value)


def _q_scale(value, sign):
    return value if sign == 1 else _q_neg(value)


def _q_dot(value, coefficients=_PROJECTION):
    return sum(value[i] * coefficients[i] for i in range(4))


def _q_norm2(value):
    return sum(x * x for x in value)


def _q_pm_key(value):
    """Canonical representative of {q,-q}, with the orientation sign."""
    value = tuple(value)
    for coordinate in value:
        if coordinate:
            if coordinate > 0:
                return value, 1
            return _q_neg(value), -1
    return value, 1


def _is_power_of_two(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 2 and value & (value - 1) == 0


def _is_character(signs):
    """Whether signs[x] is a character of the binary XOR group."""
    if not signs or signs[0] != 1 or not _is_power_of_two(len(signs)):
        return False
    basis = [signs[1 << bit] for bit in range(len(signs).bit_length() - 1)]
    for word, actual in enumerate(signs):
        expected = 1
        for bit, value in enumerate(basis):
            if word & (1 << bit):
                expected *= value
        if actual != expected:
            return False
    return True


def _sample_weights(log_n, rng, height):
    """Quaternion weights with a superincreasing public real projection."""
    weights = []
    projected_total = 0
    for bit in range(log_n):
        projected = projected_total + rng.randint(height, 2 * height + 1)
        imaginary = [0, 0, 0]
        imaginary[bit % 3] = rng.randint(2, height + 3)
        imaginary[(bit + 1) % 3] = rng.choice((-1, 0, 1))
        real = (
            projected
            - _PROJECTION[1] * imaginary[0]
            - _PROJECTION[2] * imaginary[1]
            - _PROJECTION[3] * imaginary[2]
        )
        quaternion = (real, imaginary[0], imaginary[1], imaginary[2])
        weights.append(quaternion)
        projected_total += projected
    return weights


def _joint_eigenvalues(weights, n):
    values = []
    for word in range(n):
        total = _ZERO
        for bit, weight in enumerate(weights):
            if word & (1 << bit):
                total = _q_add(total, weight)
        values.append(tuple(2 * coordinate for coordinate in total))
    return values


def make_instance(n, seed=0, **params):
    """Construct a certified quaternion tensor by a signed Walsh change of basis."""
    if not _is_power_of_two(n):
        raise ValueError("n must be a power of two and at least 2")
    height = params.pop("height", 7)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if not isinstance(height, int) or isinstance(height, bool) or height < 2:
        raise ValueError("height must be an integer at least 2")

    rng = random.Random(seed)
    log_n = n.bit_length() - 1
    weights = _sample_weights(log_n, rng, height)

    row_for_word = list(range(n))
    rng.shuffle(row_for_word)
    while True:
        row_signs = [1] + [rng.choice((-1, 1)) for _ in range(n - 1)]
        if n == 2 or not _is_character(row_signs):
            break

    diagonal = _ZERO
    for weight in weights:
        diagonal = _q_add(diagonal, weight)

    entries = []
    for word in range(n):
        physical = row_for_word[word]
        if diagonal != _ZERO:
            entries.append([physical, physical, list(diagonal)])
        for bit, weight in enumerate(weights):
            other = word ^ (1 << bit)
            if word < other:
                row = row_for_word[word]
                column = row_for_word[other]
                value = _q_scale(_q_neg(weight), row_signs[word] * row_signs[other])
                entries.append([row, column, list(value)])
                entries.append([column, row, list(value)])
    rng.shuffle(entries)

    joint = _joint_eigenvalues(weights, n)
    projected_spectrum = [_q_dot(value) for value in joint]
    if len(set(projected_spectrum)) != n:
        raise AssertionError("superincreasing projection unexpectedly collided")

    answer = {
        "row_for_word": row_for_word,
        "row_signs": row_signs,
    }
    return {
        "n": n,
        "log_n": log_n,
        "height": height,
        "tensor_shape": [n, 2, n],
        "projection": list(_PROJECTION),
        "projected_spectrum": projected_spectrum,
        "joint_eigenvalues": [list(value) for value in joint],
        "quaternion_slice_entries": entries,
        "answer": answer,
    }


def _format_q(value):
    return "[" + ",".join(str(x) for x in value) + "]"


def render(inst):
    """Render a complete exact simultaneous-diagonalization problem."""
    n = inst["n"]
    lines = [
        "Quaternion tensor rank certificate (all arithmetic is exact)",
        "",
        "A quaternion [a,b,c,d] means a + b*i + c*j + d*k, where",
        "i^2=j^2=k^2=i*j*k=-1; multiplication is in the displayed order.",
        "A simple three-way tensor has entries u[r]*v[s]*w[c], with the",
        "quaternion factors multiplied in that order. Tensor rank is the least",
        "number of simple tensors whose sum is the given array.",
        "",
        "A three-way n x 2 x n tensor is given by two n x n frontal slices",
        "(I,A). Its first slice I is the identity. The second slice A is",
        "listed sparsely below; every unlisted entry is the zero quaternion.",
        "Rows and columns are 0-indexed.",
        "",
        "Find a compressed real n x n matrix P that diagonalizes A, meaning",
        "that P^{-1} A P has zero quaternion in every off-diagonal position.",
        "Your certificate consists of two length-n lists:",
        "  row_for_word: a permutation of 0,...,n-1 that maps nonzero",
        "    off-diagonal entries exactly to word pairs whose XOR has one 1-bit;",
        "  row_signs: entries -1 or +1, with row_signs[0]=+1.",
        "They define P exactly by",
        "  P[row_for_word[x], y] = row_signs[x] * (-1)^popcount(x & y)",
        "for 0 <= x,y < n. Here '&' is bitwise AND and popcount counts 1-bits.",
        "This P is invertible and P^{-1}=P^T/n. Order matters in both lists.",
        "Since the first tensor slice is I, such a P also certifies by exact",
        "inspection that the tensor has rank n and supplies its n-term simple",
        "decomposition through the diagonal entries of P^{-1} A P.",
        "Any certificate satisfying these rules and diagonalizing A is accepted.",
        "",
        f"n = {n}",
        "The integer real projection c=(1,2,3,5) of [a,b,c,d] is",
        "a+2b+3c+5d. The projected real matrix has the following distinct",
        "eigenvalues (this list is instance data, not an answer):",
        json.dumps(inst["projected_spectrum"], separators=(",", ":")),
        "",
        "Nonzero entries of quaternion slice A, one 'row column quaternion' per line:",
    ]
    for row, column, value in sorted(inst["quaternion_slice_entries"]):
        lines.append(f"{row} {column} {_format_q(value)}")

    example = {
        "row_for_word": list(range(n)),
        "row_signs": [1] * n,
    }
    lines.extend(
        [
            "",
            "Give your final answer inside <answer></answer> tags as one JSON object",
            "with exactly the keys row_for_word and row_signs. Use decimal integers.",
            "Example of the required syntax (the values are only a format example):",
            "<answer>" + json.dumps(example, separators=(",", ":")) + "</answer>",
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
    """Extract the JSON answer object from tags, fences, or surrounding prose."""
    if not isinstance(text, str):
        return None
    candidates = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    candidates.extend(re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.I | re.S))
    candidates.append(text.strip())
    decoder = json.JSONDecoder()
    for candidate in candidates:
        candidate = candidate.strip()
        try:
            value = json.loads(candidate)
            if isinstance(value, dict):
                return value
        except (TypeError, ValueError):
            pass
        for match in re.finditer(r"\{", candidate):
            try:
                value, _ = decoder.raw_decode(candidate[match.start() :])
            except ValueError:
                continue
            if isinstance(value, dict):
                return value
    return None


def _matrix_lookup(inst):
    cached = inst.get("_matrix_lookup_cache")
    if isinstance(cached, dict):
        return cached
    n = inst.get("n")
    entries = inst.get("quaternion_slice_entries")
    if not _is_power_of_two(n) or not isinstance(entries, list):
        raise ValueError("malformed tensor instance")
    lookup = {}
    for item in entries:
        if not isinstance(item, list) or len(item) != 3:
            raise ValueError("malformed sparse matrix entry")
        row, column, value = item
        if (
            not isinstance(row, int)
            or isinstance(row, bool)
            or not isinstance(column, int)
            or isinstance(column, bool)
            or not (0 <= row < n and 0 <= column < n)
            or not isinstance(value, list)
            or len(value) != 4
            or any(not isinstance(x, int) or isinstance(x, bool) for x in value)
        ):
            raise ValueError("malformed sparse matrix entry")
        key = (row, column)
        quaternion = tuple(value)
        if key in lookup or quaternion == _ZERO:
            raise ValueError("duplicate or zero sparse matrix entry")
        lookup[key] = quaternion
    inst["_matrix_lookup_cache"] = lookup
    return lookup


def verify(inst, answer):
    """Check any normalized signed-Walsh diagonalizer; never consult the plant."""
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if set(answer) != {"row_for_word", "row_signs"}:
        return False, "answer must contain exactly row_for_word and row_signs"
    n = inst.get("n")
    order = answer.get("row_for_word")
    signs = answer.get("row_signs")
    if not isinstance(order, list) or len(order) != n:
        return False, f"row_for_word must have length {n}"
    if not isinstance(signs, list) or len(signs) != n:
        return False, f"row_signs must have length {n}"
    if any(not isinstance(value, int) or isinstance(value, bool) for value in order):
        return False, "row_for_word entries must be integers"
    if any(value < 0 or value >= n for value in order):
        return False, f"row_for_word entries must lie in 0..{n - 1}"
    if len(set(order)) != n:
        return False, "row_for_word must be a permutation without repeats"
    if any(value not in (-1, 1) or isinstance(value, bool) for value in signs):
        return False, "row_signs entries must each be -1 or +1"
    if signs[0] != 1:
        return False, "normalization requires row_signs[0] to be +1"
    try:
        matrix = _matrix_lookup(inst)
    except (TypeError, ValueError) as exc:
        return False, str(exc)

    # B[x,z] = signs[x] A[order[x],order[z]] signs[z].  The real Walsh
    # matrix diagonalizes B exactly iff B[x,z] depends only on x XOR z.
    kernels = []
    root = order[0]
    for delta in range(n):
        value = matrix.get((root, order[delta]), _ZERO)
        kernels.append(_q_scale(value, signs[delta]))
    for word in range(1, n):
        physical = order[word]
        left_sign = signs[word]
        for other in range(n):
            value = matrix.get((physical, order[other]), _ZERO)
            changed = _q_scale(value, left_sign * signs[other])
            delta = word ^ other
            if changed != kernels[delta]:
                return (
                    False,
                    "matrix certificate leaves a nonzero off-diagonal Walsh entry "
                    f"(first mismatch at words {word},{other})",
                )

    # Enforce the stated support normalization after the usually much quicker
    # sign/convolution rejection.  random_candidate already samples only orders
    # that meet this freely visible condition.
    off_diagonal_count = sum(row != column for row, column in matrix)
    if off_diagonal_count != n * inst.get("log_n", -1):
        return False, "malformed tensor instance: unexpected off-diagonal support size"
    for word in range(n):
        physical = order[word]
        for bit in range(inst["log_n"]):
            other = word ^ (1 << bit)
            if (physical, order[other]) not in matrix:
                return (
                    False,
                    "row_for_word does not map the displayed support to "
                    f"Hamming-distance-one pairs (first mismatch {word},{other})",
                )
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample support-respecting orders and normalized signs."""
    n = inst["n"]
    log_n = inst["log_n"]
    base = inst.get("_candidate_support_order")
    if not isinstance(base, list) or len(base) != n:
        recovered, _ = _compact_route(inst)
        if recovered is None:
            raise ValueError("cannot derive the public support-coordinate language")
        base = list(recovered["row_for_word"])
        inst["_candidate_support_order"] = list(base)
    axes = list(range(log_n))
    rng.shuffle(axes)
    translation = rng.randrange(n)
    order = []
    for word in range(n):
        mapped = translation
        for new_bit, old_bit in enumerate(axes):
            if word & (1 << new_bit):
                mapped ^= 1 << old_bit
        order.append(base[mapped])
    return {
        "row_for_word": order,
        "row_signs": [1] + [rng.choice((-1, 1)) for _ in range(n - 1)],
    }


def search_space(inst):
    """Exact size of the normalized bounded certificate language."""
    n = inst["n"]
    log_n = inst["log_n"]
    return n * math.factorial(log_n) * (1 << (n - 1))


def enumerate_all(inst):
    """Count accepted certificates exactly when at most 100,000 need checking."""
    n = inst["n"]
    space = search_space(inst)
    if space > 100_000:
        return None
    recovered, _ = _compact_route(inst)
    if recovered is None:
        return 0
    base = recovered["row_for_word"]
    log_n = inst["log_n"]
    count = 0
    for translation in range(n):
        for axes in itertools.permutations(range(log_n)):
            order = []
            for word in range(n):
                mapped = translation
                for new_bit, old_bit in enumerate(axes):
                    if word & (1 << new_bit):
                        mapped ^= 1 << old_bit
                order.append(base[mapped])
            for tail in itertools.product((-1, 1), repeat=n - 1):
                answer = {"row_for_word": list(order), "row_signs": [1] + list(tail)}
                count += int(verify(inst, answer)[0])
    return count


def canonical_key(inst):
    """Public entry invariant under signed simultaneous basis relabelling."""
    matrix = _matrix_lookup(inst)
    diagonal = sorted(value for (row, column), value in matrix.items() if row == column)
    off_diagonal = sorted(
        _q_pm_key(value)[0]
        for (row, column), value in matrix.items()
        if row < column
    )
    payload = {
        "n": inst.get("n"),
        "diagonal_multiset": diagonal,
        "off_diagonal_pm_multiset": off_diagonal,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def escalate(params):
    """Raise coefficient height first, then dimension while the certificate fits."""
    harder = dict(params)
    height = int(harder.get("height", 7))
    n = int(harder.get("n", 8))
    if height < 2184:
        harder["height"] = height * 2
        return harder
    if n < 128:
        harder["n"] = n * 2
        harder["height"] = height + 1
        return harder
    return "cap_bound"


def _sparse_projected_matrix(inst):
    entries = []
    operations = 0
    for row, column, value in inst["quaternion_slice_entries"]:
        total = 0
        for coefficient, coordinate in zip(inst["projection"], value):
            total += coefficient * coordinate
            operations += 2
        entries.append((row, column, total))
    return entries, operations


def _reference_algorithm(inst):
    """Exact modular spectral projectors, then verified Walsh compression."""
    started = time.perf_counter()
    projected, operations = _sparse_projected_matrix(inst)
    spectrum = sorted(inst["projected_spectrum"])
    modulus = (1 << 61) - 1
    if len({value % modulus for value in spectrum}) != len(spectrum):
        return None, {"operations": operations, "wall_clock_sec": time.perf_counter() - started}

    n = inst["n"]
    columns = []
    for eigenvalue in spectrum:
        # product_{mu != lambda}(C-mu*I)e_0 is a nonzero multiple of the
        # lambda eigenvector.  Work modulo a prime, lift the resulting signs,
        # and verify the final certificate over the integer quaternions.
        vector = [1] + [0] * (n - 1)
        for other in spectrum:
            if other == eigenvalue:
                continue
            changed = [(-other * value) % modulus for value in vector]
            operations += 2 * n
            for row, column, value in projected:
                changed[row] = (changed[row] + value * vector[column]) % modulus
                operations += 2
            vector = changed
        if not vector[0]:
            return None, {"operations": operations, "wall_clock_sec": time.perf_counter() - started}
        inverse = pow(vector[0], modulus - 2, modulus)
        operations += 2 * modulus.bit_length()
        normalized = [(entry * inverse) % modulus for entry in vector]
        operations += n
        if any(entry not in (1, modulus - 1) for entry in normalized):
            return None, {"operations": operations, "wall_clock_sec": time.perf_counter() - started}
        columns.append([1 if entry == 1 else -1 for entry in normalized])

    log_n = inst["log_n"]
    order = [-1] * n
    signs = [0] * n
    for physical in range(n):
        row = [columns[column][physical] for column in range(n)]
        sign = row[0]
        word = 0
        for bit in range(log_n):
            value = row[1 << bit] * sign
            operations += 1
            if value == -1:
                word |= 1 << bit
            elif value != 1:
                return None, {"operations": operations, "wall_clock_sec": time.perf_counter() - started}
        if order[word] != -1:
            return None, {"operations": operations, "wall_clock_sec": time.perf_counter() - started}
        order[word] = physical
        signs[word] = sign
    answer = {"row_for_word": order, "row_signs": signs}
    if not verify(inst, answer)[0]:
        return None, {"operations": operations, "wall_clock_sec": time.perf_counter() - started}
    return answer, {"operations": operations, "wall_clock_sec": time.perf_counter() - started}


def _compact_route(inst):
    """Recover the signed XOR coordinates from repeated quaternion classes."""
    started = time.perf_counter()
    n = inst["n"]
    matrix = _matrix_lookup(inst)
    class_at = {}
    transitions = [dict() for _ in range(n)]
    inspections = 0
    for (row, column), value in matrix.items():
        if row >= column:
            continue
        key, _ = _q_pm_key(value)
        class_at[key] = None
        transitions[row][key] = column
        transitions[column][key] = row
        inspections += 1
    classes = sorted(class_at)
    if len(classes) != inst["log_n"]:
        return None, {"operations": 0, "inspections": inspections, "wall_clock_sec": time.perf_counter() - started}

    root = 0
    kernels = {}
    for key in classes:
        other = transitions[root].get(key)
        if other is None:
            return None, {"operations": 0, "inspections": inspections, "wall_clock_sec": time.perf_counter() - started}
        kernels[key] = matrix[(root, other)]

    order = [-1] * n
    signs = [0] * n
    order[0] = root
    signs[0] = 1
    for word in range(1, n):
        lowest = word & -word
        bit = lowest.bit_length() - 1
        parent = word ^ lowest
        key = classes[bit]
        physical_parent = order[parent]
        physical = transitions[physical_parent].get(key)
        if physical is None:
            return None, {"operations": word - 1, "inspections": inspections, "wall_clock_sec": time.perf_counter() - started}
        value = matrix[(physical_parent, physical)]
        if value == kernels[key]:
            relative = 1
        elif value == _q_neg(kernels[key]):
            relative = -1
        else:
            return None, {"operations": word - 1, "inspections": inspections, "wall_clock_sec": time.perf_counter() - started}
        order[word] = physical
        signs[word] = signs[parent] * relative
    if len(set(order)) != n:
        return None, {"operations": n - 1, "inspections": inspections, "wall_clock_sec": time.perf_counter() - started}
    answer = {"row_for_word": order, "row_signs": signs}
    return answer, {
        "operations": n - 1,
        "inspections": inspections + inst["log_n"],
        "wall_clock_sec": time.perf_counter() - started,
    }


def _attack_outlier_row_order(inst):
    matrix = _matrix_lookup(inst)
    n = inst["n"]
    signatures = []
    for row in range(n):
        norms = sorted(_q_norm2(value) for (source, column), value in matrix.items() if source == row and column != row)
        signatures.append((norms, row))
    order = [row for _, row in sorted(signatures)]
    answer = {"row_for_word": order, "row_signs": [1] * n}
    return verify(inst, answer)[0]


def _attack_unsigned_coordinate_greedy(inst):
    answer, _ = _compact_route(inst)
    if answer is None:
        return False
    answer["row_signs"] = [1] * inst["n"]
    return verify(inst, answer)[0]


def _attack_random_restart(inst, seed):
    rng = random.Random(seed ^ 0x5A17D00D)
    for _ in range(256):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True
    return False


def _attack_separable_sign_ansatz(inst):
    answer, _ = _compact_route(inst)
    if answer is None:
        return False
    n = inst["n"]
    for mask in range(n):
        trial = {
            "row_for_word": list(answer["row_for_word"]),
            "row_signs": [1 if (mask & word).bit_count() % 2 == 0 else -1 for word in range(n)],
        }
        if verify(inst, trial)[0]:
            return True
    return False


def _transform_instance(inst, permutation, basis_signs, shuffle_seed):
    """Apply a real signed simultaneous row-column relabelling and carry P."""
    transformed = copy.deepcopy(inst)
    transformed.pop("_matrix_lookup_cache", None)
    transformed.pop("_candidate_support_order", None)
    entries = []
    for row, column, value in inst["quaternion_slice_entries"]:
        entries.append(
            [
                permutation[row],
                permutation[column],
                list(_q_scale(tuple(value), basis_signs[row] * basis_signs[column])),
            ]
        )
    random.Random(shuffle_seed).shuffle(entries)
    transformed["quaternion_slice_entries"] = entries

    old_order = inst["answer"]["row_for_word"]
    old_signs = inst["answer"]["row_signs"]
    new_order = [permutation[row] for row in old_order]
    new_signs = [old_signs[word] * basis_signs[old_order[word]] for word in range(inst["n"])]
    if new_signs[0] == -1:
        new_signs = [-value for value in new_signs]
    transformed["answer"] = {"row_for_word": new_order, "row_signs": new_signs}
    return transformed


def _answer_atoms(answer):
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, list):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def selftest():
    report = {}
    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=872341, **shipping_params)

    failures = []
    attempts = 0
    for preset, parameters in DIFFICULTY.items():
        for seed in (3, 19, 101):
            attempts += 1
            instance = make_instance(seed=seed, **parameters)
            ok, reason = verify(instance, instance["answer"])
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(instance["answer"])) != instance["answer"]:
                failures.append({"preset": preset, "seed": seed, "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
    }

    planted = copy.deepcopy(shipping["answer"])
    swapped = copy.deepcopy(planted)
    swap_found = False
    for left in range(shipping["n"]):
        for right in range(left + 1, shipping["n"]):
            swapped = copy.deepcopy(planted)
            swapped["row_for_word"][left], swapped["row_for_word"][right] = (
                swapped["row_for_word"][right],
                swapped["row_for_word"][left],
            )
            if not verify(shipping, swapped)[0]:
                swap_found = True
                break
        if swap_found:
            break
    corruptions = {
        "drop_one": {"row_for_word": planted["row_for_word"][:-1], "row_signs": planted["row_signs"]},
        "swap_two": swapped,
        "duplicate": {
            "row_for_word": [planted["row_for_word"][0], planted["row_for_word"][0]] + planted["row_for_word"][2:],
            "row_signs": planted["row_signs"],
        },
        "empty": [],
        "out_of_range": {
            "row_for_word": [shipping["n"]] + planted["row_for_word"][1:],
            "row_signs": planted["row_signs"],
        },
    }
    corruption_results = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_results[name] = {"accepted": ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": swap_found
        and all(not result["accepted"] for result in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The Walsh basis gives the following certificate.\n```json\n<answer>\n"
        + json.dumps(shipping["answer"])
        + "\n</answer>\n```\nThe entries are exact."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and verify(shipping, parsed)[0],
        "parsed": parsed == shipping["answer"],
    }

    sample_total = 200_000
    sample_hits = 0
    sample_rng = random.Random(604211)
    sample_started = time.perf_counter()
    for _ in range(sample_total):
        sample_hits += int(verify(shipping, random_candidate(shipping, sample_rng))[0])
    sample_wall = time.perf_counter() - sample_started
    report["G4_guess_resistance"] = {
        "pass": sample_hits / sample_total < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "observed_probability": sample_hits / sample_total,
        "construction_exact_probability": shipping["n"] / (1 << (shipping["n"] - 1)),
        "certificate_space": search_space(shipping),
        "wall_clock_sec": round(sample_wall, 6),
    }

    reference_answer, reference_stats = _reference_algorithm(shipping)
    compact_answer, compact_stats = _compact_route(shipping)
    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": demo_count is not None
        and reference_answer is not None
        and verify(shipping, reference_answer)[0]
        and compact_answer is not None
        and verify(shipping, compact_answer)[0],
        "shipping_density_hits": sample_hits,
        "shipping_density_samples": sample_total,
        "shipping_sampled_valid_fraction": sample_hits / sample_total,
        "shipping_construction_exact_valid_count": (
            shipping["n"] * math.factorial(shipping["log_n"]) * shipping["n"]
        ),
        "shipping_construction_exact_valid_fraction": (
            shipping["n"] / (1 << (shipping["n"] - 1))
        ),
        "demo_exact_solution_count": demo_count,
        "demo_certificate_space": search_space(demo),
        "reference_algorithm_operations": reference_stats["operations"],
        "reference_algorithm_wall_clock_sec": round(reference_stats["wall_clock_sec"], 6),
        "compact_route_operations": compact_stats["operations"],
        "compact_route_wall_clock_sec": round(compact_stats["wall_clock_sec"], 6),
    }

    attack_counts = {
        "outlier_row_norm_order": 0,
        "greedy_unsigned_xor_coordinates": 0,
        "random_restart_256": 0,
        "separable_character_sign_ansatz": 0,
    }
    reference_runs = []
    for seed in range(310, 318):
        attacked = make_instance(seed=seed, **shipping_params)
        attack_counts["outlier_row_norm_order"] += int(_attack_outlier_row_order(attacked))
        attack_counts["greedy_unsigned_xor_coordinates"] += int(_attack_unsigned_coordinate_greedy(attacked))
        attack_counts["random_restart_256"] += int(_attack_random_restart(attacked, seed))
        attack_counts["separable_character_sign_ansatz"] += int(_attack_separable_sign_ansatz(attacked))
        found, stats = _reference_algorithm(attacked)
        stats["solved"] = bool(found is not None and verify(attacked, found)[0])
        reference_runs.append(stats)
    attacks = {
        name: {"successes": successes, "attempts": 8}
        for name, successes in attack_counts.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(result["successes"] == 0 for result in attacks.values())
        and all(run["solved"] for run in reference_runs),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "real projection plus exact modular Lagrange spectral projectors",
            "complexity": "O(n^4) dense, O(n^3 log n) on the generated sparse slices",
            "operations": reference_stats["operations"],
            "max_operations": max(run["operations"] for run in reference_runs),
            "wall_clock_sec": round(reference_stats["wall_clock_sec"], 6),
            "max_wall_clock_sec": round(max(run["wall_clock_sec"] for run in reference_runs), 6),
            "solves": f"{sum(run['solved'] for run in reference_runs)}/8, as expected",
        },
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] = 2 * shipping_params["n"]
    doubled_params["height"] = shipping_params["height"] + 1
    doubled = make_instance(seed=991, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    doubled_compact, doubled_stats = _compact_route(doubled)
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled_compact is not None
        and verify(doubled, doubled_compact)[0]
        and search_space(doubled) > search_space(shipping),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "doubled_verify_reason": doubled_reason,
        "shipping_search_space_bits": search_space(shipping).bit_length(),
        "doubled_search_space_bits": search_space(doubled).bit_length(),
        "doubled_compact_operations": doubled_stats["operations"],
    }

    invariance_checks = 0
    carried_checks = 0
    key_failures = []
    unrelated_keys = set()
    for seed in range(20):
        instance = make_instance(seed=8000 + seed, **shipping_params)
        base_key = canonical_key(instance)
        unrelated_keys.add(base_key)
        rng = random.Random(9000 + seed)
        permutation = list(range(instance["n"]))
        rng.shuffle(permutation)
        basis_signs = [rng.choice((-1, 1)) for _ in range(instance["n"])]
        identity = list(range(instance["n"]))
        all_positive = [1] * instance["n"]
        variants = [
            _transform_instance(instance, permutation, all_positive, seed),
            _transform_instance(instance, identity, basis_signs, seed + 100),
            _transform_instance(instance, permutation, basis_signs, seed + 200),
        ]
        for variant in variants:
            invariance_checks += 1
            if canonical_key(variant) != base_key:
                key_failures.append({"seed": seed, "kind": "invariance"})
            carried_checks += 1
            if not verify(variant, variant["answer"])[0]:
                key_failures.append({"seed": seed, "kind": "carried_witness"})
    report["G8_canonical_key"] = {
        "pass": not key_failures and len(unrelated_keys) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "distinct_unrelated": len(unrelated_keys),
        "unrelated_attempts": 20,
        "transformations": [
            "simultaneous row-column permutation",
            "real diagonal sign conjugation",
            "their composition plus sparse-entry reordering",
        ],
        "failures": key_failures,
    }

    answer_blobs = [
        json.dumps(make_instance(seed=seed, **shipping_params)["answer"], separators=(",", ":"))
        for seed in range(100)
    ]
    answer_chars = max(map(len, answer_blobs))
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(shipping["answer"])
    arms = copy.deepcopy(G9_ORACLE_RESULTS)
    hinted_verdict = arms.pop("hinted_verdict", "not_run")
    hinted = arms["hinted"]
    placebo = arms["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else None
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else None
    diagnostic_complete = all(arms[name]["attempts"] >= 3 for name in ("bare", "hinted", "placebo"))
    compact_ok = compact_answer is not None and verify(shipping, compact_answer)[0]
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and compact_stats["operations"] <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps and compact_ok,
        "arms": arms,
        "diagnostic_complete": diagnostic_complete,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate if hinted_rate is not None and placebo_rate is not None else None
        ),
        "hinted_verdict": hinted_verdict,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": compact_stats["operations"],
        "intended_route_verified": compact_ok,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping_params)
    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
