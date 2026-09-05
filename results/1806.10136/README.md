# Verified generator for arXiv:1806.10136

## Profile

| field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | number theory |
| Object regime | integer lattice |
| Computational core | other (bounded ternary Diophantine search) |
| Certificate | integer tuple `[x1,x2,x3]` |
| Intuition | change of variables |
| Domain essentiality | native |
| Reduction | none |
| Shipping preset | **medium**: `n=40, core_bits=7` |

## The problem and why the checker is trustworthy

The source is Wu, Ni, and Pan, [*On the almost universality of
floor(x²/a)+floor(y²/b)+floor(z²/c)*](https://arxiv.org/abs/1806.10136).
An instance gives three positive denominators, a target, and an inclusive
interval for each coordinate.  The solver must return three pairwise-distinct
nonnegative integers in those intervals whose three exact floor-square terms
sum to the target.  These are the paper's native integer objects; no graph,
finite-field surrogate, or convenience reduction is used.

`verify` checks types, shape, distinctness, intervals, three integer squares,
three floor divisions, and exact equality.  It never reads `inst["answer"]` and
accepts any witness satisfying the displayed problem.  Generation knows a
witness before the target exists: equation (1.2) carries representations
through square factors, while an integer orthogonal transform of
`(t²-1, 2t, t²+1)` has squared norm `18(t²+1)²`.  A planted common residue adds
an exactly known linear correction.  This is inverse generation/composition of
identities, not a search over the completed instance.

## Why this is Track B

Section 1 defines the floor form.  Theorem 1.1 proves that `F_m` is almost
universal for every `m>=3`, and Corollary 1.1 uses equation (1.2) when the
denominators have a common squarefree part.  Section 2 and Lemma 2.2 obtain
eventual representation from local conditions and modular-form coefficient
bounds.  That proof is non-effective here: it says “sufficiently large” but
does not provide a threshold or an algorithm that outputs the three integers.

An executable algorithm nevertheless exists for this bounded distribution.
Take the common core `m`, strip the small square factors using equation (1.2),
and for every first coordinate run a monotone two-pointer search over the two
remaining floor-square values.  It uses `O(U²)` exact comparisons and `O(1)`
auxiliary memory, with `U=floor(sqrt(m(N+1)-1))`.  Across eight shipping
instances the saved selftest measured 8,362,194 exact operations, 1,672,391
pair comparisons, and 0.430 seconds total; the worst instance took 2,413,021
operations.  This algorithm solves 8/8, as Track B expects.

The compact route notices the common-core substitution and the orthogonal
Pythagorean identity, recovers its small residue from the target correction,
and evaluates the three coordinates.  It solved 8/8 in at most 112 counted
exact operations.  The benchmark tests finding that structure; it does not
claim computational hardness.  Section 1's already-universal small parameters
and its observation that larger denominators make floor-square values denser
identify easy regimes.  An earlier generator used large random square factors
and was discarded when residual greedy search solved 8/8.  Shipping uses only
the small factor patterns `(1,1,1)`, `(1,1,2)`, and `(1,2,3)`, and requires each
term to make a material contribution.

## Worked demo

The full `demo`, at seed 0, is:

```text
Find a bounded representation by a ternary floor-quadratic form.

For a real number q, floor(q) is the greatest integer not exceeding q.
Find three pairwise-distinct nonnegative integers x1, x2, x3 such that

  floor(x1^2/20) + floor(x2^2/5) + floor(x3^2/5) = 2178.

The coordinates are indexed from 1 and tied to the denominators in the
displayed order; coordinate order therefore matters. Repeats are forbidden.
All bounds are inclusive:
  38 <= x1 <= 198
  19 <= x2 <= 99
  19 <= x3 <= 99
Only exact integer arithmetic is intended; decimal approximations are not accepted.

Give your final answer inside <answer></answer> tags, as a JSON list
[x1,x2,x3] containing exactly three base-10 integers.
Example: <answer>[12,34,56]</answer>
Output nothing else inside the tags.
```

One answer is `<answer>[118,74,44]</answer>`:
`118²//20 + 74²//5 + 44²//5 = 696+1095+387 = 2178`, so `verify`
returns `(True, "ok")`.  Changing the first entry to 119 returns
`(False, "the exact floor sum does not equal the target")`.  A person can solve
this demo on paper by extracting the common core 5 and recognizing the small
`t=2` identity; its arithmetic is intentionally hand-scale.

## Difficulty presets

| preset | parameters | status |
|---|---|---|
| demo | `n=2, core_bits=3` | hand example; skipped by hardening |
| easy | `n=28, core_bits=6` | rejected by oracle loop: solved 2/3 |
| medium | `n=40, core_bits=7` | **ships; bare held 0/3** |
| hard | `n=56, core_bits=8` | available, not reached |

Both `n` and `core_bits` enlarge the bounded coordinate space while the
certificate remains three integers.  `escalate` raises the core size before
raising `n`; it does not lengthen the answer by adding coordinates.

## Gate results

| gate | saved measurement | result |
|---|---|---|
| G1 | 20 planted checks across every preset; JSON round-trip included | pass |
| G2 | five corruptions rejected with five distinct reasons | pass |
| G3 | tagged JSON recovered through prose and a Markdown fence | pass |
| G4 | 0 hits / 200,000 structure-aware samples; space 2,331,748,922,056,068,403 | pass |
| G5 | shipping reference: 564,131 ops, 112,820 comparisons, 0.028 s; demo has 446 answers | pass |
| G6 | four attacks each 0/8; reference and compact solvers each 8/8 | pass |
| G7 | doubled `n`: space grows from 2.33e18 to 2.76e20 and witness verifies | pass |
| G8 | 60 permutation-invariance/carry checks; 20/20 unrelated keys distinct | pass |
| G9 | 23 chars, 6 estimated tokens, 3 atoms, 112 intended operations | pass |

## Bare oracle loop

| preset | model | seed | solved | result |
|---|---|---:|---:|---|
| easy | Gemini 3.8 Flash | 861174035 | no | parsed tuple, wrong exact sum |
| easy | GPT-5.6 Terra | 1371489433 | yes | verified |
| easy | GPT-5.6 Terra | 1020254783 | yes | verified |
| medium | GPT-5.6 Terra | 2064220432 | no | parsed tuple, wrong exact sum |
| medium | Gemini 3.8 Flash | 1833620276 | no | parsed tuple, wrong exact sum |
| medium | GPT-5.6 Terra | 499943610 | no | parsed tuple, wrong exact sum |

The script-owned verdict is `hardened` at medium.  Every bare reply contained a
parseable answer; no hardness claim rests on a parser miss.

## G9 diagnostic arms

| arm | solved / attempts | interpretation |
|---|---:|---|
| bare | 0/3 | shipping evidence |
| structural hint | 1/3 | the named identity enabled one exact solution |
| placebo hint | 0/3 | prompt framing alone did not help |

`hinted - placebo = 1/3`.  This supports the declared “change of variables”
intuition: some difficulty lies in discovering the structure.  One hinted
Gemini call exhausted its 32,000-token completion budget and returned empty,
so the small-sample diagnostic is not a clean three-way comparison.  The
hinted arm is recorded, not gated.  The maximum answer observed over 64
shipping seeds was 26 characters (7 estimated tokens); the representative was
23 characters, and the compact route stayed at 112 operations.

## Use

```python
import gen_1806_10136 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=123, **params)
print(g.render(inst))
candidate = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
print(g.verify(inst, candidate))  # (True, "ok")
```

From the repository root, emit instances with:

```bash
bash scripts/emit.sh 1806.10136 20
```

## Caveats

- This is not a Track A or NP-hardness claim.  The reference algorithm is
  expected to solve every generated instance, and the planted identity is a
  short formula once recognized.
- The paper proves almost universality for unrestricted integral coordinates;
  this generator samples a structured subdistribution and adds explicit
  intervals plus pairwise distinctness.  It tests native exact representations,
  not the modular-form proof or arbitrary sufficiently large targets.
- The 0/200,000 density result concerns the uniform prior over triples already
  satisfying all visible shape, interval, and distinctness constraints.  It
  does not bound a solver's informed, identity-aware prior.
- The panel did not run an SMT solver, a CAS three-square routine, lattice
  reduction, or optimized modular sieves.  It did run the exact domain
  reference search and four construction-aware no-tool attacks.
- Canonicalization covers permutations of the three summands, the evident
  instance relabelling.  It does not attempt to identify unrelated equations
  connected by deeper Diophantine coincidences.
- `gvlib` is imported when present as required by the repository convention,
  but this family has a complete standard-library exact-arithmetic path.
