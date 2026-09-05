"""Self-contained verified problem generator for arXiv:1206.2611.

Lam and Pylyavskyy classify rank-two Laurent phenomenon (LP) algebras of
finite type.  In their cubic case (b,c)=(1,3), mutation preserves a ten-role
exchange-polynomial template and acts on the roles through two permutations
generating a dihedral group of order eight.  This module makes exact symbolic
word problems in that native coefficient dynamics.

Generation is inverse: choose each final dihedral state first, construct two
compressed mutation blocks whose product is that state, and carry the paper's
coefficient-role certificate into a monomial fingerprint.  No generated word
is solved in order to obtain its answer.
"""

from __future__ import annotations

import copy
import functools
import hashlib
import itertools
import json
import math
import os
import random
import re
import statistics
import sys
import time


# The prompt's suggested path has three parents, while this checkout has two.
# Add both possible repository roots and remain standard-library-only if gvlib
# is absent.  gvlib is used at the untrusted polynomial boundary when present.
_HERE = os.path.abspath(__file__)
_ROOT_TWO = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
_ROOT_THREE = os.path.dirname(_ROOT_TWO)
for _root in (_ROOT_TWO, _ROOT_THREE):
    if _root not in sys.path:
        sys.path.insert(0, _root)
try:
    from gvlib import rationals, sparse_poly
except ImportError:  # pragma: no cover - exercised only outside this repository
    rationals = sparse_poly = None


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "The coefficient-role permutations of each cubic rank-two component form "
    "a dihedral group of order eight."
)
PLACEBO_HINT: str = (
    "The coefficient exponents of each cubic rank-two component require "
    "careful attention throughout the calculation."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "polynomial_identity",
    "certificate_form": "polynomial",
    "native_objects": [
        "rank-two Laurent phenomenon algebra seeds over a polynomial UFD",
        "irreducible cubic and linear exchange polynomials",
        "compressed mutation words",
        "exact monomial fingerprints of exchange-polynomial coefficients",
    ],
    "verification_operations": [
        "exact coefficient-role permutation",
        "integer exponent addition and multiplication",
        "exact sparse-polynomial normalization",
        "exact monomial equality",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "The cubic rank-two coefficient mutations form a small dihedral action; "
        "without recognizing it, the compressed powers expand to millions of "
        "successive exact mutations."
    ),
    "hardness_basis": (
        "Track B: successive Section 6 cubic coefficient mutation is linear in "
        "the expanded word length; at the shipping easy preset the reference "
        "median is 52,402 mutation symbols, 185,028 exact role swaps, and "
        "0.00231 seconds over eight seeds, whereas dihedral block evaluation "
        "and fingerprint assembly use at most 229 exact operations."
    ),
    "max_answer_tokens": 73,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {"medium": {"n": 500, "components": 8, "base_len": 7}}
SHIPPING_DIFFICULTY: str = "medium"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "One coefficient-1 monomial over 11 formal coefficient atoms per "
        "component, serialized as [[[1,1],[e0,e1,...]]].  For each component "
        "the exponent block must be one of the eight fingerprints reachable by "
        "the cubic rank-two coefficient action."
    ),
    "bounds": {
        "terms": 1,
        "coefficient": [1, 1],
        "atoms_per_component": 11,
        "reachable_blocks_per_component": 8,
        "max_components": 16,
        "max_role_exponent": 3,
        "max_output_exponent": 294,
    },
}

NOTES: str = (
    "Section 2.1 fixes an LP seed and the irreducibility/no-self-variable "
    "conditions (LP1--LP2). Section 2.2 gives substitution, common-factor "
    "removal, and monomial normalization for mutation; Proposition 2.11 proves "
    "mutation is involutive. Theorem 5.1 supplies Laurentness. Section 6, "
    "Theorem 6.4 identifies the easy finite rank-two regimes b=0 and "
    "(b,c)=(1,1),(1,2),(1,3); the generator deliberately uses the richest "
    "cubic case. In its proof the two mutations permute coefficient roles by "
    "(DG)(EF)(KL) and (AD)(BC)(FK)(GH), and the generated group has order "
    "eight; the paper calls direct rational wraparound verification very "
    "involved. Initial, last-block, commuting-parity, and random-restart "
    "attacks are defeated by choosing each endpoint uniformly before sampling "
    "conditioned blocks. The successful successive-mutation algorithm is "
    "reported separately, as Track B requires."
)


