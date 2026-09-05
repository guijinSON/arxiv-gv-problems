# Verified generator for arXiv:2107.07024

| Profile field | Value |
|---|---|
| Track | **B — no-tool compression** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | exact cover / bipartite edge-colouring |
| Certificate | matrix certificate: explicit disjoint rainbow bases |
| Intended intuition | invariant — modular midpoints and five shared signed radii |
| Domain essentiality | native; no reduction |

## Problem and trust status

[McGuinness, *Rota's Basis Conjecture for Matroids with Density Close to One*](https://arxiv.org/abs/2107.07024) defines a rainbow basis by choosing one element from each coloured matroid basis, with the chosen elements themselves forming a basis. Two rainbow bases are disjoint when a colour never reuses an element. This generator gives the solver the uniform matroid `U_{n,n+2}` and `n` coloured bases, each encoded by the two ground elements it omits, and asks for the `n-2^3 = n-8` disjoint rainbow bases promised by Theorem 1.2.

Generation is inverse: it first chooses modular centres and five signed radius pairs, builds every two-element omission symmetrically around its centre, and retains the other `n-8` translations as the planted certificate. Verification is exact set membership and cardinality; it never reads `inst["answer"]` and accepts any valid collection.

G and V are locally verified. The local Track-B evidence also passes, but the required external hardness claim is **pending**. The fresh bare run completed seven real calls: easy was solved 3/3, medium was solved 2/3, and the first hard call failed. The OpenRouter account then reached its total limit, so four redraws errored and the harness correctly refused to issue a verdict. The structural-hint and placebo runs were likewise blocked before a scored attempt. All script-owned records are retained rather than replaced with invented evidence.

## Why Track B

The paper does not prove search hardness. Sections 5–12 construct certificates using Rado/matroid intersection, alternating paths, and path-chain repairs. The introduction also cites the known easy strongly-base-orderable class, which contains this uniform-matroid specialization. A Track A label would therefore be false.

The domain-standard route here regularises the coloured incidence graph to an `n`-regular bipartite multigraph and repeatedly finds augmenting-path perfect matchings. The implementation is polynomial, `O(n(n+2)^3)`, solves 8/8 shipping instances, and used 28,190 counted edge-scan/augmentation operations (0.0567 s in the final, heavily loaded shared-host run; 30,494 operations was the eight-seed maximum). The compact route takes modular midpoints, finds the ten shared forbidden offsets, and translates the centres; it uses 285 modular operations. The mechanical route is easy for software but not realistically executable unaided in the evaluation context.

## Worked demo

For `make_instance(n=9, seed=7)`, the ground set is `0,...,10`, the matroid is `U_{9,11}`, and the nine input bases omit:

```text
colour 0: 0,5    colour 1: 5,10   colour 2: 4,6
colour 3: 4,8    colour 4: 1,8    colour 5: 7,10
colour 6: 5,6    colour 7: 3,4    colour 8: 6,7
```

The complete task is to give one list of nine distinct labels, in colour order, avoiding the corresponding pair. One answer is:

```json
[[8, 2, 5, 6, 10, 3, 0, 9, 1]]
```

`verify(inst, inst["answer"])` returns `(True, "ok")`. Dropping its last entry returns `(False, "rainbow basis 0 must contain exactly 9 entries")`. A person can solve this smallest setting on paper by a short greedy matching; it is deliberately illustrative rather than hard.

## Difficulty presets

| Preset | `n` | Required bases | Answer atoms | Compact operations | Status |
|---|---:|---:|---:|---:|---|
| demo | 9 | 1 | 9 | 45 | hand-scale illustration |
| easy | 11 | 3 | 33 | 77 | solved by the bare pool, 3/3 |
| medium | 15 | 7 | 105 | 165 | solved by the bare pool, 2/3 |
| hard | 19 | 11 | 209 | 285 | designated shipping preset; 0/1 before quota blocked completion |

The next escalation exceeds the 256-atom output cap, so `escalate()` returns `"cap_bound"`; this is not a mathematical rejection.

## Gate results

| Gate | Result | Measured evidence |
|---|---|---|
| G1 planted verifies | pass | 12/12 preset-seed instances; all answers JSON-native |
| G2 corruption | pass | drop, swap, duplicate, empty, and out-of-range all rejected with 5 distinct reasons |
| G3 round trip | pass | realistic prose/fence/tag response parsed and verified |
| G4 guess resistance | pass | 0/200,000 under the row-feasible structure-aware prior |
| G5 density and baseline | pass | shipping sampled density 0/200,000; demo exact count 3,339,664 of 387,420,489; reference cost 28,190 operations / 0.0567 s |
| G6 adversaries | pass | four attacks at 0/8 each; reference algorithm 8/8 |
| G7 scaling | pass | `n=39` builds and verifies; search-space bit length grows by 4,615 |
| G8 canonical key | pass | 80 invariance and 80 carried-witness checks; 20/20 unrelated keys distinct |
| G9(c) caps | pass | 762 chars, 191 estimated tokens, 209 atoms, 285 intended operations |

## Oracle loop

| Preset | Seed | Model | Solved | Why |
|---|---:|---|---|---|
| easy | 1861467083 | OpenAI Terra | yes | verified witness |
| easy | 1655043929 | Gemini 3.8 Flash | yes | verified witness |
| easy | 1221213753 | Gemini 3.8 Flash | yes | verified witness |
| medium | 7730373 | Gemini 3.8 Flash | no | used an omitted element |
| medium | 1402332742 | OpenAI Terra | yes | verified witness |
| medium | 1987924126 | Gemini 3.8 Flash | yes | verified witness |
| hard | 1598315551 | Gemini 3.8 Flash | no | exhausted 32,000 tokens without emitting an answer |
| hard | four further seeds | OpenAI Terra | error | HTTP 403 total-key-limit errors; not scored |

There is no `hardened`, `too_easy`, or `cap_bound` verdict: the script stopped because the pool became unreachable. The single hard failure is evidence, but it is not the three scored failures required to hold the level.

## G9 diagnostic

| Arm | Solved / scored attempts | Outcome |
|---|---:|---|
| bare | 0/1 at hard | one length-limited failure before quota exhaustion |
| structural hint | 0/0 | four HTTP 403 redraw errors |
| placebo hint | 0/0 | four HTTP 403 redraw errors |

Because errors do not count as oracle attempts, `hinted - placebo` is unmeasured, not zero. No conclusion about the hint's causal value is justified yet. The answer is 762 characters, approximately 191 tokens, and 209 atomic entries; the intended route uses 285 exact modular operations, all within G9(c).

## Use

```python
import gen_2107_07024 as g

inst = g.make_instance(n=19, seed=42)
statement = g.render(inst)
answer = g.parse_answer("<answer>" + __import__("json").dumps(inst["answer"]) + "</answer>")
assert g.verify(inst, answer) == (True, "ok")
```

From the repository root, emit instances with:

```bash
bash scripts/emit.sh 2107.07024
```

After quota is restored, regenerate the hardness evidence from this directory with `python3 ../../scripts/harden.py gen_2107_07024.py`; run the structural and placebo arms in their existing scratch directories with `GV_HINT_MODE=structural` and `GV_HINT_MODE=placebo` respectively. Each invocation overwrites its transcript.

## Caveats

This is an intentionally easy algorithmic class and makes only a Track B claim. Seeing the midpoint/radius invariant makes the planted schedule straightforward; a different augmenting-path implementation also solves it quickly. The zero-hit G4 estimate is under a prior that already enforces every colour's membership and no-reuse constraints but does not condition on per-basis injectivity—the remaining cross-colour matching condition is the search core. It establishes an observed rate below `1/200,000`, not a proof of a distributional probability. The attack panel did not run ILP, SAT, or alternative edge-colouring heuristics. The canonical key uses colour refinement, distance profiles, and multigraph invariants rather than complete graph-isomorphism canonisation, so rare nonisomorphic collisions remain possible. Most importantly, the incomplete hard and G9 arms mean this result must not be submitted as externally hardened until the harness runs complete normally.
