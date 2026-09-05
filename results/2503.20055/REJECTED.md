# Rejected: arXiv 2503.20055

## Decision

No family from I. J. Dejter's
[*From semi-total to equitable total colorings*](https://arxiv.org/abs/2503.20055)
cleared **G, H, and V** together.  The retained prototype passes inverse
generation and exact witness checking, but fails **H on Track A** under the
mandatory domain-standard attack.  Relabelling that same prototype Track B
would also be wrong: its private planted colouring is not a compact route that
a solver can recover from the public graph.

This decision uses the current v6 full text, not the abstract.  Section 1,
Definitions 1 and 8 fix the native problem: a total colouring colours both
vertices and edges, forbids equal colours on adjacent or incident elements,
and is equitable when any two complete colour classes differ in size by at
most one.  The same section cites NP-completeness of deciding equitable
four-total-colourability for bipartite cubic graphs.  That is a worst-case
statement; it does not establish hardness for an inverse-generated yes
distribution.

## The attempted native family

The prior-triage proposal was implemented without replacing the graph by SAT
or another surrogate.  On the two sides of a hidden bipartition, the generator
first samples the same four near-equal vertex-colour class sizes.  For every
edge colour `j`, it creates a perfect matching on the vertices whose vertex
colour is not `j`, never joining equal vertex colours.  Consequently every
vertex and its three incident edges use all four colours.  Colour-safe
two-switches mix the four layers, after which vertices and edges are randomly
relabelled and all hidden colours are removed from the instance.

The certificate is a word colouring every vertex and edge.  `verify` checks
all adjacency and incidence inequalities plus exact class sizes and accepts
any valid normalized word; it never reads `inst["answer"]`.  Thus **G and V
pass**.  The demo instance has exactly two normalized equitable witnesses, as
counted by exhaustive constraint propagation.

The complete experiment remains as `rejected_gen_2503_20055.py`, in accordance
with the retention rule.

## Why Track A fails

The shipping-sized experiment used 102 vertices, 153 edges, and a 255-symbol
answer.  It is inside the cited bipartite-cubic/four-colour parameter regime,
but the distribution has an easy tail.  A capacity-aware exact equitable
DSATUR/DPLL search returned a witness that the independent checker accepted:

| setting | seed | exact search result | measured cost |
|---|---:|---|---:|
| `n=102`, 8 switch rounds | 3100 | solved | 619,838 nodes, 32.129 s |
| `n=102`, 8 switch rounds | 424242 | node cap reached | 1,000,001 nodes, 41.387 s |
| `n=102`, 32 switch rounds | 3105 | solved | 493,237 nodes, 14.13 s in a four-process run |
| `n=102`, 64 switch rounds | 3101 | solved | 86,081 nodes, 7.48 s at a 200,000-node probe |
| `n=102`, 64 switch rounds | 3102 | solved | 11,921 nodes, 0.51 s at a 200,000-node probe |

One success is already disqualifying under G6; the several successes also show
that more switching is not a monotone hardness axis.  Changing the imbalance
did not cure this: at `n=100`, 32 switch rounds, seeds 3103 and 3102 were solved
in 303,380 and 624,817 nodes respectively.  Reporting only the capped failures
would therefore conceal known successful runs.  The paper's worst-case theorem
cannot turn this measured planted distribution into a Track A family.

There is a second construction-specific danger.  Equal hidden vertex-class
sizes give an exact equitable partition of the adjacency matrix: the three
colour-contrast vectors are eigenvectors of eigenvalue `-1`.  This is the same
kind of polynomial spectral leak that has invalidated earlier planted graph
families.  The prototype deliberately used class sizes differing by two to
remove that exact eigenspace, but exact DPLL still found the easy tail above.

## Why this is not Track B

For the retained planted family, the successful mechanical route is the exact
search just measured: 619,838 nodes on the first solved shipping instance.
There is **no shorter public compact route**.  The linear-time route that the
generator used was to remember four hidden matchings and their colours before
forgetting them; those data are absent from the problem statement.  Once only
the public graph remains, “every vertex and its incident edges use all four
colours” is merely the stated local constraint, not a shortcut to the hidden
global colouring.  Even after that observation, a solver must search and must
write 255 independent colour symbols.  Calling the private plant an insight
would make any planted CSP a Track B family and erase the distinction the track
is meant to enforce.

The paper's genuinely constructive alternatives were also checked for Track B:

- Theorem 1 swaps two colours on the supplied skeleton of a maximal
  colour-alternating path.  With the skeleton supplied, the mechanical cost and
  compact route are the **same** `length(skeleton)` colour exchanges.  If the
  skeleton is hidden, the theorem does not identify which path improves beta or
  gamma; finding one becomes an unstructured scan invented by the benchmark.
- Theorem 2 lifts a supplied colouring through a supplied covering map.  Both
  the standard method and the compact description perform one copied colour
  assignment per output element: **Theta(|V|+|E|)** operations either way.
- Theorem 3's colourings of `Q3` and `C_(4j) square K2` are explicit periodic
  constructions.  Evaluating the formula and writing the requested total
  colour word are again the same linear pass.  At the largest writable cubic
  instance this is 255 assignments; there is no million-operation mechanical
  route hiding behind a dozen-operation invariant.

Thus the efficient constructions are not rejected merely because an algorithm
exists: their **mechanical cost and compact route are comparable**.  The one
candidate with a large mechanical cost has no compact route at all.  Neither
case satisfies Track B.

## Easy regimes and cap check

The source paper itself identifies the regimes that cannot support a hardness
claim: Theorem 1 gives a direct Kempe-style exchange once an alternating
skeleton is known; Theorem 2 copies colourings through covering maps; Theorem 3
gives explicit efficient total colourings of the cube and polygon prisms; and
the later symmetric/cage examples list the actual reduction paths.  Section 4
also recalls a constructive expansion family with equitable chromatic number
five.  None supplies a hard distribution of promised yes-instances.

The retained answer is 255 atomic colour assignments (257 JSON characters),
already at the 256-atom limit.  Increasing only `n` would therefore be a
`cap_bound`, not evidence against the mathematics, and it was not used as the
rejection reason.  Fixed-length mixing was tested through 64 switch rounds and
continued to produce exact-search successes.  More importantly, the missing
Track B compact route is independent of the cap.

## Gate outcome

| requirement | result |
|---|---|
| G — generatable | Pass: inverse construction from four hidden matchings. |
| V — verifiable | Pass: exact adjacency, incidence, and cardinality checks. |
| H — Track A | **Fail:** the standard exact colouring attack succeeds on the generated shipping distribution. |
| H — Track B | **Fail:** the planted family has no public compact route; the paper's explicit families have mechanical and compact routes of the same linear length. |
| Overall | **Rejected.** |

No oracle hardening or G9 arms were run after the mandatory local G6 failure;
creating transcripts or a passing self-test at that point would misstate the
evidence.
