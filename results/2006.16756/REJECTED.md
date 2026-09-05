# Step-0 rejection: arXiv:2006.16756

Paper: [Farzali Izadi, *Euclidean Geometry and Elliptic Curves*](https://arxiv.org/abs/2006.16756), arXiv:2006.16756v2.

## Decision

No generator is shipped. The natural exact-witness family passes **G** and **V** but
fails **H on both tracks**. This was decided from the full paper and its LaTeX source,
before writing a generator, as required by Step 0.

The paper describes explicit parametrized constructions; it does not state a
complexity or distributional-hardness result. Section 1 calls the article a review,
says that it demonstrates results from earlier papers, and leaves their details to
those papers. Consequently there is no theorem or parameter regime supporting a
Track-A claim for instances obtained by sampling the displayed parameters.

Track B does not rescue the natural family. The mechanical certificate-producing
algorithm and the compact route are the same constant-length calculation, so there is
nothing structural to discover.

## The discriminating calculation

Section 4, Theorems 4.1 and 4.2, uses

\[
E_k:\quad y^2=(x+a(k)b(k))(x+b(k)c(k))(x+a(k)c(k)),
\]

with the three displayed polynomial functions `a(k)`, `b(k)`, and `c(k)`. A faithful
candidate problem would provide these native rational objects and ask for a rational
point with nonzero `y`. But the instance itself gives

\[
P=(0,a(k)b(k)c(k)),
\]

because the right-hand side at `x=0` is `(abc)^2`. Verification is exact substitution,
so G and V are immediate. H is not:

| route | exact work at a would-be 256-bit shipping parameter |
|---|---:|
| mechanical formula evaluation | 2 integer multiplications (`a*b`, then `*c`) |
| compact route/by hand | the same 2 integer multiplications |
| expanded-cubic variant | 1 exact integer square root of the square constant term |

A deterministic Python benchmark (`random.Random`, 10,000 admissible positive
256-bit integer values of `k`) took 0.020803 seconds for the direct formula, or 2.080
microseconds per instance. On 2,000 independently sampled 256-bit values, exact
`math.isqrt` of the expanded cubic's constant term had median 8.480 microseconds and
95th percentile 8.890 microseconds. The resulting `y` had about 617 decimal digits,
comfortably below the answer-character cap. Thus this is not a cap-bound case: it is
an easy family. The obvious `x=0` attack succeeds on every generated instance.

These numbers also satisfy the required Track-B comparison. The mechanical cost is
2 operations and the compact route is 2 operations (or one square-root operation in
both descriptions after expansion). There is no million-operation mechanical route
versus a short structural shortcut.

## Why the other sections do not supply a harder witness family

- Section 2, equations (2.2)--(2.4), writes down `P1` through `P5` explicitly.
- Section 3, equations (3.7)--(3.9), again writes down five explicit rational sections.
- Section 7 states that the quadrilateral-to-curve correspondence gives explicit
  formulas for the curve and two non-2-torsion points.
- Section 8 gives a fixed one-parameter curve family and a closed-form torsion
  characterization (Theorem 8.2), not a growing search regime.
- Section 9, equations (9.4)--(9.6), gives the point `(s,S)`, the birational
  substitution, and all three rational 2-torsion points explicitly.

In each verifiable point-finding version, the certificate producer is evaluation of a
displayed formula followed by substitution. Sampling larger numerators increases
bit-length but not the number of structural steps. Expanding the equations only turns
the same task into an exact square-root or fixed-degree factorization, still comparable
to the shortcut.

Asking instead for positive rank, exact rank, linear independence of the displayed
sections, or a complete torsion subgroup does not fix H while retaining the required
checker: a point-on-curve substitution is not by itself a certificate of infinite
order or independence, and the paper's specialization and torsion arguments are not
finite objects that the requested checker can simply inspect.

Finally, hiding the paper's parameters behind unrelated affine masks, large decoy
sets, or a synthetic chain of coordinate changes could manufacture a search puzzle,
but its difficulty would come from the added concealment rather than a theorem or
construction in this paper. It would not justify Track A, and the paper supplies no
Track-B mechanical/compact gap for that modified distribution.

## Gate classification

- **G:** achievable by theorem-backed/direct construction.
- **V:** achievable by exact rational substitution.
- **H / Track A:** fails; there is no distributional-hardness theorem or regime, and
  the sampled displayed families have constant-length witness formulas.
- **H / Track B:** fails; measured mechanical cost and compact-route length are the
  same (2 exact multiplications), so the family tests formula evaluation rather than
  recognition of a compressed route.

No `gen_2006_16756.py`, self-test report, or hardening transcript was created because
the task explicitly requires stopping when Step 0 shows that G, H, or V fails.
