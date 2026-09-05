# Generalized Implicit Factorization Problem — verified generator

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | number theory |
| Object regime | finite discrete, exact integers |
| Computational core | polynomial identity |
| Certificate form | integer tuple: two prime divisors |
| Intended intuition | change of variables: paired bit shifts turn a factorization into one modular invariant |
| Domain essentiality | native |
| Reduction | none |

## What the family is

This module implements an exact native special case of Feng, Nitaj, and Pan’s [*Generalized Implicit Factorization Problem*](https://arxiv.org/abs/2304.08718). Definition 3 gives two equally long RSA moduli `N_i=p_i q_i`: the two `q_i` have the same `alpha*n` bit length, while the large primes share `gamma*n` consecutive binary digits, possibly at different positions. The solver must return the smaller prime divisor of each displayed modulus.

Instances are inverse-generated. For `K=2^(b-2)`, the generator first constructs and exactly certifies primes `p`, `2p+1`, `q1=2r+1`, and `q2=r+K`, with `q1` and `q2` both exactly `b` bits. Only then does it form

```text
N_A = p(2r+1),              N_B = (2p+1)(r+K).
```

The binary block of `p` beginning at bit 1 occurs in `2p+1` beginning at bit 2. Both products are checked to have exactly `n` bits. The answer is carried through a random row reordering. `verify` checks bit lengths, exact divisibility, factor order, multiplication, and the promised shifted overlap of the recovered large factors; it never reads `inst["answer"]` and accepts any valid divisor pair.

## Why this is Track B

A Track A claim would be false. Section 3.2, Theorem 3 gives a polynomial-time Coppersmith/LLL plus Gröbner-basis attack, under Assumption 1, when

```text
gamma > 4*alpha*(1-sqrt(alpha)),       alpha+gamma <= 1.
```

Unknown block positions add an `O(n^2)` traversal. The shipping instance has `n=200`, `alpha=25/200`, and `gamma=173/200`, so it is deliberately inside that easy-for-tools regime. Table 3 reports 1.8620 seconds for LLL and 0.0033 seconds for Gröbner reduction on a 28-dimensional, 200-bit example (with different finite `alpha`, `beta`, and `gamma`). The locally executable reference scan also succeeds as expected: over eight shipping instances it used 3,865,433 exact trial divisions, 483,179 per instance on average, in 0.266494 seconds.

The short route is hidden structure, not computational hardness. Since

```text
D = N_B-N_A = (2K-1)p + r + K
```

and `K <= r < 2K`, it follows that

```text
r = (D mod (2K-1)) + K - 1,
q1 = 2r+1,
q2 = r+K.
```

The smaller displayed modulus is always `N_A`, so this also fixes the output order. The implementation measures 9 high-level exact operations; a conservative digitwise estimate is 96 steps, including forming `K`, subtracting the 60-digit moduli, and a decimal remainder recurrence. Without recognizing the affine shifts, a no-tool solver must somehow execute the paper’s lattice route or inspect a huge bounded factor range.

## Worked demo

`make_instance(seed=5, **DIFFICULTY["demo"])` renders the following hand-scale problem:

```text
Factor two RSA moduli with a generalized implicit binary overlap.

Definitions and promises:
- Each displayed modulus is a positive integer of exactly 16 binary bits and is the product of two distinct odd primes.
- Bit positions are counted from 0 at the least significant bit.
- For an integer x, start s>=0, and length L>=1, define block(x,s,L) = floor(x/2^s) modulo 2^L.
- If P1 and P2 denote the larger prime factors of the two moduli, there exist two different, unknown starts s1 and s2 such that block(P1,s1,9) = block(P2,s2,9).
- Both smaller prime factors have at most 5 bits.  Thus alpha=5/16 and gamma=9/16; these satisfy the high-overlap regime gamma > 4*alpha*(1-sqrt(alpha)) and alpha+gamma <= 1.

Task:
Return the smaller prime divisor of each modulus, in the displayed order.
The divisor for each row must have exactly the row's stated bit length.
Order matters, the two divisors must be different, decimal notation is required, and neither 1 nor the modulus itself is allowed.

Moduli:
1. N1 = 50761   (smaller prime has exactly 5 bits)
2. N2 = 34193   (smaller prime has exactly 5 bits)

Give your final answer inside <answer></answer> tags, as one JSON array [d1,d2] of exactly two decimal integers.
Example format only: <answer>[104729, 130363]</answer>
Output nothing else inside the tags.
```

Here `K=8`, `D=50761-34193=16568`, and `D mod 15=8`, hence `r=15`. The answer is `<answer>[23,31]</answer>`. `verify(inst,[23,31])` returns `(True,"ok")`; `verify(inst,[23])` returns `(False,"wrong length: expected 2 divisors, got 1")`. This preset is genuinely solvable on paper.

## Difficulty presets

| Preset | Modulus bits | Small-factor bits | Shared bits | Answer atoms | Status |
|---|---:|---:|---:|---:|---|
| demo | 16 | 5 each | 9 | 2 | hand example |
| easy | 200 | 25 each | 173 | 2 | **shipping; oracle held** |
| medium | 300 | 27 each | 271 | 2 | local gates pass |
| hard | 400 | 29 each | 369 | 2 | local gates pass |

The ladder grows both the native modulus and the small-prime search range while keeping the answer at two atoms. `make_instance` also imposes a monotone factor-bit floor from `n=100` onward, so increasing `n` cannot silently leave trial-division difficulty constant.

## Gate results

| Gate | Result | Measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted answers and 48/48 exact prime certificates verified |
| G2 | pass | drop, swap, duplicate, empty, and out-of-range corruptions rejected with five distinct reasons |
| G3 | pass | tagged prose, fenced JSON, garbage rejection, and JSON-native round trip checked |
| G4 | pass | 0/200,000 structure-aware guesses; exact ordered-distinct language size 971,836,143,306 |
| G5 | pass | shipping density 0/200,000; demo exactly 1/20; reference 3,865,433 divisions / 0.266494 s |
| G6 | pass | five attacks each 0/8; mechanical reference 8/8; compact invariant 8/8 in 9 high-level operations each |
| G7 | pass | `n` doubled 200→400, factor bits grew 25→29, planted answer still verified with two atoms |
| G8 | pass | 20/20 row swaps invariant, 20/20 carried witnesses valid, 20/20 unrelated keys distinct |
| G9(c) | pass | 19 characters, 5 estimated tokens, 2 atoms, 96 conservative digitwise operations |

The failing attack panel was: lowest-prime endpoint, low bits of the modulus difference, 256 uniform prime restarts, twelve obvious equal/one-bit GCD relations, and 256 Fermat steps per modulus. Each recorded 0/8. The successful exhaustive scan and compact invariant are reported separately, as Track B requires.

## Oracle loop and G9 arms

The bare script-owned run held `easy` with no escalation:

| Model | Seed | Result | Reason |
|---|---:|---|---|
| `openai/gpt-5.6-terra` | 1550580595 | failed | parsed pair was not a divisor |
| `google/gemini-3.8-flash` | 1711594768 | failed | length-limited reasoning emitted no tagged answer |
| `openai/gpt-5.6-terra` | 410203827 | failed | parsed pair was not a divisor |

The repository’s current `harden.py` is configured with two providers, despite the task text describing a four-vendor default, so one provider necessarily repeats in each three-attempt arm. This is narrower evidence than a four-vendor sweep and is retained explicitly in `.meta.json`.

| G9 arm | Solved/attempts | Verdict |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened |
| placebo hint | 0/3 | hardened |

Hinted-minus-placebo is `0.0`. The structural sentence did not measurably help this pool; that weakens evidence that the benchmark isolates the declared change-of-variables intuition. Two G9 Google calls returned empty length-limited responses after consuming the 32,000-token budget, which the harness scores as failures but the transcripts distinguish from wrong answers.

## Use

From the repository root:

```python
import importlib.util, json

path = "results/2304.08718/gen_2304_08718.py"
spec = importlib.util.spec_from_file_location("generator", path)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=42, **params)
statement = g.render(inst)
answer = g.parse_answer("Result: <answer>" + json.dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

Emit records with:

```bash
bash scripts/emit.sh 2304.08718 20
```

## Caveats

- This is a deliberately structured GIFP subdistribution, not ordinary RSA-key generation. Code that tests the affine construction solves it immediately; that is why it is Track B.
- `0/200,000` samples uniformly from ordered pairs of distinct primes with the stated exact bit length. It does not model a solver conditioned on the hidden affine relation, and it is an observed density, not proof that no other valid pair exists.
- SageMath was unavailable, so the paper’s Coppersmith/LLL implementation was not rerun on these exact instances. The Table 3 timing is from a different 200-bit parameter tuple; the local bounded-prime scan is the measured executable reference.
- ECM, quadratic sieve, number-field sieve, and an external Coppersmith implementation were not tested. The explicit 25-bit bound makes prime trial division the simplest complete mechanical baseline here.
- The oracle evidence uses the two-provider pool actually configured in the repository, not the four-vendor pool stated in the task. Several G9 failures were length-budget failures rather than incorrect factor pairs.
- `canonical_key` handles the instance’s only input relabelling, row order. It does not attempt a broader integer-isomorphism notion, for which these exact moduli have no natural action.
