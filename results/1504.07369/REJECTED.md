# Rejection — arXiv:1504.07369

Paper: [Merola, Pasotti, and Pellegrini, *Cyclic Hamiltonian cycle systems of the complete multipartite graph: even number of parts*](https://arxiv.org/abs/1504.07369).

## Decision

The paper clears **G** and **V**, but no reviewed family clears **H** on either track. The deciding failure is H, not the external oracle outage and not the witness rule.

The paper's native objects are Hamiltonian base cycles in `Z_(mn)` and their partial-difference multisets. Definition 2.1 fixes partial differences, and Theorem 2.2 says that base cycles certify a cyclic HCS exactly when their partial differences cover `Z_(mn) \ mZ_(mn)`. A checker can expand compressed cycles, check every vertex and edge, compute the stabilizers and partial differences, and compare multisets using exact modular arithmetic. Thus verification is executable and cheap relative to the certificate. Theorems 4.4 and 4.9 also make generation constructive.

## Why the direct construction does not give H

Theorem 1.1 is a complete existence classification for even `m`. In the `n = 0 mod 4` regime, Theorem 4.4 writes the base paths and their steps out by explicit formulas; Proposition 4.2 does the same for `m=2`. Consequently, the algorithm producing the natural certificate is the paper's formula itself, in time linear in the certificate it emits.

There is no Track A claim: the generated distribution is solved directly by those formulas. There is also no Track B compression gap for the natural “output the HCS” problem. At the prototype's large example `m=8`, part size `131072 = 4t`, Theorem 4.4 emits `3t = 98,304` base-cycle descriptors. Mechanical formula expansion and the alleged compact route both require `Theta(98,304)` output actions. That exceeds the answer cap. If the answer is instead allowed to be the fixed loop formula, the certificate collapses to restating the paper's displayed construction, so its mechanical and compact routes are both constant-size. The two costs are comparable in either representation.

The one non-formula choice in Theorem 4.9 is a `kappa` for which a displayed arithmetic-progression term is coprime to `n/2`. Lemmas 4.7–4.8 guarantee existence. Asking for any such `kappa` is guessable when coprime terms are dense; asking for the first one makes the checker establish all earlier failures unless the answer carries a correspondingly long factor certificate. Neither produces a bounded, hard witness family from the paper's construction.

## Rejected prototype and the missed standard algorithm

The retained [`rejected_gen_1504_07369.py`](rejected_gen_1504_07369.py) tried a transformation family based on the `b=3` cycle in Theorem 4.4. It gives an eight-entry source partial-difference signature, three candidate target signatures in `Z_(2^20)`, and asks for the unit multiplier and its inverse. Generation samples the multiplier first and carries the known cycle through a group automorphism; verification is exact.

The prototype initially appeared to have `1,572,852` structure-aware candidates and exactly one answer. That cardinality was misleading. Every source signature contains four odd residues, and every odd residue is invertible modulo `2^20`. Pick one odd source entry `d`. Its image must be one of the four odd entries `e` in a target, so every possible multiplier is immediately `e * d^(-1) mod 2^20`. Across three targets, at most 12 multipliers need checking.

Measured on eight shipping seeds, this unit-anchor normalization:

| quantity | measured cost |
|---|---:|
| candidate multipliers tried, median | 3.5 |
| candidate multipliers tried, maximum | 12 |
| counted exact modular operations, median | 17.5 |
| counted exact modular operations, maximum | 43 |
| wall clock, median | 0.0000037 s |
| successes | 8/8 |

Its complexity is `O(h r^2 log M)` for `h` targets and signature length `r`, and here `h=3`, `r=8`, and `M=2^20`. This is the domain-standard normalization for a multiplicative group action on a finite set. It is shorter than the proposed modular-sum route, which measured 40 operations at the median and had a conservative 247-operation bound. The mechanical route and compact route are therefore not merely close: the obvious mechanical route is better. This fails Track B. The same deterministic polynomial-time attack also rules out Track A for this distribution. The retained module now includes this attack in its adversary panel and records 8/8 successes.

## External-run note

The required harness was attempted for the bare, structural-hint, and placebo arms. OpenRouter returned HTTP 403 `Key limit exceeded` on every redraw, so all preserved transcript rows are errors and none is counted as a model failure. This infrastructure problem is not part of the rejection rationale; the exact 8/8 unit-anchor break is sufficient without an oracle experiment.

In short: Theorem 2.2 gives an excellent exact verifier and Theorems 4.4/4.9 give excellent generators, but the paper's own formula makes the natural family mechanically direct, while the attempted hidden-automorphism variant has a 12-candidate anchor attack. G and V pass; H fails on Track A and Track B.
