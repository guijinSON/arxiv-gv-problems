# Inverse-adjoint certificates for formal duality

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| native domain | algebra |
| object regime | finite field |
| computational core | linear algebra |
| certificate form | matrix certificate |
| intended intuition | change of variables — recognize an identity-plus-rank-one automorphism and transport the dual through its inverse adjoint |
| domain essentiality | licensed reduction |
| reduction | paper-licensed — Section 2, Proposition 2.16, with Proposition 2.13(3) and Section 3, Proposition 3.2 |

This generator is based on Li, Pott, and Schüler,
[“Formal Duality in Finite Abelian Groups”](https://arxiv.org/abs/1804.06328).
It hands the solver a linear automorphism of an elementary abelian group and a
symbolically specified, known formally dual pair. The solver must return a
normalized rank-one factorization of the automorphism's inverse adjoint, which
parametrizes the transported dual set. The checker expands that factorization
and checks `B*A^T = I` using exact arithmetic modulo the displayed prime.
This is a representational reduction explicitly licensed by Proposition 2.16,
not a claim of irreducible native formal-duality search coverage.

Trust status: every local gate G1–G9(c) passes. The script-owned bare loop
reached `hard`, where all three scored attempts failed, and recorded a
`hardened` verdict. The isolated structural-hint and placebo arms also each
record three scored failures. `selftest_report.json` therefore records
`oracle_evidence_complete: true`.

## Family and construction

Definition 2.15 gives the finite-group pairing and its adjoint. Proposition
2.13(3) gives the parabola pair
`S={(x,x^2)}` and `T={(x^2,x)}` over `F_p^2`; Proposition 3.2 composes copies
of it. Most importantly, Proposition 2.16 says that applying an automorphism
`A` to `S` transports `T` by `(A^T)^(-1)`.

Generation samples nonzero vectors `u,v` and first builds
`A = I + u*v^T`, forcing `1+v^T*u != 0`. It simultaneously carries the
certificate

```text
(A^T)^(-1) = I - v*u^T / (1 + u^T*v).
```

The answer stores the rank-one correction as `alpha`, `left`, and `right`,
normalized by `left[0]=1` and `right[0]=A[0][0]-1`. Thus generation knows the
witness from the sampled factors; it never inverts the emitted matrix.

## Why Track B

This distribution is efficiently solvable and makes no Track A or average-case
hardness claim. The automatic reference algorithm subtracts the identity,
checks every `2x2` rank-one minor against one pivot, and applies the
Sherman–Morrison identity. Its complexity is `O(n^2)`; at hard it succeeds 8/8
and averages 24,484 exact field operations and about 0.002 seconds.

The compact route notices rank one without validating all `n^2` entries. The
first row, first column, and diagonal determine the normalized factors and the
trace correction. At shipping size this costs 272 field operations, under the
300-operation cap but impractical to reproduce by generic elimination in the
no-tool setting. Proposition 2.16 itself is the easy-case result that rules out
Track A: once the automorphism and adjoint relation are recognized, the
certificate is an exact linear-algebra computation. Appendix A's exhaustive
classification only covers groups through order 63 and is not being used as a
hardness claim here.

## Worked demo

For `make_instance(n=2, p=11, seed=0)`, the rendered matrix is

```text
BEGIN_MATRIX
8 5
7 6
END_MATRIX
```

The nonidentity part is `[[7,5],[7,5]]`. Its trace is `1 mod 11`, and the
normalized certificate is

```text
<answer>{"alpha":5,"left":[1,7],"right":[7,7]}</answer>
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Replacing `alpha` by
`11` returns `(False, "alpha is outside the nonzero range 1..10")`. This demo
is genuinely hand-scale: one modular inverse and a `2x2` identity check suffice.

## Difficulty presets

| preset | dimension `n` | prime `p` | rendered chars (seed 0) | answer atoms | compact operations | status |
|---|---:|---:|---:|---:|---:|---|
| demo | 2 | 11 | 1,867 | 5 | 8 | hand example; skipped by hardening |
| easy | 24 | 101 | 3,650 | 49 | 74 | solved 3/3; rejected as too easy |
| medium | 54 | 503 | 13,141 | 109 | 164 | solved 1/3; rejected as too easy |
| hard | 90 | 997 | 33,749 | 181 | 272 | **ships**; held 0/3 |

After `hard`, `escalate()` raises the prime at fixed dimension and fixed atom
count. It therefore grows coefficient entropy rather than lengthening the
witness; it returns `cap_bound` once further prime growth would exhaust the
serialized-answer allowance.

## Gate results

| gate | measured result |
|---|---|
| G1 | 16/16 planted witnesses verified; 16/16 JSON round-trips |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | 3/3 tagged model-style answers parsed; garbage rejected |
| G4 | 0/200,000 normalized structure-aware guesses; normalization makes the sole valid answer exactly 1 out of the reported search space |
| G5 | shipping density 0/200,000; demo exact enumeration found 1 valid answer among 1,000; reference cost 24,484 operations / 0.002078 s in the final self-test run |
| G6 | top-left outlier, greedy transpose, 256 restarts, and first-order Neumann attacks all 0/8; reference solver 8/8 as expected |
| G7 | doubled dimension 180 verifies; fixed-length escalation to `p=10007` verifies |
| G8 | 20/20 composed invariance tests, 20/20 carried witnesses, and 20/20 unrelated keys distinct |
| G9(c) | worst-case 750 chars, 188 conservative tokens, 181 atoms, and 272 operations; all within cap |

Full measurements are in [`selftest_report.json`](selftest_report.json).

## Oracle loop

The script-owned bare transcript is preserved in
[`llm_loop_transcript.jsonl`](llm_loop_transcript.jsonl). The currently
configured pool contains OpenAI GPT-5.6 Terra and Google Gemini 3.8 Flash; the
harness redraws between them with a fresh seed. Easy and medium were defeated,
while hard held across three scored attempts and two vendors.

| preset | model | seed | result | why |
|---|---|---:|---|---|
| easy | Gemini 3.8 Flash | 1844438446 | solved | valid certificate |
| easy | GPT-5.6 Terra | 441457336 | failed | inverse identity failed |
| easy | Gemini 3.8 Flash | 1453035296 | solved | valid certificate |
| medium | GPT-5.6 Terra | 891013265 | solved | valid certificate |
| medium | Gemini 3.8 Flash | 2056083140 | solved | valid certificate |
| medium | GPT-5.6 Terra | 577070028 | failed | inverse identity failed |
| hard | GPT-5.6 Terra | 1039774477 | failed | inverse identity failed |
| hard | Gemini 3.8 Flash | 1890695765 | failed | reasoning exhausted the response budget without an answer |
| hard | Gemini 3.8 Flash | 1464781918 | failed | inverse identity failed |

## G9 arms

| arm | completed solved / attempts | error retries | conclusion |
|---|---:|---:|---|
| bare | 0 / 3 | 0 | shipping level held |
| structural hint | 0 / 3 | 0 | naming rank one did not produce a valid witness |
| placebo hint | 0 / 3 | 0 | matched the hinted arm |

The hinted-minus-placebo success-rate difference is `0.0`. On this sample, the
structural sentence bought no measurable improvement over a same-register
placebo; recognizing rank one alone did not remove the exact arithmetic and
output burden. The scratch outputs are preserved as
[`g9_hinted_transcript.jsonl`](g9_hinted_transcript.jsonl) and
[`g9_placebo_transcript.jsonl`](g9_placebo_transcript.jsonl). The worst-case
answer is 750 characters, 188 conservative tokens, and 181 atomic elements;
the intended route is 272 exact field operations.

## Use

The module is standard-library-only; its exact finite-field operations do not
need the optional `gvlib` helpers.

```python
from gen_1804_06328 import (DIFFICULTY, SHIPPING_DIFFICULTY,
                            make_instance, parse_answer, render, verify)

params = DIFFICULTY[SHIPPING_DIFFICULTY]
inst = make_instance(seed=12345, **params)
question = render(inst)
candidate = parse_answer(model_output)
ok, reason = verify(inst, candidate)
```

Emit from the repository root with:

```bash
bash scripts/emit.sh 1804.06328 20 hard
```

## Caveats

- This is deliberately Track B. A computer recognizes and solves every
  generated instance in milliseconds; the benchmark tests recognition and
  unaided execution of the compact rank-one route, not computational hardness.
- `0/200,000` is a sampled rate under the exact declared prior: all entries are
  nonzero and both normalizations are enforced. It is not a confidence bound
  under a learned solver prior. The normalized valid certificate is unique.
- The hard prompt contains a dense `90x90` matrix. Some model failure may reflect
  navigation through 8,100 residues as well as failure to recognize the change
  of variables, even though the answer and intended arithmetic fit G9(c).
- The checker verifies the candidate-dependent claim—the exact inverse-adjoint
  identity—rather than enumerating the astronomically large formal-dual subsets.
  The base pair and the implication from that identity are the theorem-backed
  part of Propositions 2.13, 3.2, and 2.16.
- The adversary panel does not include a CAS, generic Gaussian elimination, or
  a dense matrix-inversion package. The stronger construction-aware automatic
  method is included separately as the successful Track B reference algorithm.
- `canonical_key` is complete under similarity for these nonzero-trace rank-one
  updates and is invariant under transpose. It is not a canonicalizer for
  arbitrary matrices outside this generated family.
- The current hardening harness uses the two-vendor pool recorded in `.meta.json`,
  not the older four-vendor pool described by the original task text. Hard held
  under that actual configured pool; this README does not extrapolate beyond it.
