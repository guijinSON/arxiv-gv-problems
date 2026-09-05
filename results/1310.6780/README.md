# Archived prototype — see REJECTED.md for the final decision

> This README documents the earlier reversible-opcode Track-B prototype.  It is
> retained as audit evidence, but it is not the final disposition of the paper.
> The later scored experiment and paper-level rejection are in `REJECTED.md`.

# arXiv 1310.6780 — exact uncertain-clique probability

> Trust status: the generator and all local gates pass, but this result is **not
> yet oracle-hardened**. The required harness reached OpenRouter and received HTTP
> 403 `Key limit exceeded (total limit)` on every redraw. Its four error records
> are preserved in `llm_loop_transcript.jsonl`; no model failure is claimed.

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | `combinatorics` |
| Object regime | `rational_exact` |
| Computational core | `telescoping` |
| Certificate form | `telescoping` |
| Intended intuition | `change of variables` |
| Domain essentiality | `native` |
| Reduction | none |

## Problem and construction

[Mukherjee, Xu, and Tirthapura, *Mining Maximal Cliques from an Uncertain
Graph*](https://arxiv.org/abs/1310.6780) defines an uncertain graph in Section 2:
possible edges occur independently. Definition 3 calls the probability that a
set is a clique its *clique probability*, and Observation 1 says this is exactly
the product of its internal edge probabilities.

The solver receives a complete uncertain graph, a designated clique containing
all vertices, and exact formulas for its rational edge probabilities. It must
return four rational factors, one for each edge-rank lane, whose product is the
clique probability. The generator samples the four answer factors first. It
then builds each lane from consecutive ratios
`(B+s)/(B+s+1)` and hides their order behind compositions of reversible vertex
and edge-rank operations. Thus generation is inverse generation plus composition
of telescoping identities, never solution of the emitted instance. `verify`
checks the four endpoints by exact integer arithmetic and does not read
`inst["answer"]`.

This is the paper's native rational uncertain-graph object, but it is a fixed-
clique probability subproblem—not the paper's full enumeration task. The prior
idea “plant a high-probability maximal clique” was not used: by Observation 2,
one can greedily extend a clique, so obtaining just one maximal clique would not
support Track A. Theorem 3/MULE's `O(n 2^n)` bound is for enumerating *all*
alpha-maximal cliques, whose exponential output also conflicts with the answer
cap.

## Why Track B

The standard algorithm is precisely Observation 1: evaluate all
`M = n(n-1)/2` edge probabilities and multiply them exactly. At the provisional
hard preset (`n=144`, `M=10,296`, 120 edge-rank operations), the reference
implementation succeeded on 8/8 instances. The recorded run cost 5,081,692
high-level arithmetic/index operations and 1.329497 seconds total, or 0.166187
seconds per instance on this machine.

The compact route is to notice that every opcode is a bijection. The vertex
program merely relabels the complete graph; triangular ranking therefore still
visits every edge rank once. The edge program permutes those ranks again. Each
residue lane consequently contains every `s` from zero to its lane length minus
one, so it telescopes to `B/(B+length)`. The four divisions finish the answer.
The measured intended route is at most 174 exact operations, versus over five
million for the mechanical route. This is an insight gap, not a complexity-
theoretic hardness claim.

## Worked demo (`seed=7`)

This is the complete rendered demo instance (without a hint):

```text
Exact clique probability in an uncertain graph

An uncertain graph is an undirected simple graph in which each possible edge
occurs independently with its stated probability.  The probability that a
vertex set is a clique is therefore the product of the probabilities of all
unordered edges having both endpoints in that set.

Here the vertices are the integers 0 through 7.  Every unordered pair is
a possible edge, and C is the set of all 8 vertices.  Thus C contains all
M = 28 unordered edges.  Compute each edge probability by the exact integer
rules below; `%` is least nonnegative remainder, `//` is floor division,
table/list positions are 0-indexed, and all displayed interval bounds are
inclusive where applicable.

For an index z in 0,...,D-1, execute a program record-by-record with modulus D.
The first integer in each record is its opcode:
  [0,s]     means z = (z+s) % D.
  [1,a,b]   swaps values a and b and leaves every other z unchanged.
  [2]       means z = D-1-z.
  [3,k]     means z = (z//k)*k + (k-1-(z%k)).
  [4,k]     means z = (z%k)*(D//k) + z//k.
  [5,k,s]   means z = (z//k)*k + ((z%k)+s)%k.
Every k appearing below divides its program's modulus exactly.

Vertex program (modulus D=8):
[[0,7],[4,2]]

Edge-rank program (modulus D=28):
[[2],[4,2],[4,4],[0,3]]

Lane bases B[0],...,B[3]:
[12384171716, 9783815741, 13451331761, 8242052952]

For an unordered edge {u,v}:
  1. Run u and v separately through the vertex program, obtaining x and y.
  2. Swap x,y if needed so x<y.
  3. Set t = x*(2*8-x-1)//2 + (y-x-1).
  4. Run t through the edge-rank program, obtaining z.
  5. Set j=z%4 and s=z//4. The edge probability is
     (B[j]+s)/(B[j]+s+1).

Give the exact clique probability in factorized form: output exactly 4 reduced
positive fractions in lane order j=0,...,3. Fraction j must equal the product
of the probabilities of exactly the edges whose computed lane is j;
consequently the product of all four fractions is the probability that C is a
clique. There are no omitted or repeated edges. Each fraction must use decimal
integers as numerator/denominator. The four numerators are distinct and each
lies in the inclusive interval [1073741824,2147483647].

Give your final answer inside <answer></answer> tags, as fractions separated by semicolons.
Example: <answer>1073741824/1073741825; 1073741826/1073741827; 1073741828/1073741829; 1073741830/1073741831</answer>
Output nothing else inside the tags.
```

The answer is:

```text
<answer>1769167388/1769167389; 1397687963/1397687964; 1921618823/1921618824; 1177436136/1177436137</answer>
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping the last
fraction returns `(False, "expected 4 lane fractions")`. A person can solve the
demo on paper: it has only 28 edges, although the reversible-index observation
is still the intended shortcut.

## Difficulty presets

| Preset | n | Edges | Vertex rounds | Rank rounds | Status |
|---|---:|---:|---:|---:|---|
| demo | 8 | 28 | 2 | 4 | hand-scale; skipped by hardening |
| easy | 64 | 2,016 | 20 | 40 | oracle run blocked before scoring |
| medium | 96 | 4,560 | 30 | 80 | not reached |
| hard | 144 | 10,296 | 40 | 120 | provisional `SHIPPING_DIFFICULTY`; local gates pass |

## Gate results

| Gate | Result |
|---|---|
| G1 | 16/16 planted certificates verified; all JSON-native |
| G2 | 5/5 corruptions rejected with five distinct reasons |
| G3 | prose + fenced tagged answer round-tripped; garbage returned `None` |
| G4 | 0/200,000 hits; declared space `2^120` |
| G5 | exact one valid ordered certificate; sampled density 0/200,000; reference 5,081,692 operations |
| G6 | four attacks each 0/8; reference exact product 8/8 as Track B expects |
| G7 | escalated build and doubled `n=288` both verified; answer stayed at 8 atoms |
| G8 | 80/80 invariance and 80/80 carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) | 97 characters, about 25 tokens, 8 atoms, 174 intended operations: within all caps |

## Oracle loop and G9 diagnostic

The main harness made no scored attempt. These are infrastructure errors, not
unsolved answers:

| Preset | Model | Seed | Result | Why |
|---|---|---:|---|---|
| easy | Grok 4.6 | 1468491898 | error | HTTP 403 key total limit |
| easy | Grok 4.6 | 1889594378 | error | HTTP 403 key total limit |
| easy | Gemini 3.1 Pro Preview | 2041507871 | error | HTTP 403 key total limit |
| easy | Grok 4.6 | 1931863472 | error | HTTP 403 key total limit |

| G9 arm | Solved / attempts | Verdict |
|---|---:|---|
| bare | 0/0 | not scored |
| structural hint | 0/0 | unscored: key total limit exceeded |
| placebo hint | 0/0 | unscored: key total limit exceeded |

`hinted − placebo` is undefined with zero attempts (stored as `0.0` only for the
numeric report field), so no conclusion about the claimed change-of-variables
intuition is warranted yet. Replenish the OpenRouter key, rerun the bare harness,
then run the two G9 arms in separate scratch directories before submission.

## Use

```python
from gen_1310_6780 import DIFFICULTY, make_instance, render, parse_answer, verify

inst = make_instance(seed=7, **DIFFICULTY["demo"])
print(render(inst))
candidate = parse_answer("<answer>1769167388/1769167389; 1397687963/1397687964; 1921618823/1921618824; 1177436136/1177436137</answer>")
assert verify(inst, candidate) == (True, "ok")
```

After a successful hardening run, emit records from the repository root with:

```bash
scripts/emit.sh 1310.6780 20 hard
```

## Caveats

- The crucial missing evidence is the four-vendor oracle loop. The current
  `llm_loop_transcript.jsonl` is intentionally not submission-valid because all
  records are API errors and `.meta.json` has no hardness verdict.
- This family measures recognition of a deliberately structured exact product,
  not the hardness of maximal-clique enumeration on natural uncertain graphs.
  A solver specialized for these six reversible opcodes obtains the compact
  answer immediately; that is why the claim is Track B.
- The `2^120` guess space is conservative in one direction: candidates already
  know that each factor is an adjacent reduced fraction. It says nothing about
  a semantic solver's success probability and is not evidence of Track-A
  hardness.
- The panel did not test a language model or a symbolic pattern recognizer; it
  tested four explicit no-tool heuristics. The successful full product is timed
  separately. Wall time is machine-dependent, while the operation count is the
  stable comparison.
- `canonical_key` deliberately identifies all edge-factor reorderings and lane
  renamings with the same endpoint multiset. That is the exact equivalence for
  this all-edge product task, but it is coarser than weighted-graph isomorphism.
- `verify` uses the executable endpoint identity after validating sizes and
  bases; `_reference_product` independently expands every edge and was checked
  8/8. The module uses only the Python standard library, so `gvlib` is not
  required.
