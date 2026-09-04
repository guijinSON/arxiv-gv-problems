# Rejected at Step 0: certificate generation leaves the hard distribution

Paper: Abhishek Dhawan and Yuzhou Wang,
[*The Low-Degree Hardness of Finding Large Independent Sets in Sparse Random
Hypergraphs*](https://arxiv.org/abs/2404.03842), arXiv:2404.03842v3 (2025).

## Decision

This paper does not support a self-contained family satisfying G, H, and V at
the same time. The independent-set witness is finite and exactly checkable, but
there is a fundamental conflict between retaining the paper's hard random
distribution and knowing such a witness without solving the sampled instance.
I therefore stopped at Step 0. No generator, fabricated gate report, or oracle
transcript was created.

| Requirement | Result | Evidence |
|---|---:|---|
| G -- certificate known by construction | **fails in the hard regime** | Theorems 1.6 and 1.9 are impossibility results for unconditioned Erdos--Renyi inputs; they do not construct or identify an independent set in a sampled instance. |
| H -- hard on the generated distribution | **fails for the available constructive regimes** | Theorem 1.5 is an achievability theorem implemented through a local/random-greedy algorithm; Theorem 1.9 gives a degree-1 algorithm for the multipartite problem. |
| V -- cheap exact verification | passes | Check the required cardinality (and balance, if applicable), then scan every hyperedge and reject if one is contained in the proposed set. |
| Overall | **rejected** | All three requirements must hold for one and the same distribution and parameter regime. |

## The paper's actual objects and hard regime

Definition 1.4 gives two independent-edge models.

- In \(\mathcal H_r(n,p)\), every \(r\)-subset of \([n]\) is included
  independently with
  \(p=d/\binom{n-1}{r-1}\).
- In \(\mathcal H(r,n,p)\), the vertex set is \([n]\times[r]\), every edge
  takes exactly one vertex from each part, and all such edges are included
  independently with \(p=d/n^{r-1}\).

An independent set contains no complete hyperedge. Definition 1.7 additionally
requires a \(\boldsymbol\gamma\)-balanced independent set to have
\(|I\cap V_i|=\gamma_i|I|\) in every part. These definitions make V easy and
exact.

For fixed \(r\geq2\), sufficiently large constant \(d\), and then sufficiently
large \(n\), Theorem 1.6 rules out the specified class of degree-
\(D\) polynomial algorithms above

\[
k=n(1+\varepsilon)
  \left(\frac{1}{r-1}\frac{\log d}{d}\right)^{1/(r-1)},
\]

where \(1\leq D\leq C_1n/(\xi\log n)\) and the required failure probability is
at most \(\exp(-C_2\xi D\log n)\). The second half of Theorem 1.9 gives the
analogous low-degree barrier for balanced independent sets. Sections 3.2--3.3
and 4.3--4.4 prove these barriers using ensemble overlap-gap forbidden
structures along correlated sequences of *unconditioned* random hypergraphs.

This is evidence against a restricted algorithm class, not a worst-case
NP-hardness result and not a theorem about a planted distribution. The paper
states polynomial-time hardness only as Conjectures 1 and 2.

## The Step 0 certificate question

The decisive question is: **what algorithm produces the independent-set
certificate, and what does it cost?** There are only two regimes supported by
the paper.

1. At or below the achievable threshold, an algorithm produces it. Section
   3.1 starts from the Nie--Verstraete random greedy algorithm, transfers a
   local algorithm from a regular hypertree to a Poisson Galton--Watson
   hypertree, and then approximates the local rule by a low-degree polynomial.
   Theorem 1.5 consequently supplies a low-degree algorithm for
   \(\mathcal H_r(n,p)\). Using its output as the generator's answer would be
   obtaining the certificate by solving the generated instance; it also fails
   H by the task's discriminating test.

2. The balanced multipartite case is even more direct. In Section 4.2, fix
   sets \(L_i\subseteq V_i\) for \(i<r\), and put into \(L_r\) exactly those
   vertices having no edge to \(L_1\times\cdots\times L_{r-1}\). The resulting
   union is independent by inspection. This is the degree-1 polynomial in the
   achievability half of Theorem 1.9. It is an explicit efficient search rule,
   not a hard witness family.

Above those achievable thresholds, Theorems 1.6 and 1.9 say that suitable
low-degree algorithms cannot find the requested set with the stated success
probability. They do not hand the generator a set. The corresponding existence
statements are probabilistic counting/concentration results: Theorem 1.8, for
example, locates the maximum balanced independent-set density with high
probability, while its proof uses first moment, second moment, McDiarmid, and
Azuma arguments. Existence with high probability is not a concrete certificate
known for the particular sampled instance. Recovering one by branch-and-bound,
SAT, ILP, or exhaustive search would violate G.

## Why inverse planting does not repair the family

The prior-triage proposal was to choose a large independent set \(I\) first and
then sample every other edge while forbidding all edges contained in \(I\).
That would make G and V pass, but it changes the instance law:

\[
\Pr[e\in E\mid e\subseteq I]=0
\quad\text{instead of}\quad
\Pr[e\in E]=p.
\]

Thus edges are no longer independent Bernoulli variables with the common
probability in Definition 1.4. Theorem 1.6's and Theorem 1.9's low-degree
barriers do not apply to this planted/conditioned distribution. The paper
mentions planted models only as a different framework for testing and
estimation in Section 1.1; it proves no quiet-planting, contiguity,
semi-random-robustness, or planted-recovery hardness theorem that would carry
the optimization lower bound over.

Randomly permuting vertices hides their names but does not fix the distribution
mismatch. Rejection-sampling a pair \((H,I)\) until \(I\) is independent does
not fix it either: the marginal law of \(H\) is size-biased by its number of
size-\(k\) independent sets. Composing certified blocks or imposing algebraic
structure similarly creates a new, visibly structured distribution outside
the paper's theorem.

Consequently, a Track A module based on planting would make a false claim about
the distribution to which the cited hardness theorem applies. Empirical
failure of a few heuristics or of the oracle pool could not supply the missing
theorem. It would also require the mandated hypergraph domain attack (at least
a SAT/ILP or branch-and-bound search, and construction-aware spectral or
message-passing probes), but passing those finite tests would still not bridge
the logical gap.

## Why Track B is not an honest fallback

Track B would need both an efficient reference algorithm and a genuinely
compact, at-most-300-operation route that a solver can discover from the
rendered instance. The paper's constructive routes do not have that shape:
they compute the set by processing the sampled edge structure. Encoding a
special symmetry, invariant, seed, or compact decoder so that the planted set
can instead be recovered in a few operations would define an invented
structured distribution not studied by the paper. Revealing the fixed
\(L_1,\ldots,L_{r-1}\) construction from Section 4.2 merely reduces the task to
the paper's explicit degree-1 scan and tests mechanical edge processing, not a
compact mathematical insight.

## Other formulations considered

- **Ask for a maximum independent set.** Feasibility of the set is easy to
  check, but maximality is not optimality. A cheap exact certificate of global
  optimality is not supplied by the paper, so this fails the witness rule.
- **Ask for the independence number.** A bare integer has the same optimality
  problem. Exhaustively listing or refuting all larger sets is not bounded or
  writable at the required scale.
- **Ask for the low-degree polynomial.** Theorems 1.5 and 1.9 make the
  constructive cases easy, while verifying that an arbitrary submitted
  polynomial succeeds with the required probability over all random
  hypergraphs is not cheap exact substitution on one instance.
- **Ask for an overlap-gap forbidden structure or its absence.** The paper
  proves probabilistic nonexistence. A negative instance claim has no bounded,
  executable certificate in the paper.
- **Use disjoint unions of certified hypergraphs.** Certificates compose, but
  the block decomposition makes the distribution non-Erdos--Renyi and makes
  the answer recoverable component by component.

## Full-text audit

I read the complete 56-page v3 paper, including Definitions 1.1--1.4 and 1.7;
Theorems 1.5, 1.6, 1.8, and 1.9; the local/stable algorithm definitions in
Section 2; the constructive proof in Section 3.1; the ordinary-hypergraph OGP
and intractability proofs in Sections 3.2--3.3; the statistical threshold and
explicit degree-1 construction in Sections 4.1--4.2; the balanced OGP and
intractability proofs in Sections 4.3--4.4; the conclusion; and the local
hypertree appendix. Searches of the full text found no theorem transferring
the low-degree lower bounds to an independent-set-planted or conditioned law.

The rejection is not a claim that finding large independent sets in sparse
random hypergraphs is easy. It is the narrower conclusion required here: the
paper's hard distribution does not expose a construction-time witness, and the
paper's witness-producing regimes are algorithmically easy by its own results.
