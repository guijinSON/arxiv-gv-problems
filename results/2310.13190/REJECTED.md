# Rejected at Step 0: long Berge cycles in the planted distribution are easy

Paper: Alexandr Kostochka, Ruth Luo, and Grace McCourt,
[*A hypergraph analog of Dirac's Theorem for long cycles in 2-connected
graphs, II: Large uniformities*](https://arxiv.org/abs/2310.13190), arXiv
2310.13190v1.

## Decision

No generator is shipped. The prior-triage proposal—plant a long Berge cycle
inside a random uniform hypergraph—can satisfy **G** and **V**, but it fails
**H on Track A** for two independent reasons:

1. The paper proves an extremal existence theorem, not computational or
   distributional hardness. It gives no basis for claiming that random
   hypergraphs conditioned around a planted cycle are hard.
2. A construction-aware test of that proposed distribution is easy. A simple
   randomized incidence walk found a valid target-length Berge cycle on every
   tested instance, without trying to recover the planted cycle.

The theorem alone cannot replace planting for **G**. Its proof is by
contradiction and begins by choosing a longest cycle and then a lexicographically
"best" lollipop. It does not output an executable, bounded certificate from a
new hypergraph. Sampling a theorem-valid hypergraph without planting would
therefore leave the generator needing to solve the same cycle-search instance
it plans to pose.

Track B was considered before rejection. With no planting leak visible to the
solver, the paper supplies no compact route shorter than the ordinary incidence
search. Making the planted order visible through labels or a stated recurrence
would create an artificial shortcut not present in the paper, and the obvious
in-context attack—follow that order and choose its containing edges—would
succeed. Thus there is no qualifying paper-backed compression gap.

Per the task's Step-0 rule, no `gen_2310_13190.py`, self-test report, README, or
oracle transcript was created. Running the oracle loop cannot repair an
analytical H failure.

## Exact paper objects and parameter regime

Definition 1.1 in Section 1.2 defines a Berge cycle of length `c` as an
alternating sequence

\[
v_1,e_1,v_2,e_2,\ldots,v_c,e_c,v_1
\]

of `c` distinct vertices and `c` distinct hyperedges, with

\[
\{v_i,v_{i+1}\}\subseteq e_i
\]

for every cyclic index `i`. These are exactly the finite witness and the
containment checks that the proposed verifier would use.

Definitions 1.2 and 1.3 define the incidence bipartite graph `I_H`, with one
part `V(H)`, the other part `E(H)`, and incidence as adjacency. A hypergraph
is 2-connected precisely when this incidence graph is 2-connected. Section 1.2
also states the natural bijection between length-`c` Berge cycles in `H` and
length-`2c` graph cycles in `I_H`.

Theorem 7 in Section 1.3 is the main result. For

\[
3\leq k\leq r+1\leq n,
\]

every 2-connected `n`-vertex `r`-uniform hypergraph with minimum degree at
least `k` has circumference at least

\[
\min\{2k,n,|E(H)|\}.
\]

This is the correct large-uniformity regime. It is not a hardness regime.
Section 1.3 explicitly says the proof is by contradiction. Sections 2–7 order
lollipops and disjoint cycle–path pairs first by the length of `C`; in
particular, a 1-good lollipop contains a *longest* cycle. The subsequent lemmas
show that a hypothetical counterexample cannot possess the required best
structures. They do not give a certificate-construction algorithm that a
generator can run without first finding a longest cycle.

The nearby easy/exposed constructions do not help. Construction 1.1 is a
sharpness example with minimum degree `k-2`, outside Theorem 7's hypothesis;
its two common vertices `x,y` and its blocks `A_i` are explicit.
Constructions 1.2 and 1.3 are similarly explicit block/bipartition sharpness
examples for the earlier small-uniformity theorem. They certify upper bounds on
circumference, rather than hiding a long-cycle witness.

## The proposed planted generator and its fatal attack

The triage experiment used only standard-library code and the exact native
objects above. For each seed it:

- sampled `L=2k=24` distinct defining vertices;
- planted 24 distinct `r=16` hyperedges, each containing its required
  consecutive defining pair and 14 filler vertices;
- added degree-balanced random 16-edges until every one of `n` vertices had
  degree at least `k=12`; and
- randomly reordered all hyperedges.

Thus the answer was known before the instance, and direct containment checks
would verify it. A Tarjan articulation-point check on the incidence graph
confirmed 2-connectivity on all tested instances. Since `n >= 128` and
`|E(H)| >= 99`, Theorem 7's promised length is exactly 24.

The attack does not detect the plant. Starting from a random vertex, it
repeatedly chooses an unused incident hyperedge and then an unused vertex in
that edge. At 24 vertices it checks for an unused hyperedge back to the start,
restarting if necessary. Each successful output was independently checked for
24 distinct vertices, 24 distinct hyperedges, and all 24 consecutive-pair
containments.

| `n` | attempts | valid instances | attack successes | hyperedges | median incidence scans | maximum scans | median attack seconds |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 128 | 32 | 32 | **32** | 99–110 | 314.5 | 1,491 | 0.000110 |
| 256 | 32 | 32 | **32** | 203–223 | 626 | 2,135 | 0.000222 |
| 512 | 32 | 32 | **32** | 387–448 | 942.5 | 2,254 | 0.000390 |

The walk was capped at 64 restarts. Its median restart count was 1, 2, and 3,
respectively. Growing the ambient vertex set while keeping the 48-identifier
witness fixed therefore grows the haystack but does not create hardness: the
same inexpensive attack continues to return some valid long cycle. It is
irrelevant whether it recovers the generator's planted one, because `verify`
must accept any valid witness.

This result is consistent with the source theorem's regime. Minimum degree and
2-connectivity force enough incidence structure to create a long cycle; random
fill creates many locally available continuations. The theorem guarantees an
answer, while the proposed random distribution makes alternatives plentiful.

## Step-0 certificate-cost test

**What algorithm produces the certificate, and what does it cost?**

For the proposed planted distribution, the certificate is produced by the
randomized incidence walk above. At the largest tested fixed-answer setting it
used a median of 943 and a maximum of 2,254 edge-incidence scans, taking a
median 0.00039 seconds, and solved 32/32 instances. This is already an attack a
solver could express directly from Definition 1.1; no theorem machinery is
needed.

For a possible Track B interpretation, there are only two cases:

- **No visible plant structure.** The solver's compact route is the same
  incidence walk: roughly 943 scans at `n=512`. There is no shorter invariant,
  symmetry, or change of variables in the paper that recovers the hidden
  alternating sequence, so mechanical and compact costs are comparable.
- **Expose a planted order or recurrence.** Following it takes about 24
  successor choices, 24 containing-edge choices, and writing 48 identifiers
  (roughly 96 elementary steps). But this "shortcut" is the planted answer in
  disguise, not a consequence of Theorem 7. The by-hand follow-the-recurrence
  attack would succeed, so the required fourth failing Track B attack and the
  hinted G9 gate would both fail.

The general incidence-graph formulation also does not rescue Track B. A full
cycle search can be implemented by backtracking or fixed-length cycle
algorithms, but the paper neither states such an algorithm nor provides a
sub-300-operation route for arbitrary theorem-valid inputs. Its proof's choice
of a longest cycle is an existential extremal device, not compression advice.

## Other paper-native families considered

| Candidate | Outcome | Reason |
|---|---|---|
| Sample any hypergraph satisfying Theorem 7 and ask for its guaranteed cycle | **G fails** | The contradiction proof guarantees existence but does not hand the generator a concrete alternating sequence; obtaining one requires cycle search. |
| Plant the alternating sequence, as prior triage proposed | **H fails on Track A** | The paper gives no distributional hardness, and the incidence-walk attack solved 96/96 tested instances over three sizes. |
| Turn the plant into a visible algebraic/label pattern | **H fails on Track B** | The compact route is an invented leak and is itself a successful in-context attack. |
| Ask for a longest cycle or the circumference | **V fails** | A submitted cycle proves only a lower bound. The paper supplies no finite, cheaply executable optimality certificate for an arbitrary instance. |
| Ask for a best lollipop or dcp-pair | **V fails** | "Best" is defined by global comparison beginning with a longest cycle; checking optimality requires the forbidden search. |
| Use Construction 1.1's separators/blocks as the answer | **H fails** | The common vertices and components are recovered directly by edge intersection and connectivity scans; the construction is an exposed extremal example outside the main theorem's degree threshold. |

## Gate outcome

| Requirement | Result | Evidence |
|---|---|---|
| G — known witness by construction | Possible only with planting | Sample the 24 vertices and 24 containing edges first. The theorem-only alternative does not produce an executable witness. |
| H — Track A distributional hardness | **Fail** | No such theorem appears in the paper; a direct attack solved 96/96 theorem-valid planted instances. |
| H — Track B no-tool compression | **Fail** | Without leaking the plant there is no compact paper-backed route; with the leak, the obvious in-context attack succeeds. |
| V — exact witness checking | Pass in isolation | Check shape, distinctness, index ranges, and the 24 pair-in-hyperedge containments. |
| Overall | **Rejected at Step 0** | G, H, and V do not hold simultaneously for a paper-backed family. |

The measured attack also explains why random-guess resistance would be
misleading here: a uniformly sampled 48-identifier alternating sequence has
tiny probability of verifying, while a solver that grows a path through the
incidence graph succeeds almost immediately. Cardinality is not the relevant
difficulty signal.
