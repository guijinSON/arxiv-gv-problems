# Projective-cycle Path Set Packing

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| native domain | combinatorics |
| object regime | finite field |
| computational core | graph |
| certificate form | matrix certificate: a normalized `2×2` matrix over `GF(q)` |
| intended intuition | symmetry — two alternating classes of one incidence cycle are projective-linear maps |
| domain essentiality | native |
| reduction | none |

This is a generator for N.R. Aravind and Roopam Saxena, [“Parameterized
Complexity of Path Set Packing”](https://arxiv.org/abs/2209.08757). The solver
receives the paper’s native objects: an undirected star and explicitly listed
simple paths in it. It must give a matrix whose projective action selects
`q+1` listed paths. The checker expands the matrix, looks up every selected
path, and scans the actual star edges for collisions using exact integer
arithmetic. It never reads `inst["answer"]`.

Trust status: the nine local construction/checking gates pass, but this family
is **rejected on H/Track B**. In the live bare hardening run, every scored
attempt solved: 3/3 at each of `q=1009`, `q=2003`, and `q=4001`. The automatic
`q=8009` level could not be scored because the external key then reached its
limit. API errors are not model failures, and there is no `hardened` verdict.

## What the family is

The star has centre `C`, left leaves `L_x`, and right leaves `R_y`, where
`x,y` range over the projective line `P¹(F_q)`. A candidate path `(x,y)` is
`L_x--C--R_y`; a set of such paths is edge-disjoint exactly when no left or
right label repeats.

The generator composes two known projective permutations. Their relative map
is a Singer cycle of length `q+1`, so their union is one even incidence cycle.
Each alternating edge class is a perfect packing. Independent projective
changes of coordinates and a random path order hide both classes symmetrically.
The planted matrix is computed before the paths are emitted—generation never
runs matching or solves its own instance. Two distinct projective maps can
agree at at most two points, so for `q≥5` no third map can choose its `q+1`
values from the union; every instance has exactly two valid certificates.

## Why Track B

This cannot honestly be Track A. Section 1.1 explicitly says Path Set Packing
is polynomial-time solvable when the host is a tree. Section 5.1 restates the
polynomial EPT independent-set routine, and its forest corollary computes a
maximum path packing in polynomial time. On this star, the direct reference is
augmenting-path bipartite matching followed by interpolation of the selected
projective map. Its complexity is `O(VE)` plus exact evaluation; at shipping
`q=1009`, eight runs averaged **16,241 counted edge/field operations and 0.0026
seconds**, solving 8/8 as expected. In this count, an adjacency or queue action
and an exact `GF(q)` field operation each cost one; a field inversion is one
field operation.

The compact route recognizes the one even cycle, follows five incident edges,
takes three correspondences of one parity, and solves their `3×4` homogeneous
system. Three projective correspondences determine the normalized matrix. The
conservative count is **92 exact operations** after the symmetry is seen,
independent of `q`. Without that insight, processing the 2,020-path table is
mechanical matching work that the no-tool model cannot delegate to a solver.

The paper’s genuine hard regimes are not being borrowed dishonestly. Theorem 1
is W[1]-hard for vertex-cover number; its Section 3 reduction asks for
`k(n−1)+C(k,2)` paths. Theorem 2 is W[1]-hard for pathwidth plus maximum degree
plus solution size; its Section 4 reduction asks for `k+C(k,2)` paths. These
are worst-case parameterized results, not distributional hardness theorems for
a planted generator. Theorem 3 (feedback-vertex number plus maximum degree)
and Theorem 5 (treewidth plus maximum degree plus maximum path length) also
identify FPT regimes that a Track A construction would have to avoid.

## Worked demo

This is the complete output of `render(make_instance(n=5, seed=0))`:

```text
Find an exact projective certificate for a Path Set Packing.

Graph and paths.
Let q=5, a prime. The projective labels are 0,1,...,4,INF;
the table encodes INF by the integer 5.
The undirected host graph is a star with centre C and two disjoint
families of leaves L_x and R_y, one leaf for each projective label.
For every table row 'id x y', candidate path id is the simple path
L_x--C--R_y. Path IDs are 0-indexed. Different paths are edge-disjoint
exactly when they repeat neither a left label x nor a right label y.
You need a packing of exactly k=6 candidate paths.

Certificate language.
Output one 2-by-2 matrix [[a,b],[c,d]] over GF(q). Every entry must be
an ordinary decimal integer in 0..4. Its determinant a*d-b*c
must be nonzero modulo q. Matrices differing by a nonzero scalar encode
the same map, so the first nonzero entry in row-major order must be 1.
No other normalization is accepted.

The matrix acts on the projective labels as follows, with all finite
arithmetic modulo q:
  finite x: T(x)=INF if c*x+d=0; otherwise
            T(x)=(a*x+b)*(c*x+d)^(-1) modulo q;
  x=INF:    T(INF)=INF if c=0; otherwise T(INF)=a*c^(-1) modulo q.
Here z^(-1) is the unique residue w with z*w=1 modulo q.

For every projective x, the table must contain the path (x,T(x)).
Those 6 paths are the packing certified by your matrix. The
checker expands the rule, checks table membership, and scans their two
host edges for collisions. Order in the table has no mathematical role,
and candidate paths may not be repeated in a packing.

CANDIDATE_PATHS (id x y)
0 0 1
1 2 5
2 4 4
3 0 3
4 3 1
5 5 3
6 2 2
7 3 5
8 1 0
9 1 2
10 4 0
11 5 4
END_CANDIDATE_PATHS

Give your final answer inside <answer></answer> tags as exactly one JSON
object with key matrix and the normalized 2-by-2 integer array.
Example syntax (only a format example):
<answer>{"matrix":[[1,2],[3,4]]}</answer>
Output nothing else inside the tags.
```

The answer is `<answer>{"matrix":[[1,4],[2,4]]}</answer>`, for which
`verify` returns `(True, "ok")`. Duplicating its first row gives
`{"matrix":[[1,4],[1,4]]}` and returns `(False, "matrix is singular modulo
q")`. A person can solve this demo on paper by drawing the 12-edge incidence
cycle, taking alternating edges, and interpolating over `F_5`.

## Difficulty presets

| preset | q | candidate paths | certificate space | rendered chars, seed 0 | status |
|---|---:|---:|---:|---:|---|
| demo | 5 | 12 | 120 | 1,911 | hand-solvable; hardener skips it |
| easy | 1,009 | 2,020 | 1,027,242,720 | 26,605 | rejected: oracle solved 3/3 |
| medium | 2,003 | 4,008 | 8,036,052,024 | 56,425 | rejected: oracle solved 3/3 |
| hard | 4,001 | 8,004 | 64,048,008,000 | 116,365 | rejected: oracle solved 3/3 |

`escalate()` moves to the next prime above twice `q`. This grows the path
haystack while the answer remains exactly four field elements.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted certificates verify; 12/12 JSON round-trips |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | 3/3 prose/fenced answers parsed; garbage rejected |
| G4 | 0/200,000 structure-aware guesses; exact language size 1,027,242,720 |
| G5 | exact shipping count 2, density `2/1,027,242,720`; demo count 2; reference mean 16,241 operations / 0.0026 s |
| G6 | leaf-frequency, display-greedy, 256-restart, and affine-ansatz attacks each 0/8; reference 8/8 |
| G7 | doubled size at next prime 2,027 verifies; answer stays four atoms |
| G8 | 80/80 invariance and 80/80 carried-witness checks; 20/20 unrelated keys distinct |
| G9 | 31 chars, about 8 tokens, 4 atoms, 92 intended operations; caps pass |

## Oracle loop

| preset | q | scored results | conclusion |
|---|---:|---:|---|
| easy | 1,009 | 3/3 solved | defeated |
| medium | 2,003 | 3/3 solved | defeated |
| hard | 4,001 | 3/3 solved | defeated |
| escalated | 8,009 | 0 scored; 4 API errors | unavailable, not a failure |

The successful rows used GPT-5.6 Terra and Gemini 3.8 Flash; every answer
parsed and verified. There is no hardening verdict and no shipping level. The
full seeds, models, replies, and timings remain in the script-owned transcript.

## G9 arms

| arm | solved / scored attempts | API errors | conclusion |
|---|---:|---:|---|
| bare | 3/3 | 0 | the shipping candidate is easy |
| structural hint | 0/0 | 4 | unavailable |
| placebo hint | 0/0 | 4 | unavailable |

`hinted − placebo` is undefined because neither extra arm produced a scored
attempt. Nothing can be concluded about the hint effect. The bare arm already
rejects the family. The answer and intended route remain within G9(c): 31
characters, four atomic field entries, and 92 exact operations.

## Use

```python
from rejected_gen_2209_08757 import make_instance, parse_answer, render, verify

inst = make_instance(n=5, seed=0)
print(render(inst))
candidate = parse_answer('<answer>{"matrix":[[1,4],[2,4]]}</answer>')
print(verify(inst, candidate))  # (True, "ok")
```

The module is retained for audit and experimentation; do not emit it into the
release corpus. `REJECTED.md` records the disposition.

## Caveats

- This is deliberately an easy tree-host regime and only supports a Track B
  no-tool-compression claim. Any solver with matching code should solve it in
  milliseconds.
- The answer language asks for a projective matrix, not an arbitrary explicit
  list of path IDs. That preserves a four-atom symbolic witness but benchmarks
  recognition of the planted projective structure as well as path packing.
- The G4 prior is uniform over every normalized nonsingular `2×2` matrix, after
  all syntactic and determinant constraints are enforced. Its tiny success
  rate says nothing about nonuniform algebraic or cycle-following strategies.
- All leaves have degree two and both valid alternating classes are symmetric,
  but the family is not intended to resist the standard matching algorithm.
  The panel did not test sophisticated projective-invariant sampling, graph
  neural methods, or an external CAS.
- Canonical equivalence treats projective coordinate changes, side exchange,
  and path reordering as relabellings. Arbitrary permutations of field labels
  are not symmetries because they destroy the stated field operations and
  certificate language.
- Most importantly, the bare diagnostic is decisive in the wrong direction:
  9/9 scored attempts solved across all named presets. The hinted and placebo
  arms remain unavailable because of the later external API quota limit.
