# Connected subgraphs in many star layers (arXiv:1604.07724)

| Profile field | Value |
|---|---|
| Track | **A — structural hardness** |
| Native domain | `combinatorics` |
| Object regime | `finite_discrete` |
| Computational core | `graph` |
| Certificate form | `integer_tuple` |
| Intended intuition | `reduction recognition`: shared-hub connectivity is a balanced biclique in the vertex-by-layer incidence graph |
| Domain essentiality | `native` |
| Reduction | `paper_licensed`, Section 4, Theorem 1 and Corollary 5 |

## What the family asks

This implements the native Connectivity-ML-Subgraph problem from Bredereck et al., [*Assessing the Computational Complexity of Multi-Layer Subgraph Detection*](https://arxiv.org/abs/1604.07724). The solver receives many undirected star layers on one common vertex set and must return exactly `k` vertices whose induced graph is connected in at least `ell` layers. Each star is encoded without loss as a fixed-width hexadecimal layer-incidence mask for every non-hub vertex. Checking a witness takes exact bitset intersections and a population count; `verify` never reads `inst["answer"]`.

Generation is inverse and theorem-backed. Two disjoint `h`-sets are sampled first. A dense `G(n,1/2)` graph is drawn, and missing edges between those sets are inserted with degree-preserving 2-switches. Independent vertex and layer permutations hide the two shores. Theorem 1's construction makes one star layer from each graph neighborhood, so the hub plus either planted shore is connected in the `h` opposite-shore layers. No generated instance is solved to obtain its certificate.

## Why Track A is plausible

Section 4, Theorem 1 proves W[1]-hardness in the combined selected-vertex and selected-layer parameters by reducing Balanced Biclique to precisely these shared-hub star layers; Corollary 5 applies it to Connectivity. The shipping regime has `n=256`, `ell=13`, and `k=14`; both `ell` and `k` grow along the ladder. The plant is above the logarithmic scale where accidental balanced bicliques appear in a dense random graph, but below the square-root scale targeted by the basic spectral attack. This is a distributional claim supported by the measured attacks below, not an average-case theorem from the paper.

The easy regimes were explicitly avoided. Proposition 3 gives an FPT algorithm in the total layer count `t` and polynomial time when `ell` or `t-ell` is constant, so here `t=n` and `ell` both grow. Section 5, Theorem 2 makes matching with at most two required layers polynomial-time; that is not this family. Proposition 2 makes finitely-forbidden hereditary properties FPT for small vertex/layer deletion parameters; Connectivity is non-hereditary and the generated deletion parameters grow.

An earlier candidate rung, `n=128, ell=11`, was removed even though the bare oracle failed 0/3: the 20-million-node exact biclique attack solved 4/8 seeds. This is why the shipped ladder begins at `n=256`.

## Worked demo (`seed=0`)

This is the complete output of `render(make_instance(n=8, h=2, seed=0))`:

```text
Connected induced subgraph in many layers

There are 9 vertices, with integer IDs 0 through
8, and 8 undirected simple graph
layers numbered 0 through 7.  Every layer is a star
with the same hub vertex H=4; a star may have any number of
leaves.  Thus the only possible edge in layer j incident to a non-hub vertex v
is {H,v}.

The table below completely specifies every layer.  Each row is
"vertex: hexadecimal-mask" for one non-hub vertex.  Every mask has exactly
2 hexadecimal digits.  Bit j of the represented
nonnegative integer is 1 exactly when edge {H,v} is present in layer j; bit
0 is the least-significant (rightmost) bit.  No edges other than those encoded
by these masks exist.  Row order has no significance.

7: b0
3: 29
0: 98
8: aa
5: 5d
2: cc
6: b7
1: 4b

Find exactly k=3 distinct vertices such that their induced
subgraph is connected in at least ell=2 different
layers.  In a layer, "induced" means keeping precisely the edges of that layer
whose two endpoints are both selected.  A graph is connected when every pair
of its vertices is joined by an edge-path.  The same selected vertex set must
work in all counted layers.  Layer order does not matter.

Give the k vertex IDs as one strictly increasing JSON list; IDs are 0-indexed,
order is otherwise mathematically irrelevant, and repetitions are forbidden.
Give your final answer inside <answer></answer> tags, as that JSON list.
Example: <answer>[0, 1, 2]</answer>
Output nothing else inside the tags.
```

The planted answer is `<answer>[1, 4, 6]</answer>` and `verify` returns `(True, "ok")`. Dropping vertex 6 gives `[1, 4]`, for which it returns `(False, "answer must contain exactly 3 vertices")`. A person can solve this demo by converting eight two-digit masks and testing pairwise intersections; `enumerate_all` finds 20 valid formatted witnesses.

## Difficulty presets

| Preset | `n=t` | `ell=h` | `k` | Status |
|---|---:|---:|---:|---|
| demo | 8 | 2 | 3 | Hand-scale; skipped by hardening |
| easy | 256 | 13 | 14 | **Ships**; local gates and bare oracle hold |
| medium | 400 | 15 | 16 | Available escalation |
| hard | 600 | 17 | 18 | Available escalation |

`escalate` first enlarges only the ambient graph and keeps the witness length fixed. It raises `h` by two only when the first-moment estimate for accidental `K_h,h` subgraphs reaches `1e-6`; at shipping, the separate size-doubling check also builds `n=512` while keeping the 14-element witness.

## Gate results

| Gate | Result | Measurement at shipping unless noted |
|---|---|---|
| G1 | pass | 12/12 preset-seed planted witnesses verify and JSON-round-trip |
| G2 | pass | 6 corruptions rejected; the five mandatory forms have five distinct reasons |
| G3 | pass | Model-style fenced/prose response round-trips; garbage returns `None` |
| G4 | pass | 0/200,000 structure-aware guesses; space `C(256,13)=2,389,501,662,813,006,112,000` |
| G5 | pass | 0/200,000 sampled density; exact attack exhausted 20,000,000 nodes in 5.36 s; demo has 20 exact answers |
| G6 | pass | Degree, greedy, 256-restart, pair-outlier, centered spectral, and exact attacks all 0/8; exact panel used 160,000,000 nodes in 40.35 s |
| G7 | pass | `n=512` builds and verifies; named candidate spaces strictly increase |
| G8 | pass | 60 relabelling invariance checks, 60 carried-witness checks, 20/20 unrelated keys distinct |
| G9 | pass | 52 chars, 14 atoms, about 13 tokens, 14 intended bitset operations |

Times are measurements from `selftest_report.json` on this machine and may vary.

## Bare oracle loop

| Preset | Seed | Model | Solved | Recorded reason |
|---|---:|---|---|---|
| easy | 1431020018 | GPT-5.6 Terra | no | Parsed witness connected in 0 layers |
| easy | 320166238 | Gemini 3.8 Flash | no | Parsed witness connected in 0 layers |
| easy | 1023447726 | Gemini 3.8 Flash | no | Empty length-limited response; no witness parsed |

The script-owned verdict is `hardened` at `n=256, h=13`, with zero escalations. Two calls produced concrete wrong witnesses; one exhausted the default 32,000 completion/reasoning-token budget and is called out again under caveats.

## G9 diagnostic arms

| Arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened |
| placebo hint | 0/3 | hardened |

`hinted - placebo = 0.0`. Naming the balanced-biclique structure bought this oracle pool nothing, so the measured difficulty is not merely recognizing the reduction; extracting 13 labels from the 256-by-256 incidence data remains the dominant obstacle. The answer and post-recognition verification route remain small: 52 characters, 14 atoms, and 14 exact bitset operations.

## Use

From this directory:

```python
import random
import gen_1604_07724 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=123, **params)
prompt = g.render(inst)
answer = g.parse_answer(f"<answer>{inst['answer']}</answer>")
assert g.verify(inst, answer) == (True, "ok")
candidate = g.random_candidate(inst, random.Random(7))
```

From the repository root, emit samples with:

```bash
bash scripts/emit.sh 1604.07724 20
```

The module uses only the standard library. It includes the requested graceful `gvlib` import, but this graph family does not need those helpers.

## Caveats

- The paper proves worst-case NP/W[1]-hardness, not average-case hardness of this degree-preserving planted distribution. Track A rests on the failed measured attacks and the familiar planted-biclique gap, not a theorem that rules out all polynomial algorithms.
- The 2-switch process preserves every initial degree exactly, but it is not proved to sample uniformly from graphs conditioned on containing the plant. Higher-order correlations may admit an attack not in the panel.
- The exact baseline is a custom common-neighborhood branch-and-bound, not a state-of-the-art maximum-biclique package, SAT/ILP encoding, SDP/nuclear-norm relaxation, or commercial solver. The spectral probe is centered power iteration, not a full multi-eigenvector/SVD or SDP implementation. Those stronger attacks were not tried.
- The 0/200,000 guess result is an empirical frequency under the strongest freely deducible prior used here: the hub is included and a uniform `h`-subset of non-hub vertices is sampled. It does not count all shipping solutions or prove a probabilistic upper bound below `1e-6`; it does show no hit in the mandated sample. Other solver priors are represented only by G6.
- `canonical_key` is a five-round bipartite Weisfeiler-Leman invariant. It is relabelling-invariant and separated all 20 unrelated tests, but it is not a complete graph-isomorphism canonical form and can collide on specially constructed incidence graphs.
- One bare oracle attempt returned no text after consuming the default model budget. The harness specification counts that as a completed failure, but only two of the three bare records contain inspectable wrong witnesses. Both hinted and placebo arms contain three parsed, concretely invalid witnesses.
- The removed `n=128, h=11` rung demonstrates that no-tool oracle failure is not evidence against a specialist exact attack; it must not be restored as the shipping preset without retesting.
