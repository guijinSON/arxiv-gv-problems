"""Native noisy-polynomial recovery generator for arXiv:1401.1331.

The unknown is the sparse polynomial a4*X^4+a3*X^3 over GF(p).  Its
coefficients are sampled first, and every published short-interval value is
then formed by adding a bounded integer error.  The certificate is therefore
known by inverse generation, never by decoding the completed instance.
"""

from __future__ import annotations

import hashlib
import json
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
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "polynomial",
    "native_objects": [
        "a sparse polynomial over GF(p) with known exponents 4 and 3",
        "noisy evaluations at integer points in a short interval",
        "the coefficient vector of the recovered finite-field polynomial",
    ],
    "verification_operations": [
        "exact modular exponentiation and addition",
        "centered residue distance comparison",
        "coefficient range and polynomial-shape checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Within one packet, the three arithmetic-progression triples have "
        "the same second finite difference of their error, so subtracting "
        "their second differences removes the noise; without recognizing "
        "that invariant one must perform bounded-distance decoding."
    ),
    "hardness_basis": (
        "Track B: Lemma 7 and Theorem 9 use fixed-dimensional exact CVP, "
        "polynomial in the input bit length; the executable two-unknown "
        "decoder costs O((2*Delta+1)^2*m) and at the hard preset measured "
        "117236 candidate error pairs, 938121 exact operations, and 1.262 "
        "seconds per instance on average, versus at most 294 operations for "
        "the compact packet second-difference route."
    ),
    "max_answer_tokens": 57,
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
        "A polynomial coefficient vector [a4,a3] with both coefficients "
        "integers in [0,p-1], denoting a4*X^4+a3*X^3 in GF(p)[X]."
    ),
    "bounds": {
        "coefficient_count": 2,
        "exponents_in_output_order": [4, 3],
        "coefficient_range": "0 through p-1 inclusive",
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 1, "p_bits": 7, "delta": 2, "h": 18},
    "easy": {"n": 2, "p_bits": 31, "delta": 31, "h": 300},
    "medium": {"n": 3, "p_bits": 61, "delta": 63, "h": 3000},
    "hard": {"n": 5, "p_bits": 89, "delta": 255, "h": 30000},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "One packet has a common error second difference across its three "
    "arithmetic-progression triples."
)
PLACEBO_HINT = (
    "One careful pass through the packets can help keep the modular "
    "arithmetic organized."
)

# Filled from script-owned harden.py transcripts after the three runs.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unavailable_http_403_key_limit",
}

NOTES = r"""
STEP 0.  Section 1.2 fixes the exact noisy interpolation object: GF(p) is
identified with residues 0,...,p-1, and |s-f(t)|_p is distance to the nearest
multiple of p.  It also explicitly discusses sparse polynomials with known
monomial degrees.  Theorem 9 in Section 4.1 is the decisive easy-result: in its
parameter regime a deterministic polynomial-time algorithm recovers the
polynomial with high probability.  Sections 3.1--3.2 say what produces the
answer: fixed-dimensional exact CVP in the displayed polynomial-evaluation
lattice.  Therefore this family is Track B and makes no Track A claim.

The construction stays in the paper's native objects.  It samples the two
coefficients of f(X)=a4*X^4+a3*X^3 first, places evaluation points in the short
integer interval [-h,h], samples bounded integer errors, and publishes the
noisy residues.  Section 5.2's discrete-difference viewpoint motivates the
planted invariant.  Each packet contains three length-three arithmetic
progressions.  In one hidden packet their error triples have a common second
difference.  Taking a second difference and subtracting between triples gives
two exact linear equations for a4,a3.  The other packets use identically
distributed individual error triples but independent second differences.

The reference decoder ignores packets.  It enumerates the allowed errors on
any two linearly independent observations, solves the resulting 2x2 system,
and checks every observation.  This is the two-unknown exact bounded-distance
specialization of the paper's lattice route and costs (2*Delta+1)^2 candidate
error pairs in the worst case.  The outlier attack uses the smallest centered
published residues; the greedy attack assumes two observations are exact; the
random restart guesses two allowed errors; and the by-hand ansatz drops one of
the two monomials.  All are checked on eight shipping seeds.
""".strip()


