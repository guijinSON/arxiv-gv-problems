# Verified generator for arXiv:2309.11256

## What the family is

This module turns [Chen, Grigoriev, and Shpilrain, *Tropical cryptography III: digital signatures*](https://arxiv.org/abs/2309.11256) into a witness problem. The solver receives all coefficients of a formal one-variable tropical polynomial `C` and must return two prescribed-degree coefficient lists `A` and `B`. Their tropical product is min-plus convolution: `C[k] = min(A[i] + B[j])` over `i+j=k`. Checking a witness is exact integer work, takes quadratic time, and accepts any valid factor pair rather than only the planted one.

Generation is inverse: `A` and `B` are sampled first, with equal growing degree, zero endpoints, and i.i.d. internal coefficients from `[1,127]`; only then is `C` computed. Formal coefficient equality is essential—equality only as evaluated piecewise-linear functions is a different, easier notion.

## Why it is plausibly hard

The paper's §2.1 and §4.3 fix the formal definition and product, while §5 identifies recovery of `X,Y` from `M=X⊗Y` with factorization. The cited [Kim–Roush paper](https://arxiv.org/abs/math/0501167), Theorem 7, proves NP-completeness for growing degree in the equal-slope, equal-degree concave regime, even with public coefficients in `{0,1,2,3}`. Its Proposition 3 makes convex coefficient diagrams easy, and its algorithms section says fixed degree reduces to finitely many linear programs and gives an exponential branch-and-bound approach. This generator therefore grows the degree and forces the three zero-height vertices at degrees `0,n,2n`; positive internal factor coefficients avoid advertising extra zero vertices.

The signature paper's §4.1 explicitly says safe-key generation is unresolved. It recommends endpoint-zero factors to suppress low-degree factors; [Brown–Monico §3 and §5.2](https://eprint.iacr.org/2023/1837) likewise show that exact division is cheap *given a divisor* and that endpoint zeros defeat their small-degree enumeration attack. Worst-case NP-completeness does not establish average-case hardness for this planted distribution, so the local attacks and oracle loop below are necessary empirical evidence, not a proof.

## Worked smallest-preset example

This is the complete output of `render(make_instance(seed=0, **DIFFICULTY["easy"]))`.

```text
FORMAL TROPICAL POLYNOMIAL FACTORIZATION

A coefficient list A=[a_0,...,a_n] denotes a formal one-variable
polynomial.  Tropical multiplication of A and B=[b_0,...,b_n] is the
coefficient list C=[c_0,...,c_{2n}] defined exactly by

    c_k = min(a_i + b_j over all integers i,j with 0<=i,j<=n and i+j=k).

The plus sign inside that formula is ordinary integer addition.  Equality is
equality of every formal coefficient, not merely equality of the functions
obtained by evaluating the polynomials.

Here n=18.  Find two lists A and B, each containing exactly 19 ordinary
    integers.  Both lists must have endpoint coefficients zero,
a_0=a_18=b_0=b_18=0.  Every non-endpoint entry must lie in the inclusive
range [1,127].  A and B may be equal; no entries may be omitted;
repeated coefficient values are allowed.  The order of the two factors does
not matter, but the position within each list is its degree and is 0-indexed.
Their tropical product must equal the public C below at every degree.

Public coefficients, one line as "degree: coefficient":
0: 0
1: 46
2: 50
3: 96
4: 114
5: 28
6: 6
7: 18
8: 37
9: 18
10: 63
11: 13
12: 62
13: 24
14: 33
15: 24
16: 52
17: 19
18: 0
19: 46
20: 39
21: 67
22: 57
23: 28
24: 6
25: 18
26: 37
27: 18
28: 63
29: 13
30: 80
31: 95
32: 33
33: 39
34: 117
35: 62
36: 0

Give your final answer inside <answer></answer> tags as one JSON object with
exactly the keys "factor_a" and "factor_b", whose values are the two integer
lists in increasing degree order.
Example of the required shape (the values shown are only a format example):
<answer>{"factor_a":[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],"factor_b":[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]}</answer>
Output nothing else inside the tags.
```

One accepted answer is:

```text
<answer>{"factor_a":[0,109,50,98,114,54,6,34,124,66,63,52,118,101,107,39,124,62,0],"factor_b":[0,46,75,115,117,28,65,18,37,18,97,13,80,103,33,127,117,69,0]}</answer>
```

`verify(inst, answer)` returns `(True, "ok")`. Dropping the last entry of `factor_a` returns `(False, "factor_a must contain exactly 19 coefficients")`.

## Difficulty presets

| Preset | Factor degree `n` | Internal range | Status |
|---|---:|---:|---|
| `easy` | 18 | 1–127 | Rejected: two oracle vendors solved it |
| `medium` | 36 | 1–127 | **Ships; three deciding vendors did not solve** |
| `hard` | 72 | 1–127 | Local gates pass; not reached by the oracle loop |
| `paper` | 150 | 1–127 | Paper-recommended degree; local gates pass; not reached |

`SHIPPING_DIFFICULTY = "medium"`. Larger `n` adds factor variables and antidiagonal constraints while retaining the growing-degree regime; `escalate()` multiplies `n` by 1.5 up to 600.

## Gate results at shipping difficulty

| Gate | Measured result |
|---|---|
| G1 | 20/20 planted witnesses verified (5 seeds × 4 presets) |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | Tagged fenced JSON amid prose round-tripped; garbage returned `None` |
| G4 | 0/200,000 structure-aware random candidates verified; observed rate 0 |
| G5 | Enumerable case: 10/117,649 ordered candidates valid (`8.50e-5`) |
| G6 | Lower-envelope 0/8, greedy repair 0/8, 64-restart sampler 0/8 seeds solved |
| G7 | Doubled degree 72 built and planted witness verified; space increased |
| G8 | 60/60 key-invariance and 80/80 mapped-witness checks passed; 20/20 unrelated keys distinct |

G4's candidate prior already enforces endpoint zeros, every immediate public lower bound on each hidden coefficient, and the exact degree-1 and degree-`2n-1` minimum equations. The enormous `search_space()` value is only the naive ordered coefficient cube; G4, not that number, is the guess-resistance gate.

## Required oracle hardening loop

| Preset | Seed | Model | Result | Checker evidence |
|---|---:|---|---|---|
| easy | 563003122 | GPT-5.6 Terra | solved | `ok` |
| easy | 457600486 | Claude Sonnet 5 | solved | `ok` |
| easy | 1911209941 | Gemini 3.1 Pro Preview | failed | mismatch at degree 6 |
| medium | 1882492042 | Gemini 3.1 Pro Preview | failed | mismatch at degree 3 |
| medium | 1455936660 | Claude Sonnet 5 | failed | empty after consuming the 32k-token limit |
| medium | 483891241 | GPT-5.6 Terra | failed | mismatch at degree 6 |

Two Grok 4.6 transport calls (seeds 367359058 and 51772193) ended in `IncompleteRead`; the harness recorded and redrew them, so neither counted as a failure. Final verdict: `hardened`, one escalation, shipping preset `medium`. See `llm_loop_transcript.jsonl` and `.meta.json` for exact replies, timings, and schema fields.

## Use

```python
import random
import gen_2309_11256 as g

inst = g.make_instance(seed=2026, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
question = g.render(inst)
candidate = g.parse_answer(model_output)
ok, reason = g.verify(inst, candidate)
assert g.verify(inst, inst["answer"]) == (True, "ok")
probe = g.random_candidate(inst, random.Random(99))
```

From this result directory, emit 20 fresh shipping instances with:

```bash
bash ../../scripts/emit.sh 2309.11256 20 medium
```

Run all local gates with `python3 gen_2309_11256.py`.

## Caveats

- The NP-completeness theorem is worst-case and uses specially constructed low coefficients; no cited result proves these random planted instances average-case hard.
- The authors themselves say reliable safe-key generation needs more study. Internal positivity and endpoint zeros avoid known obvious geometry, but do not certify irreducibility or uniqueness. Multiple valid witnesses may exist, and the verifier deliberately accepts them.
- The 0/200,000 estimate applies only to the documented structure-aware independent prior. It does not bound a SAT/ILP encoding, full Kim–Roush branch-and-bound, exhaustive low-degree divisor search, advanced tropical division/residuation, or a learned attack. Those were not run.
- Only three clean oracle attempts decided `medium`, and one was a length-limited empty Claude response; the two returned candidate witnesses both failed exact multiplication. This is useful but small-sample evidence.
- `canonical_key` exactly handles input-term order and degree reversal, plus the factor-order witness symmetry in tests. No other nontrivial relabelling preserving the endpoint/range-constrained formal problem is known; its SHA-256 digest has the usual negligible theoretical collision risk.
