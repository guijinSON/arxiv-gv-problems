# Sparse root enumerators for ribbon tilings (arXiv:2408.09272)

> **Status: locally verified, but not shippable yet.** The bare oracle run reached
> medium and recorded two genuine failures, but the OpenRouter account then returned
> HTTP 403 `Key limit exceeded (total limit)` before the deciding third attempt.
> API errors are not model failures, so STEP 4 and the G9 arms remain incomplete.

## Profile

| field | value |
|---|---|
| track | **B — no-tool compression** |
| native domain | combinatorics |
| object regime | rational exact |
| computational core | polynomial identity |
| certificate | sparse Laurent polynomial |
| intended intuition | change of variables: take a first difference |
| domain essentiality | native |
| reduction | none |

## Problem and trust model

The source is Blackburn, Chen, and Kargin,
[*An upper bound on the per-tile entropy of ribbon tilings*](https://arxiv.org/abs/2408.09272).
Definition 1 says an `L`-ribbon contains one square at each of `L` consecutive
diagonal levels. If `sigma_l` counts region squares on level `l` and `tau_j`
counts ribbons rooted on level `j`, Section 2, Equation (2) gives

`sigma_l = tau_l + tau_(l-1) + ... + tau_(l-L+1)`.

An instance gives the nonzero `sigma_l` as exact constant runs and asks for the
sparse Laurent polynomial `Q(x)=sum tau_j*x^j`. The generator samples `Q` first
and constructs `S=(1+x+...+x^(L-1))Q` by endpoint events. This is inverse
generation, not solution of a generated instance. The histogram is realizable by
a finite region: use the requested number of mutually translated, disjoint
all-east ribbons at every root level. The checker multiplies the submitted `Q`
by the ribbon factor using integer events and compares every coefficient exactly;
it never reads `inst["answer"]`. Since Laurent-polynomial multiplication by a
nonzero polynomial is injective, every instance has exactly one accepted `Q`.

## Why Track B, not Track A

The paper does not support a Track-A distributional-hardness claim. Section 1
cites Sheffield's linear-in-area algorithm for simply connected ribbon regions
and says the existence complexity for general ribbon regions is open. The
NP-completeness result mentioned there is for 180-trominoes, not this enumerator
problem.

The disclosed mechanical algorithm is the dense recurrence derived from Equation
(2), `tau_l=sigma_l-sigma_(l-1)+tau_(l-L)`. It costs `O(D)` exact operations for
a displayed level span `D`; on the recorded hard instance it used **21,196,647
operations in 1.38 s**. Across eight hard seeds it used at least 20,794,476
operations and averaged 1.43 s, solving 8/8 as expected. The compact route notices
`(1-x)S=(1-x^L)Q`: constant runs collapse to endpoints, after which sparse division
uses **160** exact additions on the recorded instance. The 21-million-versus-160
gap is the Track-B claim. It is not a claim of computational intractability.

## Worked demo (`seed=3`)

The complete data are:

```text
L = 5
terms(Q) = 3
1 <= tau_j <= 3
root exponent range = [9,19]
level runs [first,last,sigma] = [[9,13,3],[14,18,1],[19,23,2]]
```

The exact rational-polynomial answer is:

```json
[[[3,1],[9]],[[1,1],[14]],[[2,1],[19]]]
```

`verify(inst, answer)` returns `(True, "ok")`. Changing the last coefficient
from 2 to 3 returns `(False, "polynomial identity does not match the level
counts")`. A person can solve this demo on paper: the three length-five blocks
are visible directly. Brute force finds one valid answer among the nine candidates
that already obey the forced outer terms and coefficient sum.

## Difficulty presets

| preset | ribbon length `L` | answer terms | residue chains | status |
|---|---:|---:|---:|---|
| demo | 5 | 3 | 1 | hand-solvable illustration |
| easy | 80,003 | 32 | 8 | solved by all 3 oracle attempts |
| medium | 400,009 | 40 | 10 | 2/2 completed attempts failed; third blocked |
| hard | 1,500,007 | 48 | 12 | provisional `SHIPPING_DIFFICULTY` |

After `hard`, `escalate()` keeps 48 answer terms while increasing `L`, the
coefficient range, and the number of interleaved residue chains (up to 16). It
returns `cap_bound` only when a conservative serialized-length bound exceeds
2,000 characters.

## Local gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted identities and JSON round trips |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged/fenced prose, raw JSON, and garbage cases |
| G4 | pass | 0/200,000; exact log10 density `-294.8033` under the informed prior |
| G5 | pass | one exact solution; 21,196,647 dense / 160 compact operations |
| G6 | pass locally | five attacks 0/8; every attack candidate obeyed the bounded language; reference recurrence 8/8 |
| G7 | pass | doubled `L=3,000,014` built and verified |
| G8 | pass | 80/80 invariant keys, 80/80 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | pass | 865 chars, about 217 tokens, 144 atoms, 160 operations |

The five G6 attacks are positive boundary events, largest event jumps, raw run
starts, naive endpoint pairing, and 256 random sparse restarts. Before grading,
each heuristic candidate is repaired to obey the forced endpoints, coefficient
sum, term count, exponent range, and coefficient bound.

## Oracle loop

| preset | model | seed | result | reason |
|---|---|---:|---|---|
| easy | GPT-5.6 Terra | 1,754,979,090 | solved | verified exact answer |
| easy | Gemini 3.8 Flash | 2,090,768,840 | solved | verified exact answer |
| easy | Gemini 3.8 Flash | 1,419,904,428 | solved | verified exact answer |
| medium | Gemini 3.8 Flash | 1,473,452,537 | failed | returned 39 rather than 40 terms |
| medium | GPT-5.6 Terra | 1,125,787,892 | failed | polynomial identity mismatch |
| medium | pool redraws | several | error | OpenRouter total key limit |

The script aborted without writing a `harden_verdict`; therefore neither medium
nor hard is certified as the shipping rung. The transcript is preserved because
it is real partial evidence, not a hardness verdict.

## G9 arms

| arm | solved / completed attempts | conclusion |
|---|---:|---|
| bare | 0 / 0 at provisional hard | unavailable; the bare ladder stopped earlier on API errors |
| structural hint | 0 / 0 | four HTTP 403 error records, no scored attempt |
| placebo hint | 0 / 0 | four HTTP 403 error records, no scored attempt |

Hinted-minus-placebo is undefined. The hint names only the finite-difference
invariant; it does not provide the subsequent division procedure. The required
`g9_*_transcript.jsonl` files contain the script-produced error records so the
infrastructure failure is auditable. G9(c) is unaffected and passes; the
three-arm diagnostic must be rerun after the key limit is restored.

## Use

```python
from gen_2408_09272 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=3, **DIFFICULTY["demo"])
print(render(inst))
candidate = parse_answer(
    '<answer>[[[3,1],[9]],[[1,1],[14]],[[2,1],[19]]]</answer>'
)
assert verify(inst, candidate) == (True, "ok")
```

After a successful bare and G9 rerun, emit from the repository root with:

```bash
scripts/emit.sh 2408.09272 20 hard
```

Do not emit the current provisional result as a shipped artifact.

## Caveats

- Sparse polynomial division solves every instance efficiently once the identity
  is recognized. This family measures no-tool compression, not complexity-theoretic
  hardness.
- The G4 prior is uniform over internal supports and bounded positive coefficient
  compositions after conditioning on the outer terms and total coefficient sum.
  Its tiny density measures blind guessing only; it says nothing about a solver
  that finds the first-difference invariant.
- The solver receives the level enumerator, not square coordinates. This object is
  native to Equation (2), but the family tests the paper's enumerator identity and
  not geometric placement of individual ribbons.
- SAT/SMT encodings, CAS sparse division, and learned pattern detectors were not
  tested. The successful dense recurrence is reported separately because Track B
  expects the reference algorithm to work.
- The oracle and G9 infrastructure evidence is incomplete. Local gates and the
  operation gap do not replace the missing scored calls.
