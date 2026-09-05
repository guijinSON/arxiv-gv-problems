# Odd Egyptian-fraction subset generator (arXiv:1606.02117)

Status: **locally verified, oracle hardening blocked by external OpenRouter quota**.  The module and all local gates are complete, but this result must not be treated as a hardened release until `scripts/harden.py` obtains three valid oracle attempts and records a verdict.

| Profile field | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain | `number_theory` |
| Object regime | `rational_exact` |
| Computational core | `subset_sum` |
| Certificate | `integer_tuple` (the paper's native odd denominators) |
| Intuition | `change of variables`: recover one Lemma 2.5 block from its anchor and common scale |
| Domain essentiality | `native`; no reduction |

## Problem and provenance

Christian Elsholtz's [*Egyptian Fractions with odd denominators*](https://arxiv.org/abs/1606.02117) studies distinct positive integers whose unit fractions sum to one.  The generated problem gives a finite shuffled list of distinct odd denominators and asks for exactly eleven whose reciprocals equal a displayed unit fraction.  Verification checks membership, parity, distinctness, and the reciprocal sum with Python `Fraction`; it never reads the planted answer and uses no floating point.

Lemma 2.5(a) supplies the construction.  Put `q=2^t-1`, choose `d=2^a-1` with `a|t`, set `s=q/d` and `y=q+2d`, and take distinct odd `n_i` satisfying `sum(1/n_i)=2`.  Then

```text
1/q = 1/y + sum_i 1/(s*y*n_i).
```

Here the `n_i` are 1 plus one of the five nine-term odd representations of one recorded in Section 1. (The displayed identity is still exact with `n_i=1`, and the module checks it over Q.) Each instance is a shuffled union of independently sampled complete blocks. Every displayed candidate therefore belongs to a valid answer, and the generator knows every certificate before it assembles the subset instance; it never searches the pool.

## Why Track B

This cannot honestly be Track A: Theorem 1.1 and Corollary 1.2 are abundance results, not distributional hardness theorems, and Lemma 2.5 explicitly exposes the construction. For a solver that misses the structure, the executable reference is fixed-eleven modular meet-in-the-middle search: `O(N^6)` time and `O(N^5)` space for fixed answer length. It already enforces the obvious one-anchor/ten-tail magnitude bound. At shipping `N=44`, it solved 8/8 instances, as expected, averaging 1.296019 seconds and 7,103,905 modular additions before the first exact hit. Exhaustively counting the shipping instance required 19,082,232 additions.

The compact route is different: identify an anchor `q+2d`, derive `d` and the scale `(q/d)(q+2d)`, and select its ten divisible companions. It succeeds 8/8 in the selftest with a conservative budget of 153 exact operations. The paper's easy regime to avoid is precisely a bare request for any nine-term representation: Section 1 says there are only five, making that a fixed lookup rather than an instance family. Mixing independently scaled Lemma 2.5 blocks provides changing instance data while keeping the arithmetic native.

## Worked demo

For `make_instance(n=11, exponent=4, seed=7)`, the complete candidate list is:

```text
target = 1/15
candidates =
525, 24255, 945, 1575, 4725, 735, 315, 3675, 105, 21, 1155
```

The answer is

```text
21, 105, 315, 525, 735, 945, 1155, 1575, 3675, 4725, 24255
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Replacing the last entry by a duplicate returns `(False, "denominators must not repeat")`. A person can solve this demo on paper because all eleven candidates must be selected: their gcd is 21, the remaining terms are 105 times `1,3,5,7,9,11,15,35,45,231`, and the last nine reciprocals sum to one, so the displayed sum is `1/21 + 2/105 = 1/15`.

## Difficulty presets

| Preset | Candidates | Exponent | Search space | Role |
|---|---:|---:|---:|---|
| demo | 11 | 4 | 1 | hand-checkable illustration |
| easy | 22 | 84 | 369,512 | two mixed blocks; first oracle rung |
| medium | 33 | 84 | 90,135,045 | three mixed blocks |
| hard | 44 | 84 | 3,390,642,112 | four mixed blocks; configured shipping rung, oracle validation pending |

Escalation adds one complete eleven-entry block without lengthening the witness. A doubled `N=88` instance builds in 0.055710 seconds, verifies, and has search space 13,171,936,880,960.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted answers; 12/12 JSON-native |
| G2 | pass | five corruptions rejected for five distinct reasons |
| G3 | pass | tagged answer recovered from prose and a Markdown fence |
| G4 | pass | 0/200,000 legal guesses with exactly one target-scale entry; space 3,390,642,112 |
| G5 | pass | exactly 4 solutions; density 1.179717548e-9; full count 19,082,232 additions |
| G6 | pass | five attacks at 0/8; reference algorithm 8/8 |
| G7 | pass | 88-candidate doubled instance builds and verifies |
| G8 | pass | 80/80 invariance checks, 80/80 real transforms, 20/20 distinct unrelated keys |
| G9(c) | pass | worst answer 561 characters, 141 estimated tokens, 11 atoms; route 153 operations and 8/8 recovery |

The failed attacks were smallest-magnitude outliers, exact reciprocal greedy, every consecutive eleven-entry magnitude window, decimal-length clustering, and 256 uniform restarts per seed. Block assemblies are deterministically rejection-sampled against these attacks, but this does not search for a certificate: every complete block is already certified. The generic meet-in-the-middle solver is deliberately reported as the successful Track B reference, not as a failed attack.

## Oracle and G9 diagnostics

| Arm | Rung | Valid solved/attempts | Errors | Outcome |
|---|---|---:|---:|---|
| bare | easy | 0/0 | 4 | blocked by HTTP 403 key-total-limit |
| structural | hard | 0/0 | 4 | blocked by HTTP 403 key-total-limit |
| placebo | hard | 0/0 | 4 | blocked by HTTP 403 key-total-limit |

The bare oracle-loop records are:

| Preset | Seed | Model | Solved | Why |
|---|---:|---|---|---|
| easy | 970850887 | `openai/gpt-5.6-terra` | error | HTTP 403 key-total-limit |
| easy | 2089814119 | `x-ai/grok-4.6` | error | HTTP 403 key-total-limit |
| easy | 2024955103 | `x-ai/grok-4.6` | error | HTTP 403 key-total-limit |
| easy | 983745636 | `x-ai/grok-4.6` | error | HTTP 403 key-total-limit |

Errors do not consume attempts, so `hinted - placebo` is not estimable; the stored numeric placeholder 0.0 is not evidence. The script-owned transcripts preserve every failed request. Once quota is restored, rerun the bare loop in this directory and both diagnostic loops in isolated scratch directories, copy their transcripts back, and update `G9_ORACLE_RESULTS`.

## Use

```python
from gen_1606_02117 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=123, **DIFFICULTY["hard"])
print(render(inst))
candidate = parse_answer("<answer>...</answer>")
print(verify(inst, candidate))
```

From the repository root, after a successful oracle run:

```bash
scripts/emit.sh 1606.02117
```

## Caveats

The exact density uses the strongest freely deducible magnitude prior: choose exactly one of the four entries between `q` and `3q`, then ten of the forty larger entries. It says nothing about a solver using the paper's block prior. Indeed, recognizing `q+2d` makes the family easy by design, and a solver that has memorized the five `k=9` identities has an additional shortcut. Every candidate comes from a complete valid block, eliminating a planted-versus-decoy marginal signature, but this introduces correlations that a stronger gcd/divisibility clusterer could exploit. I did not test lattice reduction, a general-purpose CP/SAT encoding, or a full pairwise-gcd clustering panel. No vendor model produced a valid attempt because the required OpenRouter key was quota-blocked. Most importantly, local attacks are not a substitute for STEP 4: this family remains provisional until the four-vendor bare run says `hardened`.
