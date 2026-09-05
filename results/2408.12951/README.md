# Finite-field certificates for b*-coloring (arXiv:2408.12951)

> Status: the generator and all local gates pass, but this result is **not yet
> submission-ready**. The required OpenRouter run made no scored oracle calls:
> every redraw returned HTTP 403 `Key limit exceeded (total limit)`. The
> script-owned error transcripts are retained; they are not hardness evidence.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite field |
| Computational core | graph |
| Certificate form | matrix certificate (a normalized field covector) |
| Intuition | invariant: nonedge differences share one codimension-one subspace |
| Domain essentiality | native |
| Reduction | none |

## The problem

The source is Manouchehr Zaker, [*On z-coloring and b*-coloring of graphs as
improved variants of the b-coloring*](https://arxiv.org/abs/2408.12951). An
instance gives a simple graph through exact nonedge lists and assigns every
vertex a vector over a displayed prime field. The solver returns a normalized
covector. Its dot products with the vertex vectors induce the colors. The
checker expands that coloring and directly checks properness, every b-vertex's
neighborhood colors, and the existence of a nice vertex adjacent to b-vertices
of all other colors.

Generation is inverse: it samples the covector first, constructs affine level
sets for it, and makes those sets the independent parts of a complete
multipartite graph. Thus every vertex is a b-vertex and a nice vertex under the
planted coloring. No emitted instance is solved during generation.

## Why Track B

Section 1 supplies the exact b* definition. Section 2, Proposition 5 proves
NP-completeness on co-bipartite graphs, but that worst-case theorem says nothing
about this generated distribution and is not used as a Track A claim. The paper
also identifies regimes that are mechanically easy: Proposition 2 computes
`m*` in `O(n Delta)`, Propositions 6–8 give constructive results for block
graphs and cacti, Proposition 9 handles z-coloring of P4-sparse graphs, and
Section 3 gives both locality (Proposition 11) and a 0–1 model (Proposition 13).

This family is deliberately honest about its algorithm. Complement-component
recognition followed by modular Gaussian elimination solves every instance in
`O(N^2 + N d^2)`. At the hard preset it solved 8/8 instances, averaging 9,316
field operations and 0.0048 seconds in the measured run. The compact route is
to notice that one nonedge component already contains `d-1` independent
differences; solving only that 5-by-5 system costs 185 field operations. The
gap is between processing roughly 255 displayed equations and isolating the
one color class that determines their common invariant.

## Worked demo

This is the complete `demo` instance for seed 123:

```text
Finite-field b*-coloring certificate

Let p = 11 (a prime), d = 3, and k = 3.
Distinct vertices are nonadjacent exactly when listed after `|`; every other
distinct pair is an edge. Each row is `id : coordinates | nonneighbors`.

113452 : 1,0,4 | 758838,971999
657839 : 10,9,5 | 469008,625344
758838 : 8,9,5 | 113452,971999
625344 : 0,1,2 | 469008,657839
481173 : 9,9,5 | 525427,340259
971999 : 9,1,2 | 758838,113452
469008 : 3,0,4 | 625344,657839
525427 : 10,1,2 | 340259,481173
340259 : 2,0,4 | 525427,481173
```

The answer is `<answer>[1, 0, 4]</answer>`. It yields three residue classes,
one per independent part. `verify(inst, [1, 0, 4])` returns `(True, "ok")`;
dropping the last coefficient returns `(False, "answer must contain exactly 3
coefficients")`. A person can solve this demo on paper: subtract the coordinates
of two nonneighbors and solve the resulting 2-by-2 equations modulo 11.

## Difficulty presets

| Preset | Classes `n` | Dimension | Prime | Typical vertices (seed 123) | Covector space |
|---|---:|---:|---:|---:|---:|
| demo | 3 | 3 | 11 | 9 | 121 |
| easy | 12 | 5 | 65,537 | 73 | 18,447,869,999,386,460,161 |
| medium | 24 | 6 | 1,000,003 | 178 | about `10^30` |
| hard (selected) | 34 | 6 | 2,147,483,647 | 295 | about `4.57e46` |

The hard preset is the intended shipping level, but it has not earned a Step 4
shipping verdict because the external oracle account was unavailable. No preset
was rejected by a local gate.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | planted witness verified on 12 preset/seed pairs |
| G2 | pass | 5 corruptions rejected with 5 distinct reasons |
| G3 | pass | tagged prose/fenced JSON round-trip |
| G4 | pass | 0/200,000 guesses; exact density `2.1895e-47` |
| G5 | pass | exactly 1 valid covector; strongest attack tried 65,536 candidates in 0.621 s |
| G6 | pass | 5 attacks, each 0/8; reference and compact routes each 8/8 |
| G7 | pass | 301 vertices to 581 when `n` doubles; witness still verifies |
| G8 | pass | 60/60 invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 55 characters, 14 estimated tokens, 6 atoms, 185 operations |

## Oracle loop and G9 diagnostics

The bare harness reached only its retry logic. These are errors, not failures to
solve, and therefore do not support a hardening claim.

| Arm | Scored solved/attempts | Script calls | Result |
|---|---:|---:|---|
| bare | 0/0 | 4 | all HTTP 403 key-limit errors |
| structural hint | 0/0 | 4 | all HTTP 403 key-limit errors |
| placebo hint | 0/0 | 4 | all HTTP 403 key-limit errors |

`hinted - placebo` is unavailable (stored as 0.0 only because both scored
denominators are zero), so no conclusion about hint sensitivity is possible.
The structural hint names only the common codimension-one invariant; it does
not provide the elimination procedure.

## Use

```python
from gen_2408_12951 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=123, **DIFFICULTY["demo"])
print(render(inst))
answer = parse_answer("<answer>[1, 0, 4]</answer>")
assert verify(inst, answer) == (True, "ok")
```

From the repository root, after a successful oracle rerun, emit examples with:

```bash
bash scripts/emit.sh 2408.12951 20 hard
```

## Caveats

This is not evidence that generic b*-coloring is hard on this distribution:
with a sandbox, the disclosed polynomial algorithm solves it in milliseconds.
The benchmark tests whether a no-tool solver sees the affine invariant before
attempting all displayed equations. Even after that insight, the hard instance
requires exact modular arithmetic, so some failures may reflect arithmetic
rather than graph intuition.

The exact density is relative to the declared language of normalized linear
covectors, not to all possible vertex colorings. I tested coordinate-axis,
small-coefficient, one-pass greedy, one-equation, and 8,192-restart attacks. I
did not run a separate ILP/SDP package: for this complete multipartite
representation, complement recognition plus exact elimination is a stronger
direct reference. Finally, the canonical key deliberately identifies all
invertible affine coordinate presentations of the same complete multipartite
graph; its structural invariant is the sorted part-size multiset.
