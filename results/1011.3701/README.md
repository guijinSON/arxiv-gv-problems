# arXiv 1011.3701 — parked Track-B generator

**Status: parked, not shippable.** The module is correct and passes G1–G8, but the
authoritative oracle loop returned `budget_bound`: 19 of 21 calls solved the family
through `p=4049`, and `escalate()` could still offer `p=8101`. Under the harness
contract this is neither a ship nor a rejection. G9 was therefore not completed and
no `REJECTED.md` was written.

| profile field | value |
|---|---|
| Track | B (an efficient algorithm is acknowledged) |
| native domain | combinatorics |
| object regime | finite field |
| computational core | graph |
| certificate | matrix certificate (or an explicit permutation below the atom cap) |
| intuition | change of variables: recognize a projective matching preserving cross-ratios |
| domain essentiality | native; no reduction |

## Problem and provenance

The source is Dinitz and Krauthgamer, [*Directed Spanners via Flow-Based Linear
Programs*](https://arxiv.org/abs/1011.3701). Section 1.1 defines the client-server
model: only client arcs impose stretch demands, and a spanner uses server arcs.
Section 5.2 says the directed unit-length 2-spanner rounding extends to the
client-server and augmentation variants.

An instance gives a root, left and right client targets, and candidate server
vertices. Choosing candidate root arcs according to a perfect matching gives every
client arc a server-only two-hop path. The generator first samples a projective
matrix over `F_p`, uses its Möbius permutation as the known matching, and only then
adds edge-disjoint random permutation layers as decoys. The four matrix entries are
therefore known by inverse generation, never by solving the emitted graph. `verify`
expands the matrix (or accepts any explicit perfect matching), checks allowed server
arcs and bijectivity, and recomputes coverage exactly.

## Why this was Track B, and why it was parked

The exact completion has a mechanical polynomial route: Hopcroft–Karp on the
bipartite server-incidence graph, in `O(E sqrt(V))`. At the candidate hard preset,
the self-test solved 8/8 instances using 28,204 incidence-edge scans total and 0.263
seconds. The compact route tries the three choices for each of the rows infinity,
0, and 1, reconstructs a Möbius matrix, and uses row 2 as a filter—at most 228 exact
operations. Theorem 5.2's polynomial `O(log n)` approximation and the paper's stated
`Omega(log n)` hardness for general directed 2-spanner do not establish hardness for
this inverse-planted distribution, so Track A would have been false.

In practice the compact route was too visible: every oracle solved `easy`, `medium`,
`hard`, `p=503`, and `p=1009`; two of three also solved `p=2017` and `p=4049`. Merely
growing the modulus did not hide the four-row recovery. The run exhausted the
script's six-escalation budget while a fixed-size answer could still be generated,
which is exactly the `budget_bound` condition.

## Worked demo (`seed=0`)

The complete rendered instance is:

```text
Find a sparse client-server directed 2-spanner completion.

Definitions.
A directed path follows arc directions, and its length is its number of
unit-length arcs. Client arcs specify demands; a valid client-server
2-spanner uses only server arcs and gives, for each client arc u->v, a
server-only directed path from u to v of length at most 2.

Here p=5 is prime. A projective point is an integer 0 through 5,
inclusive; 5 denotes infinity. The graph has a root r, client target
vertices L_x and R_y for all projective points, and a candidate server
vertex S_(x,y) for every allowed pair (x,y) in the table below.
Its client arcs are r->L_x and r->R_y for every x and y.
For every table pair (x,y), its server arcs are r->S_(x,y),
S_(x,y)->L_x, and S_(x,y)->R_y. There are no other arcs.

The completion template always includes both arcs from every S_(x,y)
to its two targets. Your witness chooses exactly one root arc
r->S_(x,f(x)) for every x. It is valid exactly when every chosen pair
is allowed and f is a permutation: then every L_x and every R_y has a
server-only path of length 2. The completed spanner consequently has
exactly 30 arcs.
Every left and right endpoint occurs in exactly 2 allowed pairs.

Either of these two exact witness formats is accepted:

1. Compact matrix: [[a,b],[c,d]], with entries 0..p-1, determinant
ad-bc nonzero modulo p, and first nonzero row-major entry equal to 1.
It defines f(x)=(a*x+b)/(c*x+d) modulo p. A zero denominator means
infinity; f(infinity)=a/c when c is nonzero and infinity otherwise.
The pair (x,f(x)) must be allowed for every projective point x.

2. Explicit permutation: [y_0,y_1,...,y_5], exactly 6 integers.
Entry x is f(x); entries must be a permutation of 0 through 5,
and (x,f(x)) must be allowed. List order is numeric x order
0,1,...,5, regardless of the printed table's original order.

Allowed server-incidence table (x: allowed y values):
0: 1 4
1: 1 5
2: 3 2
3: 5 0
4: 3 4
5: 0 2

Give your final answer inside <answer></answer> tags as JSON in one accepted format.
Example syntax: <answer>[[1,0],[0,1]]</answer>
Output nothing else inside the tags.
```

The planted answer is `[[1,2],[3,2]]`.
`verify(inst, [[1,2],[3,2]])` returns `(True, "ok")`.
`verify(inst, [])` returns
`(False, "empty answer: expected a matrix or an explicit permutation")`.
A person can solve this six-row demo on paper by finding an allowed perfect matching
or testing the small projective matrix space.

## Difficulty presets

| preset | p | points | degree | candidate servers | client arcs | completed-spanner arcs | outcome |
|---|---:|---:|---:|---:|---:|---:|---|
| demo | 5 | 6 | 2 | 12 | 12 | 30 | hand example |
| easy | 127 | 128 | 3 | 384 | 256 | 896 | oracle 3/3 solved |
| medium | 181 | 182 | 3 | 546 | 364 | 1,274 | oracle 3/3 solved |
| hard | 251 | 252 | 3 | 756 | 504 | 1,764 | oracle 3/3 solved; candidate only, not shipping |

## Gate results

| gate | result | measurement |
|---|---|---|
| G1 | pass | 16/16 planted certificates verified and JSON-round-tripped |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON recovered through prose and a Markdown fence |
| G4 | pass | 0 hits / 200,000 structure-aware guesses at candidate `hard` |
| G5 | pass | random-restart baseline failed after 80,658 checks; demo has 4/840 valid strings |
| G6 | pass | four attacks each 0/8; reference matching 8/8 as expected |
| G7 | pass | `p=251` to `p=503`; answer stayed at four atoms |
| G8 | pass | 60/60 invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9 | **fail/pending** | bare hard was solved 3/3; hinted/placebo arms intentionally not run after park verdict |

The structure-aware G4 prior gives equal mass to normalized projective matrices and
well-formed explicit permutations; it is not a posterior over likely solver
strategies. Zero observed hits only bounds this sampler's density and did not predict
oracle hardness.

## Authoritative oracle loop

| rung | solved / attempts | evidence |
|---|---:|---|
| easy, p=127 | 3/3 | all returned verified matrices |
| medium, p=181 | 3/3 | all returned verified matrices |
| hard, p=251 | 3/3 | all returned verified matrices |
| escalated, p=503 | 3/3 | all returned verified matrices |
| escalated, p=1009 | 3/3 | all returned verified matrices |
| escalated, p=2017 | 2/3 | one matrix failed at server pair `(2,1429)` |
| escalated, p=4049 | 2/3 | one matrix failed at server pair `(2,1938)` |

The bare candidate-hard G9 arm is 3/3 solved. Hinted and placebo arms were not run,
so `hinted_minus_placebo` is unavailable and no claim about hint efficacy is made.
The planted compact answer measured 18 characters, 5 approximate tokens, and 4
atoms; the largest accepted explicit hard answer measured 899 characters, 225 tokens,
and 252 atoms. The intended compact route is bounded at 228 exact operations.

## Use

```python
import gen_1011_3701 as g
inst = g.make_instance(seed=0, **g.DIFFICULTY["demo"])
answer = g.parse_answer("work... <answer>[[1,2],[3,2]]</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

If the family is reactivated and eventually hardens, emission from the repository
root is `bash scripts/emit.sh 1011.3701 20 hard`. Do not emit the present parked
version: `selftest_report.json` deliberately records G9 as failing.

## Caveats

The projective matrix format itself tells a solver the successful ansatz, and three
source-image pairs determine the matrix; this is what made the oracle loop easy. The
canonical key is a strong typed distance-profile fingerprint, not complete bipartite
graph canonization. No ILP or LP relaxation was run beyond exact matching, and no
claim is made that these planted regular incidence graphs inherit the paper's
worst-case hardness. The adversary panel also does not test learned projective-pattern
recognition—the oracle loop did, and it broke the family decisively.
