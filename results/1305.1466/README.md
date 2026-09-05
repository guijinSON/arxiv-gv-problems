# Full-rainbow certificate generator for arXiv:1305.1466

> **Status:** the generator and all local gates pass. The required external
> hardening loop passed at `hard`: all three usable shipping-preset replies
> failed verification. The live repository policy currently uses two vendors
> over three fresh attempts per level. A stricter four-vendor rerun was attempted,
> but a 900-second Grok timeout followed by quota errors prevented that extra run
> from producing a verdict.

| profile | value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | permutation / bipartite incidence matching |
| Certificate | integer tuple: one colour per displayed matching edge |
| Intended intuition | change of variables: expose an affine permutation modulo a prime |
| Domain essentiality | native; no reduction |

## Problem and trust

Kotlar and Ziv’s [“Large matchings in bipartite graphs have a rainbow
matching”](https://arxiv.org/abs/1305.1466) defines a full rainbow matching as
pairwise-disjoint edges, one chosen from every member of a family (Section 1).
Theorem 2.1 proves existence for `p` matchings of size `floor(5p/3)`. This
generator supplies exactly such a bipartite graph and family, together with a
displayed `p`-edge matching `R`. The solver must give a bijection assigning each
edge of `R` to a different colour class that contains it. Verification checks
the permutation, exact memberships, class sizes, and endpoint disjointness.

Generation is inverse. It samples nonzero `a` and offset `b` modulo prime `p`,
puts `B_(a*c+b)` in `F_c`, and only then draws same-marginal core decoys and
private padding. Thus `c=a^-1(t-b)` certifies every `B_t`. The certificate is
known before the finished instance exists. Twelve preset/seed combinations
verified, were JSON-native, and met Theorem 2.1’s exact size regime.

## Why Track B

This is not a Track A claim. Once `R` is fixed, put its edges on one side of an
incidence graph and the colour classes on the other; a perfect matching is
exactly the requested certificate. Hopcroft–Karp solves this in
`O(E sqrt(V))`. At the shipping preset the executable reference solved 8/8
instances, averaging **2,443 edge scans, three BFS rounds, and 0.000360 s**.
The paper itself also reasons through alternating replacements from a maximum
partial rainbow matching in Proposition 2.1 and Theorem 2.1.

The no-tool task is to avoid executing that matching algorithm. The first six
labelled incidence rows contain a unique line `t=a*c+b (mod p)`. Testing those
small-row differences, taking one modular inverse, and emitting by recurrence
was executed and verified at **266 exact arithmetic operations**. Section 1’s
easy greedy bound `g(p)<=2p-1` is another warning against claiming structural
hardness; the benchmark measures recognition of the planted change of
variables, not hardness of rainbow matching in general.

## Worked demo

This is the complete `render(make_instance(seed=7, n=7, width=2))` instance:

```text
Certify a displayed full rainbow matching

A matching is a set of graph edges with no shared endpoint. A full rainbow
matching for colour classes F_0,...,F_{p-1} is a matching of p edges that
uses exactly one edge from every F_c. An edge may belong to several F_c;
the certificate must specify which distinct colour is assigned to each edge.

Here p=7. The graph is bipartite. Its displayed core vertices are
L_0,...,L_6 on the left and R_0,...,R_6 on the right.
For 0 <= t < 7, B_t is the edge (L_t,R_t). Thus
R={B_0,...,B_(p-1)} is already a p-edge matching.

There are p colour classes. Every F_c is itself a matching of exactly
floor(5p/3)=11 edges. The row for F_c below lists the 2
core indices t for which B_t belongs to F_c.
In addition, F_c contains exactly 9 private padding edges
(X_(c,j),Y_(c,j)) for j=0,...,padding-1. All X_(c,j) and Y_(c,j)
are vertices different from every core vertex and from private vertices
with another pair (c,j). These padding edges make the stated class size
exact; they are not edges of the displayed matching R.
The order of rows and the order of indices within a row have no meaning.

Core incidences:
  F_1: 4 0
  F_5: 2 3
  F_2: 2 0
  F_6: 5 0
  F_3: 4 3
  F_4: 6 0
  F_0: 3 1

Assign every edge of R to a different colour class containing it. This
assignment certifies that the displayed R is a full rainbow matching.

Give your final answer inside <answer></answer> tags as one JSON array of exactly 7 integers.
Array entry t is the colour c assigned to B_t; the array must be a
permutation of all integers 0,...,6. Indices are 0-based, both
bounds are inclusive, and no colour may repeat.
Example format: <answer>[2,0,1]</answer>
Output nothing else inside the tags.
```

One answer is `<answer>[2,0,5,3,1,6,4]</answer>`;
`verify` returns `(True, "ok")`. Swapping its first two entries gives
`[0,2,5,3,1,6,4]`, rejected as
`(False, "edge B_0 is not present in F_0")`. A person can solve this demo by
checking only seven rows; exhaustive enumeration finds two answers out of 5040.

## Difficulty presets

| preset | prime `p` | core incidences per `F_c` | total size of every `F_c` | answer atoms | status |
|---|---:|---:|---:|---:|---|
| demo | 7 | 2 | 11 | 7 | hand example; skipped by hardener |
| easy | 79 | 4 | 131 | 79 | defeated: 2/3 oracle replies solved |
| medium | 97 | 6 | 161 | 97 | defeated: 1/3 oracle replies solved |
| hard | 107 | 8 | 178 | 107 | **ships: 0/3 oracle replies solved** |

Escalation first increases incidence crowding at fixed answer length, then
raises the prime. It reports `cap_bound` after prime 167 rather than pretending
the answer-format ceiling is a mathematical failure.

## Gate results

| gate | measured result |
|---|---|
| G1 | 12/12 planted witnesses verified; 12/12 JSON-native; 12/12 in the exact theorem regime |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | tagged, fenced prose round-tripped the 107-entry answer |
| G4 | 0/200,000 valid structure-aware guesses; candidate language `107!` (572 bits) |
| G5 | shipping density estimate 0/200,000; demo exact count 2/5040; reference 2,443 scans / 0.000360 s |
| G6 | frequency outlier, first fit, 256 random restarts, and slopes ±1/±2: 0/8 each; Hopcroft–Karp 8/8 |
| G7 | requested doubled size 214 rounded to prime 223, built and verified |
| G8 | 80/80 invariant and 80/80 carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | 319 characters, about 80 tokens, 107 atoms; 266 intended exact operations |

## Oracle loop and G9 arms

The live `harden.py` policy sampled OpenAI and Google over three fresh attempts
per level. A single valid witness defeats a rung; all three must fail for it to
hold. The shipping level has three parsed answers and three exact verification
failures, so its result does not rest on transport or parsing errors.

| preset | model | seed | solved | exact outcome |
|---|---|---:|---:|---|
| easy | OpenAI | 910215215 | yes | verified witness |
| easy | Google | 927094424 | no | empty length-limited response |
| easy | Google | 173404554 | yes | verified witness |
| medium | Google | 1027812791 | no | unfinished, no tagged answer |
| medium | OpenAI | 365752811 | yes | verified witness |
| medium | OpenAI | 121196632 | no | membership failure at `B_17` |
| hard | Google | 766420955 | no | repeated/missing colour |
| hard | OpenAI | 1882502493 | no | membership failure at `B_98` |
| hard | Google | 230677666 | no | repeated/missing colour |

The task text called for four vendors, while the repository’s current hardener
and validator use a two-vendor pool. I also invoked the named four-vendor pool:
Anthropic produced a usable failure, Grok exceeded the 900-second hard deadline,
and the subsequent redraws hit the account-wide quota. That aborted run is not
counted as hardness evidence; its script-owned records are retained in
`four_vendor_attempt_transcript.jsonl` and `four_vendor_attempt_meta.json`.

| G9 arm at `hard` | solved / usable attempts | outcome |
|---|---:|---|
| bare | 0/3 | hardened |
| structural hint | 0/0 | four pre-inference HTTP 403 quota errors |
| placebo hint | 0/0 | four pre-inference HTTP 403 quota errors |

Hinted minus placebo is substantively undefined; `selftest_report.json` stores
`0.0` only as the zero-attempt sentinel. No hint-responsiveness conclusion is
warranted. The structural hint names only the affine-incidence invariant. The
answer is 319 characters, approximately 80 tokens, and 107 atoms; the intended
affine route takes 266 counted exact operations.

## Use

```python
import json
from gen_1305_1466 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=123, **DIFFICULTY["hard"])
prompt = render(inst)
wire = "<answer>" + json.dumps(inst["answer"]) + "</answer>"
answer = parse_answer(wire)
assert verify(inst, answer) == (True, "ok")
```

Emit from the repository root with:

```bash
bash scripts/emit.sh 1305.1466
```

## Caveats

The task certifies a **specified** matching `R`; it does not ask for an arbitrary
full rainbow matching. Theorem 2.1 fixes the native regime, but inverse
generation—not the theorem—guarantees that this particular `R` is rainbow.
Private padding also makes unrestricted full-rainbow search easy, so no hardness
claim is made for that different task. This restriction is the largest caveat.

The 0/200,000 estimate is only for a uniform random permutation, the strongest
freely implied prior; it says nothing about adaptive matching or affine recovery.
The local panel did not run industrial ILP/CP-SAT, specialized list recovery, or
broader affine slopes; all are expected to help, which is consistent with Track
B. The canonical key is an eight-round Weisfeiler–Lehman invariant, not a complete
graph-isomorphism canon and can collide on non-isomorphic inputs. Finally, the
mechanical/compact gap is 2,443 versus 266 counted operations—not a
complexity-theoretic separation. The shipping transcript satisfies the live
two-vendor repository policy; the task text's stricter four-vendor evidence and
both non-bare G9 diagnostics remain unavailable because of timeout/quota limits.
