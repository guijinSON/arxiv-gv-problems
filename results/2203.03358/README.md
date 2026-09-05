# IC-WCOL(1) projective-holonomy generator

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate form | integer tuple (projective-labelled graph vertices) |
| Intuition | change of variables: parabolic holonomy on a unique cycle |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed, Section 3.1, Theorem 3.1 |

## What the problem is

This generator turns the paper [*Turbocharging Heuristics for Weak Coloring Numbers*](https://arxiv.org/abs/2203.03358) into certified yes-instances of **Incremental Conservative Weak 1-Coloring** (IC-WCOL(1)). The solver receives a succinctly specified graph `H`, a fixed partial ordering `L_S`, `r=1`, `k=2`, and must append `c` vertices while keeping every weakly reachable set of size at most two.

The base graph has one clique for each node of a unicyclic constraint graph. A base vertex `(i,t)` chooses a point `t` of the projective line over `F_p`; each constraint permits one Möbius-mapped partner and makes every other cross-pair adjacent. Theorem 3.1 replaces each base edge by the paper's `x,y1,y2` gadget. Its proof gives an exact equivalence: a valid appended subordering consists of an independent set in the base graph. `verify` checks that equivalence with modular integer arithmetic and never reads the planted answer.

## Why it is hard—and why this is Track B

This is not an average-case claim derived from the paper's worst-case theorem. Theorem 3.1 says IC-WCOL(r) is NP-hard and W[1]-hard in `k+c` for each fixed `r`, but that alone says nothing about this generated distribution. The Track B claim is narrower.

The mechanical algorithm enumerates all `p+1` choices at one group and propagates each through the constraint graph. It costs `O((p+1)(g+e))`; at the shipping preset the eight-seed run solved 8/8, averaging **346,247 exact projective transitions and 0.948 s** (maximum 514,668 transitions). The compact route composes the Möbius maps around the unique cycle, takes the repeated fixed point of the resulting parabolic map, and propagates it through the attached trees. The measured worst route used **220 exact operations**.

The easy regimes were explicitly avoided. Proposition 3.2 gives an XP algorithm for IC-WCOL with cost `O(|V\S|^c poly(|V|))`, so fixed `c` is polynomial. Theorem 3.3 makes the different WCOL-Merge problem FPT in `k+|S2|`; Section 4 also reports that successful practical reconstructions mostly have `c=1`. This generator declares Track B and uses neither of those facts as a hardness claim.

## Worked demo

The `demo` preset with seed 7 renders this complete instance:

```text
Incremental Conservative Weak 1-Coloring (IC-WCOL(1))

All arithmetic below is modulo the printed prime p.  The projective line
P^1(F_p) is encoded by the integers 0,...,p: 0,...,p-1 are the usual
field elements and the integer p denotes the point infinity.

For a nonsingular matrix P=[[a,b],[c,d]], define
  P(t)=(a*t+b)/(c*t+d) on P^1(F_p).
A zero denominator means infinity; P(infinity)=a/c, with c=0 giving
infinity.  P^{-1} uses [[d,-b],[-c,a]]; a nonzero scalar multiple
represents the same projective map.

p = 5
number of groups g = 4
The constraint graph on the groups is given by directed records
i j a b c d.  Such a record permits exactly the pairs (t_i,t_j)
satisfying t_j=M(t_i), where M=[[a,b],[c,d]].
Constraint records:
  3 1 2 2 1 3
  3 2 2 1 3 2
  2 0 0 2 2 2
  0 1 1 1 4 3

These data specify a base graph B.  Its vertices are all pairs (i,t)
with 0<=i<g and 0<=t<=p.  Distinct vertices in the same group are
adjacent.  Vertices in different groups are adjacent exactly when a
constraint record between their groups exists and their values do NOT
form its permitted pair.  Thus each constraint record describes all
incompatible cross-pairs, not just one edge.

Now construct the IC-WCOL graph H exactly as follows.  For every edge
{u,v} of B, replace it by u--x_{uv}--v and add
y1_{uv}--y2_{uv}--x_{uv}.  The fixed partial ordering L_S contains all
y1_{uv}, in lexicographic order of {u,v}.  All other vertices are free.
The radius is r=1, the bound is k=2, and c=4 vertices must be appended.

For a partial ordering, a vertex q is weakly 1-reachable from v when
q=v, or q is already ordered and the one-edge path q--v has no ordered
vertex before q.  The weak 1-coloring number is the maximum number of
weakly 1-reachable vertices over all vertices of H.  An extension is
extendable when this maximum is at most k.

Find an extendable right extension obtained by appending c vertices.
For this construction every valid extension necessarily appends exactly
one base vertex (i,t) from each group.  Give those g vertices; their order
inside the answer is irrelevant.  Repeated groups and repeated vertices
are forbidden.  Bounds are inclusive, and group indices are 0-based.

Give your final answer inside <answer></answer> tags, as one JSON list
of g pairs [i,t], with t=p representing infinity.
Example: <answer>[[0,3],[1,5],[2,0]]</answer>
Output nothing else inside the tags.
```

The answer is `[[0,2],[1,3],[2,2],[3,3]]`. The calls return:

```python
verify(inst, [[0,2],[1,3],[2,2],[3,3]])
# (True, "ok")
verify(inst, [[0,3],[1,3],[2,2],[3,3]])
# (False, "incompatible choices on constraint 2->0")
```

A person can solve this six-value-per-group demo on paper by testing a starting projective value or composing the four small matrices.

## Difficulty presets

| Preset | `n` | Actual prime `p` | Groups / answer vertices | Status |
|---|---:|---:|---:|---|
| demo | 5 | 5 | 4 | hand example; skipped by hardener |
| easy | 10,000 | 10,007 | 10 | oracle solved 1/3, so rejected as shipping rung |
| medium | 50,000 | 50,021 | 11 | **ships; held 0/3** |
| hard | 100,000 | 100,003 | 12 | local gates pass; not needed after medium held |

`escalate` raises the modulus while keeping the number of answer vertices fixed.

## Gate results

| Gate | Result |
|---|---|
| G1 | 16/16 planted and JSON-native checks passed |
| G2 | empty, drop, duplicate, changed value, and out-of-range corruptions rejected with five distinct reasons |
| G3 | tagged JSON recovered from prose and verified |
| G4 | 0/200,000 structure-aware guesses; space `(50022)^11` |
| G5 | shipping sample 0/200,000; exact constructed count 1; demo brute-force count 1; baseline 523,842 transitions / 1.449 s on the recorded seed |
| G6 | four attacks each 0/8; reference enumeration 8/8 as expected |
| G7 | doubling `n` raised the search-space bit length 172 to 183 with the same 22 answer atoms |
| G8 | 20/20 relabelling invariance and witness-preservation checks; 20 distinct canonical keys |
| G9 | 133 characters, about 34 tokens, 22 atoms, and at most 220 exact operations |

## Oracle hardening loop

| Preset | Model | Seed | Result | Recorded reason |
|---|---|---:|---|---|
| easy | OpenAI gpt-5.6-terra | 627681447 | solved | valid witness |
| easy | Google gemini-3.8-flash | 1783104074 | failed | length-limited empty reply |
| easy | Google gemini-3.8-flash | 1692790941 | failed | incompatible constraint |
| medium | OpenAI gpt-5.6-terra | 1924712983 | failed | asserted no solution; no tagged answer |
| medium | Google gemini-3.8-flash | 2059219498 | failed | incompatible constraint `9->7` |
| medium | Google gemini-3.8-flash | 739337420 | failed | incompatible constraint `0->8` |

The script-owned verdict is `hardened` at `medium` after one escalation.

## G9 diagnostic arms

| Arm | Solved / attempts |
|---|---:|
| bare | 0/3 |
| structural hint | 1/3 |
| placebo hint | 0/3 |

The hinted-minus-placebo rate is `+1/3`. Naming parabolic holonomy helped one run, which supports the claimed intuition, but two hinted runs still failed on the exact computation. This is diagnostic only. The answer and route remain within the 2,000-character, 256-atom, and 300-operation caps.

## Use

```python
from gen_2203_03358 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=123, **DIFFICULTY["medium"])
question = render(inst)
answer = parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert verify(inst, answer) == (True, "ok")
```

From the repository root, emit records with:

```bash
bash scripts/emit.sh 2203.03358 20 medium
```

## Caveats

- The compact holonomy solver makes the family easy with a CAS or a few lines of code. That is intentional and is why the family is Track B, not Track A.
- The graph is defined succinctly. At shipping it denotes 550,242 base vertices and roughly 123.9 billion IC-WCOL vertices; the paper's complexity results assume ordinary explicit graphs. The construction uses the paper's exact reduction, but the benchmark must not be cited as an explicit-graph runtime result.
- G4 samples the informed language “one projective value per group,” not arbitrary vertices of `H`. Its 0/200,000 observation is only an empirical upper signal; uniqueness follows separately from nonzero cycle holonomy.
- The canonical key uses the modulus and an exact unlabelled unicyclic topology code. It intentionally collapses different projective gauges on the same topology, because those are relabellings. Collisions are resampled rather than counted as diversity.
- I did not materialize the enormous graph for a generic ILP, SAT, or maximum-independent-set package. The exact reference enumeration and exact compact holonomy solver were both run; the four cheap no-tool attacks all failed.
- The family becomes easy as soon as the solver recognizes how to compose projective maps around the unique cycle. The bare oracle result tests discovery of that structure, not computational intractability.
