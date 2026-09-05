# Critical maximum independent sets (arXiv:0906.4609)

> Status: **locally verified, but not shippable yet**. The bare oracle run
> defeated `easy`, `medium`, `hard`, and the first denser escalation. At the next
> level the OpenRouter key reached its total quota before a three-model verdict.
> The harness therefore wrote no `harden_verdict`; this is neither a hardness
> pass nor a paper rejection.

| Profile field | Value |
|---|---|
| Track | B — no-tool compression |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | graph |
| Certificate form | integer tuple (a vertex set) |
| Intended intuition | constraint propagation from equality in a matching bound |
| Domain essentiality | native |
| Reduction | none |

## What the family is

The source is Levit and Mandrescu, [*Critical independent sets and
König–Egerváry graphs*](https://arxiv.org/abs/0906.4609). An instance gives a
finite simple graph and a matching with exactly one exposed vertex. The solver
must return an independent set consisting of that vertex and one endpoint from
every matching edge.

The witness is checked locally and exactly. A matching edge contributes at most
one vertex to an independent set, so an independent set of size `|M|+1` is
maximum. Mapping each selected matched vertex to its mate also proves
`|S|-|N(S)| <= 1`; the returned set attains one. Thus `verify` checks the graph,
matching, independence, neighborhood, and cardinalities without reading
`inst["answer"]` or running an optimizer.

Generation is inverse: it samples the chosen endpoint of every matching edge,
adds the exposed vertex, and only then inserts edges that avoid the planted set.
The matching and planted set establish `alpha(G)+mu(G)=|V|`, so the graph is
König–Egerváry. Theorem 2.7 then says every maximum independent set is critical.

## Why this is Track B

Track A would be false. Section 1 explicitly states that critical-independent-set
search is polynomial-time solvable, and Theorem 2.7 connects maximum critical
sets to maximum independent sets on König–Egerváry graphs. With the displayed
near-perfect matching there is an even simpler reference method: choose one
endpoint per matching edge, translate graph edges into 2-SAT clauses, and solve
the implication graph by strongly connected components in `O(|V|+|E|)`.

At the provisional shipping parameters (`n=96`, seed 271828), the reference
method used 5,373 implication/DFS arc operations and 0.000948 seconds. The
compact route starts with the exposed vertex and propagates forced orientations
along alternating edges. It makes 96 forced choices, although the measured
implementation inspected 797 adjacency entries. This is a genuine compression,
but the completed oracle calls show that the named presets are not hard enough.

## Worked demo

`make_instance(seed=0, n=6, block_size=3, cross_percent=70,
internal_percent=15)` has vertices 0 through 12, target size 7, matching

```text
(4,8) (2,1) (12,11) (7,9) (3,10) (5,6)
```

and adjacency list

```text
0: 11
1: 2 3 5 6
2: 1 6
3: 1 10
4: 8 9 11
5: 1 6 10
6: 1 2 5 7 10
7: 6 9 11
8: 4 11 12
9: 4 7 12
10: 3 5 6
11: 0 4 7 8 12
12: 8 9 11
```

The answer is `[0,2,3,4,5,7,12]`. A person can solve this demo by hand:
vertex 0 is exposed, so 11 is excluded, and the six remaining matching choices
propagate through adjacency.

```python
>>> verify(inst, [0, 2, 3, 4, 5, 7, 12])
(True, 'ok')
>>> verify(inst, [0, 2, 3, 4, 5, 7])
(False, 'wrong length: expected 7 vertices')
```

## Difficulty presets

| Preset | Matching pairs | Block size | Cross % | Internal % | Oracle status |
|---|---:|---:|---:|---:|---|
| demo | 6 | 3 | 70 | 15 | hand example; never ships |
| easy | 96 | 16 | 50 | 15 | defeated: 1/3 solved |
| medium | 112 | 14 | 50 | 15 | defeated: 3/3 solved |
| hard | 128 | 16 | 50 | 15 | defeated: 3/3 solved |

`SHIPPING_DIFFICULTY="easy"` remains only a provisional local-test target. It
must not be emitted until a complete rerun finds a level where all attempts fail,
then the ladder must be slid to put those held parameters under a named preset.

## Local gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted witnesses across all presets; JSON-native answers |
| G2 | pass | 5/5 corruptions rejected with five distinct reasons |
| G3 | pass | tagged JSON recovered through prose and a Markdown fence |
| G4 | pass | 0/200,000 structure-aware guesses; language size `2^96` |
| G5 | pass | exact density `1/2^96`; sampled 0/200,000; reference cost 5,373 operations |
| G6 | pass | four attacks each 0/8; SCC reference 8/8, as expected for Track B |
| G7 | pass | doubled `n=192` builds and verifies; answer-space exponent doubles |
| G8 | pass | 300/300 symmetry compositions invariant and real; 20/20 unrelated keys distinct |
| G9(c) | pass | 329 chars, 97 atoms, about 83 tokens, 96 forced-orientation operations |

The four failing G6 attacks are lower-degree endpoint selection, static greedy
matching order, 256 random orientations, and one-hop propagation from the
exposed vertex. The full SCC reference algorithm used 41,844 recorded operations
over eight instances and solved all eight, as Track B requires.

## Bare oracle loop

| Round | Parameters | Seeds with answered calls | Solved / failed / error | Outcome |
|---:|---|---|---:|---|
| 0 | `n=96, cross=50` | 1401792884, 1142412639, 1206664431 | 1 / 2 / 0 | escalate |
| 1 | `n=112, cross=50` | 1855808685, 1091486080, 633238003 | 3 / 0 / 0 | escalate |
| 2 | `n=128, cross=50` | 1813873639, 1290635453, 1831365792 | 3 / 0 / 0 | escalate |
| 3 | `n=128, cross=55` | 1909491940, 2124449473, 304789766 | 2 / 1 / 0 | escalate |
| 4 | `n=128, cross=60` | 1722040257 | 0 / 1 / 4 | aborted by total quota |

The last row is incomplete. Its four errors are HTTP 403 quota failures and do
not count as oracle failures. `.meta.json` consequently has no final verdict.

## G9 arms

| Arm | Scored result | Infrastructure errors | Conclusion |
|---|---:|---:|---|
| bare | 1 solved / 3 attempts at provisional `easy` | 0 in that arm | the provisional rung is defeated |
| structural hint | unavailable | 4 | quota blocked every call |
| placebo hint | unavailable | 4 | quota blocked every call |

`hinted - placebo` is unavailable, and `hinted_verdict` remains `pending`.
The two `g9_*_transcript.jsonl` files were produced by isolated harness runs and
contain only the quota errors. Under the current protocol these arms are
diagnostic rather than gating, but they still must be rerun to characterize what
the family measures.

## Use

```python
from gen_0906_4609 import DIFFICULTY, make_instance, parse_answer, render, verify

inst = make_instance(seed=12345, **DIFFICULTY["easy"])
question = render(inst)
candidate = parse_answer("<answer>[0,2,5]</answer>")
ok, reason = verify(inst, candidate)
```

After OpenRouter quota is restored, rerun the bare harness from this directory:

```bash
python3 ../../scripts/harden.py gen_0906_4609.py
```

Only after it records `hardened`, updates the named ladder, and the local gates
are rerun should artifacts be emitted from the repository root:

```bash
bash scripts/emit.sh 0906.4609 20 <shipping-preset>
```

## Caveats

- This is emphatically Track B. The exact SCC implementation solves every local
  audit instance in about a millisecond; there is no complexity-theoretic claim.
- G4 samples the exact prior forced by the displayed matching: the exposed
  vertex plus one uniform endpoint per edge. The `1/2^96` density does not model
  correlated propagation, and the oracle results demonstrate that cardinality
  alone is not hardness.
- The compact route makes 96 forced orientations but scans roughly 750–800
  adjacency entries. Failure at a larger rung may measure bookkeeping as much as
  discovery of the alternating-reachability invariant.
- Full spectral relaxations, an external SAT package, and a separate generic
  maximum-critical-independent-set implementation were not run. The exact 2-SAT
  SCC solver is the strongest directly relevant reference algorithm here.
- `canonical_key` is a typed 1-WL fingerprint, not a complete graph-isomorphism
  canonical form. It is proved invariant for arbitrary vertex renaming, edge and
  matching reorderings, endpoint reversal, and all tested compositions, but may
  collide on nonisomorphic colored graphs.
- The current blocker is external quota. The evidence is not sufficient to ship,
  reject, or claim `cap_bound`; a complete script-owned run is still required.
