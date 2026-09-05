# Candidate generator for arXiv:2402.17528 — oracle evidence blocked

> **Status:** the module passes every local G1–G9(c) gate, but it is not a
> shippable result yet. The required bare hardening run obtained two countable
> failures at `easy`, then OpenRouter returned HTTP 403 “Key limit exceeded” on
> every redraw before the third attempt. There is no hardening verdict, and the
> hinted/placebo diagnostics consequently have not been run.

| Profile field | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain | algebra |
| Object regime | rational exact |
| Computational core | linear algebra |
| Certificate form | polynomial |
| Intended intuition | invariant |
| Domain essentiality | native |
| Reduction | none |

## Problem and trust basis

The module instantiates Greaves and Suda,
[*Constructions of t-designs from weighing matrices and association
schemes*](https://arxiv.org/abs/2402.17528). A solver receives an exact,
implicitly represented matrix

    B = d I + u D P C P^T D,

where `C` is the paper's Paley skew-conference matrix, `P` is a displayed
permutation, and `D` is a displayed diagonal sign matrix. The witness is the
coefficients of `x^(v-3)` and `x^(v-4)` in `det(xI-B)`, encoded as two
rational-coefficient monomials.

Generation is theorem-backed and transformational, not search-based. Section
1.4 fixes principal-submatrix notation; Lemma 1.6 connects characteristic
coefficients with sums of principal minors. Section 2.2 and Example 2.4 give
the Paley skew-conference construction and

    det(xI-C) = (x^2 + q)^((q+1)/2).

Signed simultaneous permutation preserves the characteristic polynomial;
scaling and shifting give

    det(xI-B) = ((x-d)^2 + q u^2)^((q+1)/2).

The generator expands only the two requested terms. `verify` does not read
`inst["answer"]`: it validates the entire instance grammar and independently
recomputes those exact integer coefficients from the factor above.

## Why Track B

Track A would be false. A generic trace/Newton algorithm computes these
coefficients in polynomial time. The reference implementation expands `B`,
computes the needed traces through degree four, and applies Newton identities;
at the candidate shipping preset `v=180` it succeeds 8/8 and performs exactly
11,825,836 counted scalar operations per instance. The latest local median
wall time was 8.819489 seconds (host-load dependent).

The compact route recognizes that `DP` is an orthogonal signed permutation,
uses the conference identity `C^2=-qI`, and expands two near-leading terms of
`((x-d)^2+qu^2)^(v/2)`. It uses 30 exact big-integer operations. The invariant
therefore compresses millions of mechanical operations to a short route,
although the seed-dependent arithmetic is still nontrivial without a
calculator.

The paper's easy case is explicit: Remark 2.6 says that a two-eigenvalue Seidel
matrix whose smaller eigenvalue multiplicity is one yields the trivial design
of all `k`-subsets. This family instead uses Paley skew-conference matrices with
both eigenvalue multiplicities equal to `v/2`.

## Worked demo

For `demo`, seed 0, `render` returns the following complete statement:

~~~text
Recover two exact coefficients of a transformed Paley conference matrix.

All indexing is 0-based. Let q=3, an odd prime congruent to 3 modulo 4, and
let v=q+1=4. The projective point set is {0,1,...,q-1,infinity}; in the
integer data below, the value q represents infinity.

For a nonzero finite residue z modulo q, its Legendre symbol chi(z) is +1 when
z is a square modulo q and -1 otherwise. Define the v by v skew matrix C,
whose rows and columns are indexed by the projective points, by

  C[r,r] = 0;
  C[infinity,s] = -1 and C[s,infinity] = +1 for finite s;
  C[r,s] = -chi(r-s) for distinct finite r,s (reduce r-s modulo q).

The displayed matrix B is specified without printing all v^2 entries. Put
d=1 and u=1. For displayed indices i,j, let
pi and eps be the following permutation and sign list:

pi  = [3,2,1,0]
eps = [1,1,1,1]

Then B[i,i]=d and, for i != j,

  B[i,j] = u * eps[i] * eps[j] * C[pi[i],pi[j]].

Let f(x)=det(x I_v-B), a monic polynomial over the integers. Return exactly
the terms of f at exponents v-3=1 and v-4=0, in that descending
order. A term is encoded as [[numerator,denominator],[exponent]]. Here both
denominators must be exactly 1. Do not include zero terms or any other terms.

For the bounded certificate language, the first numerator must lie in the
inclusive range -B3 <= value <= -1 with B3=24; the second must
lie in 0 <= value <= B4 with B4=16.

Give your final answer inside <answer></answer> tags, as a JSON list containing
exactly the two terms just defined.
Syntax-only example: <answer>[[[-1,1],[1]],[[1,1],[0]]]</answer>
(The illustrative numerators -1 and 1 are not the answer.)
Output nothing else inside the tags.
~~~

The hand calculation is `((x-1)^2+3)^2`, so the answer is
`<answer>[[[-16,1],[1]],[[16,1],[0]]]</answer>`.

~~~python
>>> verify(demo, [[[-16, 1], [1]], [[16, 1], [0]]])
(True, "ok")
>>> verify(demo, [[[-15, 1], [1]], [[16, 1], [0]]])
(False, "the x^(v-3) coefficient is incorrect")
~~~

This smallest setting is genuinely hand-solvable.

## Difficulty presets

| Preset | lower bound `n` | actual `q` | order `v` | coefficient bits | Status |
|---|---:|---:|---:|---:|---|
| demo | 3 | 3 | 4 | 1 | hand-scale |
| easy | 127 | 127 | 128 | 27 | two counted oracle failures; third attempt blocked |
| medium | 179 | 179 | 180 | 34 | candidate shipping rung; not oracle-tested |
| hard | 251 | 251 | 252 | 41 | available; not oracle-tested |

`escalate()` increases matrix order and coefficient entropy while keeping the
answer at two terms. It returns `cap_bound` only when the 2,000-character
answer limit would bind.

## Local gates

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 plants, JSON round-trips, and independent compact reconstructions |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged/fenced prose round-trips; garbage returns `None` |
| G4 | pass | 0/200,000 structured guesses; exact probability about 2.82e-87 |
| G5 | pass | one valid bounded answer; reference succeeds 8/8 with 11,825,836 operations and 8.819489 s median |
| G6 | pass | four non-reference attacks each 0/8; reference algorithm 8/8 as expected |
| G7 | pass | doubled order builds and verifies; cubic-work ratio 8.0 |
| G8 | pass | 60/60 invariant keys and carried witnesses; 20/20 unrelated keys distinct |
| G9(c) | pass | 115 characters, 29 estimated tokens, 6 atoms, 30 intended operations |

The four failed Track-B attacks are a diagonal-only estimate, a first-row
effective-root greedy estimate, 256 bounded random restarts, and the plausible
but wrong by-hand ansatz that omits the factor `q` in the conference identity.

## Oracle loop and G9 diagnostics

The current bare transcript is script-owned but incomplete:

| Preset | Model | Seed | Counted result | Reason |
|---|---|---:|---|---|
| easy | GPT-5.6 Terra | 1939039951 | failed | parsed polynomial; `x^(v-3)` coefficient wrong |
| easy | Gemini 3.8 Flash | 566635636 | failed | parsed polynomial; `x^(v-3)` coefficient wrong |
| easy | redraws | four seeds | excluded errors | HTTP 403 total key limit |

Because three countable attempts are required, 0/2 solves is not a hardening
verdict. The official G9 arms are likewise incomplete:

| Arm | Solved / attempts | Conclusion |
|---|---:|---|
| bare shipping arm | 0/0 | not run; bare ladder never reached shipping |
| structural hint | 0/0 | not run |
| placebo hint | 0/0 | not run |

`hinted - placebo` is undefined; the report stores zero only because neither
denominator exists. No conclusion about hint effectiveness is claimed. The
hinted and placebo transcript files are absent rather than fabricated.

## Use

~~~python
from gen_2402_17528 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["medium"])
print(render(inst))
candidate = parse_answer("<answer>...</answer>")
ok, reason = verify(inst, candidate)
~~~

