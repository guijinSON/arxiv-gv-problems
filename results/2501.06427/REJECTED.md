# Rejected: arXiv 2501.06427

Paper: Brice Huang and Mark Sellke, [*Strong Low Degree Hardness for Stable Local Optima in Spin Glasses*](https://arxiv.org/abs/2501.06427) (v2, 31 March 2026).

## Decision

This paper does not provide one distribution that satisfies **G (inverse generation)** and **H (supported hardness)** at the same time. Its main search problems are hard only when the disorder is sampled from an **unconditioned random ensemble**. Sampling a witness first and constructing the disorder around it instead produces a planted/conditioned ensemble, and none of the paper's theorems claims hardness for that ensemble. The paper calls its principal result the first strong low-degree lower bound for a random search problem *without planted structure*, so this distinction is part of the theorem rather than a cosmetic implementation choice.

I therefore stopped at Step 0. No generator, self-test report, README, or oracle transcript was created: any such deliverable would either misapply the paper's hardness theorem or manufacture a different problem family whose hardness is unsupported here.

## What the full paper actually defines

Section 1.1 defines the Sherrington--Kirkpatrick Hamiltonian on spins `sigma in {-1,+1}^N`:

```text
H_N(sigma) = (1/sqrt(N)) sum_{i,j} g_ij sigma_i sigma_j,
```

where every `g_ij` is an independent standard Gaussian. For coordinate `i`, the paper defines the local field from half the energy lost by flipping that spin. Definition 1.1 calls `sigma` a `(gamma, delta)`-gapped state when at most `delta*N` coordinates have signed local field below the positive constant `gamma`. Thus the exact witness is a length-`N` sign vector, and checking it only requires recomputing all local fields.

Theorem 1.1 gives the relevant hardness regime: for every fixed `gamma > 0`, there is a fixed `delta > 0` such that, on an **ordinary IID-Gaussian SK Hamiltonian**, rounded deterministic polynomial algorithms of degree `D = o(N)` succeed with probability `o(1)`. The theorem also gives exponential failure for fixed-Lipschitz algorithms and a stretched-exponential bound for `D <= log(N)/11`. Section 2 proves the result using correlated Hamiltonians, separation of gapped states, and a disorder-chaos obstruction. Section 3.1 strengthens the low-degree conclusion.

The paper is careful about what this means. Section 1.2 labels the claim *strong low degree hardness*, Section 1.3 describes the resulting exponential-runtime interpretation as a heuristic, and explicitly warns that low degree is not a universally valid proxy for runtime. This is not an NP-hardness theorem for arbitrary coupling matrices.

The paper also treats these other search problems:

| Full-text location | Witness problem | Hard input distribution/regime |
|---|---|---|
| Section 3.2.1 | a spin attaining a near-ground-state energy in an even pure `k`-spin model, `k >= 4` | unconditioned Gaussian tensor; degree `o(N)` |
| Section 3.2.2 | a sign vector satisfying every Ising-perceptron constraint | unconditioned IID Gaussian rows; specified small symmetric or sufficiently negative asymmetric margins; degree `o(N/log N)` |
| Section 3.3.1 | an independent set larger than the greedy scale | `G(N,d/N)` with sufficiently large fixed `d`; target at least `(1+iota)N log(d)/d`; degree `o(N)` |
| Section 3.3.2 | a satisfying assignment | random `k`-SAT with large fixed `k` and density `kappa*2^k log(k)/k`, `kappa > 4.911`; degree `o(N)` |
| Section 3.4 | an independent set above the greedy scale | unconditioned `G(N,1/2)`; degree `o(log^2 N)` |
| Section 4 | a spherical well reached by Langevin dynamics | unconditioned mixed spherical spin glass, no external field, fixed dimension-free time |

Every hardness statement above is average-case and uses the stated unconditioned ensemble.

## Why the suggested SK generator fails

The suggested construction is to sample `sigma` first and choose couplings that make it locally stable. It has attractive G and V properties: `sigma` is known before the instance is built, and a checker can substitute the signs and compare `N` local-field margins.

It does **not** inherit H from Theorem 1.1. Under the theorem, the couplings are IID centered Gaussians before any solution is chosen. Requiring the sampled `sigma` to have all or nearly all positive margins conditions `N` correlated linear forms of those couplings. Directly biasing or repairing entries is an even larger distribution change. In the gauge where the planted spin becomes the all-ones vector, the altered row sums expose exactly the signal that spectral, degree, local-field, and iterative attacks can exploit. Randomly permuting vertices or flipping gauges hides labels but does not restore the IID Gaussian law.

Exact conditional sampling would not cure the theorem mismatch. It would generate the SK law conditioned on one specified vector being gapped (equivalently, a size-biased planted law after hiding the vector), not the unconditioned SK law of Theorem 1.1. The paper proves no quiet-planting, contiguity, indistinguishability, or planted-recovery lower bound connecting those distributions. Indeed, Section 1.2 contrasts its result with planted problems and says the testing tools used for planted structure provide a different notion of evidence.

There is no distribution-preserving answer-first shortcut in the paper. Sampling an ordinary SK Hamiltonian and then locating one of its gapped states would preserve H, but it asks the generator to solve the very search problem being posed. Rejection-sampling an IID Hamiltonian until an independently sampled spin is gapped has exponentially small acceptance for a strict constant gap and is just another way to sample the conditioned law. Running ordinary single-spin local improvement only guarantees a marginal local optimum; it does not supply the positive constant gap required by Theorem 1.1, and the paper's introduction explains that ordinary dynamics are expected to remain marginal.

There is also an exactness issue. The theorem uses real Gaussian couplings. Python floats do not provide an exact mathematical Gaussian instance or exact comparison at the margin boundary. Replacing them by bounded integers or rationals would make verification exact, but the paper proves no corresponding hardness theorem for that disorder distribution.

## Why the other paper families do not rescue the task

### Sparse or dense independent set

Choosing a vertex subset first and suppressing its internal edges gives a valid planted independent set and an exact cheap verifier. However, Section 3.3.1 concerns an ordinary `G(N,d/N)` sample, and Section 3.4 concerns ordinary `G(N,1/2)`. Suppressing all planted internal edges conditions the graph and creates a planted-subgraph model. Neither result covers it. At or below the paper's greedy target, a simple greedy algorithm is an explicitly identified easy regime; above it, the only hardness evidence in the paper is for the unplanted graph.

### Random `k`-SAT

Sampling an assignment and retaining only clauses it satisfies is standard planting, but the result in Section 3.3.2 samples each of the `kM` literals independently and uniformly with no conditioning on an assignment. The paper supplies no quiet-planted clause distribution and no transfer theorem. Its asymptotic hard regime also requires `k` sufficiently large while using clause density proportional to `2^k log(k)/k`, making a literal inline instance impractically large before the unspecified asymptotic threshold is safely reached.

### Ising perceptrons

Conditioning Gaussian rows to put a sampled sign vector inside every required interval again changes the unconditioned Gaussian ensemble of Section 3.2.2. In addition, unrestricted Gaussian coefficients and interval comparisons are not exact standard-library arithmetic, while rational discretization is outside the stated theorem.

### Near-ground-state spin optimization

The witness is accepted by comparison with a threshold involving the asymptotic Parisi value `GS(k)-delta`, neither supplied as exact finite data nor suitable for the requested exact standard-library checker. Planting a high-energy spin changes the Gaussian tensor distribution. Asking for the actual optimum would additionally make optimality the claim, which the task explicitly forbids.

### Spherical wells and Langevin dynamics

A spherical well is a real vector satisfying a small-gradient condition and an eigenvalue condition on the Riemannian Hessian. This violates the ban on real-number answers and does not admit the requested cheap exact substitution checker. The theorem is also a negative statement about what one particular dynamics cannot reach in fixed time, not a hard inverse-generatable witness family.

## Easy regimes and limits that matter

- Section 1.3 states only a heuristic correspondence between degree `D` and roughly exponential-in-`D` runtime; it notes counterexamples to a universal correspondence.
- Sections 1.3 and 3.5 construct degree `O(N)` algorithms that approximate Ising spin-glass ground states, showing the low-degree lower-bound range is sharp for that optimization task.
- Section 1.4 notes that sufficiently strong external field makes the spherical landscape topologically trivial and allows low-temperature Langevin dynamics to reach the global optimum rapidly; the spherical theorem therefore excludes external field.
- Section 3.3.1 records a simple greedy independent-set algorithm at approximately `N log(d)/d`; hardness is only claimed above `(1+iota)` times that scale and only for ordinary random graphs.
- Section 3.3.2 records an algorithmic regime for random `k`-SAT below approximately `2^k log(k)/k`; the strong low-degree result uses the larger factor `kappa > 4.911` and sufficiently large fixed `k`.
- Section 3.4 records that greedy finds approximately `log_2 N` vertices in `G(N,1/2)`; the hard target is above that scale, while brute force in `exp(O(log^2 N))` time reaches maximum independent sets.

These boundaries prevent weakening the target merely to make answer-first generation easier.

## Gate outcome

| Requirement | Result |
|---|---|
| G -- sample the witness first | Possible only after conditioning or modifying the random input; the resulting planted distribution is not the distribution in the hardness theorem |
| H -- no known polynomial/closed-form method in the generated regime | **Unsupported/fail:** all relevant lower bounds are for unconditioned ensembles, not the answer-first planted ensembles |
| V -- cheap exact witness verification | Passes algebraically for rational SK couplings, independent sets, and SAT assignments, but rational SK is outside the theorem; Gaussian and spherical formulations have exact-real issues |
| G4/G6 -- guessing and planting attacks | Not run: the analytical distribution mismatch already invalidates the hardness claim; attack measurements cannot manufacture a missing theorem |
| G7 -- scaling | The paper's asymptotic families scale, but no supported answer-first distribution does |
| Oracle loop | Not run, as required after a Step-0 G/H/V failure |

The decisive failure is not that one particular planted implementation looked weak. It is that the paper's contribution deliberately proves hardness **without planted structure**, while the required generator deliberately introduces planted structure, and the paper contains no result bridging the two.