_MERSENNE_PRIMES = {
    7: (1 << 7) - 1,
    31: (1 << 31) - 1,
    61: (1 << 61) - 1,
    89: (1 << 89) - 1,
    107: (1 << 107) - 1,
    127: (1 << 127) - 1,
}


def _validate_params(n: int, p_bits: int, delta: int, h: int) -> None:
    values = (n, p_bits, delta, h)
    if any(isinstance(value, bool) or not isinstance(value, int)
           for value in values):
        raise ValueError("n, p_bits, delta, and h must be integers")
    if n < 1 or n > 40:
        raise ValueError("n must be between 1 and 40 packets")
    if p_bits not in _MERSENNE_PRIMES:
        raise ValueError("unsupported p_bits; use one of "
                         + repr(sorted(_MERSENNE_PRIMES)))
    p = _MERSENNE_PRIMES[p_bits]
    if delta < 1 or 2 * delta >= p:
        raise ValueError("delta must satisfy 1 <= delta < p/2")
    if h < 12 or 2 * h >= p:
        raise ValueError("h must satisfy 12 <= h < p/2")


def _basis_row(t: int, p: int) -> tuple[int, int]:
    return pow(t, 4, p), pow(t, 3, p)


def _det2(row1: tuple[int, int], row2: tuple[int, int], p: int) -> int:
    return (row1[0] * row2[1] - row1[1] * row2[0]) % p


def _solve2(row1: tuple[int, int], rhs1: int,
            row2: tuple[int, int], rhs2: int, p: int) -> list[int] | None:
    det = _det2(row1, row2, p)
    if det == 0:
        return None
    inv = pow(det, -1, p)
    a4 = (rhs1 * row2[1] - rhs2 * row1[1]) * inv % p
    a3 = (row1[0] * rhs2 - row2[0] * rhs1) * inv % p
    return [a4, a3]


def _packet_equation_rows(triples: list[list[list[int]]], p: int) -> tuple:
    """The two noise-cancelled equations derived from one packet."""
    derived = []
    for triple in triples:
        ordered = sorted(triple, key=lambda pair: pair[0])
        if len(ordered) != 3:
            return ()
        (t0, u0), (t1, u1), (t2, u2) = ordered
        if t1 - t0 != t2 - t1:
            return ()
        q = t1 - t0
        q2 = q * q
        midpoint = t1
        # Exact integer identities for the second forward differences.
        d4 = (12 * q2 * midpoint * midpoint + 2 * q2 * q2) % p
        d3 = (6 * q2 * midpoint) % p
        du = (u0 - 2 * u1 + u2) % p
        derived.append(((d4, d3), du))
    if len(derived) != 3:
        return ()
    row0, rhs0 = derived[0]
    out = []
    for row, rhs in derived[1:]:
        out.append(((row[0] - row0[0]) % p,
                    (row[1] - row0[1]) % p,
                    (rhs - rhs0) % p))
    return tuple(out)


