# Planted Orthogonal Vectors problem generator

| Profile field | Value |
|---|---|
| Track | **A — structural hardness** |
| Native domain | combinatorics |
| Object regime | finite discrete |
| Computational core | CSP/SAT-style cross-collection search |
| Certificate | integer tuple, encoded as `[set_id,row_index]` records |
| Intuition | constraint propagation through the running coordinatewise AND |
| Domain essentiality | native; no reduction |

This module implements the search distribution from Kühnemann, Polak, and Rosen,
[“The Planted Orthogonal Vectors Problem”](https://arxiv.org/abs/2505.00206).
The solver gets `k` collections of equal-length binary vectors and must choose one
row from each so their bitwise AND is zero. The answer is checked by range checks
and exact integer ANDs. Generation follows the paper's Section 3 `Plant` procedure:
the row locations are chosen first, so the certificate is known without solving the
instance. Lemmas 2 and 5 guarantee orthogonality and the proper-marginal camouflage.

## Why this is Track A

Conjecture 10 rules out `n^(k-epsilon)` average-case algorithms in the regime
`d=alpha(n) log n`, fixed `k`, and `alpha(n)=omega(1)`. Here `k=4` and
`alpha(n)=max(96,ceil(log2(n)^2))`; at shipping size `(n,d,alpha)=(96,633,96)`.
A search solver would also decide the planted-vs-model problem by verifying its
output, so the decision conjecture is relevant to this witness task. This is a
conjectural distributional claim, not a worst-case NP-hardness claim.

The paper's easy regimes matter. Section 1.2 describes faster algorithms for fixed
`p` and `d=Theta(log n)`, while Theorem 16 gives a downsampling attack of expected
cost `n^(k-k/(1+alpha))`. At the shipping parameters its exponent is 3.95876 and
its estimate is about 70.4 million tuples, close to the full 84.9 million. The
implemented attack examined one million tuples on each of eight seeds—eight million
total in 18.492 seconds in the final gate run—and found no witness. The certificate checker itself is
`O(k)` arbitrary-precision ANDs.

## Worked demo

This is the complete rendered `demo` instance for seed 731 (`n=2`, `k=3`, `d=36`):

```text
Planted k-Orthogonal Vectors

There are k=3 collections, numbered 0 through 2. Each collection contains n=2
binary vectors, with rows numbered 0 through 1. Every vector has d=36
coordinates, numbered 0 through 35.

Choose exactly one row from every collection. The chosen vectors are orthogonal
when, at every coordinate, at least one chosen vector has bit 0; equivalently,
their coordinatewise bitwise AND is the all-zero vector.
This instance is guaranteed to contain at least one such tuple.

Vectors below are 9-digit hexadecimal integers with leading zeros. Coordinate 0
is the least-significant bit (the rightmost hex digit contains coordinates
0,1,2,3); any padding bits to the left of coordinate d-1 are 0. Hex digits use
0-9 and a-f.

Collection 0:
  0: bf8989060
  1: b896c8a51

Collection 1:
  0: 09fc38e80
  1: 4371c676a

Collection 2:
  0: fbc70ec1b
  1: 1c6a85b91

Output a JSON list of exactly k records [set_id,row_index], one for every set_id,
in increasing set_id order. A row-index value may repeat in different collections.
All indices are 0-based and both endpoints of each stated range are allowed.

Give your final answer inside <answer></answer> tags.
Format example only: <answer>[[0,0],[1,1],[2,0]]</answer>
Output nothing else inside the tags.
```

Coordinate 0 is the least-significant bit. The answer is
`[[0,1],[1,1],[2,0]]`; `verify` returns `(True, "ok")`. Changing the first choice
to row 0 gives `[[0,0],[1,1],[2,0]]` and returns
`(False, "not_orthogonal: every selected vector has a 1 at coordinate 20")`.
With only eight possible tuples, this smallest setting is genuinely hand-solvable.

## Presets

| Preset | n | k | alpha floor | Status |
|---|---:|---:|---:|---|
| demo | 2 | 3 | 36 | paper-scale illustration; not scored |
| easy | 96 | 4 | 96 | **shipping preset**; all local gates pass |
| medium | 144 | 4 | 96 | build and planted verification pass |
| hard | 216 | 4 | 96 | build and planted verification pass |

No preset was rejected by a local gate. The external oracle ladder could not score
even the first preset because every request returned HTTP 403 for exhausted
OpenRouter key limits; therefore there is no honest `hardened`/`too_easy` verdict.

## Gate results

| Gate | Result | Measurement |
|---|---|---|
| G1 | pass | 12/12 planted checks; answers JSON-native |
| G2 | pass | 5/5 corruptions rejected with five distinct reason codes |
| G3 | pass | tagged, fenced, prose-surrounded answer round-trips |
| G4 | pass | 0/200,000 structure-aware uniform row tuples valid |
| G5 | pass | demo exact count 1/8; shipping sample 0/200,000; baseline 8,000,000 nodes in 18.492 s |
| G6 | pass | five attacks, each 0/8; Section 9 downsampling included |
| G7 | pass | doubled `n=192` builds/verifies; space grows from 84,934,656 to 1,358,954,496 |
| G8 | pass | 80/80 relabelling and witness-transport checks; 20/20 unrelated keys distinct |
| G9(c) | pass | 29 chars, 8 atoms, about 8 tokens, 163 exact nibble/shape operations |

## Oracle loop

The repository-owned harness made these bare-prompt calls before correctly stopping
on infrastructure failure. Error calls are not model failures and support no
hardness inference.

| Preset | Model | Seed | Scored result | Why |
|---|---|---:|---|---|
| easy | Gemini 3.8 Flash | 2083188677 | error | OpenRouter HTTP 403: key limit exceeded |
| easy | Gemini 3.8 Flash | 1272812962 | error | OpenRouter HTTP 403: key limit exceeded |
| easy | GPT-5.6 Terra | 1846383811 | error | OpenRouter HTTP 403: key limit exceeded |
| easy | GPT-5.6 Terra | 903064306 | error | OpenRouter HTTP 403: key limit exceeded |

## G9 diagnostic arms

| Arm | Solved / scored attempts | API errors |
|---|---:|---:|
| bare | 0 / 0 | 4 |
| structural hint | 0 / 0 | 4 |
| placebo hint | 0 / 0 | 4 |

`hinted - placebo` is undefined because neither arm obtained a scored attempt; no
conclusion about the usefulness of the running-AND hint is possible. The separate
transcripts preserve all errors. The size/effort cap is unaffected and passes with
29 answer characters, eight atomic integers, and 163 exact operations after a
candidate path is identified.

## Use

```python
from gen_2505_00206 import DIFFICULTY, make_instance, render, verify

inst = make_instance(seed=7, **DIFFICULTY["easy"])
print(render(inst))
ok, reason = verify(inst, inst["answer"])
assert (ok, reason) == (True, "ok")
```

From the repository root, after a successful oracle rerun, emit instances with:

```bash
bash scripts/emit.sh 2505.00206 20 easy
```

## Caveats

The Track A claim inherits Conjecture 10; it is not a theorem that these finite
instances are hard. `0/200,000` estimates density under the exact prior a reader gets
for free—uniformly one row per collection—but it is not an exact shipping solution
count and is not a confidence proof of uniqueness. Python samples `p` to the
53-bit precision of `random.Random.random`; verification remains wholly exact.
The attacks do not include a high-performance native-code OV implementation,
SAT compilation, GPU bitset search, or the Alman–Andoni–Zhang average-case method.
The canonical key is a tested strong invariant, not a complete isomorphism
canonical form. Most importantly, the required external no-tool evaluation remains
unmeasured until the OpenRouter quota is restored and all three harness runs are
repeated; this directory should not be submitted as hardened before then.
