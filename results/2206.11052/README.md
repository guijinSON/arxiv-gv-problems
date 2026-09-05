# Signed half-edge colourings from arXiv:2206.11052

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | integer tuple (one signed colour per edge) |
| Intended intuition | change of variables: modular reciprocals reveal constant-difference matchings |
| Domain essentiality | native |
| Reduction | none |

This generator turns Steffen and Wolf's [*Bounds for the chromatic index of signed multigraphs*](https://arxiv.org/abs/2206.11052) into an exact signed-edge-colouring task.  The solver receives a signed bipartite graph, a half-edge orientation, immutable residue tags on its vertices, and the symmetric palette `{-k,...,-1,1,...,k}`.  It must return one raw colour per displayed edge.  `verify` multiplies each raw colour by its half-edge orientation and checks exact pairwise distinctness at every vertex, including the defining identity `sigma = -tau_left*tau_right`.

## Why Track B

Section 2.1 supplies the exact half-edge definition and proves invariance under resigning.  The opening of Section 3 observes that an antibalanced signed graph has the ordinary chromatic index of its underlying graph; for this bipartite construction, König decomposition is therefore an efficient solution.  Theorem 3.2 gives the general signed Shannon bound but no distributional hardness theorem, so Track A would be false.

The disclosed reference algorithm repeatedly finds perfect matchings with a Kuhn augmenting-path matcher.  Its complexity is `O(Delta*V*E)` here; over eight hard instances it solved 8/8 in 5,620.88 counted operations on average (6,246 maximum) and 0.001112 seconds.  The compact route recognizes that reciprocating the vertex tags recovers cyclic coordinates, after which edge differences expose the planted perfect-matching classes.  That route is counted at 237 exact operations.  The generator samples shifts and their colours before building the graph, then carries the colouring through vertex permutations, edge shuffling, reciprocal tags, and resigning; it never runs a colouring algorithm to obtain `inst["answer"]`.

## Worked demo

With `make_instance(n=5, degree=2, seed=0)`, the complete rendered instance is:

```text
SIGNED HALF-EDGE COLORING

A signed graph edge has one half-edge at each endpoint.  Each half-edge
has an orientation tau in {-1,+1}; the edge sign is
sigma = -(tau_left * tau_right).  A symmetric color palette contains
both a and -a whenever it contains a.  If edge e receives raw color
c(e), its oriented color at an endpoint v is tau(e,v)*c(e).
A coloring is valid exactly when the oriented colors of all distinct
edges incident with each vertex are pairwise different.

There are two vertex classes L0..L4 and R0..R4.
Every vertex has degree 2; there are 10 edges.
The modulus for the immutable residue tags is the prime p=5.
Vertex IDs are arbitrary; the residue tag shown beside each vertex is
part of the instance and moves with that vertex under relabeling.
Allowed raw colors, with no zero color, are: [-1, 1]

Vertex residue tags (ID:tag):
L: L0:4 L1:1 L2:2 L3:3 L4:0
R: R0:0 R1:3 R2:2 R3:4 R4:1

Edges are indexed from 0.  Each row is
index  left-ID  right-ID  tau-left  tau-right  sigma.
0 L4 R3 -1 -1 -1
1 L0 R4 -1 -1 -1
2 L3 R4 -1 -1 -1
3 L0 R2 -1 +1 +1
4 L2 R1 +1 -1 +1
5 L1 R2 -1 +1 +1
6 L1 R0 -1 +1 +1
7 L4 R1 -1 -1 -1
8 L2 R0 +1 +1 -1
9 L3 R3 -1 -1 -1

Return exactly 10 integers, one raw color for each edge
in increasing edge-index order.  Repetitions are allowed globally, but
every entry must belong to the displayed palette.  The list is a JSON
array; order matters and indices are 0-based.
Give your final answer inside <answer></answer> tags, as a JSON array of integers.
Example: <answer>[-1, 1, -1, 1]</answer>
Output nothing else inside the tags.
```

