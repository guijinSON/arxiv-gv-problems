# Frozen token placements from *Token Sliding on Chordal Graphs*

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate | integer tuple representing an independent set |
| Intended intuition | change of variables |
| Domain essentiality | native |
| Reduction | paper-licensed: Section 2, Theorem 5 |

This generator asks for a frozen placement of tokens in a split graph. A split
graph is given by its clique, its independent side, and every cross-neighborhood;
a placement is frozen if no token can slide along an edge while preserving
independence. The answer is the special vertex followed by twelve eligible
independent-side vertices. Checking it requires only exact membership and
neighbor-count operations. The family comes from Bonamy and Bousquet,
[*Token Sliding on Chordal Graphs*](https://arxiv.org/abs/1605.00442), especially
the frozen/blocking-set observation and Theorem 5 in Section 2.

## Why the construction and certificate are trustworthy

Generation is inverse, not search. The module first samples a size-`k` set and
builds an exactly regular base graph in which that set dominates every vertex.
It then applies the paper's Theorem 5 construction: the corresponding
independent-side vertices, together with `w_special`, form a frozen
`(k+1)`-token placement. Every base-clique vertex sees the special token and at
least one selected dominating vertex, while every gadget-clique vertex sees
zero selected vertices; consequently no clique vertex has exactly one selected
neighbor and no slide is legal.

`verify` never reads `inst["answer"]`. It accepts every normalized requested-form
placement that is genuinely frozen. The base graph is regular, making both
candidate degree and total neighborhood-overlap identical, so the planted set
does not have a per-vertex degree signature.

## Hardness claim: Track B

This is not a Track A claim. Theorem 5 proves worst-case co-NP-hardness (and
Corollary 6 co-W[2]-hardness parameterized by token count) for connectivity of
the token-sliding graph on split graphs; it does not prove this generated
distribution hard. Moreover, Section 3, Procedures 1 and 2 and Theorem 3 give a
polynomial-time method for pairwise reachability on interval graphs. That result
rules out the prior-triage idea of treating a planted interval-graph slide
sequence as structurally hard. The proof of Lemma 4 also treats dominating-set
sizes `k<=3` as polynomial-time cases; the demo uses `k=4` and shipping uses
`k=12`, with `n>k` throughout.

For this generated distribution, an efficient algorithm is deliberately
public: exact GF(2) Gaussian elimination recovers the unique decoder word, then
parity classifies the eligible vertices. Its complexity is
`O(r*b^2 + n*b)` bit operations. At the shipping preset it solved 8/8 fixed
test seeds with a median 790,570 counted bit operations and 0.002948 seconds.
The compact route notices that, relative to the displayed mask `O`, the
informative rows are the complete weight-one affine basis. It recovers one key
bit per row and classifies the annotations in 251 packed XOR/parity operations.
That is below the no-tool cap but is still a substantial amount of exact
hexadecimal bookkeeping without a sandbox or calculator.

## Worked demo (seed 0)

This is the complete output of
`render(make_instance(seed=0, **DIFFICULTY["demo"]))`:

```text
FROZEN TOKEN PLACEMENT IN A SPLIT GRAPH

A split graph has a clique K (every two vertices of K are adjacent) and
an independent side S (no two vertices of S are adjacent). Its remaining
edges run between K and S and are listed below.

A token placement is an independent set of occupied vertices. A legal token
slide replaces one occupied vertex x by an unoccupied neighbor y, provided
the occupied vertices after the replacement are still independent. A
placement is frozen when no legal token slide exists.

There are 43 vertices, numbered 0 through 42.
K = 4 8 9 10 11 13 14 16 17 18 20 24 26 27 29 30 31 32 33 35 39
S = 0 1 2 3 5 6 7 12 15 19 21 22 23 25 28 34 36 37 38 40 41 42

For each vertex of K, the following row gives all of its neighbors in S.
There are no cross-edges other than those listed:
  4: 1 3 5 6 15 37 41 42
  8: 36
  9: 0 1 2 5 15 19 37 41
  10: 0 1 3 19 21 23 41 42
  11: 1 2 3 5 19 21 28 34
  13: 12
  14: 0 1 2 5 21 22 25 42
  16: 1 3 5 21 25 28 34 41
  17: 40
  18: 1 2 6 22 23 25 37 42
  20: 0 1 3 6 19 37 41 42
  24: 0 1 5 6 15 21 22 23
  26: 0 1 5 15 22 28 34 37
  27: 1 2 15 22 25 34 41 42
  29: 7
  30: 1 2 3 19 22 25 28 42
  31: 1 2 6 15 23 28 37 41
  32: 1 3 6 23 25 28 34 37
  33: 1 6 15 19 21 23 25 34
  35: 38
  39: 0 1 19 21 22 23 28 34

Your placement must contain the following displayed special vertex:
  special = 1
It must also contain exactly 4 vertices from this eligible set:
  eligible = 0 2 3 5 6 15 19 21 22 23 25 28 34 37 41 42
The other vertices of S are not eligible for the requested certificate.

Auxiliary exact decoder data are supplied to help find such a placement.
Every mask is a 8-bit hexadecimal integer; bit 0 is the least
significant bit. For an unknown promised unique word X, each row
'mask | rhs' means parity(mask AND X)=rhs over GF(2), where parity is
the number of 1-bits modulo 2. XOR is addition over GF(2).
The distinguished public mask is O = 57.
Decoder rows:
  5f | 1
  77 | 0
  57 | 0
  56 | 0
  55 | 0
  53 | 0
  47 | 1
  d7 | 1
  17 | 1

Each eligible vertex v has an annotation a(v). The promised frozen
placement consists of special together with exactly those eligible
vertices for which parity(a(v) AND X)=0. The checker does not require
this decoder route: it accepts every requested-format frozen placement.
Annotations (vertex : mask):
  0: 7a
  2: 3d
  3: 0a
  5: 2d
  6: 65
  15: 09
  19: bb
  21: 45
  22: 26
  23: 0c
  25: db
  28: 9e
  34: 5c
  37: ef
  41: 85
  42: b7

Output exactly 5 decimal vertex identifiers. The
special vertex must be first. The remaining eligible identifiers must
be distinct and in strictly increasing order. Order otherwise has no
meaning; repetitions are forbidden; all displayed sets and bounds are
inclusive; vertex numbering is 0-based.

Give your final answer inside <answer></answer> tags, as comma-separated
decimal integers.
Example format: <answer>17, 3, 29, 41</answer>
Output nothing else inside the tags.
```

The planted answer is `[1, 2, 22, 25, 42]` and verifies as `(True, "ok")`.
Dropping the last entry gives `[1, 2, 22, 25]`, which verifies as
`(False, "answer must contain exactly 5 vertices")`. A person can solve the
demo on paper: it has an 8-bit decoder and sixteen annotations, although its
443 valid placements mean the displayed planted answer is not unique.

## Difficulty presets

| preset | base vertices | token answer | base degree | decoder bits | decoy rows | status |
|---|---:|---:|---:|---:|---:|---|
| demo | 16 | 5 | 6 | 8 | 0 | hand-scale illustration |
| easy | 120 | 13 | 12 | 96 | 48 | oracle solved; not shipped |
| medium | 144 | 13 | 14 | 104 | 96 | **shipping; hardened** |
| hard | 168 | 13 | 16 | 112 | 192 | retained above shipping |

The ladder grows the split graph and decoder while keeping the answer at
thirteen labels. `escalate` first adds decoder decoys without changing the
witness, then can enlarge the regular base graph.

## Gate results

| gate | measured result at medium shipping unless stated otherwise |
|---|---|
| G1 | 12/12 planted checks passed across all four presets; answers JSON-round-trip |
| G2 | empty, dropped, duplicate, unknown, missing-special, and one-element replacement corruptions rejected with six distinct reasons |
| G3 | realistic prose/fence/tag response parsed; 13 labels recovered |
| G4 | 0/200,000 structure-aware random candidates valid; candidate space `C(144,12)=103,619,293,824,707,388` |
| G5 | shipping density 0/200,000; demo exact valid count 443; bounded DPLL median 200,000 nodes / 3.238257 s |
| G6 | five attacks each 0/8; Gaussian reference decoder 8/8 as expected |
| G7 | doubled 288-base-vertex instance built and its planted witness verified |
| G8 | 20/20 relabelling invariance, 20/20 carried witnesses, and 20/20 unrelated keys distinct |
| G9 | 65 worst-case characters, about 17 tokens, 13 atoms, 251 intended packed operations; hinted verdict hardened |

The five failing attacks were regular-degree/overlap outliers, greedy maximum
coverage, 512 uniform restarts, treating shuffled RHS order as key order, and a
200,000-node bounded set-cover DPLL. The successful exact elimination algorithm
is correctly reported under `reference_algorithm`, not as a failing Track B
attack.

## Bare oracle loop

Error rows are shown because they are part of the audit trail, but the harness
did not count them as failed solvers.

| round / preset | model | seed | result | exact outcome |
|---|---|---:|---|---|
| 0 / easy | OpenAI GPT-5.6 Terra | 279193011 | failed | parsed; token 255 can slide to 264 |
| 0 / easy | Anthropic Claude Sonnet 5 | 205659790 | failed | empty length-limited response |
| 0 / easy | xAI Grok 4.6 | 1425257734 | error | 900-second hard deadline; redrawn |
| 0 / easy | xAI Grok 4.6 | 1552748732 | **solved** | valid frozen placement; caused escalation |
| 1 / medium | xAI Grok 4.6 | 1065379703 | error | 900-second hard deadline; redrawn |
| 1 / medium | xAI Grok 4.6 | 1108242607 | failed | parsed; token 9 can slide to 158 |
| 1 / medium | Anthropic Claude Sonnet 5 | 370792128 | failed | empty length-limited response |
| 1 / medium | Google Gemini 3.1 Pro Preview | 1893454339 | failed | parsed; token 212 can slide to 288 |

The harness verdict was `hardened` at `medium` after one escalation.

## G9 arms

Only the three shipping-preset attempts in each transcript are counted here.

| arm | solved / attempts | conclusion |
|---|---:|---|
| bare | 0 / 3 | medium hardened |
| structural hint | 0 / 3 | medium hardened; gated G9(b) passes |
| placebo hint | 1 / 3 | one vendor recovered a valid placement |

Hinted minus placebo is `-1/3`. With only three trials per arm, this is not a
stable effect-size estimate, but it provides no evidence that naming the affine
basis made the task easier; the placebo sentence happened to accompany one
successful Grok run. The answer has at most 65 serialized characters,
approximately 17 tokens, and 13 atomic elements. The intended route uses 251 packed XOR/parity
operations. The generic placebo harness began one escalated round after its
shipping success; that irrelevant extra round was interrupted, and the exact
four-row transcript is retained rather than rewritten by hand.

## Use

```python
import random
import gen_1605_00442 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=123, **params)
statement = g.render(inst)
wire = "<answer>" + ", ".join(map(str, inst["answer"])) + "</answer>"
candidate = g.parse_answer(wire)
assert g.verify(inst, candidate) == (True, "ok")
assert g.random_candidate(inst, random.Random(1)) is not None
```

From the repository root, emit samples with:

```bash
bash scripts/emit.sh 1605.00442 20
```

The module uses only the Python standard library and performs no file or network
I/O during import.

## Caveats

The public GF(2) decoder is auxiliary benchmark structure, not an object from
the paper. It makes the generated distribution efficiently solvable and is why
the family is Track B; removing it would change the hardness claim. Conversely,
revealing the decoded word would make the task trivial. The paper's co-NP-hard
and co-W[2]-hard results are worst-case results and are not evidence that this
regular planted distribution is Track-A hard.

The 0/200,000 estimate samples uniformly from the exact declared language:
special plus a uniformly random 12-subset of the 144 eligible vertices. It does
not bound decoder-aware, spectral, LP/ILP, or learned priors. A bounded
set-cover DPLL was tested, but industrial ILP/CP-SAT, spectral community
recovery, and unbounded exact search were not. Exact regularity removes degree
and aggregate-overlap outliers, but higher-order statistics may still reveal
the planted dominating set.

The canonical key uses role-aware Weisfeiler-Leman refinement plus invariant
degree, overlap, annotation, and decoder summaries. It passed all required
relabellings and separated 20/20 unrelated instances, but it is not a complete
split-graph isomorphism test and pathological collisions remain possible. Two
bare/hinted Sonnet attempts emitted no final answer after consuming their token
budget; the transcripts expose those limitations rather than disguising them as
incorrect mathematical work.
