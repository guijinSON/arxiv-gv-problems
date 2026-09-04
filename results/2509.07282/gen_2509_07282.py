"""Verified Track-B cryptogram generator based on arXiv:2509.07282.

The paper's native object is a one-to-one monoalphabetic substitution cipher.
Instances here expose such a ciphertext and, on easier rungs, a few correct
ciphertext-to-plaintext crib mappings.  The answer is the complete inverse
permutation.  A SHA-256 commitment to the generated plaintext makes verification
exact without revealing the plaintext or replacing the cryptogram by a surrogate.
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

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "permutation",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "one-to-one monoalphabetic substitution ciphertext",
        "partial inverse-cipher cribs",
        "SHA-256 commitment to the plaintext",
    ],
    "verification_operations": [
        "permutation syntax and bijectivity checks",
        "exact character substitution",
        "exact crib comparison",
        "SHA-256 digest comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "Combine repeated-letter word patterns and frequency clues under one global "
        "bijection; treating words independently leaves an unmanageable permutation search."
    ),
    "hardness_basis": (
        "Track B: ALICE-Base solves by one 12-layer Transformer forward pass, with "
        "Theta(12*(L*d^2+L^2*d)) arithmetic and the paper's measured CPU throughput "
        "of 5,431 letters/s; the exact distribution-aware reference enumerator's "
        "shipping wall time and candidate count are measured in G6, while the intended "
        "pattern-and-bijection route stays below 300 exact character operations."
    ),
    "max_answer_tokens": 7,
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
    "demo": {"n": 5, "variant": 0},
    "easy": {"n": 14, "variant": 0},
    "medium": {"n": 20, "variant": 0},
    "hard": {"n": 26, "variant": 1},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Hint: Link repeated-letter word patterns first, then propagate one bijection "
    "across every occurrence before using ordinary letter frequencies."
)
PLACEBO_HINT = (
    "Hint: Keep the stated alphabet order fixed, and check every position and "
    "punctuation mark before submitting the final permutation."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A 26-character permutation of A through Z.  Position i is the plaintext "
        "letter assigned to ciphertext letter chr(65+i), and every published crib "
        "is fixed in advance."
    ),
    "bounds": {
        "length": 26,
        "alphabet": "A-Z",
        "all_distinct": True,
        "fixed_positions": "26-n published crib positions",
        "candidate_count": "n!",
    },
}

# Filled after the script-owned bare/hinted/placebo runs.  Keeping the evidence in
# one constant makes selftest deterministic and prevents it from inventing results.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}

NOTES = r"""
Paper definition. Section 1.1 fixes the native task: an alphabet Sigma, a
bijection f in the symmetric group, plaintext x, ciphertext c_i=f(x_i), and
inference of f^{-1} from ciphertext without access to f. This module hands the
solver that exact 26-letter object. The answer is the inverse permutation, the
same object made explicit by ALICE-Bijective in Sections 2.1 and 5. A SHA-256
plaintext commitment is validation metadata: it reveals no plaintext characters,
but lets verify decrypt with a proposed permutation and compare exactly instead
of appealing to an English-language oracle.

Step-0 hardness decision. Track A is false for this distribution. Section 3.2
reports near-perfect neural decryption as context grows; Appendix A lists
dictionary, Viterbi, compression and beam-search solvers; Appendix H reports
ALICE-Base at 5,431 letters/s on one CPU core and 1.2 million letters/s on an H100.
The family is therefore openly Track B. The relevant gap is an 85M-parameter,
12-layer mechanical forward pass (or the exact generated-grammar enumeration
measured by selftest) versus the short human route described in Section 5:
frequency evidence appears early and word-level structure later. Appendix I is
direct evidence for the evaluation setting: the paper records state-of-the-art
LLMs failing a short cryptogram even though ALICE solves the class.

Construction. A grammatical plaintext, encryption permutation and inverse key are
sampled first with random.Random(seed); ciphertext and digest are then derived.
The certificate is never found by solving the emitted instance. The text grammar
has hundreds of thousands of combinations and several surface templates, so seeds
do not merely recolor one fixed plaintext. Difficulty n is the number of hidden
inverse-key entries. More n removes freely usable cribs while the answer remains
26 characters. Once all 26 entries are hidden, variant increases difficulty by
shortening the available linguistic context, following Section 3.2's measured
easy/hard direction rather than assuming longer ciphertext is harder.

