# Steiner triple-system parity certificates (arXiv:2310.15909)

Status: the generator and all local gates pass, but this result is **not yet
shippable**. The required OpenRouter hardening and G9 runs were attempted by the
official script and every request returned HTTP 403 `Key limit exceeded`; errors
are not model failures. The script-owned error transcripts are retained so the
blocker is auditable.

| profile field | value |
|---|---|
| Track | B — no-tool compression |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT |
| Certificate form | integer tuple (a natural four-set partition) |
| Intuition | symmetry: recognize the period-four classes of a primitive-root orbit |
| Domain essentiality | native; no reduction |

## Problem and trust model

[Hyunwoo Lee, *Towards a high-dimensional Dirac's theorem*](https://arxiv.org/abs/2310.15909)
studies Steiner triple systems (STSs) inside 3-uniform hypergraphs. An STS is a
set of triples that covers each vertex pair exactly once. This family asks for
a four-part partition certifying that no STS exists. `verify` checks the
partition, every hyperedge's part pattern, and the final odd parity count using
integers only; it does not read the planted answer.

The construction is exactly the obstruction in Proposition 1.7 (Section 1.4),
followed by safe random edge deletion. `V0` is even and `V1,V2,V3` are odd.
The allowed edge types force a certain odd number of pairs between the three
odd parts to be covered by triples contributing two such pairs each, an
impossibility. Sampling the partition first and then sampling all retained
edges uniformly from the same allowed set gives a certificate by construction.

This is Track B. Theorem 1.2/Corollary 1.9 only prove asymptotic existence above
the paper's codegree threshold; they do not prove that a random planted search
distribution is hard. Section 3 also gives a max-flow/min-cut construction for
the fractional relaxation, while Sections 4–6 use pseudorandom matching and
iterative absorption. Those are existence tools, not evidence that the proposed
random planted distribution is hard. Here the efficient reference method instead
computes one quartic character per public coordinate in `O(n log n + |E|)`. At
`n=229` it used 2,052 modular multiplications to produce the certificate, then
1,832 edge checks, and took under 0.01 seconds. The compact route recognizes the
period-four primitive-root orbit and uses 228 modular multiplications. The former
is easy for a program but not a realistic unaided calculation; the latter fits
the 300-operation cap once the symmetry is seen.

## Worked demo

This is the complete `demo`, seed 0. A person can solve it on paper: start at the
coordinate of marked vertex 1, repeatedly multiply by 2 modulo 13, and group
orbit positions modulo 4.

```text
STEINER-TRIPLE-SYSTEM PARITY CERTIFICATE

A 3-uniform hypergraph has vertices 0,...,n-1 and hyperedges that are unordered triples of distinct vertices.  A Steiner triple system (STS) inside it would be a set of hyperedges in which every unordered pair of distinct vertices occurs in exactly one selected triple.

Certify that the displayed hypergraph has no STS by finding an ordered partition [V0,V1,V2,V3].  Every vertex must occur exactly once.  Order inside a part is irrelevant and repetitions are forbidden.
The required part sizes are [4, 3, 3, 3]; V0 must contain both marked vertices 8 and 1.
Every displayed hyperedge must avoid all three forbidden color patterns:
  (i) three vertices in V0;
  (ii) one vertex in V0 and two vertices in the same Vi for i=1,2,3;
  (iii) one vertex in each of V1,V2,V3.
Here the color of a vertex is the index of the part containing it.
These conditions are an exact parity certificate: V0 is even and the other parts are odd, and the remaining cross-pairs would have to be covered two at a time by any alleged STS.

n = p = 13, where p is prime (all coordinate arithmetic below is modulo p).
A primitive root is a number whose first p-1 positive powers visit every nonzero residue exactly once.
The public primitive root used here is g = 2.
Each public coordinate is already centered: the marked center has coordinate 0.
Public coordinate attached to each vertex (vertex:coordinate):
0:6 1:2 2:1 3:10 4:3 5:7 6:8 7:12 8:0 9:9 10:5 11:4 12:11

Hyperedges (65 lines, each sorted increasingly):
0 1 6
0 1 9
0 1 12
0 2 7
0 3 4
0 3 10
0 4 7
0 4 8
0 5 7
0 7 8
0 7 9
0 8 9
0 8 11
0 9 10
0 9 12
0 10 12
1 2 3
1 2 7
1 3 4
1 4 8
1 4 10
1 4 11
1 5 8
1 5 9
1 5 11
1 6 9
1 7 9
1 10 12
2 3 4
2 3 11
2 4 9
2 4 11
2 5 6
2 5 12
2 8 12
2 9 11
3 4 8
3 5 10
3 5 12
3 6 11
3 6 12
3 8 9
3 8 10
3 9 10
3 9 11
4 6 9
4 7 9
4 7 10
4 8 10
5 6 9
5 7 8
5 7 10
5 7 12
5 9 10
5 10 11
6 7 10
6 8 10
6 9 10
6 11 12
7 8 12
7 9 10
7 10 12
8 9 10
9 10 11
10 11 12

Give your final answer inside <answer></answer> tags as one JSON array [V0,V1,V2,V3] of four integer arrays.
Example: <answer>[[0,4],[1],[2],[3]]</answer>
Output nothing else inside the tags.
```

Answer:

```json
[[0,1,8,10],[3,7,11],[5,6,12],[2,4,9]]
```

`verify(inst, answer)` returns `(True, "ok")`. Removing the last vertex returns
`(False, "wrong part sizes: expected [4, 3, 3, 3], got [4, 3, 3, 2]")`.

## Difficulty

| preset | n | retained edges | reference operations | status |
|---|---:|---:|---:|---|
| demo | 13 | 65 | 101 | hand-solvable illustration |
| easy | 37 | 296 | 476 | local gates pass; oracle call blocked |
| medium | 109 | 872 | 1,736 | local gates pass; not reached by oracle |
| hard | 229 | 1,832 | 3,884 | configured shipping preset; oracle evidence pending |

After `hard`, `escalate` first keeps the 229-atom answer fixed and deletes clues
by lowering `edge_factor` through 6, 4, and 3. Only then does it return
`"cap_bound"`: the next admissible prime is 277, beyond the 256-atom cap.

## Gate results

| gate | result |
|---|---|
| G1 | pass, 12/12 planted certificates |
| G2 | pass, five corruptions rejected with five distinct reasons |
| G3 | pass, tagged JSON round-trip with prose/fence |
| G4 | pass, 0/200,000 structure-aware guesses; 443-bit candidate space |
| G5 | pass locally; shipping density 0/200,000, demo has exactly 6/92,400 answers, reference cost 2,052 certificate operations + 1,832 checks; compact route verifies in 228 operations |
| G6 | pass; degree, consecutive-coordinate, coordinate-mod-4, quadratic-character, 256-restart, and 256-node DPLL attacks each succeed 0/8; reference succeeds 8/8 |
| G7 | pass; n=541 builds and verifies |
| G8 | pass; 80/80 invariance, 80/80 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | pass; 1,043 characters, 261 estimated tokens, 229 atoms, 228 intended operations |
| G9(a,b) | **pending** because every official oracle request returned HTTP 403 |

## Oracle loop

No solved/failed model attempt exists yet: the harness redraws provider errors
and then aborts, as it should. The counts below therefore remain 0/0 rather
than misreporting API failure as hardness.

| preset | seed | model | solved | why |
|---|---:|---|---|---|
| easy | 775365020 | OpenAI GPT-5.6 Terra | error | HTTP 403 key limit |
| easy | 1794220179 | OpenAI GPT-5.6 Terra | error | HTTP 403 key limit |
| easy | 1580483517 | Google Gemini 3.8 Flash | error | HTTP 403 key limit |
| easy | 540271021 | OpenAI GPT-5.6 Terra | error | HTTP 403 key limit; harness aborted |

## G9 arms

| arm | preset | seeds | valid solved/attempts | provider errors |
|---|---|---|---:|---:|
| bare | easy | 775365020, 1794220179, 1580483517, 540271021 | 0/0 | 4 |
| structural hint | hard | 239961674, 107385593, 1928942996, 687315165 | 0/0 | 4 |
| placebo hint | hard | 497404828, 143457290, 1733420638, 395055992 | 0/0 | 4 |

Hinted minus placebo is unavailable. No conclusion about the claimed intuition
can be drawn until these arms run successfully.

## Use

```python
import gen_2310_15909 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY["demo"])
statement = g.render(inst)
ok, reason = g.verify(inst, inst["answer"])
assert (ok, reason) == (True, "ok")
```

From the repository root, after successful oracle reruns and updating
`G9_EVIDENCE`:

```bash
scripts/emit.sh 2310.15909 20 hard
```

## Caveats

The quartic structure is generator-specific, not a theorem of the paper; the
paper supplies the parity obstruction that makes the certificate sound. A
tool-enabled solver finds the partition quickly, which is why this is Track B.
The 0/200,000 estimate is relative to uniformly random exact-size ordered
partitions with both anchors already placed in `V0`; it is not a probability
under every solver prior and does not establish complexity-theoretic hardness.
The attack panel includes a standard-library DPLL baseline with unit and
cardinality propagation, but not an industrial SAT/SMT or CP solver; it also
reports the faster distribution-specific character algorithm. Sparse edge
thinning may admit certificates unrelated to the planted cosets. At medium and
hard there are fewer retained edges than an STS would require, so nonexistence
itself is also visible by edge count; the graded object is specifically the
paper's executable four-part parity certificate. Exact hypergraph isomorphism is
not attempted; `canonical_key` normalizes all public coordinate symmetries and
input relabellings used by this family, but an accidental isomorphism outside
that group could survive as a distinct key. Finally, no
LLM-hardness claim is currently justified: rerun the three official harness
arms once OpenRouter quota is restored, inspect replies for parser bugs, update
`G9_EVIDENCE`, rerun `selftest()`, and only then treat `hard` as shipped.
