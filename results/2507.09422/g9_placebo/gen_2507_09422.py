"""Verified problem generator for arXiv:2507.09422.

The paper's Proposition 4.1 gives a four-player two-action game with a
unique fully mixed Nash equilibrium in a degree-six number field, and
Proposition 6.6 composes copies by products.  This module takes products of
that game, applies invertible affine substitutions around the known interior
root, multiplies every payoff-advantage polynomial by an independently sampled
dense polynomial that is strictly positive on the probability cube, and then
renames players and actions.  The affine substitutions carry the planted
polynomial identities (they are not claimed to preserve every boundary
equilibrium), while the positive factors preserve their zero sets and signs.
Thus the exact fully mixed equilibrium certificate is carried through the
construction rather than found by solving the emitted instance.
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
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import roots
except ImportError:  # pragma: no cover - the repository ships gvlib
    roots = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "real_algebraic",
    "computational_core": "polynomial_identity",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "two-action normal-form game represented by exact payoff-advantage polynomials",
        "real algebraic probability isolated by a polynomial over Q",
        "mixed-strategy profile as polynomials in that algebraic probability",
    ],
    "verification_operations": [
        "exact rational interval bound",
        "exact polynomial substitution",
        "exact remainder modulo the algebraic number's defining polynomial",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Each displayed polynomial is a tensor product of a sign-changing game "
        "factor and a dense positive mask; separating those variable sets reveals "
        "relabelled copies of the paper's four-player game."
    ),
    "hardness_basis": (
        "Track B: exact rank-one coefficient-tensor decomposition followed by "
        "matching 11 affine scales and 4!*2^4 action/player relabellings costs "
        "O(n*(C(s,2)+C(s,3))*2^s+4224*n), and measured 307436 exact coefficient "
        "probes and 1.240 seconds per shipping instance; the compact decomposition "
        "route uses at most 156 exact operations."
    ),
    "max_answer_tokens": 172,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": " +
        PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "easy": {"n": 12, "mask_width": 2, "value_slots": 12},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The coefficient tables split into tensor factors on disjoint sets of variables."
)
PLACEBO_HINT = (
    "The coefficient order and one-based player labels require consistent exact "
    "bookkeeping."
)

# z = x_4 - 8/25.  Appendix A isolates x_4 in
# (0.320065197644, 0.320065197645), hence z lies in this interval.
PRIMITIVE_POLY = [
    434, -6665425, 134165625, -1061484375,
    3919921875, -1679687500, 244140625,
]
PRIMITIVE_INTERVAL = [
    [16299411, 250000000000],
    [13039529, 200000000000],
]
SHIFT = [8, 25]

# A vector [c0,...,c5] denotes
# c0/D0 + sum_{k=1}^5 (ck/D1) z^k.  These are, in order,
# x1,1-x1,x2,1-x2,x3,1-x3,x4,1-x4 from Proposition 4.1.
D0 = 7_812_500
D1 = 437_500
CORE_VALUES = [
    [4136044, -958696, -1157300, -3700000, 1937500, -312500],
    [3676456, 958696, 1157300, 3700000, -1937500, 312500],
    [6612577, 32137, 8653225, -397446875, 184406250, -27890625],
    [1199923, -32137, -8653225, 397446875, -184406250, 27890625],
    [4081027, 7178107, -70409025, 354696875, -155593750, 22890625],
    [3731473, -7178107, 70409025, -354696875, 155593750, -22890625],
    [2500000, 437500, 0, 0, 0, 0],
    [5312500, -437500, 0, 0, 0, 0],
]
SCALE_CHOICES = (1, 5, 8, 9, 10, 11, 12, 14, 16, 18, 24)
MASK_COEFF_BOUND = 31


def _scaled_value(scale, role, flipped=False):
    base = CORE_VALUES[2 * role]
    vector = [(scale * base[0]) % D0] + [scale * c for c in base[1:]]
    if flipped:
        vector = [D0 - vector[0]] + [-c for c in vector[1:]]
    return vector


CODEBOOK = [
    _scaled_value(scale, role, flipped)
    for scale in SCALE_CHOICES
    for role in range(4)
    for flipped in (False, True)
]
CODEBOOK_SET = {tuple(vector) for vector in CODEBOOK}

CERTIFICATE_LANGUAGE = {
    "description": (
        "Exactly n distinct degree-at-most-five polynomials R(z), each encoded by "
        "six integer coefficients [c0,...,c5] as c0/7812500 + sum_{k=1}^5 "
        "ck*z^k/437500 and drawn from the 88-element affine codebook generated by "
        "four Proposition-4.1 base vectors, scale K in {1,5,8,9,10,11,12,14,16,18,24}, "
        "and optional complementation; plus a permutation of 0,...,n-1 assigning "
        "the n listed polynomials to the n players."
    ),
    "bounds": {
        "value_slots": "n",
        "max_degree": 5,
        "coefficients_per_value": 6,
        "affine_codebook_size": 88,
        "scale_choices": list(SCALE_CHOICES),
        "selector": "a permutation of range(n)",
    },
}

NOTES = (
    "Section 2, Equation (1) and Lemma 2.1 fix the exact payoff-advantage and "
    "best-response definition. Proposition 4.1 and Appendix A supply the degree-six "
    "algebraic equilibrium and exact Sturm isolation; Proposition 6.6 and Lemma 6.2 "
    "license product composition. The affine coordinate substitutions are a separate "
    "composition-of-identities step: they carry the known interior zero but do not "
    "assert global strategic equivalence. Proposition 3.2 is the easy regime to avoid: every "
    "three-player 2x2x2 integer-payoff game has an equilibrium expressible with only "
    "rational arithmetic and square roots. The paper obtains the core certificate by "
    "Mathematica Groebner bases and exact root isolation, so this is Track B, never a "
    "Track A hardness claim. An earlier product of two fixed linear masks leaked all "
    "12 values to a five-statistic coefficient fingerprint on 8/8 seeds; independently "
    "sampled dense positive masks defeat that attack. Independent action flips remove "
    "sign outliers, player shuffling defeats positional and cyclic guesses, and the "
    "panel also tests displayed-equation greedy residual descent and random restarts. "
    "The successful reference algorithm "
    "extracts rank-one factors from coefficient tensors and checks all 384 relabellings "
    "of each four-player core at each allowed affine scale. "
    "A separate SymPy 1.12 F5B probe computed the unmasked four-player Groebner basis "
    "in 0.010 seconds but did not finish a shipping instance within 120 seconds."
)

# Filled from script-owned hardening runs after the module is stable.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unrun",
}


# Multilinear polynomials are dictionaries frozenset(variable indices) -> int.
# The four roles use the paper's x1,x2,x3,x4 order.
BASE_F = [
    {frozenset((1, 2, 3)): 1, frozenset((1, 2)): 2,
     frozenset((1,)): -2, frozenset((2, 3)): -2, frozenset(): 1},
    {frozenset((0, 2, 3)): 3, frozenset((0, 2)): -3,
     frozenset((0,)): 1, frozenset((2, 3)): -1,
     frozenset((2,)): 1, frozenset((3,)): -1},
    {frozenset((0, 3)): 1, frozenset((0,)): -1,
     frozenset((3,)): -2, frozenset(): 1},
    {frozenset((0, 1, 2)): -1, frozenset((0, 2)): 3,
     frozenset((1, 2)): -1, frozenset((1,)): 1, frozenset(): -1},
]

MOD_PRIME = 1_000_003
SCREEN_PRIME = 101
SCREEN_ROOT = 84  # PRIMITIVE_POLY(84) == 0 mod 101
_MOD_INV_D0 = pow(D0, MOD_PRIME - 2, MOD_PRIME)
_MOD_INV_D1 = pow(D1, MOD_PRIME - 2, MOD_PRIME)
_SCREEN_INV_D0 = pow(D0, SCREEN_PRIME - 2, SCREEN_PRIME)
_SCREEN_INV_D1 = pow(D1, SCREEN_PRIME - 2, SCREEN_PRIME)
_SCREEN_VALUE_CACHE = {}
_RANGE_CACHE = {}
_PRIMITIVE_CACHE = {}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_params(n, mask_width, value_slots):
    if not _is_int(n) or n < 4 or n % 4:
        raise ValueError("n must be an integer multiple of 4 and at least 4")
    if not _is_int(mask_width) or mask_width < 0 or mask_width > n - 4:
        raise ValueError("mask_width must be an integer between 0 and n-4")
    if value_slots != n:
        raise ValueError("value_slots must equal n")
    if n == 4 and mask_width != 0:
        raise ValueError("the four-player demo requires mask_width=0 and value_slots=4")
    if n > 4 and n // 4 > len(SCALE_CHOICES) - 1:
        raise ValueError("not enough distinct nontrivial affine scales for this n")


def _clean(poly):
    return {m: c for m, c in poly.items() if c}


def _scale(poly, scalar):
    return _clean({m: scalar * c for m, c in poly.items()})


def _mul_linear(poly, var, constant, slope):
    out = {}
    for monomial, coeff in poly.items():
        out[monomial] = out.get(monomial, 0) + constant * coeff
        with_var = frozenset(set(monomial) | {var})
        if var in monomial:
            raise ValueError("mask variable already occurs in the polynomial")
        out[with_var] = out.get(with_var, 0) + slope * coeff
    return _clean(out)


def _mul_disjoint(left, right):
    """Multiply multilinear polynomials whose variable sets are disjoint."""
    out = {}
    for left_monomial, left_coeff in left.items():
        for right_monomial, right_coeff in right.items():
            if left_monomial & right_monomial:
                raise ValueError("polynomial factors use overlapping variables")
            monomial = left_monomial | right_monomial
            out[monomial] = out.get(monomial, 0) + left_coeff * right_coeff
    return _clean(out)


def _random_positive_mask(rng, variables):
    """Dense integer multilinear M with M(y)>=1 throughout [0,1]^variables."""
    variables = tuple(sorted(variables))
    if not variables:
        return {frozenset(): 1}
    mask = {}
    negative_mass = 0
    for bits in range(1, 1 << len(variables)):
        coefficient = 0
        while coefficient == 0:
            coefficient = rng.randint(-MASK_COEFF_BOUND, MASK_COEFF_BOUND)
        monomial = frozenset(
            variables[index]
            for index in range(len(variables))
            if (bits >> index) & 1
        )
        mask[monomial] = coefficient
        if coefficient < 0:
            negative_mass -= coefficient
    # Every monomial is in [0,1].  Replacing every negative monomial by 1 and
    # every positive monomial by 0 gives a valid global lower bound.
    mask[frozenset()] = negative_mass + rng.randint(1, MASK_COEFF_BOUND)
    return mask


def _flip_variable(poly, var):
    """Substitute old x_var = 1-new x_var in a multilinear polynomial."""
    out = {}
    for monomial, coeff in poly.items():
        if var not in monomial:
            out[monomial] = out.get(monomial, 0) + coeff
            continue
        rest = frozenset(v for v in monomial if v != var)
        out[rest] = out.get(rest, 0) + coeff
        out[monomial] = out.get(monomial, 0) - coeff
    return _clean(out)


def _affine_variable(poly, var, constant, slope):
    """Substitute old x_var = constant + slope*new x_var exactly."""
    out = {}
    for monomial, coeff in poly.items():
        coeff = Fraction(coeff)
        if var not in monomial:
            out[monomial] = out.get(monomial, Fraction(0)) + coeff
            continue
        rest = frozenset(v for v in monomial if v != var)
        out[rest] = out.get(rest, Fraction(0)) + coeff * constant
        out[monomial] = out.get(monomial, Fraction(0)) + coeff * slope
    return _clean(out)


def _integer_normalize(poly):
    """Clear rational denominators and positive common content."""
    denominator = 1
    for coeff in poly.values():
        denominator = math.lcm(denominator, Fraction(coeff).denominator)
    integers = {m: int(Fraction(c) * denominator) for m, c in poly.items()}
    content = 0
    for coeff in integers.values():
        content = math.gcd(content, abs(coeff))
    if content > 1:
        integers = {m: c // content for m, c in integers.items()}
    return _clean(integers)


def _rename_poly(poly, old_to_new):
    return {
        frozenset(old_to_new[v] for v in monomial): coeff
        for monomial, coeff in poly.items()
    }


def _poly_to_json(poly):
    return [
        [coeff, [v + 1 for v in sorted(monomial)]]
        for monomial, coeff in sorted(
            poly.items(), key=lambda item: (-len(item[0]), tuple(sorted(item[0])))
        )
    ]


def _poly_from_json(data, n):
    if not isinstance(data, list):
        raise ValueError("polynomial is not a term list")
    out = {}
    for term in data:
        if (not isinstance(term, list) or len(term) != 2 or
                not _is_int(term[0]) or not isinstance(term[1], list)):
            raise ValueError("malformed polynomial term")
        variables = term[1]
        if (any(not _is_int(v) or not 1 <= v <= n for v in variables) or
                variables != sorted(set(variables))):
            raise ValueError("term variables must be distinct increasing player labels")
        monomial = frozenset(v - 1 for v in variables)
        out[monomial] = out.get(monomial, 0) + term[0]
    return _clean(out)


def _transform_base(role_to_player, flips, scale=1):
    equations = [{} for _ in range(4)]
    for role in range(4):
        poly = {
            frozenset(role_to_player[v] for v in monomial): coeff
            for monomial, coeff in BASE_F[role].items()
        }
        for other_role in range(4):
            player = role_to_player[other_role]
            if other_role == role:
                continue
            base_constant = CORE_VALUES[2 * other_role][0]
            shift = (scale * base_constant) // D0
            if flips[player]:
                constant = Fraction(shift + 1, scale)
                slope = Fraction(-1, scale)
            else:
                constant = Fraction(shift, scale)
                slope = Fraction(1, scale)
            poly = _affine_variable(poly, player, constant, slope)
        poly = _integer_normalize(poly)
        owner = role_to_player[role]
        if flips[owner]:
            poly = _scale(poly, -1)
        equations[role] = poly
    return equations


def make_instance(n, seed=0, mask_width=0, value_slots=None, **params):
    """Transform products of Proposition 4.1 games, carrying their certificate."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if value_slots is None:
        value_slots = n
    _validate_params(n, mask_width, value_slots)
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    blocks = n // 4
    if n == 4:
        block_scales = [1]
    else:
        block_scales = rng.sample(list(SCALE_CHOICES[1:]), blocks)

    # Work first in canonical (block, role) labels.
    masks = []
    for owner in range(n):
        block = owner // 4
        eligible = [v for v in range(n) if v // 4 != block]
        chosen = rng.sample(eligible, mask_width) if mask_width else []
        masks.append(sorted(chosen))

    flips = [False] * n
    if n > 4:
        flips = [bool(rng.getrandbits(1)) for _ in range(n)]

    unpermuted_core = [{} for _ in range(n)]
    unpermuted_full = [{} for _ in range(n)]
    for block in range(blocks):
        role_to_player = [4 * block + role for role in range(4)]
        transformed = _transform_base(role_to_player, flips, block_scales[block])
        for role, owner in enumerate(role_to_player):
            core_poly = transformed[role]
            positive_mask = _random_positive_mask(rng, masks[owner])
            full_poly = _mul_disjoint(core_poly, positive_mask)
            unpermuted_core[owner] = core_poly
            unpermuted_full[owner] = full_poly

    if n == 4:
        order = list(range(n))
    else:
        order = list(range(n))
        rng.shuffle(order)
    old_to_new = {old: new for new, old in enumerate(order)}
    equations = [None] * n
    core_equations = [None] * n
    structure = [None] * n
    selector = [None] * n
    for old in range(n):
        new = old_to_new[old]
        equations[new] = _rename_poly(unpermuted_full[old], old_to_new)
        core_equations[new] = _rename_poly(unpermuted_core[old], old_to_new)
        structure[new] = {
            "block": old // 4,
            "role": old % 4,
            "scale": block_scales[old // 4],
            "masks": [old_to_new[v] for v in masks[old]],
        }

    player_values = [None] * n
    for old in range(n):
        new = old_to_new[old]
        player_values[new] = _scaled_value(
            block_scales[old // 4], old % 4, flips[old]
        )
    value_order = list(range(n))
    rng.shuffle(value_order)
    answer_values = [player_values[player] for player in value_order]
    value_position = {
        tuple(value): position for position, value in enumerate(answer_values)
    }
    for player in range(n):
        selector[player] = value_position[tuple(player_values[player])]

    inst = {
        "paper": "arXiv:2507.09422",
        "family": "fully mixed Nash equilibrium over an isolated degree-six field",
        "n": n,
        "mask_width": mask_width,
        "value_slots": value_slots,
        "primitive_polynomial": list(PRIMITIVE_POLY),
        "primitive_interval": [list(x) for x in PRIMITIVE_INTERVAL],
        "shift": list(SHIFT),
        "equations": [_poly_to_json(poly) for poly in equations],
        # Checker/canonicalisation data are deterministic structural summaries of
        # the displayed polynomials, never a second copy of the answer.
        "_core_equations": [_poly_to_json(poly) for poly in core_equations],
        "_structure": structure,
    }
    inst["answer"] = {
        "values": [list(value) for value in answer_values],
        "selector": selector,
    }
    return inst


def _rat_text(pair):
    return f"{pair[0]}/{pair[1]}"


def _term_text(term):
    coeff, variables = term
    if variables:
        monomial = "*".join(f"y{v}" for v in variables)
        if coeff == 1:
            return monomial
        if coeff == -1:
            return "-" + monomial
        return f"{coeff}*{monomial}"
    return str(coeff)


def _equation_text(terms):
    pieces = []
    for term in terms:
        text = _term_text(term)
        if pieces and not text.startswith("-"):
            text = "+" + text
        pieces.append(text)
    return "".join(pieces) if pieces else "0"


def render(inst):
    """Render a self-contained exact Nash-equilibrium problem."""
    n = inst["n"]
    slots = inst["value_slots"]
    p_terms = []
    for degree in range(len(inst["primitive_polynomial"]) - 1, -1, -1):
        coeff = inst["primitive_polynomial"][degree]
        if not coeff:
            continue
        variable = "" if degree == 0 else ("z" if degree == 1 else f"z^{degree}")
        if variable and coeff == 1:
            text = variable
        elif variable and coeff == -1:
            text = "-" + variable
        else:
            text = f"{coeff}" + ("*" + variable if variable else "")
        if p_terms and not text.startswith("-"):
            text = "+" + text
        p_terms.append(text)
    lines = [
        "Find an exact fully mixed Nash equilibrium of the following two-action game.",
        "",
        f"There are {n} players, numbered 1 through {n}. Player i uses action 0 with",
        "probability y_i and action 1 with probability 1-y_i. For each player i, F_i",
        "is the expected-payoff advantage of action 0 over action 1. Thus a profile",
        "with 0<y_i<1 for every i is a Nash equilibrium exactly when F_i=0 for every i.",
        "All displayed polynomials are multilinear and all arithmetic is exact.",
        "",
        "The answer is represented in Q(z), where z is the unique real root in the",
        f"open interval ({_rat_text(inst['primitive_interval'][0])},",
        f"{_rat_text(inst['primitive_interval'][1])}) of",
        "P(z)=" + "".join(p_terms) + ".",
        "The interval endpoints are excluded.",
        "",
        "Payoff-advantage polynomials:",
    ]
    for i, terms in enumerate(inst["equations"], 1):
        lines.append(f"F_{i}={_equation_text(terms)}")
    lines.extend([
        "",
        "Answer format (compact JSON):",
        f'- "values" must contain exactly {slots} pairwise-distinct six-integer vectors',
        "  [c0,c1,c2,c3,c4,c5]. Such a vector denotes the exact polynomial",
        "  R(z)=c0/7812500+(c1*z+c2*z^2+c3*z^3+c4*z^4+c5*z^5)/437500.",
        "  Each vector must come from this finite affine codebook. Start with one of",
        "  B1=[4136044,-958696,-1157300,-3700000,1937500,-312500],",
        "  B2=[6612577,32137,8653225,-397446875,184406250,-27890625],",
        "  B3=[4081027,7178107,-70409025,354696875,-155593750,22890625], or",
        "  B4=[2500000,437500,0,0,0,0]. Choose",
        "  K in {1,5,8,9,10,11,12,14,16,18,24}; replace [b0,b1,...,b5] by",
        "  [(K*b0) mod 7812500,K*b1,...,K*b5]; optionally complement it by",
        "  replacing [c0,c1,...,c5] with [7812500-c0,-c1,...,-c5].",
        f'- "selector" must be a JSON list containing each integer 0 through {n - 1}',
        "  exactly once. Its i-th entry chooses the value polynomial for player i+1.",
        "  Order of value vectors matters because selector entries are zero-based.",
        "",
        "Give your final answer inside <answer></answer> tags as compact JSON.",
        "Example syntax only: <answer>{\"values\":[[2500000,437500,0,0,0,0]],\"selector\":[0]}</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    """Extract the final tagged JSON answer, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer>\s*(.*?)\s*</answer>", text, flags=re.I | re.S)
    candidates = list(reversed(matches))
    if not candidates:
        fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.I | re.S)
        candidates.extend(reversed(fenced))
    for body in candidates:
        try:
            value = json.loads(body.strip())
        except (TypeError, ValueError):
            continue
        if isinstance(value, dict):
            return value
    return None


def _dense_normalize(poly):
    out = list(poly)
    while out and out[-1] == 0:
        out.pop()
    return out


def _dense_add(a, b):
    out = [Fraction(0)] * max(len(a), len(b))
    for i in range(len(a)):
        out[i] += a[i]
    for i in range(len(b)):
        out[i] += b[i]
    return _dense_normalize(out)


def _dense_scale(a, scalar):
    return _dense_normalize([scalar * x for x in a])


def _dense_mul_raw(a, b):
    if not a or not b:
        return []
    out = [Fraction(0)] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i + j] += x * y
    return _dense_normalize(out)


def _dense_mod(poly, modulus):
    if not poly:
        return []
    if roots is not None:
        return roots.divmod_poly(poly, modulus)[1]
    # Standard-library fallback: exact long division.
    rem = list(poly)
    degree = len(modulus) - 1
    lead = modulus[-1]
    while len(rem) - 1 >= degree:
        factor = rem[-1] / lead
        shift = len(rem) - len(modulus)
        for j, coeff in enumerate(modulus):
            rem[shift + j] -= factor * coeff
        rem = _dense_normalize(rem)
    return rem


def _dense_divmod_pair(a, b):
    a = _dense_normalize([Fraction(x) for x in a])
    b = _dense_normalize([Fraction(x) for x in b])
    if not b:
        raise ZeroDivisionError("zero polynomial divisor")
    quotient = [Fraction(0)] * max(0, len(a) - len(b) + 1)
    remainder = list(a)
    while len(remainder) >= len(b):
        factor = remainder[-1] / b[-1]
        shift = len(remainder) - len(b)
        quotient[shift] += factor
        for j, coeff in enumerate(b):
            remainder[shift + j] -= factor * coeff
        remainder = _dense_normalize(remainder)
    return _dense_normalize(quotient), remainder


def _evaluate_dense(poly, x):
    value = Fraction(0)
    for coefficient in reversed(poly):
        value = value * x + coefficient
    return value


def _fallback_root_count_one(poly, lo, hi):
    derivative = [Fraction(i) * poly[i] for i in range(1, len(poly))]
    a, b = list(poly), _dense_normalize(derivative)
    while b:
        _, remainder = _dense_divmod_pair(a, b)
        a, b = b, remainder
    if len(a) != 1:
        return False
    sequence = [list(poly), _dense_normalize(derivative)]
    while len(sequence[-1]) > 1:
        _, remainder = _dense_divmod_pair(sequence[-2], sequence[-1])
        if not remainder:
            break
        sequence.append([-c for c in remainder])

    def changes(x):
        signs = []
        for member in sequence:
            value = _evaluate_dense(member, x)
            if value:
                signs.append(1 if value > 0 else -1)
        return sum(a != b for a, b in zip(signs, signs[1:]))

    if _evaluate_dense(poly, lo) == 0 or _evaluate_dense(poly, hi) == 0:
        return False
    return changes(lo) - changes(hi) == 1


def _validate_primitive(inst):
    try:
        poly_key = tuple(inst["primitive_polynomial"])
        interval_key = tuple(tuple(x) for x in inst["primitive_interval"])
        key = (poly_key, interval_key)
        if key in _PRIMITIVE_CACHE:
            return _PRIMITIVE_CACHE[key]
        if (not poly_key or any(not _is_int(c) for c in poly_key) or
                len(interval_key) != 2):
            result = False
        else:
            poly = [Fraction(c) for c in poly_key]
            lo, hi = (Fraction(*pair) for pair in interval_key)
            if roots is not None:
                result = (roots.is_squarefree(poly) and
                          roots.count_roots(poly, lo, hi) == 1)
            else:
                result = _fallback_root_count_one(poly, lo, hi)
        _PRIMITIVE_CACHE[key] = result
        return result
    except (TypeError, ValueError, ZeroDivisionError):
        return False


def _field_mul(a, b, modulus):
    return _dense_mod(_dense_mul_raw(a, b), modulus)


def _vector_to_poly(vector):
    return [Fraction(vector[0], D0)] + [Fraction(c, D1) for c in vector[1:]]


def _mod_normalize(poly):
    out = [x % MOD_PRIME for x in poly]
    while out and out[-1] == 0:
        out.pop()
    return out


def _mod_remainder(poly, modulus):
    rem = _mod_normalize(poly)
    mod = _mod_normalize(modulus)
    inv_lead = pow(mod[-1], MOD_PRIME - 2, MOD_PRIME)
    while len(rem) >= len(mod):
        factor = rem[-1] * inv_lead % MOD_PRIME
        shift = len(rem) - len(mod)
        for j, coeff in enumerate(mod):
            rem[shift + j] = (rem[shift + j] - factor * coeff) % MOD_PRIME
        rem = _mod_normalize(rem)
    return rem


def _mod_mul(a, b, modulus):
    if not a or not b:
        return []
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i + j] = (out[i + j] + x * y) % MOD_PRIME
    return _mod_remainder(out, modulus)


def _vector_to_mod_poly(vector):
    return [vector[0] * _MOD_INV_D0 % MOD_PRIME] + [
        c * _MOD_INV_D1 % MOD_PRIME for c in vector[1:]
    ]


def _vector_at_screen_root(vector):
    key = tuple(vector)
    if key in _SCREEN_VALUE_CACHE:
        return _SCREEN_VALUE_CACHE[key]
    value = vector[0] * _SCREEN_INV_D0
    power = SCREEN_ROOT
    for coefficient in vector[1:]:
        value += coefficient * _SCREEN_INV_D1 * power
        power = power * SCREEN_ROOT % SCREEN_PRIME
    result = value % SCREEN_PRIME
    _SCREEN_VALUE_CACHE[key] = result
    return result


def _screen_equation(terms, scalar_values):
    result = 0
    for coefficient, variables in terms:
        term = coefficient % SCREEN_PRIME
        for variable in variables:
            term = term * scalar_values[variable - 1] % SCREEN_PRIME
        result = (result + term) % SCREEN_PRIME
    return result


def _eval_multilinear_field(poly, values, modulus, modular=False):
    add = (lambda a, b: _mod_normalize([
        ((a[i] if i < len(a) else 0) + (b[i] if i < len(b) else 0)) % MOD_PRIME
        for i in range(max(len(a), len(b)))
    ])) if modular else _dense_add
    scale = (lambda a, c: _mod_normalize([(c * x) % MOD_PRIME for x in a])) \
        if modular else _dense_scale
    mul = _mod_mul if modular else _field_mul
    result = []
    for monomial, coeff in poly.items():
        term = [1]
        for variable in monomial:
            term = mul(term, values[variable], modulus)
        result = add(result, scale(term, coeff))
    return result


def _parse_candidate(inst, answer):
    if not isinstance(answer, dict):
        return None, "answer must be a JSON object"
    if set(answer) != {"values", "selector"}:
        return None, "answer object must contain exactly values and selector"
    values = answer["values"]
    slots = inst["value_slots"]
    if not isinstance(values, list) or len(values) != slots:
        return None, f"expected exactly {slots} value definitions"
    checked = []
    for index, vector in enumerate(values):
        if (not isinstance(vector, list) or len(vector) != 6 or
                any(not _is_int(c) for c in vector)):
            return None, f"value {index} must be a six-integer coefficient vector"
        if tuple(vector) not in CODEBOOK_SET:
            return None, f"value {index} is outside the declared affine codebook"
        checked.append(tuple(vector))
    if len(set(checked)) != slots:
        return None, "value definitions must be pairwise distinct"
    selector = answer["selector"]
    if (not isinstance(selector, list) or len(selector) != inst["n"] or
            any(not _is_int(x) for x in selector)):
        return None, f"selector must be a list of exactly {inst['n']} integers"
    if sorted(selector) != list(range(slots)):
        return None, f"selector must be a permutation of 0 through {slots - 1}"
    # Inspect the exact interval image of every value polynomial; floats and
    # an unexecuted appeal to the paper would not be a witness check.
    lo = Fraction(*inst["primitive_interval"][0])
    hi = Fraction(*inst["primitive_interval"][1])
    if not 0 < lo < hi:
        return None, "instance primitive interval is malformed"
    for index, vector in enumerate(checked):
        cache_key = (tuple(inst["primitive_interval"][0]),
                     tuple(inst["primitive_interval"][1]), vector)
        in_range = _RANGE_CACHE.get(cache_key)
        if in_range is None:
            lower = upper = Fraction(vector[0], D0)
            for degree, coefficient in enumerate(vector[1:], 1):
                c = Fraction(coefficient, D1)
                a, b = c * lo ** degree, c * hi ** degree
                lower += min(a, b)
                upper += max(a, b)
            in_range = 0 < lower and upper < 1
            _RANGE_CACHE[cache_key] = in_range
        if not in_range:
            return None, f"value {index} is not certified strictly between 0 and 1"
    return (checked, list(selector)), None


def verify(inst, answer):
    """Check any bounded exact equilibrium witness; never consult inst['answer']."""
    try:
        if not _validate_primitive(inst):
            return False, "instance does not contain a squarefree polynomial with one root in its interval"
        parsed, reason = _parse_candidate(inst, answer)
        if parsed is None:
            return False, reason
        vectors, selectors = parsed
        n = inst["n"]
        # A polynomial identity in Q[z]/(P) remains an identity after reduction
        # modulo 101 and evaluation at the finite-field root z=84.  This is a
        # sound one-sided rejection screen, not a probabilistic acceptance test.
        screen_dictionary = [_vector_at_screen_root(v) for v in vectors]
        screen_values = [screen_dictionary[s] for s in selectors]
        screen_order = sorted(range(n), key=lambda i: len(inst["equations"][i]))
        for player in screen_order:
            if _screen_equation(inst["equations"][player], screen_values):
                return False, f"player {player + 1} payoff advantage is nonzero"
        equations = [_poly_from_json(poly, n) for poly in inst["equations"]]
        order = screen_order
        mod_p = [c % MOD_PRIME for c in inst["primitive_polynomial"]]
        mod_values = [_vector_to_mod_poly(list(vectors[s])) for s in selectors]
        for player in order:
            residual = _eval_multilinear_field(
                equations[player], mod_values, mod_p, modular=True
            )
            if residual:
                return False, f"player {player + 1} payoff advantage is nonzero"
        # Passing a million-element finite-field screen is not a proof.  Recheck
        # the full identities over Q[z]/(P) with exact Fractions.
        modulus = [Fraction(c) for c in inst["primitive_polynomial"]]
        exact_values = [_vector_to_poly(list(vectors[s])) for s in selectors]
        for player in order:
            residual = _eval_multilinear_field(
                equations[player], exact_values, modulus, modular=False
            )
            if residual:
                return False, f"player {player + 1} exact payoff identity fails"
        return True, "ok"
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        return False, "malformed instance or answer: " + str(exc)


def random_candidate(inst, rng):
    """Uniform sample from the bounded, already-fully-mixed certificate language."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    slots = inst["value_slots"]
    values = [list(CODEBOOK[index])
              for index in rng.sample(range(len(CODEBOOK)), slots)]
    selector = rng.sample(range(slots), slots)
    return {"values": values, "selector": selector}


def search_space(inst):
    """Exact size of the finite coefficient-vector language."""
    slots = inst["value_slots"]
    ordered_distinct = 1
    for j in range(slots):
        ordered_distinct *= len(CODEBOOK) - j
    return ordered_distinct * math.factorial(slots)


def enumerate_all(inst):
    """The smallest language is already far above the safe brute-force cap."""
    return None


def _canonical_structure(inst):
    structure = inst["_structure"]
    blocks = inst["n"] // 4
    by_label = {i: node for i, node in enumerate(structure)}
    best = None
    for perm_tuple in itertools.permutations(range(blocks)):
        block_map = {old: new for old, new in enumerate(perm_tuple)}
        rows = []
        for label, node in by_label.items():
            source = (block_map[node["block"]], node["scale"], node["role"])
            targets = []
            for target_label in node["masks"]:
                target = by_label[target_label]
                targets.append((block_map[target["block"]], target["scale"], target["role"]))
            rows.append((source, tuple(sorted(targets))))
        code = tuple(sorted(rows))
        if best is None or code < best:
            best = code
    return best


def canonical_key(inst):
    """Canonicalise block renaming, player numbering, and every action relabelling."""
    payload = repr((inst["n"], inst["mask_width"], _canonical_structure(inst))).encode()
    return hashlib.sha256(payload).hexdigest()


def escalate(params):
    """First thicken positive masks at fixed answer length, then add more blocks."""
    out = {k: v for k, v in params.items() if k != "_preset"}
    n = out["n"]
    width = out["mask_width"]
    if width < min(7, n - 4):
        out["mask_width"] = width + 1
        return out
    if n + 4 > 36:
        return "cap_bound"
    out["n"] = n + 4
    out["value_slots"] = out["n"]
    out["mask_width"] = min(7, out["n"] - 4)
    return out


def _all_subsets(variables):
    variables = tuple(sorted(variables))
    return [
        frozenset(variables[index] for index in range(len(variables))
                  if (bits >> index) & 1)
        for bits in range(1 << len(variables))
    ]


def _canonical_poly_shape(poly):
    """Coefficient-labelled shape, canonical under renaming its variables."""
    variables = sorted(set().union(*poly.keys())) if poly else []
    best = None
    for image in itertools.permutations(range(len(variables))):
        rename = dict(zip(variables, image))
        code = tuple(sorted(
            (tuple(sorted(rename[var] for var in monomial)), Fraction(coeff))
            for monomial, coeff in poly.items()
        ))
        if best is None or code < best:
            best = code
    return best


_CORE_SHAPE_CACHE = None


def _core_shape_set():
    global _CORE_SHAPE_CACHE
    if _CORE_SHAPE_CACHE is None:
        shapes = set()
        for scale in SCALE_CHOICES:
            for flip_mask in range(16):
                flips = [bool((flip_mask >> role) & 1) for role in range(4)]
                for poly in _transform_base(list(range(4)), flips, scale):
                    shapes.add(_canonical_poly_shape(poly))
        _CORE_SHAPE_CACHE = shapes
    return _CORE_SHAPE_CACHE


def _factor_over_partition(poly, left_variables, counter):
    """Recover the left tensor factor when coefficients have rank one."""
    support = set().union(*poly.keys()) if poly else set()
    left_variables = set(left_variables)
    right_variables = support - left_variables
    left_subsets = _all_subsets(left_variables)
    right_subsets = _all_subsets(right_variables)

    # Use the empty right monomial.  In generated instances it is multiplied
    # by the strictly positive constant coefficient of the mask, so primitive
    # integer normalisation preserves the core factor's sign.
    empty = frozenset()
    pivot_left = next(
        (left for left in left_subsets if poly.get(left, 0) != 0), None
    )
    if pivot_left is None:
        return None
    pivot = Fraction(poly[pivot_left])
    left_factor = {
        left: Fraction(poly.get(left, 0))
        for left in left_subsets if poly.get(left, 0) != 0
    }
    right_factor = {}
    for right in right_subsets:
        coefficient = Fraction(poly.get(pivot_left | right, 0), 1) / pivot
        if coefficient:
            right_factor[right] = coefficient
    for left in left_subsets:
        for right in right_subsets:
            counter[0] += 2
            actual = Fraction(poly.get(left | right, 0))
            predicted = left_factor.get(left, 0) * right_factor.get(right, 0)
            if actual != predicted:
                return None
    return _integer_normalize(left_factor)


def _extract_core_factor(poly, counter):
    support = set().union(*poly.keys()) if poly else set()
    candidates = {}
    shapes = _core_shape_set()
    for size in (2, 3):
        if size > len(support):
            continue
        for variables in itertools.combinations(sorted(support), size):
            factor = _factor_over_partition(poly, variables, counter)
            if factor is None or _canonical_poly_shape(factor) not in shapes:
                continue
            key = tuple(sorted((tuple(sorted(monomial)), coefficient)
                               for monomial, coefficient in factor.items()))
            candidates[key] = factor
    if len(candidates) != 1:
        return None
    return next(iter(candidates.values()))


def _reference_algorithm(inst):
    """Split coefficient tensors, then try all core role/action symmetries."""
    n = inst["n"]
    full = [_poly_from_json(poly, n) for poly in inst["equations"]]
    counter = [0]
    stripped = []
    for poly in full:
        core = _extract_core_factor(poly, counter)
        if core is None:
            return None, counter[0]
        stripped.append(core)

    adjacency = [set() for _ in range(n)]
    for owner, poly in enumerate(stripped):
        support = set().union(*poly.keys()) if poly else set()
        for var in support:
            adjacency[owner].add(var)
            adjacency[var].add(owner)
    components = []
    unseen = set(range(n))
    while unseen:
        start = min(unseen)
        stack = [start]
        component = set()
        while stack:
            v = stack.pop()
            if v in component:
                continue
            component.add(v)
            stack.extend(adjacency[v] - component)
        unseen -= component
        components.append(sorted(component))
    if any(len(component) != 4 for component in components):
        return None, counter[0]

    player_values = [None] * n
    for component in components:
        found = False
        for scale in SCALE_CHOICES:
            for role_to_player in itertools.permutations(component):
                for flip_mask in range(16):
                    trial_flips = [False] * n
                    for role, player in enumerate(role_to_player):
                        trial_flips[player] = bool((flip_mask >> role) & 1)
                    expected = _transform_base(role_to_player, trial_flips, scale)
                    counter[0] += sum(len(poly) for poly in expected)
                    if all(expected[role] == stripped[role_to_player[role]]
                           for role in range(4)):
                        for role, player in enumerate(role_to_player):
                            player_values[player] = _scaled_value(
                                scale, role, trial_flips[player]
                            )
                        found = True
                        break
                if found:
                    break
            if found:
                break
        if not found:
            return None, counter[0]
    answer = {
        "values": [list(value) for value in player_values],
        "selector": list(range(n)),
    }
    return answer, counter[0]


def _carry_permutation(inst, old_to_new):
    n = inst["n"]
    out = {k: v for k, v in inst.items() if k not in (
        "equations", "_core_equations", "_structure", "answer"
    )}
    for key in ("equations", "_core_equations"):
        polys = [_poly_from_json(poly, n) for poly in inst[key]]
        moved = [None] * n
        for old in range(n):
            moved[old_to_new[old]] = _rename_poly(polys[old], old_to_new)
        out[key] = [_poly_to_json(poly) for poly in moved]
    structure = [None] * n
    for old, node in enumerate(inst["_structure"]):
        structure[old_to_new[old]] = {
            "block": node["block"],
            "role": node["role"],
            "scale": node["scale"],
            "masks": [old_to_new[v] for v in node["masks"]],
        }
    out["_structure"] = structure
    selector = [None] * n
    for old, slot in enumerate(inst["answer"]["selector"]):
        selector[old_to_new[old]] = slot
    out["answer"] = {
        "values": [list(v) for v in inst["answer"]["values"]],
        "selector": selector,
    }
    return out


def _carry_action_swaps(inst, swap_flags):
    n = inst["n"]
    out = {k: v for k, v in inst.items() if k not in (
        "equations", "_core_equations", "answer"
    )}
    for key in ("equations", "_core_equations"):
        result = []
        for owner, data in enumerate(inst[key]):
            poly = _poly_from_json(data, n)
            for var, flag in enumerate(swap_flags):
                if flag and var != owner:
                    poly = _flip_variable(poly, var)
            if swap_flags[owner]:
                poly = _scale(poly, -1)
            result.append(_poly_to_json(poly))
        out[key] = result
    values = [list(v) for v in inst["answer"]["values"]]
    selector = list(inst["answer"]["selector"])
    for player, slot in enumerate(selector):
        if swap_flags[player]:
            vector = values[slot]
            values[slot] = [D0 - vector[0]] + [-c for c in vector[1:]]
    out["answer"] = {
        "values": values,
        "selector": selector,
    }
    return out


def _candidate_from_player_values(player_values):
    return {
        "values": [list(value) for value in player_values],
        "selector": list(range(len(player_values))),
    }


def _coefficient_feature(poly, remove_mask_width=0):
    coefficients = list(poly.values())
    maximum = max(abs(value) for value in coefficients)
    term_count = len(poly) // (1 << remove_mask_width)
    absolute_sum = sum(abs(value) for value in coefficients)
    signed_sum = sum(coefficients)
    constant = poly.get(frozenset(), 0)
    return (
        term_count,
        math.log1p(absolute_sum / maximum),
        math.log1p(abs(signed_sum) / maximum),
        math.log1p(abs(constant) / maximum),
        1 if signed_sum > 0 else (-1 if signed_sum < 0 else 0),
        1 if constant > 0 else (-1 if constant < 0 else 0),
    )


def _attack_coefficient_fingerprint(inst):
    """Guess each value from five aggregate per-equation statistics only."""
    templates = {}
    for scale in SCALE_CHOICES:
        for flip_mask in range(16):
            flips = [bool((flip_mask >> role) & 1) for role in range(4)]
            for role, poly in enumerate(_transform_base(list(range(4)), flips, scale)):
                value = tuple(_scaled_value(scale, role, flips[role]))
                templates.setdefault(value, []).append(_coefficient_feature(poly))

    player_options = []
    n = inst["n"]
    for data in inst["equations"]:
        observed = _coefficient_feature(
            _poly_from_json(data, n), inst["mask_width"]
        )
        options = []
        for value, features in templates.items():
            best = min(
                (observed[0] - feature[0]) ** 2 * 4.0 +
                sum((observed[index] - feature[index]) ** 2
                    for index in range(1, 4)) +
                sum(2.0 for index in (4, 5)
                    if observed[index] != feature[index])
                for feature in features
            )
            options.append((best, value))
        player_options.append(sorted(options))

    chosen = []
    used = set()
    for options in player_options:
        value = next(value for _, value in options if value not in used)
        chosen.append(value)
        used.add(value)
    return _candidate_from_player_values(chosen)


def _constant_value(vector):
    return Fraction(vector[0], D0)


def _eval_multilinear_rational(poly, values):
    total = Fraction(0)
    for monomial, coeff in poly.items():
        term = Fraction(coeff)
        for variable in monomial:
            term *= values[variable]
        total += term
    return total


def _attack_greedy(inst):
    n = inst["n"]
    player_vectors = [tuple(CODEBOOK[i]) for i in range(n)]
    equations = [_poly_from_json(poly, n) for poly in inst["equations"]]
    for _ in range(2):
        current = [_constant_value(v) for v in player_vectors]
        for player in range(n):
            best = None
            # A player's own F_i omits y_i, so greedily choose the value that
            # minimizes the residuals of equations in which that player occurs.
            used_elsewhere = set(player_vectors[:player] + player_vectors[player + 1:])
            for vector in CODEBOOK:
                vector = tuple(vector)
                if vector in used_elsewhere:
                    continue
                current[player] = _constant_value(vector)
                score = sum(
                    abs(_eval_multilinear_rational(equations[j], current))
                    for j in range(n) if j != player and
                    any(player in monomial for monomial in equations[j])
                )
                choice = (score, vector)
                if best is None or choice < best:
                    best = choice
            player_vectors[player] = best[1]
            current[player] = _constant_value(best[1])
    return _candidate_from_player_values(player_vectors)


def _attack_cyclic(inst):
    return _candidate_from_player_values(CODEBOOK[:inst["n"]])


def _attack_random_restart(inst, seed, restarts=256):
    rng = random.Random(seed ^ 0x5A17C9)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest():
    report = {}
    planted_attempts = 0
    planted_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in range(3):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            planted_attempts += 1
            if not ok:
                planted_failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                planted_failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not planted_failures,
        "attempts": planted_attempts,
        "failures": planted_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=712, **ship_params)
    corruptions = {}
    dropped = json.loads(json.dumps(inst["answer"]))
    dropped["values"].pop()
    corruptions["drop_one"] = verify(inst, dropped)
    swapped = json.loads(json.dumps(inst["answer"]))
    selectors = list(swapped["selector"])
    selectors[0], selectors[1] = selectors[1], selectors[0]
    swapped["selector"] = selectors
    corruptions["swap_two"] = verify(inst, swapped)
    duplicate = json.loads(json.dumps(inst["answer"]))
    duplicate["values"][1] = list(duplicate["values"][0])
    corruptions["duplicate"] = verify(inst, duplicate)
    corruptions["empty"] = verify(inst, {})
    out_of_range = json.loads(json.dumps(inst["answer"]))
    out_of_range["selector"][0] = inst["n"]
    corruptions["out_of_range"] = verify(inst, out_of_range)
    reasons = [result[1] for result in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not result[0] for result in corruptions.values()) and
                len(set(reasons)) == len(reasons),
        "cases": {name: {"accepted": result[0], "reason": result[1]}
                  for name, result in corruptions.items()},
    }

    wire = json.dumps(inst["answer"], separators=(",", ":"))
    response = "I reduced the exact identities.\n```json\n<answer>" + wire + \
               "</answer>\n```\nThe tags contain only the requested JSON."
    parsed = parse_answer(response)
    garbage = parse_answer("not an answer")
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and garbage is None,
        "model_style_parsed": parsed == inst["answer"],
        "garbage_returns_none": garbage is None,
    }

    guess_rng = random.Random(0x250709422)
    guess_total = 200_000
    guess_hits = 0
    t_guess = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(inst, guess_rng)
        if verify(inst, candidate)[0]:
            guess_hits += 1
    guess_seconds = time.perf_counter() - t_guess
    valid_encodings = math.factorial(inst["n"])
    exact_guess_probability = Fraction(valid_encodings, search_space(inst))
    report["G4_guess_resistance"] = {
        "pass": exact_guess_probability < Fraction(1, 1_000_000),
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_hits / guess_total,
        "exact_probability_numerator": exact_guess_probability.numerator,
        "exact_probability_denominator": exact_guess_probability.denominator,
        "exact_probability": float(exact_guess_probability),
        "structure_aware": True,
        "sample_wall_clock_sec": round(guess_seconds, 6),
        "search_space": search_space(inst),
    }

    attack_names = [
        "aggregate_coefficient_fingerprint",
        "greedy_constant_residual_two_sweeps",
        "random_restart_256",
        "cyclic_value_ansatz",
    ]
    attack_counts = {name: 0 for name in attack_names}
    attack_attempts = 8
    reference_successes = 0
    reference_operations = []
    reference_wall = 0.0
    for seed in range(attack_attempts):
        attack_inst = make_instance(seed=9000 + seed, **ship_params)
        candidates = [
            _attack_coefficient_fingerprint(attack_inst),
            _attack_greedy(attack_inst),
            _attack_random_restart(attack_inst, seed),
            _attack_cyclic(attack_inst),
        ]
        for name, candidate in zip(attack_names, candidates):
            if candidate is not None and verify(attack_inst, candidate)[0]:
                attack_counts[name] += 1
        t0 = time.perf_counter()
        reference, operations = _reference_algorithm(attack_inst)
        reference_wall += time.perf_counter() - t0
        reference_operations.append(operations)
        if reference is not None and verify(attack_inst, reference)[0]:
            reference_successes += 1
    attack_report = {
        name: {"successes": attack_counts[name], "attempts": attack_attempts}
        for name in attack_names
    }
    reference = {
        "name": "rank-one coefficient-tensor split plus exhaustive G4 symmetry matching",
        "complexity": (
            "O(n*(C(s,2)+C(s,3))*2^s + 4224*n) exact coefficient probes; "
            "s<=5 at the shipping preset"
        ),
        "wall_clock_sec": round(reference_wall / attack_attempts, 6),
        "operations": max(reference_operations),
        "solves": f"{reference_successes}/{attack_attempts}, as expected",
    }
    report["G6_adversary_panel"] = {
        "pass": all(value == 0 for value in attack_counts.values()) and
                reference_successes == attack_attempts,
        "attacks": attack_report,
        "reference_algorithm": reference,
        "generic_domain_algorithm_probe": {
            "name": "SymPy 1.12 lexicographic Groebner basis with F5B",
            "demo_wall_clock_sec": 0.00993,
            "shipping_wall_clock_sec": ">120 (timeout)",
            "shipping_seed": 9000,
            "note": "external diagnostic only; SymPy is not imported by this module",
        },
    }

    report["G5_density_and_baseline_cost"] = {
        "pass": guess_total >= 200_000 and reference_successes == attack_attempts,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_estimate": guess_hits / guess_total,
        "theorem_valid_encoding_count": valid_encodings,
        "exact_density_numerator": exact_guess_probability.numerator,
        "exact_density_denominator": exact_guess_probability.denominator,
        "baseline_wall_clock_sec": reference["wall_clock_sec"],
        "baseline_operation_count": reference["operations"],
        "baseline_algorithm": reference["name"],
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] *= 2
    doubled_params["value_slots"] = doubled_params["n"]
    doubled = make_instance(seed=12345, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    ref_small, ops_small = _reference_algorithm(inst)
    ref_large, ops_large = _reference_algorithm(doubled)
    terms_small = sum(len(poly) for poly in inst["equations"])
    terms_large = sum(len(poly) for poly in doubled["equations"])
    report["G7_scales"] = {
        "pass": doubled_ok and ref_small is not None and ref_large is not None and
                terms_large > terms_small and ops_large > ops_small,
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "shipping_terms": terms_small,
        "doubled_terms": terms_large,
        "shipping_reference_operations": ops_small,
        "doubled_reference_operations": ops_large,
    }

    invariant_checks = 0
    carried_checks = 0
    keys = []
    g8_failures = []
    for seed in range(20):
        original = make_instance(seed=20000 + seed, **ship_params)
        key = canonical_key(original)
        keys.append(key)
        rng = random.Random(30000 + seed)
        perm = list(range(original["n"]))
        rng.shuffle(perm)
        old_to_new = {old: perm[old] for old in range(original["n"])}
        permuted = _carry_permutation(original, old_to_new)
        swaps = [bool(rng.getrandbits(1)) for _ in range(original["n"])]
        swapped_inst = _carry_action_swaps(original, swaps)
        composed = _carry_action_swaps(permuted, [swaps[old_to_new_inv]
            for old_to_new_inv in sorted(old_to_new, key=old_to_new.get)])
        for transformed in (permuted, swapped_inst, composed):
            invariant_checks += 1
            if canonical_key(transformed) != key:
                g8_failures.append([seed, "key changed"])
            carried_checks += 1
            if not verify(transformed, transformed["answer"])[0]:
                g8_failures.append([seed, "carried certificate failed"])
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct == 20,
        "invariance_checks": invariant_checks,
        "carried_certificate_checks": carried_checks,
        "distinct_unrelated_keys": distinct,
        "unrelated_instances": 20,
        "transformations": ["player permutation", "action relabelling", "composition"],
        "failures": g8_failures,
    }

    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(inst["answer"])
    # Compact-route accounting at mask_width=2: three ratios determine a dense
    # two-variable tensor factor and three independent cross-products confirm it,
    # per mask variable and equation.  A final codebook/role selection is charged
    # once per player.  Comparisons and transcription are not counted as arithmetic.
    intended_factor_ratio_tests = 6 * inst["mask_width"] * inst["n"]
    intended_codebook_selections = inst["n"]
    intended_operations = intended_factor_ratio_tests + intended_codebook_selections
    arms = {name: dict(G9_ORACLE_RESULTS[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = (arms["hinted"]["solved"] / hinted_attempts
                   if hinted_attempts else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / placebo_attempts
                    if placebo_attempts else 0.0)
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "intended_route_breakdown": {
            "coefficient_ratio_tests": intended_factor_ratio_tests,
            "codebook_role_selections": intended_codebook_selections,
        },
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items() if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
