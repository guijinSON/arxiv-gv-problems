# Rejected at Step 0: arXiv:1003.1520

Paper: Zoltán Kása, [*On arc-disjoint Hamiltonian cycles in De Bruijn
graphs*](https://arxiv.org/abs/1003.1520) (v3, 2013).

## Decision

No generator is shipped. The prior-triage proposal—construct `B(q,k)` and
retain known arc-disjoint Hamiltonian cycles—does not give an unlimited
answer-first family. The scalable statement needed to justify those retained
answers is **Conjecture 1**, and the more structured morphism version is
**Conjecture 2**. The paper proves neither. Running its displayed backtracking
procedure until a suitable cycle is encountered would obtain the certificate
by solving the very instance being generated, which is forbidden by G.

The paper's four displayed successful parameter pairs can be retained as fixed
known instances, but rotations and alphabet renamings are isomorphisms and must
collapse under `canonical_key`. They therefore cannot meet G7/G8 or manufacture
an unlimited difficulty ladder.

The natural weaker fallback—ask for just one Hamiltonian cycle in a De Bruijn
graph—does pass G and V, but fails H on **Track A** because the paper itself
gives the standard linear-time Euler-tour construction. It also fails **Track
B** because, under the answer cap, the mechanical construction is already
output-linear and there is no shorter compact route. This is a Step-0
rejection, not a G9 rejection; no module, self-test report, README, or oracle
transcripts were fabricated after the G/H failure.

## What the paper actually says

Pages 1–2 define the directed De Bruijn graph `B(q,k)` exactly:

- its `q^k` vertices are all length-`k` words over a `q`-letter alphabet;
- its `q^(k+1)` arcs are the length-`k+1` words; and
- there is an arc from `x_1...x_k` to `y_1...y_k` exactly when
  `x_2...x_k = y_1...y_(k-1)`.

A Hamiltonian path/cycle spells a De Bruijn word. The paragraph immediately
before Conjecture 1 observes that `B(q,k)` is Eulerian and that an Eulerian
circuit in `B(q,k)` gives a Hamiltonian path, extendable to a cycle, in
`B(q,k+1)`.

**Conjecture 1 (page 3)** claims that the maximum number of pairwise
arc-disjoint Hamiltonian cycles in `B(q,k)` is `q-1` for `q >= 2`, `k > 1`.
The upper bound is forced by the `q-1` non-loop outgoing arcs at a constant-word
vertex, but the paper does not prove the lower bound.

For **Conjecture 2 (pages 3–4)**, the alphabet morphism `mu` fixes `0` and
cycles `1,2,...,q-1`. It claims that one can choose a Hamiltonian cycle `H0`
such that

```text
H0, mu(H0), mu^2(H0), ..., mu^(q-2)(H0)
```

are pairwise arc-disjoint. The paper proves only that these formulations are
equivalent and displays witnesses for four parameter pairs:

| graph | vertices per cycle | displayed cycles | explicit answer atoms |
|---|---:|---:|---:|
| `B(3,2)` | 9 | 2 | 18 |
| `B(3,3)` | 27 | 2 | 54 |
| `B(4,2)` | 16 | 3 | 48 |
| `B(5,2)` | 25 | 4 | 100 |

Here an atom is one vertex ID and the repeated closing vertex is omitted. If
only `H0` is submitted and the checker expands its morphic orbit, the answers
use 9, 27, 16, and 25 atoms respectively, but this compression does not turn
four lookup entries into a scalable construction.

The displayed `DeBruijn` procedure on pages 1–2 is an enumerator: it recursively
tries symbols while marking already seen length-`k` words. It can generate all
De Bruijn words, after which one could test the morphic orbit for arc
disjointness. That is certificate **search**, not an answer-first generator.
For scale, the standard count of cyclic De Bruijn sequences is
`(q!)^(q^(k-1)) / q^k`; even the paper's small cases contain 24 cycles for
`(3,2)`, 373,248 for `(3,3)`, 20,736 for `(4,2)`, and 995,328,000 for `(5,2)`.
Enumerating until a compatible `H0` appears is exactly the work the proposed
solver is meant to do.

## The certificate-production question

There are only three honest ways to implement the triaged proposal, and none
clears the gates:

| proposed generator | what produces its certificate | outcome |
|---|---|---|
| General `q,k`, run the paper's recursion and test `mu`-orbits | Backtracking search through De Bruijn words | **Fails G:** the generator solves the instance. |
| Hard-code the four displayed `H0` words and relabel/rotate them | A four-row lookup table plus graph automorphisms | **Fails G7/G8 and H:** no scalable family; relabellings have the same structural key. |
| Import a later constructive result for a weaker collection or a special alphabet regime | An efficient rewiring/feedback-shift-register construction | **Fails Track A H:** the domain-standard constructor succeeds; an explicit-cycle witness remains output-linear. It also no longer implements this paper's morphism conjecture in general. |

As a cross-check rather than a substitute for reading this paper, Lin, Ward,
Jain, and Skiena's later Theorems 7–8 in [*Constructing Orthogonal de Bruijn
Sequences*](https://doi.org/10.1007/978-3-642-22300-6_50) construct two
orthogonal tours for `q >= 3` and at least `floor(q/2)` in general. Their
Section 3.1 still describes Kása's full `q-1` morphic family as a conjecture and
reports only finite computational evidence. Thus a weaker theorem-backed
family exists, but it is produced algorithmically and is not the proposed
full collection.

## Mechanical cost versus compact route

The efficient one-cycle fallback must be considered before rejecting merely
because "an algorithm exists." Let `N = q^k`. Hierholzer's algorithm on
`B(q,k-1)` traverses its `N` arcs once and returns the corresponding
Hamiltonian cycle in `B(q,k)`. The required explicit witness contains `N`
vertex IDs, so every route also has an `Omega(N)` output cost.

I measured a standard-library deterministic implementation at the largest
single-cycle setting allowed by G9's 256-atom cap, `B(4,4)`:

| quantity | measured value |
|---|---:|
| Hamiltonian-cycle answer atoms | 256 |
| Euler-tour arc traversals | 256 |
| stack pops, including the repeated start | 257 |
| median wall clock over 20,000 runs | 41.04 microseconds |
| compact-route lower bound | 256 vertex emissions |

The meaningful ratio is therefore one arc construction per emitted answer
atom (or about two simple loop events per atom if stack pops are counted).
The alleged compact route is the same output-linear tour construction. Making
the graph larger lengthens the answer and immediately crosses G9; it does not
open a million-operations-versus-dozens compression gap.

For the paper's intended full collection the explicit output has
`(q-1)q^k` atoms. The largest displayed example, `B(5,2)`, takes only 100
atoms; expanding its three nontrivial morphic images from `H0` costs 75 symbol
substitutions and emitting all four cycles costs 100 symbols. This is again
the same scale as the written witness.

It is true that blind backtracking for a *morphism-compatible* `H0` can be
enormous. That does not establish Track B, because the paper supplies no
scalable compact route to such an `H0`. A private hard-coded word is not an
instance-visible insight. Revealing enough of that word to make recovery
compact makes the obvious follow-the-revealed-cycle attack succeed, while
hiding it leaves the solver with the same backtracking search.

## Why random planting does not rescue the proposal

One could first choose a known cycle and then add random allowed/forbidden arcs
inside the De Bruijn graph. This would satisfy inverse generation and exact
verification, but it is a new distribution of **constrained subgraphs**. No
theorem or complexity result in this paper analyzes that distribution. There
is therefore no Track A hardness basis. On Track B, a hidden random plant has
no solver-visible compact route; a visibly structured plant becomes the
mandatory successful in-context attack. Adding generic graph, SAT, or
exact-cover decoys would be benchmark convenience, not support from Kása's
conjectures.

## Gate outcome

| requirement | result |
|---|---|
| G for `q-1` arc-disjoint cycles | **Fail:** the necessary scalable claim is Conjecture 1/2; the paper's only certificates are four fixed examples, and its general procedure searches for them. |
| H — Track A | **Fail:** no computational or distributional hardness theorem is present; the one-cycle fallback has a linear-time standard algorithm. |
| H — Track B | **Fail:** for one cycle, 256 arc traversals versus 256 mandatory emissions at the largest writable size; for the conjectured family, no scalable compact route exists. |
| V | Passable: check each list is a permutation of all `q^k` vertices, every consecutive overlap is an arc, and the cycle arc sets are pairwise disjoint. |
| G7/G8 for the displayed examples | **Fail:** four fixed parameter pairs do not scale, and rotations/alphabet renamings are canonical-key-preserving isomorphisms. |
| Overall | **Rejected at Step 0.** No one paper-native family clears G, H, and V simultaneously. |

The failure is not that Hamiltonian cycles are invalid witnesses. They are
excellent exact witnesses. The failure is that this paper either gives a
linear/output-scale construction for the weak task or only conjectures the
scalable existence needed for the strong task.
