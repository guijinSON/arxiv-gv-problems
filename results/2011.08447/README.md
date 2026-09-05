# Planted-clique witness generator (arXiv:2011.08447)

> **Status: rejected.** This is retained exploratory evidence, not a shipping
> family. `REJECTED.md` records the decisive issue: the paper's theorem regime is
> polynomial-time, while the below-threshold fallback has no compact no-tool route
> after the claimed insight. The HTTP 403 oracle transcript is not hardness evidence.

| profile field | value |
|---|---|
| Track | A -- structural hardness |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate | integer tuple (a vertex set) |
| Intuition | search pruning by persistent common neighborhoods |
| Domain essentiality | native; no reduction |

## Problem and trust model

This module uses the ordinary planted-clique specialization of Yash Khanna's
[*Exact recovery of planted cliques in semi-random graphs*](https://arxiv.org/abs/2011.08447).
Definition 2 constructs the semi-random graph; Section 1.4 explicitly says that
`r=t=0` leaves a planted clique in `G(n,p)`. The generator first samples the answer
set `S`, forces all pairs in `S` to be edges, and flips an independent fair coin for
every other pair. It never searches the finished graph. A submitted witness is checked
exactly by range/distinctness tests and `C(k,2)` adjacency lookups; `verify` never reads
the planted answer.

The Track A claim deliberately avoids Theorem 2's easy regime. That theorem recovers
the plant in polynomial time when `k=Omega(sqrt(np(r+t+2)))` under its stated
conditions, using SDP 1 and Algorithm 1. Here `p=1/2` and
`k=ceil(1.1 n^0.4)=o(sqrt(n))`. Section 1.4 cites the
[Barak--Hopkins--Kelner--Kothari--Moitra--Potechin SoS lower bound](https://arxiv.org/abs/1604.03084),
which gives a nearly tight `n^(1/2-o(1))` barrier for degree `d=o(log n)` SoS. This is
evidence against a broad standard algorithm family, not a proof that every algorithm
is slow. At `n=768,k=16`, a dependency-free exact color-bound search exhausted 100,000
nodes on all eight seeds (54.58 seconds total), and four cheaper recovery attacks also
failed 8/8.

## Worked demo

This `demo` instance is small enough to solve and check on paper (`seed=0`):

```text
PLANTED-CLIQUE WITNESS PROBLEM
Vertices: 0 through 15. Find 6 vertices inducing a clique.
For row i, bit offset t is the edge (i, i+1+t).

0: 001111110101011
1: 11010001011011
2: 1111110001011
3: 100100001110
4: 11110011101
5: 0111100110
6: 111111101
7: 10110010
8: 1101011
9: 100110
10: 11000
11: 1011
12: 111
13: 00
14: 0
15: -
```

The answer is `<answer>0, 4, 6, 8, 12, 15</answer>`.
`verify(inst, [0,4,6,8,12,15])` returns `(True, "ok")`; replacing the final
vertex by 1 returns `(False, "vertices 0 and 1 are not adjacent")`.

## Difficulty and measured gates

| preset | n | k | role |
|---|---:|---:|---|
| demo | 16 | 6 | hand-solvable illustration |
| easy | 768 | 16 | candidate shipping preset |
| medium | 896 | 17 | harder fallback |
| hard | 1024 | 18 | hardest named rung |

| gate | result |
|---|---|
| G1 | 12/12 planted witnesses verify |
| G2 | 5/5 corruption types rejected with distinct reasons |
| G3 | tagged prose/fence round-trip passes |
| G4 | 0 hits / 200,000 structure-aware uniform `k`-sets; space `598191506203970835856150766731728` |
| G5 | demo has exactly 1 solution among 8,008; shipping density 0/200,000; exact baseline 100,001 nodes on every seed |
| G6 | degree, greedy, 256 restarts, centered spectral, and exact color-bound attacks each succeed 0/8 |
| G7 | doubled `n=1536,k=21` builds and verifies; candidate space increases |
| G8 | 60/60 relabellings preserve the key and transported witness; 20/20 unrelated keys distinct |
| G9(c) | answer is 65 chars / 16 atoms, but the shortest measured answer-producing route still exceeds 100,000 branch nodes -- fails the 300-operation cap |
| G9(b) | pending: OpenRouter key limit blocked every oracle call |

## Oracle loop and G9 arms

| run | preset | outcome |
|---|---|---|
| bare | easy | no scored attempts; 4 HTTP 403 API errors, harness aborted correctly |
| structural hint | easy | not run |
| placebo hint | easy | not run |

There is therefore no valid hinted-minus-placebo diagnostic and no claim that the
structural hint helps. Once OpenRouter quota is restored, rerun the bare command below,
then run the hinted and placebo copies exactly as specified in the task; successful runs
will overwrite the failed bare transcript and replace the pending G9 fields.

## Use

```python
from rejected_gen_2011_08447 import make_instance, render, parse_answer, verify

inst = make_instance(n=768, seed=7)
statement = render(inst)
answer = parse_answer("<answer>...</answer>")
ok, reason = verify(inst, answer)
```

From the repository root, after a valid oracle run:

```bash
python3 scripts/harden.py results/2011.08447/rejected_gen_2011_08447.py
```

## Caveats

The 0/200,000 estimate is only for uniformly sampled `k`-subsets; it does not bound a
clever correlated search. The exact attack is deliberately budgeted, so failure means
“not within 100,000 nodes,” not a lower bound. The paper's SDP was not run because the
allowed dependency set supplies no SDP solver; this is the most important untested
attack. The canonical key is an eight-round color-refinement invariant, not a complete
graph-isomorphism canonizer. Finally, the earlier 135-operation accounting counted
`k-1` intersections and 120 edge checks only after the successful branch was already
known. That assumes the witness and is not valid G9(c) accounting; the measured branch
route exceeds 100,000 nodes. This is the decisive reason the exploratory family is
rejected rather than parked merely for unavailable oracle quota.
