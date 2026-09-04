# Rejected: arXiv 1707.01795

Paper: Arnab Bhattacharyya, Suprovat Ghoshal, and Rishi Saket,
[*Hardness of learning noisy halfspaces using polynomial thresholds*](https://arxiv.org/abs/1707.01795)
(2017).

## Decision

No family in this paper supports all of **G, H, and V** under the required
generator distribution. The prior-triage proposal—sample a halfspace, label
sampled points with it, and corrupt a bounded fraction—can be generated with a
known witness and checked exactly, but it fails **H as a justified Track A
family**. The paper proves worst-case promise hardness for instances obtained
from a particular Smooth Label Cover reduction. It does not prove hardness for
randomly planted noisy-halfspace instances, and inverse planting does not
preserve the reduction's hardness.

I therefore stopped at Step 0. No generator, self-test report, README, or LLM
hardening transcripts were created. Oracle failures on an invented planted
distribution could not supply the missing theorem-and-regime basis required by
Track A.

## The paper's exact problem and hardness regime

Section 1 defines a halfspace as

\[
x \longmapsto \operatorname{sign}(\langle v,x\rangle-c)
\]

and measures its accuracy on a distribution of points in
\(\mathbb R^n\) carrying labels in \(\{-1,1\}\). Theorem 1.1 states that, for
fixed constants \(d\geq 1\) and \(\delta>0\), it is NP-hard to distinguish:

- a YES instance on which some halfspace classifies at least a
  \((1-\delta)\)-fraction correctly; from
- a NO instance on which every degree-\(d\) polynomial threshold function
  classifies at most a \((1/2+\delta)\)-fraction correctly.

This is not an average-case or planted-distribution statement. Sections 2 and
3 identify the precise hard regime. The starting object is the Smooth Label
Cover instance in Theorem 2.1, with

\[
k=7^{(J+1)R},\qquad L=2^R7^{JR},
\]

constant graph degree depending on \(J,R\), preimages of size at most \(4^R\),
the stated smoothness condition, weak expansion, perfect completeness, and
soundness below \(2^{-c_0R}\). Theorem 3.1 chooses \(R,J\) from \(d,\xi\) and
reduces those instances to labeled real points using \(T=10d\), a correlated
Gaussian dictatorship test, independent coordinate noise, and folding onto
the subspace orthogonal to all Label Cover constraints. Section 4.5 then
replaces the Gaussian test by a finite discretization.

Thus the theorem applies to outputs of that reduction, not to arbitrary point
clouds labeled by a planted hyperplane.

## What produces the completeness witness

Section 3.4 gives the witness explicitly *once a satisfying Label Cover
labeling is already known*. For a labeling \(\sigma:V\to[k]\) satisfying every
edge, it defines

\[
L^*(Y)=\sum_{v\in V}Y^v_{\sigma(v)}.
\]

The folding constraints put its coefficient vector in the required subspace,
and a union bound shows that it classifies at least a \((1-\epsilon T)\)-fraction
of the test examples correctly. Constructing the coefficient vector from
\(\sigma\) is linear in \(|V|\); checking its empirical accuracy is a scan of
the finite labeled set.

This establishes G and V only when the generator possesses \(\sigma\). It does
not establish H for a generator that samples \(\sigma\) first. The NP-hardness
theorem says that arbitrary reduced instances are hard to distinguish; it does
not say that satisfiable instances assembled around a sampled labeling are
hard on average. The paper gives no distribution-preserving inverse generator
for its Smooth Label Cover instances and no theorem that hides a planted
labeling under the required smoothness and expansion conditions.

Starting instead from a genuinely hard Label Cover instance does not fix G:
the generator would then have to solve that instance to obtain the completeness
witness. Starting from an easy instance whose labeling is known fixes G but
abandons the only hardness regime proved in the paper.

## Why the prior-triage family is unsupported

The proposed sampler discards all load-bearing parts of the reduction:
Smooth Label Cover projection maps, the \(k,L,J,R\) regime, the correlated
\(T\)-block test, and folding. Its difficulty would be a claim about a new
planted distribution, not a consequence of Theorem 1.1 or Theorem 3.1.

The paper also explicitly identifies natural easy regimes in Section 1:

- noiseless halfspace learning admits a linear-programming separator;
- random classification noise has efficient learning algorithms, including a
  proper learner;
- adversarial noise is tractable under several well-behaved input
  distributions; and
- minimizing error under the uniform distribution on a sphere has a PTAS.

These results do not prove that every possible planted sampler is easy, but
they prevent an honest `hardness_basis` from citing this paper for the proposed
one. Point distribution and noise mechanism are exactly the details that
separate those algorithms from the paper's worst-case result.

The “finite field constructions” note in prior triage is also incorrect. No
finite-field construction is used by the paper's reduction. Section 1.1 only
discusses noisy parity over \(\mathbb F_2\) as related work; the paper's native
objects and its reduction are labeled points, real polynomials, real
subspaces, and Gaussian/discretized real test distributions. Replacing them
with a finite-field task would be an unlicensed convenience reduction rather
than coverage of this paper.

## Other paper-native witness families considered

| Candidate | Outcome | Reason |
|---|---|---|
| Output a high-accuracy halfspace for a reduced YES instance | G/H conflict | The witness is obtained from a satisfying Label Cover labeling. Generating a known labeling by planting loses the paper's hardness guarantee; using an arbitrary hard source instance loses the known certificate. |
| Output a certificate that no good PTF exists | V fails | The NO case is proved by a global soundness argument and randomized decoding. The paper gives no bounded, cheaply executable refutation object attached to an individual instance. |
| Find the distinguished pair \((j^*,d^*)\) from Section 4 | Track A H fails | Given the polynomial coefficients and noise set, compute every coefficient mass \(c_{i,j,d'}^2\) and scan the \(Td\) pairs. This is polynomial-time coefficient accounting—the same work the checker would perform. |
| Find a “good” index in the linear-mass Lemma of Section 7 | Track A H fails | Expand \(Q=(\sum_j W_j)S\), extract each \(W_j\)-linear part \(Q_{j,1}\), compute its squared coefficient norm, and scan. The theorem guarantees abundance, while direct coefficient scanning finds a witness in polynomial time. |
| Recast either structural lemma as Track B | No supported compact route | The general input is an arbitrary coefficient table. The paper's proof supplies bounds and an iterative argument, not a sub-300-operation shortcut for recovering the witness. Planting a special factorization or symmetry would make the shortcut an invented property of the generator, not a result or construction in the paper. |

The structural-lemma candidates are valid finite witnesses, but they illustrate
the prompt's discriminating test exactly: their certificates are outputs of a
straight polynomial-time coefficient scan. They therefore cannot be presented
as Track A. A Track B family would additionally require a genuine compact route
and measured separation from four in-context attacks; the paper supplies no
such route, and manufacturing one would move the benchmark's substance away
from this paper.

## Gate outcome

| Requirement | Result | Evidence |
|---|---:|---|
| G — certificate known by construction | Possible in isolation | Plant a rational halfspace, or begin with a known satisfying Label Cover labeling and use Section 3.4's \(L^*\). |
| H — justified for the generated distribution | **Fail** | Theorems 1.1 and 3.1 are worst-case reductions from the exact Smooth Label Cover regime of Theorem 2.1; no planted-instance hardness theorem is given. The paper-native structural witnesses are recoverable by coefficient scans. |
| V — cheap exact witness checking | Possible in isolation | For rational finite points, evaluate the submitted affine form exactly and count agreements. |
| Overall | **Rejected at Step 0** | G, H, and V must hold simultaneously. |

No G1–G9 measurements were fabricated after the analytical H failure, and
`scripts/harden.py` was not run. The rejected distribution has no honest Track
A theorem-and-regime claim, while the paper provides no qualifying Track B
compression problem.
