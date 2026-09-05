# Dense translation certificates for flat logic engines

| profile | value |
|---|---|
| track | **B — no-tool compression** |
| native domain | logic |
| object regime | finite discrete |
| computational core | polynomial identity |
| certificate | Boolean polynomial in algebraic normal form |
| intended intuition | invariant: odd XOR-translation preserves the quadratic ANF part |
| domain essentiality | licensed reduction |
| reduction | paper-licensed, Sections 1.4 and 4 |

This generator is based on Eric Binnendyk’s [“Determining unit distance graphs
with coordinates in Z² is NP-complete”
(v2)](https://arxiv.org/abs/2510.15002v2). It hands the solver a compact family
of the paper’s logic-engine flag rows. The solver returns a sparse Boolean
polynomial whose truth table gives every primary armature’s up/down
orientation. Verification expands the polynomial and recomputes every parity
row exactly.

This is **not native geometry coverage**. Sections 3–4 license the reduction
from arbitrary NAE-3 logic engines to integer-lattice unit-distance graphs, but
the rendered instance does not enumerate the much larger frame, shaft, square
chains, or all lattice coordinates. Those geometric objects were deliberately
not disguised as an adjacency-matrix benchmark; the retained object is the
paper’s Section 1.4 logic engine, and the profile says `licensed_reduction`.

Trust status: all local gates G1–G9(c) pass. STEP 4 is **blocked, not passed**.
Every OpenRouter draw returned HTTP 403 “Key limit exceeded,” leaving zero
scored oracle attempts. The script-owned error transcripts are preserved, so
this directory is auditable but not submission-ready.

## Construction and certificate

Primary armatures are indexed by the vectors of `F_2^k`. Generation first
samples a non-affine quadratic ANF `q`, then an odd set `S` of translation
masks, and publishes

```text
R(i) = XOR over s in S of q(i XOR s).
```

This is inverse generation: `q` exists before `R`. If `A=sum(T_s)` is the
translation operator, characteristic two gives `A²=|S|I=I`: cross terms cancel,
every translation squares to the identity, and `|S|` is odd. Thus the answer is
unique. The checker does not rely on that proof; it evaluates the candidate
ANF and substitutes it into all displayed equations.

Each long parity is an exact shorthand for NAE-3 rows. Accumulator armatures
reduce it to ternary XOR relations. With a fixed reference armature `Z=0`, four
NAE-4 clauses forbid the four wrong-parity triples, and each NAE-4 expands to
two NAE-3 clauses. A deterministic auxiliary rule (`not l0` if `l0=l1`, else
`l2` if `l2=l3`, else zero) turns every accepted NAE-4 into a concrete pair of
accepted NAE-3 rows. Section 1.4’s first-unflagged-link construction then gives
a complete flat flag orientation.

## Why Track B

The paper’s main theorem proves worst-case NP-completeness through arbitrary
NAE-3SAT. It does not prove hardness for randomly planted coordinate drawings,
so the prior Track-A idea was rejected. Section 2 also distinguishes this
recognition problem from Eppstein’s polynomial-time lattice-dimension problem,
whose shortest-path/Manhattan condition is absent here.

This generated restriction has an efficient algorithm and says so openly. A
full Boolean Möbius transform of the 2,048-bit right-side table, followed by
symbolic translation, solves it in `O(n log n + k²)`: **11,479 measured Boolean
operations** and **0.011857 s** averaged over eight shipping seeds on the
shared runner. Directly applying the dense involution is a slower
2,104,320-XOR alternative.

The compact route inspects only `R(0)`, the basis-vector entries, and the
pairwise-basis entries. These recover the common quadratic part; the supplied
first- and second-moment checksums correct the affine terms. It costs **215
Boolean operations**. The gap is therefore 11,479 mechanical operations versus
215 after seeing the invariant—not a claim that this distribution is hard with
tools.

The current arXiv v3 is a withdrawal notice because a stronger 1987 result for
unit-distance trees was already known. This module is grounded explicitly in
the available 15-page v2 definitions and reduction; withdrawal affects novelty,
not those executable objects.

## Worked demo

For `seed=0`, the full demo statement is:

```text
DENSE FLAT LOGIC-ENGINE ORIENTATION (exact Boolean instance)

There are n=8=2^3 primary armatures X_0,...,X_7.
Write each index as a k-bit vector; XOR below is bitwise exclusive-or.
Orientation 1 means the unprimed chain points up; 0 means it points down.

The shift list S has w=3 distinct entries. For every
row index i=0,...,n-1 the required relation is

  XOR over s in S of X_(i XOR s) = R[i].

This is a finite logic engine, not a probabilistic condition. Process S
in displayed order, introducing an accumulator after each later X value.
Enforce each update A XOR B XOR C=0 (C is the new accumulator) as follows.
Add a reference armature Z fixed to 0. For each of the four bit triples
t=(t0,t1,t2) with t0 XOR t1 XOR t2=1, include the NAE-4 clause
NAE(A XOR t0,B XOR t1,C XOR t2,Z); it forbids exactly that wrong triple.
NAE means its literals are not all equal. Expand each NAE-4(l0,l1,l2,l3)
as NAE(l0,l1,y) and NAE(not y,l2,l3), with a fresh auxiliary y. The final
accumulator equals R[i]. All auxiliaries are fixed by the primary X values,
so the requested polynomial is a compact complete orientation. The checker
evaluates it and recomputes every accumulator parity exactly.

Represent orientations by a Boolean polynomial q in algebraic normal form
(ANF): XOR of distinct squarefree monomials in Boolean variables
u_0,...,u_2, evaluated on i's k bits (least-significant is u_0).
At most 8 nonzero monomials are allowed. Write a monomial
as its strictly increasing JSON list of variable indices; [] is constant 1.
Sort the outer list by each monomial's binary mask sum(2^j). Coefficients
are 1 in GF(2), so terms may not repeat. Example [[],[0],[1,3]] means
q=1 XOR u_0 XOR (u_1*u_3).

SHIFT LIST S (order matters only for named accumulators):
  4 3 7
END SHIFT LIST

RIGHT-SIDE TABLE R (half-open offsets):
  R[0:8] = 11000110
END RIGHT-SIDE TABLE

Exact checksums of S, included as instance data:
  T = XOR of all masks in S = 0
  Pair order = (0,1), (0,2), (1,2)
  U = 011
U has one bit in that pair order; its (a,b) bit is the parity of the
number of s in S whose bits a and b are both 1.

Return one nonempty canonical JSON list of monomials. The stated order is
mandatory, and repeated terms are forbidden.

Give your final answer inside <answer></answer> tags as that JSON list.
Example: <answer>[[],[0],[1,3]]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[[1],[2],[0,2]]</answer>`. Verification returns
`(True, "ok")`; dropping `[0,2]` returns
`(False, "dense parity row 0 is violated")`. A person can solve this demo on
paper: it needs 27 Boolean operations after recognizing the invariant.

## Difficulty presets

| preset | n | shift weight | implicit NAE-3 rows | rendered chars (seed 0) | compact ops | status |
|---|---:|---:|---:|---:|---:|---|
| demo | 8 | 3 | 136 | 2,376 | 27 | hand-solvable; hardening skips it |
| easy | 128 | 63 | 63,616 | 2,845 | 97 | first unscored oracle rung |
| medium | 512 | 255 | 1,040,896 | 4,193 | 150 | not reached |
| hard | 2,048 | 1,023 | 16,746,496 | 9,800 | 215 | intended shipping; locally passes |

`escalate()` grows `n` and the dense table while the answer grows only with
`log n`; 4,096 and 8,192 remain supported. It returns `None` beyond that: the
next compact route would exceed the 300-operation effort cap, while increasing
shift weight at fixed `n` would not raise the strongest reference cost.

## Gate results

| gate | measured result |
|---|---|
| G1 | 16/16 planted certificates verified; 16/16 JSON round-trips; all 8 ternary truth-table rows matched the expanded NAE gadget |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | 3/3 realistic tagged responses parsed; garbage rejected |
| G4 | 0/200,000 uniform bounded-ANF candidates; exact probability `1.17e-167` |
| G5 | shipping sample 0/200,000; exact count 1 and density `1.17e-167` from involution uniqueness; reference 11,479 operations and 0.001470 s |
| G6 | five attacks all 0/8; reference and compact algorithms both 8/8 |
| G7 | doubled `n=4096` instance verified; reference cost rose to 24,828 operations |
| G8 | 20/20 invariant keys, 20/20 carried witnesses, 20/20 unrelated keys distinct |
| G9(c) | exact generated-answer bound: 221 chars, 56 tokens, 104 atoms; compact route 215 operations; all within caps |

The exact worst case over the generator's shipping support is 221 serialized
characters, 56 conservative tokens, and 104 atoms; the 56-token bound is in
`PROBLEM_PROFILE`. (A prior 256-seed sample reached 215 characters and 102
atoms.)

## Oracle loop and G9 arms

| arm / preset | provider draws | scored solved / attempts | result |
|---|---:|---:|---|
| bare / easy | 4 | 0/0 | HTTP 403 key-limit; no verdict |
| structural / hard | 4 | 0/0 | HTTP 403 key-limit; no verdict |
| placebo / hard | 4 | 0/0 | HTTP 403 key-limit; no verdict |

The stored hinted-minus-placebo numeric value is `0.0`, but with zero completed
attempts it is undefined as evidence. No conclusion about the invariant hint is
drawn. The hint names only the invariant and gives no recovery procedure.

## Use

```python
from gen_2510_15002 import DIFFICULTY, SHIPPING_DIFFICULTY
from gen_2510_15002 import make_instance, parse_answer, render, verify

inst = make_instance(seed=12345, **DIFFICULTY[SHIPPING_DIFFICULTY])
question = render(inst)
candidate = parse_answer(model_output)
ok, reason = verify(inst, candidate)
```

After replenishing `OPENROUTER_API_KEY`, rerun the bare loop and isolated G9
arms before emitting:

```bash
cd results/2510.15002
python3 ../../scripts/harden.py gen_2510_15002.py
cd ../..
bash scripts/emit.sh 2510.15002 20 hard
```

## Caveats

- This is a paper-licensed logic reduction, not a coordinate-realization
  benchmark. The explicit lattice embedding is not handed to the solver.
- The 0/200,000 rate uses the declared uniform prior over canonical nonempty
  ANFs with at most 96 terms. It is not a model-conditioned probability. The
  exact probability follows from uniqueness of the odd convolution.
- A solver that notices the right-side table is quadratic can use the compact
  route; that is the intended success mode. With a sandbox, the full Möbius
  transform makes the instance easy in milliseconds.
- The panel did not run an external SAT/SMT package or a specialized sparse
  Boolean interpolation library. It did run the complete standard ANF method,
  plus occurrence, copied-ANF, affine-only, moment-blind, and random-restart
  attacks.
- The absolute Walsh spectrum is not a complete affine-isomorphism test, though
  it passed all stated transformations and separated 20/20 unrelated seeds.
- No oracle hardness claim exists until the provider-quota blocker is cleared.
