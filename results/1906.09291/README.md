# Verified generator for arXiv:1906.09291

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite field |
| Computational core | graph |
| Certificate | integer tuple `[row,v0,v1,v2,v3]` |
| Intended intuition | change of variables |
| Domain essentiality | native |
| Reduction | none |

This module turns Adrián Vázquez-Ávila’s [“A note on two orthogonal totally
`C4`-free one-factorizations of complete graphs”](https://arxiv.org/abs/1906.09291)
into a cycle-witness problem. The solver receives several independent pairs of
one-factors of `K_(q+1)`, represented exactly by the paper’s quadratic-residue
starter maps over `F_q`. Exactly one pair contains a four-cycle; the required
witness is its row and four vertices in alternating factor order. Verification
performs four exact mate-map evaluations and a distinctness check. It never reads
the planted answer and uses no floating point.

## Why it can be trusted

Generation reverses case (ii) in the proof of Lemma 2.1. It samples a
nonresidue `beta` and a square `a`, then sets

`i = a*beta*(beta+1)/(beta-1)`.

The four vertices displayed by that case then close by construction. A random
square scale and translation hide their coordinates, and the rows are shuffled.
Every decoy chooses `beta` in Lemma 2.1’s sufficient regime, so the lemma—not a
cycle search—guarantees its translated one-factors are `C4`-free. The eight sign
cases in the same proof give a constant-size exact exhaustion; on the measured
shipping instance they certify one geometric cycle, represented by four valid
ordered answers.

## Why Track B, not Track A

Section 1 defines starters and translated one-factors; Proposition 1.4 gives
`S_beta`, Lemma 2.1 gives the `C4`-free character test, and Theorem 2.7 explicitly
constructs the paper’s totally `C4`-free pair. These are constructive results,
not search-hardness theorems. A Step 0 scan at the prime `q=1,000,003` found
375,034 members of Theorem 2.7’s displayed set `M` among 1,000,002 nonzero
elements—about 37.5%, or about 75% after the obvious nonresidue restriction.
Asking merely for such a parameter would therefore fail G4 badly.

The disclosed reference algorithm builds the quadratic-residue table and
traverses the alternating-cycle decomposition. It is exact, runs in `O(rq)`
time and `O(q)` memory, and solved 8/8 shipping instances in a median **1.897647
seconds**, using **18,376,459 counted operations**. Centering each row at its two
matching centers exposes the two character-selected linear branches from Lemma
2.1; that compact route solved 8/8 in **265 exact modular operations** and about
`2.11e-5` seconds. The benchmark claim is only that a no-tool solver must discover
that coordinate change and accurately execute the large-prime character tests.

## Worked demo

The `demo` preset with seed 0 is hand-solvable. Its complete rendered instance is:

~~~text
FOUR-CYCLE IN FINITE-FIELD ONE-FACTORS

Work in the prime field F_19, represented by 0,...,18, with all
finite arithmetic reduced modulo p. A nonzero field element x is a
quadratic residue when x=y^2 for some nonzero y; otherwise it is a
quadratic nonresidue. The extra vertex infinity is encoded by the integer
p itself, namely 19. Thus every vertex label is an integer in 0..19.

Each input row is an independent labeled copy of this vertex set and
defines two one-factors (perfect matchings), A and B. For a center c and
the row's nonresidue beta, define mate(c,x) as follows:
  * mate(c,infinity)=c and mate(c,c)=infinity;
  * otherwise put d=x-c modulo p. If d is a quadratic residue,
    mate(c,x)=c+beta*d; if d is a nonresidue,
    mate(c,x)=c+beta^(-1)*d, always modulo p.
Factor A joins every x to mate(center_A,x), and factor B uses center_B.
The formula is involutive, so each undirected edge is listed twice by the
mate map but belongs only once to the matching.

Exactly one row is promised to contain a four-cycle in A union B. Find any
such cycle. If your answer is [r,v0,v1,v2,v3], the five integers must obey
mate(A,v0)=v1, mate(B,v1)=v2, mate(A,v2)=v3, mate(B,v3)=v0, and the four
vertices must be distinct. Rows are 0-based; order and orientation matter
only through this stated A,B,A,B convention. No repeated vertex is allowed.

Rows (row center_A center_B beta):
  0 11 18 15
  1 5 6 3

Give your final answer inside <answer></answer> tags as one JSON list of
exactly five base-10 integers [r,v0,v1,v2,v3].
Example format: <answer>[0, 0, 1, 2, 19]</answer>
Output nothing else inside the tags.
~~~

The answer is `<answer>[0,16,10,12,7]</answer>`.

~~~python
>>> verify(demo, [0, 16, 10, 12, 7])
(True, 'ok')
>>> verify(demo, [0, 16, 12, 10, 7])
(False, 'vertices 0-1 are not an edge of factor A')
~~~

A person can list the ten squares modulo 19 and follow both mate maps on paper;
the exact enumerator confirms four ordered encodings of the same cycle.

## Difficulty presets

| Preset | Lower bound on `q` | Rows | Minimum structured space | Status |
|---|---:|---:|---:|---|
| demo | 19 | 2 | 40 | hand-solvable illustration |
| easy | 1,200,007 | 6 | 7,200,048 | **ships; bare and hinted hardened** |
| medium | 2,400,019 | 6 | 14,400,120 | available |
| hard | 5,000,003 | 6 | 30,000,024 | available |

An earlier ladder held at `q>=200,003`, but its structured answer space did not
meet G4’s strict threshold. The ladder was moved upward and the bare loop was
rerun; the retained transcript is only the final, G4-compliant run.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 preset–seed plants verify; 12/12 JSON round trips |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | fenced realistic response round-trips; garbage returns `None` |
| G4 | pass | exact `4/7,206,672 = 5.5504e-7`; sampled 0/200,000 |
| G5 | pass | shipping exact count 4; 4,096-restart baseline failed in 0.054521 s |
| G6 | pass | five attacks each 0/8; traversal and compact reference both 8/8 |
| G7 | pass | doubled prime builds, verifies, and raises space to 14,797,584 |
| G8 | pass | 80/80 composed-symmetry witness/key checks; 20/20 keys distinct |
| G9 | pass | hinted 0/3; 35 chars, 9 tokens, 5 atoms; 265 operations |

## Oracle loop

| Preset | Model | Seed | Solved | Exact outcome |
|---|---|---:|---|---|
| easy | OpenAI GPT-5.6 Terra | 28,949,997 | no | edge 0–1 was not in factor A |
| easy | Google Gemini 3.1 Pro | 637,873,649 | no | edge 0–1 was not in factor A |
| easy | Anthropic Claude Sonnet 5 | 1,481,067,096 | no | exhausted 32,000 tokens without a witness |

The script-owned verdict is **hardened with zero escalations**. Full replies,
timings, status codes, and finish reasons are in `llm_loop_transcript.jsonl`.

## G9 arms

| Arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/3 | hardened |
| placebo hint | 0/3 | hardened |

Hinted minus placebo is **0.0**. In this small diagnostic, merely naming the
centered branch structure did not help relative to a content-free sentence; the
remaining obstacle was deriving the correct branch equation and exact arithmetic.
The largest answer observed over 201 shipping instances was 35 characters, about
9 tokens and 5 atomic elements. The intended route uses 265 exact operations.

## Use

~~~python
from gen_1906_09291 import DIFFICULTY, make_instance, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["easy"])
candidate = parse_answer("<answer>[0,1,2,3,4]</answer>")
ok, reason = verify(inst, candidate)
~~~

