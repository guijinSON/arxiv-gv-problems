# Rejection: arXiv:1602.08620

Paper: Nathan Mull, Daniel J. Fremont, and Sanjit A. Seshia, [*On the
Hardness of SAT with Community Structure*](https://arxiv.org/abs/1602.08620).

## Decision

No generator is shipped. The paper does not supply a problem family that
simultaneously clears G, H, and V under either track. The prior-triage proposal
to plant a satisfying assignment is not licensed by the paper's average-case
theorem: that theorem is about formulas drawn from the unplanted community
attachment distribution, conditional on being unsatisfiable.

The failure is the intersection of **G and H**, not V. A Boolean assignment is
an excellent exact witness and is checked by evaluating the clauses. The paper's
hard distribution, however, consists of negative instances, while its result
says that the natural executable negative certificate is exponentially long.

## Step 0 discriminator

### The average-case result

Sections 4.1--4.4 define the community attachment distribution
`F_k(n,m,c,p)` exactly: with probability `p`, a clause uses variables from one
uniformly chosen community; otherwise its variables come from `k` different
communities. Literal polarities are uniform. Theorem 4.3 states that when
`m=O(n)` and `c=O(n^alpha)` for `alpha<1/10`, with high probability an
**unsatisfiable** random 3-CNF has no resolution refutation of size
`2^{O(n^lambda)}` for some `lambda>0`. Theorem 4.4 turns that into an
exponential CDCL runtime lower bound, again conditional on unsatisfiability.

What produces a checkable negative certificate here is a resolution/CDCL
refutation. Its mechanical cost is the theorem's exponential lower bound,
`2^{Omega(n^lambda)}` resolution steps with high probability (the paper writes
the equivalent exclusion of refutations of size `2^{O(n^lambda)}`). The compact
route length is no smaller: the paper provides no bounded shortcut certificate,
and the resolution lower bound expressly rules one out in that proof language.
For all sufficiently large instances this also exceeds the 256-atom and
2,000-character answer caps. Thus this is not Track B: there is no short
structure-aware route separated from a long mechanical route.

Sampling from `F_k(n,m,c,p)` until an unsatisfiable formula appears would require
solving the generated formula, which violates G. Merely relying on
"unsatisfiable with high probability" is not an exact certificate. Planting a
contradiction or a short refutation would change the distribution and destroy
the basis for Theorems 4.3--4.4. No Nullstellensatz, Positivstellensatz, or other
bounded exact refutation is constructed in the paper.

### The worst-case result

Theorem 3.3 proves NP-hardness for high community-structure scores by taking an
arbitrary SAT formula `phi`, adjoining a fresh guard `x`, adding every clause
`x or y or z` for variables `y,z` of `phi`, and making `c(n)` disjoint copies.
Setting every guard to true leaves exactly the original task of satisfying
`phi`; the copies do not create a new search problem.

Let `s` be the number of variables of `phi` and let `T_phi` be the cost of
finding its assignment. With unordered distinct pairs, an explicit mechanical
implementation reads `c * binom(s,2)` padding clauses and then still pays
`T_phi`. The paper-specific compact route is one semantic step--set the guard to
true--followed by the same `T_phi`; copying the assignment is linear in the
answer length. For example, at `s=255, c=10`, the mechanical padding is exactly
`323,850` clause visits, while the compact paper-specific part is one guard
choice, but **both routes still contain the identical unknown `T_phi`**. If the
padding is represented succinctly so it fits a no-tool prompt, the standard
preprocessor can make that same guard choice without expanding those clauses.
The apparent 323,850-to-1 gap is therefore input expansion, not certificate
search or a mathematical shortcut.

Inverse-generating `phi` around a planted assignment clears G but does not clear
H: Theorem 3.3 is worst-case NP-hardness of a class, not average-case hardness of
the resulting planted distribution. Choosing a specially structured `phi` with
some separate compact solution method would make all actual difficulty come
from that external construction, not this paper. Choosing an easy `phi` makes
the in-context attack "set the pure-positive guard and solve one component"
succeed. Hence the construction supports neither Track A distributional
hardness nor an intrinsic Track B compression benchmark.

## Easy regimes that must not be hidden

Section 5 explicitly explains why the average-case lower bound cannot extend to
communities of logarithmic size (`c=Theta(n/log n)`): with high probability one
community is itself unsatisfiable and has a polynomial-length resolution
refutation. It also notes that `p=1` decomposes the formula into independent
community subproblems. These observations further prevent substituting an
arbitrary convenient parameter regime for the stated `alpha<1/10` regime.

## Gates

| Gate | Result | Reason |
|---|---|---|
| G | fail for the hard distribution | No exact bounded negative witness is known by construction; finding one by SAT search is forbidden. |
| H, Track A | fail for planted positives | Theorems 4.3--4.4 do not apply after planting; Theorem 3.3 is only worst-case. |
| H, Track B | fail | The hard negative route and its certificate are both exponential; the padding reduction's shortcut still leaves exactly `T_phi`. |
| V | pass in isolation | Assignments and bounded refutations can be checked exactly, but neither forms an admissible hard generatable family here. |

Because triage fails before implementation, `gen_1602_08620.py`, self-test
artifacts, and oracle transcripts were deliberately not fabricated.