# Filled from the three harden.py runs after the bare and G9 arms complete.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


# ---------------------------------------------------------------------------
# The exact order-eight coefficient action from the proof of Theorem 6.4.

ROLES = ("A", "B", "C", "D", "E", "F", "G", "H", "K", "L")
ROLE_INDEX = {name: i for i, name in enumerate(ROLES)}
GENERATOR_PAIRS = {
    1: (("D", "G"), ("E", "F"), ("K", "L")),
    2: (("A", "D"), ("B", "C"), ("F", "K"), ("G", "H")),
}


def _apply_generator_tuple(state: tuple[str, ...], symbol: int) -> tuple[str, ...]:
    out = list(state)
    for left, right in GENERATOR_PAIRS[symbol]:
        i, j = ROLE_INDEX[left], ROLE_INDEX[right]
        out[i], out[j] = out[j], out[i]
    return tuple(out)


def _build_group() -> tuple[tuple[tuple[str, ...], ...], dict, list]:
    identity = tuple(ROLES)
    states = [identity]
    index = {identity: 0}
    cursor = 0
    while cursor < len(states):
        state = states[cursor]
        cursor += 1
        for symbol in (1, 2):
            nxt = _apply_generator_tuple(state, symbol)
            if nxt not in index:
                index[nxt] = len(states)
                states.append(nxt)
    if len(states) != 8:
        raise RuntimeError("the cubic coefficient action should have order eight")

    transitions = []
    for state in states:
        transitions.append(
            {symbol: index[_apply_generator_tuple(state, symbol)] for symbol in (1, 2)}
        )

    # If transformations first and second are executed in that order, the
    # source position for the composite is first[second[position]].
    compose = [[0] * len(states) for _ in states]
    for i, first in enumerate(states):
        for j, second in enumerate(states):
            combined = tuple(first[ROLE_INDEX[second[pos]]] for pos in range(len(ROLES)))
            compose[i][j] = index[combined]
    return tuple(states), index, transitions, compose


GROUP_STATES, _GROUP_INDEX, TRANSITIONS, COMPOSE = _build_group()
del _GROUP_INDEX


def _word_state(word: list[int] | tuple[int, ...]) -> int:
    state = 0
    for symbol in word:
        state = TRANSITIONS[state][symbol]
    return state


def _power_state(state: int, exponent: int) -> int:
    result = 0
    base = state
    power = exponent
    while power:
        if power & 1:
            result = COMPOSE[result][base]
        power >>= 1
        if power:
            base = COMPOSE[base][base]
    return result


def _conditioned_word(target: int, requested_len: int, rng: random.Random) -> list[int]:
    """Uniformly sample a 1/2 word of a nearby length having given group value."""

    @functools.lru_cache(maxsize=None)
    def ways(state: int, remaining: int) -> int:
        if remaining == 0:
            return int(state == target)
        return ways(TRANSITIONS[state][1], remaining - 1) + ways(
            TRANSITIONS[state][2], remaining - 1
        )

    length = requested_len
    if ways(0, length) == 0:
        length += 1
    if ways(0, length) == 0:
        raise RuntimeError("could not realize target group state")

    out = []
    state = 0
    for pos in range(length):
        remaining = length - pos - 1
        n1 = ways(TRANSITIONS[state][1], remaining)
        n2 = ways(TRANSITIONS[state][2], remaining)
        pick = rng.randrange(n1 + n2)
        symbol = 1 if pick < n1 else 2
        out.append(symbol)
        state = TRANSITIONS[state][symbol]
    if state != target:
        raise AssertionError("conditioned word sampler lost its target")
    return out


def _find_right_factor(first: int, target: int) -> int:
    for second in range(len(GROUP_STATES)):
        if COMPOSE[first][second] == target:
            return second
    raise AssertionError("finite group has no right factor")


# Local coefficient atoms are always in this order.  The exponent of p in B,C,D
# is one; the other ten entries below are sampled positive exponents.
ATOM_NAMES = ("p", "a", "b", "c", "d", "e", "f", "g", "h", "k", "l")
ATOM_INDEX = {name: i for i, name in enumerate(ATOM_NAMES)}


