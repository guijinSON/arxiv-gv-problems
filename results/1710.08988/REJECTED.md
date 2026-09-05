# Rejected at Step 0: arXiv 1710.08988

Paper: Peter Allen, Christoph Koch, Olaf Parczyk, and Yury Person,
[*Finding tight Hamilton cycles in random hypergraphs faster*](https://arxiv.org/abs/1710.08988).

## Decision

No paper-native family here clears **G + H + V** under either declared
hardness track. The prior-triage proposal—choose a cyclic order, force its
consecutive hyperedges, and add random decoys—is generatable and exactly
verifiable, but it has no Track A hardness result for its planted distribution.
In the prompt-sized sparse regime it is also recovered by a direct
construction-aware attack. The paper's actual distributional result goes in
the opposite direction: Theorem 1 gives a deterministic polynomial-time
algorithm that finds the requested witness.

Track B was considered before rejection. It fails for two separate, quantified
reasons. In the prompt-sized planted regime the mechanical pair-codegree route
is already a sub-millisecond shortcut, so there is no meaningful compression
gap. In the paper's theorem-backed random regime the smallest value of `n`
even compatible with the explicit constant in the proof is far beyond the
answer cap, and the paper supplies no separate compact route that avoids its
fan/reservoir search. A structured affine or recurrence-based planted order
could manufacture such a route, but that structure is not in the paper or its
random-hypergraph model; it would benchmark a side channel invented by the
generator.

Implementation therefore stopped before Step 1. No generator, self-test
report, README, or oracle transcripts were created, and no unrun gate is
reported as passing.

## Exact native problem and certificate

Section 1 defines the binomial random `r`-uniform hypergraph
`G^(r)(n,p)` on `[n]`: every `r`-element set is independently present with
probability `p`. A tight Hamilton cycle is a cyclic ordering of all `n`
vertices for which every block of `r` consecutive vertices, including the
blocks crossing the end of the displayed order, is a hyperedge. Thus a natural
certificate is a permutation of `[n]`, modulo rotation and reversal. A checker
only has to verify the permutation and perform `n` exact edge-membership tests.

That makes the two non-hardness gates straightforward:

- **G can pass in isolation:** sample the cyclic permutation first, insert its
  `n` consecutive `r`-sets, and carry that permutation as the certificate.
- **V can pass:** check length, range, distinctness, normalization, and the `n`
  consecutive `r`-sets using integer set membership.

The conflict is H. Forcing the cycle changes `G^(r)(n,p)` to a planted/conditioned
distribution not covered by any hardness statement in the paper. Conversely,
sampling an unconditioned `G^(r)(n,p)` and running the paper's algorithm to get
the answer is specifically forbidden generation-by-solving.

## What produces the witness and what it costs

Theorem 1 states that, for each fixed `r >= 3`, a deterministic algorithm runs
in `O(n^r)` and asymptotically almost surely finds a tight Hamilton cycle in
`G^(r)(n,p)` whenever

```text
p >= C (log n)^3 / n.
```

Algorithm 1 in Section 3.2 is the certificate-producing method. It constructs
a reservoir path with Lemma 2, greedily extends it through the remaining
vertices, uses the Connecting Lemma to close the almost-cycle, and locally
reroutes the reservoir path to remove repeated reservoir vertices. The runtime
paragraph at the end of Section 3.2 gives `O(n^2)` for the greedy and local
rerouting portions; Lemma 2 and its proof in Section 5 dominate at `O(n^r)`.
For `r=3`, the mechanical scale is therefore cubic.

The proof of Theorem 1 in Section 3.3 explicitly chooses
`C >= max(C_Lemma2, C_Lemma3, 108)`. Even granting the smallest displayed
choice `C=108`, the inequality `108 (log n)^3 / n <= 1` first becomes possible
at `n=195,246` (natural logarithm). At that point:

| Quantity | Value |
|---|---:|
| Cubic mechanical scale `n^3` | 7,442,972,866,746,936 |
| Atoms in an explicit cyclic-order witness | 195,246 |
| Python/JSON characters in `[0,1,...,n-1]` | 1,450,858 |
| Information in an arbitrary normalized order | about 3,149,747 bits |

The witness therefore exceeds both G9(c) limits—256 atomic elements and 2,000
characters—by orders of magnitude before the paper's stated probability regime
is even nonempty. The actual constants from Lemmas 2 and 3 may be larger, and
the proof additionally assumes `n` is sufficiently large, so `195,246` is only
an optimistic lower bound.

At the opposite extreme, the largest explicit order allowed by the atom cap
has `n=256`. The same displayed lower bound gives
`108 (log 256)^3 / 256 = 71.93 > 1`, so no probability `p <= 1` puts such an
instance in Theorem 1's regime. At `n=120`, a convenient handoff size for an
explicit edge list, the lower bound is `98.76 > 1`.

## Measured audit of the proposed planted sampler

I tested the exact prior-triage construction for `r=3`: choose a uniform random
cyclic order, insert its `n` consecutive triples, then add uniformly sampled
distinct decoy triples. The attack counts, for every vertex pair, how many
hyperedges contain it; it keeps pairs of codegree at least two and performs a
constrained path search that checks each next triple. This is the natural
overlap representation of a tight path, not knowledge of the planted answer.

All timings below are standard-library Python on this runner, over eight seeds.
One counted preprocessing operation is one pair-codegree increment (three per
triple); one search node is one partial cyclic ordering visited.

| `n` | Total triples | Decoys | Successes | Median / max search nodes | Median wall time |
|---:|---:|---:|---:|---:|---:|
| 120 | 240 | 120 | 8/8 | 120 / 120 | 0.001070 s |
| 120 | 1,080 | 960 | 8/8 | 134 / 161 | 0.002160 s |
| 120 | 2,040 | 1,920 | 8/8 | 235 / 538 | 0.005555 s |
| 120 | 3,000 | 2,880 | 8/8 | 25,398.5 / 68,957 | 0.352959 s |
| 240 | 4,080 | 3,840 | 8/8 | 258 / 413 | 0.004745 s |

The `n=240`, 4,080-triple case—the largest tested explicit witness close to the
atom cap—costs 12,240 pair increments plus a median 258 search nodes, or 12,498
counted core steps. This **mechanical cost** is the same route as the supposed
**compact route**: compute the overlap codegrees and trace the surviving
cycle. There is no second invariant that shortens it below 300 exact operations,
and the complete implementation already succeeds in under five milliseconds
at the median (under eleven milliseconds on the slowest of the eight seeds).
At lower decoy counts the search itself is exactly one node per answer element.

Increasing the density can erase the codegree signature, but it does not repair
the hardness claim. For example, at `n=120` and 3,960 total triples the measured
pair-codegree search exhausted a 200,000-node cap on 8/8 seeds, but the edge
probability is only about `0.0141`, while even the optimistic displayed theorem
bound is greater than 98. Such an instance is neither in Theorem 1's regime nor
supported by any average-case hardness theorem in the paper. It is merely a new
planted distribution whose difficulty would have to be established from
scratch. A failed bounded heuristic cannot supply the required Track A theorem
and parameter regime.

This comparison is why the rejection is not the invalid argument “an efficient
algorithm exists.” At the only prompt-sized planted settings actually tested,
the standard overlap attack is cheap and the compact route is identical to it.
At the theorem-backed settings, the mechanical algorithm is large but an
explicit certificate and instance do not fit the benchmark, while the paper
offers no distinct compact route.

## Other paper-native objects considered

| Paper object | Potential witness | Why it does not rescue a family |
|---|---|---|
| Lemma 3 connecting path | A short tight path between two ordered `(r-1)`-tuples | The lemma itself gives a deterministic `O(n^(r-1))` fan/BFS construction. Its hypotheses use the same random regime and a set of size `C p^-1 log n`; no sub-300-operation recovery invariant is supplied. Planting a distinguished connector recreates the overlap outlier problem. |
| Definition 4 / Lemma 6 spike path | The sequence of pairwise disjoint spikes | Lemma 6 is obtained by the same fan construction, again in `O(n^(r-1))`. The compact and mechanical routes are the same local expansion. |
| Lemma 2 reservoir path | A path, reservoir set, and reroutings | Its defining property quantifies over every subset of the reservoir. A path and set alone are not an executable witness for that universal claim; listing all reroutings is exponential in `|R|`. The paper verifies the property through its construction proof, not a bounded object a checker can inspect cheaply. |
| A negative instance below threshold | A certificate of no tight Hamilton cycle | The first-moment and threshold arguments are probabilistic existence statements. The paper gives no bounded refutation certificate for an individual hypergraph. |

The conclusion reinforces the boundary. The deterministic algorithm covers
`p >= C(log n)^3/n`; finding cycles algorithmically remains open in the lower
windows `e/n <= p < C(log n)^3/n` for `r >= 4` and
`1/n << p < C(log n)^3/n` for `r=3`. Those open windows cannot be cited as a
hardness theorem for an inverse-planted generator.

## Gate diagnosis

| Requirement | Result | Evidence |
|---|---:|---|
| G — generatable | Passes alone | Inverse planting gives a cyclic order before any search. |
| V — exact witness checking | Passes alone | A permutation check plus `n` exact hyperedge-membership tests. |
| H — Track A | **Fails** | The paper proves an efficient finder in its random regime and proves no hardness for the forced-cycle distribution. The proposed prompt-sized sampler is also solved 8/8 by the measured overlap attack. |
| H — Track B | **Fails** | Prompt-sized mechanical and compact routes coincide (12,498 counted steps and 0.004745 s median in the largest audit); theorem-backed sizes violate the answer cap, and no paper-supplied sub-300-operation shortcut exists. |
| Overall | **Rejected at Step 0** | No one family satisfies G, H, V, and the no-tool caps simultaneously. |
