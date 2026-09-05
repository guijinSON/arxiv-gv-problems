# Matrices of nonnegative integer rank two — rejected candidate

| Profile field | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain / regime | geometry / integer lattice |
| Computational core | exact linear algebra in a planar cone |
| Certificate | matrix certificate: one split and two primitive generators |
| Intended intuition | hidden coordinate-swap symmetry |
| Domain essentiality | native; no reduction |
| Disposition | **rejected: fails Track B hardness** |

This directory records a rejected candidate family for [*Matrices of nonnegative integer rank two*](https://arxiv.org/abs/2602.05957), not a shippable generator.  The precise evidence and STEP 0 analysis are in [REJECTED.md](REJECTED.md).

## What was tested

The solver receives the native object of Problem 2.2: a pointed rational cone in a rank-two integer lattice and finitely many lattice points.  It must return two primitive lattice generators and a split of the minimum-slope point.  `verify` checks cone membership, primitive rays, and every semigroup coordinate using exact integer determinants and divisibility.

Instances are inverse-generated from a unimodular pair `a,b`.  Displayed points occur in pairs

```text
alpha*a + beta*b,    beta*a + alpha*b.
```

Pair centers vary, which defeats the raw coordinate-extrema shortcut.  The intended compact route is still to recognize that the two oriented-slope extremes form a swapped pair, primitive-normalize their sum and difference, and recover `a,b`.

## Why it was rejected

Algorithm 1 in Section 3 is the disclosed mechanical method.  At the named `hard` preset its exact implementation examined 7.08 million triangle splits and 142.2 million counted operations on average over eight seeds (4.01 s mean, 7.97 s maximum).  The symmetry route used 135 counted operations, so this was a plausible Track B family in principle.

It was not hard in practice.  The script-owned oracle run produced verified witnesses on 17/19 valid calls: 2/3 at `easy`, 3/3 at `medium`, 3/3 at `hard`, then 2/3, 3/3, and 3/3 on the next three fixed-answer-length escalations.  OpenRouter quota exhaustion interrupted the following rung after its first call also solved.  Errors are not counted as failures.  The repeated verified solutions, not the existence of the paper's algorithm and not the API errors, are the rejection reason.

## Local gate summary

| Gate | Result |
|---|---|
| G1--G3 | 16/16 planted witnesses verified; five corruptions rejected distinctly; tagged JSON round-tripped |
| G4 | 0/200,000 structure-aware random candidates verified at shipping size |
| G5 | reference Algorithm 1 solved 8/8; demo has 2 valid answers among 42 candidates |
| G6 | six cheap attacks each 0/8; reference algorithm reported separately as Track B requires |
| G7 | doubling `n` increased the split space and preserved the planted witness |
| G8 | 420/420 composed point-order and `GL(2,Z)` invariance/witness checks passed; 20/20 unrelated keys distinct |
| G9(c) | 58 characters, six atoms, about 15 tokens; 135 intended-route operations |

G and V pass.  H does not.

## Retained artifacts

- `rejected_gen_2602_05957.py`: the complete deterministic candidate implementation, retained for audit and possible future redesign.
- `selftest_report.json`: measurements from the last full local gate run.
- `llm_loop_transcript.jsonl`: script-owned oracle evidence, including the final quota errors.
- `g9_hinted_transcript.jsonl` and `g9_placebo_transcript.jsonl`: earlier script-owned error-only attempts; they do not support the rejection.

No `gen_2602_05957.py` is shipped.  Do not emit this family into the corpus.