def _draw_packet_points(rng: random.Random, h: int, p: int,
                        occupied: set[int]) -> list[list[list[int]]]:
    max_q = max(2, h // 20)
    for _ in range(10_000):
        q = rng.randint(1, max_q)
        starts = []
        used = set(occupied)
        for _slot in range(3):
            choices = []
            for _ in range(200):
                start = rng.randint(-h, h - 2 * q)
                points = {start, start + q, start + 2 * q}
                if len(points) == 3 and not (points & used):
                    choices.append(start)
                    break
            if not choices:
                break
            start = choices[0]
            starts.append(start)
            used.update((start, start + q, start + 2 * q))
        if len(starts) != 3:
            continue
        triples = [
            [[start, 0], [start + q, 0], [start + 2 * q, 0]]
            for start in starts
        ]
        equations = _packet_equation_rows(triples, p)
        if equations and _det2(equations[0][:2], equations[1][:2], p):
            occupied.update(used - occupied)
            return triples
    raise RuntimeError("could not place a nondegenerate packet in [-h,h]")


def _draw_error_triple(rng: random.Random, delta: int,
                       gamma: int | None = None) -> tuple[list[int], int]:
    span = max(1, delta // 4)
    for _ in range(10_000):
        g = gamma if gamma is not None else rng.randint(-span, span)
        alpha = rng.randint(-span, span)
        beta = rng.randint(-span, span)
        errors = [alpha, alpha + beta, alpha + 2 * beta + g]
        if all(-delta <= error <= delta for error in errors):
            return errors, g
    raise RuntimeError("could not draw a bounded correlated error triple")


def _flatten_samples(inst: dict) -> list[tuple[int, int]]:
    return [tuple(pair) for packet in inst["packets"]
            for triple in packet for pair in triple]


def make_instance(n: int, seed: int = 0, p_bits: int = 61,
                  delta: int = 63, h: int = 3000, **params) -> dict:
    """Inverse-generate a certified noisy short-interval interpolation task."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, p_bits, delta, h)
    rng = random.Random(seed)
    p = _MERSENNE_PRIMES[p_bits]

    # The answer is sampled before any observations exist.
    a4 = rng.randrange(1, p)
    a3 = rng.randrange(1, p)
    while a3 == a4:
        a3 = rng.randrange(1, p)

    special = rng.randrange(n)
    occupied: set[int] = set()
    packets = []
    for packet_index in range(n):
        triples = _draw_packet_points(rng, h, p, occupied)
        error_triples = []
        if packet_index == special:
            span = max(1, delta // 4)
            common_gamma = rng.choice(
                [value for value in range(-span, span + 1) if value != 0]
            )
            for _ in range(3):
                errors, _ = _draw_error_triple(rng, delta, common_gamma)
                error_triples.append(errors)
        else:
            while True:
                error_triples = []
                gammas = []
                for _ in range(3):
                    errors, gamma = _draw_error_triple(rng, delta)
                    error_triples.append(errors)
                    gammas.append(gamma)
                if len(set(gammas)) > 1:
                    break

        packet = []
        for point_triple, errors in zip(triples, error_triples):
            observed = []
            for pair, error in zip(point_triple, errors):
                t = pair[0]
                value = (a4 * pow(t, 4, p) + a3 * pow(t, 3, p) + error) % p
                observed.append([t, value])
            rng.shuffle(observed)
            packet.append(observed)
        rng.shuffle(packet)
        packets.append(packet)
    rng.shuffle(packets)

    inst = {
        "p": p,
        "p_bits": p_bits,
        "delta": delta,
        "h": h,
        "exponents": [4, 3],
        "packets": packets,
        "answer": [a4, a3],
    }
    ok, why = verify(inst, inst["answer"])
    if not ok:
        raise AssertionError("inverse construction failed: " + why)
    return inst


def render(inst: dict) -> str:
    """Render the complete native finite-field recovery problem."""
    lines = [
        "Recover a sparse polynomial over a prime finite field from noisy values",
        "",
        f"Let p = {inst['p']} (a prime). Identify GF(p) with the integers 0 through p-1.",
        "For an integer z, define its centered residue distance by",
        "    |z|_p = min(r, p-r), where r is the unique residue z mod p in 0..p-1.",
        f"The unknown polynomial is exactly f(X) = a4*X^4 + a3*X^3 in GF(p)[X].",
        "Both coefficients a4 and a3 are integers from 0 through p-1; all other coefficients are known to be zero.",
        f"Every evaluation point t is an ordinary integer in the inclusive short interval [-{inst['h']},{inst['h']}].",
        f"Each displayed pair (t,u) obeys |u - f(t)|_p <= Delta, where Delta = {inst['delta']}.",
        "Powers and arithmetic in f(t) are reduced modulo p. Negative t values are reduced modulo p in the usual way.",
        "Find any coefficient pair satisfying every displayed noisy evaluation.",
        "Packets, triples, and their order only lay out the supplied evaluations; validity is checked on every pair.",
        "",
        "Noisy evaluations (each triple contains three (t,u) pairs):",
    ]
    for packet_index, packet in enumerate(inst["packets"], 1):
        lines.append(f"Packet {packet_index}:")
        for triple_index, triple in enumerate(packet, 1):
            body = "  ".join(f"({t},{u})" for t, u in triple)
            lines.append(f"  Triple {triple_index}: {body}")
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags as the JSON list [a4,a3], in that order.",
        "The list must contain exactly two base-10 integers, each in 0..p-1; repeats are allowed.",
        "Example: <answer>[17,42]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: object) -> object | None:
    """Parse one tagged JSON coefficient vector; never raise on junk."""
    try:
        if not isinstance(text, str):
            return None
        match = re.search(r"<answer>(.*?)</answer>", text,
                          flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        body = match.group(1).strip()
        body = re.sub(r"^```(?:json)?\s*", "", body,
                      flags=re.IGNORECASE)
        body = re.sub(r"\s*```$", "", body).strip()
        value = json.loads(body)
        if (not isinstance(value, list)
                or any(isinstance(x, bool) or not isinstance(x, int)
                       for x in value)):
            return None
        return value
    except (ValueError, TypeError, OverflowError):
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid polynomial witness without consulting inst['answer']."""
    if not isinstance(answer, list):
        return False, "malformed: expected the JSON list [a4,a3]"
    if len(answer) == 0:
        return False, "empty answer: expected exactly two coefficients"
    if len(answer) != 2:
        return False, f"wrong length: expected 2 coefficients, got {len(answer)}"
    if any(isinstance(value, bool) or not isinstance(value, int)
           for value in answer):
        return False, "malformed coefficient: both entries must be integers"
    p = inst["p"]
    for index, value in enumerate(answer):
        if value < 0 or value >= p:
            return False, (f"coefficient out of range: entry {index} is {value}, "
                           f"not in 0..{p - 1}")
    a4, a3 = answer
    delta = inst["delta"]
    for packet_index, packet in enumerate(inst["packets"]):
        for triple_index, triple in enumerate(packet):
            for sample_index, (t, observed) in enumerate(triple):
                predicted = (a4 * pow(t, 4, p) + a3 * pow(t, 3, p)) % p
                residue = (observed - predicted) % p
                distance = min(residue, p - residue)
                if distance > delta:
                    return False, (
                        f"sample {packet_index}:{triple_index}:{sample_index} "
                        f"has centered distance {distance} > {delta}"
                    )
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the statement's promised two-coefficient language."""
    p = inst["p"]
    return [rng.randrange(p), rng.randrange(p)]


def search_space(inst: dict) -> int | None:
    return inst["p"] ** 2


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space is None or space > 50_000:
        return None
    count = 0
    for a4 in range(inst["p"]):
        for a3 in range(inst["p"]):
            count += int(verify(inst, [a4, a3])[0])
    return count


def canonical_key(inst: dict) -> str:
    """Canonicalize input order and the interval reflection t -> -t."""
    samples = sorted(_flatten_samples(inst))
    reflected = sorted((-t, u) for t, u in samples)
    chosen = min(samples, reflected)
    payload = {
        "p": inst["p"],
        "delta": inst["delta"],
        "h": inst["h"],
        "exponents": [4, 3],
        "samples": chosen,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow error-search width and packet crowding at fixed answer length."""
    out = {key: value for key, value in params.items() if key != "_preset"}
    bits = out.get("p_bits", 61)
    bit_ladder = [7, 31, 61, 89, 107, 127]
    if bits not in bit_ladder:
        return None
    if bits != 127:
        out["p_bits"] = bit_ladder[bit_ladder.index(bits) + 1]
    out["delta"] = 2 * out.get("delta", 63) + 1
    out["h"] = 2 * out.get("h", 3000)
    out["n"] = min(8, out.get("n", 3) + 1)
    if out["n"] == params.get("n") and bits == 127:
        # Delta can still grow without changing the two-atom answer.
        if out["delta"] >= (1 << 20):
            return "cap_bound"
    return out


def _independent_pair(inst: dict,
                      samples: list[tuple[int, int]] | None = None) -> tuple:
    samples = samples or _flatten_samples(inst)
    p = inst["p"]
    rows = [_basis_row(t, p) for t, _ in samples]
    for i in range(len(samples)):
        for j in range(i + 1, len(samples)):
            if _det2(rows[i], rows[j], p):
                return samples[i], rows[i], samples[j], rows[j]
    raise RuntimeError("instance has no independent observation pair")


def _reference_algorithm(inst: dict) -> dict:
    """Exact two-error bounded-distance decoding, independent of packets."""
    start = time.perf_counter()
    p, delta = inst["p"], inst["delta"]
    samples = _flatten_samples(inst)
    first, row1, second, row2 = _independent_pair(inst, samples)
    det_inv = pow(_det2(row1, row2, p), -1, p)
    prepared = [(t, u, *_basis_row(t, p)) for t, u in samples
                if (t, u) not in (first, second)]
    candidates = 0
    sample_checks = 0
    answer = None
    for error1 in range(-delta, delta + 1):
        rhs1 = (first[1] - error1) % p
        left_a = rhs1 * row2[1]
        left_b = row2[0] * rhs1
        for error2 in range(-delta, delta + 1):
            candidates += 1
            rhs2 = (second[1] - error2) % p
            a4 = (left_a - rhs2 * row1[1]) * det_inv % p
            a3 = (row1[0] * rhs2 - left_b) * det_inv % p
            valid = True
            for _t, observed, t4, t3 in prepared:
                sample_checks += 1
                predicted = (a4 * t4 + a3 * t3) % p
                residue = (observed - predicted) % p
                if min(residue, p - residue) > delta:
                    valid = False
                    break
            if valid:
                candidate = [a4, a3]
                if verify(inst, candidate)[0]:
                    answer = candidate
                    break
        if answer is not None:
            break
    # Conservative exact-operation accounting for the implemented loops.
    operations = 3 * candidates + 5 * sample_checks + 20
    return {
        "answer": answer,
        "ok": answer is not None and verify(inst, answer)[0],
        "candidate_error_pairs": candidates,
        "sample_checks": sample_checks,
        "operations": operations,
        "wall_clock_sec": time.perf_counter() - start,
    }


def _quick_crosscheck(inst: dict, candidate: list[int],
                      excluded_packet: int, limit: int = 4) -> tuple[bool, int]:
    checked = 0
    operations = 0
    p, delta = inst["p"], inst["delta"]
    a4, a3 = candidate
    for packet_index, packet in enumerate(inst["packets"]):
        if packet_index == excluded_packet:
            continue
        for triple in packet:
            for t, observed in triple:
                t2 = t * t % p
                t3 = t2 * t % p
                t4 = t2 * t2 % p
                predicted = (a4 * t4 + a3 * t3) % p
                residue = (observed - predicted) % p
                operations += 8
                checked += 1
                if min(residue, p - residue) > delta:
                    return False, operations
                if checked >= limit:
                    return True, operations
    return True, operations


def _compact_decode(inst: dict) -> dict:
    """Decode through the planted second-difference invariant."""
    start = time.perf_counter()
    p = inst["p"]
    operations = 0
    answer = None
    packets_examined = 0
    for packet_index, packet in enumerate(inst["packets"]):
        packets_examined += 1
        equations = _packet_equation_rows(packet, p)
        # Per packet: derive q^2/q^4 once, three closed-form monomial second
        # differences, three observed second differences, and two subtractions.
        operations += 34
        if not equations:
            continue
        row1 = equations[0][:2]
        row2 = equations[1][:2]
        candidate = _solve2(row1, equations[0][2],
                            row2, equations[1][2], p)
        operations += 12
        if candidate is None:
            continue
        plausible, used = _quick_crosscheck(inst, candidate, packet_index)
        operations += used
        if plausible and verify(inst, candidate)[0]:
            answer = candidate
            break
    return {
        "answer": answer,
        "ok": answer is not None and verify(inst, answer)[0],
        "operations": operations,
        "packets_examined": packets_examined,
        "wall_clock_sec": time.perf_counter() - start,
    }


def _attack_zero_noise_pair(inst: dict,
                            samples: list[tuple[int, int]] | None = None) -> object:
    first, row1, second, row2 = _independent_pair(inst, samples)
    return _solve2(row1, first[1], row2, second[1], inst["p"])


def _attack_outlier_small_residue(inst: dict) -> object:
    p = inst["p"]
    samples = sorted(_flatten_samples(inst),
                     key=lambda pair: (min(pair[1], p - pair[1]),
                                       abs(pair[0]), pair))
    try:
        return _attack_zero_noise_pair(inst, samples)
    except RuntimeError:
        return [0, 0]


def _attack_random_restart(inst: dict, seed: int,
                           restarts: int = 256) -> object:
    rng = random.Random(seed ^ 0x14011331)
    first, row1, second, row2 = _independent_pair(inst)
    last = [0, 0]
    for _ in range(restarts):
        error1 = rng.randint(-inst["delta"], inst["delta"])
        error2 = rng.randint(-inst["delta"], inst["delta"])
        last = _solve2(row1, (first[1] - error1) % inst["p"],
                       row2, (second[1] - error2) % inst["p"], inst["p"])
        if last is not None and verify(inst, last)[0]:
            return last
    return last


def _attack_single_monomial(inst: dict) -> object:
    p = inst["p"]
    last = [0, 0]
    for t, observed in _flatten_samples(inst)[:12]:
        t4, t3 = _basis_row(t, p)
        if t4:
            last = [observed * pow(t4, -1, p) % p, 0]
            if verify(inst, last)[0]:
                return last
        if t3:
            last = [0, observed * pow(t3, -1, p) % p]
            if verify(inst, last)[0]:
                return last
    return last


def _reordered_instance(inst: dict, rng: random.Random) -> dict:
    moved = {key: value for key, value in inst.items() if key != "packets"}
    packets = []
    for source_packet in inst["packets"]:
        packet = []
        for source_triple in source_packet:
            triple = [list(pair) for pair in source_triple]
            rng.shuffle(triple)
            packet.append(triple)
        rng.shuffle(packet)
        packets.append(packet)
    rng.shuffle(packets)
    moved["packets"] = packets
    return moved


def _reflected_instance(inst: dict) -> tuple[dict, list[int]]:
    moved = {key: value for key, value in inst.items()
             if key not in ("packets", "answer")}
    moved["packets"] = [
        [[[-t, u] for t, u in triple] for triple in packet]
        for packet in inst["packets"]
    ]
    carried = [inst["answer"][0], (-inst["answer"][1]) % inst["p"]]
    moved["answer"] = carried
    return moved, carried


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))
    # Character count is a conservative tokenizer-independent token bound.
    return len(encoded), len(encoded), 2


def selftest() -> dict:
    """Run all mandatory gates and return JSON-native measured evidence."""
    report: dict = {}

    checks = 0
    failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 99):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            json_ok = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            checks += 1
            if not (ok and json_ok):
                failures.append({"preset": preset, "seed": seed,
                                 "reason": why, "json_native": json_ok})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checks": checks,
        "failures": failures,
        "generation_route": "inverse generation of coefficients and bounded errors",
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **ship_params)
    a4, a3 = inst["answer"]
    corruptions = {
        "drop_one": [a4],
        "swap_order": [a3, a4],
        "duplicate": [a4, a4],
        "empty": [],
        "out_of_range": [inst["p"], a3],
    }
    reasons = {}
    rejected = True
    for name, bad in corruptions.items():
        ok, why = verify(inst, bad)
        rejected &= not ok
        reasons[name] = why
    distinct = len(set(reasons.values())) == len(corruptions)
    report["G2_rejects_corruption"] = {
        "pass": rejected and distinct,
        "rejections": reasons,
        "distinct_reasons": len(set(reasons.values())),
    }

    realistic = (
        "The common second difference gave two exact equations.\n\n"
        "```json\n"
        f"<answer>{json.dumps(inst['answer'])}</answer>\n"
        "```\nThe entries are in [a4,a3] order."
    )
    parsed = parse_answer(realistic)
    garbage_none = parse_answer("No final tagged answer was produced.") is None
    report["G3_round_trip"] = {
        "pass": (parsed == inst["answer"] and verify(inst, parsed)[0]
                 and garbage_none),
        "parsed_matches": parsed == inst["answer"],
        "garbage_returns_none": garbage_none,
        "json_native": True,
    }

    guess_rng = random.Random(0x14011331)
    guess_total = 200_000
    guess_hits = 0
    guess_start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - guess_start
    density = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": density < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "empirical_probability": density,
        "structure_aware_space": search_space(inst),
        "prior": "uniform over both promised GF(p) coefficients",
        "sampling_wall_seconds": guess_seconds,
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": density < 1e-6 and demo_count is not None,
        "shipping_observed_valid_fraction": density,
        "shipping_density_sample_count": guess_total,
        "shipping_valid_hits": guess_hits,
        "shipping_candidate_space": search_space(inst),
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo),
    }

    attack_successes = {
        "outlier_smallest_centered_residues": 0,
        "greedy_assume_two_exact_samples": 0,
        "random_restart_256_bounded_errors": 0,
        "by_hand_single_monomial_ansatz": 0,
    }
    reference_runs = []
    compact_runs = []
    for seed in range(100, 108):
        trial = make_instance(seed=seed, **ship_params)
        attack_successes["outlier_smallest_centered_residues"] += int(
            verify(trial, _attack_outlier_small_residue(trial))[0])
        attack_successes["greedy_assume_two_exact_samples"] += int(
            verify(trial, _attack_zero_noise_pair(trial))[0])
        attack_successes["random_restart_256_bounded_errors"] += int(
            verify(trial, _attack_random_restart(trial, seed))[0])
        attack_successes["by_hand_single_monomial_ansatz"] += int(
            verify(trial, _attack_single_monomial(trial))[0])
        reference_runs.append(_reference_algorithm(trial))
        compact_runs.append(_compact_decode(trial))
    ref_ok = sum(int(run["ok"]) for run in reference_runs)
    compact_ok = sum(int(run["ok"]) for run in compact_runs)
    ref_wall = sum(run["wall_clock_sec"] for run in reference_runs)
    ref_operations = sum(run["operations"] for run in reference_runs)
    ref_pairs = sum(run["candidate_error_pairs"] for run in reference_runs)
    ref_checks = sum(run["sample_checks"] for run in reference_runs)
    compact_wall = sum(run["wall_clock_sec"] for run in compact_runs)
    compact_max_ops = max(run["operations"] for run in compact_runs)
    all_attacks_failed = all(value == 0 for value in attack_successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and ref_ok == 8 and compact_ok == 8,
        "attacks": {
            name: {"successes": successes, "attempts": 8}
            for name, successes in attack_successes.items()
        },
        "reference_algorithm": {
            "name": "two-error exhaustive bounded-distance decoder",
            "paper_connection": "the two-unknown specialization of Sections 3.2--4.1 exact CVP decoding",
            "complexity": "O((2*Delta+1)^2*m) exact modular operations",
            "wall_clock_sec": ref_wall,
            "mean_wall_clock_sec": ref_wall / 8,
            "candidate_error_pairs": ref_pairs,
            "mean_candidate_error_pairs": ref_pairs / 8,
            "sample_checks": ref_checks,
            "operations": ref_operations,
            "mean_operations": ref_operations // 8,
            "solves": f"{ref_ok}/8, as expected",
        },
        "compact_route": {
            "name": "common second finite difference and two 2x2 equations",
            "wall_clock_sec": compact_wall,
            "max_exact_operations": compact_max_ops,
            "solves": f"{compact_ok}/8",
        },
    }
    report["G5_density_and_baseline_cost"].update({
        "reference_algorithm_wall_seconds": ref_wall,
        "reference_algorithm_mean_wall_seconds": ref_wall / 8,
        "reference_algorithm_candidate_error_pairs": ref_pairs,
        "reference_algorithm_mean_candidate_error_pairs": ref_pairs / 8,
        "reference_algorithm_operations": ref_operations,
        "reference_algorithm_mean_operations": ref_operations // 8,
    })
    report["G5_density_and_baseline_cost"]["pass"] &= ref_ok == 8

    doubled = make_instance(n=2 * ship_params["n"], seed=77,
                            p_bits=ship_params["p_bits"],
                            delta=ship_params["delta"],
                            h=2 * ship_params["h"])
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and len(doubled["packets"]) == 2 * ship_params["n"],
        "base_n": ship_params["n"],
        "doubled_n": len(doubled["packets"]),
        "base_samples": 9 * ship_params["n"],
        "doubled_samples": len(_flatten_samples(doubled)),
        "doubled_verify": doubled_why,
        "answer_elements_unchanged": len(doubled["answer"]) == 2,
    }

    invariance_ok = 0
    witness_ok = 0
    attempts = 0
    for seed in range(20):
        trial = make_instance(seed=700 + seed, **ship_params)
        reordered = _reordered_instance(trial, random.Random(seed))
        reflected, carried = _reflected_instance(trial)
        composed = _reordered_instance(reflected, random.Random(seed + 1000))
        for moved, witness in ((reordered, trial["answer"]),
                               (reflected, carried),
                               (composed, carried)):
            attempts += 1
            invariance_ok += int(canonical_key(moved) == canonical_key(trial))
            witness_ok += int(verify(moved, witness)[0])
    unrelated = {
        canonical_key(make_instance(seed=9000 + seed, **ship_params))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": (invariance_ok == attempts and witness_ok == attempts
                 and len(unrelated) == 20),
        "invariance_checks": invariance_ok,
        "invariance_attempts": attempts,
        "transformed_witness_checks": witness_ok,
        "transformed_witness_attempts": attempts,
        "unrelated_distinct": len(unrelated),
        "unrelated_attempts": 20,
        "transformations": (
            "packet/triple/sample reorder, interval reflection t -> -t, "
            "and their composition"
        ),
    }

    chars, tokens, elements = _answer_metrics(inst["answer"])
    evidence = G9_EVIDENCE
    hinted_attempts = evidence["hinted"]["attempts"]
    placebo_attempts = evidence["placebo"]["attempts"]
    hinted_rate = (evidence["hinted"]["solved"] / hinted_attempts
                   if hinted_attempts else 0.0)
    placebo_rate = (evidence["placebo"]["solved"] / placebo_attempts
                    if placebo_attempts else 0.0)
    within_caps = (chars <= 2000 and tokens <= 500 and elements <= 256
                   and compact_max_ops <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": {
            "bare": dict(evidence["bare"]),
            "hinted": dict(evidence["hinted"]),
            "placebo": dict(evidence["placebo"]),
        },
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": evidence["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": compact_max_ops,
        "caps": {"chars": 2000, "tokens": 500,
                 "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(ship_params)
    report["certificate_language"] = CERTIFICATE_LANGUAGE
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    report["oracle_evidence_complete"] = False
    report["oracle_blocker"] = (
        "The bare easy arm completed (1/3 solved), but OpenRouter then "
        "returned HTTP 403 Key limit exceeded before medium; both shipping "
        "G9 arms likewise contain API errors only. No shipping hardness "
        "verdict is claimed."
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=False))