Reference algorithm and attacks. The local exact reference enumerates this
generator's public distribution, hashes each possible plaintext, and derives a
consistent substitution key at the unique matching commitment. It is measured on
eight shipping seeds. ALICE is the paper's domain-standard polynomial inference
algorithm and its operation estimate is also reported. The failing attack panel
contains an ETAOIN frequency assignment (per-letter outlier probe), first-occurrence
ordering, a greedy 'most common three-letter word is THE' rule, 4,096 uniform
restarts, and a modal-template ansatz a solver could attempt from the prompt alone.
Random keys make ciphertext labels exchangeable; plants and alternatives do not
come from different distributions.

Canonicalization. The only presentation symmetry is a global relabeling of the
ciphertext alphabet, with crib keys and the inverse permutation carried through it.
canonical_key replaces appearing cipher symbols by first-occurrence labels and
canonically orders unseen cribbed symbols by their plaintext targets. The selftest
checks individual relabelings, composed relabelings, carried witnesses, and
distinct plaintext commitments over twenty seeds.
""".strip()


_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)

_ADJECTIVES = (
    "CURIOUS", "PATIENT", "CAREFUL", "MODEST", "RESTLESS", "QUIET",
    "CLEVER", "HONEST", "WEARY", "GENTLE", "DARING", "WATCHFUL",
)
_SUBJECTS = (
    "SCHOLAR", "CAPTAIN", "FARMER", "TEACHER", "PAINTER", "DOCTOR",
    "SAILOR", "BANKER", "RANGER", "SINGER", "LAWYER", "BAKER",
)
_VERBS = (
    "EXAMINED", "CARRIED", "REPAIRED", "MEASURED", "FOLLOWED", "GUARDED",
    "OPENED", "MARKED", "CROSSED", "COUNTED", "WATCHED", "MOVED",
)
_SECOND_ADJECTIVES = (
    "ANCIENT", "BROKEN", "NARROW", "SILVER", "WOODEN", "HIDDEN",
    "EMPTY", "FRAGILE", "DISTANT", "HEAVY", "STRANGE", "BRIGHT",
)
_OBJECTS = (
    "LANTERN", "PACKAGE", "DOORWAY", "COMPASS", "NOTEBOOK", "BRIDGE",
    "CABINET", "PORTRAIT", "BLANKET", "VESSEL", "WINDOW", "GARDEN",
)
_SLOT_POOLS = (
    _ADJECTIVES, _SUBJECTS, _VERBS, _SECOND_ADJECTIVES, _OBJECTS,
)

_TEMPLATES = {
    0: (
        "WHEN THE {0} {1} {2} THE {3} {4}, EVERY PERSON IN THE ROOM BECAME QUIET.",
        "ALTHOUGH A {0} {1} {2} THE {3} {4}, NOBODY DOUBTED THE FINAL REPORT.",
        "BEFORE SUNSET, THE {0} {1} {2} EACH {3} {4} WITH GREAT CARE.",
    ),
    1: (
        "THE {0} {1} {2} A {3} {4} BEFORE MIDNIGHT.",
        "WHY HAD THE {0} {1} {2} THAT {3} {4}?",
        "A {0} {1} QUIETLY {2} THE {3} {4}.",
    ),
    2: (
        "THE {0} {1} {2} THE {3} {4}.",
        "{0} {1}: {2} THAT {3} {4}.",
        "ONE {0} {1} {2} A {3} {4}.",
    ),
}


def _format_plaintext(template: str, words: tuple[str, ...]) -> str:
    return template.format(*words)


def _sample_plaintext(variant: int, rng: random.Random) -> str:
    template = rng.choice(_TEMPLATES[variant])
    words = tuple(rng.choice(pool) for pool in _SLOT_POOLS)
    return _format_plaintext(template, words)


def _translate_letters(text: str, mapping: dict[str, str]) -> str:
    return "".join(mapping.get(ch, ch) for ch in text)


def make_instance(n: int, seed: int = 0, variant: int = 0, **params) -> dict:
    """Inverse-generate a monoalphabetic cryptogram and its inverse key.

    ``n`` is the number of unpublished ciphertext-to-plaintext key entries.
    Larger n strictly enlarges the structure-aware key space from n! to (n+1)!
    when all else is fixed. ``variant`` shortens context after n reaches 26.
    """
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or not 2 <= n <= 26:
        raise ValueError("n must be an integer from 2 through 26")
    if isinstance(variant, bool) or not isinstance(variant, int) or variant not in _TEMPLATES:
        raise ValueError("variant must be 0, 1, or 2")

    rng = random.Random(seed)
    plaintext = _sample_plaintext(variant, rng)

    cipher_letters = list(_ALPHABET)
    rng.shuffle(cipher_letters)
    encrypt = dict(zip(_ALPHABET, cipher_letters))
    decrypt = {cipher: plain for plain, cipher in encrypt.items()}
    ciphertext = _translate_letters(plaintext, encrypt)
    answer = "".join(decrypt[ch] for ch in _ALPHABET)

    hidden = set(rng.sample(list(_ALPHABET), n))
    cribs = {ch: decrypt[ch] for ch in _ALPHABET if ch not in hidden}
    digest = hashlib.sha256(plaintext.encode("ascii")).hexdigest()
    return {
        "family": "committed monoalphabetic substitution cryptogram",
        "alphabet": _ALPHABET,
        "n": n,
        "variant": variant,
        "ciphertext": ciphertext,
        "cribs": cribs,
        "plaintext_sha256": digest,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render a self-contained ciphertext-only cryptogram statement."""
    cribs = inst["cribs"]
    crib_text = (
        "NONE (all 26 inverse-key entries are hidden)"
        if not cribs
        else " ".join(f"{c}->{cribs[c]}" for c in sorted(cribs))
    )
    statement = f"""Exact monoalphabetic substitution cryptogram

The alphabet is the 26 uppercase ASCII letters A through Z. Spaces and
punctuation were not encrypted. One unknown one-to-one substitution was used
everywhere: each plaintext letter was replaced by one unique ciphertext letter,
and different plaintext letters always have different replacements.

Recover the complete INVERSE key. Write exactly 26 uppercase letters. Character
1 of your answer is the plaintext letter produced by ciphertext A, character 2
is the plaintext letter produced by ciphertext B, and so on through ciphertext
Z. Thus your answer must contain each of A,...,Z exactly once. Indices in this
description are 1-based; the key itself has no separators.

Ciphertext:
{inst['ciphertext']}

Known inverse-key cribs (ciphertext->plaintext):
{crib_text}

For exact grading, the intended plaintext's uppercase ASCII byte string has this
SHA-256 digest:
{inst['plaintext_sha256']}
The digest is only a commitment used to check the completed decryption; you are
not expected to invert SHA-256. A key is accepted exactly when it is a permutation,
obeys every crib, decrypts the ciphertext by the convention above, and the complete
decrypted string (including its displayed spaces and punctuation) has that digest.

Give your final answer inside <answer></answer> tags, as one 26-letter uppercase
permutation with no spaces or punctuation.
Example: <answer>QWERTYUIOPASDFGHJKLZXCVBNM</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text) -> object | None:
    """Extract the tagged permutation, tolerating prose and Markdown fences."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    candidate = "".join(match.group(1).split())
    if len(candidate) != 26 or any(ch not in _ALPHABET for ch in candidate):
        return None
    return candidate


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Check any valid inverse key without consulting ``inst['answer']``."""
    if not isinstance(answer, str):
        return False, "answer must be a string"
    if answer == "":
        return False, "answer is empty"
    if len(answer) != 26:
        return False, "key length must be exactly 26"
    if any(ch not in _ALPHABET for ch in answer):
        return False, "key contains a character outside uppercase A-Z"
    if set(answer) != set(_ALPHABET):
        return False, "key must contain every uppercase letter exactly once"

    for cipher, plain in inst["cribs"].items():
        if answer[ord(cipher) - 65] != plain:
            return False, f"key violates published crib {cipher}->{plain}"

    inverse = dict(zip(_ALPHABET, answer))
    plaintext = _translate_letters(inst["ciphertext"], inverse)
    digest = hashlib.sha256(plaintext.encode("ascii")).hexdigest()
    if digest != inst["plaintext_sha256"]:
        return False, "decrypted plaintext does not match the SHA-256 commitment"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from permutations satisfying every published crib."""
    fixed = dict(inst["cribs"])
    open_cipher = [ch for ch in _ALPHABET if ch not in fixed]
    used_plain = set(fixed.values())
    open_plain = [ch for ch in _ALPHABET if ch not in used_plain]
    rng.shuffle(open_plain)
    trial = dict(fixed)
    trial.update(zip(open_cipher, open_plain))
    return "".join(trial[ch] for ch in _ALPHABET)


