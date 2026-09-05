# arXiv 1207.3887 — finite point ideals with compact lex bases

| profile | value |
|---|---|
| Track | **B — no-tool compression**; no Track A claim |
| Native domain / regime | algebra / finite field |
| Computational core | polynomial identity and point-ideal interpolation |
| Certificate | exact symbolic power-binomial polynomial circuits |
| Intended intuition | change of variables via projection-fiber sums |
| Domain essentiality | native; no reduction |

## What the family is, and whether to trust it

The source is Xavier Dahan, [*On lexicographic Groebner bases of radical
ideals in dimension zero: interpolation and structure*](https://arxiv.org/abs/1207.3887).
The solver receives a finite set `V` of points in `GF(p)^d` and must return a
minimal monic lexicographic Gröbner basis of `I(V)`, the polynomials vanishing
on those points.  Each answer polynomial is an exact circuit

`g_i = (x_i + a_i * sum_j weights[i][j] x_j)^r - 1`,

so the answer stays short even when `V` has 10,000 points.

There is a crucial source caveat: arXiv v3 is **withdrawn**, with the author's
statement that the key decomposition in §2.2 does not have the claimed
property and that the ensuing proofs are flawed.  This generator does not use
that decomposition or its Structure Theorem.  It uses the native definitions
from §1 and the projection/interpolation objects of §§2.1, 2.3, and 4, then supplies
an independent construction and executable proof:

- Choose the answer scalars first and put
  `L_0=x_0`, `L_i=x_i+a_i sum_j w_ij x_j`.
- Enumerate every tuple `(u_0,...,u_(d-1))` of `r`-th roots of unity and solve
  the triangular equations `L_i(x)=u_i`.  This is inverse generation, not a
  Gröbner-basis computation on the completed instance.
- Every returned circuit vanishes exactly because `u_i^r=1`.  Its leading
  monomial is `x_i^r`; these pure powers are pairwise coprime, hence the
  circuits form a minimal monic lex basis of their ideal.
- The checker confirms `r^d` distinct points and exact vanishing.  The candidate
  quotient and `I(V)` both have dimension `r^d`, so containment is equality.

`verify` performs only modular integer arithmetic and never reads
`inst["answer"]`.  Thus the flawed theorem is neither trusted nor needed.

## Why this is Track B

The paper itself makes Track A untenable.  Its introduction names the
Buchberger–Möller point-ideal algorithm, Lederer's reconstruction algorithm,
and the lex game, and calls the two-variable case easy.  Its proposed
algorithm/complexity section is unfinished.  This generated distribution also
has an efficient specialized algorithm.

The successful shipping reference mechanically tabulates **every** projection
fiber, sums all of them, reconstructs the circuits, and checks all 10,000
points.  It costs `O(d*m)` point inspections plus
`O(d*r^(d-1))` field operations for `m=r^d`; over eight shipping instances it
solved 8/8 with medians of 30,000 point inspections, 541,029 counted operations,
and 0.070731 seconds.  Generic Buchberger–Möller evaluation elimination is
`O(d*m^3)` in this implementation: the executable 256-point calibration already
used 20,173,299 operations and 1.189680 seconds.  It was not run with a 10,000
column evaluation matrix, and that smaller calibration is not presented as a
shipping measurement.

The compact route notices that all roots of `T^r-1` sum to zero.  For one
projection fiber,

`a_i * sum_j w_ij*x_j = -(1/r) * sum_fiber x_i`.

One nonzero fiber determines each of the three scalars.  The instrumented route
solved 8/8 shipping instances with at most 235 exact operations.  The benchmark
is the gap between discovering and executing that one-fiber invariant and
mechanically processing the whole point table; it is not a complexity-theoretic
hardness claim.

## Worked demo

For `demo`, `seed=7`, `render` returns the following complete statement:

```text
Recover a compact lexicographic Groebner basis of a finite point ideal.

Definitions and arithmetic.
Work in the finite field GF(p) with p = 17.
A field element is written as its unique integer residue from 0 through p-1.
Every addition, subtraction, multiplication, and power below is modulo p.
There are d = 2 variables x0,...,x1 and r = 2.
For exponent vectors alpha and beta, the lexicographic order compares the
largest variable index where they differ; the monomial with the larger
exponent there is larger. Thus x0 < x1 < ... < x(d-1).
For a finite point set V, I(V) is the set of all polynomials over GF(p)
that evaluate to zero at every point of V.
A monic Groebner basis is minimal when none of its leading monomials
divides another. In the promised answer the leading monomials are
x0^r,...,x(d-1)^r, which are pairwise coprime.

Promised bounded certificate language.
Return exactly d symbolic circuits. Circuit i represents
  g_i(x) = (linear[0]*x0 + ... + linear[d-1]*x(d-1))^r - 1.
Its JSON field constant must therefore be p-1, the residue of -1.
Circuit i must have linear[i]=1 and linear[j]=0 for every j>i.
For i>0 there is one hidden scalar a_i such that
  linear[j] = a_i * weights[i][j] (mod p) for 0 <= j < i.
The d-1 scalars a_i must be pairwise distinct integers in [1,7].
Row 0 has no scalar. All circuit powers must equal r.
The public weight rows, indexed 0 through d-1, are:
  weights[0] = []
  weights[1] = [1]

Point set V (exactly 4 distinct points).
Coordinates and points are 0-indexed. The list is sorted lexicographically;
its order is not part of V and repeated points are forbidden.
  [1,13]
  [1,15]
  [16,2]
  [16,4]

Task.
Find circuits in the promised language that vanish on every displayed point.
Because their leading monomials are the pairwise-coprime pure powers x_i^r,
they form a minimal monic lexicographic Groebner basis of their ideal.
The quotient has exactly r^d standard monomials, equal to |V|, so vanishing
also proves that this ideal is exactly I(V).
Order the basis by i=0,1,...,d-1. No circuit or coefficient may be omitted.
Use JSON with exactly one key, basis; each circuit has exactly the keys
linear, power, constant, and every linear list has exactly d residues.
Give your final answer inside <answer></answer> tags, as that JSON object.
Example of the required shape: <answer>{"basis":[{"linear":[1,0],"power":2,"constant":16},{"linear":[1,1],"power":2,"constant":16}]}</answer>
Output nothing else inside the tags.
```

One answer is
`{"basis":[{"linear":[1,0],"power":2,"constant":16},{"linear":[3,1],"power":2,"constant":16}]}`.
`verify` returns `(True, "ok")`.  Replacing the second linear row by `[4,1]`
returns `(False, "circuit_1_does_not_vanish_at_point_0")`.  A person can solve
this demo on paper: the two `x1` values over `x0=1` sum to `11 mod 17`, giving
`a_1 = -(11/2) = 3 mod 17`.

## Difficulty and gate results

After the script hardened only at an escalated level, the ladder was slid up as
required; `demo` stayed fixed.  `hard` is the shipping preset.

| preset | `r=n` | `d` | points | `p` | oracle status |
|---|---:|---:|---:|---:|---|
| demo | 2 | 2 | 4 | 17 | hand example; skipped |
| easy | 6 | 4 | 1,296 | 2,013,265,921 | rejected: 1/3 solved |
| medium | 8 | 4 | 4,096 | 2,013,265,921 | rejected: 1/3 solved |
| **hard** | **10** | **4** | **10,000** | **2,013,265,921** | **ships: 0/3 solved** |

| gate | measured result |
|---|---|
| G1 | 16/16 preset/seed witnesses verify; 16/16 field hypotheses checked |
| G2 | empty, drop, swap, duplicate, and out-of-range corruptions rejected for five distinct reasons |
| G3 | tagged fenced prose round-trips; garbage returns `None` |
| G4 | 0/200,000 structure-aware legal circuit guesses |
| G5 | unique shipping answer among 8,160,249,270,239,027,939,392,880,640 candidates; reference 541,029 ops / 0.070731 s median |
| G6 | four attacks each 0/8; full reference and compact route each 8/8 |
| G7 | 10,000 to 20,736 points, with the answer fixed at 24 atoms |
| G8 | 80/80 reorder/composition invariance and carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | 317 worst-case characters, about 80 tokens, 24 atoms, 235 intended operations |

The four failing attacks are smallest legal residues (outlier/magnitude), a
greedy first-point fit that assumes the residual root is one, an ordinary
integer coordinate-span heuristic that ignores modular wraparound, and 256
structured random restarts.  Each candidate already obeys the public circuit
shape and coefficient constraints.

## Oracle ladder

The repository hardener used its recorded two-vendor pool.  “Wrong” means the
reply parsed but failed exact verification; “empty” is the script's scored
empty-response case.  Every level below order 10 was defeated by at least one
valid answer.

| round / level | seeds | outcomes and exact reason |
|---|---|---|
| 0 / original easy (`r=4,d=3,p=65537`) | 559513699, 105915339, 2147104618 | solved, solved, solved |
| 1 / original medium (`r=4,d=4,p=65537`) | 272784407, 1197041354, 1120120156 | solved, solved, solved |
| 2 / original hard (`r=4,d=4`, 31-bit `p`) | 698393691, 1225332753, 388233217 | solved; wrong (`circuit_2` point 0); solved |
| 3 / escalated `r=5` | 1340333940, 1035479808, 655534491 | wrong proportionality; solved; wrong proportionality |
| 4 / escalated `r=6` | 228232400, 1203032053, 1850280240 | solved; wrong `circuit_1` point 0; wrong `circuit_2` point 0 |
| 5 / escalated `r=8` | 1724870159, 223796015, 1164056698 | wrong `circuit_3` point 2; solved; empty at token limit |
| 6 / escalated `r=10` | 502776563, 1930414088, 1411684335 | wrong proportionality; empty provider response; wrong proportionality — **held** |

## G9 diagnostic arms

| arm at shipping hard | solved / attempts | conclusion |
|---|---:|---|
| bare | 0/3 | hardened in the main ladder |
| structural | 1/3 | one Gemini solution |
| placebo | 1/3 | one Gemini solution |

`hinted - placebo = 0/3 = 0.0`.  The structural sentence showed no net benefit
over a same-register placebo in this small sample.  That does not falsify the
change-of-variables interpretation, but it means the oracle evidence cannot
attribute the difference to the hint.  Both diagnostic transcripts were made
in isolated directories and copied back; the 317-character/24-atom answer and
235-operation intended route are within G9(c).

## Use

```python
import json
import gen_1207_3887 as g

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=42, **params)
statement = g.render(inst)
wire = "<answer>" + json.dumps(inst["answer"]) + "</answer>"
candidate = g.parse_answer(wire)
assert g.verify(inst, candidate) == (True, "ok")
```

From the repository root:

```bash
bash scripts/emit.sh 1207.3887 20 hard
```

## Caveats

- The source's main proof is withdrawn and flawed.  This benchmark covers its
  native point-ideal/interpolation problem, not the validity of that proof or
  its claimed general decomposition.
- The family is a deliberately structured triangular subclass invented for
  inverse generation.  It does not represent arbitrary radical point ideals.
- The exact density `1/8.160...e27` and 0/200,000 sample apply only to the
  uniform prior on legal bounded circuits.  They say nothing about a solver
  using fiber correlations.
- Hardening emerged by growing the displayed point table to 10,000 rows.  Two
  shipping oracles returned explicit invalid circuits, but the third returned
  an empty provider response with `finish_reason=error` and zero recorded prompt
  tokens; `harden.py` scores such empty replies as unsolved.  Context/attention
  load is therefore part of the evidence, and one of three failures is weaker
  than an explicit wrong witness.
- Generic Buchberger–Möller was run only at 256 points.  No CAS, F4/F5, FGLM,
  lex-game implementation, SMT solver, or external Gröbner package was tried.
  The shipping reference exploits the promised circuit language and is not a
  general point-ideal routine.
- `canonical_key` is complete for reordering the unlabeled input set.  It does
  not quotient by affine changes of field coordinates, because those change
  the numerically stated problem and carry the requested basis to a new answer.
- `gvlib` has exact rational polynomials but no finite-field Gröbner engine, so
  this module uses auditable standard-library modular integers throughout.