After a funded OpenRouter credential is configured, resume with:

~~~bash
cd results/2402.17528
python3 ../../scripts/harden.py gen_2402_17528.py
~~~

Only after a hardened bare verdict and the two scratch-directory G9 runs may
the release be emitted from the repository root:

~~~bash
bash scripts/emit.sh 2402.17528 20 medium
~~~

## Caveats

- This is a Track-B compression benchmark, not a claim that characteristic
  polynomials are computationally hard. A CAS or the successful reference
  implementation solves it routinely.
- `P(random guess)` is uniform over the exact printed coefficient bounds after
  enforcing support, exponent order, denominators, and signs. It does not model
  a solver that recognizes the quadratic factor; such a solver succeeds
  deterministically.
- No optimized Berkowitz/modular characteristic-polynomial implementation or
  CAS was tested. The successful trace/Newton implementation is sufficient to
  establish tool-equipped tractability, but its Python wall time is host-load
  dependent.
- The canonical key is complete for displayed-index permutations and diagonal
  sign congruences. It deliberately treats all such displays with the same
  `q,d,u` as one problem.
- The earlier `VOIDED_REJECTION.md` describes a different incidence-count
  family that the oracle solved. It is historical evidence, not the disposition
  of this polynomial family.
- Most importantly, Step 4 and both G9 comparison arms remain incomplete because
  the external account limit prevented the harness from finishing.