def search_space(inst: dict) -> int | None:
    """Return the exact structure-aware candidate count n!."""
    hidden = 26 - len(inst["cribs"])
    return math.factorial(hidden)


def enumerate_all(inst: dict) -> int | None:
    """Brute-force exact valid-answer count when at most eight entries are hidden."""
    fixed = dict(inst["cribs"])
    open_cipher = [ch for ch in _ALPHABET if ch not in fixed]
    if len(open_cipher) > 8:
        return None
    open_plain = [ch for ch in _ALPHABET if ch not in set(fixed.values())]
    count = 0
    for perm in itertools.permutations(open_plain):
        candidate = dict(fixed)
        candidate.update(zip(open_cipher, perm))
        key = "".join(candidate[ch] for ch in _ALPHABET)
        if verify(inst, key)[0]:
            count += 1
    return count


def _canonical_payload(inst: dict) -> dict:
    labels: dict[str, int] = {}
    next_label = 0
    encoded = []
    for ch in inst["ciphertext"]:
        if ch in _ALPHABET:
            if ch not in labels:
                labels[ch] = next_label
                next_label += 1
            encoded.append(labels[ch])
        else:
            encoded.append(ch)

    unseen_cribs = sorted(
        ((plain, cipher) for cipher, plain in inst["cribs"].items() if cipher not in labels)
    )
    for _plain, cipher in unseen_cribs:
        labels[cipher] = next_label
        next_label += 1
    crib_repr = sorted((labels[cipher], plain) for cipher, plain in inst["cribs"].items())
    return {
        "cipher_pattern": encoded,
        "cribs": crib_repr,
        "plaintext_sha256": inst["plaintext_sha256"],
    }


