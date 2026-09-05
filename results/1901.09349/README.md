# Large Minors in Expanders — verified generator

| Profile field | Value |
|---|---|
| Track | **B** — an efficient mechanical method exists |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | integer tuple (ordered singleton branch sets) |
| Intended intuition | symmetry: detect the hidden two-sheet involution through 4-cycle incidence |
| Domain essentiality | native |
| Reduction | none |

## Problem and trust model

The module turns Chuzhoy and Nimavat's [*Large Minors in Expanders*](https://arxiv.org/abs/1901.09349) into a search problem on the paper's own objects.  The solver receives a finite simple target graph `H` and a connected regular host graph `G`, then returns an ordered injective vertex map whose singleton branch sets realize every edge of `H` in `G`.  This is a special, direct instance of the minor-model definition in Section 2: singleton branch sets are connected and every model path is one host edge.  `verify` checks ranges, injectivity, and all required adjacencies exactly; it never reads the planted answer.

Generation composes a known model.  Each decoy is sampled as a connected cubic girth-at-least-five graph, duplicated into a two-sheet prism, and given a vertical matching.  One quotient is selected uniformly and independently relabelled as `H`; its untouched sheet is the certificate.  A degree-preserving ring switch joins all prism blocks while retaining that sheet.  A final global relabelling hides all construction identifiers.  Target and decoy quotients use the same distribution.  The resulting host is connected and 4-regular, so the elementary bound `alpha = 2/|V(G)|` is guaranteed without solving a sparsest-cut instance.

## Why Track B

Step 0 rules out Track A.  Theorem 1.1 gives a randomized model-finding algorithm in time `poly(N) * (d/alpha)^O(log(d/alpha))` under its stated target-size bound; Theorem 1.2 gives a `poly(N,d/alpha)` algorithm under a slightly smaller bound.  The shipping parameters are not claimed to satisfy the paper's hidden universal constants, but this generated family has its own efficient recognizer: count 4-cycles per host edge, recover the two-sheet matching, recognize quotient candidates, and run exact fixed-size cubic graph isomorphism.  Its implementation is `O(M d^2 + q k!)` in the worst case, with fixed `k=14`; it solved 8/8 shipping instances at a measured mean of 20,968 counted operations and about 0.006 seconds (maximum 75,902 operations and about 0.019 seconds).

The compact route is to notice the same involution, compare the target's 21 edges against the four quotient candidates, and select one intact sheet: 112 counted branch/quotient checks at shipping size.  The no-tool difficulty is discovering and executing that compression from an unannotated 224-edge list.  This is deliberately not a claim that minor finding is hard on this distribution when code is available.

## Worked demo (`seed=0`)

The demo is hand-solvable: find a five-cycle in the 10-vertex prism and align it with the target five-cycle.  Its complete rendered instance is:

```text
Find a graph-minor model of H in G with the required branch-set shape.

All graphs here are finite, simple and undirected.  The target H has vertices 0 through 4.  The host G has vertices 0 through 9.  A branch set is a set of host vertices.  A model of H in G assigns one nonempty branch set B_i to every target vertex i such that branch sets are pairwise disjoint, each G[B_i] is connected, and for every target edge i-j there is a host edge with one endpoint in B_i and the other in B_j.  Extra host edges and unused host vertices are allowed.  A connecting host edge is a one-edge path, so these data are also a path model in the usual graph-minor definition.

For this problem every branch set must be a singleton.  Encode the model as [v_0,v_1,...], where B_i={v_i}.  Entries occur in target-label order, and no host vertex may repeat.  Indexing is zero-based.

The host is 3-regular, connected, and therefore is promised to be an alpha-expander for alpha=2/10: every nontrivial vertex cut has at least alpha times the smaller shore in crossing edges.

Complete target edge list (5 edges):
  0 1
  0 2
  1 4
  2 3
  3 4

Complete host edge list (15 edges):
  0 2
  0 3
  0 9
  1 5
  1 6
  1 9
  2 7
  2 8
  3 5
  3 7
  4 5
  4 6
  4 7
  6 8
  8 9

Give your final answer inside <answer></answer> tags, as one JSON array of exactly 5 distinct integer vertex identifiers in target-label order.
Example: <answer>[3,17,8]</answer>
Output nothing else inside the tags.
```

