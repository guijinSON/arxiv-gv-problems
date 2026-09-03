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


---

# Second finding: the computational core collapses

The audit above asked whether shipped families were *hard*. A reviewer asked a
different question — whether they are *diverse* — and the answer is no, in a way
the family labels actively hide.

## Measured

`scripts/corpus_report.py` classifies each shipped generator by what the solver is
actually handed:

| computational core | share |
|---|---|
| graph / conflict-graph | 42.5% |
| exact cover | 15.0% |
| CSP / SAT | 10.0% |
| other | 32.5% |

**68% of shipped generators are discrete search at the core**, and **11 of 40 carry
a family label that disagrees with their core** — including both "geometric
configurations" rows.

## How it happens

Not (only) the triage prompt. The generator compiles native structure into a
discrete surrogate, and nothing downstream notices:

- `2104.04330` equiangular lines — a paper about Gram matrices, Seidel matrices and
  eigenvalue interlacing — ships as a 720-vertex adjacency matrix whose `verify`
  docstring reads *"check any size-k clique"*. **The instance contains no vectors.**
- `2404.18447` quantum satisfiability over complex polynomial systems ships as an
  assignment problem over 𝔽₁₁.
- `2411.04916` kissing numbers, with explicit real coordinates and sign patterns,
  ships as `planted_spherical_subcode_3colour` over a conflict graph.
- `2311.15057` rectangle contacts takes the paper's integer-coordinate variant when
  a real-coordinate one exists.

Every one passed all gates and the oracle pool. The mathematics was discarded
before the solver saw anything.

The domain-attack audit was already evidence of this and I misread it: families
fell to Algorithm X, 1-in-3 DPLL and spectral+greedy. Generic discrete solvers do
not crack genuinely geometric or analytic problems. **The attack that works is a
measurement of the core.**

## Fixed

- `NATIVE` is now a required module field: domain / core / objects / intuition /
  reduction. `domain` is what the solver reasons about, not the arXiv category.
- STEP 0 requires building in the paper's own objects first, and forbids replacing a
  problem over ℝ, ℂ, manifolds or functions with a graph/SAT/finite-field surrogate
  unless the paper licenses it — with these four cases quoted as the warning.
- `submit.sh` refuses a module whose declared core contradicts the instance it hands
  the solver, and refuses a continuous-domain claim over a discrete core with
  `reduction=None`. Both real failures are blocked by it; honest declarations pass
  and are recorded as *discretised analogue*.
- `scripts/corpus_report.py` reports the corpus by core so the collapse is visible.

## Not fixed

The source pool. 45.7% of the 12,167 strong papers are `graph structures` and only
5.3% touch any continuous category (math.AP: 6 papers). Better prompts recover some
diversity from existing papers; a balanced benchmark needs a new retrieval pass
targeting symbolic computation, real algebraic geometry, dynamical systems, ODEs,
optimization and special functions — and quotas enforced on **core**, not category.

Until then the accurate claim is **tool-free intuition for finite constructive
search**, not mathematical intuition.
