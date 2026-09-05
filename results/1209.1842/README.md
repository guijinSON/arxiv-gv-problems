# Binary-matrix alternatives from arXiv:1209.1842

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | other (binary-matrix dichotomy) |
| Certificate form | exact symbolic A/B word |
| Intended intuition | invariant: audit-word XOR plus complement-transpose |
| Domain essentiality | native |
| Reduction | none |

This generator turns Proposition 3 of Choudhary, Margulies, and Hicks,
[*A Note on Integer Domination of Cartesian Product Graphs*](https://arxiv.org/abs/1209.1842),
into an exact witness task.  The solver receives explicit binary root matrices and
exact row/column or complement-transpose definitions of all other matrices.  For
each matrix it must say either **A** (“every column contains a 1”) or **B** (“every
row contains a 0”).  Proposition 3 says at least one alternative always holds; the
generator makes exactly one hold.  Checking a word requires bit inspection at the
roots and exact propagation through the defining forest.  `verify` never reads the
planted answer.

## Why the Track B claim is honest

Section 2, Proposition 3 also identifies the efficient algorithm that rules out
Track A: inspect every root matrix, decide A/B, and propagate each exact transform.
At the shipping preset this is `O(roots * matrix_size^2 + n)` under scalar bit
inspection, or `O(roots * matrix_size + n)` with packed rows.  It measured **205,008
bit/edge operations**, **2,768 packed-word/edge operations**, and **0.00037241 s**
median over eight seeds.  The compact construction-specific route XORs the 32 audit
words, reads its 32 root bits, and propagates 208 relations: **271 exact operations**
and **0.00012492 s**.  The benchmark asks whether a no-tool solver discovers and
executes that compression; it makes no complexity-theoretic hardness claim.

The definition work came from Section 1 (finite graphs, multisets, closed
neighborhoods, and integer domination), while Proposition 3 is the binary-matrix
lemma actually used in the proof of Theorem 1.  A direct planted dominating-set
attempt was not shipped: balancing its vertex degrees introduced an exact spectral
linear relation, so a Track A claim would have been false, and removing that relation
left no sub-300-operation intended route.

## Worked demo

The demo is hand-solvable: inspect the three 8×8 roots, use that P preserves an
alternative and F (complement-transpose) swaps it, and fill the five descendants.
Here is the complete rendering for seed 5.

```text
BINARY-MATRIX ALTERNATIVE CERTIFICATE

A binary matrix has entries only in {0,1}.  For every matrix M, label:
  A  when every column of M contains at least one 1;
  B  when every row of M contains at least one 0.
The instance promises that every matrix below satisfies exactly one of A
and B.  You must label every matrix with its valid alternative.

There are n=8 matrices, numbered 0 through 7.
Every matrix has 8 rows and 8 columns.
Some root matrices are displayed explicitly.  Each row is one fixed-width
hexadecimal binary word.  Column 0 is its least significant bit and column
7 is its most significant bit; leading zeroes are significant.

ROOT MATRICES
root 4:
  00: 8b
  01: 1a
  02: 92
  03: 3f
  04: ff
  05: bb
  06: 37
  07: 68
root 6:
  00: 2c
  01: e8
  02: dc
  03: c4
  04: 61
  05: 28
  06: c1
  07: cc
root 5:
  00: 22
  01: 9e
  02: 9e
  03: 70
  04: 20
  05: 20
  06: 00
  07: f8

Every non-root has one defining relation.  A P relation
  child parent P a b
means M_child[r,c] = M_parent[(r+a) mod m,(c+b) mod m].
An F relation
  child parent F a b
means M_child[r,c] = 1-M_parent[(c+b) mod m,(r+a) mod m].
Here m is the common matrix size.  Thus these equations define every
entry of every non-root exactly; the relation lines form a forest.
Row and column indices are 0-based, and all displayed bounds are inclusive.

RELATIONS (child parent kind row_shift column_shift)
1 4 F 6 2
2 5 F 3 3
0 6 F 1 5
3 4 P 2 2
7 6 P 6 4

The following 32-bit hexadecimal audit words are auxiliary instance data.
They impose no extra validity condition beyond the matrices just defined.
AUDIT WORDS
bde5c099 383f9f5b 4164d839 9f767c45

Output one word of exactly 8 uppercase letters in matrix-number
order: character i must be A or B and labels matrix i.  Do not insert
spaces, commas, quotes, or a prefix; order matters and repetitions are allowed.
Give your final answer inside <answer></answer> tags.
Example format: <answer>ABBABA</answer>
Output nothing else inside the tags.
```

The answer is `<answer>ABAAABBB</answer>` and
`verify(inst, "ABAAABBB") == (True, "ok")`.  Flipping its first character gives
`BBAAABBB`, rejected as `matrix 0 contradicts its F relation`.

## Difficulty presets

| preset | matrices `n` | roots | root size | independent search space | status |
|---|---:|---:|---:|---:|---|
| demo | 8 | 3 | 8×8 | 2³ | hand example |
| easy | 160 | 24 | 40×40 | 2²⁴ | a precursor at these parameters was solved by Grok |
| medium | 240 | 32 | 64×64 | 2³² | bare held, but Grok solved the structural-hint arm |
| hard | 240 | 32 | 80×80 | 2³² | **ships; bare and hinted both held** |

The move from medium to hard grows the matrix haystack while leaving the
240-letter witness and 271-operation intended route unchanged.  This was the single
G9(b)-permitted escalation.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verify; 12/12 JSON round-trips |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | realistic fenced/prose response round-trips; garbage returns `None` |
| G4 | 0/200,000 hits; exact structure-aware probability 2⁻³² = 2.3283064365e-10 |
| G5 | exactly one valid forest-consistent word; 4,096-restart baseline failed in 0.589218 s |
| G6 | five attacks × eight seeds: 0 successes; reference and compact algorithms 8/8 |
| G7 | doubled case (480 matrices, 160×160 roots) verifies; defined bits grow 8× |
| G8 | 80/80 invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9 | 242 serialized chars, 240 atoms, about 61 tokens; intended route 271 operations |

## Shipping oracle loop

| model | seed | solved | exact outcome |
|---|---:|---:|---|
| Claude Sonnet 5 | 61,825,073 | no | exhausted the 32k completion/reasoning budget with no answer |
| Gemini 3.1 Pro Preview | 982,892,305 | no | answer too short |
| Grok 4.6 | 1,282,226,365 | no | answer too long |

The Claude record is a length-limited empty response, which the harness explicitly
counts as unsolved rather than as an API error.  The other two are concrete malformed
witnesses.  This distinction is preserved in `llm_loop_transcript.jsonl`.

## G9 arms

| arm | solved / attempts | conclusion |
|---|---:|---|
| bare | 0 / 3 | shipping prompt held |
| structural hint | 0 / 3 | polarity-flipped gate held |
| placebo hint | 0 / 3 | diagnostic control also held |

Hinted minus placebo is **0.0**.  At the final preset the named XOR invariant bought
no observed solves, so this three-call diagnostic does not establish that the oracle
pool is responsive to the claimed intuition.  It did matter one rung lower: Grok
solved the hinted 64×64 version, which forced the sole allowed escalation.

## Use

```python
import random
import gen_1209_1842 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=12345, **params)
question = g.render(inst)
candidate = g.parse_answer("<answer>" + inst["answer"] + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
assert g.search_space(inst) == 2 ** 32
sample = g.random_candidate(inst, random.Random(7))
```

From the repository root, emit records with:

```bash
bash scripts/emit.sh 1209.1842 20 hard
```

## Caveats

This is native coverage of the binary matrices in the paper's proof, not a generator
of Cartesian-product graphs or minimum k-dominating multisets.  The audit-word XOR is
a generator-added correlation; Proposition 3 licenses the alternatives and their
verification, not that checksum.  The 2⁻³² density is exact only for the
forest-consistent prior sampled by `random_candidate`; it does not model a solver
that has already discovered the checksum.  The canonical key uses sorted row/column
sum signatures rather than solving full bipartite matrix isomorphism, so adversarial
collisions are possible.  We did not run a SAT/SMT encoding or a GPU/vectorized bit
scanner; the disclosed reference scan already demonstrates that tools make the task
easy.  Finally, the shipping prompt is about 48k tokens, and one bare plus one placebo
oracle consumed its whole 32k reasoning/output allowance without emitting text; the
remaining concrete failures and all three hinted failures prevent the hardness claim
from resting solely on that budget effect, but prompt scale is still part of what the
benchmark measures.
