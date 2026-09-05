# Rejected at Step 0: the native families are explicitly parametrized conics

Paper: Shamik Das and Debajyoti De, [*Some Remarks on
\(\tau\)-Congruent Numbers*](https://arxiv.org/abs/2605.27639),
arXiv:2605.27639v1 (26 May 2026).

## Decision

No problem generator is shipped. The prior-triage proposal—sample a rational
triangle, compute its associated congruent number, and ask for the triangle—can
meet **G** by inverse generation and **V** by exact rational substitution. On the
paper's actual geometric families, however, it fails **H on Track A** because
the certificate is produced by an explicit genus-zero parametrization. It also
fails **H on Track B**: the mechanical route and the compact route are the same
constant-size formula, or at most the same quadratic inversion. Increasing the
bit length makes both routes perform the same handful of larger integer
operations and turns the task into arithmetic/transcription rather than
structural compression.

The unrestricted congruent-number inverse problem mentioned in the introduction
does not rescue the proposal. The paper gives no average-case hardness theorem
or generated parameter regime for it. Sampling an arbitrary Pythagorean/Heron
triangle and publishing only its area would create a new planted rational-point
distribution, for which worst-case folklore about elliptic curves does not
establish Track A. Nor does the paper give a solver-visible compact route that
would make that distribution Track B.

Per the task's Step 0 instruction, work stopped before module, self-test, and
oracle construction. No gate or oracle result was fabricated after the
analytical H failure.

## Exact definitions and certificate-producing results

Definition 1.1 fixes

\[
  \tau=\tan(\theta/2)\in\mathbb Q_{>0}
\]

and calls a positive integer \(n\) \(\tau\)-congruent when a rational-sided
triangle has angle \(\theta\) and area

\[
  n=\frac{ab\tau}{1+\tau^2}.
\]

The paper then imposes geometric normalizations which make every relevant
curve rational of genus zero:

- **Section 2, equation (2.2) and Theorems 2.2--2.3.** A triangle with unit
  incircle and prescribed angle is obtained from

  \[
    y=\frac{\tau x+1}{x-\tau},\qquad
    (a,b,c)=\left(y+\tau^{-1},x+\tau^{-1},x+y\right).
  \]

  Thus one freely chosen rational \(x>\tau\) produces the complete geometric
  witness. The exact area computed in the proof is \(xy/\tau\); the paper writes
  \(\tau xy\) as the associated representative modulo
  \(\mathbb Q^{\times 2}\). Their ratio is the rational square \(\tau^2\).

- **Section 3, Theorems 3.2 and 3.4.** For the ellipse

  \[
    E_a:\ (X-a)^2/a^2+a^2(Y-1/a)^2=1,
  \]

  the determinant-one map \(T_a(X,Y)=(X/a,aY)\) reduces the problem to a unit
  circle. Every circumscribing right triangle is parametrized by

  \[
    u=a(t+2),\qquad v=\frac{2}{a}\left(1+\frac1t\right),\qquad
    \mathcal A=\frac{(t+2)(t+1)}t.
  \]

- **Section 4, Proposition 4.1.** A right triangle of circumradius \(R\) is
  produced directly from any rational \(0<t<1\):

  \[
    (a,b,c)=\left(2R\frac{1-t^2}{1+t^2},
                   2R\frac{2t}{1+t^2},2R\right).
  \]

- **Section 5, Proposition 5.1 and Theorem 5.2.** Unit-excircle right triangles
  are again parametrized by rational points on one of three displayed genus-zero
  curves. For example, the \(c\)-excircle case is

  \[
    xy+x+y=1,\qquad (a,b,c)=(1-y,1-x,x+y),
  \]

  so choosing \(x\in(0,1)\cap\mathbb Q\) and setting
  \(y=(1-x)/(1+x)\) emits the witness immediately.

These are classification and construction results, not computational-hardness
results. The paper contains no hard parameter regime, NP-hardness reduction, or
distributional hardness theorem.

## The fatal algorithms

### Asking for any normalized triangle

This version has a direct answer on every input. In Section 2, choose any
rational \(x>\tau\) (for example \(x=\tau+1\)), evaluate equation (2.2), and
write the three displayed sides. In Section 3 choose any positive rational
\(t\); in Section 4 choose any rational \(0<t<1\); in the Section 5
\(c\)-excircle family choose, for example, \(x=1/2\) and \(y=1/3\).

Consequently, a generator can make the syntactic coefficient space enormous,
but a solver never searches that space. A domain-aware candidate sampler would
sample the free rational parameter and satisfy the geometry by construction.
The construction itself is the solver.

### Adding the generated area does not help

For the Section 2 unit-incircle family, let \(A\) denote the exact area. The
curve equation and the proof of Theorem 2.3 give

\[
  xy=A\tau,\qquad x+y=A-\tau^{-1}.
\]

Therefore \(x\) and \(y\) are simply the two roots of

\[
  z^2-(A-\tau^{-1})z+A\tau=0.
\]

The only ambiguity swaps the two adjacent sides, and either answer is valid.
This takes a constant number of exact rational operations and an exact square
root of a promised rational square.

The same collapse occurs in every other section:

| Native family | Target quantity | Exact inverse |
|---|---|---|
| Section 3 ellipse | \(A=(t+2)(t+1)/t\) | \(t^2+(3-A)t+2=0\) |
| Section 4 circumcircle | fixed \(R,A\) | \(ab=2A\), \((a+b)^2=4R^2+4A\), followed by a quadratic |
| Section 5 \(a\)- or \(b\)-excircle | \(A=x(x+1)/(1-x)\) | \(x^2+(1+A)x-A=0\) |
| Section 5 \(c\)-excircle | \(A=x(1-x)/(1+x)\) | \(x^2+(A-1)x+A=0\) |

Thus conditioning the inverse generator on the area does not create a search
problem; it creates a degree-two equation whose coefficients are already in the
statement.

## Mechanical cost versus compact route

I measured the two most promising formulations with Python's exact
`fractions.Fraction`, using 256-bit numerators and denominators. Each timing is
the average of 20,000 constructions on this runner.

| Formulation | Mechanical algorithm | Measured cost | Compact route | Track-B result |
|---|---|---:|---:|---|
| Section 2, parameters \((\tau,x)\) supplied | Evaluate (2.2), then Theorem 2.2 | 10 rational arithmetic operations; **14.279 microseconds** | The identical displayed formula, 10 operations | No gap |
| Section 2, exact area \((\tau,A)\) supplied | Form the quadratic above and take its promised exact square root | about 12 rational operations plus two integer square roots; **27.865 microseconds** | The identical quadratic, with the same operations | No gap |
| Section 3, parameters \((a,t)\) supplied | Evaluate \(u,v,A\) | about 8 rational operations; **6.859 microseconds** | The identical displayed formula | No gap |
| Section 3, exact area \(A\) supplied | Solve \(t^2+(3-A)t+2=0\) | about 5 rational operations plus two integer square roots; **12.656 microseconds** | The identical quadratic | No gap |

At this bit size the serialized Section 2 triangle used 1,277 characters and
the Section 3 pair of legs used 643, so these are already representative of
the largest comfortable answer-cap scale. Larger coefficients do not increase
the number of algebraic steps; bit-operation costs increase on both sides in
the same way. The mechanical/compact cost ratio is effectively one, whereas
Track B requires a substantial computation replaced by a short structural
route.

## Why nearby variants do not qualify

### Hide a rational square factor

The tables frequently pass from a rational area to its class modulo
\(\mathbb Q^{\times 2}\). Multiplying the published representative by a secret
rational square can defeat the quadratic equality inversion, but it also
removes the paper's compact route. Recovering a triangle then becomes the
general rational-point problem on the elliptic curve quoted in Section 1,

\[
  E_{\tau,n}:Y^2=X(X-n\tau)(X+n\tau^{-1}).
\]

The paper supplies neither an efficient reference algorithm nor a sub-300-step
solver-visible shortcut for that masked distribution, so it is not Track B.
It also supplies no average-case hardness theorem for the distribution, so it
cannot honestly be declared Track A merely because bounded searches happen to
fail.

Canonicalization introduces a second problem: equivalent rational
representatives differ by arbitrary squares. Computing a canonical squarefree
representative requires the very integer-factorization work the mask was meant
to hide, unless the canonical representative is included in the instance. If
it is included, the mask contributes no problem data.

### Ask for the squarefree representative in the tables

For a generic rational \(t\), producing the squarefree part of
\(t(t+1)(t+2)\) requires factoring numerator and denominator. Factoring a random
generated value to obtain the answer would violate G: the generator would be
solving its own instance. The paper provides only the five small examples in
Table 2, not an unlimited theorem-backed family of parameters with known
factorization. Constructing an external factoring benchmark around the formula
would test the wrapper rather than the paper's geometric results.

### Use the unrestricted congruent-number problem

One could sample Euclid parameters, form an integer-area Pythagorean triangle,
publish only the area, and retain the sides as an inverse-generated witness.
That gives an exact witness and may be difficult for some point-search programs,
but the paper proves no complexity statement for this planted distribution.
Its only relevant statement is the background equivalence with a rational point
on \(E_{\tau,n}\). Track A requires evidence for the generated distribution,
not an appeal to the possible difficulty of unrelated elliptic curves. For
Track B, recovering the hidden Euclid parameters is the mechanical work itself;
the paper gives no shorter invariant or change of variables which recovers
them.

### Use products of three consecutive integers

Theorem 3.4(d) says \(t(t+1)(t+2)\) is congruent and yields the familiar triangle

\[
  \bigl(t(t+2),\ 2(t+1),\ t^2+2t+2\bigr).
\]

Given the integer, however, recognizing it means solving
\(k^3-k=N\) for \(k=t+1\), an ordinary exact integer-cube-root check. At small
sizes it is executable by hand; at large sizes it is a big-integer arithmetic
test, not a geometric insight, and the answer digits themselves approach the
output cap. If \(t\) is encoded in an easily recognized decimal pattern, the
obvious by-hand ansatz succeeds and G6 fails. If it is not, the intended route
is the same long arithmetic as the mechanical route and G9(c)'s purpose is
defeated.

### Add decoys or unrelated transformations

Hiding one valid triangle among a large list, applying a general affine map not
used by the paper, or encoding the rational-point problem as SAT/graph search
would make the difficulty come from a benchmark-convenience wrapper. The only
paper-licensed transformation is the diagonal area-preserving map \(T_a\), and
its inverse is printed in equation (3.2). Such variants would not be native
coverage of the paper.

## Track and gate outcome

| Requirement | Result | Evidence |
|---|---:|---|
| G -- certificate known by construction | Passes in isolation | Sample the free rational parameter and evaluate the paper's formula. |
| V -- cheap exact verification | Passes in isolation | Exact rational law of cosines/Pythagoras, area, and inradius/exradius or tangency identities. |
| H -- Track A | **Fail** for the paper's families | Equations (2.2), (3.2), and the parametrizations in Theorems 2.2, 3.2, 5.2 and Proposition 4.1 are direct solvers; no hard distribution theorem is present. |
| H -- Track B | **Fail** | Forward construction is 8--10 rational operations; target-area recovery is one quadratic. Mechanical and compact routes coincide. |
| G4 | Fails for the “any triangle” versions | Sampling the freely stated rational parameter and applying the parametrization succeeds by construction. |
| G6 | Fails analytically | The displayed parametrization or quadratic inversion succeeds on every generated native instance. |
| G7 | Does not rescue H | Increasing coefficient bit length changes operand size, not algebraic route length. |
| G9(c) | Does not rescue H | Answer-cap-sized instances already take only 6.9--27.9 microseconds mechanically; larger digits test arithmetic and transcription. |
| Overall | **Rejected at Step 0** | No paper-native family clears G, H, and V under either track. |

The prior triage was right about inverse generation and exact geometric
verification, but it missed that the paper's contribution is a complete
one-parameter classification. That same classification is a solver for every
proposed witness task in the normalized geometric regimes.