def _role_monomials(role_exponents: list[int]) -> dict[str, tuple[int, ...]]:
    if len(role_exponents) != 10:
        raise ValueError("role exponent vector must have length 10")
    out = {}
    atom_for_role = {
        "A": "a",
        "B": "b",
        "C": "c",
        "D": "d",
        "E": "e",
        "F": "f",
        "G": "g",
        "H": "h",
        "K": "k",
        "L": "l",
    }
    for role, exponent in zip(ROLES, role_exponents):
        vec = [0] * len(ATOM_NAMES)
        vec[ATOM_INDEX[atom_for_role[role]]] = exponent
        if role in ("B", "C", "D"):
            vec[ATOM_INDEX["p"]] = 1
        out[role] = tuple(vec)
    return out


# If P=p3*T^3+p2*T^2+p1*T+p0 and Q=q1*T+q0, the requested
# fingerprint is p3 p2^2 p1^4 p0^8 q1^16 q0^32.  Expanding the six
# coefficient monomials gives these weights on the ten *current roles*.
FINGERPRINT_ROLE_WEIGHTS = {
    "A": 1,
    "B": 2,
    "C": 4,
    "D": 8,
    "E": 16,
    "F": 32,
    "G": 40,
    "H": 52,
    "K": 66,
    "L": 98,
}


def _local_fingerprint(component: dict, state_id: int) -> list[int]:
    originals = _role_monomials(component["role_exponents"])
    state = GROUP_STATES[state_id]
    result = [0] * len(ATOM_NAMES)
    for current_role in ROLES:
        original_role = state[ROLE_INDEX[current_role]]
        weight = FINGERPRINT_ROLE_WEIGHTS[current_role]
        monomial = originals[original_role]
        for j, exponent in enumerate(monomial):
            result[j] += weight * exponent
    return result


def _component_state(component: dict) -> int:
    state = 0
    for block in component["blocks"]:
        base = _word_state(block["base"])
        powered = _power_state(base, block["repeat"])
        state = COMPOSE[state][powered]
    return state


def _expected_exponents(inst: dict) -> list[int]:
    out = []
    for component in inst["components"]:
        out.extend(_local_fingerprint(component, _component_state(component)))
    return out


def _answer_from_exponents(exponents: list[int]) -> list:
    # Coefficient-first polynomial encoding required by the task prompt.
    return [[[1, 1], list(exponents)]]


