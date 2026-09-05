# Encoded two-step counts in a directed strongly regular graph

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | matrix certificate |
| Intended intuition | invariant — the affine potential is conserved along the coordinate decoder |
| Domain essentiality | native |
| Reduction | none |

## What the family is

The source is Jerod Michel and Baokun Ding, [*Notes on Various Methods for Constructing Directed Strongly Regular Graphs*](https://arxiv.org/abs/1510.00110). Section 3, Theorem 3.1 (“Construction I”) defines a digraph on `G × G × Z_m` and proves its exact directed-strongly-regular parameters. This generator takes `G=Z_q`, applies a bijective affine relabelling to every coordinate, and hands the solver the resulting native directed graph by its exact adjacency predicate. The requested witness is a small submatrix of `A²`: entry `(r,c)` is the exact number of directed two-step paths from displayed row vertex `r` to displayed column vertex `c`.

The generator chooses decoded vertices first, deliberately includes diagonal, forward-edge, backward-edge, same-layer-edge, and non-edge cases, and then inverse-maps them through the public recurrences. Theorem 3.1 supplies the carried counts `t`, `lambda`, and `mu`; generation never searches for a path count. `verify` does not read the planted answer. It executes the displayed recurrences, classifies every ordered pair, and compares exact integers. As an independent audit, `selftest` expands all 75 vertices of the demo graph and checks all 5,625 entries of `A²` directly.

## Why this is Track B

This paper does not support a Track A claim: its contribution is an explicit construction, not a hardness theorem. The same Theorem 3.1 that guarantees generation also makes the decoded problem easy. For group order `q` and odd layer order `m`, Construction I has

`k=mq+q-2`, `t=2q+m-3`, `lambda=q+m-3`, and `mu=m+1`.

The standard exact evaluator runs all `n` stages of the public decoder for the 12 queried vertices and then applies these cases. Its complexity is `O(n·side + side²)`; at shipping `n=128`, `side=6`, it uses 18,510 counted modular operations, succeeds 8/8 as expected, and averaged 0.00056 seconds in the final self-test. That is easy for Python and not a complexity claim.

The compression is the conserved quantity

`a[r+1] z[r+1] + b[r+1] = a[r] z[r] + b[r] (mod s)`.

It collapses all 128 stages to the two endpoints of each chain. Decoding, classifying the 36 matrix entries, and forming the three path-count values then takes at most 222 exact arithmetic operations. That fits the no-tool cap, while mechanically executing 18,510 modular operations does not. Section 3’s explicit construction is also the paper result that identifies the easy regime; the generator avoids exposing decoded coordinates directly, but it does not pretend the tool-enabled algorithm is hard.

## Worked demo

`make_instance(seed=0, n=2, side=2, moduli="toy")` renders as follows:

```text
Compute exact two-step path counts in a directed graph.

The graph has V = Z_5 x Z_5 x Z_3.  Z_s means the integers 0,...,s-1 with addition and multiplication reduced modulo s.  A displayed vertex is a triple (A,B,C) in these ranges.

Coordinates are decoded by two public affine recurrences of length L=2.  For a displayed group coordinate z[0] in Z_5, use the arrays ga, gainv, gb below and compute, for r=0,...,L-1,

  z[r+1] = gainv[r+1] * (ga[r]*z[r] + gb[r] - gb[r+1]) mod q.

Each gainv[r] is the multiplicative inverse of ga[r] modulo q.

  ga[0:3] = 4 4 1

  gainv[0:3] = 4 4 1

  gb[0:3] = 2 4 3

For the displayed layer coordinate z[0] in Z_3, use ma, mainv, mb in the identical recurrence, reducing modulo m instead of q.

  ma[0:3] = 2 2 2

  mainv[0:3] = 2 2 2

  mb[0:3] = 1 2 0

Decode (A,B,C) as (x,y,i) by running the group recurrence on A and B separately and the layer recurrence on C.  All intervals below are inclusive.  Put h=(m-1)/2.  There is a directed edge

  (x,y,i) -> (u,v,j)

if and only if at least one of these four conditions holds:
  1. i=j, x=u, and y!=v;
  2. i=j, y=v, and x!=u;
  3. delta=(j-i) mod m lies in 1,...,h and u=(x+y) mod q;
  4. delta lies in h+1,...,m-1 and v=(x+y) mod q.
Thus loops are absent.  Every vertex has the same out-degree and in-degree K=18.

The following ordered row and column lists each contain 2 distinct displayed vertices.

  R[0] = (3, 4, 0)
  R[1] = (0, 3, 2)

  C[0] = (0, 3, 2)
  C[1] = (3, 0, 1)

Return the 2-by-2 integer matrix W in this exact order, where W[p][q] is the number of displayed vertices X in all of V such that R[p] -> X and X -> C[q].  Every entry is an integer in the inclusive range 0,...,K.  Matrix row and column order matters; no row or entry may be omitted.

Give your final answer inside <answer></answer> tags, as exactly one JSON object with the sole key "counts" and a rectangular integer matrix value.
Example: <answer>{"counts":[[0,0],[0,0]]}</answer>
Output nothing else inside the tags.
```

The answer is `{"counts":[[5,5],[10,4]]}`. This smallest setting is genuinely hand-solvable: each recurrence has two stages, and the graph has only 75 vertices if one wants to check by enumeration.

```python
>>> verify(inst, {"counts": [[5, 5], [10, 4]]})
(True, 'ok')
>>> verify(inst, {"counts": [[6, 5], [10, 4]]})
(False, 'entry (0,0) is not the exact two-step count')
```

## Difficulty presets

| Preset | Decoder length `n` | Matrix | Moduli | Render chars at seed 0 | Reference ops | Answer chars | Status |
|---|---:|---:|---|---:|---:|---:|---|
| demo | 2 | 2×2 | 5, 3 | 1,996 | 110 | 25 | hand-solvable illustration |
| easy | 128 | 6×6 | 31-bit primes | 12,124 | 18,510 | 420 | **shipping; bare level held** |
| medium | 256 | 6×6 | 61-bit primes | 37,106 | 36,942 | 744 | available, not reached |
| hard | 512 | 6×6 | 127-bit primes | 133,429 | 73,806 | 1,464 | available, not reached |

No preset was rejected. The bare harness held at its first evaluated rung, so it did not escalate.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted certificates; demo expansion checked 5,625/5,625 `A²` entries; answers JSON-round-trip |
| G2 | pass | drop, swap, duplicate, empty, and out-of-range corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON recovered through prose and a Markdown fence; garbage returned `None` |
| G4 | pass | 0/200,000 structure-aware guesses; exact density has log10 `-648.0000003` |
| G5 | pass | exactly one shipping answer; demo brute force found one; 256-restart baseline averaged 0.002585 s |
| G6 | pass | six attacks each 0/8; the direct reference and invariant route each solved 8/8 |
| G7 | pass | doubling decoder length to 256 built and verified; answer stayed at 36 atoms while reference work rose to 36,942 ops |
| G8 | pass | 140/140 relabellings invariant, 140/140 carried witnesses valid, 20/20 unrelated keys distinct |
| G9 | pass | 420 answer characters, about 105 tokens, 36 atoms, and 222 intended operations |

The six failing attacks were a raw-coordinate magnitude outlier, an all-nonedge mode, raw-coordinate greedy classification, a one-step decoder, a diagonal-only ansatz, and 256 uniform random restarts. The successful direct chain evaluator is reported separately as the Track B reference algorithm.

## Bare oracle loop

| Model | Preset | Seed | Solved | Recorded outcome |
|---|---|---:|---:|---|
| OpenAI GPT-5.6 Terra | easy | 383615593 | no | returned the all-zero matrix; first entry wrong |
| Google Gemini 3.8 Flash | easy | 693300350 | no | found the three parameter values but misclassified entry `(2,3)` |
| OpenAI GPT-5.6 Terra | easy | 1473083956 | no | attempted the three-value pattern but misclassified entry `(0,5)` |

`.meta.json` records `verdict: hardened`, zero escalations, and `easy` as the shipping preset. Every reply parsed, so none is a contract false negative.

## G9 arms

| Arm | Solved / attempts | Observation |
|---|---:|---|
| bare | 0 / 3 | hardened |
| structural hint | 0 / 3 | hardened; the invariant was named explicitly, but all three matrices still had a wrong classification |
| placebo hint | 0 / 3 | hardened |

Hinted minus placebo is `0.0`. In this small diagnostic the invariant sentence bought no successful answer. The replies show that several models nevertheless reached the correct three count values; the remaining difficulty was exact endpoint decoding and classification, so the benchmark measures execution as well as discovery. The shipping answer is 420 characters (about 105 tokens), has 36 atomic entries, and the intended route is 222 exact operations.

## Use

```python
from gen_1510_00110 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=12345, **DIFFICULTY["easy"])
question = render(inst)
candidate = parse_answer('<answer>{"counts":[[0,0,0,0,0,0],[0,0,0,0,0,0],[0,0,0,0,0,0],[0,0,0,0,0,0],[0,0,0,0,0,0],[0,0,0,0,0,0]]}</answer>')
ok, reason = verify(inst, candidate)
```

From the repository root, emit fresh verified instances with:

```bash
bash scripts/emit.sh 1510.00110 20 easy
```

## Caveats

- This is emphatically Track B. The direct evaluator solves every generated instance in under a millisecond on this machine. It is not evidence that path counting, directed strongly regular graph recognition, or graph isomorphism is computationally hard.
- G4 samples uniformly from the exact statement-level language of bounded 6×6 count matrices. It enforces shape and the obvious `0,...,K` bound, but it does not grant the unstated Theorem 3.1 fact that only three count values occur. Its tiny density rules out blind matrix guessing, not theorem-aware structured attacks; G6 and the oracle transcripts address a few such attacks.
- The long recurrence is an added structure-preserving relabelling of the paper’s graph, not a new graph theorem. The graph, adjacency predicate, and `A²` certificate remain native; the task covers Construction I rather than the Cayley and block-matrix constructions in Sections 4 and 5.
- I did not test a general SMT encoding, a computer-algebra simplifier, automated invariant discovery, or arbitrary graph-isomorphism software as failing attacks. Tool-enabled symbolic simplification is expected to succeed.
- `canonical_key` is complete for input reordering, public affine encoder relabelling, cyclic-group multiplication automorphisms, layer translations, and the coordinate-swap/layer-reflection symmetry tested here. The graph may have additional automorphisms; the key is the strongest cheap invariant implemented, not a proof of full graph-isomorphism canonicalization.
- The medium and hard renderings are large because the public recurrence is the mechanical haystack. Only `easy` ships. A model with a calculator or sandbox can ignore that burden, which is precisely why the claim is no-tool compression rather than structural hardness.
