# arXiv:1401.3909 — three-game road-trip planning

> **Status:** the native generator and every local gate pass. The mandatory
> multi-vendor verdict is incomplete: two models solved `easy`, after which the
> OpenRouter account-wide limit returned HTTP 403 on every redraw and on both
> shipping-preset G9 arms. Those errors are preserved and are not model failures.

| Profile field | Value |
|---|---|
| Track | **B** — no-tool compression |
| Native domain | optimization |
| Object regime | finite discrete |
| Computational core | exact cover |
| Certificate | integer tuple: an ordered three-game road-trip plan |
| Intended intuition | invariant: equal home-distance residues identify the trips |
| Domain essentiality | **native** |
| Reduction | none |

## What the family is

Hoshino and Kawarabayashi's [*Scheduling Bipartite Tournaments to Minimize
Total Travel Distance*](https://arxiv.org/abs/1401.3909) defines BTTP travel in
Section 2: teams leave home, travel directly among consecutive away venues,
and return home after the last away game. In Section 5, the authors compute an
individual lower bound `ILB_t` by splitting the opposing league into ordered
three-game road trips.

This generator poses exactly that native Section 5 problem. The solver receives
a symmetric integer metric on one home venue and `n` away venues and must
partition all away teams into ordered triples whose total closed-trip distance
meets an exact threshold. The answer is checked by coverage tests and direct
integer addition; no hidden data, optimization solver, or `inst["answer"]` is
consulted.

Instances are certified by construction. The away venues are leaves of a
weighted tree, three leaves per branch. Every complete plan traverses every
leaf edge twice. The planted grouping traverses each positive branch edge
twice, while any different grouping splits a branch between trips and traverses
that edge at least four times. Thus the planted grouping is optimal by an edge-
traversal identity, not by solving the completed instance.

## Why Track B

This is deliberately not a Track-A claim. Theorem 1 proves general BTTP and
BTTP* NP-complete via 3-SAT, but worst-case hardness says nothing about this
tree-metric distribution. Section 4 also identifies an easy special regime:
Propositions 1 and 2 prune the `n=6` NPB instance using global constraints and
individual lower bounds (the paper still reports 34,716 seconds of Maplesoft
computation).

The paper's Section 5 mechanical route enumerates
`n!/((n/3)! 2^(n/3))` ordered trip plans—340,540,200 cases already at its
`n=15` NBA calculation. A stronger algorithm exists for this generated
distribution and is reported honestly: scan every away pair and compute
`D(H,i)+D(H,j)-D(i,j)`. Positive slack means the two leaves share a branch. At
shipping `n=126`, this exact `O(n^2)` scan succeeds 8/8, uses 7,875 pair tests
and 15,750 additions/subtractions, and measured 0.0117 seconds on average
(0.0641 seconds maximum).

The compact route is to reduce each home distance modulo `n+1`; equal residues
are exactly the planted triples. It uses 126 modular reductions. The benchmark
tests whether a no-tool solver notices that invariant instead of trying to
execute thousands of arithmetic operations or search an exact cover.

## Worked demo

`make_instance(seed=0, **DIFFICULTY["demo"])` renders:

```text
Three-game road-trip planning (arXiv:1401.3909, Section 5)

One team has a home venue H and must play once at each of n=6 away
venues labelled 0,...,5. It starts at H, makes exactly
2 separate road trips, and returns to H after every trip. Every
road trip visits exactly three distinct away venues, and every away venue must
occur in exactly one trip.

A trip [a,b,c] is ordered: its route is H -> a -> b -> c -> H. Its length is
D(H,a)+D(a,b)+D(b,c)+D(c,H). The total plan length is the sum over all trips.
The order of the trips is irrelevant. Reversing one trip gives the same length
because D is symmetric, but any orientation is accepted.

The exact symmetric integer distance matrix has zero diagonal. Its strict
upper triangle is listed below. The first row gives D(H,0),...,D(H,n-1).
Each later row i gives D(i,i+1),...,D(i,n-1), in that order.

H: 7136474 5396184 8704083 13229632 13471152 3346751
0: 12532658 15840557 20366106 20607554 10483153
1: 14100007 18625556 18867336 8742935
2: 21933455 22175235 12050834
3: 26700784 16576383
4: 16817831
5: (empty)

Find a road-trip plan whose total length is at most T=102567888
(inclusive).

Give your final answer inside <answer></answer> tags as one JSON list of exactly
2 ordered triples, using each integer 0,...,5
exactly once. Example syntax: <answer>[[0,1,2],[3,4,5]]</answer>
Output nothing else inside the tags.
```

The answer is `<answer>[[0,4,5],[1,2,3]]</answer>`, and `verify` returns
`(True, "ok")`. Swapping the first members gives `[[1,4,5],[0,2,3]]`, for
which it returns `(False, "travel 102568220 exceeds target 102567888")`.
This demo is hand-solvable: the home-distance residues modulo 7 are
`[2,3,3,3,2,2]`.

## Difficulty presets

| Preset | Away venues | Weight scale | Structure-aware road plans | Rendered chars | Status |
|---|---:|---:|---:|---:|---|
| demo | 6 | 1 | 90 | 1,369 | hand example |
| easy | 18 | 16 | 138,940,401,600 | 2,941 | solved by two oracle calls |
| medium | 60 | 256 | about `3.26e57` | 23,316 | locally verified |
| hard | 126 | 4,096 | about `3.84e147` | 109,703 | **provisional shipping preset** |

Escalation first raises `weight_scale` at fixed `n`, making wrong plans closer
to the exact optimum relative to the displayed magnitudes without changing the
answer. Only after that fixed-length crowding axis is exhausted does it double
to `n=252`; another increase would exceed the 256-atom answer cap.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 20/20 planted plans verify and JSON-round-trip |
| G2 | pass | five corruptions rejected with five distinct reasons |
| G3 | pass | tagged nested JSON recovered through prose and Markdown |
| G4 | pass | 0/200,000 structure-aware guesses; exact density `2.8503e-128` |
| G5 | pass | demo exactly 9/90; shipping density 0/200,000; reference mean 0.0117 s |
| G6 | pass | home-sort, shortest-edge greedy, consecutive labels, and 256 restarts all 0/8; reference scan 8/8 |
| G7 | pass | `n=252` builds/verifies; the answer remains under the 256-atom cap |
| G8 | pass | 20/20 relabelings and compositions preserve the key and carried witness; 20/20 unrelated keys differ |
| G9(c) | pass | 479 characters, 120 estimated tokens, 126 atoms, 126 intended operations |

An additional audit exhaustively checked 20 independently generated `n=6` and
`n=9` instances: every exact valid-plan count matched `3^(n/3)`, and all 13,430
tested triangle inequalities held.

## Oracle loop and G9 arms

The script-owned bare run reached two valid `easy` answers before the external
key limit was exhausted. The third attempt and all redraws failed at the API
layer, so the harness correctly produced no hardness verdict and never reached
`medium` or `hard`.

| Preset | Model | Result |
|---|---|---|
| easy | Gemini 3.8 Flash | solved, verified |
| easy | GPT-5.6 Terra | solved, verified |
| easy | both vendors over four redraws | HTTP 403 key limit |

The G9 hard-only runs were made in separate scratch directories as required.

| G9 arm | Solved / valid attempts | Script calls | Conclusion |
|---|---:|---:|---|
| bare shipping | 0 / 0 | not reached by the interrupted main ladder | unavailable |
| structural hint | 0 / 0 | 4 | all HTTP 403 |
| placebo hint | 0 / 0 | 4 | all HTTP 403 |

`hinted - placebo` is unavailable, not zero: API errors do not consume attempts.
Therefore the transcripts support no claim about whether the residue hint helps.
The size/effort arm still passes at 479 characters, 126 atoms, and 126 exact
operations.

## Use

```python
import json
from gen_1401_3909 import DIFFICULTY, make_instance, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["hard"])
assert verify(inst, inst["answer"]) == (True, "ok")
raw = "Result: <answer>" + json.dumps(inst["answer"]) + "</answer>"
assert parse_answer(raw) == inst["answer"]
```

From the repository root, after obtaining a valid hardening verdict:

```bash
bash scripts/emit.sh 1401.3909 20 hard
```

## Caveats

This is the individual three-game road-trip optimization used to compute
`ILB_t` in Section 5, not a complete `2n`-team BTTP schedule. That scope is
native to the paper, but it omits match synchronization, no-repeat constraints,
and interactions among all teams' trips.

The exact random-guess density applies to the declared prior: uniform ordered
trip plans after quotienting trip order and reversal. It says nothing about a
solver exploiting metric structure. Indeed, the positive home-slack scan solves
every generated instance quickly; that fact is the reason for Track B. The
attack panel did not run ILP/CP-SAT, subset dynamic programming, or every
possible modular checksum. The canonical key uses sorted weighted row profiles
rather than full weighted-graph canonization and could over-collapse a
contrived collision. The 109,703-character shipping prompt is large, although
the answer and intended arithmetic route are within G9's caps.

Most importantly, the required multi-vendor shipping evidence is absent because
of the external account limit. This directory is locally verified but must not
be represented as oracle-hardened or emitted until `harden.py` and both G9 arms
complete with real model responses.
