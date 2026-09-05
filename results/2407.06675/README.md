# Rooted loop subdivisions from arXiv:2407.06675

**Status:** all local G1–G9 gates pass, but the required multi-vendor oracle run is
unscored. OpenRouter returned HTTP 403 `Key limit exceeded` on every redraw, so
this result is not yet ready to submit as hardened.

| Profile | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | integer tuple: a rooted directed-cycle sequence |
| Intuition | change of variables: centered inversion exposes translation |
| Domain essentiality | native |
| Reduction | none |

## Problem and trust model

[Zhou and Yan, *Semi-Degree Condition for Arbitrary H-Linked Oriented
Graphs*](https://arxiv.org/abs/2407.06675) define an `H`-subdivision in Section
1 by replacing every arc of a multidigraph with a consistently directed path.
For `H` equal to one vertex with one loop, a prescribed subdivision path is a
directed cycle through the prescribed image of that vertex. The generator asks
for length `n`, hence for a rooted directed Hamilton cycle.

The solver receives the paper's native objects: an oriented tournament, its
prescribed branch vertex, and its prescribed loop-path length. The graph is
given by an exact finite-field arc rule. A submitted list is checked for its
shape, rooted closure, exact coverage of all vertices, and every directed arc.
`verify` never reads `inst["answer"]` and accepts any valid rooted Hamilton
cycle.

Generation is by composition of identities. Choosing one element from every
pair `{d,-d}` orients the nonzero differences of `F_p`. Exactly one of `1` and
`-1` is allowed, and repeated addition of that difference visits all field
elements because `p` is prime. The generator carries this known cycle through
centered inversion and a random vertex permutation. It never runs a
Hamilton-cycle solver.

## Why Track B

Track A would be unsupported. Theorem 1.1 is an existence theorem for
sufficiently large oriented graphs; it gives no average-case hardness claim.
Its proof is constructive in structure: Lemma 3.3 uses butterflies and a greedy
segment for short prescribed paths, Lemma 3.8 supplies random partitions,
Definition 4.4 pinches endpoints, and Lemmas 4.3 and 4.5 finish with Hamilton
cycles. Proposition 2.2 also identifies the easy-to-misstate boundary: lengths
below four are excluded because even denser examples can lack a prescribed
3-path.

These generated graphs are tournaments, so the standard constructive Camion
algorithm finds a Hamilton cycle in polynomial time. The implementation
materializes the displayed exact arc rule and grows a directed cycle by vertex
insertion and path splicing. At shipping `n=47`, seed `271828`, it succeeds in
10,787 counted Euclidean/arithmetic/membership or adjacency operations and
0.003929 seconds; over eight seeds it succeeds 8/8 with 86,264 operations in
0.037471 seconds. This successful algorithm is deliberately outside the failing
attack panel.

The compact route notices that the displayed rational expression is
`z_y-z_x` after the substitution `z=1/(x+c)`, with the pole mapped to zero.
Translation by the allowed member of `{1,-1}` then gives the cycle. Including
every Euclidean quotient used for modular inversion, this takes 276 operations
on the reporting instance and at most 278 over the eight attack seeds. The
mechanical algorithm is easy for a computer but not executable in context by
hand; the shorter route fits the 300-operation cap only if the coordinate
change is found.

## Worked demo

For `make_instance(n=7, seed=0)`, the complete rendered instance is:

```text
Find a prescribed rooted loop-subdivision in an oriented graph.

Definitions.  An oriented graph is a directed graph with no loops and with
at most one of u->v and v->u for distinct vertices.  A subdivision of a
one-vertex, one-loop multidigraph replaces that loop by a directed cycle
through the prescribed image of its vertex.  Cycle length means number of
directed arcs.  Here the prescribed length equals the number of graph
vertices, so the requested subdivision is a rooted directed Hamilton cycle.

The graph has 7 vertices, with IDs 0 through 6, inclusive.
All arithmetic below is modulo the prime p=7.
The prescribed root is vertex 3.
The prescribed loop-path length is exactly 7 arcs.

Each vertex ID has one field coordinate x (the order of this table has no
graph-theoretic meaning):
  0:6 1:5 2:1 3:3 4:4 5:2 6:0

The centered-inversion parameter is c=3.
For two distinct coordinates x and y, define Delta(x,y) exactly as follows:
  if x+c = 0 and y+c != 0: Delta(x,y) = inverse(y+c);
  if x+c != 0 and y+c = 0: Delta(x,y) = -inverse(x+c);
  otherwise: Delta(x,y) = (x-y)*inverse((x+c)*(y+c)).
Here inverse(a) is the unique b in {1,...,p-1} with a*b = 1 modulo p;
every displayed equality and zero test in this definition is modulo p.

There is an arc u->v exactly when Delta(x_u,x_v), reduced to 0..p-1,
belongs to this connection set S:
  S = 1 3 5
For every nonzero d, exactly one of d and -d belongs to S, so this rule
does define an oriented tournament.  Every vertex has equal in-degree and
out-degree 3; in particular 8*delta^0 >= 3p-4.

Return a JSON list [v_0,...,v_7] of exactly 8 decimal vertex IDs.
It must have v_0=v_7=3; the entries v_0,...,v_6
must contain every ID 0,...,6 exactly once; and every consecutive
pair must be an arc in the displayed direction.  The repeated root is the
only allowed repetition.  Vertex IDs are zero-indexed and no ellipsis is
allowed.

Give your final answer inside <answer></answer> tags, as the JSON list just specified.
Example format: <answer>[3,0,2,1,3]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[3,4,1,2,5,0,6,3]</answer>`.

```python
>>> verify(inst, [3, 4, 1, 2, 5, 0, 6, 3])
(True, 'ok')
>>> verify(inst, [3, 4, 1, 2, 5, 0, 6])
(False, 'wrong length: expected 8 vertex entries')
```

A person can solve this demo on paper: only seven inversions and seven table
lookups are needed after spotting the change of variables.

## Difficulty presets

| Preset | n | Candidate language | Entropy | Answer atoms | Status |
|---|---:|---:|---:|---:|---|
| demo | 7 | `6! = 720` | 9.49 bits | 8 | hand-solvable; 17 exact valid answers |
| easy | 23 | `22!` | 69.93 bits | 24 | first oracle rung; API blocked |
| medium | 37 | `36!` | 138.09 bits | 38 | locally verified |
| **hard** | **47** | **`46!`** | **191.81 bits** | **48** | shipping preset, pending oracle evidence |

Escalation stops with `cap_bound` after `n=47`: the next prime (`53`) pushes
the honestly counted compact route over 300 operations. A Hamiltonian witness
intrinsically grows with the ground set, so there is no fixed-length ambient
axis for this particular one-loop family.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 16/16 preset/seed certificates verify; every answer is JSON-native |
| G2 | pass | 6/6 corruptions rejected with 6 distinct reasons |
| G3 | pass | tagged JSON recovered through prose and a Markdown fence |
| G4 | pass | 0/200,000 structure-aware rooted permutations; `46!` candidates |
| G5 | pass | shipping density sample 0/200,000; demo exact count 17/720; strongest restart attack 0/256 after 527 prefix checks |
| G6 | pass | four attacks each 0/8; reference algorithm 8/8 as expected |
| G7 | pass | doubled-size prime `n=97` builds and verifies; entropy rises to 498.28 bits |
| G8 | pass | 160/160 individual and composed symmetry checks preserve keys and carried witnesses; 20/20 unrelated keys distinct |
| G9(c) | pass | 135 chars, 34 estimated tokens, 48 atoms, 276 intended operations |

## Oracle loop and G9 diagnostics

No row below is a scored attempt: API errors are correctly excluded from the
denominator. The script-generated transcripts are retained for audit.

| Run | Preset | Seeds | Scored solved/attempts | Result |
|---|---|---|---:|---|
| bare | easy | 1147591471, 1220179310, 346987311, 1689950746 | 0/0 | four HTTP 403 quota errors on the current two-vendor pool; harness aborted |
| structural | hard | 625530131, 1148845547, 422115880, 1788923625 | 0/0 | four HTTP 403 quota errors; harness aborted |
| placebo | hard | 1720701565, 977740136, 416006868, 827622751 | 0/0 | four HTTP 403 quota errors; harness aborted |

`hinted - placebo` is therefore undefined, and no conclusion about the value of
the hint is justified. The structural hint names only the centered-inversion
invariant; it does not give the translation step or output procedure.

## Use

```python
import json
import gen_2407_06675 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY["hard"])
question = g.render(inst)
answer = g.parse_answer("<answer>" + json.dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

After a valid bare and two diagnostic oracle runs, emit from the repository root:

```bash
bash scripts/emit.sh 2407.06675 20 hard
```

## Caveats

- This is a Track B benchmark. A computer solves every instance quickly; the
  claim is only that executing the generic route unaided is too large while a
  discoverable coordinate shortcut fits the no-tool budget.
- `0/200,000` samples uniform permutations after enforcing the fixed root,
  repeated endpoint, Hamiltonian coverage, and no-repeat shape. It is not a
  posterior conditioned on recognizing the centered-inversion structure.
- The attack panel covers equal-degree/ID ordering, lowest-ID out-neighbor
  greedy, 256 random restarts, and raw-coordinate translation. It does not run
  an ILP/SAT encoding, spectral ordering, or a full catalogue of tournament
  heuristics. The exact constructive Camion algorithm was run separately.
- Generation conditions away the rare connection-set/numbering draw solved by
  the declared deterministic greedy attacks. This does not search for the
  certificate, but it does define a filtered presentation distribution.
- `canonical_key` normalizes the Cayley connection set under all nonzero field
  scalings and ignores translations and vertex numbering. It is not a complete
  canonical labelling for arbitrary tournament isomorphisms, so rare
  non-affine-isomorphic collisions may be collapsed.
- The theorem's unspecified `n_0` is not invoked to certify these small
  instances. Their cycles verify directly by construction; the graphs do meet
  the theorem's exact numerical loop semi-degree inequality.
- The module is standard-library-only; `gvlib` is unnecessary for this finite
  graph certificate.
- Most importantly, the current OpenRouter quota prevents the required STEP 4
  hardness claim. Re-run all three arms before submission.