The planted answer is `[1,-1,1,1,1,-1,1,-1,-1,-1]`.  `verify(inst, inst["answer"])` returns `(True, "ok")`; changing its first entry to `0` returns `(False, "a color lies outside the displayed symmetric palette")`.  This demo is genuinely hand-scale: reciprocal tags modulo 5 and ten two-colour checks fit on paper.

## Difficulty presets

| Preset | `n` / actual prime | Degree | Edges / answer atoms | Status |
|---|---:|---:|---:|---|
| demo | 5 | 2 | 10 | hand example; skipped by hardener |
| easy | 7 | 4 | 28 | oracle call blocked before scoring |
| medium | 13 | 8 | 104 | not reached |
| hard | 19 | 12 | 228 | configured shipping preset; local gates pass |

The hard preset is configured as `SHIPPING_DIFFICULTY`, but it is **not yet oracle-certified** because the supplied OpenRouter key hit its total limit before any scored call.  A successful rerun of STEP 4 is still required before submission.

## Gate results

| Gate | Result |
|---|---|
| G1 | 12/12 planted answers verify |
| G2 | 5/5 corruption classes rejected with 5 distinct reasons |
| G3 | tagged, fenced model-style response round-trips; answer is JSON-native |
| G4 | 0/200,000 structure-aware balanced-word guesses; declared space about `1.403e235` |
| G5 | shipping sampled density `0/200,000`; demo has exactly 2 answers; reference cost 5,787 operations and 4,070 edge scans on the density seed |
| G6 | five attacks each 0/8; reference König decomposition 8/8 as expected |
| G7 | doubled request builds at prime 41 and verifies (492-edge answer) |
| G8 | 140/140 key invariance checks and 140/140 carried witnesses; 20/20 unrelated keys distinct |
| G9(c) | 571 characters, 143 estimated tokens, 228 atoms, 237 intended operations: all within caps |

## Oracle loop and G9 diagnostics

No row below is a model failure.  Every call was an HTTP 403 API error, so `harden.py` correctly refused to make a hardness claim.

| Arm | Preset | Harness calls | Scored solved/attempts | Outcome |
|---|---|---:|---:|---|
| bare | easy | 4 | 0/0 | OpenRouter total key limit; ladder stopped |
| structural hint | hard | 4 | 0/0 | OpenRouter total key limit |
| placebo hint | hard | 4 | 0/0 | OpenRouter total key limit |

The recorded `hinted - placebo` value is `0.0` only because both denominators are zero; it is not interpretable evidence about the change-of-variables intuition.  The harness-owned error records remain in the three transcript files so the blockage is auditable.  Once the key limit is raised, rerun all three arms and replace this table with scored results.

## Use

```python
from gen_2206_11052 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=123, **DIFFICULTY["hard"])
prompt = render(inst)
candidate = parse_answer("<answer>" + str(inst["answer"]) + "</answer>")
assert verify(inst, candidate) == (True, "ok")
```

From the repository root, after a successful hardening rerun, emit records with:

```bash
bash scripts/emit.sh 2206.11052 20
```

The module is standard-library-only; `gvlib` is imported opportunistically but is not required.

## Caveats

This is deliberately Track B: any solver with matching code disposes of the instances in milliseconds.  The 0/200,000 estimate samples uniformly from colour words that already have the forced global multiplicity of each colour; it is much stronger than independent noise, but it does not enforce local constraints on one bipartition and therefore is not a proof of practical hardness.  The answer uses 228 of the 256 allowed atoms, so although it is only 571 characters, failures may still contain a transcription component; the doubled G7 instance is over the shipping atom cap and is not shippable.  The panel includes the standard matching algorithm, first-fit greedy, orientation/outlier, raw-tag-difference, rank-sum, and random-restart probes, but not an optimized external matching package or a solver explicitly handed reciprocal decoding, since that is the intended compact route.  Finally, the missing four-vendor and G9 measurements are a real release blocker, not a family failure; the current artifacts must not be represented as hardened until those API calls succeed.
