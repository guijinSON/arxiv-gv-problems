"""Verified Track-B generator for arXiv:1604.02303.

The paper studies membership in semigroups of nonsingular 2 x 2 integer
matrices.  This module inverse-generates a target as a product of supplied
generators and asks for a generator word.  Every generator is a simultaneous
unimodular conjugate of [[B,d],[0,1]], but neither the conjugating matrix nor
the digits are disclosed.  A witness is checked only by exact multiplication.
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


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # pragma: no cover - this family remains stdlib-only
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "integer_lattice",
    "computational_core": "other",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "nonsingular 2 x 2 integer matrices",
        "matrix-semigroup generator word",
    ],
    "verification_operations": [
        "exact integer matrix multiplication",
        "exact matrix equality comparison",
        "generator-label validation",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Recognize the common rank-one affine line of the generators and use its "
        "coordinate as a base-det(G) digit; without that change of variables, "
        "bounded bidirectional product search enumerates exponentially many words."
    ),
    "hardness_basis": (
        "Track B: Theorem 1 gives an EXPSPACE decision procedure in general; for the "
        "fixed shipping length k=10, determinant-forced bidirectional meet-in-the-middle "
        "is O(n^5) and solved 8/8 instances at n=14 using 871,963 product nodes, about "
        "10,463,560 scalar operations, and 5.341744 seconds per instance on average, "
        "whereas recognizing and normalizing the common affine line gives an "
        "O(n log n+k) decoder using 181 exact arithmetic operations."
    ),
    "max_answer_tokens": 16,
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
    "demo": {"n": 4, "word_length": 3, "digit_bits": 5},
    "easy": {"n": 10, "word_length": 8, "digit_bits": 32},
    "medium": {"n": 12, "word_length": 10, "digit_bits": 40},
    "hard": {"n": 14, "word_length": 10, "digit_bits": 48},
}
SHIPPING_DIFFICULTY = "hard"


STRUCTURAL_HINT = (
    "All pairwise generator differences occupy one rank-one matrix direction "
    "associated with their common absolute determinant."
)
PLACEBO_HINT = (
    "All displayed matrix entries are exact signed integers whose multiplication "
    "order should be tracked with careful bookkeeping."
)


CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of exactly k generator labels from g00,...,g(n-1), with order "
        "significant and repetition allowed; determinant equality makes k freely "
        "deducible from the statement, so random_candidate samples all n^k such words."
    ),
    "bounds": {
        "max_word_tokens_at_named_presets": 10,
        "alphabet_size_at_named_presets": 14,
        "repetition_allowed": True,
        "ordered": True,
    },
}


NOTES = (
    "Section 2 fixes the native membership definition: the semigroup includes the "
    "identity and a positive-length generator word is a membership witness. Section "
    "3, Theorem 1 proves decidability for nonsingular 2x2 integer matrices and bounds "
    "the number of non-unimodular factors by log_2 |det(M)|. Its complexity remark "
    "places the full procedure in EXPSPACE. Section 3.1, Definition 4 and Proposition "
    "5/Corollary 6 give unique canonical words for GL(2,Z); Proposition 7 and "
    "Corollary 8 make the determinant-+-1 regime regular-language decidable. Those "
    "results rule out an honest Track-A claim here. Generation is inverse: sample a "
    "word, multiply its matrices, and retain that word without solving. The generated "
    "subclass has its own polynomial affine-coordinate decoder, so it is explicitly "
    "Track B. Simultaneous unimodular conjugation hides triangular coordinates, all "
    "generator digits come from the same distribution, and public generator order is "
    "shuffled. Every triangular digit is congruent modulo B^k, so the obvious "
    "left-division integrality test keeps every branch alive through depth k instead "
    "of leaking the next label. The attack panel checks that test as well as "
    "matrix-norm outliers, direct-distance greedy, uniform random restart, and a "
    "raw-entry radix ansatz. The successful bounded meet-in-the-middle algorithm is "
    "reported separately as the Track-B reference."
)


# Updated only after isolated harden.py runs.  A pending value deliberately makes
# G9 fail, preventing an unmeasured oracle claim from entering selftest_report.json.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 2_000_000
_IDENTITY = (1, 0, 0, 1)


def _mat_tuple(matrix):
    return (matrix[0][0], matrix[0][1], matrix[1][0], matrix[1][1])


def _mat_json(matrix):
    a, b, c, d = matrix
    return [[a, b], [c, d]]


def _mat_mul(left, right):
    a, b, c, d = left
    e, f, g, h = right
    return (
        a * e + b * g,
        a * f + b * h,
        c * e + d * g,
        c * f + d * h,
    )


def _mat_pow(matrix, exponent, counter=None):
    result = _IDENTITY
    base = matrix
    while exponent:
        if exponent & 1:
            result = _mat_mul(result, base)
            if counter is not None:
                counter["arithmetic_operations"] += 12
        exponent >>= 1
        if exponent:
            base = _mat_mul(base, base)
            if counter is not None:
                counter["arithmetic_operations"] += 12
    return result


def _det(matrix):
    a, b, c, d = matrix
    return a * d - b * c


def _egcd(a, b):
    old_r, r = a, b
    old_s, s = 1, 0
    old_t, t = 0, 1
    while r:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_s, s = s, old_s - q * s
        old_t, t = t, old_t - q * t
    return old_r, old_s, old_t


def _conjugator(rng):
    while True:
        p = rng.randint(2, 97)
        r = rng.randint(2, 97)
        if rng.randrange(2):
            p = -p
        if rng.randrange(2):
            r = -r
        gcd, s, t = _egcd(p, r)
        if gcd == -1:
            gcd, s, t = 1, -s, -t
        if gcd == 1:
            # p*s + r*t = 1, so [[p,-t],[r,s]] has determinant one.
            return (p, -t, r, s)


def _inverse_unimodular(matrix):
    a, b, c, d = matrix
    determinant = _det(matrix)
    if determinant not in (-1, 1):
        raise ValueError("matrix is not unimodular")
    return (d // determinant, -b // determinant,
            -c // determinant, a // determinant)


def _conjugate(matrix, basis):
    return _mat_mul(_mat_mul(basis, matrix), _inverse_unimodular(basis))


def _label(index, n):
    return "g" + str(index).zfill(max(2, len(str(n - 1))))


def _label_index(label, n):
    if not isinstance(label, str):
        return None
    width = max(2, len(str(n - 1)))
    if not re.fullmatch(r"g\d{" + str(width) + r"}", label):
        return None
    value = int(label[1:])
    return value if 0 <= value < n else None


def _validate_params(n, word_length, digit_bits):
    if isinstance(n, bool) or not isinstance(n, int) or n < 3:
        raise ValueError("n must be an integer at least 3")
    if isinstance(word_length, bool) or not isinstance(word_length, int) or word_length < 2:
        raise ValueError("word_length must be an integer at least 2")
    if word_length > 256:
        raise ValueError("word_length exceeds the 256-atom answer cap")
    if isinstance(digit_bits, bool) or not isinstance(digit_bits, int) or digit_bits < 4:
        raise ValueError("digit_bits must be an integer at least 4")
    if digit_bits > 512:
        raise ValueError("digit_bits may not exceed 512")
    if n > (1 << digit_bits):
        raise ValueError("the requested digit alphabet is too small for n generators")


def make_instance(n, seed=0, **params):
    """Inverse-generate a matrix-semigroup membership witness.

    ``n`` is the number of supplied generators.  ``word_length`` fixes the
    determinant-forced witness length, while ``digit_bits`` enlarges the exact
    arithmetic haystack without lengthening the answer.
    """
    unknown = set(params) - {"word_length", "digit_bits"}
    if unknown:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(unknown)))
    word_length = params.get("word_length", 10)
    digit_bits = params.get("digit_bits", 32)
    _validate_params(n, word_length, digit_bits)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    lower = 1 << (digit_bits - 1)
    base = rng.randrange(lower, 1 << digit_bits)
    if base <= n + 1:
        base = n + 2

    digits = [0, base - 1]
    if base - 2 <= sys.maxsize:
        interior = rng.sample(range(1, base - 1), n - 2)
    else:
        # random.sample(range(...)) asks len(range), which overflows Py_ssize_t
        # once escalation reaches a 64-bit radix. Direct rejection sampling
        # retains deterministic, uniform draws for the small n used here.
        interior = []
        selected = set()
        while len(interior) < n - 2:
            value = rng.randrange(1, base - 1)
            if value not in selected:
                selected.add(value)
                interior.append(value)
    digits.extend(interior)
    rng.shuffle(digits)

    # If the displayed triangular entries were the radix digits themselves, a
    # solver could peel the word from the left: exactly one G^{-1}*Target would
    # remain integral at each step. Put every entry in the same residue class
    # modulo B^k instead. After any t <= k proposed left factors, all n
    # quotients remain integral; a wrong branch is exposed only by the terminal
    # equality. Affine endpoint normalisation still recovers the hidden base-B
    # digits, because pairwise differences are B^k(e_i-e_j).
    camouflage_modulus = base ** word_length
    # A multiple of B-1 also makes digit complementation an actual integral
    # unimodular conjugation, which is one of canonical_key's normalisations.
    offset = (base - 1) * rng.randrange(camouflage_modulus // (base - 1))

    basis = _conjugator(rng)
    generators = []
    for digit in digits:
        triangular = (base, offset + camouflage_modulus * digit, 0, 1)
        generators.append(_conjugate(triangular, basis))

    word = [rng.randrange(n) for _ in range(word_length)]
    target = _IDENTITY
    for index in word:
        target = _mat_mul(target, generators[index])

    return {
        "family": "nonsingular_integer_matrix_semigroup_membership",
        "n": n,
        "word_length": word_length,
        "generators": [_mat_json(matrix) for matrix in generators],
        "target": _mat_json(target),
        "answer": [_label(index, n) for index in word],
    }


def render(inst):
    n = inst["n"]
    k = inst["word_length"]
    rows = []
    for index, matrix in enumerate(inst["generators"]):
        rows.append(f"  {_label(index, n)} = {matrix}")
    parts = [
        "Find a membership witness in a semigroup of nonsingular 2 x 2 integer matrices.\n\n",
        "Definitions. Multiplication is ordinary left-to-right matrix multiplication "
        "over the integers. The semigroup generated by the displayed matrices consists "
        "of the identity and every finite product of one or more generators; order "
        "matters and a generator may be repeated. A membership witness is the ordered "
        "word of generator labels whose product equals the target exactly. Matrix rows "
        "and entries are shown as [[a,b],[c,d]].\n\n",
        f"There are {n} generators. Their labels are g00 through {_label(n - 1, n)}.\n",
        "\n".join(rows),
        f"\n\nTarget = {inst['target']}\n\n",
        f"For this instance, the absolute determinant of every generator is the same "
        f"integer B>1, while |det(Target)|=B^{k}. Consequently every valid word has "
        f"exactly {k} labels. Return exactly {k} labels in multiplication order. "
        "Repetition is allowed; generator indices are 0-based; list order is significant.\n",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        parts.extend(["\nHint: ", STRUCTURAL_HINT, "\n"])
    elif mode == "placebo":
        parts.extend(["\nHint: ", PLACEBO_HINT, "\n"])
    parts.extend(
        [
            "\nGive your final answer inside <answer></answer> tags as a JSON list "
            "of quoted generator labels.\n",
            "Example format: <answer>"
            + json.dumps(
                [_label(position % n, n) for position in range(k)],
                separators=(",", ":"),
            )
            + "</answer>\n",
            "Output nothing else inside the tags.",
        ]
    )
    return "".join(parts)


def parse_answer(text):
    try:
        if not isinstance(text, str):
            return None
        match = _ANSWER_RE.search(text)
        if not match:
            return None
        body = match.group(1).strip()
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body).strip()
        if not body:
            return []
        try:
            value = json.loads(body)
        except (TypeError, ValueError):
            return None
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            return None
        return value
    except Exception:
        return None


def verify(inst, answer):
    n = inst["n"]
    k = inst["word_length"]
    if not isinstance(answer, list) or not all(isinstance(x, str) for x in answer):
        return False, "malformed answer: expected a JSON list of generator-label strings"
    if not answer:
        return False, "empty word: the target is not the identity matrix"
    if len(answer) != k:
        return False, f"wrong word length: determinants require {k} labels, got {len(answer)}"
    indices = []
    for position, token in enumerate(answer):
        index = _label_index(token, n)
        if index is None:
            return False, f"unknown generator label at position {position}: {token!r}"
        indices.append(index)
    product = _IDENTITY
    generators = [_mat_tuple(matrix) for matrix in inst["generators"]]
    for index in indices:
        product = _mat_mul(product, generators[index])
    target = _mat_tuple(inst["target"])
    if product != target:
        return False, f"product mismatch: obtained {_mat_json(product)}, not {inst['target']}"
    return True, "ok"


def random_candidate(inst, rng):
    n = inst["n"]
    return [_label(rng.randrange(n), n) for _ in range(inst["word_length"])]


def search_space(inst):
    return inst["n"] ** inst["word_length"]


def enumerate_all(inst):
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    n = inst["n"]
    valid = 0
    for word in itertools.product(range(n), repeat=inst["word_length"]):
        answer = [_label(index, n) for index in word]
        if verify(inst, answer)[0]:
            valid += 1
    return valid


def _affine_decode(inst, count_operations=False):
    """Recover a word using the hidden affine coordinate, never inst['answer']."""
    generators = [_mat_tuple(matrix) for matrix in inst["generators"]]
    target = _mat_tuple(inst["target"])
    n = len(generators)
    k = inst["word_length"]
    counter = {"arithmetic_operations": 0}

    base = abs(_det(generators[0]))
    counter["arithmetic_operations"] += 3
    if base <= 1 or any(abs(_det(matrix)) != base for matrix in generators):
        raise ValueError("generators do not have a common absolute determinant > 1")
    counter["arithmetic_operations"] += 3 * max(0, n - 1)

    coordinate = None
    values = None
    for position in range(4):
        trial = [matrix[position] for matrix in generators]
        if min(trial) != max(trial):
            coordinate, values = position, trial
            break
    if coordinate is None or values is None:
        raise ValueError("generator matrices do not span a nontrivial affine line")
    order = sorted(range(n), key=lambda index: values[index])
    low_index, high_index = order[0], order[-1]
    span = values[high_index] - values[low_index]
    digits = {}
    for index, value in enumerate(values):
        numerator = (value - values[low_index]) * (base - 1)
        counter["arithmetic_operations"] += 2
        digit, remainder = divmod(numerator, span)
        counter["arithmetic_operations"] += 1
        if remainder or not 0 <= digit < base or digit in digits:
            raise ValueError("generators are not distinct integral digits on the affine line")
        digits[digit] = index

    zero = generators[low_index]
    high = generators[high_index]
    direction = []
    for a, b in zip(high, zero):
        quotient, remainder = divmod(a - b, base - 1)
        counter["arithmetic_operations"] += 2
        if remainder:
            raise ValueError("affine endpoint difference is not divisible by B-1")
        direction.append(quotient)

    zero_power = _mat_pow(zero, k, counter)
    displacement = tuple(a - b for a, b in zip(target, zero_power))
    counter["arithmetic_operations"] += 4
    pivot = next((i for i, value in enumerate(direction) if value), None)
    if pivot is None:
        raise ValueError("zero affine direction")
    encoded, remainder = divmod(displacement[pivot], direction[pivot])
    counter["arithmetic_operations"] += 1
    if remainder or any(x != encoded * y for x, y in zip(displacement, direction)):
        raise ValueError("target is not on the induced length-k affine line")
    counter["arithmetic_operations"] += 4
    if not 0 <= encoded < base ** k:
        raise ValueError("target affine coordinate is outside the length-k radix range")

    indices = []
    word_digits = []
    for _ in range(k):
        digit, encoded = encoded % base, encoded // base
        counter["arithmetic_operations"] += 2
        if digit not in digits:
            raise ValueError("target digit is absent from the generator set")
        word_digits.append(digit)
        indices.append(digits[digit])
    if encoded:
        raise ValueError("target has more than k radix digits")
    answer = [_label(index, n) for index in indices]
    if not verify(inst, answer)[0]:
        # Transposition reverses multiplication.  The same affine-line invariant
        # therefore exposes the radix digits in the opposite order.
        indices.reverse()
        word_digits.reverse()
        answer = [_label(index, n) for index in indices]
        if not verify(inst, answer)[0]:
            raise ValueError("decoded word did not verify in either orientation")
    result = {
        "answer": answer,
        "base": base,
        "digits": sorted(digits),
        "word_digits": word_digits,
    }
    if count_operations:
        result.update(counter)
    return result


def canonical_key(inst):
    decoded = _affine_decode(inst)
    base = decoded["base"]
    digits = decoded["digits"]
    word = decoded["word_digits"]
    complement_digits = sorted(base - 1 - digit for digit in digits)
    complement_word = [base - 1 - digit for digit in word]
    # Complementing the affine coordinate is a unimodular change of basis.
    # Transposition is an anti-automorphism and carries a witness by reversing
    # its word, so reversal belongs in the normal form as well.
    orientation = min(
        (digits, word),
        (complement_digits, complement_word),
        (digits, list(reversed(word))),
        (complement_digits, list(reversed(complement_word))),
    )
    payload = [base, inst["word_length"], orientation[0], orientation[1]]
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


def escalate(params):
    harder = dict(params)
    harder["n"] = int(params.get("n", 10)) + 2
    harder["digit_bits"] = min(512, int(params.get("digit_bits", 32)) + 8)
    harder["word_length"] = int(params.get("word_length", 10))
    return harder


def _mitm_reference(inst):
    """Generic exact-length bidirectional search; intentionally ignores structure."""
    generators = [_mat_tuple(matrix) for matrix in inst["generators"]]
    target = _mat_tuple(inst["target"])
    n = len(generators)
    k = inst["word_length"]
    left_depth = k // 2
    right_depth = k - left_depth
    nodes = 0

    states = {_IDENTITY: 0}
    for _ in range(left_depth):
        following = {}
        for matrix, code in states.items():
            for index, generator in enumerate(generators):
                following[_mat_mul(matrix, generator)] = code * n + index
                nodes += 1
        states = following

    right_determinant = abs(_det(generators[0])) ** right_depth
    found = None

    def decode(code, length):
        values = [0] * length
        for position in range(length - 1, -1, -1):
            code, values[position] = divmod(code, n)
        return values

    def visit(depth, matrix, code):
        nonlocal nodes, found
        if found is not None:
            return
        if depth == right_depth:
            a, b, c, d = matrix
            adjugate = (d, -b, -c, a)
            numerator = _mat_mul(target, adjugate)
            if any(value % right_determinant for value in numerator):
                return
            needed = tuple(value // right_determinant for value in numerator)
            left_code = states.get(needed)
            if left_code is not None:
                found = decode(left_code, left_depth) + decode(code, right_depth)
            return
        for index, generator in enumerate(generators):
            nodes += 1
            visit(depth + 1, _mat_mul(matrix, generator), code * n + index)
            if found is not None:
                return

    visit(0, _IDENTITY, 0)
    answer = None if found is None else [_label(index, n) for index in found]
    return answer, nodes


def _attack_outlier_norm(inst, rng):
    del rng
    generators = [_mat_tuple(matrix) for matrix in inst["generators"]]
    index = min(range(inst["n"]), key=lambda i: sum(x * x for x in generators[i]))
    return [_label(index, inst["n"])] * inst["word_length"], 1


def _attack_direct_greedy(inst, rng):
    del rng
    generators = [_mat_tuple(matrix) for matrix in inst["generators"]]
    target = _mat_tuple(inst["target"])
    prefix = _IDENTITY
    word = []
    nodes = 0
    for _ in range(inst["word_length"]):
        trials = [_mat_mul(prefix, generator) for generator in generators]
        nodes += len(trials)
        index = min(
            range(inst["n"]),
            key=lambda i: sum(abs(a - b) for a, b in zip(trials[i], target)),
        )
        word.append(_label(index, inst["n"]))
        prefix = trials[index]
    return word, nodes


def _attack_random_restart(inst, rng, restarts=4096):
    for attempt in range(1, restarts + 1):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate, attempt
    return None, restarts


def _attack_raw_entry_radix(inst, rng):
    del rng
    base = abs(_det(_mat_tuple(inst["generators"][0])))
    value = abs(inst["target"][0][1])
    word = []
    for _ in range(inst["word_length"]):
        raw, value = value % base, value // base
        word.append(_label(raw % inst["n"], inst["n"]))
    return word, inst["word_length"] * 2


def _attack_integral_left_quotient(inst, rng):
    """Try the usual prefix test G^{-1}R integral, choosing the first tie."""
    del rng
    generators = [_mat_tuple(matrix) for matrix in inst["generators"]]
    residual = _mat_tuple(inst["target"])
    word = []
    nodes = 0
    for _ in range(inst["word_length"]):
        integral = []
        for index, generator in enumerate(generators):
            determinant = _det(generator)
            a, b, c, d = generator
            numerator = _mat_mul((d, -b, -c, a), residual)
            nodes += 1
            if all(value % determinant == 0 for value in numerator):
                quotient = tuple(value // determinant for value in numerator)
                integral.append((index, quotient))
        if not integral:
            return None, nodes
        index, residual = integral[0]
        word.append(_label(index, inst["n"]))
    return word, nodes


def _relabel_instance(inst, permutation):
    n = inst["n"]
    old_to_new = {old: new for new, old in enumerate(permutation)}
    answer = []
    for token in inst["answer"]:
        old = _label_index(token, n)
        answer.append(_label(old_to_new[old], n))
    return {
        **inst,
        "generators": [inst["generators"][old] for old in permutation],
        "answer": answer,
    }


def _conjugate_instance(inst, basis):
    return {
        **inst,
        "generators": [
            _mat_json(_conjugate(_mat_tuple(matrix), basis))
            for matrix in inst["generators"]
        ],
        "target": _mat_json(_conjugate(_mat_tuple(inst["target"]), basis)),
        "answer": list(inst["answer"]),
    }


def _transpose_instance(inst):
    def transpose(matrix):
        return [[matrix[0][0], matrix[1][0]], [matrix[0][1], matrix[1][1]]]

    return {
        **inst,
        "generators": [transpose(matrix) for matrix in inst["generators"]],
        "target": transpose(inst["target"]),
        "answer": list(reversed(inst["answer"])),
    }


def _answer_atoms(answer):
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, list):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def selftest():
    report = {}

    g1_checked = 0
    g1_ok = True
    json_ok = True
    for params in DIFFICULTY.values():
        for seed in range(5):
            inst = make_instance(seed=seed, **params)
            ok, _ = verify(inst, inst["answer"])
            g1_ok &= ok
            json_ok &= json.loads(json.dumps(inst["answer"])) == inst["answer"]
            g1_checked += 1
    report["G1_planted_verifies"] = {
        "pass": bool(g1_ok and json_ok),
        "instances_checked": g1_checked,
        "json_native_answers": bool(json_ok),
    }

    test_inst = make_instance(seed=90210, **DIFFICULTY["easy"])
    planted = list(test_inst["answer"])
    unequal = next(
        ((i, j) for i in range(len(planted)) for j in range(i + 1, len(planted))
         if planted[i] != planted[j]),
        None,
    )
    if unequal is None:
        replacement = _label((_label_index(planted[0], test_inst["n"]) + 1) % test_inst["n"], test_inst["n"])
        swapped = list(planted)
        swapped[0] = replacement
        duplicated = list(planted)
        duplicated[-1] = replacement
    else:
        i, j = unequal
        swapped = list(planted)
        swapped[i], swapped[j] = swapped[j], swapped[i]
        duplicated = list(planted)
        duplicated[j] = duplicated[i]
    corruptions = {
        "drop_one": planted[:-1],
        "swap_two": swapped,
        "duplicate_replacement": duplicated,
        "empty": [],
        "out_of_range": planted[:-1] + ["g999999"],
    }
    corruption_reasons = {}
    corruptions_rejected = True
    for name, answer in corruptions.items():
        ok, reason = verify(test_inst, answer)
        corruptions_rejected &= not ok
        corruption_reasons[name] = reason
    report["G2_rejects_corruption"] = {
        "pass": bool(corruptions_rejected and len(set(corruption_reasons.values())) == 5),
        "reasons": corruption_reasons,
        "distinct_reasons": len(set(corruption_reasons.values())),
    }

    model_response = (
        "I multiplied the factors in the stated order.\n\n```json\n<answer>"
        + json.dumps(planted)
        + "</answer>\n```\n"
    )
    parsed = parse_answer(model_response)
    garbage_rejected = parse_answer("<answer>not valid JSON</answer>") is None
    report["G3_round_trip"] = {
        "pass": parsed == planted and verify(test_inst, parsed)[0] and garbage_rejected,
        "model_style_response_parsed": parsed == planted,
        "garbage_returns_none": garbage_rejected,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=271828, **shipping_params)
    guess_rng = random.Random(314159)
    guess_total = 200_000
    guess_hits = 0
    guess_t0 = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_seconds = time.perf_counter() - guess_t0
    guess_density = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_total >= 200_000 and guess_density < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "sampled_probability": guess_density,
        "certificate_space": search_space(shipping),
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    attack_seeds = list(range(800, 808))
    attacks = {
        "outlier_smallest_frobenius": [_attack_outlier_norm, 0, 0, 0.0],
        "greedy_direct_target_distance": [_attack_direct_greedy, 0, 0, 0.0],
        "random_restart_4096": [_attack_random_restart, 0, 0, 0.0],
        "in_context_raw_entry_radix": [_attack_raw_entry_radix, 0, 0, 0.0],
        "greedy_first_integral_left_quotient": [
            _attack_integral_left_quotient, 0, 0, 0.0
        ],
    }
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **shipping_params)
        for offset, entry in enumerate(attacks.values()):
            attack = entry[0]
            t0 = time.perf_counter()
            candidate, nodes = attack(inst, random.Random(seed * 1009 + offset))
            entry[3] += time.perf_counter() - t0
            entry[2] += nodes
            if candidate is not None and verify(inst, candidate)[0]:
                entry[1] += 1

    attack_report = {}
    for name, (_, successes, nodes, seconds) in attacks.items():
        attack_report[name] = {
            "successes": successes,
            "attempts": len(attack_seeds),
            "nodes": nodes,
            "wall_clock_sec": round(seconds, 6),
        }

    # Exhaust the demo prefix tree and verify the congruence camouflage itself:
    # every proposed prefix, including every wrong one, leaves an integer
    # quotient. Only the planted terminal prefix leaves the identity.
    demo_generators = [_mat_tuple(matrix) for matrix in demo["generators"]]
    demo_target = _mat_tuple(demo["target"])
    camouflage_ok = True
    camouflage_prefix_states = 0
    camouflage_identity_terminals = 0
    for depth in range(demo["word_length"] + 1):
        for prefix in itertools.product(range(demo["n"]), repeat=depth):
            residual = demo_target
            for index in prefix:
                a, b, c, d = demo_generators[index]
                determinant = _det(demo_generators[index])
                numerator = _mat_mul((d, -b, -c, a), residual)
                if not all(value % determinant == 0 for value in numerator):
                    camouflage_ok = False
                    break
                residual = tuple(value // determinant for value in numerator)
            camouflage_prefix_states += 1
            if depth == demo["word_length"] and residual == _IDENTITY:
                camouflage_identity_terminals += 1

    reference_successes = 0
    reference_nodes = 0
    reference_seconds = 0.0
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **shipping_params)
        t0 = time.perf_counter()
        candidate, nodes = _mitm_reference(inst)
        reference_seconds += time.perf_counter() - t0
        reference_nodes += nodes
        if candidate is not None and verify(inst, candidate)[0]:
            reference_successes += 1

    all_attacks_failed = all(row["successes"] == 0 for row in attack_report.values())
    reference = {
        "name": "determinant-forced bidirectional meet-in-the-middle matrix-product search",
        "complexity": "O(n^(ceil(k/2))) exact matrix states",
        "wall_clock_sec": round(reference_seconds, 6),
        "average_wall_clock_sec": round(reference_seconds / len(attack_seeds), 6),
        "product_nodes": reference_nodes,
        "average_product_nodes": reference_nodes // len(attack_seeds),
        "exact_arithmetic_operations": reference_nodes * 12,
        "average_exact_arithmetic_operations": (
            reference_nodes * 12 // len(attack_seeds)
        ),
        "successes": reference_successes,
        "attempts": len(attack_seeds),
        "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
    }
    strongest_failing = max(
        attack_report.items(), key=lambda item: item[1]["nodes"]
    )[1]
    report["G5_density_and_baseline"] = {
        "pass": bool(
            demo_count == 1
            and guess_total >= 200_000
            and guess_density < 1e-6
            and reference_successes == len(attack_seeds)
        ),
        "shipping_density_hits": guess_hits,
        "shipping_density_sample_size": guess_total,
        "shipping_density_fraction": guess_density,
        "shipping_density_wall_sec": round(guess_seconds, 6),
        "demo_exact_valid_count": demo_count,
        "strongest_failing_attack_nodes": strongest_failing["nodes"],
        "strongest_failing_attack_wall_clock_sec": strongest_failing["wall_clock_sec"],
        "baseline_reference_product_nodes": reference_nodes,
        "baseline_reference_product_nodes_mean": (
            reference_nodes // len(attack_seeds)
        ),
        "baseline_reference_exact_operations": reference_nodes * 12,
        "baseline_reference_exact_operations_mean": (
            reference_nodes * 12 // len(attack_seeds)
        ),
        "baseline_reference_wall_clock_sec": round(reference_seconds, 6),
        "baseline_reference_wall_clock_sec_mean": round(
            reference_seconds / len(attack_seeds), 6
        ),
    }
    report["G6_adversary_panel"] = {
        "pass": bool(all_attacks_failed and len(attack_report) >= 4
                     and reference_successes == len(attack_seeds)
                     and camouflage_ok and camouflage_identity_terminals == 1),
        "attacks": attack_report,
        "reference_algorithm": reference,
        "integrality_camouflage_audit": {
            "demo_prefix_states_checked": camouflage_prefix_states,
            "all_prefix_quotients_integral": camouflage_ok,
            "identity_terminal_prefixes": camouflage_identity_terminals,
        },
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=1618, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": bool(doubled_ok and search_space(doubled) > search_space(shipping)),
        "shipping_n": shipping_params["n"],
        "doubled_n": doubled_params["n"],
        "shipping_search_space": search_space(shipping),
        "doubled_search_space": search_space(doubled),
        "answer_atoms_unchanged": len(doubled["answer"]) == len(shipping["answer"]),
    }

    invariant_checks = 0
    preservation_checks = 0
    invariant_ok = True
    preservation_ok = True
    unrelated_keys = []
    conjugating_basis = (1, 1, 1, 2)
    orientation_reversing_basis = (0, 1, 1, 0)
    for seed in range(20):
        inst = make_instance(seed=10_000 + seed, **shipping_params)
        key = canonical_key(inst)
        unrelated_keys.append(key)
        permutation = list(range(inst["n"]))
        random.Random(seed + 77).shuffle(permutation)
        relabelled = _relabel_instance(inst, permutation)
        conjugated = _conjugate_instance(inst, conjugating_basis)
        conjugated_det_minus_one = _conjugate_instance(inst, orientation_reversing_basis)
        composed = _conjugate_instance(relabelled, conjugating_basis)
        transposed = _transpose_instance(inst)
        for transformed in (
            relabelled,
            conjugated,
            conjugated_det_minus_one,
            composed,
            transposed,
        ):
            invariant_checks += 1
            invariant_ok &= canonical_key(transformed) == key
            preservation_checks += 1
            preservation_ok &= verify(transformed, transformed["answer"])[0]
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": bool(invariant_ok and preservation_ok and distinct_count == 20),
        "invariance_checks_passed": invariant_checks if invariant_ok else 0,
        "invariance_checks_total": invariant_checks,
        "witness_preservation_passed": preservation_checks if preservation_ok else 0,
        "witness_preservation_total": preservation_checks,
        "distinct_unrelated_keys": distinct_count,
        "unrelated_instances": 20,
        "transformations": [
            "generator relabelling",
            "simultaneous determinant +1 GL(2,Z) conjugation",
            "simultaneous determinant -1 GL(2,Z) conjugation",
            "composition of relabelling and conjugation",
            "matrix transposition with word reversal",
        ],
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    route = _affine_decode(shipping, count_operations=True)
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_verdict = G9_ORACLE_RESULTS.get("hinted_verdict")
    oracle_measured = all(arms[name]["attempts"] >= 3 for name in arms)
    within_caps = (
        len(answer_blob) <= 2000
        and _answer_atoms(shipping["answer"]) <= 256
        and route["arithmetic_operations"] <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": bool(oracle_measured and hinted_verdict == "hardened" and within_caps),
        "arms": arms,
        "hinted_minus_placebo": (
            arms["hinted"]["solved"] / arms["hinted"]["attempts"]
            - arms["placebo"]["solved"] / arms["placebo"]["attempts"]
            if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]
            else None
        ),
        "hinted_verdict": hinted_verdict,
        "answer_chars": len(answer_blob),
        "answer_tokens": math.ceil(len(answer_blob) / 4),
        "answer_elements": _answer_atoms(shipping["answer"]),
        "intended_route_operations": route["arithmetic_operations"],
        "route_answer_verifies": verify(shipping, route["answer"])[0],
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
