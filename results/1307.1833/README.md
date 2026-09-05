# Exact factor certificates from Schubert calculus (arXiv:1307.1833)

Status: **parked, not shippable**. The module is a deterministic, exactly
verified generator and every local gate passes, but the no-hint oracle pool
solved 18/21 attempts across seven levels. `harden.py` returned `budget_bound`
because `escalate()` could keep enlarging the generic polynomial degree; the
transcript shows that this axis does not enlarge the degree-four compressed
calculation the models actually use. No `REJECTED.md` is present because a
budget-bound result is parked under the repository rules.

| Profile field | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain | algebra |
| Object regime | rational exact |
| Computational core | polynomial identity |
| Certificate form | polynomial |
| Intended intuition | decomposition: three residue blocks hide a difference of quadratic-form squares |
| Domain essentiality | licensed reduction |
| Reduction | paper-licensed, Section III.4, Theorem III.4.2 |

## Problem and trust model

Hein's [*Reality and Computation in Schubert
Calculus*](https://arxiv.org/abs/1307.1833) studies real points of osculating
Schubert problems. Section II.3 defines the incidence conditions, Section II.6
relates osculation to a Wronskian, and Theorem III.4.2 proves that real points of
the special problem `(omega, box^(N-1))` correspond exactly to monic real
factorizations `f'(t)=A(t)B(t)` of prescribed degrees. The solver receives the
real squarefree osculation-divisor polynomial `f` and returns one factor in an
exact three-residue-block encoding. This is the paper's central licensed
polynomial representation; it does not expose full flags or Stiefel matrices,
so it is not claimed as full native-object coverage.

Generation samples `q`, `r`, and `c` first, sets `X=q(t^m)` and
`Y=t*r(t^m)`, and composes the identity

`X^4 + (2-c^2)X^2Y^2 + Y^4 = (X^2-cXY+Y^2)(X^2+cXY+Y^2)`.

It then integrates the product to obtain `f`. Modular gcd tests certify that
`f` has distinct complex roots and that the modular reference prime is good;
they never discover the stored factor. Verification differentiates `f`, expands
the submitted residue blocks, divides exactly in `Z[t]`, and checks the monic
cofactor. It never reads `inst["answer"]`.

## Why Track B

This is not a Track A claim. Exact factorization over `Q[t]` is polynomial-time
via LLL. The executable reference uses Berlekamp factorization over `F_97` and
a centered, degree-balanced lift. At the provisional derivative degree 144 it
solved 8/8 instances at a median 11,049,990 counted field operations and about
0.543 seconds in the final local run.
The compact route recognizes that the derivative's residue-0 and residue-4
blocks are fourth powers and its residue-2 block is the scaled product square;
it then assembles one quadratic-form factor in 241 exact operations. A CAS makes
the task easy, as does seeing this decomposition. The intended difficulty is
finding that structure without tools. The external evidence says this candidate
does not achieve that goal: both vendors repeatedly reconstructed the compressed
fourth roots. Raising the compressed degree from four to five is the remaining
natural hardening axis, but the measured intended route rises from about 240 to
about 360 exact operations, exceeding G9(c)'s 300-operation cap.

Section III.2 is the paper's general mechanical route: determinantal equations,
Groebner elimination, and Sturm-Habicht root counting. Chapter V says
characteristic-zero Groebner calculations become infeasible around 16 variables
or 100 solutions and gives a square primal-dual formulation for certifiable
numerics. For this special Section III.4 family, however, Theorem III.4.2 is the
decisive easy-regime result and forces the Track B label.

## Worked demo

`make_instance(seed=3, **DIFFICULTY["demo"])` renders:

```text
Exact factor certificate for a real osculating Schubert instance

Let Q[t] be the ring of one-variable polynomials with rational coefficients.
In the displayed sparse term list, each pair [a/b,e] means the exact term
(a/b)*t^e (with an integer shown instead of a/1); unlisted coefficients are
zero and every displayed denominator is positive.

The geometric source is a conjugation-stable osculating instance in the complex
Grassmannian Gr(k,C^N), whose points are k-dimensional complex linear subspaces
of C^N, with N=22 and k=11.
Its conditions are omega=(2,3,...,k,N) at infinity and the standard codimension-one
Schubert incidence condition at each of the 21
distinct complex roots of the following real squarefree polynomial f(t)
("squarefree" means that no complex root is repeated):

f terms (coefficient, exponent), descending by exponent:
[[1/21, 21], [-1/4, 16], [-7/13, 13], [6/11, 11], [7/4, 8],
 [-2/3, 6], [1/5, 5], [-7/3, 3], [1, 1], [2122, 0]]

For this special family, the paper proves that its real points (the k-planes
defined over R) are in bijection with factorizations f'(t)=A(t)B(t) in which A
and B are monic real polynomials of degree 10; "monic" means leading
coefficient 1.  Thus a complete concrete certificate is one such factor A(t).
No knowledge of Grassmannians is needed: return A in the bounded exact language
below, and the checker differentiates f and performs exact polynomial division.
Numeric approximations and lists of roots are not accepted.

Encode A by three coefficient blocks.  The JSON object
{"stride":m,"blocks":[C0,C1,C2]} represents the ordinary polynomial
  A(t) = sum over r=0,1,2 and j>=0 of C_r[j] * t^(m*j+r).
All block arrays are in increasing j order and include zero coefficients.

Your answer must have exactly the two keys "stride" and "blocks".  The stride
must be the integer 5.  C0, C1, C2 must have lengths 3,
2, 1, respectively.  Every entry must be an integer in
the inclusive range [-3,3].  The final entry of C0 must be 1,
the first entry of C0 must be nonzero, and no other nonzero pattern is assumed.
These rules make A monic of degree exactly 10; order is the displayed
C0,C1,C2 residue order and repetitions within a coefficient array are allowed.

Give your final answer inside <answer></answer> tags, as that JSON object.
Example: <answer>{"stride":5,"blocks":[[1,2,1],[-2,-2],[1]]}</answer>
Output nothing else inside the tags.
```

The planted answer is
`{"stride":5,"blocks":[[1,-2,1],[3,-3],[1]]}`.
`verify(inst, inst["answer"])` returns `(True, "ok")`; deleting the last
entry of block 0 returns `(False, "block 0 must have exactly 3 coefficients")`.
The demo has exactly 2 valid certificates among 14,406 language-valid
candidates. A person can solve it on paper by differentiating the ten displayed
terms and recognizing the quadratic-form identity; brute-forcing 14,406
candidates is not the intended hand route.

## Difficulty presets

| Preset | Factor / derivative degree | Stride | Block lengths | Search space | Status |
|---|---:|---:|---:|---:|---|
| demo | 10 / 20 | 5 | 3, 2, 1 | 14,406 | hand example |
| easy | 72 / 144 | 9 | 9, 8, 7 | 4.91e45 | oracle solved 2/3 |
| medium | 104 / 208 | 13 | 9, 8, 7 | 4.91e45 | oracle solved 3/3 |
| hard | 136 / 272 | 17 | 9, 8, 7 | 4.91e45 | oracle solved 2/3 |

Nothing ships. `SHIPPING_DIFFICULTY="easy"` is retained only because the module
interface requires one of the three non-demo names; it identifies the preset
used for local measurements and G9, not an accepted release level. The harness
also tried factor degrees 152, 168, 184, and 200, and every one was defeated.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted certificates verify and JSON-round-trip |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON object survives prose and a Markdown fence |
| G4 | pass | 0/200,000 hits in the exact structure-aware language |
| G5 | pass | provisional density 0/200,000; demo exact 2/14,406; reference 11,049,990 ops / 0.543 s median |
| G6 | pass | four attacks each 0/8; reference and compact route each 8/8 |
| G7 | pass | factor degree doubles 72 to 144 while block lengths stay 9,8,7 |
| G8 | pass | 60/60 symmetry and carried-witness checks; 20/20 unrelated keys distinct; 20/20 equal-derivative/different-constant instances distinguished |
| G9(c) | pass | 89 chars, about 23 tokens, 25 atoms, 241 intended operations; generated-answer worst case 26 tokens |

## Oracle loop and G9 diagnostics

| Bare preset / factor degree | Seeds | Solved | Why |
|---|---|---:|---|
| easy / 72 | 840279072, 1092252228, 1393449678 | 2/3 | two verified; one coefficient exceeded the bound |
| medium / 104 | 857644818, 192438863, 1878583757 | 3/3 | all verified |
| hard / 136 | 1062200562, 1418135163, 1193408263 | 2/3 | two verified; one failed evaluation divisibility |
| escalated / 152 | 295580898, 286613588, 655521369 | 3/3 | all verified |
| escalated / 168 | 1861771119, 545419083, 1897617218 | 2/3 | two verified; one failed evaluation divisibility |
| escalated / 184 | 1116227198, 1403358774, 1733180407 | 3/3 | all verified |
| escalated / 200 | 1926265428, 1386323851, 932318401 | 3/3 | all verified |

The script verdict is `budget_bound`, not `hardened`: increasing the residue
stride remained available after six escalations. Successful replies show that
this is not meaningful no-tool scaling, because the degree-four block problem
never changes.

| G9 arm at easy | Solved/attempts |
|---|---:|
| bare | 2/3 |
| structural hint | 3/3 |
| placebo hint | 2/3 |

The hinted-minus-placebo rate is `1/3`. The hint helped one additional attempt,
but bare and placebo were already broadly solvable, so the diagnostic does not
rescue the claimed decomposition difficulty. The measured answer is 89
characters, about 23 tokens and 25 atoms; the intended route is 241 exact
operations.

## Use

```python
import importlib.util, json

path = "results/1307.1833/gen_1307_1833.py"
spec = importlib.util.spec_from_file_location("gen_1307_1833", path)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

params = g.DIFFICULTY[g.SHIPPING_DIFFICULTY]
inst = g.make_instance(seed=42, **params)
wire = "<answer>" + json.dumps(inst["answer"]) + "</answer>"
assert g.verify(inst, g.parse_answer(wire)) == (True, "ok")
```

For local inspection only, from the repository root:
`bash scripts/emit.sh 1307.1833 20 easy`. Do not add the resulting artifact to a
release while `.meta.json` records `budget_bound`.

## Caveats

- The 0/200,000 estimate samples uniformly from the exact three-block language,
  including its fixed lengths, stride, monicity, height bound, and nonzero
  constant. It does not model a solver that has recognized the fourth-power
  blocks; that solver should use the compact route and succeed.
- The local attacks are a coefficient-magnitude projection, greedy residue
  projection, 256 structured random restarts, and a symmetric/alternating
  by-hand ansatz. A full LLL factorizer, commercial CAS, and a Groebner solve of
  the original flag-incidence equations were not run. The first two are expected
  to succeed and are why this is Track B.
- The executable reference deliberately uses a good prime certified during
  generation and a coefficient bound small enough for unique centered lifting.
  General polynomial-time factorization is supplied by rational LLL theory, not
  by a worst-case claim for this compact reference implementation.
- Canonicalization covers input-term reordering and the projective reflection
  `t -> -t`, and it includes the integration constant; the self-test explicitly
  separates polynomials with equal derivatives but different constants. General
  projective changes do not preserve the bounded residue-block answer language
  and are outside this generator's represented family.
- The decisive caveat is empirical: the generic factorization baseline is large,
  but the model pool found the compressed route on 18/21 bare attempts. Search
  space and generic operation count therefore do not establish Track B hardness.
