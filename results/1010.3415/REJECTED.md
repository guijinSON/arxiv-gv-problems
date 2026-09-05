# Rejected at Step 0: the probabilistic existence proof does not yield a hard, finite witness family

Paper: František Kardoš, Daniel Kráľ, and Jan Volec,
[*Fractional colorings of cubic graphs with large girth*](https://arxiv.org/abs/1010.3415),
arXiv:1010.3415v1 (2010).

## Decision

No generator is shipped. The natural native task is to give a cubic graph of
large girth and request an independent set of the size guaranteed by Corollary
2. The paper proves that such a set exists by constructing a **probability
distribution** whose expected set size is large. It does not construct a
particular sufficiently large set from the graph, nor a finite explicit
fractional coloring that can be inspected by the checker.

Consequently, the native candidates do not make **G, H, and V hold at the same
time**:

- Using Theorem 1 directly does not pass **G** for a large-set witness. One run
  of the randomized procedure always produces an independent set, but only an
  expectation argument says that some outcome is large. Repeating outcomes
  until one crosses the bound is searching for the answer, which the generator
  rules forbid.
- Planting an independent set first would pass **G** and **V**, but fails **H on
  Track A**. It changes the ordinary cubic/high-girth input into a conditioned
  planted distribution, and this paper contains no distributional hardness,
  quiet-planting, or indistinguishability result for that distribution. The
  paper instead supplies a randomized local construction designed to find large
  independent sets in its regime.
- **Track B also fails.** If the random choices are included in the instance,
  the answer is obtained by executing the Section 3 procedure; there is no
  shorter invariant or change of variables in the paper that recovers the
  individual red vertices. If a planted set or decomposition is exposed to
  create a shortcut, the shortcut simply reveals the answer. If it is hidden,
  it is private generator state rather than a solver-visible compact route.
- Asking for the full fractional coloring does not rescue **V**. Theorem 1
  gives an implicit probability law over independent sets. It does not give a
  bounded rational support with weights. Verifying the stochastic recipe's
  marginal guarantee would require replaying the paper's probabilistic proof,
  numerical recurrence analysis, and limiting argument rather than inspecting
  a finite exact certificate.

This is not a `cap_bound` decision. The size obstruction below reinforces that
the main theorem cannot furnish a literal benchmark instance, but the decisive
failure is the absence of any family that simultaneously has construction by
certificate, supported hardness on either track, and a finite exact checker.
Steps 1--4 were therefore not run, as required by the Step-0 rule.

## What the paper actually proves

Section 1 fixes the native objects. An independent set contains no adjacent
vertices. A fractional coloring assigns nonnegative weights to independent
sets so that the total weight covering each vertex is at least one. A graph is
cubic when every vertex has degree three, and its girth is the length of its
shortest cycle.

Theorem 1 states that, for some girth threshold, every cubic graph has a
probability distribution on independent sets in which every vertex is present
with probability at least `0.4352`. Corollaries 2--4 derive, respectively, an
independent set of size at least `0.4352 n`, a fractional chromatic number at
most `2.2978`, and a cut of size at least `0.8704 m`.

The certificate-producing mechanism is explicit about being randomized:

- Section 3 colors vertices white, blue, and red. The first round activates
  vertices independently; later rounds process maximal white paths of types
  `1↔1`, `1↔3`, and `3↔3`. Red vertices form an independent set.
- Section 4 proves the conditional-independence lemma and derives recurrences
  only for the **probabilities** of the colors and white degrees.
- Section 4.3 solves those recurrences numerically with
  `p1 = p2 = 10^-5` for `K = 307,449` rounds. The Appendix is the floating-point
  Python program used for this calculation; it computes the density bound, not
  an individual certificate.
- Section 5 modifies the stochastic process for finite high-girth graphs by
  truncating long paths and attaching randomly sampled virtual trees. Theorem
  7 says that a fixed vertex is red with probability at least `r_K - epsilon`
  when the girth is at least `8 K L + 2` for a sufficiently large `L`.

The expected cardinality of the red set then implies that at least one large
outcome exists. That last implication is existential. The paper does not give
the random bits of such an outcome, a derandomization, or a compact description
of a successful outcome.

Theorem 8 is an explicit weaker odd-girth result. Its proof first takes a
2-factor, deletes a periodic set of cycle vertices, chooses bipartition classes
of the remaining paths, and randomly repairs conflicts on the complementary
matching. This again constructs a distribution and proves vertex marginals. If
the 2-factor and random choices are included in a puzzle, the proof is the
direct solution algorithm; if they are omitted, the paper supplies no distinct
compact route to the particular outcome.

## Step-0 mechanical-cost and compact-route comparison

There is no actual shipping size in the theorem-backed regime, so the first row
uses `n = 588`, the largest graph for which an explicit `0.4352 n` independent
set could fit the 256-atom output cap. This is deliberately a generous
counterfactual: such a graph cannot meet the paper's proven girth threshold, as
shown in the next section.

| Candidate task | Mechanical cost at the would-be shipping size | Compact route | Result |
|---|---:|---:|---|
| Execute the Section 3 process and return its red vertices | At least `K n = 307,449 * 588 = 180,780,012` vertex-round visits, before scanning white paths or virtual-tree data | **No shorter route in the paper**; determining the individual colors requires the same round/path updates, so the paper-backed compact/mechanical cost ratio is 1 | Track B fails, and the route also exceeds the 300-operation no-tool cap |
| Return a set of size at least `0.4352 n` from the graph alone | The stochastic procedure above plus selection of a sufficiently large outcome; generic exact independent-set search is an alternative | **No finite route is given.** The recurrences reveal only expected density, not which vertices to output | G fails if the generator selects an outcome; hiding a planted outcome does not create a public shortcut |
| Use Theorem 8 at odd girth `g=5` | Its guarantee is `n/4`, so `n=1,024` already fills all 256 answer atoms. Once a 2-factor and the random choices are known, the proof performs a linear pass over those 1,024 vertices and their matching edges | The identical periodic deletion, bipartition, and conflict-repair pass; no shorter solver-visible invariant is supplied | Track B fails: the compact and mechanical routes are the same construction |
| Find the needed 2-factor rather than include it | Standard perfect-matching algorithms are polynomial time; a conservative dense bound is `O(n^3)`, about `1.07 * 10^9` primitive triples at `n=1,024` | No separate shortcut on the paper's arbitrary bridgeless input. A generator-planted matching is private state unless exposed, in which case reading it is the algorithm | A large mechanical number alone does not establish Track B |
| Output the Appendix recurrence value or a marginal probability | 307,449 iterations of the displayed floating-point recurrence | The same recurrence; the paper gives no closed form or invariant that skips it | Track A fails because the certificate is algorithm output; Track B fails because there is nothing to compress, and floats are not an exact witness |

Thus the large operation counts do not provide a Track-B family. Track B needs a
short, solver-visible route to the same witness. Here the only paper-backed
route to an individual outcome is the mechanical stochastic/path process
itself; the genuinely compact recurrence computes only an average and therefore
does not produce the required witness.

## The finite-girth regime is far beyond the output format

This is supporting evidence, not the rejection gate. With the paper's chosen
`K = 307,449`, even the impossible best case `L = 1` in Theorem 7 requires

```text
girth >= 8 * 307,449 + 2 = 2,459,594.
```

The cubic Moore bound says that a cubic graph of even girth `g = 2r` has at
least `2(2^r - 1)` vertices. Here `r = 1,229,797`, so even this lower bound has
370,207 decimal digits. A literal independent-set witness containing 43.52% of
those vertices, and a literal inline graph instance, are outside the benchmark
format by an astronomical margin. The `L` actually needed for the limiting
error is larger, not smaller.

Using practical girth instead would no longer be the parameter regime proved by
Theorem 1. Theorem 8 avoids this size issue by assuming only large **odd** girth,
but its proof's explicit randomized construction has the same G/Track-B problem
described above.

## Why the prior planted-set triage does not work

The suggested generator would choose a large independent set and then pair
configuration-model half-edges subject to forbidding edges inside it. That
does know a witness by construction and exact verification is cheap. It is not,
however, the ordinary random cubic model discussed in Section 1.1: it is the
model conditioned on a named set having no internal edges. Relabeling hides the
name but does not undo the conditioning.

The paper proves no hardness theorem at all, much less average-case hardness for
this planted law. Indeed, Section 1.1 describes `0.4352 n` as a universal lower
bound and reports experimental typical independent-set sizes around `0.439 n`
and `0.447 n` in random cubic graphs. Those observations make the target a
guaranteed/typical feasible level, not a paper-supported hard recovery threshold.
Worst-case NP-hardness of maximum independent set would not establish hardness
of finding a submaximum set from this conditioned distribution.

Adding symmetry, arithmetic labels, or a compressed selector to expose a short
planted route would create a new puzzle distribution not analyzed in this
paper. It would test recovery of the benchmark author's encoding rather than
the large-girth fractional-coloring argument.

## Other native witness formulations considered

| Native formulation | G | H | V | Outcome |
|---|---:|---:|---:|---|
| A `0.4352 n` independent set in the Theorem 1 regime | Fails without outcome search; inverse planting repairs G | Track A unsupported for the plant; Track B has no compact route | Pass for an explicit vertex set | Rejected |
| A cut of size `0.8704 m` from Corollary 4 | Same issue, because the proof obtains the cut from the large independent set | Same issue | Pass for an explicit bipartition | Rejected |
| A rational fractional coloring of total weight at most `2.2978` | The theorem gives an implicit probability law, not bounded rational support | Extracting support would add a new search/LP step | Exact checking would pass only after such unsupported support were supplied | Rejected |
| The random choices and resulting red set of Section 3 | Pass by composition/simulation | Track A false; Track B has identical mechanical and compact routes | Pass | Rejected |
| The numerical recurrence result | Pass only as the output of the Appendix algorithm | Fails Track A; no shorter Track-B route | The paper's floats are not an exact certificate | Rejected |

## Gate outcome

| Requirement | Result | Evidence |
|---|---:|---|
| G — certificate known without solving | **Fails for the theorem-backed large-set task** | The proof controls expectation; selecting a sufficiently large realization is a search. Inverse planting changes the distribution |
| H — Track A structural hardness | **Fails/unsupported** | The paper gives a randomized local construction and no hardness result for the proposed planted distribution |
| H — Track B no-tool compression | **Fails** | The shortest paper-backed route to individual red vertices is the same `K`-round path process; the compact recurrence returns only marginals |
| V — exact finite checking | Passes for explicit sets/cuts, but **fails for the implicit distribution as certificate** | Set independence is cheap; validating the stochastic marginal bound is not inspection of a bounded exact answer |
| Overall | **Rejected at Step 0** | No native formulation passes G, H, and V together |

No self-test numbers or oracle failures were fabricated after this analytical
failure, and no graph/SAT surrogate was substituted for the paper's native
objects.
