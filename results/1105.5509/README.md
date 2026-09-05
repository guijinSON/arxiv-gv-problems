# Multihomogeneous Gröbner-basis generator for arXiv:1105.5509

> **Status:** verified and hardened at `medium`. The bare harness first found
> `easy` solvable, then recorded three failures at `medium`. The structural-hint
> diagnostic also recorded three failures. OpenRouter exhausted the key before
> the placebo diagnostic scored an attempt, so that comparison is unavailable
> and is reported as such rather than inferred from API errors.

| profile axis | declaration |
|---|---|
| hardness track | **B — no-tool compression** |
| native domain | `algebra` |
| object regime | `finite_field` |
| computational core | `polynomial_identity` |
| certificate form | `matrix_certificate` |
| intended intuition | `invariant`: recognize a rank-one constant-row component in the leading coefficients |
| domain essentiality | `native` |
| reduction | none |

## Problem and trust model

The solver receives coefficient rows of multihomogeneous polynomials over a
prime field and must return the two tail coefficients of every polynomial in
the reduced Gröbner basis. The family comes from Sköldberg,
Vejdemo-Johansson, and Dusek, [“A parallel Buchberger algorithm for multigraded
ideals”](https://arxiv.org/abs/1105.5509). Sections 2–3 define the grading
lattice, multihomogeneous reduction, and its degree dependencies; Section 4
schedules S-polynomials by antichains.

Generation is inverse, not a solve. It first samples
`B_i = x_i^2 + u_i*a*b + v_i*c*d`. All three monomials have multidegree
`(2,2)`, and the pairwise-coprime leading monomials `x_i^2` make `B` a reduced
Gröbner basis. It then publishes a shuffled invertible recombination `F=A B`,
where `A=I+1*w^T` and `sum(w)=0`, hence `A^-1=I-1*w^T`. The verifier never
reads the planted answer: it reduces every displayed generator by the proposed
basis, checks full leading-block rank, and exactly reduces every Buchberger
S-polynomial to zero over `GF(p)`.

This is deliberately not Track A. A standard Gauss–Jordan solve of the
degree-`(2,2)` coefficient matrix recovers the answer in
`O(n^3+n^2 t)` field operations (`t=2`). At the shipping preset it took 9,666
counted operations and 0.003195 s in the final self-test; across eight seeds it
averaged 10,772 operations and solved 8/8. Once the rank-one invariant is
recognized, two weighted sums and row corrections take exactly 214 modular
operations. That route is within the no-tool cap but sufficiently arithmetic
heavy that the mandatory oracle experiment is needed before any hardness claim
is credible. Section 1.1 calls Buchberger exponential in general, but that
worst-case fact is not used as distributional evidence. Example 1.1 also shows
the easy regimes: `I_1,I_2` are blackboard computations, `I_3` takes minutes,
and term order drastically changes basis size. Section 6 identifies densely
populated grades as the serial bottleneck this construction occupies.

## Worked demo

For `make_instance(n=2, modulus_bits=2, seed=0)`, `render()` produces this
complete hand-scale question:

```text
Recover a reduced multihomogeneous Groebner basis

Work in the polynomial ring GF(5)[x0,x1,a,b,c,d].  GF(5) is
the prime field: add and multiply integer representatives modulo 5, always
writing a field element as its unique integer in the inclusive range 0..4.

Use lexicographic monomial order with
x0 > x1 > a > b > c > d.  For exponent vectors, compare the
exponent of the first variable where they differ; the monomial with the larger
exponent there is larger.  The variables have N^2 multidegrees
|x_i|=(1,1), |a|=(1,0), |b|=(1,2), |c|=(0,1), |d|=(2,1).
Thus x_i^2, a*b, and c*d all have multidegree (2,2).

Each following row is the coefficient vector of one generator of an ideal I.
The generated ideal I consists of every finite sum of polynomial multiples of
these rows.  Rows may be used in any order.  The coefficient columns, in order,
are:
x0^2 x1^2 a*b c*d

0 1 0 2
4 2 2 1

A monomial's multidegree is the sum of the variable multidegrees counted with
their exponents; a polynomial is multihomogeneous when all its monomials have
one multidegree.  LM(f) denotes the largest monomial of f in the stated order.
A finite set G is a Groebner basis when every polynomial in I has leading
monomial divisible by a leading monomial of G.  It is reduced when every member
is monic and no nonleading monomial of one member is divisible by a leading
monomial of any member.  Equivalently for checking here, Buchberger's criterion
says that every pair's S-polynomial must reduce to zero by G.  For monic f,g,
S(f,g)=lcm(LM(f),LM(g))/LM(f)*f - lcm(LM(f),LM(g))/LM(g)*g, where
the lcm takes the coordinatewise maximum of the two exponent vectors.

The reduced Groebner basis of I is promised to have exactly 2 polynomials in
this fixed form, with row index i and all arithmetic in GF(5):

    B_i = x_i^2 + U[i][0]*a*b + U[i][1]*c*d,   0 <= i < 2.

Return U as exactly 2 rows of two canonical field integers.  Row order is
fixed by x0,x1; do not reorder rows.  Entries may repeat.  No fractions,
negative representatives, omitted rows, or extra keys are allowed.

Give your final answer inside <answer></answer> tags as one JSON matrix.
Example format only: <answer>[[0,1],[2,3]]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[[3,3],[0,2]]</answer>`. Verification returns
`(True, "ok")`. Changing its first entry to `4` returns
`(False, "candidate basis does not generate the displayed ideal")`. A person
can solve this demo by two short linear equations modulo 5.

## Difficulty and local gates

| preset | `n` | modulus | answer entries | status |
|---|---:|---:|---:|---|
| `demo` | 2 | 5 | 4 | hand-solvable; skipped by hardening |
| `easy` | 24 | 4099 | 48 | oracle solved 2/3; rejected for shipping |
| `medium` | 36 | 65537 | 72 | **ships; oracle solved 0/3** |
| `hard` | 48 | 1048583 | 96 | locally verified; not needed after `medium` held |

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verified (four presets × three seeds) |
| G2 | drop, swap, duplicate, empty, and out-of-range corruptions rejected with five distinct reasons |
| G3 | exact JSON recovered through prose, tags, and inner or outer Markdown fences; garbage rejected; JSON-native round trip passed |
| G4 | 0/200,000 uniform structure-aware guesses; declared shipping space has 1,153 bits |
| G5 | shipping density 0/200,000; demo exact solution count 1; Gauss–Jordan 9,666 operations and 0.003195 s; compact decoder verified in 214 operations |
| G6 | six attacks each 0/8; reference Gauss–Jordan solved 8/8, averaging 10,772 operations and 0.013673 s on the contended final run |
| G7 | doubled `n=72` instance verified; language grew from 1,153 to 2,305 bits |
| G8 | 20/20 composed relabellings invariant, 20/20 carried witnesses valid, 20/20 unrelated keys distinct |
| G9(c) | 501 characters, about 126 tokens, 72 atomic entries, 214 intended operations |
| G9 diagnostics | bare 0/3 and structural hint 0/3 at shipping; placebo unavailable after the key limit |

The failing attacks are smallest-row anchoring, raw pivot-row extraction,
random restart (256 samples), fixing an arbitrary row-difference origin,
unweighted centering, and replacing finite-field weights by their signs. The
last three are realistic in-context attempts that partly recognize the visible
row structure but miss the exact global correction.

## Oracle loop and G9 arms

The harness rejected `easy` after two verified solves and hardened at `medium`.
All answers shown below parsed; the three medium candidates then failed exact
verification.

| preset | model | seed | solved? | reason |
|---|---|---:|---|---|
| `easy` | Gemini 3.8 Flash | 554667089 | no | wrong coefficient matrix |
| `easy` | GPT-5.6 Terra | 1745998660 | yes | verified |
| `easy` | GPT-5.6 Terra | 1522421646 | yes | verified |
| `medium` | GPT-5.6 Terra | 2133353614 | no | wrong coefficient matrix |
| `medium` | Gemini 3.8 Flash | 752716821 | no | negative, noncanonical field entries |
| `medium` | GPT-5.6 Terra | 947893310 | no | wrong coefficient matrix |

| G9 arm | solved / scored attempts | conclusion |
|---|---:|---|
| bare | 0/3 | shipping preset held |
| structural hint | 0/3 | hint did not produce a verified witness |
| placebo hint | 0/0 | HTTP 403 total-key limit before a scored attempt |

No hinted-minus-placebo estimate exists; the JSON report records it as `null`
rather than manufacturing a number from zero attempts. The structural hint did
not break the family, but without the placebo arm that cannot be attributed
specifically to the claimed invariant. One hinted reply used an outer JSON
fence without tags; parser replay after broadening `parse_answer` extracted it
and exact verification still rejected it. Harness transcripts remain unedited.

## Use

```python
from gen_1105_5509 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=123, **DIFFICULTY["medium"])
question = render(inst)
assert verify(inst, inst["answer"]) == (True, "ok")
```

Emit from the repository root with:

```bash
bash scripts/emit.sh 1105.5509 20
```

## Caveats

This family is easy with tools: its measured reference solve is about one
millisecond. It tests recognition and exact execution, not complexity theory,
and the paper's general exponential statement does not make these planted
instances Track A. Revealing the mixing vector, omitting the row shuffle, using
small `n`, or allowing a CAS makes the task immediate.

The 0/200,000 guess result applies only to uniform `n×2` matrices over `GF(p)`;
it says nothing about a solver exploiting the coefficient rows. No external
CAS, F4/F5 implementation, or Gröbner package was run; exact Gauss–Jordan is a
strictly cheaper complete solver for this restricted family, so it is the
relevant reference. `gvlib` has no finite-field or Gröbner engine, so the module
uses a small standard-library implementation and checks it through explicit
S-polynomial reductions. The canonical key handles input-row permutation,
permutation of the `x_i`, and swapping the two tail variable pairs, but it is
not a complete invariant under every polynomial-ring automorphism. The final
placebo arm was not measured, so the three-arm diagnostic cannot distinguish
structural help from prompt-length or hint-expectation effects; rerun that arm
when OpenRouter credit is available.
