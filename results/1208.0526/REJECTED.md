# Rejected at Step 0: the constructible distributions are not the hard distributions

Paper: Mária Ercsey-Ravasz and Zoltán Toroczkai,
[*Optimization hardness as transient chaos in an analog approach to constraint
satisfaction*](https://arxiv.org/abs/1208.0526), arXiv:1208.0526.

## Decision

No generator is shipped. The prior-triage proposal—choose a Boolean assignment
and sample clauses that it satisfies—passes inverse generation (**G**) and exact
verification (**V**), but the paper gives no hardness result for that planted
distribution. The paper's hardness regime is an unconditioned random ensemble.
Sampling that ensemble while retaining a satisfying assignment would require
solving the sampled instance, which is forbidden by **G**.

The paper's other natural exact family, 3-XORSAT, does not repair the problem:
Supplementary Section G explicitly identifies it as linear and says it is better
to work directly with the parity equations. Gaussian elimination then produces a
solution in polynomial time. It therefore fails Track A's discriminating test.
The hard-core regime has no paper-supplied compact route that could justify Track
B; after leaf removal, solving the remaining core is still linear algebra.

## What the paper actually defines

The main text defines a `k`-SAT instance using `N` Boolean variables and `M`
clauses, each an OR of `k` distinct variables or their negations. A witness is a
Boolean assignment satisfying every clause. With spins `s_i in {-1,1}` and clause
signs `c_mi in {-1,0,1}`, the paper writes

`K_m(s) = 2^(-k) product_i (1 - c_mi s_i)`.

Thus `K_m(s)=0` exactly when clause `m` is satisfied, and checking a proposed
Boolean assignment is a finite exact computation.

The paper then maps a formula to the continuous system in equations (1)--(2).
The SAT solutions and their connected single-flip clusters are fixed-point
attractors. Supplementary Sections A--E analyze invariance, attraction, absence
of limit cycles, and escape from nonsolution regions. None of these results
constructs a satisfying assignment for a newly sampled hard formula without
running the search dynamics.

The parameter regimes are specific:

- For random 3-SAT, clauses are chosen uniformly at fixed
  `alpha=M/N`. The main text places the freezing transition near
  `alpha_f ~= 4.25` and the satisfiability threshold near
  `alpha_s ~= 4.26`; it reports that local search becomes exponential or fails
  beyond `alpha=4.21`, and survey-propagation methods fail beyond `4.25`.
- Random 3-SAT at `alpha=3` is explicitly used as an easy regime. Formulas
  without a core have laminar flow and smooth basin boundaries.
- Random positive 1-in-3-SAT is a locked occupation problem. A constraint is
  satisfied only when exactly one of its three unnegated variables is true. With
  `l=3M/N`, the paper gives `l_d ~= 2.256` and `l_s ~= 2.368` and studies
  `l=2.34` in the frozen regime.
- Supplementary Section G defines random 3-XORSAT as parity equations on three
  uniformly selected distinct variables. It gives the hyperloop/core transition
  `gamma_d=0.8185` and SAT/UNSAT transition `gamma_c=0.9179`, and identifies
  leaf removal as the operation exposing the core.

The paper's analog method does not turn these into polynomial-time exact digital
search. Equation (3) and Supplementary Section H concern polynomial *continuous*
time. The main text and Supplementary Section I explain that the energy has
exponential fluctuations and that a Runge--Kutta simulation takes exponentially
many discretization steps in the hard regime.

## The Step-0 certificate question

> What algorithm produces the certificate, and what does it cost?

| Candidate family | Certificate producer | Outcome |
|---|---|---|
| Uniform random 3-SAT near `alpha=4.25` | A SAT search (or the paper's numerically integrated analog search) | **G fails:** the generator learns the assignment by solving the instance. |
| Planted 3-SAT near `alpha=4.25` | The generator samples the assignment first | **H is unsupported:** conditioning every clause on one shared assignment changes the joint formula distribution. The paper's random-ensemble evidence does not transfer. |
| Uniform random positive 1-in-3-SAT near `l=2.34` | A CSP search | **G fails:** no answer-first construction for this ensemble is provided. |
| Planted positive 1-in-3-SAT | The generator samples a 1-in-3 assignment first | **H is unsupported:** it is again a different, correlated planted ensemble, with no distributional hardness theorem in this paper. |
| 3-XORSAT parity equations | Gaussian elimination over `GF(2)` | **Track A fails:** polynomial-time exact linear algebra produces the witness. |
| SAT fixed point or attractor | The same satisfying assignment, or a numerical ODE trajectory | The corner fixed point inherits the SAT generation gap; a floating trajectory is not an exact finite witness. |

For planted SAT, averaging over a uniformly random hidden assignment can make an
individual clause marginally uniform, but clauses sharing variables remain
correlated through that hidden assignment. The paper analyzes formulas whose
clauses are jointly sampled from the stated random ensemble, not this planted
mixture. Worst-case NP-completeness also does not establish hardness of the
planted distribution.

## Why Track B was not used

A random XORSAT instance would make an honest no-tool linear-algebra task, but it
does not have the second ingredient required by Track B: a compact route after
the structural insight. Below `gamma_d`, leaf removal gives the ordinary linear
procedure and describes the paper's easy, core-free regime. Above `gamma_d`, an
extensive hyperloop core survives, and the exact route is elimination on that
core. Inventing a specially circulant, triangular, tagged, or otherwise leaked
matrix would supply a compact shortcut, but that would be a new structured
benchmark distribution rather than the random XORSAT regime analyzed by the
paper. It would also need its own adversarial and distributional justification.

Likewise, declaring Track B for planted 3-SAT would be dishonest: the paper does
not provide a polynomial-time exact algorithm for that generated distribution,
so there is no reference algorithm and measured complexity to disclose.

## Gate disposition

| Requirement | Result |
|---|---|
| G — known witness by construction | Passes only after planting, which changes the hard distribution; fails for the paper's random hard ensembles. |
| H — hardness for the generated distribution | **Fails/unsupported for planted SAT and 1-in-3-SAT; fails outright for XORSAT under Track A.** |
| V — cheap exact checking | Passes for Boolean assignments and parity assignments. |
| Track B alternative | **Rejected:** the paper's hard-core objects have no compact route distinct from the mechanical solver. |
| Remaining mandatory gates | Not run after the Step-0 failure. |

Per the task's stop rule, there is intentionally no `gen_1208_0526.py`,
`selftest_report.json`, `README.md`, or hardening transcript. Creating those
files would falsely suggest that an admissible family reached Steps 1--5.
