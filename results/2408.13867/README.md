# Four equal-sum/equal-product triples (arXiv:2408.13867)

Status: the generator and all local gates pass. The mandatory OpenRouter
hardening run and both G9 diagnostic arms were attempted with the provided key,
but every request returned HTTP 403 `Key limit exceeded (total limit)`. Those
script-written error records are preserved; they are not counted as model
failures, so this is **not yet a shippable hardness claim**.

| Profile field | Value |
|---|---|
| Track | **B** — no-tool compression; no Track A claim |
| Native domain | `number_theory` |
| Object regime | `integer_lattice` |
| Computational core | `other` (exact sum/product collision) |
| Certificate form | `integer_tuple` (four integer triples) |
| Intended intuition | `ansatz`: recognize Proposition 2.8's factor-incidence pattern |
| Domain essentiality | `native` |
| Reduction | none |

## Problem and trust model

[Youmbai, Shamsi Zargar, and Voznyy, *Partitions into Triples with Equal
Products and Families of Elliptic Curves*](https://arxiv.org/abs/2408.13867)
defines \(\mathcal S_\ell(M,N)\) in Problem 1.1 as \(\ell\) triples of
positive integers with one common sum and product. Proposition 2.8 gives the
paper's new two-parameter construction for \(\ell=4,n=1\).

The generator fixes `q=2`, chooses `s>=3`, evaluates that proposition, and
negates all twelve entries. This produces four positive triples because, after
writing `s=u+3`, the relevant quantities `t1`, `t2`, `-t3`, `-t4`, and `t5`
are polynomials in `u` with positive coefficients. Global negation preserves
equality of sums and equality of products. The witness is therefore known
before any decoy exists.

The solver receives positive integer triples and the proposition's labeled
factor multiset. Every plant and decoy is a three-block multiplicative
partition of that same multiset, so every row has the same product. It must
return four displayed rows with a common sum. `verify` checks shape,
positivity, normalization, distinctness, pool membership, sums, and products
with exact integers and never reads `inst["answer"]`.

## Why Track B

The paper supplies constructions and elliptic-curve rank bounds, not a
computational-hardness theorem, so Track A would be unsupported. The standard
algorithm here is expected-linear dictionary bucketing by exact row sum. On
eight shipping instances it solved 8/8 using 50,855 counted operations (6,356
per instance) in about 0.006 seconds.

The compact route is Proposition 2.8's four-by-three incidence ansatz. Once it
is recognized, the twelve entries require 40 integer multiplications and the
four sums require 8 additions: 48 exact operations. The intended gap is thus a
mechanical scan of 1,600 crowded rows versus recognizing one short structured
identity. Proposition 2.8 is also the easy regime: a solver that recalls or
reconstructs its incidence pattern immediately defeats the instance.

An earlier Section 2.2 version was discarded during this audit. A simple
construction-aware rule—start from the two largest labeled factors—recovered
its plant 8/8, and three valid scratch-oracle calls solved `easy` 3/3. The
present version uses Proposition 2.8 and makes all rows, not just the plant,
whole-factor partitions.

## Worked demo

`make_instance(n=10, s_min=3, s_max=3, seed=0)` renders the following complete
candidate list (the statement also gives the shared product and output rules):

```text
q=2, s=3, d=2, v=7, a=19, b=32, c=63, e=199, f=2011

0: 24, 48013, 15328839456
1: 448, 2729882, 14443002
2: 2166, 2432, 3353183631
3: 2166, 143678, 56758464
4: 2432, 25137, 288936458
5: 12736, 380079, 3648988
6: 76418, 477603, 483968
7: 76608, 458508, 502873
8: 152836, 159201, 725952
9: 153216, 158802, 725971
```

The answer is:

```json
[[76418, 477603, 483968], [76608, 458508, 502873], [152836, 159201, 725952], [153216, 158802, 725971]]
```

All four rows sum to `1,037,989`. `verify(inst, answer)` returns
`(True, "ok")`. Increasing the first `76418` to `76419` returns
`(False, "every submitted triple must occur in the candidate pool")`. A person
can solve the demo by adding ten rows; the arithmetic is somewhat tedious, but
the list is deliberately small enough to check on paper.

## Difficulty presets

| Preset | Rows `n` | `s` range | Status |
|---|---:|---:|---|
| demo | 10 | 3 | hand-checkable illustration |
| easy | 600 | 5–17 | local gates pass; oracle unavailable |
| medium | 1,000 | 11–31 | local gates pass |
| hard | 1,600 | 19–47 | configured shipping candidate; oracle unavailable |

`hard` is configured to ship. `escalate` increases the row pool and shifts and
widens the `s` range while keeping the answer at twelve integers. A doubled
`n=3200` instance builds and verifies.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 preset/seed witnesses verify and JSON-round-trip |
| G2 | pass | six corruptions rejected; five required cases have distinct reasons |
| G3 | pass | tagged prose and fenced JSON round-trip; garbage returns `None` |
| G4 | pass | 0/200,000 legal guesses; space `272,043,839,600` |
| G5 | pass | exactly 1 answer; exact density `3.6758781285779205e-12`; reference 50,855 operations/8 instances |
| G6 | pass | six attacks each 0/8; reference and compact routes each 8/8 as expected |
| G7 | pass | named sizes 10, 600, 1,000, 1,600; doubled size verifies |
| G8 | pass | 60/60 invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | sampled answer 225 chars/~57 tokens/12 atoms; worst case 270 chars/~68 tokens; 48 intended operations |

The strongest failing panel probe used the visible separation pattern of
`c,e,f` and 38,400 scored steps over eight instances. Other probes were median
magnitude, smallest row spread, the visible `a^2` incidence, 256 uniform legal
restarts, and a cyclic whole-factor ansatz. A separate 300-seed stress audit
found no deterministic-attack success and no non-unique instance.

## Oracle loop and G9 arms

| Arm | Preset reached | Valid solved/attempts | Script result |
|---|---|---:|---|
| bare | easy | 0/0 | four HTTP 403 errors; no verdict |
| structural hint | hard | 0/0 | four HTTP 403 errors; diagnostic unavailable |
| placebo hint | hard | 0/0 | four HTTP 403 errors; diagnostic unavailable |

Because no request became a valid attempt, `hinted - placebo` is undefined;
the machine-readable placeholder is `0.0` and `hinted_verdict` is `not_run`.
No conclusion about the `ansatz` hint is justified. The answer-size and route
caps do pass independently: the exhaustive shipping-range worst case is 270
characters, about 68 tokens, 12 atomic integers, and 48 arithmetic operations.

## Use

```python
import json
import gen_2408_13867 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY["hard"])
prompt = g.render(inst)
wire = "<answer>" + json.dumps(inst["answer"]) + "</answer>"
candidate = g.parse_answer(wire)
assert g.verify(inst, candidate) == (True, "ok")
assert g.search_space(inst) == 272_043_839_600
```

After a genuine `hardened` verdict, emit from the repository root with:

```bash
scripts/emit.sh 2408.13867 20 hard
```

Do not emit this result yet. Increase or replace `OPENROUTER_API_KEY`, rerun the
bare loop and both isolated G9 arms, copy the two diagnostic transcripts back,
update `G9_ORACLE_RESULTS`, rerun `selftest()`, and refresh this page.

The module is standard-library-only. It does not need `gvlib` because every
object and every verification operation is integral.

## Caveats

- This is deliberately not a complexity-hard family. Exact sum hashing solves
  it in expected linear time, and the paper gives the compact construction.
- G4 samples uniformly from all four-row subsets after enforcing every stated
  shape, membership, distinctness, ordering, and common-product constraint. Its
  tiny density rules out blind guessing under that prior; it says nothing about
  sum hashing or successful recognition of Proposition 2.8.
- The 1,600-row hard prompt is about 112,000 characters for one measured seed.
  A bare-model failure could partly reflect list-reading burden. The unavailable
  hinted/placebo comparison is important for separating that from failure to
  find the incidence ansatz.
- Plants and decoys inhabit the same thirteen-factor partition universe, and
  the listed incidence and magnitude probes fail. A learned construction
  classifier, symbolic recovery of Proposition 2.8, and more elaborate combined
  incidence filters were not tested.
- `canonical_key` is exact for candidate-row reorderings and independent
  coordinate permutations, but it does not identify unrelated parameter values
  that might accidentally induce isomorphic numerical data.
- Most importantly, local gates do not establish no-tool hardness. The required
  multi-vendor evidence is absent because the external key limit blocked every
  scored call.