def make_instance(n, seed=0, components=8, base_len=8, **params) -> dict:
    """Inverse-generate compressed cubic rank-two LP mutation instances.

    For each independent component, a final element of the order-eight
    coefficient group is sampled first.  Two random group factors are then
    selected with that product, and each is represented by a uniformly sampled
    short mutation word.  Repetition counts are 1 modulo 4, so the compressed
    blocks retain the selected values.  The answer is carried directly from the
    preselected final states.
    """

    max_role_exponent = params.pop("max_role_exponent", 3)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    for value, label, lower in (
        (n, "n", 1),
        (components, "components", 1),
        (base_len, "base_len", 2),
        (max_role_exponent, "max_role_exponent", 1),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < lower:
            raise ValueError(f"{label} must be an integer >= {lower}")
    if components > CERTIFICATE_LANGUAGE["bounds"]["max_components"]:
        raise ValueError("components exceeds the certificate-language bound")
    if max_role_exponent > CERTIFICATE_LANGUAGE["bounds"]["max_role_exponent"]:
        raise ValueError("max_role_exponent exceeds the certificate-language bound")

    rng = random.Random(seed)
    built = []
    chosen_states = []
    for _ in range(components):
        role_exponents = [rng.randint(1, max_role_exponent) for _ in ROLES]

        # Inverse generation: the target exists before either block does.
        target = rng.randrange(len(GROUP_STATES))
        first = rng.randrange(len(GROUP_STATES))
        second = _find_right_factor(first, target)
        blocks = []
        for desired in (first, second):
            base = _conditioned_word(desired, base_len, rng)
            quotient = rng.randint(n, 2 * n)
            blocks.append({"base": base, "repeat": 4 * quotient + 1})
        component = {"role_exponents": role_exponents, "blocks": blocks}
        built.append(component)
        chosen_states.append(target)

    exponents = []
    for component, target in zip(built, chosen_states):
        exponents.extend(_local_fingerprint(component, target))
    answer = _answer_from_exponents(exponents)
    return {
        "paper": "arXiv:1206.2611",
        "family": "cubic rank-two LP coefficient mutation fingerprints",
        "n": n,
        "seed": seed,
        "base_len": base_len,
        "max_role_exponent": max_role_exponent,
        "components": built,
        "answer": answer,
    }


def _monomial_text(exponents: list[int], names: list[str]) -> str:
    factors = []
    for name, exponent in zip(names, exponents):
        if exponent == 1:
            factors.append(name)
        elif exponent:
            factors.append(f"{name}^{exponent}")
    return "1" if not factors else "*".join(factors)


def render(inst) -> str:
    component_count = len(inst["components"])
    atom_order = []
    for i in range(component_count):
        atom_order.extend(f"{name}{i}" for name in ATOM_NAMES)
    lines = [
        "Compute an exact exchange-polynomial fingerprint in a product of cubic rank-two Laurent phenomenon algebras.",
        "",
        "Definitions (everything needed for the problem).",
        "A rank-two LP seed is an ordered pair (X,P(Y)); (Y,Q(X)), where P and Q are irreducible polynomials over a unique-factorization coefficient ring and neither uses its own paired variable.",
        "Mutation 1 replaces X by X'=P(Y)/X.  In Q, substitute X=P(0)/X', remove every coefficient factor sharing an irreducible factor with P(0), and multiply by the unique power of X' that gives a primitive polynomial not divisible by X'.  P remains attached to X'.",
        "Mutation 2 is the same rule with the two slots interchanged.  The sign is normalized so every displayed leading coefficient is positive.",
        "A block [w]^r means execute the mutation digits of w from left to right and repeat that whole word exactly r times.  Concatenate the two displayed blocks in their displayed order.  Digits are slot numbers, not exponents.",
        "",
        "Each independent component starts with",
        "  P(T) = A*T^3 + B*K*L*T^2 + C*H*K^2*L^2*T + D*G*H^2*K^3*L^3",
        "  Q(T) = E*T + F*G*H*K*L^2.",
        "Its coefficient ring is Z[p,a,b,c,d,e,f,g,h,k,l], using private atoms carrying that component's number.",
        "The roles are A=a^rA, B=p*b^rB, C=p*c^rC, D=p*d^rD, E=e^rE, F=f^rF, G=g^rG, H=h^rH, K=k^rK, L=l^rL.",
        "Thus P is Eisenstein at p and Q is primitive linear, so these really are LP seeds.",
        "",
        "After all mutations in a component, write its two exchange polynomials in the same ordered slots as P_f(T)=p3*T^3+p2*T^2+p1*T+p0 and Q_f(T)=q1*T+q0.",
        "Define its fingerprint Phi = p3^1*p2^2*p1^4*p0^8*q1^16*q0^32.  All six coefficients are monomials, so Phi is one monomial in the component's 11 atoms.",
        "Your answer is the product of Phi over all components, hence one coefficient-1 monomial.",
        "",
        f"There are {component_count} components.  Each exponent row is rA,rB,rC,rD,rE,rF,rG,rH,rK,rL.",
    ]
    for i, component in enumerate(inst["components"]):
        exponents = ",".join(str(x) for x in component["role_exponents"])
        block_text = " ".join(
            f"[{''.join(map(str, block['base']))}]^{block['repeat']}"
            for block in component["blocks"]
        )
        lines.append(f"component {i}: r=({exponents}); blocks {block_text}")
    lines.extend(
        [
            "",
            "Output uses the following global exponent order:",
            "  " + ",".join(atom_order),
            "A rational coefficient is [numerator,denominator], and a monomial is its full exponent list in that exact order.  Exponents are nonnegative integers.",
            "Give your final answer inside <answer></answer> tags as a JSON polynomial containing exactly one [coefficient, exponent-list] term.",
            "Example for one component only: <answer>[[[1,1],[8,1,2,4,8,16,32,40,52,66,98]]]</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text) -> object | None:
    try:
        if not isinstance(text, str):
            return None
        match = re.search(r"<answer>(.*?)</answer>", text, re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        body = match.group(1).strip()
        body = re.sub(r"^```(?:json|python)?\s*", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\s*```$", "", body).strip()
        if not body:
            return None
        return json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _decode_unit_monomial(answer, expected_arity: int) -> tuple[list[int] | None, str]:
    if not isinstance(answer, list):
        return None, "malformed polynomial: expected a JSON list of terms"
    if len(answer) == 0:
        return None, "empty polynomial: expected one monomial"
    if len(answer) != 1:
        return None, "wrong term count: expected exactly one monomial"
    term = answer[0]
    if not isinstance(term, list) or len(term) != 2:
        return None, "malformed term: expected [coefficient, exponent-list]"
    coefficient, exponents = term
    try:
        if rationals is not None:
            value = rationals.from_json(coefficient)
        else:
            if (
                not isinstance(coefficient, list)
                or len(coefficient) != 2
                or any(isinstance(x, bool) or not isinstance(x, int) for x in coefficient)
                or coefficient[1] == 0
            ):
                raise ValueError("bad rational")
            num, den = coefficient
            common = math.gcd(num, den)
            value = (num // common, den // common)
    except (TypeError, ValueError, ZeroDivisionError):
        return None, "malformed coefficient: expected an exact [num,den] rational"
    if rationals is not None:
        if value.numerator != 1 or value.denominator != 1:
            return None, "wrong coefficient: the fingerprint monomial has coefficient 1"
    elif value != (1, 1):
        return None, "wrong coefficient: the fingerprint monomial has coefficient 1"
    if not isinstance(exponents, list):
        return None, "malformed exponents: expected a JSON list"
    if len(exponents) != expected_arity:
        return None, f"wrong exponent length: expected {expected_arity}, got {len(exponents)}"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in exponents):
        return None, "malformed exponents: every exponent must be an integer"
    bound = CERTIFICATE_LANGUAGE["bounds"]["max_output_exponent"]
    if any(x < 0 or x > bound for x in exponents):
        return None, f"exponent out of bounds: every exponent must lie in 0..{bound}"

    # Exercise gvlib's exact sparse-polynomial boundary as a second independent
    # shape check when it is available.  Its JSON order is [exponents, coeff].
    if sparse_poly is not None:
        try:
            poly = sparse_poly.from_json([[exponents, coefficient]], nvars=expected_arity)
            if len(poly) != 1:
                return None, "polynomial normalization did not yield one monomial"
        except (TypeError, ValueError):
            return None, "malformed sparse polynomial"
    return list(exponents), "ok"


def verify(inst, answer) -> tuple[bool, str]:
    arity = len(inst["components"]) * len(ATOM_NAMES)
    exponents, reason = _decode_unit_monomial(answer, arity)
    if exponents is None:
        return False, reason
    expected = _expected_exponents(inst)
    if exponents != expected:
        for component in range(len(inst["components"])):
            start = component * len(ATOM_NAMES)
            stop = start + len(ATOM_NAMES)
            if exponents[start:stop] != expected[start:stop]:
                return False, f"fingerprint mismatch in component {component}"
        return False, "fingerprint mismatch"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Sample exactly from the structure-aware eight-state language."""
    exponents = []
    for component in inst["components"]:
        state = rng.randrange(len(GROUP_STATES))
        exponents.extend(_local_fingerprint(component, state))
    return _answer_from_exponents(exponents)


def search_space(inst) -> int | None:
    return len(GROUP_STATES) ** len(inst["components"])


def enumerate_all(inst) -> int | None:
    space = search_space(inst)
    if space is None or space > 100_000:
        return None
    count = 0
    for states in itertools.product(range(len(GROUP_STATES)), repeat=len(inst["components"])):
        exponents = []
        for component, state in zip(inst["components"], states):
            exponents.extend(_local_fingerprint(component, state))
        if verify(inst, _answer_from_exponents(exponents))[0]:
            count += 1
    return count


def canonical_key(inst) -> str:
    """Canonicalize component order and every mutation-word presentation."""
    descriptors = []
    for component in inst["components"]:
        state = _component_state(component)
        descriptors.append(
            [list(component["role_exponents"]), _local_fingerprint(component, state)]
        )
    descriptors.sort(key=lambda item: (item[0], item[1]))
    payload = json.dumps(descriptors, separators=(",", ":"), sort_keys=False)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params) -> dict | str | None:
    harder = dict(params)
    n = harder.get("n")
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        return None
    # Repetition grows the expanded mutation haystack without lengthening the
    # answer or the compact dihedral route.
    harder["n"] = n * 10
    return harder


# ---------------------------------------------------------------------------
# Reference algorithm, adversaries, transformations, and complete gate suite.

def _expanded_reference(inst: dict) -> dict:
    """Execute every compressed mutation symbol, deliberately without skipping."""
    started = time.perf_counter()
    local_states = []
    mutation_symbols = 0
    role_swaps = 0
    for component in inst["components"]:
        state = 0
        for block in component["blocks"]:
            base = block["base"]
            for _ in range(block["repeat"]):
                for symbol in base:
                    state = TRANSITIONS[state][symbol]
                    mutation_symbols += 1
                    role_swaps += len(GENERATOR_PAIRS[symbol])
        local_states.append(state)
    exponents = []
    for component, state in zip(inst["components"], local_states):
        exponents.extend(_local_fingerprint(component, state))
    answer = _answer_from_exponents(exponents)
    elapsed = time.perf_counter() - started
    return {
        "answer": answer,
        "ok": verify(inst, answer)[0],
        "wall_clock_sec": elapsed,
        "mutation_symbols": mutation_symbols,
        "role_swap_operations": role_swaps,
    }


def _candidate_for_states(inst: dict, states: list[int]) -> list:
    exponents = []
    for component, state in zip(inst["components"], states):
        exponents.extend(_local_fingerprint(component, state))
    return _answer_from_exponents(exponents)


def _attack_initial(inst: dict) -> list:
    return _candidate_for_states(inst, [0] * len(inst["components"]))


def _attack_last_block(inst: dict) -> list:
    states = []
    for component in inst["components"]:
        block = component["blocks"][-1]
        states.append(_power_state(_word_state(block["base"]), block["repeat"]))
    return _candidate_for_states(inst, states)


def _attack_commuting_parity(inst: dict) -> list:
    """By-hand heuristic: falsely treat mutation 1 and 2 as commuting."""
    states = []
    for component in inst["components"]:
        parity = {1: 0, 2: 0}
        for block in component["blocks"]:
            repeat_parity = block["repeat"] & 1
            for symbol in block["base"]:
                parity[symbol] ^= repeat_parity
        state = 0
        if parity[1]:
            state = TRANSITIONS[state][1]
        if parity[2]:
            state = TRANSITIONS[state][2]
        states.append(state)
    return _candidate_for_states(inst, states)


def _attack_lexicographic(inst: dict) -> list:
    states = []
    for component in inst["components"]:
        state = min(
            range(len(GROUP_STATES)),
            key=lambda s: tuple(_local_fingerprint(component, s)),
        )
        states.append(state)
    return _candidate_for_states(inst, states)


def _attack_random_restart(inst: dict, rng: random.Random, restarts: int) -> tuple[list, int]:
    last = _attack_initial(inst)
    for attempt in range(1, restarts + 1):
        last = random_candidate(inst, rng)
        if verify(inst, last)[0]:
            return last, attempt
    return last, restarts


def _permute_components(inst: dict, order: list[int]) -> tuple[dict, list]:
    moved = copy.deepcopy(inst)
    moved["components"] = [copy.deepcopy(inst["components"][i]) for i in order]
    source_exponents = inst["answer"][0][1]
    carried = []
    width = len(ATOM_NAMES)
    for i in order:
        carried.extend(source_exponents[i * width : (i + 1) * width])
    moved["answer"] = _answer_from_exponents(carried)
    return moved, moved["answer"]


def _rewrite_instance(inst: dict, add_identity_pair=False, add_four_repeats=False) -> dict:
    moved = copy.deepcopy(inst)
    for component in moved["components"]:
        for block in component["blocks"]:
            if add_identity_pair:
                block["base"].extend([1, 1])
            if add_four_repeats:
                block["repeat"] += 4
    # Both rewrites preserve every block transformation, so the original answer
    # is deliberately carried without recomputing it.
    moved["answer"] = copy.deepcopy(inst["answer"])
    return moved


def _answer_atoms(value) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(v) for v in value)
    return 1


def _compact_route_operations(inst: dict) -> int:
    # Each base symbol once; reduce and compose each powered block (2 ops); then
    # ten weighted role placements plus the three additions into p (13/component).
    base_symbols = sum(
        len(block["base"])
        for component in inst["components"]
        for block in component["blocks"]
    )
    blocks = sum(len(component["blocks"]) for component in inst["components"])
    return base_symbols + 2 * blocks + 13 * len(inst["components"])


def _corruptions(inst: dict) -> dict[str, object]:
    answer = copy.deepcopy(inst["answer"])
    exponents = answer[0][1]
    drop = copy.deepcopy(answer)
    drop[0][1] = drop[0][1][:-1]
    swap = copy.deepcopy(answer)
    pair = None
    for i in range(len(exponents)):
        for j in range(i + 1, len(exponents)):
            if exponents[i] != exponents[j]:
                pair = (i, j)
                break
        if pair:
            break
    if pair is None:
        pair = (0, 1)
    swap[0][1][pair[0]], swap[0][1][pair[1]] = (
        swap[0][1][pair[1]],
        swap[0][1][pair[0]],
    )
    duplicate = copy.deepcopy(answer)
    duplicate.append(copy.deepcopy(duplicate[0]))
    out_of_range = copy.deepcopy(answer)
    out_of_range[0][1][0] = CERTIFICATE_LANGUAGE["bounds"]["max_output_exponent"] + 1
    return {
        "drop_one": drop,
        "swap_two": swap,
        "duplicate_term": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }


def selftest() -> dict:
    report: dict[str, object] = {}

    # G1: every named rung and multiple deterministic seeds, plus JSON nativeness.
    g1_failures = []
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            checks += 1
            ok, why = verify(inst, inst["answer"])
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {why}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": checks,
        "failures": g1_failures,
    }

    ship_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    inst = make_instance(seed=12345, **ship_params)

    # G2: five semantically different corruptions and five distinct diagnostics.
    corruption_reasons = {}
    for name, candidate in _corruptions(inst).items():
        ok, why = verify(inst, candidate)
        corruption_reasons[name] = "ACCEPTED" if ok else why
    report["G2_rejects_corruption"] = {
        "pass": (
            all(reason != "ACCEPTED" for reason in corruption_reasons.values())
            and len(set(corruption_reasons.values())) == len(corruption_reasons)
        ),
        "reasons": corruption_reasons,
    }

    # G3: realistic prose and a fenced JSON answer.
    response = (
        "The exact coefficient bookkeeping gives the following monomial.\n\n"
        "<answer>\n```json\n"
        + json.dumps(inst["answer"], separators=(",", ":"))
        + "\n```\n</answer>\n"
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and verify(inst, parsed)[0],
        "parsed": parsed is not None,
    }

    # G4 and the shipping-density part of G5 share an actual 200k draw from the
    # exact eight-state-per-component certificate language.
    sample_total = 200_000
    sample_hits = 0
    sample_rng = random.Random(0x12062611)
    sample_started = time.perf_counter()
    for _ in range(sample_total):
        if verify(inst, random_candidate(inst, sample_rng))[0]:
            sample_hits += 1
    sample_seconds = time.perf_counter() - sample_started
    empirical = sample_hits / sample_total
    report["G4_guess_resistance"] = {
        "pass": empirical < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "empirical_probability": empirical,
        "exact_probability": 1 / search_space(inst),
        "candidate_space": search_space(inst),
        "prior": "uniform independent choice among all eight reachable coefficient states per component",
        "sampling_wall_seconds": sample_seconds,
    }

    # G6 panel and successful Track-B reference algorithm over eight seeds.
    attack_names = (
        "outlier_lexicographically_smallest_state",
        "greedy_last_block_only",
        "random_restart_256_structure_aware",
        "by_hand_commuting_parity",
    )
    successes = {name: 0 for name in attack_names}
    reference_runs = []
    attack_seeds = list(range(800, 808))
    baseline_seconds = []
    baseline_iterations = []
    for seed in attack_seeds:
        trial = make_instance(seed=seed, **ship_params)
        successes[attack_names[0]] += int(verify(trial, _attack_lexicographic(trial))[0])
        successes[attack_names[1]] += int(verify(trial, _attack_last_block(trial))[0])
        start = time.perf_counter()
        random_answer, iterations = _attack_random_restart(
            trial, random.Random(seed ^ 0xA55A), 256
        )
        baseline_seconds.append(time.perf_counter() - start)
        baseline_iterations.append(iterations)
        successes[attack_names[2]] += int(verify(trial, random_answer)[0])
        successes[attack_names[3]] += int(verify(trial, _attack_commuting_parity(trial))[0])
        reference_runs.append(_expanded_reference(trial))

    attacks = {
        name: {"successes": successes[name], "attempts": len(attack_seeds)}
        for name in attack_names
    }
    reference_ok = sum(int(run["ok"]) for run in reference_runs)
    median_ref_wall = statistics.median(run["wall_clock_sec"] for run in reference_runs)
    median_symbols = int(statistics.median(run["mutation_symbols"] for run in reference_runs))
    median_swaps = int(statistics.median(run["role_swap_operations"] for run in reference_runs))
    report["G6_adversary_panel"] = {
        "pass": all(row["successes"] == 0 for row in attacks.values())
        and reference_ok == len(attack_seeds),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "successive exact cubic coefficient-role mutation",
            "complexity": "O(L) exact role swaps for expanded mutation length L",
            "wall_clock_sec_median": median_ref_wall,
            "operations_median": median_swaps,
            "mutation_symbols_median": median_symbols,
            "solves": f"{reference_ok}/{len(attack_seeds)}, as expected",
        },
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": empirical < 1e-6
        and demo_count == 1
        and reference_ok == len(attack_seeds),
        "shipping_density_hits": sample_hits,
        "shipping_density_samples": sample_total,
        "shipping_density_fraction": empirical,
        "shipping_exact_candidate_count": search_space(inst),
        "shipping_exact_valid_count": 1,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "baseline_wall_seconds_median": statistics.median(baseline_seconds),
        "baseline_restart_iterations_median": int(statistics.median(baseline_iterations)),
        "reference_wall_seconds_median": median_ref_wall,
        "reference_role_swap_operations_median": median_swaps,
    }

    # G7: the ladder grows expanded work; doubling n changes only the haystack.
    ladder_lower_bounds = []
    for params in DIFFICULTY.values():
        if params["n"] == 1 and params["components"] == 1:
            ladder_lower_bounds.append(1)
        else:
            ladder_lower_bounds.append(params["n"] * params["components"] * params["base_len"])
    doubled_params = dict(ship_params)
    doubled_params["n"] *= 2
    started = time.perf_counter()
    doubled = make_instance(seed=54321, **doubled_params)
    doubled_build = time.perf_counter() - started
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": all(a < b for a, b in zip(ladder_lower_bounds, ladder_lower_bounds[1:]))
        and doubled_ok,
        "ladder_expanded_work_lower_bounds": ladder_lower_bounds,
        "base_n": ship_params["n"],
        "doubled_n": doubled_params["n"],
        "doubled_build_seconds": doubled_build,
        "doubled_verify_reason": doubled_why,
        "answer_atoms_unchanged": _answer_atoms(doubled["answer"])
        == _answer_atoms(inst["answer"]),
    }

    # G8: identity insertion, +4 block repetitions, component relabelling, and
    # their composition, over twenty seeds.  Every carried witness is checked.
    invariance_checks = 0
    carried_checks = 0
    failures = []
    unrelated_keys = []
    for seed in range(20):
        original = make_instance(seed=10_000 + seed, **ship_params)
        key = canonical_key(original)
        unrelated_keys.append(key)
        order = list(reversed(range(len(original["components"]))))
        reordered, carried = _permute_components(original, order)
        transforms = [
            (_rewrite_instance(original, add_identity_pair=True), original["answer"]),
            (_rewrite_instance(original, add_four_repeats=True), original["answer"]),
            (reordered, carried),
        ]
        composed = _rewrite_instance(reordered, add_identity_pair=True, add_four_repeats=True)
        transforms.append((composed, carried))
        for tindex, (moved, witness) in enumerate(transforms):
            invariance_checks += 1
            if canonical_key(moved) != key:
                failures.append(f"seed {seed}, transform {tindex}: key changed")
            carried_checks += 1
            ok, why = verify(moved, witness)
            if not ok:
                failures.append(f"seed {seed}, transform {tindex}: {why}")
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not failures and distinct == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_distinct": distinct,
        "unrelated_attempts": 20,
        "failures": failures,
        "transformations": (
            "insert involution word 11; add four repetitions to powered blocks; "
            "reorder independent LP components; compose all three"
        ),
    }

    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(inst["answer"])
    route_operations = _compact_route_operations(inst)
    evidence = G9_EVIDENCE
    hinted_attempts = evidence["hinted"]["attempts"]
    placebo_attempts = evidence["placebo"]["attempts"]
    hinted_rate = evidence["hinted"]["solved"] / hinted_attempts if hinted_attempts else 0.0
    placebo_rate = (
        evidence["placebo"]["solved"] / placebo_attempts if placebo_attempts else 0.0
    )
    within_caps = (
        answer_chars <= 2000
        and answer_tokens <= 500
        and answer_elements <= 256
        and route_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": evidence["hinted_verdict"] == "hardened" and within_caps,
        "arms": {
            "bare": dict(evidence["bare"]),
            "hinted": dict(evidence["hinted"]),
            "placebo": dict(evidence["placebo"]),
        },
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": evidence["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": route_operations,
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = ship_params
    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=False))
