# Exact-weight binary syndromes from arXiv:2411.19413

## What the family is

The instance gives `n` indexed vectors in the binary vector space `F_2^r` and a target. The witness is exactly `h` distinct, 1-based indices whose vectors XOR to the target. Checking is cheap and exact: enforce the shape, XOR the indexed bit strings, and compare once.

This is the binary form of an *h-linear combination* in Section 3, Definitions 3.1-3.2 of Guerrero Pantoja, Castillo, and Trujillo Solarte, [“S_h-sets and linear codes over F_q”](https://arxiv.org/abs/2411.19413). In `F_2` the only nonzero coefficient is 1. Theorem 3.1 supplies the parity-check-matrix correspondence: selecting columns is the support form of binary syndrome decoding.

## Why it is hard, and what was avoided

The solver is finding a binary solution of exact Hamming weight `h` to `Hx=s`. The exact-weight decision problem `LinEq=` is NP-complete, and Theorem 3.1 of Arvind, Köbler, Kuhnert, and Torán proves W[1]-hardness parameterized by `h` even at three occurrences per variable ([author manuscript](https://www.sebastian-kuhnert.de/cs/paper/linearequations.pdf)); the foundational general-decoding NP-completeness result is Berlekamp, McEliece, and van Tilborg ([Caltech record](https://authors.library.caltech.edu/records/aw9vs-ann16)). The shipping preset keeps `h` and `r` growing with `n`, uses dense unstructured equations, and has about `2^71.8` exact-shape candidates.

The paper itself proves structure, not computational hardness. Its Lemma 3.1 makes every linearly independent set automatically `S_h`-linear, and its post-Theorem-3.2 example constructs one directly from a BCH code; either would make a reconstruction task transparent or decodable. This generator instead samples the support first, creates dense columns independently of support membership, and defines the target last. It also avoids fixed small `h`, small `r`, equation size at most two, and structured BCH/Goppa decoding regimes.

## Worked demo (`demo`, seed 0)

The demo is intentionally easy and is **not shipped**: `h=n`, so it exists only to show the complete contract compactly.

```text
Exact-weight binary syndrome problem

All vectors below belong to the binary vector space F_2^r. Addition in
this space is coordinatewise XOR: 0+0=0, 0+1=1, and 1+1=0.
Here r=12. Each displayed bit string has exactly 12 coordinates;
the leftmost displayed bit is coordinate 1 and the rightmost is coordinate r.

Choose exactly h=24 DISTINCT vectors from the n=24 indexed vectors
so that their XOR is exactly the target. Each index may be used at most once.
Indices are 1-based and inclusive (1 through n). Order does not matter.

target: 100101011111
vectors:
 1: 010101011110
 2: 100001001111
 3: 000000000101
 4: 010110010010
 5: 001010111101
 6: 110010010000
 7: 001101110000
 8: 000111000111
 9: 010101010101
10: 010010011001
11: 011101101100
12: 001000001100
13: 111111101010
14: 011111100110
15: 101010110001
16: 001111011100
17: 100010000011
18: 100111001011
19: 010001101000
20: 011000100100
21: 101000011110
22: 110000100011
23: 101000000010
24: 011110110101

Give your final answer inside <answer></answer> tags, as exactly
24 comma-separated decimal indices. Repeats are forbidden; order is ignored.
Example of the required syntax (not a hint): <answer>1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24</answer>
Output nothing else inside the tags.
```

Answer:

```text
<answer>1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24</answer>
```

`verify(inst, inst["answer"]) == (True, "ok")`. Dropping index 24 returns `(False, "wrong number of indices: expected 24, got 23")`.

## Difficulty presets

| preset | n | r | h | exact-shape space | status |
|---|---:|---:|---:|---:|---|
| demo | 24 | 12 | 24 | 1 | Rejected: G4 is 1 and all 3 oracles solved it |
| **standard** | **160** | **92** | **16** | **4,059,949,873,964,357,469,950** | **Ships; oracle-hardened** |
| hard | 208 | 120 | 20 | 3,676,359,629,336,848,917,409,411,920 | Reserve escalation rung |
| extreme | 256 | 148 | 24 | 3,325,115,649,019,001,626,323,394,511,652,000 | Reserve escalation rung |

`escalate()` increases `n`, `r`, and `h` at fixed approximate rates after the named ladder. The standard preset held, so no generated escalation is shipped.

## Gate results at shipping difficulty

| gate | measured result |
|---|---|
| G1 | 16/16 plants verified: 4 presets x 4 seeds |
| G2 | 5/5 corruptions rejected with 5 distinct reasons |
| G3 | Prose + Markdown fence round-trip passed; malformed text returned `None` |
| G4 | 0/250,000 uniform exact-size guesses; 4.06e21 structure-aware candidates |
| G5 | Exact small count: 2/91,390 = 2.1884e-5 |
| G6 | 0/8 successes for each of 6 attacks |
| G7 | `n=320,r=184,h=32` plant verified; search-space floor grew 71 to 146 bits |
| G8 | 100/100 relabellings invariant and witness-preserving; 20/20 unrelated keys distinct |

The six G6 attacks were first positions, lowest column weight, closest column-to-target distance, highest affine-dependency degree, greedy residual reduction, and 20-restart swap local search.

## Oracle hardening loop

Every reply parsed. Thus none of the failures below is an output-contract false negative.

| preset | model | seed | result | checker reason |
|---|---|---:|---|---|
| demo | GPT-5.6 Terra | 816929056 | solved | ok |
| demo | Claude Sonnet 5 | 1877308237 | solved | ok |
| demo | Gemini 3.1 Pro Preview | 760034692 | solved | ok |
| standard | Claude Sonnet 5 | 1119439405 | failed | selected vectors XOR to the wrong target |
| standard | Grok 4.6 | 1550330522 | failed | selected vectors XOR to the wrong target |
| standard | Gemini 3.1 Pro Preview | 1022246242 | failed | selected vectors XOR to the wrong target |

Verdict: `hardened`, one escalation from demo to standard. The complete replies, timing, HTTP status, and finish reasons are in `llm_loop_transcript.jsonl`; the script-owned master seed and verdict are in `.meta.json`.

## Use

```python
import random
import gen_2411_19413 as g

inst = g.make_instance(seed=7, **g.DIFFICULTY[g.SHIPPING_DIFFICULTY])
question = g.render(inst)
candidate = g.parse_answer("<answer>" + ", ".join(map(str, inst["answer"])) + "</answer>")
assert g.verify(inst, candidate) == (True, "ok")
guess = g.random_candidate(inst, random.Random(99))
```

From the repository root, emit 20 checked, deduplicated shipping instances with:

```bash
bash scripts/emit.sh 2411.19413 20 standard
```

Run the local gates from this directory with `python3 gen_2411_19413.py`.

## Caveats

- NP-completeness and W[1]-hardness are worst-case results; they do not prove that this particular planted random distribution is average-case hard. The multi-vendor failures are empirical evidence, not a reduction.
- G4 samples uniformly from exactly `h` distinct indices, correctly incorporating the obvious answer shape. `0/250,000` is the measured rate for that prior, not a rigorous upper bound below `1e-6`, and says nothing about a nonuniform or algebraic solver.
- A small random affine-dependency gadget is independent of planted membership and makes structural duplicate detection useful. It also creates known four-column relations and sometimes alternative witnesses. Degree, greedy, and local-swap attacks failed, but the gadget could assist a stronger future attack.
- Not tested: optimized information-set decoding, SAT/MILP solvers, large-memory meet-in-the-middle, GPU/quantum search, or learned decoding. Small fixed `h`, small `r`, highly redundant targets, `h` near 0 or `n`, and structured decodable codes can all make the task easy.
- `canonical_key` is invariant under every tested column permutation, coordinate permutation, general `GL(r,2)` basis change, binary global translation, and their composition. Full affine binary-matroid isomorphism is intractable here, so the key uses the colour-refined zero-XOR 4-hypergraph plus low-order target counts. It can theoretically collide on non-isomorphic problems.