def canonical_key(inst: dict) -> str:
    """Canonicalize global ciphertext-alphabet relabelings."""
    payload = json.dumps(_canonical_payload(inst), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Hide more mappings first, then shorten context at fixed answer length."""
    clean = {k: v for k, v in params.items() if k != "_preset"}
    n = int(clean.get("n", 26))
    variant = int(clean.get("variant", 0))
    if n < 26:
        return {"n": min(26, n + 4), "variant": variant}
    if variant < 2:
        return {"n": 26, "variant": variant + 1}
    return None


# ---------------------------------------------------------------------------
# Reference solver and deliberately cheap attacks used only by selftest.

def _key_from_plaintext(inst: dict, plaintext: str) -> str | None:
    if len(plaintext) != len(inst["ciphertext"]):
        return None
    mapping: dict[str, str] = dict(inst["cribs"])
    reverse = {plain: cipher for cipher, plain in mapping.items()}
    for cipher, plain in zip(inst["ciphertext"], plaintext):
        if cipher in _ALPHABET:
            if plain not in _ALPHABET:
                return None
            if cipher in mapping and mapping[cipher] != plain:
                return None
            if plain in reverse and reverse[plain] != cipher:
                return None
            mapping[cipher] = plain
            reverse[plain] = cipher
        elif cipher != plain:
            return None
    open_cipher = [ch for ch in _ALPHABET if ch not in mapping]
    open_plain = [ch for ch in _ALPHABET if ch not in reverse]
    mapping.update(zip(open_cipher, open_plain))
    key = "".join(mapping[ch] for ch in _ALPHABET)
    return key if verify(inst, key)[0] else None


def _reference_grammar_solver(inst: dict) -> tuple[str | None, int]:
    """Exact distribution-aware enumeration; returns (key, candidates hashed)."""
    target = inst["plaintext_sha256"]
    tested = 0
    for template in _TEMPLATES[inst["variant"]]:
        for words in itertools.product(*_SLOT_POOLS):
            plaintext = _format_plaintext(template, words)
            tested += 1
            if hashlib.sha256(plaintext.encode("ascii")).hexdigest() != target:
                continue
            return _key_from_plaintext(inst, plaintext), tested
    return None, tested


def _fill_key(inst: dict, partial: dict[str, str], cipher_order: list[str],
              plain_order: str) -> str | None:
    mapping = dict(inst["cribs"])
    for cipher, plain in partial.items():
        if cipher not in _ALPHABET or plain not in _ALPHABET:
            return None
        if cipher in mapping and mapping[cipher] != plain:
            return None
        if plain in mapping.values() and mapping.get(cipher) != plain:
            return None
        mapping[cipher] = plain
    if len(set(mapping.values())) != len(mapping):
        return None
    remaining_plain = [ch for ch in plain_order if ch not in set(mapping.values())]
    remaining_plain += [
        ch for ch in _ALPHABET if ch not in set(mapping.values()) and ch not in remaining_plain
    ]
    remaining_cipher = [ch for ch in cipher_order if ch not in mapping]
    remaining_cipher += [
        ch for ch in _ALPHABET if ch not in mapping and ch not in remaining_cipher
    ]
    if len(remaining_cipher) != len(remaining_plain):
        return None
    mapping.update(zip(remaining_cipher, remaining_plain))
    return "".join(mapping[ch] for ch in _ALPHABET)


def _frequency_attack(inst: dict) -> str | None:
    counts = {ch: inst["ciphertext"].count(ch) for ch in _ALPHABET}
    cipher_order = sorted(_ALPHABET, key=lambda ch: (-counts[ch], ch))
    return _fill_key(inst, {}, cipher_order, "ETAOINSHRDLCUMWFGYPBVKJXQZ")


def _first_occurrence_attack(inst: dict) -> str | None:
    seen = []
    for ch in inst["ciphertext"]:
        if ch in _ALPHABET and ch not in seen:
            seen.append(ch)
    return _fill_key(inst, {}, seen, _ALPHABET)


def _greedy_the_attack(inst: dict) -> str | None:
    words = re.findall(r"[A-Z]+", inst["ciphertext"])
    triples = [word for word in words if len(word) == 3 and len(set(word)) == 3]
    partial: dict[str, str] = {}
    if triples:
        word = max(triples, key=lambda w: (words.count(w), -words.index(w)))
        partial = dict(zip(word, "THE"))
    counts = {ch: inst["ciphertext"].count(ch) for ch in _ALPHABET}
    order = sorted(_ALPHABET, key=lambda ch: (-counts[ch], ch))
    return _fill_key(inst, partial, order, "ETAOINSHRDLCUMWFGYPBVKJXQZ")


def _modal_template_attack(inst: dict) -> str | None:
    modal_words = tuple(pool[0] for pool in _SLOT_POOLS)
    for template in _TEMPLATES[inst["variant"]]:
        key = _key_from_plaintext(inst, _format_plaintext(template, modal_words))
        if key is not None:
            return key
    return _frequency_attack(inst)


def _random_restart_attack(inst: dict, seed: int, trials: int = 4096) -> tuple[str | None, int]:
    rng = random.Random(seed)
    last = None
    for attempt in range(1, trials + 1):
        last = random_candidate(inst, rng)
        if verify(inst, last)[0]:
            return last, attempt
    return last, trials


def _relabel_instance(inst: dict, relabel: dict[str, str]) -> dict:
    transformed = dict(inst)
    transformed["ciphertext"] = _translate_letters(inst["ciphertext"], relabel)
    transformed["cribs"] = {relabel[c]: p for c, p in inst["cribs"].items()}
    old_key = inst["answer"]
    carried = [""] * 26
    for old_cipher in _ALPHABET:
        new_cipher = relabel[old_cipher]
        carried[ord(new_cipher) - 65] = old_key[ord(old_cipher) - 65]
    transformed["answer"] = "".join(carried)
    return transformed


def _alice_multiply_accumulates(length: int) -> int:
    """Architecture-derived MAC estimate from Table 3 (d=768, f=2048, 12 layers)."""
    d_model = 768
    d_ff = 2048
    layers = 12
    per_layer = (
        4 * length * d_model * d_model
        + 3 * length * d_model * d_ff
        + 2 * length * length * d_model
    )
    return layers * per_layer


def _answer_elements(answer: str) -> int:
    return len(answer)


def selftest() -> dict:
    """Run all mandatory gates and return only JSON-native measured evidence."""
    report: dict[str, object] = {
        "paper": "2509.07282",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    # G1: every preset, several seeds, plus JSON-native answer serialization.
    g1_failures = []
    g1_count = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(5):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            json_native = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            g1_count += 1
            if not ok or not json_native:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "instances": g1_count,
        "failures": g1_failures,
    }

    ship = make_instance(seed=20250907, **DIFFICULTY[SHIPPING_DIFFICULTY])

    # G2: five specified corruption types, deliberately routed to distinct reasons.
    planted = ship["answer"]
    used_cipher = sorted(set(ch for ch in ship["ciphertext"] if ch in _ALPHABET))
    swapped = list(planted)
    i, j = (ord(used_cipher[0]) - 65, ord(used_cipher[1]) - 65)
    swapped[i], swapped[j] = swapped[j], swapped[i]
    duplicate = planted[:-1] + planted[0]
    out_of_range = "!" + planted[1:]
    corruptions = {
        "drop_one": planted[:-1],
        "swap_two": "".join(swapped),
        "duplicate_one": duplicate,
        "empty": "",
        "out_of_range": out_of_range,
    }
    rejection_reasons = {name: verify(ship, value)[1] for name, value in corruptions.items()}
    rejection_flags = {name: not verify(ship, value)[0] for name, value in corruptions.items()}
    report["G2_rejects_corruption"] = {
        "pass": all(rejection_flags.values()) and len(set(rejection_reasons.values())) == 5,
        "rejected": rejection_flags,
        "reasons": rejection_reasons,
        "distinct_reasons": len(set(rejection_reasons.values())),
    }

    # G3: model-style prose and fenced output round trip exactly.
    response = (
        "I propagated the bijection and checked the commitment.\n```text\n"
        f"<answer>\n{planted}\n</answer>\n```\n"
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("garbage") is None,
        "parsed_equals_answer": parsed == planted,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    # G4 and shipping density sample use the exact crib-respecting language.
    guess_rng = random.Random(9042001)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(ship, random_candidate(ship, guess_rng))[0])
    guess_probability = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_probability,
        "structure_aware_search_space": search_space(ship),
        "candidate_prior": "uniform over all permutations satisfying every published crib",
    }

    # G6 attacks: eight independent shipping seeds each.
    attack_seeds = [3101, 3109, 3119, 3121, 3137, 3163, 3167, 3181]
    attacks = {
        "outlier_frequency_etaoin": {"successes": 0, "attempts": 0},
        "first_occurrence_order": {"successes": 0, "attempts": 0},
        "greedy_three_letter_THE": {"successes": 0, "attempts": 0},
        "random_restart_4096": {"successes": 0, "attempts": 0},
        "in_context_modal_template": {"successes": 0, "attempts": 0},
    }
    random_trials_total = 0
    attack_start = time.perf_counter()
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "outlier_frequency_etaoin": _frequency_attack(inst),
            "first_occurrence_order": _first_occurrence_attack(inst),
            "greedy_three_letter_THE": _greedy_the_attack(inst),
            "in_context_modal_template": _modal_template_attack(inst),
        }
        random_answer, random_trials = _random_restart_attack(inst, seed ^ 0xA11CE)
        candidates["random_restart_4096"] = random_answer
        random_trials_total += random_trials
        for name, candidate in candidates.items():
            attacks[name]["attempts"] += 1
            attacks[name]["successes"] += int(candidate is not None and verify(inst, candidate)[0])
    attack_wall = time.perf_counter() - attack_start

    # Track-B reference algorithm: actually solve eight shipping instances.
    reference_successes = 0
    reference_candidates = 0
    reference_max_candidates = 0
    reference_start = time.perf_counter()
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key, tested = _reference_grammar_solver(inst)
        reference_candidates += tested
        reference_max_candidates = max(reference_max_candidates, tested)
        reference_successes += int(key is not None and verify(inst, key)[0])
    reference_wall = time.perf_counter() - reference_start

    sample_length = len(ship["ciphertext"])
    reference_algorithm = {
        "name": "exact generated-grammar enumeration (with ALICE-Base as domain reference)",
        "complexity": "Theta(T*s^5*L) locally; ALICE is one 12-layer Transformer forward pass",
        "wall_clock_sec": round(reference_wall, 6),
        "operations": reference_candidates,
        "max_candidates_one_instance": reference_max_candidates,
        "solves": f"{reference_successes}/{len(attack_seeds)}",
        "paper_ALICE_estimated_MACs_at_sample_length": _alice_multiply_accumulates(sample_length),
        "paper_ALICE_CPU_seconds_at_sample_length": round(sample_length / 5431.0, 6),
        "shipping_sample_ciphertext_characters": sample_length,
    }
    all_attacks_failed = all(value["successes"] == 0 for value in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == len(attack_seeds),
        "attacks": attacks,
        "reference_algorithm": reference_algorithm,
    }

    # G5 records shipping density and the strongest failing attack's measured cost.
    hidden_unused = [
        ch for ch in _ALPHABET
        if ch not in set(c for c in ship["ciphertext"] if c in _ALPHABET)
        and ch not in ship["cribs"]
    ]
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_probability < 1e-6 and all_attacks_failed,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_valid_fraction": guess_probability,
        "analytic_valid_solution_count": math.factorial(len(hidden_unused)),
        "baseline_wall_clock_seconds": round(attack_wall, 6),
        "baseline_candidate_trials": random_trials_total,
        "baseline_attack": "random_restart_4096 plus four deterministic no-tool probes",
        "demo_exact_solution_count": enumerate_all(
            make_instance(seed=20250907, **DIFFICULTY["demo"])
        ),
    }

    # G7: doubling hidden-key size strictly expands the space and keeps G1 true.
    half = make_instance(n=13, seed=771, variant=0)
    doubled = make_instance(n=26, seed=771, variant=0)
    g7_ok = (
        verify(half, half["answer"])[0]
        and verify(doubled, doubled["answer"])[0]
        and search_space(doubled) > search_space(half)
    )
    report["G7_scales"] = {
        "pass": g7_ok,
        "n_before": 13,
        "n_after_doubling": 26,
        "space_before": search_space(half),
        "space_after": search_space(doubled),
        "answer_elements_before": _answer_elements(half["answer"]),
        "answer_elements_after": _answer_elements(doubled["answer"]),
    }

    # G8: arbitrary relabelings, compositions, carried witnesses, and diversity.
    invariant_checks = 0
    carried_checks = 0
    invariant_ok = True
    carried_ok = True
    unrelated_keys = []
    for seed in range(20):
        inst = make_instance(seed=8000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        unrelated_keys.append(canonical_key(inst))
        rng = random.Random(9000 + seed)
        perm1 = list(_ALPHABET)
        perm2 = list(_ALPHABET)
        rng.shuffle(perm1)
        rng.shuffle(perm2)
        relabel1 = dict(zip(_ALPHABET, perm1))
        relabel2 = dict(zip(_ALPHABET, perm2))
        transformed1 = _relabel_instance(inst, relabel1)
        transformed2 = _relabel_instance(transformed1, relabel2)
        base_key = canonical_key(inst)
        for transformed in (transformed1, transformed2):
            invariant_checks += 1
            invariant_ok = invariant_ok and canonical_key(transformed) == base_key
            carried_checks += 1
            carried_ok = carried_ok and verify(transformed, transformed["answer"])[0]
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_ok and carried_ok and distinct_count == 20,
        "invariance_checks": invariant_checks,
        "invariance_passed": invariant_checks if invariant_ok else 0,
        "carried_witness_checks": carried_checks,
        "carried_witness_passed": carried_checks if carried_ok else 0,
        "unrelated_instances": 20,
        "distinct_keys": distinct_count,
        "symmetries": ["ciphertext alphabet relabeling", "composition of two relabelings"],
    }

    # G9 caps are local measurements; oracle evidence is script-owned.
    answer_chars = len(json.dumps(ship["answer"]))
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = len(ship["answer"])
    intended_ops = 2 * len(ship["ciphertext"]) + 26
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = arms["hinted"]["solved"] / hinted_attempts if hinted_attempts else 0.0
    placebo_rate = arms["placebo"]["solved"] / placebo_attempts if placebo_attempts else 0.0
    evidence_complete = all(arms[name]["attempts"] >= 3 for name in arms)
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    hinted_hardened = G9_ORACLE_RESULTS["hinted_verdict"] == "hardened"
    report["G9_no_tool_suitability"] = {
        "pass": evidence_complete and hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "within_caps": within_caps,
    }

    gate_values = [
        value for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    ]
    report["all_passed"] = all(value.get("pass") is True for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