From the repository root:

~~~bash
bash scripts/emit.sh 1906.09291 20
~~~

The module uses only the Python standard library; `gvlib` is unnecessary for
prime-field character and edge-membership checks.

## Caveats

- This is not Track A evidence and not a claim that finding one-factorizations is
  hard. Both the `O(rq)` traversal and the 265-operation planted-distribution
  shortcut are public and successful.
- The family uses the paper’s native starter-generated one-factors, but asks for a
  `C4` witness in a reversed Lemma 2.1 instance. It does not ask the solver to emit
  the paper’s quadratic-size pair of complete factorizations. Batching independent
  rows supplies crowding while preserving the native objects.
- `P(guess)` is uniform over the exact statement-aware language: choose a row and
  first vertex, then follow the three forced alternating edges. It does not model
  a solver that already knows the reversed case-(ii) generator prior.
- The adversary panel tried beta magnitude, center-gap greediness, 4,096 random
  starts, the infinity component, and a midpoint ansatz. It did not try a CAS,
  vectorized exhaustive search, or arbitrary graph-isomorphism software.
- One bare, one hinted, and one placebo Claude call ended at the 32,000-token
  response limit. The harness counts an empty length-limited response as unsolved;
  the other six G9 calls produced parseable wrong witnesses.
- The canonical key is exact for the declared independent-row symmetries: affine
  relabeling, factor swap, beta inversion, and row reordering. It is not a complete
  canonical form under every abstract isomorphism of the resulting union graphs.
