# arXiv 2505.00298 — retained rejected generator

**Status: rejected after adversarial audit.** Generation and exact verification
work, but the generated distribution fails Track A hardness. The retained
module is `rejected_gen_2505_00298.py`; it is evidence for revisiting the
decision, not a shippable corpus generator.

| profile field | value |
|---|---|
| declared track | A — structural hardness (failed) |
| native domain | combinatorics |
| object regime | finite discrete |
| computational core | CSP/SAT |
| certificate | exact symbolic red/blue set partition |
| intended intuition | constraint propagation in not-all-equal triples |
| domain essentiality | licensed reduction |
| reduction | paper-central, Section 2.2, Theorem 2.6 |

## Problem and trust model

Yu and Sun's [*Internally-disjoint Pendant Steiner Trees in
Digraphs*](https://arxiv.org/abs/2505.00298) defines a pendant `(S,r)`-tree as
an out-tree rooted at `r` containing `S`, with every terminal of total degree
one. Two are internally disjoint when they share no arc and their common
vertices are exactly `S`.

The candidate uses Theorem 2.6 exactly. From a 3-uniform hypergraph it builds
the theorem's symmetric digraph: a root, a clique of variable vertices, one
terminal per hyperedge, root–variable adjacencies, and incidence adjacencies.
The solver returns a red/blue partition in which each hyperedge meets both
parts. The checker deterministically expands each part into one out-tree and
checks every required graph property exactly. It accepts any valid partition
and never reads the planted answer.

The witness is known by construction: generation samples a balanced colouring
first, then a connected simple degree-regular hypergraph around it. Every
variable has the same degree and the one-red/two-red edge types are balanced.
Consequently G and V are sound even though H fails.

## Why the hardness claim failed

Theorem 2.6 proves NP-completeness for fixed `ell=2` and growing terminal count
`k`; this family is in that formal regime. Theorem 2.3's polynomial case, where
both `k` and `ell` are fixed, is deliberately avoided. But these are worst-case
results and say nothing about the inverse-generated distribution.

A greedy/noisy WalkSAT attack picks a monochromatic edge, flips the endpoint
that minimizes the new bad-edge count, and makes a random move 25% of the time.
It solved all eight audit seeds at every named non-demo preset:

| preset | n | degree | successes | wall clock over 8 seeds |
|---|---:|---:|---:|---:|
| easy | 198 | 6 | 8/8 | 0.0068–0.0413 s |
| medium | 222 | 6 | 8/8 | 0.0036–0.1081 s |
| hard | 246 | 6 | 8/8 | 0.0045–0.0512 s |

At fixed `n=198`, degrees 8, 10, and 12 also scored 8/8, generally faster.
The self-test's shipping seed took 2,688 flips, 52,920 edge inspections, and
0.0124 seconds. This falsifies Track A. It cannot be relabelled Track B: no
short invariant replaces the search, so the compact route is the same 2,688
flips as the mechanical route rather than a sub-300-operation insight.

## Worked demo

For `n=6`, `degree=2`, `seed=0`, the four hyperedges are:

```text
e1: v4 v5 v6
e2: v2 v6 v3
e3: v4 v2 v1
e4: v3 v5 v1
```

One certificate is `{"blue":[2,3,5],"red":[1,4,6]}`.
`verify(inst, inst["answer"])` returns `(True, "ok")`. Repeating vertex 1 in
the blue part returns `(False, "red and blue overlap at a vertex")`. A person
can solve the demo by checking the 31 partitions with vertex 1 fixed red; 13
are valid.

## Local gates

| gate | result | measurement |
|---|---|---|
| G1 | pass | 12/12 preset/seed witnesses verify and JSON-round-trip |
| G2 | pass | 5/5 corruptions rejected with distinct reasons |
| G3 | pass | tagged JSON recovered through prose and a Markdown fence |
| G4 | pass | 0/200,000 structured guesses; space `2^197-1` |
| G5 | **fail** | WalkSAT solved; 2,688 flips and 52,920 inspections |
| G6 | **fail** | WalkSAT 8/8, despite five weaker attacks at 0/8 |
| G7 | pass | doubled instance builds and its planted witness verifies |
| G8 | pass | 40 invariance/witness checks; 20 unrelated keys distinct |
| G9(c) | pass | 702 chars, about 176 tokens, 198 atoms, 198 stated operations |

The G4 sampler is uniform over nonempty two-partitions after quotienting global
colour exchange. It enforces shape, coverage, uniqueness, and nonempty parts,
but does not condition on the unadvertised planted balance. Its low hit rate
measures blind guessing only; it did not predict WalkSAT's gradient.

## Oracle loop and G9 arms

The bare, structural-hint, and placebo harnesses were run in their required
separate directories. Every redraw returned HTTP 403 `Key limit exceeded`, so
each transcript contains four service-error rows and zero scoreable attempts.
No service error is treated as a model failure.

| arm | solved / attempts | errors | conclusion |
|---|---:|---:|---|
| bare | unavailable / 0 | 4 | no oracle verdict |
| structural | unavailable / 0 | 4 | no hinted verdict |
| placebo | unavailable / 0 | 4 | no placebo verdict |

Thus `hinted - placebo` is unavailable. The answer-size figures are 702
characters, about 176 tokens, and 198 atomic entries. The local G6 failure is
already decisive, independently of the unavailable oracle pool.

## Reproduce the retained evidence

```python
import rejected_gen_2505_00298 as g

inst = g.make_instance(seed=0, **g.DIFFICULTY["demo"])
assert g.verify(inst, inst["answer"]) == (True, "ok")
report = g.selftest()
assert report["G6_adversary_panel"]["pass"] is False
```

Run `python3 rejected_gen_2505_00298.py` to regenerate the self-test report.
Do not run `scripts/emit.sh` for this directory: `REJECTED.md` is the controlling
decision.

## Caveats

- The successful attack is a heuristic, not a worst-case polynomial algorithm;
  its 8/8 success is a distributional refutation of this benchmark claim, not a
  contradiction of Theorem 2.6.
- No industrial SAT/SMT solver or SDP relaxation was run. They are unnecessary
  to reject a family already solved by the cheaper attack.
- The ten-round rooted Weisfeiler–Leman key is invariant but not a complete
  hypergraph isomorphism canonizer.
- A different inverse distribution based on Theorem 2.2 or 2.6 might still be
  viable. This decision rejects the implemented planted-regular family, not
  the paper's theorems.
