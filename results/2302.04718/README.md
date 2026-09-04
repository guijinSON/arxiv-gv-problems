# Projective-basis codeword coefficient recovery

| Profile | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | algebra |
| Object regime | finite field |
| Computational core | linear algebra |
| Certificate | integer tuple (indexed field coefficients) |
| Intuition | invariant: sum all evaluations to expose the common coefficient total |
| Domain essentiality | native; no reduction |

## The problem and why it is trustworthy

This family uses the projective geometric codes in Sam Adriaensen's [*A note on small weight codewords of projective geometric codes and on the smallest sets of even type*](https://arxiv.org/abs/2302.04718). Definitions 2.1 and 2.2 define the code as the span of characteristic functions of projective subspaces, equivalently the row space of their incidence matrix. An instance gives (n) points of a projective basis in (mathrm{PG}(n-1,p)), the (n) opposite hyperplanes, and a codeword's value at each basis point. The solver returns the coefficient of every hyperplane. The checker recomputes all values modulo (p), so it is exact and accepts every valid coefficient vector without consulting the planted answer.

Generation is inverse: the coefficients are sampled uniformly first, hyperplanes and points are independently reordered, and the values are then evaluated. For hyperplane (H_i) missing point (P_j), the displayed value is (b_j=S-x_i), where (S=sum_i x_i). Because (p\nmid n-1), the matrix is nonsingular and the witness is unique.

## Why Track B, not Track A

The certificate is produced mechanically by exact modular Gaussian elimination in (O(n^3)). At shipping (n=104), the measured generic implementation averaged **67,337 field operations, 95 inversions, and 0.001855 seconds**. This is fast software and therefore rules out Track A, but is far beyond unaided hand execution. The compact route recognizes the row/column permutation of (J-I): compute (S=(n-1)^{-1}sum_j b_j), then (x_i=S-b_j) at the unique point missed by (H_i). It takes exactly **208 field operations**; recognizing and accurately executing those 31-bit modular operations is the Track B test.

The paper's easier explicit families were deliberately avoided. Result 3.5 and Construction 3.6 construct minimum even sets for even (q); Theorem 1.1 and Corollary 3.17 classify/count the minimum dual words for (q=4,8) and place them in one automorphism orbit. Section 4 classifies small primal words. A shuffled word from those results would be a direct construction/lookup with no seed-level canonical diversity. This module instead uses the paper's native code definition and random codeword coefficients.

## Worked demo

For `make_instance(n=3, p=7, seed=3)`, the missed-point list is `[2,1,0]`, the point values are `[5,5,1]`, and the supplied inverse of (n-1) is 4. Thus (sum b_j=4), (S=4\cdot4=2\pmod 7), and the answer is:

```text
<answer>[[0,1],[1,4],[2,4]]</answer>
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping the last pair returns `(False, "wrong term count: expected 3, got 2")`. This demo is genuinely hand-solvable.

## Difficulty presets

| Preset | n | p | Status |
|---|---:|---:|---|
| demo | 3 | 7 | hand example; never shipped |
| easy | 96 | 2,147,483,647 | rejected by bare oracle: 1/3 solved |
| medium | 104 | 2,147,483,647 | **ships; bare 0/3 and hinted 0/3** |
| hard | 112 | 2,147,483,647 | reserved escalation rung; not needed |

## Gate results

| Gate | Result |
|---|---|
| G1 | 16/16 planted certificates verify |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | model-style tagged JSON round-trips; 4/4 garbage cases rejected |
| G4 | 0/200,000 uniform structure-aware guesses; language size (2147483647^{104}) (3,224 bits) |
| G5 | unique shipping solution; demo exact count 1; 256-restart baseline 0.005824 s |
| G6 | four attacks each 0/8; reference elimination 8/8 as expected |
| G7 | doubled (n=208) builds and verifies; candidate-space size doubles to 6,448 bits |
| G8 | 60/60 relabellings invariant and verified; 20/20 unrelated keys distinct |
| G9 | hinted remains hardened; answer 1,615 chars / 404 estimated tokens / 208 atomic integers; route 208 operations |

## Bare oracle loop

| Preset | Seed | Model | Result / exact reason |
|---|---:|---|---|
| easy | 592217679 | Claude Sonnet 5 | solved |
| easy | 909610927 | GPT-5.6 Terra | failed value check at `P_0` |
| easy | 1485876057 | Gemini 3.1 Pro | failed value check at `P_0` |
| medium | 1084460832 | Gemini 3.1 Pro | failed value check at `P_0` |
| medium | 1712827352 | Claude Sonnet 5 | failed value check at `P_0` |
| medium | 1981577663 | GPT-5.6 Terra | failed value check at `P_0` |

## G9 diagnostic

| Arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened — gated pass |
| placebo hint | 1/3 | diagnostic only |

Hinted minus placebo is **-0.333**. In this small sample, naming the invariant did not improve success; the transcripts suggest that exact arithmetic and complete output execution remain limiting after the structure is known. The two unparsed placebo failures were a length-truncated answer and a malformed coefficient, not parser misses.

## Use

```python
from gen_2302_04718 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=42, **DIFFICULTY["medium"])
prompt = render(inst)
candidate = parse_answer(model_reply)
ok, reason = verify(inst, candidate)
```

From the repository root, emit instances with `bash scripts/emit.sh 2302.04718`.

## Caveats

This is not an average-case or complexity-theoretic hardness claim: generic elimination solves it in milliseconds, and a solver with reliable big-integer arithmetic plus the displayed invariant should solve it. The zero-hit guess estimate is for the declared uniform prior on all (p^{104}) coefficient vectors; it says nothing about a solver using the equations. The attack panel covers a residue outlier, a zero-total greedy rule, random restarts, and a mode-based hand ansatz; it does not test every possible arithmetic transcription strategy. The instance is a projective-basis restriction of the paper's incidence code, not a benchmark of the paper's minimum-weight classification theorem. Canonicalization proves invariance under input reorderings; arbitrary projective coordinate changes are already absent from the containment-only representation.
