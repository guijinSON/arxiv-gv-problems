# Verified generator for arXiv:1612.00719

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | `number_theory` |
| Object regime | `integer_lattice` |
| Computational core | `subset_sum` |
| Certificate form | `integer_tuple` |
| Intended intuition | `invariant`: rearrangement fixes magnitudes; determinant signs recover signs through a hidden common linear map |
| Domain essentiality | `native` |
| Reduction | none |

## What the problem is, and whether to trust it

[Julia Brandes, *The Hasse principle for systems of quadratic and cubic diagonal equations*](https://arxiv.org/abs/1612.00719) studies integral solutions of
(sum_i c^{(2)}_{j,i}x_i^2=sum_i c^{(3)}_{h,i}x_i^3=0).
An instance here gives one quadratic and two cubic coefficient rows in the paper's
own integer-diagonal-form language. The solver returns a signed permutation of
`1,...,n` that zeros all three forms. The checker verifies the signed-permutation
grammar and substitutes with exact integers; it uses neither a solver nor the
stored answer.

The generator knows its witness before it builds any row. The quadratic row is an
equality case of the strict rearrangement inequality. For the cubics, integer
vectors are the directed edges of a strictly convex lattice polygon, so they
sum to zero; coordinate-dependent cube factors are cleared exactly, a common
invertible (2	imes2) integer map is applied, and the planted signs are carried
through using (s,s^3=1). The paper's highly nonsingular column conditions and
a rank-three Jacobian are checked exactly. This is inverse generation plus
composition of identities, not solution search.

Every deterministic gate passes. External oracle certification is **incomplete**:
OpenRouter returned HTTP 403 `Key limit exceeded (total limit)` before a model
answered in the bare, hinted, and placebo runs. The transcripts preserve these as
infrastructure errors, not model failures. Do not submit this directory as
oracle-hardened until those runs complete.

## Why it is Track B

Theorem 1.1 applies at (r_2=1,r_3=2,s=nge17), provided both coefficient
matrices are highly nonsingular. Section 4 explains the important limitation:
the asymptotic constant can vanish unless nonsingular real and (p)-adic points
exist. The planted rank-three integral point supplies such local points directly.
The theorem is an asymptotic counting result, not a computational-hardness claim
and not a certificate-finding algorithm.

An efficient mechanical method does exist for this generated subclass. Sorting
the quadratic coefficients recovers every magnitude. The remaining two equations
are a two-dimensional signed subset sum, solved by meet-in-the-middle in
(O(nlog n+2^{(n-1)/2})) time and (O(2^{(n-1)/2})) memory. On eight shipping
instances it solved 8/8, enumerating 2,097,152 states and performing 9,405,614
exact additions/subtractions in 3.292730 seconds.

The compressed route is 245 exact operations at (n=35). The quadratic
coefficients are an arithmetic progression in hidden rank. After ranks are
decoded, order cubic columns by magnitude and take determinants of consecutive
columns around the cycle. Each planted sign occurs twice in their product, so
the hidden common (2	imes2) map contributes only one global determinant sign;
(x_0>0) fixes the final global sign. Recognizing that invariant replaces more
than a million mechanical integer operations.

## Worked demo

The demo is deliberately patterned and has answer ([1,2,ldots,17]). A person
can solve it by recognizing the descending arithmetic progression in (Q) and
can check the cubics with the standard sums of cubes and fourth powers.

```text
Find a bounded nonzero integral solution of simultaneous diagonal equations.

Definitions and constraints.
There are 17 integer variables x_0,...,x_16; indices are 0-based.
Your answer must contain exactly 17 integers.
Their absolute values must be exactly 1,2,...,17, each used once.
Signs are free except that x_0 must be positive; this removes global sign ambiguity.
For a coefficient row a, its degree-d diagonal form is sum_i a_i*x_i^d.
All sums and powers are over the ordinary integers, with no modulus.
A valid answer makes the following one quadratic and two cubic forms exactly zero.

Quadratic row Q (degree 2):
21624 19839 18054 16269 14484 12699 10914 9129 7344 5559 3774 1989 204 -1581 -3366 -5151 -6936

Cubic row C1 (degree 3):
4913 4913 4913 4913 4913 4913 4913 4913 4913 4913 4913 4913 4913 4913 4913 4913 -18496

Cubic row C2 (degree 3):
4913 9826 14739 19652 24565 29478 34391 39304 44217 49130 54043 58956 63869 68782 73695 78608 -243848

Thus Q(x)=C1(x)=C2(x)=0 must hold exactly.
Order matters: entry j is x_j, and repeated absolute values are forbidden.

Give your final answer inside <answer></answer> tags, as a JSON-style list of integers.
Example: <answer>[1, -3, 2]</answer>
Output nothing else inside the tags.
```

Answer:

```text
<answer>[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]</answer>
```

`verify` returns `(True, "ok")`. Swapping the first two values returns
`(False, "quadratic residual is 5355, not zero")`. Brute force confirms that
this demo has exactly one answer in the structure-aware sign language.

## Difficulty presets

| preset | n | gap bits | transform bits | post-Q sign space | status |
|---|---:|---:|---:|---:|---|
| demo | 17 | 2 | 2 | (2^{16}) | hand-solvable patterned illustration; skipped by harden.py |
| easy | 25 | 10 | 10 | (2^{24}) | deterministic gates pass; bare oracle call blocked externally |
| medium | 31 | 16 | 16 | (2^{30}) | deterministic gates pass |
| hard | 35 | 22 | 22 | (2^{34}) | **shipping preset, pending oracle certification** |

`escalate()` first increases integer bit complexity without lengthening the
answer, then raises odd (n) while the 300-operation compact-route cap permits;
it returns `cap_bound` before that cap is exceeded.

## Gate results

| gate | measured result |
|---|---|
| G1 planted verifies | 16/16 across four presets and four seeds; 16/16 JSON round-trips |
| G2 corruptions | 5/5 rejected with five distinct reasons |
| G3 parser | recovered all 35 integers from prose and a fenced answer |
| G4 guessing | 0/200,000 structure-aware sign guesses; space (2^{34}=17,179,869,184) |
| G5 density + baseline | 0/200,000 at shipping; reference 8/8, 2,097,152 states, 9,405,614 operations, 3.292730 s |
| G6 adversaries | per-element 0/8; greedy 0/8; local restart 0/8; direct ansatz 0/8 |
| G7 scaling | (n=70) doubled instance builds and verifies; ladder spaces strictly increase |
| G8 canonical key | 60/60 invariance and 60/60 carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | compact decoder 20/20; 144 chars actual/166 worst, 35 atoms, 245 operations |

## Oracle loop and G9 diagnostics

The bare loop never completed a solver attempt:

| preset | seed | model | result |
|---|---:|---|---|
| easy | 1806180279 | google/gemini-3.8-flash | HTTP 403 infrastructure error |
| easy | 1720646383 | google/gemini-3.8-flash | HTTP 403 infrastructure error |
| easy | 1407724025 | google/gemini-3.8-flash | HTTP 403 infrastructure error |
| easy | 1008512871 | openai/gpt-5.6-terra | HTTP 403 infrastructure error |

| G9 arm | completed attempts | solved | errors | conclusion |
|---|---:|---:|---:|---|
| bare | 0 | 0 | 4 | unavailable |
| structural hint | 0 | 0 | 4 | unavailable |
| placebo hint | 0 | 0 | 4 | unavailable |

`hinted - placebo` is undefined. No conclusion about the hint's effect is
justified. The answer/effort gate passes independently: 42 worst-case estimated
tokens, 35 atomic entries, and 245 intended exact operations.

## How to use it

From the repository root:

```python
import importlib.util

path = "results/1612.00719/gen_1612_00719.py"
spec = importlib.util.spec_from_file_location("gen_1612_00719", path)
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=12345, **params)
assert gen.verify(inst, inst["answer"]) == (True, "ok")
```

```bash
python3 results/1612.00719/gen_1612_00719.py
bash scripts/emit.sh 1612.00719 20
```

The module is standard-library-only; `gvlib` is unnecessary for these integer
identities.

## Caveats

The paper does not study the signed-permutation promise or average-case
computational hardness. This benchmark keeps its native diagonal forms, but its
Track B difficulty comes from the generated subclass, not Theorem 1.1. A solver
with a sandbox can run the reference meet-in-the-middle algorithm in seconds,
and a solver that spots the determinant invariant has the intended short route.

The 0/200,000 guess figure conditions on the magnitude assignment already
deduced from (Q); it deliberately does not count the much larger, misleading
(n!) permutation space. It is an observed density, not a proof that no
additional sign solutions exist at shipping size. The exact demo count is one.

The four attacks are construction-aware but not exhaustive. No commercial
CP-SAT/SMT solver, Gröbner-basis engine, or lattice reduction package was run.
Canonicalization covers variable permutations, independent variable sign
changes, quadratic scaling/sign, and arbitrary invertible cubic row-basis
changes through exact determinant and cross-ratio invariants; it does not decide
every possible nonlinear equivalence of diagonal systems. Most importantly, the
required vendor-pool oracle evidence remains blocked by the account-wide
OpenRouter limit and must be rerun before the family can be called hardened.