The planted answer is `<answer>[1,9,5,3,0]</answer>`.  `verify(inst, inst["answer"])` returns `(True, "ok")`; dropping the last entry returns `(False, "wrong branch-set count: expected 5, received 4")`.

## Difficulty

| Preset | Blocks `n` | Target vertices `k` | Host vertices | Host edges | Answer atoms | Status |
|---|---:|---:|---:|---:|---:|---|
| demo | 1 | 5 | 10 | 15 | 5 | hand example; skipped by hardening |
| easy | 4 | 14 | 112 | 224 | 14 | **ships; oracle 0/3** |
| medium | 7 | 14 | 196 | 392 | 14 | available, not needed |
| hard | 10 | 14 | 280 | 560 | 14 | available, not needed |

`n` grows only the decoy haystack after `easy`; the witness stays at 14 integers.  `escalate` adds two more blocks until the declared no-tool route budget is exhausted.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted certificates verified (4 presets × 3 seeds) |
| G2 | pass | drop, swap, duplicate, empty, and out-of-range corruptions all rejected with distinct reasons |
| G3 | pass | tagged JSON recovered through prose and a Markdown fence |
| G4 | pass | 0/200,000 uniform ordered injective maps; exact candidate space `P(112,14) = 20,945,473,673,717,965,747,415,040,000` |
| G5 | pass | shipping density 0/200,000; exact demo solution count 20; reference solved in 8,801 operations on the fixed baseline seed |
| G6 | pass | five attacks each 0/8; reference 8/8, mean 20,968 operations |
| G7 | pass | doubling blocks gives 224 host vertices while answer remains 14 atoms |
| G8 | pass | 20/20 relabellings invariant, 20/20 carried witnesses valid, 20/20 unrelated keys distinct |
| G9(c) | pass | 42 characters, about 11 tokens, 14 atoms, 112 intended operations |

## Bare oracle loop

| Preset | Model | Seed | Solved | Recorded reason |
|---|---|---:|---|---|
| easy | GPT-5.6 Terra | 2091893757 | no | parsed map missed target edge 1-9 |
| easy | Gemini 3.8 Flash | 505097723 | no | empty length-limited reply at the 32k budget |
| easy | Gemini 3.8 Flash | 900166622 | no | no tagged answer; transcript shows unfinished manual search |

The script-owned verdict is `hardened` at `easy` with zero escalations.

## G9 diagnostic arms

| Arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened |
| placebo hint | 0 / 3 | hardened |

`hinted − placebo = 0.0`.  Naming 4-cycle incidence did not measurably help this small pool, so the run does not isolate the claimed symmetry insight from the bookkeeping needed to extract a valid labelled copy.  This diagnostic does not gate shipping.  The answer is 42 characters/14 atoms and the intended route is 112 exact checks.

## Use

```python
from gen_1901_09349 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=7, **DIFFICULTY["easy"])
print(render(inst))
assert verify(inst, inst["answer"]) == (True, "ok")
```

From the repository root, emit examples with:

```bash
scripts/emit.sh 1901.09349 20 easy
```

## Caveats

The certified expansion parameter is only `2/N`, the generic lower bound from connectedness; this generator does not claim constant-expansion hosts or instantiate the hidden constants in Theorems 1.1/1.2.  Its two-sheet construction is a native minor problem, but it is not the paper's elaborate expander-routing construction.  The strongest executable reference is construction-aware and specialized; the full randomized algorithm from the paper, nauty/Traces, SAT/SMT, and ILP encodings were not run.

G4 samples uniformly from all ordered injective maps, incorporating every free syntactic and singleton-connectivity constraint.  Its 0/200,000 observation bounds only that prior; it is not an upper confidence bound for a solver using graph structure, and there are multiple valid sheet embeddings.  One bare oracle exhausted its 32k response budget, so the 0/3 evidence includes one resource-limited failure, although the other attempts either emitted a verifier-rejected map or visibly remained unfinished.  With code, the reference method makes these instances easy—as Track B explicitly promises.
