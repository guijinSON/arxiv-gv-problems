# Balanced spanning `K_{2,3}` induced-minor models

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate | complete five-set induced-minor model (encoded by integer vertex sets) |
| Intuition | duality: suppress subdivisions and recognize the balanced three-edge cut |
| Domain essentiality | native; no reduction |

This generator turns [Bousquet et al., *Induced Minor Models. I. Structural Properties and Algorithmic Consequences* (arXiv:2402.08332)](https://arxiv.org/abs/2402.08332) into a witness problem.  The solver receives a finite simple graph as a complete subdivision table and must return five branch sets forming a **spanning** induced-minor model of `K_{2,3}`.  Verification is cheap and exact: it checks a vertex partition, induced connectivity, and the six required (and only those six) adjacencies between branch sets.  `verify` never reads the planted answer.

## Why the instance is trustworthy

The certificate is known by inverse construction.  Start with a regular graph, delete one vertex, repair all but three resulting ports, duplicate the fragment, and join corresponding ports with three edges.  Subdivide every edge and randomly relabel every vertex.  Deleting the three remembered join-edge subdivisions leaves the two connected copies; these are the two large branch sets, and the deleted vertices are the three singleton branch sets.  Generation therefore does not solve its own output.

This must be Track B.  Section 2.2 fixes the branch-set definition.  Corollary 5.4 explicitly gives a polynomial-time finding algorithm for every `K_{2,q}`, so a Track A claim for `K_{2,3}` would be false.  Section 6 gives a second route: Theorem 6.2 characterizes containment through long prisms, pyramids, thetas, and broken wheels; Theorem 6.10 detects `K_{2,3}` in `O(N^13(N+M))`; Lemma 3.2 converts decision into finding.

On this generated specialization a stronger reference method exists: suppress every degree-two vertex and run exact Stoer–Wagner global minimum cut on the regular core.  At the shipping preset it solved 8/8, with median 6,700 counted operations and 0.00081 seconds (`O(c^3)` for `c=30` core vertices).  The intended compact route recognizes the duplicated-half involution and its unique three-edge cut, then reads the corresponding three subdivision rows and components; the measured bound is 192 exact graph operations.  This gap—not complexity-theoretic hardness—is the Track B claim.

## Worked demo (`seed=0`)

The complete rendered demo is small enough to solve on paper:

```text
Find a balanced spanning induced-minor model of K_{2,3} in the finite simple undirected graph below.

Definitions.  K_{2,3} has two nonadjacent vertices U,V and three nonadjacent vertices A,B,C; every one of U,V is adjacent to every one of A,B,C.  An induced-minor model assigns a nonempty branch set of graph vertices to each target vertex so that branch sets are pairwise disjoint, each branch set induces a connected subgraph, and two branch sets have at least one edge between them if and only if their target vertices are adjacent.

This instance has 15 vertices, numbered 0 through 14.  It is the full subdivision of a 3-regular graph.  The core vertices are:
  0 1 9 11 12 14

Every other vertex has degree two.  The complete edge set is encoded by the following subdivision table.  A row "s: x y" means that edges s-x and s-y exist.  There are no other edges.
  2: 9 14
  3: 9 12
  4: 1 14
  5: 11 14
  6: 0 12
  7: 1 12
  8: 0 1
  10: 9 11
  13: 0 11

Your certificate must be [BU,BV,BA,BB,BC], a JSON array of five branch sets.  Every branch set is a JSON array of strictly increasing, unrepeated integer vertex identifiers.  The five sets must partition all graph vertices.  BU and BV must each contain exactly 6 vertices; BA, BB, and BC must each contain exactly one degree-two vertex.  For a canonical output, require min(BU) < min(BV) and the sole vertices of BA,BB,BC to increase in that order.  The induced-minor adjacency rule above must hold exactly.  Vertex indexing is zero-based.

Give your final answer inside <answer></answer> tags, as one nested JSON array in the exact [BU,BV,BA,BB,BC] format.
Example: <answer>[[0,2],[1,3],[4],[5],[6]]</answer>
Output nothing else inside the tags.
```

The answer is `[[0,1,6,7,8,12],[2,5,9,10,11,14],[3],[4],[13]]`.
`verify` returns `(True, "ok")`.  Removing vertex `12` from the first branch set returns `(False, "the five branch sets must partition every graph vertex")`.  A person can solve this demo: the suppressed core is two triangles joined by the rows `3`, `4`, and `13`.

## Difficulty presets

| preset | subdivision candidates `n` | core degree | graph vertices | answer atoms | structure-aware space |
|---|---:|---:|---:|---:|---:|
| demo | 9 | 3 | 15 | 15 | 38,808 |
| **easy (local-gate preset)** | 75 | 5 | 105 | 105 | 13,491,793,962,438,459,561,730,482,384,281,400 |
| medium | 105 | 5 | 147 | 147 | 138,740,364,344,604,729,588,120,457,613,583,047,743,736,853,000 |
| hard | 115 | 5 | 161 | 161 | 2,858,666,891,703,151,199,990,398,120,156,456,715,656,590,541,926,000 |

No preset was rejected by a local gate.  `SHIPPING_DIFFICULTY` remains `easy` as the measured local-gate preset, but **no preset ships**: the oracle solved every writable rung and the harness returned `cap_bound` after `hard`.

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 16/16 planted models; 1,712 degree identities |
| G2 | pass | six corruptions rejected with six distinct reasons |
| G3 | pass | full nested JSON answer recovered from prose and a Markdown fence |
| G4 | pass | 0/200,000 shape-aware random candidates verified |
| G5 | pass | shipping density 0/200,000; demo exact count 1/38,808; reference 6,687 ops |
| G6 | pass | five attacks at 0/8 each; exact min-cut reference at 8/8 |
| G7 | pass | `n=155` / 217-vertex doubled-size instance builds and verifies |
| G8 | pass | 60/60 relabellings invariant; 60/60 carried models; 20/20 unrelated keys distinct |
| G9(c) | pass | 425 chars, 107 estimated tokens, 105 atoms, 192 operations |

## Oracle hardening and G9 diagnostics

The required bare loop defeated every named rung and returned **`cap_bound`**.  This result is parked, not rejected and not claimed hardened.  The next monotone setting (`n=125`, degree 5) still has a writable 175-atom, 775-character answer, but its measured intended route is 312 operations, over G9(c)'s 300-operation limit; thus the binding cap is effort rather than serialization size.

| preset | seed | model | solved | why |
|---|---:|---|---|---|
| easy | 1621441287 | GPT-5.6 Terra | yes | returned a verified model |
| easy | 134897055 | Gemini 3.8 Flash | yes | returned a verified model |
| easy | 462416804 | Gemini 3.8 Flash | yes | returned a verified model |
| medium | 22535283 | Gemini 3.8 Flash | yes | returned a verified model |
| medium | 1391934904 | GPT-5.6 Terra | no | correct partition, reversed canonical shore order |
| medium | 825998069 | Gemini 3.8 Flash | yes | returned a verified model |
| hard | 1613508368 | GPT-5.6 Terra | yes | returned a verified model |
| hard | 1021523526 | Gemini 3.8 Flash | yes | returned a verified model |
| hard | 411757696 | Gemini 3.8 Flash | yes | returned a verified model |

| G9 arm at `easy` | solved / attempts | conclusion |
|---|---:|---|
| bare | 3 / 3 | the designated local preset is easy for the oracle pool |
| structural hint | 3 / 3 | the hint does not rescue the hardness claim |
| placebo hint | 3 / 3 | merely appending a sentence performs identically |

Hinted minus placebo is `0.0`.  The structural sentence bought no measured advantage, so these runs do not support the claimed involution-specific intuition.  At the local-gate preset the answer is 425 characters (about 107 tokens), 105 atoms, and the intended route is 192 operations.

## Use

```python
import random
import gen_2402_08332 as gen

params = gen.DIFFICULTY[gen.SHIPPING_DIFFICULTY]
inst = gen.make_instance(seed=17, **params)
statement = gen.render(inst)
candidate = gen.parse_answer(f"<answer>{inst['answer']}</answer>")
ok, reason = gen.verify(inst, candidate)
assert (ok, reason) == (True, "ok")
```

From the repository root, emit instances with:

```bash
bash scripts/emit.sh 2402.08332
```

## Caveats

The family is easy with a graph algorithm: exact global min-cut recovers every planted instance, by design.  The claim is only that 6,700 exact bookkeeping operations are unavailable in the evaluated no-tool context while the duplicated-half/cut insight compresses the route.  The structure-aware guess prior enforces the stated five-set shape, sizes, singleton degree, partition, and canonical order, but it does **not** condition on connected large branch sets or correct cross-adjacencies; therefore 0/200,000 is not a bound against a solver using connectivity propagation.  The measured reference cost is the more informative difficulty signal.

The panel tried local triangle-signature outliers, first-row and numeric-span greedies, an evenly spaced by-hand guess, and 256 random restarts.  It did not separately try spectral partitioning, graph canonical-labelling packages, ILP, or SDP; the exact successful min-cut reference is stronger for the planted cut but does not measure how readily a solver recognizes the involution.  `canonical_key` uses distance/refinement profiles rather than a complete graph-isomorphism canonical form, so rare nonisomorphic collisions remain possible even though all 20 tested unrelated seeds differed.  Most importantly, the oracle pool solved all writable rungs, so this module is retained as a `cap_bound` result and must not be emitted as a hardened family.
