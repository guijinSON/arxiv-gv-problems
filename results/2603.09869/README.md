# Plücker-invariant evaluation on Vandermonde codes

This is a self-contained, verified generator based on Alecci and D’Alconzo, [*Linear Code Equivalence via Plücker Coordinates*](https://arxiv.org/abs/2603.09869). It ships on **Track B**: a standard exact algorithm exists and is reported, while the intended task is to recognize a short algebraic compression.

| Profile field | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | polynomial identity |
| Certificate | exact symbolic: one canonical residue in `GF(p)` |
| Native objects | linear code, Vandermonde generator matrix, Plücker coordinates, invariant rational function |
| Intuition | change of variables: factor the minors as Vandermonde products and cancel common factors |
| Domain essentiality | native |
| Reduction | none |

## What the problem is and why it is trustworthy

The solver receives a prime field, distinct nodes `t_j`, and the exact formula `G[r,j] = t_j^r` for a generator matrix of a linear code. Four `k`-column sets define Plücker coordinates (maximal minors), and the solver must evaluate

`p_I1 p_J1 / (p_I2 p_J2)` in the field.

The sets obey `I1 ⊎ J1 = I2 ⊎ J2`. Section 4, Lemma 2 of the paper proves that this ratio is invariant under independent nonzero coordinate scalings; Theorem 4.1 uses such invariants to obtain equations for the permutation part of a code equivalence, and Theorem 4.2 gives the resulting degree and monomial count. Verification is exact: it reconstructs each minor through the Vandermonde determinant identity, performs modular inversion, and compares the canonical residue. It never reads `inst["answer"]`.

The answer is known by inverse generation. A target residue is sampled first, the fourth exceptional node is obtained from one fractional-linear equation, and a random coordinate permutation carries the determinant-orientation sign. No determinant or equivalence problem is solved during generation.

## Why Track B

Track A would be false. Section 4 explicitly calls the four-minor invariant polynomial-time computable. The reference implementation materialises all four dense `k × k` minors and uses modular Gaussian elimination, costing `O(k^3)` field operations. At the shipping `k=126`, it solved 8/8 instances, with at most **5,375,448 counted operations** and **0.362 seconds** for one run (2.715 seconds total in the recorded benchmark).

The compact route uses the Vandermonde identity. The four sets share `k-2` columns, whose pairwise-difference factors cancel. Only four oriented differences remain, so the shipping measurement used **21 exact field/Euclidean operations**, including the modular inverse. The paper identifies the opposite scale problem too: Section 4 says the full incidence matrix has `binomial(n,k)` rows for `k=O(n)`, while Theorem 4.2’s polynomial has degree `2k` and `2(k!)²` monomials; it is not practical at the stated cryptographic scale `k >= 126`.

## Worked demo

The `demo` preset at seed 7 is genuinely hand-scale:

```text
PROBLEM: Evaluate a diagonal-invariant ratio of Plucker coordinates exactly.

Work in the prime field GF(101); all arithmetic, including division, is modulo 101.
The code has dimension k=3 and length m=5.
Its k by m generator matrix G is given exactly (without expanding it) by
    G[r,j] = t_j^r in GF(p),
for row indices r=0,...,2 and column indices j=0,...,4.
Thus row 0 consists of ones.  The nodes t_j, in increasing zero-based column-index order, are:
    51, 84, 20, 93, 7

For a k-element set I of column indices, p_I is the determinant in GF(p) of the k by k submatrix formed by those columns in increasing index order.  These are Plucker coordinates of the code.
The four displayed sets have size k and satisfy I1 multiset-union J1 = I2 multiset-union J2.  The nodes are pairwise distinct, so every displayed minor is nonzero.

I1 = [1, 2, 4]
J1 = [0, 3, 4]
I2 = [2, 3, 4]
J2 = [0, 1, 4]

Compute the unique canonical nonzero residue a with 1 <= a < p such that
    a = p_I1 * p_J1 / (p_I2 * p_J2) in GF(p).
Independent nonzero rescaling of any coordinate column would not change this ratio.

Give your final answer inside <answer></answer> tags, as one base-10 integer in the range 1 through p-1.
Example: <answer>37</answer>
Output nothing else inside the tags.
```

Its planted answer is `<answer>58</answer>`. `verify(inst, 58)` returns `(True, "ok")`; `verify(inst, 59)` returns `(False, "residue does not equal the displayed Plucker ratio")`. A person can solve this instance by expanding four `3 × 3` determinants or, more cleanly, by cancelling Vandermonde factors.

## Difficulty presets

| Preset | Minor order `k` | Code length | Prime | Oracle result |
|---|---:|---:|---:|---|
| demo | 3 | 5 | 101 | hand-scale; skipped by hardener |
| easy | 32 | 34 | 1,000,003 | 2/3 solved |
| medium | 64 | 66 | 1,000,000,007 | 3/3 solved |
| **hard (ships)** | **126** | **128** | **2,147,483,647** | **0/3 solved** |

`escalate()` grows both the minor order and the prime while leaving the answer at one atomic element. A doubled `n=252` instance builds and verifies.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 16/16 planted, JSON, multiset, and compact-formula checks |
| G2 | pass | five required corruptions rejected with five distinct reasons; a wrong in-range residue also rejected |
| G3 | pass | tagged model-style response round-tripped; garbage returned `None` |
| G4 | pass | 0/200,000 structure-aware guesses; exact probability `1/2,147,483,646` |
| G5 | pass | shipping density sample 0/200,000; reference max 5,375,448 operations and 0.362 s |
| G6 | pass | five attacks, each 0/8; Gaussian reference 8/8 as expected |
| G7 | pass | escalated `k=189` and doubled `k=252` both verify; witness length stays one |
| G8 | pass | 140 key-invariance and 140 carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 10 characters, about 3 tokens, 1 atom, 21 intended operations |

The five failing attacks are largest-node outlier selection, a greedy determinant-diagonal approximation, 256 uniform restarts, the tempting value-one ansatz, and ordinary integer division applied to the reduced cross-ratio. Each recorded 0/8 successes.

## Oracle loop

| Preset | Seed | Model | Result | Reason |
|---|---:|---|---|---|
| easy | 749935283 | Gemini 3.8 Flash | failed | parsed wrong residue |
| easy | 1130716331 | GPT-5.6 Terra | solved | verified |
| easy | 1161719807 | Gemini 3.8 Flash | solved | verified |
| medium | 244570717 | Gemini 3.8 Flash | solved | verified |
| medium | 1351536178 | GPT-5.6 Terra | solved | verified |
| medium | 141987902 | GPT-5.6 Terra | solved | verified |
| hard | 1907623777 | GPT-5.6 Terra | failed | parsed wrong residue |
| hard | 1341074947 | Gemini 3.8 Flash | failed | empty provider-filtered response |
| hard | 1776203615 | Gemini 3.8 Flash | failed | parsed wrong residue |

The script-owned verdict is `hardened` at the named hard preset after two escalations. The empty hard response was HTTP-successful but had `finish_reason=content_filter`, zero reported tokens, and no parseable answer; the harness counts it as an unsolved length-limited response. The other two hard failures are substantive parsed residues rejected by exact verification.

## G9 arms

| Arm | Solved/attempts | Verdict |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened |
| placebo hint | 0/3 | hardened |

`hinted - placebo = 0.0`. The structural hint bought no observed solves: all three hinted replies contained parsed but incorrect residues. This suggests the named change of variables is relevant but exact finite-field execution remains a material part of the task. One bare and one placebo attempt were empty provider-filtered responses, so the small-sample comparison should not be over-interpreted.

## Use

```python
from gen_2603_09869 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=7, **DIFFICULTY["demo"])
question = render(inst)
answer = parse_answer("Reasoning... <answer>58</answer>")
assert verify(inst, answer) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 2603.09869 20 hard
```

## Caveats

This is a native algebraic family from the paper’s invariant machinery, but it is a structured Vandermonde subfamily and **not** a benchmark for recovering the hidden permutation in arbitrary LCE instances. With a CAS or a few lines of code it is easy; that is the reason for Track B. The measured reference time is machine-dependent, while the operation count is reproducible.

The G4 prior is uniform over every nonzero residue allowed by the statement. The inverse generator avoids `±1`, a fact not stated to the solver; conditioning on that hidden generator detail would change the exact probability negligibly from `1/(p-1)` to `1/(p-3)`. The density number establishes guess resistance, not reasoning difficulty.

The panel did not run a Gröbner-basis package, SAT encoding, or production CAS because dense exact elimination already solves 8/8 and is the honest reference algorithm for Track B. `canonical_key` handles arbitrary coordinate relabellings and all fractional-linear node changes using anchored cross-ratios; no unresolved family symmetry is known. The oracle evidence uses only the two vendors currently configured by `harden.py`, and two of the preserved bare/placebo calls were provider-filtered empties as disclosed above.
