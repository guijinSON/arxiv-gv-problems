# Dillon graph affine-equivalence generator

This module turns the CCZ-classification step in Bartoli, Grimaldi, and Stănică, [“On the Classification of Dillon’s APN Hexanomials”](https://arxiv.org/abs/2511.01003), into a witness problem.  It evaluates a random normalized Dillon hexanomial from Section 1 over `K = GF(2^(2n))`, forms its graph in the binary space `K × K`, and independently scrambles the graph twice.  A solver receives the two unordered point sets and must return an invertible binary affine map carrying the first set onto the second.  Checking is exact: apply the map to every source point and compare sets.

## Why this family, and why trust it

Section 1, Equation (1.1), fixes the polynomial form; Section 6’s Computational Classification theorem makes complete CCZ-equivalence testing the paper’s classification operation.  A CCZ witness is exactly an affine permutation of the product space mapping one graph to the other.  The module samples that affine witness uniformly **before** selecting coefficients or displaying either set.  It then applies an independent affine scramble to the source and independently shuffles both input orders, so the plant has no block or positional signature.  `random_candidate` uses an even stronger, structure-aware prior: it forces one chosen source point to map to a uniformly chosen target point.

The paper does **not** prove a complexity lower bound for recovering a CCZ map.  The H claim is instead the standard one for affine point-set/code equivalence: no polynomial-time or closed-form recovery method is known in general, while a proposed map is checked in time linear in the displayed set.  The small-field regime is genuinely easy: Section 6 exhaustively classifies `q=2,4`, `enumerate_all` handles the smallest `q=2` instance, and the oracle pool solved the `n=2` preset.  The shipped `n=3` regime has 64 points in 12 ambient dimensions and held against three vendors.  This construction intentionally does not ask whether a polynomial is APN: an APN “yes” has no cheap positive witness, and the paper’s Theorem 2.3 and summary theorem expose classified/easy coefficient regimes.  A directly planted non-APN collision was also discarded because random-direction derivative-kernel elimination solved about half its instances.

## Worked easy example (`n=2`, seed 0)

```text
AFFINE EQUIVALENCE OF TWO BINARY POINT SETS

The ambient space is the 8-dimensional vector space over GF(2).  A point
is written as exactly 2 hexadecimal digits, with leading zeroes retained;
this is the ordinary 8-bit binary encoding.  The two blocks below are
UNORDERED sets, each containing exactly 16 distinct points.
Their line order has no meaning.

Find any affine permutation T(v) = M v XOR t that maps the entire SOURCE set
onto the entire TARGET set.  Here M is an invertible 8 by 8 binary
matrix and t is a 8-bit vector.  All arithmetic is over GF(2): matrix
products use XOR for addition and AND/parity for scalar products.

Matrix convention: provide 8 binary row strings, top row first.  The top
row computes the leftmost (most significant) output bit.  Inside every row and
vector string, the rightmost bit is coordinate 0.  Thus an identity matrix is
listed from 10000000 down to 00000001.
Order within the answer matters for matrix rows.  Repeated rows are allowed by
the syntax but make M singular and are invalid.

SOURCE
4b
f2
9a
60
3b
48
7d
b8
8c
03
35
1e
bd
ce
e9
cb
END SOURCE

TARGET
4f
1d
8b
8f
58
9e
38
ca
7e
40
5a
e9
3b
c4
15
05
END TARGET

Give your final answer inside <answer></answer> tags, as one JSON object with
exactly two fields: "matrix", a list of exactly 8 binary strings of length
8, and "offset", one binary string of length 8.  Do not use 0x
prefixes.  The following shows the exact format (it is the identity example,
not necessarily a solution):
<answer>{"matrix":["10000000","01000000","00100000","00010000","00001000","00000100","00000010","00000001"],"offset":"00000000"}</answer>
Output nothing else inside the tags.
```

One answer is:

```text
<answer>{"matrix":["11011000","01100010","11000010","11100011","01101011","00001010","01000010","11110111"],"offset":"11111000"}</answer>
```

`verify(inst, answer)` returns `(True, "ok")`.  Dropping the last row returns `(False, "shape: expected exactly 8 matrix rows")`.

## Difficulty presets

| Preset | `n` | Points per set | Ambient bits | Status |
|---|---:|---:|---:|---|
| easy | 2 | 16 | 8 | Rejected: GPT-5.6-Terra solved it |
| medium | 3 | 64 | 12 | **Ships; all three oracle attempts failed** |
| hard | 4 | 256 | 16 | Available, not needed by the loop |
| extreme | 5 | 1,024 | 20 | Available, not needed by the loop |

Each increment of `n` quadruples the number of displayed points. `escalate` increases `n` by one through `n=7`.

## Mandatory gates

| Gate | Measured result |
|---|---|
| G1 planted verifies | 12/12 (four presets × three seeds) |
| G2 corruption | 5/5 rejected with distinct reasons |
| G3 round trip | Tagged JSON inside prose/fences parsed exactly |
| G4 structure-aware guess | 0/200,000; uniform `GL(12,2)` part with offset forced to map one source anchor to a uniform target point |
| G5 sparse | 192 / 322,560 valid at the only brute-force-feasible `n=1` case (`5.95e-4`) |
| G6 attacks | Outlier 0/8; greedy 0/8; 32-restart heuristic 0/8 |
| G7 scaling | `n=2→4`: 16→256 points; planted witnesses both verify |
| G8 canonical key | 80/80 relabellings invariant, 60/60 carried witnesses real, 20/20 unrelated shipping keys distinct |

The full measurements are in [`selftest_report.json`](selftest_report.json).

## Oracle hardening loop

| Preset | Seed | Model | Solved? | Why |
|---|---:|---|---|---|
| easy | 1315989065 | Claude Sonnet 5 | No | Empty length-limited response |
| easy | 1265791903 | GPT-5.6-Terra | **Yes** | Valid affine witness |
| easy | 385196591 | Gemini 3.1 Pro Preview | No | Parsed map had the wrong image |
| medium | 1891594774 | Gemini 3.1 Pro Preview | No | Parsed map had the wrong image |
| medium | 722064864 | Grok 4.6 | No | Parsed map had the wrong image |
| medium | 450217283 | GPT-5.6-Terra | No | Parsed map had the wrong image |

The script-owned verdict is `hardened`, with `shipping_params={"n":3}`.  See [`llm_loop_transcript.jsonl`](llm_loop_transcript.jsonl) and [`.meta.json`](.meta.json) for the complete replies, timings, master seed, and pool.

## Use

```python
from gen_2511_01003 import (
    DIFFICULTY, SHIPPING_DIFFICULTY, make_instance,
    parse_answer, render, verify,
)

params = DIFFICULTY[SHIPPING_DIFFICULTY]
inst = make_instance(seed=12345, **params)
question = render(inst)
candidate = parse_answer(model_output)
ok, reason = verify(inst, candidate)
```

From the repository root, emit 20 fresh shipping instances with:

```bash
bash scripts/emit.sh 2511.01003 20
```

## Caveats

The paper establishes the relevance and exact meaning of CCZ equivalence, not the computational hardness of recovering it.  A specialized code-equivalence, tensor-isomorphism, SAT, Gröbner-basis, or individualization/refinement solver was not tested and could change the hardness assessment.  G4 samples an invertible linear part and forces one free source-to-target point correspondence; it still does not model a solver conditioned on all differential invariants visible in the sets.  The point sets come from random Dillon candidates and are not promised APN.  Multiple witnesses can exist because graph sets have affine automorphisms; `verify` accepts all of them.

`canonical_key` is not a complete affine canonical form—the exact problem is intractable enough that computing one would undermine the family.  It hashes a structural differential spectrum, iterative XOR-colour refinement, and (through the 12-bit shipping width) the full codimension-two affine-intersection spectrum.  It is proven invariant under input order, independent affine relabellings, side swaps, and their compositions, and distinguished all 20 mandated shipping test seeds.  A separate 100-seed shipping stress sweep produced 93 distinct keys: those seven collisions may be genuinely CCZ-equivalent graphs or conservative over-collapsing, and `emit.sh` therefore resamples them.  Widths 13–20 omit the expensive codimension-two term; above width 20 the key falls back to the coarser spectrum.  Easy `n=2` should not be used even though its blind-guess probability is tiny: the oracle result demonstrates why search-space size alone is not hardness evidence.
