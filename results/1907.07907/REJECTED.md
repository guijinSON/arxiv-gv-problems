# Rejected at Step 0: the paper's constructions are the certificate algorithms

Paper: Rogers Mathew, Ilan Newman, Yuri Rabinovich, and Deepak
Rajendraprasad, [*Hamiltonian and Pseudo-Hamiltonian Cycles and Fillings in
Simplicial Complexes*](https://arxiv.org/abs/1907.07907),
arXiv:1907.07907v1 (2019).

## Decision

No generator is shipped. The prior-triage proposal—construct a complete
simplicial complex with a planted Hamiltonian cycle or filling—can satisfy
**G** and **V**, but it fails **H on both tracks**.

- **Track A fails.** The paper proves existence by an explicit recursive
  procedure, `FILL`, and Lemma 2.6 proves that its output is an acyclic filling.
  Theorems 2.7 and 2.8 give the choices that make the filling full-rank in
  dimension two; Theorems 3.2 and 3.5 do the corresponding job in dimension
  three; Theorem 3.8 gives the general near-Hamiltonian construction. The
  paper states no worst-case or distributional hardness theorem for recovering
  these objects. Inverse-planting a filling does not create such a theorem for
  the generated distribution.
- **Track B fails.** For a generic inverse-planted target, the only public
  paper-backed route is the same recursive construction, so there is no
  shorter compact route. The generator's private planted filling is not an
  insight visible to the solver. If the generated instance instead exposes a
  recognizable cone decomposition, Claim 1.1 itself is both the mechanical
  algorithm and the purported shortcut. Their lengths are equal; there is
  nothing to compress.

This is an H rejection, not a witness-rule rejection. A finite list of
weighted simplices is an excellent exact witness: a checker can recompute its
boundary over `F_2` or `Q`, check its support size, and row-reduce the exact
boundary columns to test acyclicity. The failure is that the paper also tells
the solver how to produce such a witness in every parameter regime it settles.

Steps 1--4 were therefore not run. There is no generator, self-test report,
README, or oracle transcript; those artifacts would only test a family already
known to fail the mandatory hardness gate.

## The native objects and exact definitions

Section 1.1 defines a `d`-simplex as a `(d+1)`-element vertex set and the
complete complex `K_n^d` as all simplices of dimension at most `d` on `[n]`.
A `d`-chain is a formal linear combination of oriented `d`-simplices over
`F_2` or `Q`. Its boundary is the alternating sum of its codimension-one faces.
A chain is a cycle when its boundary is zero.

A set of `d`-simplices is acyclic when its boundary columns are linearly
independent. A maximal such set is a `d`-hypertree; every `d`-hypertree in
`K_n^d` has rank

`r(n,d) = C(n-1,d)`.

For a given `(d-1)`-cycle `Z`, a `d`-filling is a chain `F` with
`boundary(F)=Z`. Section 1.1 observes that every fixed `d`-hypertree supports a
unique filling of every `Z`; obtaining it is exact linear algebra in a known
basis. A filling has deficit `C(n-1,d)-|support(F)|`. A zero-deficit filling of
the boundary of one `d`-simplex is called Hamiltonian, and adjoining that
simplex gives a simple Hamiltonian `d`-cycle of size `C(n-1,d)+1`.

These are the paper's own finite simplicial-chain objects. Replacing them by a
graph Hamiltonian-cycle instance on an arbitrary allowed-edge graph would not
be licensed: the paper studies the complete complex, and for `d=1` that is the
complete graph, where a Hamiltonian cycle is immediate.

## What produces the certificate

The discriminating Step-0 question has a direct answer in the paper.

1. Claim 1.1 says that if `T_d` and `T_(d-1)` are forests on `V`, then
   `T_d union Cone(x,T_(d-1))` is a `d`-forest on `V union {x}`. The same
   operation sends two hypertrees to a hypertree. Thus a cone decomposition is
   already an executable construction certificate.
2. The displayed `FILL` procedure in Section 2 chooses a pivot vertex, fills
   its link recursively, removes its star, and combines a lower-dimensional
   cone with a recursive same-dimensional filling.
3. Lemma 2.6 proves for **every** choice of pivot that `FILL` returns an acyclic
   filling and gives the exact deficit recurrence.
4. Over `F_2`, Theorem 2.7 proves that every nonzero 1-cycle has a 2-filling of
   deficit at most one, and a zero-deficit filling whenever the parity
   condition holds. Its proof explicitly chooses one of several spanning-tree
   fillings at each recursion level. Theorem 2.8 gives zero-deficit fillings
   over `Q`, apart from the two stated small exceptions, and at least two for
   `n >= 6`.
5. Theorems 3.2 and 3.5 extend the same recursive method to 2-cycles over
   `F_2`; the base cases are a finite exhaustive computation recorded in
   Appendix B.1. Theorem 3.8 inducts on `(d,n)` to obtain deficit
   `O(n^(d-3))` in all higher dimensions.
6. Theorem 4.1 then reads off the extremal cycle results. In particular, over
   `F_2` a Hamiltonian 2-cycle exists exactly for `n = 0 or 3 (mod 4)`; over
   `Q` it exists for every `n >= 4` except `n=5`.

The parity obstruction is an easy regime too, not a hard negative family.
Definition 2.1 reduces it to one parity comparison. A yes/no or residue answer
has a tiny answer space and fails G4, while attaching a full filling returns to
the constructive algorithms above.

## Mechanical cost and compact-route comparison

I measured a concrete would-be Track B family rather than rejecting merely
because the word "constructive" appears in the paper.

For each of 20 deterministic seeds, the diagnostic first made a random
2-hypertree by repeated applications of Claim 1.1, using a random Prüfer tree
at every cone step. It then published only the target 1-cycle
`Z = boundary(F)` over `F_2`. The reference implementation recovered another
zero-deficit filling from `Z` using the proof of Theorem 2.7:

- choose an incident pivot;
- realize the pivot link as the odd-degree set of a spanning tree (via a
  Prüfer sequence);
- choose an alternative tree if the next cycle would be zero; and
- recurse, combining the returned filling with the cone.

With edge sets represented by hash sets this reference route uses `O(n^3)`
primitive set work in dimension two (and `O(n^2)` stored faces, which is also
the output scale). For every fixed `d`, the paper's two-branch recurrence has
the same binomial/output-size character; allowing `d` to grow makes the output
itself exceed the benchmark cap except in the trivial codimension-one cases
discussed below.

The operation counter charged one unit for each degree update, tree edge,
scanned edge, or symmetric-difference membership operation. Boundary checking
was performed separately and was not included in the count. Timings use
standard-library Python in this workspace.

| `n` | output triangles `C(n-1,2)` | median / maximum counted operations | median / maximum wall time |
|---:|---:|---:|---:|
| 14 | 78 | 1,342 / 1,576 | 0.000488 / 0.002459 s |
| 18 | 136 | 2,806 / 2,984 | 0.000561 / 0.002215 s |
| 20 | 171 | 3,775 / 4,269 | 0.000727 / 0.001326 s |
| 22 | 210 | 5,042 / 5,410 | 0.000926 / 0.001264 s |
| 24 | 253 | 6,457 / 6,993 | 0.001076 / 0.001441 s |

All 100 recovered chains had exactly `C(n-1,2)` triangles and reproduced the
published boundary exactly. At `n=24`, 253 is already the largest writable
rank if each entire triangle is generously encoded as **one** integer simplex
ID; `n=25` needs 276 output atoms and violates the 256-atom cap. Writing each
triangle naturally as its three vertices reaches the cap earlier.

The Track B comparison is therefore:

| Proposed distribution | Mechanical cost at the writable boundary | Compact route | Result |
|---|---:|---:|---|
| Generic inverse-planted target cycle | Theorem 2.7 recursion: median 6,457 counted operations and 0.001076 s at `n=24` | **The same recursion**, about 6,457 operations; the hidden planted chain is unavailable to the solver | Fail: ratio 1 and the route exceeds the 300-operation no-tool cap |
| Publicly recognizable conical target | Enumerate the Claim 1.1 cone construction, at most one combinatorial generation step per one of the 253 output faces | **The identical cone construction**, at most 253 face-generation steps | Fail: ratio 1; the purported insight is already the cheapest mechanical algorithm |
| Bare `K_n^2`: “give any Hamiltonian cycle” | Apply Theorem 2.7/4.1 after the congruence test | The same theorem construction | Fail H; seeds can only relabel one complete-complex problem and also fail G8 canonical diversity |

The first row has a mechanical computation too long to perform comfortably by
hand, but no short solver-side invariant exists. That is not Track B: private
generator state is not no-tool compression. The second row has a short route,
but it is also the standard algorithm for that restricted distribution. Calling
the first row's general recursion the reference algorithm while quietly using
the second row's visible formula as a shortcut would be an artificial comparison.

Higher dimensions do not open a useful writable regime. Even with one integer
ID per simplex, a full 3-filling has `C(n-1,3)` atoms: `n=13` has 220, while
`n=14` has 286 and exceeds the cap. The paper's dimension-three construction
also bottoms out in the finite `n <= 7` table checked by the Appendix program.
For `3 <= d <= n-3`, the rank `C(n-1,d)` reaches the cap at least as quickly
as the two-dimensional case. The only scalable opposite-edge case is
`d=n-2`, where there are exactly `n` possible `d`-simplices and their full set
is the boundary of the unique `(d+1)`-simplex: the Hamiltonian cycle is
immediate and unique. The case `d=n-1` is still more trivial. Thus moving to
high dimension either shortens the writable ladder or collapses the search.

## Why inverse planting and succinct encodings do not rescue H

Sampling a hypertree first and publishing its boundary is a valid inverse
generator. It establishes G only. On the generated target, the planted support
has no privileged status: `verify` must accept any full-rank chain with the
same boundary, and Theorem 2.7 constructs one without recovering the plant.

A short seed or pivot list is not, by itself, the paper's filling object. To
make it a witness the checker would have to define and execute an expansion.
If that expansion is `FILL`, the candidate must determine its lower-dimensional
tree choices and the solver still has the same recursion. If it is a special
closed formula, recognizing or decoding the benchmark designer's seed—not
simplicial filling—is the search problem. When that formula is visible, it is
also the direct mechanical solution; when it is hidden, there is no compact
route available from the instance. Neither case supplies the required Track B
gap.

Similarly, adding forbidden faces, an arbitrary subcomplex, a SAT encoding, or
a graph-isomorphism wrapper could manufacture a different hard problem, but no
section of this paper licenses those changes. They would be convenience
reductions whose hardness comes from the added wrapper rather than from the
paper's complete-simplicial-complex results.

## Candidate-family audit

| Candidate task | G | H on Track A | H on Track B | V | Outcome |
|---|---:|---:|---:|---:|---|
| Fill a supplied cycle on a fixed hypertree | Pass by inverse planting | **Fail:** unique coordinates are exact linear algebra | **Fail:** the basis solve is both routes | Pass by boundary and rank | Reject |
| Find a zero-deficit 2-filling over `F_2` | Pass by planting a hypertree and taking its boundary | **Fail:** Theorem 2.7 is constructive | **Fail:** 6,457 mechanical versus 6,457 compact operations for generic targets | Pass exactly | Reject |
| Find a zero-deficit 2-filling over `Q` | Pass | **Fail:** Theorem 2.8 and fixed-hypertree linear algebra | **Fail:** no shorter public route | Pass with rational arithmetic | Reject |
| Output a Hamiltonian 2-cycle in `K_n^2` | Pass by Theorem 4.1 | **Fail:** congruence plus construction | **Fail:** same construction; no diverse instance data | Pass by boundary, size, and rank | Reject |
| Output a near-Hamiltonian higher-dimensional cycle | Pass by Theorem 3.8 | **Fail:** the theorem's proof is the recursive algorithm | **Fail:** no separate shortcut; writable `n` is small | Pass exactly, but output quickly reaches the cap | Reject |
| Certify nonexistence in the parity-obstructed cases | Pass with the parity calculation | **Fail:** one parity comparison | **Fail:** identical one-step route | Exact, but answer space is tiny | Reject |

## Gate outcome

| Requirement | Result | Evidence |
|---|---:|---|
| G — known certificate by construction | Possible in isolation | Claim 1.1, `FILL`, or inverse planting |
| H — Track A structural hardness | **Fail** | No hard generated regime is proved; the settled regimes have constructive algorithms |
| H — Track B no-tool compression | **Fail** | Generic targets have no compact route; structured targets make the compact and mechanical constructions identical |
| V — exact witness checking | Possible in isolation | Exact boundary comparison and exact boundary-column rank |
| G8 — structural diversity for the bare complete-complex task | **Fail** | At fixed `(n,d,field)`, all labelings of `K_n^d` are the same canonical instance |
| G9(c) — natural full-support output | Binding but not the rejection reason | At most 253 two-faces under the most generous one-ID-per-simplex encoding |
| Overall | **Rejected at Step 0** | No paper-backed family makes G, H, and V hold simultaneously on either track |

The output cap alone is not being used to reject a valid family, so this is not
`cap_bound`. The decisive failure occurs earlier: every native certificate
family settled by the paper either has the paper's constructive algorithm as
its only route, or becomes a direct cone construction when given recognizable
structure.
