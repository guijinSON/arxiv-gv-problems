# Rejected at Step 0: no hard, scalable witness family

Paper: John R. Doyle, [*Preperiodic points for quadratic polynomials with small cycles over quadratic fields*](https://arxiv.org/abs/1509.07098), arXiv:1509.07098v2.

## Decision

The prior-triage family—plant a rational orbit for a quadratic polynomial over a
quadratic field and ask for that orbit—clears **G** and **V**, but fails **H on
both tracks**. I therefore stopped before writing a generator or running the LLM
hardening loop.

This is not a rejection merely because an efficient algorithm exists. The two
required costs are comparable:

| formulation | mechanical certificate route | compact route | conclusion |
|---|---:|---:|---|
| The construction parameter is supplied | Proposition 4.1(c)'s displayed rational formulas: **19 exact field operations** to produce all three cycle points (43 including construction of \(c\) and three verification substitutions) | the same formulas: **19 exact field operations** | ratio 1; there is nothing shorter to discover |
| Only \(K,c\) are supplied | construct and factor the degree-6 period-3 dynatomic polynomial over the stated field | the same fixed-degree factorization; the paper's inverse \(t=\alpha+f_c(\alpha)\) already requires the unknown witness | no compact route distinct from the mechanical route |

For a concrete cap-scale measurement of the second row, I sampled five
416-bit rational parameters \(t\), formed \(c\) by Proposition 4.1(c), and asked
SymPy 1.12 to factor the exact degree-6 dynatomic polynomial over \(\mathbb Q\).
The three-point JSON answer was at most **1,895 characters** (just below the
2,000-character cap). Factorization took **0.391 seconds median** and **0.530
seconds maximum**. At 448 bits the answer was already 2,039 characters and over
the cap. Thus coefficient growth cannot create a meaningful Track-B gap before
the answer becomes a transcription/calculator test.

## What the paper actually defines

Section 1 defines the native object as \(f_c(z)=z^2+c\) over a number field
\(K\), with a directed edge \(\alpha\to\beta\) exactly when
\(f_c(\alpha)=\beta\). Section 2 defines the dynatomic polynomial
\(\Phi_N(x,c)\), exact period, and (strongly) admissible preperiodic graphs.
Table 1 gives

\[
\deg_x\Phi_N=2,2,6,12\qquad(N=1,2,3,4).
\]

These fixed degrees are the decisive easy regime for the proposed search task.
Exact factorization over a quadratic number field is an efficient general
method, so a Track-A claim would be false for every generated distribution.

The source paper then makes generation still more direct:

- Proposition 4.1 gives explicit necessary-and-sufficient parametrizations for
  periods 1, 2, and 3, including all three points of a 3-cycle.
- Proposition 4.3 gives an isomorphism from
  \(v^2=-u(u^2+1)(u^2-2u-1)\) to the period-4 modular curve, with explicit
  forward and inverse maps.
- Theorems 4.5 and 4.12 show that a quadratic pair has at most one 3-cycle and
  at most one 4-cycle, respectively; Theorem 4.12 again writes all four points
  explicitly.
- Section 3 explicitly notes that “obvious” quadratic points on a
  hyperelliptic model are manufactured by choosing rational \(x\) and adjoining
  \(\sqrt{f(x)}\). This is another direct evaluation, not a hard recovery task.

Consequently, inverse generation is easy and verification by exact iteration is
cheap, but the very formulas that provide the planted certificate also solve
the exposed-parameter problem.

## Why hiding the parameter does not rescue Track B

For period 3, Remark 4.2 recovers the modular parameter by
\(t=\alpha+f_c(\alpha)\); this is an inverse *after* a periodic point is known,
not a shortcut from \(c\) to that point. For period 4, Proposition 4.3 similarly
recovers \(u\) and \(v\) from \(\alpha,c\), again after the witness is known.
Hiding \(t\) or \((u,v)\) therefore removes the direct construction but supplies
no compact route: a solver must factor \(\Phi_3\) or \(\Phi_4\), just as the
mechanical algorithm does. Revealing enough auxiliary data to invert the map
returns to the first row of the cost table.

Affine conjugation does not help. Section 1 states that every quadratic
polynomial is linearly conjugate to a unique \(z^2+c\). For
\(\ell(z)=az+b\), the conjugate polynomial has coefficients
\(A=a\), \(B=2b\), and \(C=(b^2+c-b)/a\), so normalization recovers
\(a=A\), \(b=B/2\), and \(c=AC-b^2+b\) in a constant number of exact
operations. The mechanical and compact routes again coincide.

## Other apparent families

- The nonexistence and classification theorems do not provide bounded,
  instance-local negative certificates. Their proofs use Jacobian ranks,
  Chabauty bounds, torsion computations, and Magma calculations. Asking for the
  classification proof would fail the witness rule (**G/V**), while returning a
  member of a finite table would not be unlimited or hard.
- Definition 2.1's admissible graphs can be made arbitrarily large, but
  admissibility is only a necessary condition for realization as
  \(G(f_c,K)\), not a theorem-backed realization construction. Replacing the
  arithmetic-dynamical problem by completion or search on arbitrary admissible
  graphs would be a convenience discretisation, and its degree/cycle checks are
  elementary graph algorithms.
- Increasing coefficient height is the only remaining scale parameter for the
  explicit small-cycle formulas. It lengthens the numeric answer and exact
  arithmetic without enlarging the mathematical search; the output cap binds
  before it yields a defensible Track-B compression gap.

In short: the native positive witnesses are generatable and exactly verifiable,
but directly produced by constant-size formulas or fixed-degree factorization.
The native negative claims lack executable bounded certificates. No one problem
family in the paper satisfies G, H, and V simultaneously.
