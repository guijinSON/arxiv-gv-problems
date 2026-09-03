# Audit: shipped results vs. the domain-standard attack

`prompts/codex_task.md` did not require the standard algorithm for the problem
class until `606332e`. This audits results shipped before that.

## Coverage

44 results were shipped. Reading their `G6` panels, **29 ran only generic probes**
(outlier / greedy / random-restart) and 15 ran something domain-flavoured (mostly
MRV backtracking or bounded exact cover).

Five of the 29 were selected as highest-risk — families where the paper *itself*
presents an algorithm that solves the planted problem, or where the problem class
has a textbook attack — and the domain attack was written and run.

## Result: 5 attempted, 5 broken

| paper | family | attack | result | time |
|---|---|---|---|---|
| `2503.01929` | exact tiling (3-PARTITION) | Algorithm X / DLX with MRV | **8/8 solved** | <5 s |
| `1512.03127` | monotone 1-in-3-SAT | 1-in-3 propagation + DPLL | **8/8 solved** | <0.1 s |
| `2507.17878` | monotone 1-in-3-SAT | 1-in-3 propagation + DPLL | **8/8 solved** | <1 s |
| `1008.2814` | planted k-disjoint-clique | spectral + randomized greedy | **8/8 solved** | <60 s |
| `0901.3348` | planted clique | spectral + randomized greedy | **5/8 solved** | <45 s |

All five had `G6.pass = True`. All five were declared `hardened` by the
multi-vendor oracle pool. None of that was evidence of hardness.

## Why the generic panel missed them

Outlier / greedy / random-restart probe **how the instance was built** — they look
for a statistical signature left by the planting. They say nothing about **what is
known about the problem class**. A family can be perfectly symmetric, draw plants
and decoys from one distribution, survive every signature test, and still dissolve
under the algorithm the field already uses:

- `2503.01929` respected the 3-PARTITION band `T/4 < a < T/2` exactly, so exactly
  three items fill each block — genuinely the strongly-NP-hard regime. But *random*
  instances in that regime are not hard: ~300 sum-T triples over 96 items is a
  trivial search for MRV backtracking. Worst-case hardness, average-case triviality.
- `0901.3348` correctly put the clique **below** the spectral threshold
  (k=16 < √512≈22.6), which defeats textbook AKS. It did not anticipate that at
  n=512 the clique is close enough to the natural max (2·log₂512≈18) for randomized
  greedy with local search to reach it.
- `1008.2814` planted 3 cliques of size 10 in n=144 where ~36 random 10-cliques
  already exist, and `verify` accepts *any* 3 disjoint 10-cliques. The planted
  answer was never needed.

## The lesson, stated for the prompt

Gates passing and a strong oracle failing to solve are **jointly insufficient**.
Both were true for all five. The oracle is a weak signal (an LLM is not a SAT
solver), and the generic panel is blind by construction. Only the domain attack
discriminates — which is why `606332e` makes it mandatory and `submit.sh` now
refuses a panel with fewer than four attacks.
