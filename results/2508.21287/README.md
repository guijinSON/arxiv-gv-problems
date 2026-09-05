# Motif-guided induced subgraph isomorphism (arXiv:2508.21287)

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | integer tuple (a vertex map) |
| Intended intuition | decomposition — bridge-separated motif blocks plus a modular graph symmetry |
| Domain essentiality | native |
| Reduction | none |

## What the family is

The source is Wang et al., [*Delta-Motif: Parallel Subgraph Isomorphism via Tabular Operations for Scalable Layout Selection*](https://arxiv.org/abs/2508.21287). Section III-A defines an embedding as an injective map into a vertex-induced subgraph, so adjacency must hold in both directions; both input graphs are connected, simple, undirected, and unlabeled. Sections III-B–III-D decompose patterns into motifs, precompute motif-embedding tables, and join and filter those tables.

An instance gives a 67-vertex circulant pattern and one connected data graph made from many 67-vertex circulant blocks joined through bridge connectors. It also gives exact length-2/3/4 walk counts for each edge-step type—the small motif data that the paper precomputes. The solver returns the image of pattern vertices `0,...,66` in order. The generator samples every block by the same rule, chooses one uniformly after all blocks exist, and obtains the pattern by inverse affine relabelling of that known block. It never solves the completed instance.

`verify` checks length, range, injectivity, and all `67 choose 2` edge/nonedge equivalences against explicit edge sets. It never reads `inst["answer"]`, so any valid induced embedding is accepted.

## Why this is Track B

This cannot honestly be Track A. Section III supplies an explicit join/filter enumeration algorithm, Section V identifies VF2 as the standard baseline, and Section VI-A reports complete enumeration on connected 20–100-vertex patterns inside structured 1,600–3,600-vertex data graphs. The paper’s method completes those workloads in seconds and is sometimes hundreds of times faster than VF2.

For this restricted circulant-block representation, an even simpler mechanical algorithm exists: scan every block and every nonzero modular multiplier and compare all six transformed step types. It is `O(B*k*r)`. At the shipping preset it solved 8/8 instances, averaging 15,504.25 exact operations, 857.625 multiplier candidates, and 0.001448 seconds per solve. Those successes are expected and are reported as the Track B reference—not hidden among failing attacks.

The compact route uses the paper’s motif viewpoint. Blocks separate at bridges; the sorted short-walk profile identifies a matching block; a step type whose profile occurs once identifies the common multiplier up to sign; applying it to `0,...,66` writes the map. The audit solved 8/8 this way in at most 171 exact comparisons/arithmetic operations. Without that decomposition and symmetry, a no-tool solver faces the mechanical scan or generic subgraph backtracking.

## Worked demo

`make_instance(seed=0, n=2, pattern_size=5, step_count=1)` renders in full as:

```text
Find an induced copy of one connected graph inside another.

All graphs here are finite, simple, undirected, and unlabeled: the displayed
integers are vertex identifiers, not vertex colors.  For integers modulo k,
an undirected circulant graph with step representatives S has vertices
0,...,k-1 and an edge {x,y} exactly when min((y-x) mod k,(x-y) mod k) is in S.

PATTERN GRAPH P
  k = 5
  vertices: 0..4
  step representatives: [1]
Thus P has an edge {x,y} exactly by the circulant rule above.

DATA GRAPH D
D contains 2 circulant blocks, each with k local vertices.  In block
j, local vertex x has global identifier j*k+x.  Its internal edges use the
listed step representatives.  There is also one connector q_j with global
identifier 10+j.  Connector q_j is adjacent to local vertex 0
of block j, and consecutive connectors q_j,q_(j+1) are adjacent.  These and
the internal block edges are ALL edges of D.  Hence D is connected and has
12 vertices numbered 0..11.

Block data:
  block 0: global vertices 0..4; steps [2]; c-table [2:0/3/1]
  block 1: global vertices 5..9; steps [2]; c-table [2:0/3/1]

The c-table is redundant exact motif data of the kind precomputed by the
paper's tabular method: entry s:c2/c3/c4 gives the exact numbers of walks of
length 2, 3, and 4 between the endpoints of every internal step-s edge.
For P its c-table is [1:0/3/1].  It does not add edges or labels.

Return one injective map f from P into D as a JSON list [f(0),...,f(4)].
It is valid exactly when, for every pair of distinct pattern vertices x,y,
{x,y} is an edge of P if and only if {f(x),f(y)} is an edge of D.  This is
an induced-subgraph embedding: both edges and nonedges must be preserved.
All 5 entries must be distinct decimal integers in the inclusive range
0..11; order matters and repetition is forbidden.

Give your final answer inside <answer></answer> tags, as the JSON list just specified.
Example of the JSON syntax for a five-vertex toy instance: <answer>[4,0,1,2,3]</answer>
Output nothing else inside the tags.
```

The planted answer is `[0,3,1,4,2]`. A person can solve this demo on paper: both relevant graphs are five-cycles, and multiplying local labels by `3 modulo 5` maps step 1 to step 2.

```python
>>> verify(inst, [0, 3, 1, 4, 2])
(True, 'ok')
>>> verify(inst, [0, 3, 1, 4, 0])
(False, 'mapping is not injective')
```

## Difficulty presets

| Preset | Blocks | Pattern vertices | Data vertices | Step types | Crowding pool | Answer entries | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 2 | 5 | 12 | 1 | 1 | 5 | hand-solvable example; never ships |
| easy | 24 | 67 | 1,632 | 6 | 1 | 67 | **provisional shipping preset** |
| medium | 30 | 67 | 2,040 | 6 | 4 | 67 | available if the oracle solves easy |
| hard | 36 | 67 | 2,448 | 6 | 16 | 67 | available if the oracle solves medium |

The witness length is fixed across all non-demo rungs. Difficulty grows by adding same-distribution decoy blocks and by selecting each decoy from a larger pool for closer motif-profile near-misses. No preset has been rejected, but the required external hardening verdict is unavailable because the supplied OpenRouter key is over its account limit.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses over every preset and three seeds |
| G2 | pass | drop, swap, duplicate, empty, and out-of-range corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON recovered through prose and a Markdown fence; garbage returned `None` |
| G4 | pass | 0/200,000 structure-aware guesses; exact language size has 318 bits |
| G5 | pass | shipping density estimate 0/200,000; demo has exactly 20 witnesses; reference cost measured |
| G6 | pass | four attacks each 0/8; disclosed reference and compact algorithms each 8/8 |
| G7 | pass | 24→48 blocks, 1,632→3,264 vertices, full scan budget 28,512→57,024 operations |
| G8 | pass | 140/140 invariant keys, 140/140 carried witnesses valid, 20/20 unrelated keys distinct |
| G9(c) | pass | 269 characters, 68 estimated tokens, 67 atoms, 129 operations for the shipping sample |

## Oracle loop

The official harness was run, but no oracle call completed. API errors are correctly not counted as failures, so there is no hardness verdict and no claim that the preset defeated an oracle.

| Preset | Seeds | Completed / calls | Solved | Why |
|---|---|---:|---:|---|
| easy | 1191627564, 255182664, 1408972773, 913350338 | 0 / 4 | unmeasured | OpenRouter HTTP 403: key total limit exceeded |

The script-owned `llm_loop_transcript.jsonl` and `.meta.json` preserve those errors. Re-run the command below after restoring OpenRouter quota; if easy is solved, follow the harness’s ladder result and update `SHIPPING_DIFFICULTY`.

## G9 arms

| Arm | Completed attempts | Solved | Status |
|---|---:|---:|---|
| bare | 0 | unmeasured | four HTTP 403 errors |
| structural hint | 0 | unmeasured | four HTTP 403 errors |
| placebo hint | 0 | unmeasured | four HTTP 403 errors |

Hinted minus placebo is unmeasured, not zero evidence. The JSON field is numerically `0.0` only because neither arm has a completed denominator. No conclusion about structural help is justified until the arms run. The size/effort part still passes: 269 answer characters, 67 elements, and 129 intended-route operations for the audited shipping instance; the declared worst-case bound is 84 tokens.

## Use

```python
from gen_2508_21287 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=12345, **DIFFICULTY["easy"])
question = render(inst)
candidate = parse_answer("<answer>[0,1]</answer>")
ok, reason = verify(inst, candidate)
```

From the repository root, emit instances after the oracle run has produced a hardened verdict:

```bash
python3 results/2508.21287/gen_2508_21287.py
cd results/2508.21287 && python3 ../../scripts/harden.py gen_2508_21287.py
cd ../.. && bash scripts/emit.sh 2508.21287 20 easy
```

## Caveats

- This is Track B, not evidence of average-case or complexity-theoretic hardness. Code finds an answer in under a millisecond on the measured machine.
- The family covers the paper’s native induced-subgraph object and motif tables, but its circulant block distribution is builder-designed. It is not the paper’s square-grid, heavy-hex, or quantum-device benchmark distribution.
- G4 samples uniformly from a block and then uniformly from all `67!` bijections. That incorporates the bridge-implied block constraint, but it says nothing about structured multiplier guesses; G6 addresses only four such cheap strategies.
- The local adversary panel did not include a production VF2 implementation or the paper’s GPU Delta-Motif implementation because neither is available under the standard-library-only constraint. Both are expected to succeed and must not be interpreted as failing attacks. The exhaustive affine scan is stronger for this restricted representation.
- Every block—including the one later selected as the plant—has the same conditional sampling law, size, degree, triangle total, attachment form, and crowding selection. The pattern’s complete short-walk profile supplies the correlation needed to find an isomorphic block; another block can occasionally also be valid, and `verify` accepts it.
- `canonical_key` uses exact degree/common-neighbor fingerprints and the connector-path sequence. It passed arbitrary pattern/data relabellings and input reorderings, but it is not a complete graph-isomorphism canonical form outside this generated family.
- Most importantly, STEP 4 and the three G9 oracle arms remain externally blocked. The module and local gates are reproducible, but this directory is not submission-ready until successful script-owned oracle transcripts replace the HTTP 403 diagnostics.
