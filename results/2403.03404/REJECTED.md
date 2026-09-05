# Rejected at Step 0: the paper's certified families are explicit linear scans

Paper: Yasufumi Aita and Toru Araki, [*Secure Total Domination Number in
Maximal Outerplanar Graphs*](https://arxiv.org/abs/2403.03404),
arXiv:2403.03404v2 (2024).

## Decision

No generator is shipped. I read the complete paper, including the exact
definition in Section 1, the eight structural cases in Section 2, the
constructive induction in Section 3, and the lower-bound argument in Section
4. The natural witness--a secure total dominating set (STDS)--is concrete and
cheaply checkable, so **V passes in isolation**. The paper also gives
theorem-backed witnesses, so **G passes in isolation**. Every such source,
however, fails **H on both tracks**.

- **Track A fails.** Theorem 3.3 is a constructive procedure for finding an
  STDS of at most `floor(2n/3)` in every maximal outerplanar graph. The two
  families on which the bounds are sharp have still simpler displayed
  answers. The general NP-hardness mentioned in Section 1 applies to chordal
  bipartite and split graphs, not to the maximal-outerplanar distribution that
  the paper constructs. Worst-case hardness in those other graph classes
  supplies no distributional hardness here.
- **Track B fails.** The constructive induction is already the structural
  route: find one of eight constant-size boundary patterns, delete two or
  three vertices, recurse, and extend the set. Maintaining the boundary makes
  this a linear-size local computation. The two sharpness families are even
  more exposed: one is solved by a degree filter and the other by a universal
  vertex plus a period-three path pattern. There is no costly mechanical
  algorithm and distinct sub-300-operation shortcut.

This is an **H failure**, not a witness-rule failure. Steps 1--4 were therefore
not run: there is no `gen_2403_03404.py`, self-test report, README, or oracle
transcript. Running the oracle pool cannot turn a known linear construction
into a hard distribution.

## The exact native problem

Section 1 defines a total dominating set `S` of a graph `G` as a vertex set
such that every vertex--including every vertex in `S`--has a neighbor in `S`.
It is secure when, for every `u` outside `S`, some adjacent `v` in `S` can be
replaced by `u` while leaving a total dominating set:

`(S - {v}) union {u}` is total dominating.

Proposition 3.2 gives an equivalent local defender test using external and
internal private neighborhoods. Thus a proposed `S` is a finite native graph
witness: a checker can inspect every outside vertex and every possible
adjacent defender, perform the swap, and recompute total domination with exact
set membership. No graph surrogate or appeal to an unexecutable theorem is
needed by the checker.

Theorem 3.1 states the upper-bound search task suggested by the prior triage:
every `n`-vertex maximal outerplanar graph has an STDS of size at most
`floor(2n/3)`. The stronger Theorem 3.3 says that for `n >= 4` such a set can
avoid all degree-two vertices. Its proof is constructive. Proposition 2.2
guarantees one of eight induced patterns on five, six, or seven consecutive
boundary vertices. Cases (a)--(h) delete two or three named vertices, recurse,
and add one or two named vertices (with one constant-size exchange in case
(h-2)). That proof is precisely a certificate-producing algorithm.

Section 4 proves the lower bound

`gamma_st(G) >= ceil((n+2)/3)`

for every outerplanar graph. This proves optimality only when a constructed
witness meets the bound. It does not produce a minimum STDS for an arbitrary
maximal outerplanar graph.

## What makes the theorem-backed sources easy

The upper-sharp family `H_k` in Section 3 has `n = 3k` vertices partitioned
into triples `{a_i,b_i,c_i}`. The paper displays the minimum STDS

`S = {a_i,c_i : 1 <= i <= k}`.

For `k > 1`, the vertices `b_i` are exactly the degree-two vertices, while
every `a_i` and `c_i` has larger degree. Consequently `S` is simply

`{v : degree(v) > 2}`.

Randomly relabelling the vertices hides the names but not this invariant. The
required G6 outlier/degree attack would solve every instance, so relabelling
cannot create hardness or diversity. At a fixed `k`, all such relabellings
also have the same correct `canonical_key`; they are one graph, not an
unlimited supply of distinct instances.

The lower-sharp family `G_k` in Section 4 has `n = 3k+1`. It is a fan: `v_1`
is adjacent to every other vertex, and deleting `v_1` leaves a path. The paper
displays the minimum STDS

`S = {v_1} union {v_(3i) : 1 <= i <= k}`.

After arbitrary relabelling, the unique universal vertex reveals `v_1`, and
the remaining graph reveals the path. The selected path positions are those
congruent to two modulo three from either endpoint; reversing the path gives
the same positions. This is again a deterministic linear scan, not a hard
search.

For a general maximal outerplanar graph, Theorem 3.3's recursion is just as
algorithmic. With the Hamiltonian boundary and adjacency sets maintained, one
can queue the constant-size windows affected by each deletion. There are at
most `n` deletions and constant local work per affected window, so the natural
implementation is `O(n+m)` apart from routine data-structure bookkeeping.
Even a deliberately naive implementation that rescans the boundary after
every deletion is only `O(n^2)`. Calling that avoidable rescan the
"mechanical" route would manufacture a Track B gap by comparing against an
intentionally weak implementation; the paper's local recursion remains the
compact route and the standard algorithm at once.

## Step-0 mechanical cost versus compact route

I measured the most favorable proposed source, the upper-sharp `H_k` family,
at the largest natural point allowed by the 256-atom answer cap: `k=128`,
`n=384`, `m=2n-3=765`, and `|S|=256`. Vertices were randomly relabelled before
the attack. Although the structure-aware candidate space of all 256-subsets
has

`C(384,256) = 6.108... * 10^104` candidates (about 348 bits),

that cardinality is irrelevant because the degree rule recovers the answer.

The certificate-producing formula performs **256 mapped vertex emissions**.
In nine batches of 20,000 CPython calls, its median measured time was
**0.0000132753 seconds** per answer. The solver-visible degree attack performs,
under a simple accounting,

`2m + n + |S| = 1530 + 384 + 256 = 2170`

primitive incidence increments, degree tests, and output emissions. Its median
time over the same nine-by-20,000-call benchmark was **0.0000490298 seconds**.
It recovered the paper's STDS on **8/8** independently relabelled instances;
exact STDS checking accepted all eight (median checker time about 0.0057
seconds).

The alleged **compact route is exactly the same degree scan**, with the same
2,170-operation cost and therefore a mechanical/compact ratio of **1**. If the
canonical `a_i,b_i,c_i` names are exposed, both routes collapse instead to the
same 256 direct emissions. Reducing `n` until the degree scan fits the
300-operation intended-route cap only makes the already successful attack
smaller; increasing `n` merely increases the answer until the 256-atom cap is
hit.

The `G_k` family is no better. At its 256-atom maximum (`k=255`, `n=766`), the
displayed formula emits the universal vertex and 255 periodic path vertices
directly. Recognition is one adjacency/path scan. At any size small enough to
make that scan a sub-300-operation no-tool route, the same visible
universal-vertex and period-three rule is an immediate in-context attack.

These figures answer the Step-0 discriminating question. The paper's
certificates are produced by direct formulas or a local recursive algorithm,
and those procedures cost only linear work. The compact route is not shorter
than the mechanical route because it is the mechanical route.

## Other candidate families considered

| Native task | G | H | V | Outcome |
|---|---:|---:|---:|---|
| Given a maximal outerplanar graph, find an STDS of size at most `floor(2n/3)` | Pass by Theorem 3.3's proof | **Fails A and B:** the proof is a local certificate-producing algorithm and no distinct shortcut exists | Pass by exact swap scans | Reject |
| Given `H_k`, return a minimum STDS of size `2k` | Pass; Section 3 prints it and proves optimality | **Fails A and B:** `degree > 2` succeeds on every generated instance in 49 microseconds at the answer cap | Pass | Reject |
| Given `G_k`, return a minimum STDS of size `k+1` | Pass; Section 4 prints it and Theorem 4.1 certifies optimality | **Fails A and B:** universal vertex plus a period-three path scan | Pass | Reject |
| Given an arbitrary maximal outerplanar graph, return a minimum STDS | Not supplied by these bounds: a minimum witness and matching exact lower certificate are not known by construction | No hard generated distribution is proved | A set is checkable, but minimum optimality is not certified merely by checking the set | Reject |
| Inverse-plant an STDS in arbitrary graphs | Possible in isolation | **Track A unsupported:** the cited worst-case NP-hardness does not transfer to an answer-first distribution; visible planting is attacked, hidden planting has no paper-backed compact route | Pass | Reject |
| Ask only for `gamma_st(G)` | Fails the witness rule unless accompanied by an executable optimality certificate; the two equality families provide one only through their transparent structure | Fails on those equality families | A bare integer is not enough | Reject |

The Section 1 complexity citation cannot rescue the last two proposals. The
paper merely reports NP-hardness on chordal bipartite and split graphs; it does
not reproduce the reduction, give an answer-first distribution, or connect
those hard classes to its maximal outerplanar constructions. Importing that
worst-case theorem would still not show that generated planted instances are
hard.

## Gate diagnosis

| Requirement | Result | Evidence |
|---|---:|---|
| G -- generatable | Passes only in isolation | Theorem 3.3 recursively constructs a bounded STDS; Sections 3 and 4 explicitly construct the equality witnesses. |
| H -- Track A structural hardness | **Fail** | Every theorem-backed distribution in the paper has a linear certificate-producing scan or displayed formula; no distributional hardness theorem covers it. |
| H -- Track B no-tool compression | **Fail** | At the 256-atom limit, the strongest `H_k` attack takes 2,170 simple operations and 49 microseconds, and the compact route is that identical scan. Smaller instances remain transparent. |
| V -- exact witness checking | Passes in isolation | Check total domination, then all adjacent defender swaps, using finite exact graph operations. |
| Unlimited canonical diversity | Fails for the two equality families | For each `k` each paper-defined family has one isomorphism class; vertex relabellings must collapse under `canonical_key`. |
| Overall | **Rejected at Step 0** | G, H, and V cannot be made to hold simultaneously for a family justified by this paper. |

No G1--G9 or oracle measurements were fabricated after the analytical H
failure. In particular, the huge subset count is not evidence of difficulty
when a domain-standard per-vertex statistic recovers the witness on every
instance.
