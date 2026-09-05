# Verified generator for arXiv:1608.04838

| profile field | value |
|---|---|
| Track | **B — no-tool compression** |
| native domain | combinatorics |
| object regime | finite field |
| computational core | graph (solved mechanically through the displayed linear representation) |
| certificate form | matrix certificate (three binary-vector row strings) |
| intuition | change of variables: a shared syndrome turns the target-set XOR into three cross-part XORs |
| domain essentiality | native |
| reduction | none |

## What the problem is, and what is verified

This generator uses the exact *type-j set* and *S-absorbing edge* definition from Section 3 of Lu, Wang, and Yu, [“Almost perfect matchings in k-partite k-graphs”](https://arxiv.org/abs/1608.04838). It specializes to `k=3`. Each of the three labeled vertex parts is `GF(2)^d`; a displayed full-rank binary matrix, three coordinate permutations, and a target syndrome set define the hyperedges. The solver must return one edge disjoint from `S` that can be replaced by two edges covering `S`. `verify` checks dimensions, disjointness, the candidate edge, and both possible replacement pairs by exact GF(2) arithmetic. It never reads `inst["answer"]`.

Generation is by composition of identities, not search. If `q` is the XOR of the target syndromes, construction makes `q=A(P1(a xor a'))`. Three cross-part XORs then give the planted edge and both replacement edges syndrome `q`. The target set is composed around `q`; the planted syndrome is no longer the zero-syndrome outlier present in an earlier draft.

## Why this is Track B

The paper proves an existential co-degree theorem, not average-case hardness. Section 3, Lemma 3.2 shows that suitable co-degrees create many absorbing edges, and Lemma 3.4 obtains a small absorbing matching probabilistically. Therefore this module makes its efficient algorithm explicit: row reduction and three syndrome solves over GF(2), complexity `O(r^2 d)`. On eight hard instances it solved 8/8 and averaged **18,088 counted bit operations** (**0.0017--0.0032 s per instance** across repeated local runs). The reference method can use any displayed target syndrome and does not use the planted target-XOR relation. The compact route is **240 coordinate XORs** after recognizing the shared-syndrome invariant. The intended difficulty is finding that compression without a sandbox, not computational hardness.

Theorem 1.1 guarantees a matching of size `n-1` when every part has sufficiently large size and minimum legal co-degree at least `n/k`. This generator does **not** claim to pose that whole matching problem: its witness is the local absorber used in the non-extremal proof. At the hard preset its co-degree fraction is `21/65536`, deliberately small enough that a structure-aware random edge is rarely absorbing.

## Worked demo (`seed=0`)

This is hand-scale (`d=5`), and a person can solve it by applying the three displayed permutations and XORs.

```text
Find an S-absorbing edge in the following 3-partite 3-uniform hypergraph.

Definitions and conventions.
GF(2)^d means all binary vectors of length d=5; coordinates are numbered 0 through 4.
XOR is coordinatewise addition modulo 2.
There are three labeled vertex parts V1, V2, V3, each equal to GF(2)^d; copies in different parts are distinct vertices even when their bit vectors agree.
A triple (x,y,z) always means x in V1, y in V2, and z in V3.
For a listed permutation P, (P v)[j] = v[P[j]].
For the displayed 3-by-5 binary matrix A, A v is ordinary matrix-vector multiplication modulo 2.
A triple (x,y,z) is a hyperedge exactly when A(P1 x XOR P2 y XOR P3 z) is one of the listed target syndromes T.

The set S consists of a,a' in V1, b in V2, and c in V3.
An edge (x,y,z) is disjoint from S when x is neither a nor a', y is not b, and z is not c.
A disjoint edge (x,y,z) is S-absorbing exactly when at least one of these two alternatives holds:
  (i) (a',y,c) and (a,b,z) are both hyperedges;
  (ii) (a,y,c) and (a',b,z) are both hyperedges.
This is the k=3 specialization of replacing one matching edge by two edges covering S.

Every legal pair has exactly 20 neighbors among 32 vertices in the missing part.

P1 = [4,0,1,2,3]
P2 = [3,4,0,1,2]
P3 = [0,1,2,3,4]

Rows of A (coordinate 0 first):
10011
10110
01111

Target syndromes T (syndrome coordinate 0 first):
100
000
101
001
111

S vectors (coordinate 0 first):
a  = 10100
a' = 00101
b  = 11111
c  = 01100

Return exactly a JSON list [x,y,z] of three quoted 5-character binary strings; each string lists coordinate 0 first.
Give your final answer inside <answer></answer> tags.
Format example: <answer>["00000","00000","00000"]</answer>
Output nothing else inside the tags.
```

Answer: `<answer>["00111","11000","01101"]</answer>`.

`verify(inst, answer)` returns `(True, "ok")`. Dropping the last vector returns `(False, "answer is missing a part vector")`.

## Presets

| preset | d | rank r | targets | part size | compact XORs | status |
|---|---:|---:|---:|---:|---:|---|
| demo | 5 | 3 | 5 | 32 | 15 | hand example |
| easy | 28 | 11 | 7 | 2^28 | 84 | oracle run blocked before scoring |
| medium | 52 | 15 | 17 | 2^52 | 156 | locally verified |
| hard | 80 | 16 | 21 | 2^80 | 240 | **shipping preset; locally verified** |

## Gate results

| gate | result | measured evidence |
|---|---|---|
| G1 | pass | 12/12 planted witnesses verified |
| G2 | pass | five corruptions rejected for five distinct reasons |
| G3 | pass | tagged fenced JSON round-tripped; garbage returned `None` |
| G4 | pass | 0/200,000 valid structure-aware random disjoint edges |
| G5 | pass | hard candidate space `566158880010163435688005443564815567574036143874954027768548815798272`; demo exact answer count 10,240; reference 8/8 |
| G6 | pass | minimum-weight, greedy edge-first, 256 random restarts, and raw-coordinate XOR each 0/8; generic Gaussian reference 8/8 |
| G7 | pass | doubled dimension 160 built and verified |
| G8 | pass | 100/100 symmetry checks, 100/100 carried witnesses, and both reduced and shipping samples had 20/20 distinct keys |
| G9(c) | pass | 250 characters, about 63 tokens, 240 binary entries in 3 row strings, 240 intended XORs |

## Oracle and G9 status

The required script-owned runs were attempted, but OpenRouter returned HTTP 403 `Key limit exceeded` on every redraw. Errors are not counted as model failures, so there is **no hardened verdict and no oracle-backed hardness claim yet**.

| run | preset | scored | API-error records | conclusion |
|---|---|---:|---:|---|
| bare | easy | 0 | 4 | pool unreachable |
| structural hint | hard | 0 | 4 | pool unreachable |
| placebo hint | hard | 0 | 4 | pool unreachable |

`hinted - placebo` is therefore unavailable, not zero. The structural hint’s effect has not been measured. The three transcript files are genuine `harden.py` outputs containing the failed calls; rerun them after restoring OpenRouter quota and update `G9_ORACLE_RESULTS` from scored attempts.

## Use

From this directory:

```python
import random
import gen_1608_04838 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY["hard"])
question = g.render(inst)
answer = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
candidate = g.random_candidate(inst, random.Random(1))
```

From the repository root, after a successful oracle rerun:

```bash
scripts/emit.sh 1608.04838 20 hard
```

## Caveats

- This is a succinct, highly structured subclass of the paper’s native hypergraphs. GF(2) coordinates are generator structure, not a technique from the paper, and the task covers the absorber definition rather than the main `n-1` matching conclusion.
- The observed 0/200,000 rate uses the strongest obvious prior: candidates are already disjoint hyperedges. It is an empirical density, not a confidence proof that the true probability is below `10^-6`; it also says nothing about a solver that detects the target-XOR invariant.
- The Gaussian algorithm makes every instance easy with tools. No SAT/ILP package was run because the input is a succinct linear predicate rather than an explicit edge list; exact elimination is the stronger native reference attack here.
- The canonical key handles coordinate relabeling, syndrome-basis changes, target ordering, the named-vertex/part swaps, and target-translating affine relabelings tested in G8. It is a strong invariant, not a complete isomorphism test for arbitrary succinct hypergraphs. The recorded shipping check found 20/20 keys distinct in 8.29 seconds total on this machine.
- Most importantly, the four-vendor hardening and all three G9 arms remain externally blocked by the exhausted OpenRouter key. Do not treat this directory as submission-ready until those runs produce scored attempts and `.meta.json` records `verdict: hardened` (or the family is handled according to the script’s actual verdict).
