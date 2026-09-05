# Rejected: arXiv 2408.12412

Paper: Simone Costa and Stefano Della Fiore, [*More Heffter Spaces via finite
fields*](https://arxiv.org/abs/2408.12412), arXiv:2408.12412.

Built and measured by hand (no codex quota available), 2026-09-06.

## Decision

No generator is shipped. The paper's native object is generatable answer-first and
exactly verifiable, but it **fails H on Track B**: the mechanical route and the compact
route cost the same, so there is no gap for a tools-free solver to exhibit.

- **G passes.** A $(v,k)$ Heffter system is a partition of a half-set of $\mathbb{Z}_n$,
  $n=2v+1$, into zero-sum $k$-subsets. It can be constructed answer-first: if
  $\varepsilon$ has multiplicative order exactly $k$ modulo $n$, then for every $x$,
  $x(1+\varepsilon+\dots+\varepsilon^{k-1}) = x\frac{\varepsilon^{k}-1}{\varepsilon-1}
  \equiv 0$, so **every $\langle\varepsilon\rangle$-orbit is zero-sum**. For odd $k$,
  $-1\notin\langle\varepsilon\rangle$, so orbits pair as $O,-O$; choosing one per pair
  gives a half-set exactly tiled by the chosen orbits. Verified for
  $(n,k) \in \{(31,3),(43,3),(61,3),(67,3),(101,5),(103,3),(151,3),(211,5),(331,3),(463,3),(487,3)\}$:
  half-set, zero-sum, block size and partition all hold in every case.
- **V passes.** Checking is exact integer arithmetic: one of $\{x,-x\}$ per nonzero
  residue, blocks partition the point set, each block sums to $0 \bmod n$.
- **H fails on Track B.** Measured below.

## The two numbers the reject gate asks for

Attacks were implemented and run at $v=243$ ($n=487$, $k=3$), the largest size whose
answer fits the 256-atom cap.

| route | cost |
|---|---|
| **mechanical** — Algorithm-X exact cover with MRV over the 4,911 zero-sum triples | **82 backtracking calls, 0.11 s** |
| **compact** — recognise the $\langle\varepsilon\rangle$-orbit structure and read off the blocks | ~81 blocks, i.e. the length of the answer itself |

The mechanical route is not merely polynomial, it is *trivial*: 82 nodes for a 243-point
partition. Scaling confirms it, rather than contradicting it:

| $n$ | $v$ | triples | exact-cover calls | time |
|---|---|---|---|---|
| 151 | 75 | 466 | 26 | 0.00 s |
| 331 | 165 | 2,260 | 56 | 0.03 s |
| 463 | 231 | 4,433 | 78 | 0.09 s |
| 487 | 243 | 4,911 | 82 | 0.11 s |

Growth is *linear* in $v$, so raising $n$ grows the haystack and the needle together and
never opens a gap. The answer cap bounds $v \le 256$, so no reachable size changes this.

Two weaker attacks are recorded because they are misleading on their own: naive
backtracking with fixed `min(rem)` ordering exceeds a 2,000,000-call budget at $n\ge331$,
and randomised greedy with 400 restarts fails outright. Either alone would have suggested
hardness. **MRV ordering is what collapses it**, and a rejection resting on the weaker
attacks would have been wrong.

- **Track A is unavailable.** The paper proves an existence and construction result
  (relaxing point-regular to point-semiregular automorphism groups to reach even $k$).
  It states no worst-case or average-case hardness theorem for recovering a Heffter
  system, so there is no hardness to inherit.

## What would have to change

The paper's actual object is a Heffter *space* — a **resolvable** $(v_r,b_k)$
configuration, so $r$ parallel classes with any two points sharing at most one block.
That is far more constrained than the single partition attacked here and might well
clear H. It is not shipped because I could not construct one answer-first: the orbit
trick yields exactly one parallel class ($r=1$), and $\mathbb{Z}_n^{*}$ being cyclic has
a unique subgroup of order $k$, so additional classes cannot come from a second such
subgroup. Constructing $r>1$ directly is the paper's own contribution and needs its
semiregular-group machinery. A builder with quota should attempt that framing rather
than this one.
