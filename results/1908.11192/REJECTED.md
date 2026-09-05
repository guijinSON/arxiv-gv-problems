# Rejected at Step 0: the paper's certificate is already its fastest construction

Paper: Ajai Choudhry, [*An improvement of Prouhet's 1851 result on
multigrade chains*](https://arxiv.org/abs/1908.11192), arXiv:1908.11192v1
(2019).

## Decision

No generator is shipped.  The proposed equal-power partition is an excellent
exact witness, so the paper can satisfy **G** and **V**, but its paper-backed
families fail **H on both tracks**.

- **Track A fails.**  Lemma 5 and the proof of Theorem 6 are a direct algorithm
  for every instance in the proposed distribution.  They do not merely prove
  that a partition exists: they construct its class label by cyclically shifting
  arbitrary permutations at each induction level.  Theorems 7 and 8 use the
  same algorithm.  The paper contains no worst-case or distributional hardness
  theorem for recovering these partitions.
- **Track B fails.**  The direct induction is already the compact route.  Once
  the cyclic construction is noticed, producing an explicit partition still
  requires one constant-cost label update per output integer.  The mechanical
  and insight routes therefore have the same linear length.  If the induction
  choices are returned as a compressed symbolic certificate instead, every
  well-formed choice is valid, so a structure-aware random candidate succeeds
  with probability 1.

This is an H failure, not a witness-rule failure.  A proposed partition is
checked cheaply by confirming that it uses every input integer exactly once and
recomputing its power sums with exact integer arithmetic.  Per the task's Step-0
stop rule, Steps 1--4 were not run and there is no module, self-test report,
README, or oracle transcript.

## Exact definition and certificate-producing result

Section 1, equations (1)--(2), defines a multigrade chain.  There are `j`
distinct sets, each containing `s` integers, and for every exponent
`r = 1,...,k` all `j` sums of `r`-th powers must be equal.

The relevant results are constructive:

- Lemma 2 pairs `u` with `2j+1-u`, directly partitioning `1,...,2j` into
  `j` equal-sum pairs.
- Lemma 5 turns any order-`k` chain with `j` classes into an order-`k+1`
  chain.  It takes arbitrary distinct shifts `h_1,...,h_j`; the new class `v`
  is formed by cyclically rotating which shift is applied to each old class.
  Its proof verifies the result by binomial expansion.
- Theorem 6 starts with Lemma 2, scales the old integers by `j`, and applies
  Lemma 5 with a permutation of `1,...,j`.  It thereby partitions the first
  `N = 2j^k` positive integers into `j` sets of `2j^(k-1)` members with equal
  power sums through degree `k`.  The proof also states that fixing `h_1=1`
  and permuting the remaining shifts gives at least
  `((j-1)!)^(k-1)` chains.
- Theorems 7 and 8 repeat the same induction from Lemmas 3 and 4, respectively,
  for `N = 2m j^k` and `N = j^(k+1)`.

Thus the answer to the Step-0 discriminating question is: **the certificate is
produced by the induction in the proof of Theorem 6, in linear time in the
number of integers emitted** (after the small inverse-permutation tables are
prepared).

## The executable direct formula

The construction is especially explicit.  Number the integers by
`x = 0,...,2j^k-1`, so the paper's integer is `x+1`.  At induction level `t`,
let `f_t` be the inverse of the chosen permutation of the `j` shifts.  Write

```text
x = d_0 + d_1 j + ... + d_(k-2) j^(k-2) + q j^(k-1),
0 <= d_i < j,  0 <= q < 2j,
b(q) = q                    if q < j,
       2j - 1 - q           otherwise.
```

Then the class label is exactly

```text
f_k(d_0) - f_(k-1)(d_1) + ...
    + (-1)^(k-2) f_2(d_(k-2)) + (-1)^(k-1) b(q)    (mod j).
```

This is just Lemma 5's cyclic shift written without recursion.  Choosing every
shift permutation to be the identity gives a fixed valid witness for every
allowed `(j,k)`; no search and no oracle are involved.  The paper's examples
(11)--(14) in Section 3.2 are small expansions of this construction.

## Mechanical cost versus compact route

An explicit partition contains all `N` integers, so G9(c)'s 256-atom cap forces
`N <= 256`.  The proof can construct labels iteratively.  At level `t` it makes
`2j^t` constant-cost label updates, hence the total number of updates is

```text
sum(t=2..k) 2j^t,
```

plus the unavoidable writes of the final `N` integers.  Two representative
points were evaluated directly from the displayed recurrence:

| parameters | output | paper algorithm | compact route | serialized answer |
|---|---:|---:|---:|---:|
| `j=3, k=4` | 162 atoms | 234 label updates | the same 234 updates | 547 chars, about 137 tokens |
| `j=2, k=7` | 256 atoms | 504 label updates | the same 504 updates | 921 chars, about 231 tokens |

At `j=3,k=4` the route fits the 300-exact-operation cap but has a
mechanical-to-compact ratio of **1**.  At the largest atom-cap example
`j=2,k=7`, both routes exceed the 300-operation limit.  Moving to a smaller
instance can satisfy G9(c), but cannot create a compression gap; moving to a
larger one lengthens the answer and the algorithm together.

It would be misleading to quote exhaustive search over set partitions as the
Track-B mechanical method.  The paper itself gives the linear algorithm that
works on every promised instance, and that algorithm is exactly what a solver
who sees the structure would execute.

## Why a symbolic answer does not rescue the family

One might ask for the `k-1` shift permutations rather than the expanded sets.
That keeps the answer short, but destroys guess resistance.  Lemma 5 permits
**any** permutation of the `j` distinct shifts at every level.  Even after the
paper's normalization `h_1=1`, all

```text
((j-1)!)^(k-1)
```

well-formed strings in that certificate language verify.  A
structure-aware `random_candidate` samples one such string and therefore has

```text
P(random candidate verifies) = 1,
```

which fails G4 by six orders of magnitude.  Asking for the expanded partition
restores a large answer space, but the direct linear solver above then defeats
H.  The two representations cannot pass the gates simultaneously.

## Diversity and alternative-family audit

For fixed `(j,k,m)`, Theorems 6--8 specify one ground instance: a consecutive
integer interval.  The many permutations counted by Theorem 6 are many
*answers to that same instance*, not new instances.  Shuffling the input order
or renaming the classes is a relabelling and must not change `canonical_key`.
Lemma 1 also proves that a common affine change `x -> Mx+K` preserves every
multigrade equality, so affine copies are structure-preserving relabellings for
this family rather than seed-indexed diversity.  A fixed difficulty preset
built this way would consequently fail G8 as well.

Other obvious tasks do not repair the hardness problem:

| candidate task | G | H | V / other issue | outcome |
|---|---:|---:|---:|---|
| Partition `1,...,2j^k` as in Theorem 6 | Pass by theorem construction | **Fail A/B:** direct linear recurrence | Exact substitution passes | Reject |
| Return the induction permutations | Pass | **Fail G4/H:** every well-formed answer works | Exact expansion passes | Reject |
| Randomly reorder or affinely transform the interval | Pass via Lemma 1 | **Fail:** normalize and run the same recurrence | G8 collapses all copies | Reject |
| Compose several affine copies of known chains | Pass by adding equal power sums | Track A has no distributional theorem; a Track-B shortcut would be an added benchmark wrapper, not a result of this paper | Exact checking passes | Reject |
| Determine the least `N(k,j)` from Section 4 | Not generatable in general | Open problem, not a hardness regime | No finite optimality certificate is supplied | Reject |

Adding list-color constraints, hashes, hidden matchings, or finite-field
encodings could manufacture a new planted search problem, but none is licensed
by the paper.  Such a wrapper would either be a convenience reduction that
does not count as native coverage or an unsupported planted distribution with
no Track-A theorem and no paper-backed Track-B compression claim.

## Gate disposition

| requirement | result | evidence |
|---|---:|---|
| G -- certificate known by construction | Pass in isolation | Lemma 5 and Theorems 6--8 construct it directly |
| H -- Track A structural hardness | **Fail** | The proof gives an `O(N + kj)` solver for every generated instance; no distributional hardness theorem is present |
| H -- Track B no-tool compression | **Fail** | Mechanical and compact routes are the same 234 updates at a cap-compliant representative point |
| V -- exact witness verification | Pass in isolation | Check the partition and compare all integer power sums exactly |
| G4 -- structure-aware guessing | **Fail** for compressed certificates | Every legal permutation sequence verifies, so probability is 1 |
| G8 -- canonical diversity | **Fail** for the proposed seed transformations | Certificate choices, reorderings, and affine copies do not create new native instances |
| Overall | **Rejected at Step 0** | No paper-backed family makes G, H, and V hold simultaneously |

No oracle failure or large naive partition count can turn the paper's explicit
construction into a hard generated distribution.
