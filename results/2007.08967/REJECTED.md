# Rejected: arXiv 2007.08967

Paper: Alan Koch, [*Abelian maps, bi-skew braces, and opposite pairs of
Hopf--Galois structures*](https://arxiv.org/abs/2007.08967), v2 (2020).

## Decision

No problem generator from this paper is shipped.  The strongest paper-native
candidate passes **G** and **V**, and it has a real mechanical-versus-compact
gap on **Track B**, but it fails the mandatory **G9(b) hinted hardness gate**.
The structural hint made the compact route executable by an oracle both at the
initial shipping candidate and after the one upward move permitted by the
protocol.  That is terminal under Step 4.

In the requested G/H/V terminology: **G** passes, **V** passes, **H** fails on
Track A because an explicit inverse exists, and the only viable Track B
replacement fails the mandatory no-tool hinted-hardness test.

This is not a Track-A claim.  Corollary 5.4(3) explicitly gives the inverse of
the relevant Yang--Baxter map, so presenting the family as structurally hard
would be false.  A candidate module was implemented to measure the Track-B
alternative and was withdrawn after the script-owned oracle evidence rejected
it.

## What the paper actually defines

Section 2.3 defines a skew left brace `(B, dot, circle)` and its associated
nondegenerate set-theoretic Yang--Baxter map.  Theorem 3.1 constructs a regular,
`G`-stable permutation subgroup from any endomorphism `psi:G->G` with abelian
image.  Proposition 5.1 puts the two group operations directly on `G`:

`g circle h = g psi(g^-1) h psi(g)`,

and proves that the result is a bi-skew brace.  Corollary 5.4 writes down four
Yang--Baxter maps `R_1,...,R_4`; crucially, part (3) states
`R_1 R_2 = R_3 R_4 = id`.

The attempted family used the paper's objects without a graph or finite-field
surrogate.  Example 4.1 licenses the normal-complement projection.  It was
specialized to

`G = F_p^d semidirect C_(p-1)`,

where a primitive field element `omega` makes `b in C_(p-1)` act on the vector
space by multiplication by `omega^b`, and `psi(x,b)=(0,b)`.  The solver was
handed this nonabelian group, its abelian endomorphism, and an iterate of the
native map `R_1` from Corollary 5.4.

## The attempted Track-B family

The generator sampled an ordered source pair first and applied `R_1` forward,
so its certificate was known by inverse generation.  It then asked the solver
to recover the unique source from the public target after `n` iterations.
Both elements were restricted to the same cyclic coordinate `a`.  Exact group
substitution reduces one step on their vector parts to

`(x,y) -> (s*y, x+(1-s)*y)`, where `s=omega^(-a)`.

The checker used the closed powered identity over `F_p`; it did not read the
planted answer.  The bounded, structure-aware candidate language already
enforced the visible invariant `x+y=target_sum`.  At the initial candidate
`p=65537,d=3`, that language had **281,487,861,809,152** members.  There was one
valid answer, and uniform invariant-respecting sampling found **0/200,000**.

The five non-reference attacks all failed on eight shipping seeds:

| attack | successes |
|---|---:|
| coordinatewise minimum/outlier | 0/8 |
| target-as-source greedy guess | 0/8 |
| 512 invariant-respecting random restarts | 0/8 |
| one inverse step by hand | 0/8 |
| zero-eigenmode ansatz | 0/8 |

The bare four-vendor hardening run also held at the initial candidate: **0/3**
valid answers (OpenAI, Google, and Anthropic on distinct seeds).

## Mechanical cost and compact route

Corollary 5.4(3) supplies the mechanical inverse: apply `R_2` repeatedly.
On the equal-coordinate slice this costs `3*d*n` exact field operations after
setup.

| tested setting | mechanical route | measured wall time | compact route |
|---|---:|---:|---:|
| initial: `n=200003,p=65537,d=3` | 1,800,027 field operations | 0.115 s | at most 108 field operations |
| one permitted move: `n=800013,p=1000003,d=3` | 7,200,117 field operations | 0.530 s | 105 field operations, 0.000012 s |

The compact route is the change of variables

`C=x+y`, `D=x-s*y`.

One step fixes `C` and multiplies `D` by `-s`; hence the preimage follows from
one modular power `(-s)^(-n)` and a two-by-two reconstruction in each vector
coordinate.  The gap is large enough that the candidate was correctly treated
as Track B rather than rejected merely because an efficient algorithm exists.
It was rejected only after the required hinted experiment showed that the
compact route was executable in context.

## The fatal G9(b) evidence

The structural hint was exactly one sentence: "Use the coordinates `C=x+y`
and `D=x-sy`: one step fixes `C` and multiplies `D` by `-s`."

| hinted setting | oracle results | outcome |
|---|---|---|
| `n=200003,p=65537,d=3` | Grok solved; Claude and Gemini failed | **G9(b) fail; move up once** |
| `n=800013,p=1000003,d=3` | Grok solved; OpenAI and Gemini failed | **G9(b) fail again; reject** |

The two successful witnesses were parsed and accepted by the exact verifier;
they were not format accidents or API failures.  The second successful call
used seed `995325822` and took 548.55 seconds.  Because G9(b) permits only one
upward move, further increases in the modulus, iteration count, or arithmetic
burden would be hand-tuning past a terminal verdict.  The placebo arm was not
run after this failure because it is diagnostic only and cannot reverse G9(b).

Thus the gate status is:

| requirement | result | evidence |
|---|---:|---|
| G -- known certificate by construction | pass | sample the source pair, then apply the powered `R_1` identity |
| H -- Track A structural hardness | **fail** | Corollary 5.4(3) explicitly supplies `R_2=R_1^-1` |
| H -- Track B no-tool compression | promising bare, but **rejected by G9(b)** | the hinted compact route solved at both allowed settings |
| V -- cheap exact witness checking | pass | exact finite-field substitution into the powered coordinate map |
| G4 | pass | 0/200,000 in a 281,487,861,809,152-element structure-aware language |
| G6 | pass locally | five attacks at 0/8; successful reference algorithm reported separately |
| G9(b) | **fail** | hinted oracle solved before and after the sole allowed move |

## Why the other paper-native tasks do not rescue the paper

| candidate task | reason it does not qualify |
|---|---|
| Given `psi`, output the regular subgroup `N_psi` or its opposite | Theorem 3.1 and Corollary 3.2 are direct elementwise formulas; the mechanical and compact routes are the same, and the full permutation table soon violates the output cap. |
| Given `psi`, output the brace law or a Yang--Baxter map | Proposition 5.1 and Corollary 5.4 explicitly write them down.  This is direct evaluation, not witness search. |
| Classify abelian maps on `S_n`, `M_(p,q)`, or `D_n` | Examples 3.7 and 3.8 and the end of Section 6 give explicit parameter classifications.  Returning a listed parameter is either a lookup/direct scan or has a small answer space. |
| Recover equivalent maps using Proposition 3.3 | The central homomorphism is obtained pointwise as the quotient of the two supplied maps; no distinct compact insight remains. |
| Determine the isomorphism type of general `N_psi` | Section 6 says there appears to be no easy general method, but supplies only partial subgroup information, not a scalable planted distribution with a bounded exact certificate and justified hardness.  Hiding a relabelling would introduce a new group-isomorphism benchmark not analyzed by this paper. |
| Construct the Hopf--Galois algebra itself | The paper's correspondence is constructive, while a full group-algebra/action witness is bulky; no separate hard search problem or compact certificate is established. |

The rejected inverse family was the only natural candidate with a measured
mechanical/compact separation, a constant-size witness, and exact verification.
Its terminal hinted-oracle result leaves no honest family satisfying all of the
required gates.
