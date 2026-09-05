# arXiv 2211.12813 — retained rejected generator

**Status: rejected, not shippable.**  The native generator and exact checker
work, but H fails: the paper's constructive product labeling is as cheap as the
intended shortcut.  G9 is also incomplete because the OpenRouter quota expired.

| profile field | value |
|---|---|
| Track | B candidate, rejected |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT-style distance labeling |
| Certificate | integer tuple (one color per vertex) |
| Intuition | decomposition into Cartesian factors and diagonal classes |
| Domain essentiality | native |
| Reduction | none |

## Problem and trust status

The source is Ali and Raja, [*On the expansion constant and distance constrained
colourings of hypergraphs*](https://arxiv.org/abs/2211.12813).  An instance is a
randomly relabeled Cartesian product of a complete hypergraph and an
`r`-uniform star-hypergraph, augmented by certificate-compatible 3-edges.  The
solver returns an L(2,1)-labeling: co-hyperedge vertices differ by at least two,
and graph-distance-two vertices differ by at least one.  Checking is exact and
quadratic/cubic in the displayed finite incidence data.

G and V are trustworthy: the CRT diagonal labeling is built first from Section
4, Theorem 4.2, carried through the vertex permutation, and checked directly.
The rejection concerns H.  Section 4, Definition 4.1 makes the product factors
visible through edge sizes; direct factor recovery and the theorem construct a
witness in incidence-linear time plus sorting.  Section 3.3 similarly gives
explicit easy formulas for star-hypergraphs and hyperpaths.  The paper provides
no hard random regime to support Track A.

| route at the hard preset | measured/required work |
|---|---:|
| direct factor recovery + theorem labeling (8 seeds) | 5,094--6,234 operations, mean 5,777.5 |
| direct method wall time | 0.00037--0.00047 s, mean 0.000423 s |
| supposed compact route | the same factor recovery + at most 180 CRT assignments |
| answer writing | 210--240 integers |

Because the mechanical and compact routes share the same dominant factor
recovery, this does not meet Track B's compression criterion.  A dense CSP
front end measured millions of operations, but it was unnecessary and has been
removed from the hardness claim.

## Worked demo

With `seed=0`, the demo has 18 vertices and color bound 11.  The full rendered
edge list is:

```text
e0: 0 12 16
e1: 16 3 15 14
e2: 11 0 17 1
e3: 13 8 1
e4: 9 6 12 10
e5: 4 5 17
e6: 11 2 7 0
e7: 7 6 15
e8: 9 11 14
e9: 3 2 10
e10: 13 4 16 14
e11: 8 5 12 9
```

One answer is `1,9,10,8,10,8,9,7,11,0,6,4,3,7,2,11,5,6`.
The checker returns `(True, "ok")`; dropping the last entry returns
`(False, "expected 18 entries, got 17")`.  A person can solve the demo by hand
after identifying the three-vertex row edges and four-vertex star edges.

## Difficulty presets

| preset | complete factor `n` | star order | petals | decoys | vertices | status |
|---|---:|---:|---:|---:|---:|---|
| demo | 3 | 6 | 2 | 0 | 18 | hand example |
| easy | 11 | 20--23 | >=7 | 8 | 220--253 | one oracle solved an earlier form |
| medium | 13 | 18--19 | >=7 | 10 | 234--247 | structural hint solved an earlier form |
| hard | 15 | 14--16 | >=6 | 12 | 210--240 | rejected on H, not oracle result |

The earlier `n=5` and `n=7` designs were discarded because 64-restart greedy
solved 7/8 and 6/8 instances respectively.  The retained hard distribution
defeats the four recorded heuristics but is still easy for direct factor
recovery.

## Gate results

| gate | result |
|---|---|
| G1 planted verifies | pass, 12/12 preset/seed checks |
| G2 corruption | pass, five corruptions and five distinct reasons |
| G3 round trip | pass |
| G4 random guess | pass, 0/200,000 under the declared bounded-vector prior |
| G5 density/baseline | pass locally; density 0/200,000, direct method solves 8/8 |
| G6 attacks | pass locally; all four heuristics 0/8, reference 8/8 |
| G7 scaling | pass; `n=30`, 630 vertices verifies |
| G8 canonical key | pass; 60/60 invariance and 20/20 distinct sampled keys |
| G9 no-tool suitability | **fail/pending**; oracle evidence incomplete |

## Oracle and G9 evidence

The files are retained for audit, but a final generator correction changed the
seeded decoy instances, so these runs are **not final hardness evidence**.

| arm | completed score | errors | interpretation |
|---|---:|---:|---|
| bare hard | 0/3 solved | 0 | historical pre-correction run |
| structural hint hard | 0/2 solved | 4 quota errors | incomplete; G9(b) not passed |
| placebo hard | 0/0 solved | 4 quota errors | no diagnostic estimate possible |

The historical bare models were Claude (empty at its 32k completion cap),
Gemini (invalid adjacent colors), and GPT-5.6-terra (invalid adjacent colors).
The hinted-minus-placebo difference is undefined, despite the report's numeric
placeholder 0.0, because the placebo denominator is zero.  No conclusion about
hint effectiveness is justified at hard.

## Reproducing the retained artifact

```python
import importlib.util
spec = importlib.util.spec_from_file_location("g", "rejected_gen_2211_12813.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
inst = g.make_instance(seed=7, **g.DIFFICULTY["demo"])
assert g.verify(inst, inst["answer"]) == (True, "ok")
```

This result must not be emitted as a shipping family.  For local inspection
only, after renaming the module back to `gen_2211_12813.py`, the ordinary command
would be `bash scripts/emit.sh 2211.12813 20 hard` from the repository root.

## Caveats

The random-guess estimate covers uniformly sampled bounded vectors conditioned
only on containing zero; it does not estimate a solver's structured posterior.
The canonical key uses strong incidence and edge-intersection multisets, not
complete hypergraph isomorphism, so rare collisions are possible.  No external
SAT/SMT or ILP package was run; direct paper-aware factor recovery is already
enough to reject H.  The 12 decoys are inverse-generated against two held
certificates and do not establish a hard distribution.  Finally, the answer is
near the 256-atom cap, so apparent no-tool difficulty is substantially
transcription workload—the central reason this candidate is rejected.
