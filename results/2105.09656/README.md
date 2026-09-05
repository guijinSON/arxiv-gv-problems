# Verified problem generator for arXiv:2105.09656

| Profile | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain / object regime | number theory / finite field |
| Computational core | other (exact quadratic-field exponentiation) |
| Certificate | matrix certificate: one encoded element of each quadratic field |
| Intended intuition | invariant: the cyclotomic value depends on `p mod 16`, not on the chosen square root |
| Domain essentiality | native; no reduction |

## Problem and trust model

The source is Pallozzi Lavorante and Smaldore, [*New hemisystems of the Hermitian surface*](https://arxiv.org/abs/2105.09656). Section 3 states the orbit conditions used to make a half-hemisystem. In the previously unresolved case `p = 5 (mod 8)`, Section 4 introduces

`L=(1+h)^((p+1)/2) h^((p-1)/2)` in `F_p[h]/(h^2-2)`.

Proposition 4.7 and Appendix A prove that `L=-1` for `p=5 (mod 16)` and `L=+1` for `p=13 (mod 16)`, independently of the choice `h` or `-h`. This sign enters the explicit base generator used to select the two hemisystem orbits. An instance supplies many such native finite-field expressions, each hidden behind an invertible affine encoding; the solver returns their exact `[a,b]` coordinates. `verify` recomputes every power by exact quadratic-field arithmetic and never reads `inst["answer"]`.

Generation is theorem-backed. It samples equal numbers of exact 64-bit-certified primes in the two residue classes, then obtains each answer from Proposition 4.7 rather than evaluating the public expression. Root signs, affine offsets, scales, and row order are independent. For `n>63`, the generator adds multiples of `p^2-1` to the exponents; this is a certificate-preserving transformation in `F_(p^2)^*` and lets the mechanical size grow without lengthening the witness.

## Why this is Track B

This is not a computational-hardness claim. Binary square-and-multiply solves every instance in `O(kb)` exact `F_(p^2)` multiplications for `k` rows and `b`-bit exponents. The retained shipping self-test solved 8/8 reference instances using 71,868 counted coefficient operations and 8,972 field multiplications per instance; its measured mean wall time was 0.0051 seconds. That efficient algorithm makes Track A false.

The compact route is Proposition 4.7: inspect `p mod 16`, choose the sign, and apply the public affine encoding. It uses at most 144 exact operations for 48 rows. The bare oracle pool failed 0/3 at that size, while the structural hint produced 2/3 solves and the placebo produced 0/3. The measured difficulty therefore lies largely in finding the invariant, not in a claim that the mechanical algorithm is slow on a computer.

The full hemisystem was deliberately not used as the answer. Even the smallest `p=5` case has 378 selected lines, already beyond the 256-atom cap. The module keeps the paper's exact finite-field object instead of compiling the geometry into a graph.

## Worked demo (`n=4, k=2, seed=0`)

The complete rendered instance is:

```text
Evaluate cyclotomic signs in quadratic finite fields

For each independently listed row i, work in the field

    F_i = F_{p_i}[H]/(H^2-2).

Represent a+bH by the JSON pair [a,b], using the unique integers
0 <= a,b < p_i. All additions, multiplications, and powers below are
in F_i. The listed root r_i is either H or -H; in both cases r_i^2=2.
Define

    L_i = (1+r_i)^((p_i+1)/2) * r_i^((p_i-1)/2),
    Z_i = offset_i + scale_i * L_i.

Compute every Z_i exactly and return them in the listed order. Each
p_i is prime and is 5 or 13 modulo 16, so 2 is a nonsquare modulo
p_i and the displayed quotient really is a field. Every scale is
nonzero. Indices are 0-based; no rows may be omitted or repeated.

There are k=2 rows:
  0: p=5, r=H, offset=0, scale=3
  1: p=13, r=H, offset=6, scale=5

Your answer must be a JSON list of exactly 2 pairs [a,b].
Pair i is reduced modulo its own p_i with both endpoints allowed; the
coordinate bounds 0 <= a,b < p_i are inclusive on the left and
exclusive on the right.

Give your final answer inside <answer></answer> tags as that JSON list.
Example: <answer>[[3,0],[7,2]]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[[2,0],[11,0]]</answer>`. `verify(inst, [[2,0],[11,0]])` returns `(True, "ok")`; changing the first row to `[3,0]` returns `(False, "the encoded values have wrong multiplicities")`. A person can solve this demo on paper by evaluating the two tiny fields or checking the two residue cases; `enumerate_all` checks all four structure-aware sign matrices and finds exactly one answer.

## Difficulty presets

| Preset | `n` | Rows `k` | Status |
|---|---:|---:|---|
| demo | 4 | 2 | hand-scale illustration |
| easy | 63 | 32 | defeated by 1/3 bare oracles during escalation |
| medium | 63 | 40 | defeated by 2/3 bare oracles during escalation |
| hard | 63 | 48 | **shipping; held 0/3** |

The initial 31-bit, 43-bit, and 59-bit rungs were also defeated and were removed when the ladder was slid upward. The final fixed-answer-length exponent axis supports `n=126`; G7 built and verified it with the same 48-row witness.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 preset/seed witnesses verified and JSON-round-tripped |
| G2 | pass | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | pass | prose/fence/tag round-trip; malformed text returned `None` |
| G4 | pass | 0/200,000 structure-aware guesses; language size `2^48` |
| G5 | pass | shipping sampled density 0/200,000; 4,096 branch restarts failed in 0.510 s; demo exact count 1 |
| G6 | pass | four no-tool attacks each 0/8; reference exponentiation 8/8 |
| G7 | pass | `n=126,k=48` built and verified; answer rows unchanged |
| G8 | pass | 100/100 invariant keys and carried witnesses; 20/20 unrelated keys distinct |
| G9 | pass | 1,143 chars, 472 measured tokens, 96 atoms, 144 intended operations |

G4 uses the prior a careful solver gets after the freely deducible identity `L_i^2=1`: each row is sampled uniformly from its two affine sign branches. It does not use the misleading product of all quadratic fields.

## Bare oracle loop

The transcript retains every prescribed escalation. “Fail” means no accepted witness; the reason is the exact checker result.

| Historical rung / params | Model | Seed | Result | Reason |
|---|---|---:|---|---|
| easy `31×32` | Terra | 801052117 | solve | ok |
| easy `31×32` | Gemini | 1605265705 | solve | ok |
| easy `31×32` | Gemini | 1654318290 | solve | ok |
| medium `43×32` | Terra | 1698930531 | solve | ok |
| medium `43×32` | Gemini | 1705213161 | solve | ok |
| medium `43×32` | Terra | 15190356 | solve | ok |
| hard `59×32` | Terra | 788934981 | solve | ok |
| hard `59×32` | Gemini | 1963905511 | fail | wrong multiplicities |
| hard `59×32` | Gemini | 1492178871 | solve | ok |
| escalated `62×32` | Terra | 242702326 | solve | ok |
| escalated `62×32` | Gemini | 1133736053 | fail | wrong multiplicities |
| escalated `62×32` | Terra | 545974551 | fail | wrong multiplicities |
| escalated `63×32` | Terra | 1029026688 | solve | ok |
| escalated `63×32` | Gemini | 132050915 | fail | wrong multiplicities |
| escalated `63×32` | Terra | 1067217201 | fail | wrong multiplicities |
| escalated `63×40` | Gemini | 1939631135 | fail | no parsed answer |
| escalated `63×40` | Terra | 532298303 | solve | ok |
| escalated `63×40` | Terra | 798487166 | solve | ok |
| escalated `63×48` | Gemini | 739989381 | fail | row 7 out of range |
| escalated `63×48` | Terra | 220893828 | fail | wrong multiplicities |
| escalated `63×48` | Terra | 2018006680 | fail | wrong multiplicities |

The script-owned verdict is `hardened` at `n=63,k=48` after six escalations.

## G9 arms

| Arm | Solved / attempts | Interpretation |
|---|---:|---|
| bare | 0 / 3 | shipping level held |
| structural hint | 2 / 3 | naming the modulo-16 invariant exposed the compact route |
| placebo hint | 0 / 3 | an extra non-structural sentence did not help |

`hinted - placebo = 0.667`. This is positive evidence for the declared invariant intuition: the bare difficulty is substantially about discovering the structure. The hinted arm is diagnostic and does not gate shipping. The answer-size measurements are 1,143 characters, 472 tokens, and 96 atomic integers; the compact route is bounded by 144 exact operations.

## Use

```python
import json
from gen_2105_09656 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
print(render(inst))
wire = "<answer>" + json.dumps(inst["answer"]) + "</answer>"
answer = parse_answer(wire)
assert verify(inst, answer) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 2105.09656
```

## Caveats

- This isolates the cyclotomic sign calculation used by the hemisystem proof; it does not ask for, or claim benchmark coverage of, the full geometric hemisystem construction.
- Knowing Proposition 4.7 makes the family easy. That is intentional Track B behavior and is confirmed by the 2/3 hinted result; it must never be described as average-case or cryptographic hardness.
- The 0/200,000 estimate is for independent uniform choices among the two sign branches. It does not model a theorem-aware solver, for whom all 48 signs are correlated with the public residue classes and the answer is direct.
- The adversary panel tried the smaller encoded branch, an all-plus greedy rule, 256 random branch restarts, and the tempting rule that follows the displayed root sign. It did not run a CAS, a general finite-field package, a learned cross-instance attack, or a direct reconstruction of Appendix A; tool-backed versions are expected to succeed and do not contradict Track B.
- Exact deterministic primality is limited to 63-bit primes. Above `n=63`, difficulty grows by licensed multiplicative-period exponent lifts rather than by larger moduli.
- The affine encodings require 48 modular additions/subtractions after the insight, so some failures may include arithmetic or transcription error. The route remains below every G9 cap, and the hint/placebo contrast shows that arithmetic alone did not explain the observed bare failures.
- The outer task runner overwrote `.meta.json` while the long bare hardening run was still active, so that run's master seed is not recoverable and was not fabricated. Every individual oracle model, instance seed, response, checker result, and elapsed time remains intact in the script-written transcript; the oracle pool and final verdict are retained in metadata.
- `gvlib` is available but has no quadratic finite-field helper; the module therefore uses a small standard-library-only exact implementation.
